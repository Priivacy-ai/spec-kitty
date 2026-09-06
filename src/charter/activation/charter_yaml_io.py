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
import copy
from dataclasses import dataclass
import hashlib
from io import StringIO
import os
from pathlib import Path
import stat
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.nodes import MappingNode

__all__ = [
    "OWNED_SECTIONS",
    "UnknownCharterYamlSectionError",
    "load_charter_yaml",
    "save_charter_yaml",
    "update_charter_yaml_section",
    "PreparedYamlWrite",
    "observe_yaml_input",
    "prepare_yaml_write",
    "apply_yaml_write",
    "render_yaml_document",
    "prepare_charter_yaml_section",
]


@dataclass(frozen=True)
class _YamlInput:
    path: Path
    identity: tuple[int, ...] | None
    content: bytes | None


def observe_yaml_input(path: Path) -> _YamlInput:
    """Observe a regular file or parent without following a destination link."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return _YamlInput(path, None, None)
    if stat.S_ISLNK(info.st_mode) or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        raise ValueError(f"Unsafe YAML input kind: {path}")
    identity: tuple[int, ...] = (info.st_dev, info.st_ino, info.st_mode)
    if stat.S_ISDIR(info.st_mode):
        return _YamlInput(path, identity, None)
    content = path.read_bytes()
    identity += (info.st_mtime_ns, info.st_ctime_ns, info.st_size, info.st_nlink)
    after = path.lstat()
    if (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns):
        raise ValueError(f"precondition_changed: {path}")
    return _YamlInput(path, identity, content)


@dataclass(frozen=True)
class PreparedYamlWrite:
    """Exact YAML bytes and the complete bounded input set for one writer."""

    target: Path
    before_bytes: bytes | None
    desired_bytes: bytes
    mode: int
    observations: tuple[_YamlInput, ...]
    absent_parents: tuple[Path, ...]
    section: str
    desired_sha256: str
    kind: str = "file"

    @property
    def changed(self) -> bool:
        return self.before_bytes != self.desired_bytes

    def recheck(self) -> None:
        """Refuse stale inputs, even when an intervening rewrite kept the bytes."""
        if _bytes_digest(self.desired_bytes) != self.desired_sha256:
            raise ValueError("precondition_changed: prepared bytes")
        for observation in self.observations:
            if observe_yaml_input(observation.path) != observation:
                raise ValueError(f"precondition_changed: {observation.path}")


def _bytes_digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()  # noqa: TID251 -- exact file bytes, not charter semantic hashing


def prepare_yaml_write(
    target: Path,
    desired: bytes,
    *,
    section: str,
    inputs: tuple[_YamlInput, ...] = (),
) -> PreparedYamlWrite:
    """Retain bytes and input identities without creating directories or files."""
    parents = tuple(reversed(target.parents))
    observations = list(inputs)
    seen = {item.path for item in observations}
    for path in (*parents, target):
        if path not in seen:
            observations.append(observe_yaml_input(path))
            seen.add(path)
    before = next(item for item in observations if item.path == target)
    if before.identity is not None and before.content is None:
        raise ValueError(f"YAML target must be a regular file: {target}")
    mode = stat.S_IMODE(before.identity[2]) if before.identity else 0o644
    prepared = PreparedYamlWrite(
        target,
        before.content,
        desired,
        mode,
        tuple(observations),
        tuple(item.path for item in observations if item.path in parents and item.identity is None),
        section,
        _bytes_digest(desired),
    )
    prepared.recheck()
    return prepared


def apply_yaml_write(prepared: PreparedYamlWrite) -> bool:
    """Recheck the whole input set, then use the existing direct-file boundary."""
    prepared.recheck()
    if not prepared.changed:
        return False
    for parent in prepared.absent_parents:
        parent.mkdir(mode=0o755)
        parent.chmod(0o755)
    flags = os.O_WRONLY | (os.O_EXCL | os.O_CREAT if prepared.before_bytes is None else os.O_TRUNC)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(prepared.target, flags, prepared.mode)
    with os.fdopen(descriptor, "wb") as stream:
        if prepared.before_bytes is None:
            os.fchmod(stream.fileno(), prepared.mode)
        stream.write(prepared.desired_bytes)
    return True


def _dump_document(document: Any, yaml: YAML) -> str:
    stream = StringIO()
    yaml.dump(document, stream)
    return stream.getvalue()


def render_yaml_document(before: bytes | None, document: Any, yaml: YAML) -> bytes:
    """Render changed top-level entries, retaining every untouched source span."""
    if before is None:
        return _dump_document(document, yaml).encode("utf-8")
    text = before.decode("utf-8")
    original = _yaml_loader().load(text)
    if original == document or (original is None and document == {}):
        return before
    if original is None:
        return (text + ("\n" if text and not text.endswith("\n") else "") + _dump_document(document, yaml)).encode("utf-8")
    node = _yaml_loader().compose(text)
    if not isinstance(original, dict) or not isinstance(document, dict) or not isinstance(node, MappingNode):
        raise ValueError("YAML root must be a mapping")
    edits: list[tuple[int, int, str]] = []
    for key_node, value_node in node.value:
        key = key_node.value
        if key in document and original[key] == document[key]:
            continue
        start, end = key_node.start_mark.index, value_node.end_mark.index
        # Collection end marks include following blank/comment lines. They are
        # authored separators, not part of the replaced section.
        span = text[start:end]
        lines = span.splitlines(keepends=True)
        while lines and (not lines[-1].strip() or lines[-1].lstrip().startswith("#")):
            end -= len(lines.pop())
        replacement = _render_entry(key, document, yaml, flow=bool(node.flow_style))
        if end and text[end - 1] not in "\r\n":
            replacement = replacement.rstrip("\r\n")
        edits.append((start, end, replacement))
    additions = CommentedMap({key: value for key, value in document.items() if key not in original})
    if additions:
        if node.flow_style:
            end = node.end_mark.index - 1
            separator = ", " if original and not text[:end].rstrip().endswith(",") else ""
            addition = separator + _dump_flow_entries(additions)
        else:
            end = node.end_mark.index
            addition = ("" if end == 0 or text[end - 1] in "\r\n" else "\n") + _dump_document(additions, yaml)
        edits.append((end, end, addition))
    for start, end, replacement in sorted(edits, reverse=True):
        text = text[:start] + replacement + text[end:]
    if _yaml_loader().load(text) != document:
        raise ValueError("Cannot preserve YAML aliases or section boundaries")
    return text.encode("utf-8")


def _dump_flow_entries(document: Any) -> str:
    yaml = _yaml_loader()
    yaml.default_flow_style = True
    return _dump_document(document, yaml).strip()[1:-1]


def _render_entry(key: str, document: Any, yaml: YAML, *, flow: bool) -> str:
    if key not in document:
        if flow:
            raise ValueError("Cannot preserve deletion from flow-style YAML root")
        return ""
    entry = CommentedMap({key: document[key]})
    return _dump_flow_entries(entry) if flow else _dump_document(entry, yaml)


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

    Mirrors the codebase's established lazy-module-attribute idiom so
    ``from charter.activation.charter_yaml_io
    import _ACTIVATION_KEYS`` and ``charter_yaml_io._ACTIVATION_KEYS`` both
    keep working for existing callers/tests without a module-level import
    that would reintroduce the cycle :func:`_activation_keys` avoids.
    """
    if name == "_ACTIVATION_KEYS":
        return _activation_keys()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


#: Sections whose owned content is a single top-level scalar/mapping key —
#: mutating one of these REPLACES that key's entire value.
_SCALAR_SECTIONS: frozenset[str] = frozenset({"governance", "directives", "catalog", "metadata", "overrides"})

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
    """Prepare and apply a round-trip document without unchanged-file churn."""
    before = observe_yaml_input(path)
    desired = render_yaml_document(before.content, document, _yaml_loader())
    apply_yaml_write(prepare_yaml_write(path, desired, section="document", inputs=(before,)))


def _validate_section(section: str, values: dict[str, Any]) -> None:
    """Validate ownership before loading or mutating the document."""
    if section not in OWNED_SECTIONS:
        raise UnknownCharterYamlSectionError(section)
    if section == "activation":
        unknown_keys = sorted(set(values) - set(_activation_keys()))
        if unknown_keys:
            raise ValueError(f"Unknown activation key(s): {unknown_keys}")


def prepare_charter_yaml_section(
    path: Path,
    section: str,
    values: dict[str, Any],
) -> PreparedYamlWrite:
    """Validate and prepare one owned section without any filesystem mutation."""
    _validate_section(section, values)
    before = observe_yaml_input(path)
    if before.content is None:
        raise FileNotFoundError(path)
    document = _yaml_loader().load(before.content)
    if document is None:
        document = CommentedMap()
    if not isinstance(document, dict):
        raise ValueError("YAML root must be a mapping")
    changes = values if section == "activation" else {section: values}
    for key, value in changes.items():
        if key not in document or document[key] != value:
            document[key] = copy.deepcopy(value)
    desired = render_yaml_document(before.content, document, _yaml_loader())
    return prepare_yaml_write(path, desired, section=section, inputs=(before,))


def update_charter_yaml_section(path: Path, section: str, values: dict[str, Any]) -> None:
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
    apply_yaml_write(prepare_charter_yaml_section(path, section, values))
