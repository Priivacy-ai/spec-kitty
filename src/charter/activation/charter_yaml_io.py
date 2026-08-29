"""Shared ``charter.yaml`` write helper — INV-9 (WP01 / T003).

Three independent writers mutate ``charter.yaml``: ``activation_engine.
commit_plan`` (activation), ``pack_manager.merge_defaults`` (absent-key
seed), and ``compiler.write_compiled_charter`` (catalog/metadata). None of
them may clobber the sections they don't own — that is the #2772 clobber
reborn one level down, on a *tracked* file (data-model.md Landmine 3 /
alphonso MAJOR-3). Routing all three through this ONE
``load -> mutate-owned-section -> round-trip-save`` helper makes
section-preservation structural rather than conventional: the document is
loaded and saved via ``ruamel.yaml`` round-trip mode (comments and
formatting preserved), and a mutation only ever touches the top-level keys
that belong to the named section.

Layer rule: this module MUST NOT import ``specify_cli`` (C-002 / INV-7).
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

__all__ = [
    "OWNED_SECTIONS",
    "UnknownCharterYamlSectionError",
    "load_charter_yaml",
    "save_charter_yaml",
    "update_charter_yaml_section",
]


#: The activation section is a LOGICAL grouping: on disk these flat keys are
#: root keys (paula BLOCKER-1 — matches ``packs/default.yaml:5-38``), not
#: nested under an ``activation:`` mapping. The helper's "activation" section
#: name refers to this set collectively.
#:
#: The vocabulary itself (WP05 / FR-010 / C4.1) is DERIVED from the single
#: authority :data:`charter.activation.pack_manager.ACTIVATION_YAML_KEYS` via
#: :func:`_activation_keys` rather than hand-restated here -- a hand-written
#: literal previously drifted from the finalize migration's own copy (missing
#: ``activated_glossary_packs``, FR-010/SC-005). ``_ACTIVATION_KEYS`` stays
#: importable as a module attribute (``from charter.activation.charter_yaml_io import
#: _ACTIVATION_KEYS``) via the module ``__getattr__`` below, for callers/tests
#: that still spell it as a plain name.


@functools.lru_cache(maxsize=1)
def _activation_keys() -> tuple[str, ...]:
    """Return the flat activation-key vocabulary, derived from the authority.

    Lazy, function-scoped import of :data:`charter.activation.pack_manager.
    ACTIVATION_YAML_KEYS` -- NOT a module-level import, because
    ``charter.activation.pack_manager`` imports :func:`load_charter_yaml` /
    :func:`update_charter_yaml_section` FROM this module at ITS OWN top
    level; a module-level back-import here would be a circular import
    (``charter.activation.pack_manager`` <-> ``charter.activation.charter_yaml_io``). Deferring to
    call time breaks the cycle: by the time this function actually runs
    (inside :func:`update_charter_yaml_section`, well after both modules have
    finished their own top-level execution), the import is a cheap
    ``sys.modules`` lookup regardless of which module was entered first.
    """
    from charter.activation.pack_manager import ACTIVATION_YAML_KEYS  # noqa: PLC0415 -- avoids import cycle (WP05)

    return ACTIVATION_YAML_KEYS


def __getattr__(name: str) -> object:
    """PEP 562 lazy module attribute: resolve ``_ACTIVATION_KEYS`` on access.

    Mirrors the codebase's established lazy-module-attribute idiom (e.g.
    ``specify_cli.sync.__getattr__``) so ``from charter.activation.charter_yaml_io
    import _ACTIVATION_KEYS`` and ``charter_yaml_io._ACTIVATION_KEYS`` both
    keep working for existing callers/tests without a module-level import
    that would reintroduce the cycle :func:`_activation_keys` avoids.
    """
    if name == "_ACTIVATION_KEYS":
        return _activation_keys()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


#: Sections whose owned content is a single top-level scalar/mapping key —
#: mutating one of these REPLACES that key's entire value.
_SCALAR_SECTIONS: frozenset[str] = frozenset(
    {"governance", "directives", "catalog", "metadata", "overrides"}
)

#: All section names callers may mutate via :func:`update_charter_yaml_section`.
OWNED_SECTIONS: frozenset[str] = _SCALAR_SECTIONS | {"activation"}


class UnknownCharterYamlSectionError(ValueError):
    """Raised when a caller names a section outside :data:`OWNED_SECTIONS`."""

    def __init__(self, section: str) -> None:
        owned = ", ".join(sorted(OWNED_SECTIONS))
        super().__init__(f"Unknown charter.yaml section {section!r}. Owned sections: {owned}")


def _yaml_loader() -> YAML:
    """Construct a ruamel round-trip ``YAML`` instance with stable settings.

    Mirrors the existing project convention (``pack_manager._load_config`` /
    ``schemas.emit_yaml``): default (round-trip) ``typ``, quotes preserved,
    a wide line width so keys are never wrapped mid-value.
    """
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    return yaml


def load_charter_yaml(path: Path) -> Any:
    """Load ``charter.yaml`` preserving comments/formatting for a round trip.

    Returns an empty :class:`~ruamel.yaml.comments.CommentedMap` when the
    file is empty (mirrors the project's existing ``_load_config`` "empty
    file -> empty mapping" convention). Raises ``FileNotFoundError`` when
    ``path`` does not exist — callers that need an absent-file default
    should check ``path.exists()`` themselves; this helper never
    silently fabricates a document for a missing file.
    """
    yaml = _yaml_loader()
    with path.open("r", encoding="utf-8") as fh:
        document = yaml.load(fh)
    return document if document is not None else CommentedMap()


def save_charter_yaml(path: Path, document: Any) -> None:
    """Write ``document`` back to ``path`` via ruamel round-trip dump."""
    yaml = _yaml_loader()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.dump(document, fh)


def update_charter_yaml_section(
    path: Path, section: str, values: dict[str, Any]
) -> None:
    """Load ``charter.yaml`` -> mutate ONE owned section -> round-trip save.

    This is the ONLY writer path ``activation_engine.commit_plan``,
    ``pack_manager.merge_defaults``, and ``compiler.write_compiled_charter``
    use (INV-9). Every top-level key outside the named section is preserved
    byte-for-byte (formatting, comments, key order) because the document is
    loaded and re-dumped in ruamel round-trip mode without touching those
    keys.

    Parameters
    ----------
    path:
        Path to ``charter.yaml``.
    section:
        One of :data:`OWNED_SECTIONS` (``"governance"``, ``"directives"``,
        ``"catalog"``, ``"activation"``, ``"metadata"``, ``"overrides"``).
    values:
        For a scalar section (``governance``/``directives``/``catalog``/
        ``metadata``/``overrides``), the ENTIRE new value for that
        top-level key (the section is replaced wholesale). For the
        ``"activation"`` pseudo-section, a mapping of ``{activated_<kind>
        key: new_value}`` — only the keys present in ``values`` are
        written, so a caller may update a single activation kind (e.g.
        ``pack_manager.merge_defaults`` filling one absent key) without
        touching the other nine.

    Raises
    ------
    UnknownCharterYamlSectionError:
        ``section`` is not in :data:`OWNED_SECTIONS`.
    ValueError:
        ``section == "activation"`` and ``values`` contains a key outside
        :data:`_ACTIVATION_KEYS`.
    """
    if section not in OWNED_SECTIONS:
        raise UnknownCharterYamlSectionError(section)

    if section == "activation":
        unknown_keys = sorted(set(values) - set(_activation_keys()))
        if unknown_keys:
            raise ValueError(f"Unknown activation key(s): {unknown_keys}")

    yaml = _yaml_loader()
    with path.open("r", encoding="utf-8") as fh:
        document = yaml.load(fh)
    if document is None:
        document = CommentedMap()

    if section == "activation":
        for key, value in values.items():
            document[key] = value
    else:
        document[section] = values

    with path.open("w", encoding="utf-8") as fh:
        yaml.dump(document, fh)
