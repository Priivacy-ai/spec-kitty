"""Pre-validated pack set snapshot passed to doctrine resolvers (C-005).

This module defines ``PackContext`` — a frozen dataclass constructed
exclusively by the charter module.  The doctrine resolver receives a
``PackContext`` instance instead of reading ``.kittify/config.yaml``
directly, which enforces the architectural constraint that no
doctrine-layer code ever reads project configuration (C-005).

Invariant: ``PackContext`` is always constructed here via
``PackContext.from_config()``.  Callers in ``src/charter/`` that
previously read ``config.yaml`` for pack or activation state must
delegate to this constructor.

Layer rule
----------
``src/charter/`` MUST NOT import from ``specify_cli`` (C-001, hard
ratchet pinned by ``tests/architectural/test_layer_rules.py``).  This
module uses only stdlib + ``doctrine.drg.org_pack_config`` (which is
within the allowed layer boundary for charter→doctrine reads).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kernel.errors import KittyInternalConsistencyError
from ruamel.yaml import YAML

__all__ = ["CharterPackConfigError", "PackContext"]


class CharterPackConfigError(KittyInternalConsistencyError):
    """Raised when ``.kittify/config.yaml`` has invalid charter pack shape."""

    def __init__(self, body: str) -> None:
        super().__init__("CHARTER_PACK_CONFIG_INVALID", body)


# ---------------------------------------------------------------------------
# Built-in constants
# ---------------------------------------------------------------------------

#: IDs of the four built-in mission types shipped with spec-kitty.
#: Used as the default for ``activated_mission_types`` when config.yaml
#: has no ``mission_type_activations`` key (backward-compat / new project).
_BUILTIN_MISSION_TYPE_IDS: frozenset[str] = frozenset({"software-dev", "documentation", "research", "plan"})

#: All eight built-in artifact kinds (plural form used by DoctrineService).
#: Mirrors ``charter.activations._ALLOWED_KINDS`` and
#: ``doctrine.drg.org_pack_loader._ORG_DRG_CANONICAL_KINDS``.
#: Used as the default for ``activated_kinds`` when config.yaml has no
#: ``activated_kinds`` key (backward-compat default — all kinds are active).
_BUILTIN_ARTIFACT_KINDS: frozenset[str] = frozenset(
    {
        "directives",
        "tactics",
        "styleguides",
        "toolguides",
        "paradigms",
        "procedures",
        "agent_profiles",
        "mission_step_contracts",
    }
)

# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PackContext:
    """Pre-validated pack set constructed by the charter module.

    The doctrine resolver receives this; it never reads
    ``.kittify/config.yaml`` directly.  Invariant: constructed by the
    charter module only (C-005).

    All fields are immutable types (``frozenset``, ``tuple``) so the
    instance is safe to hash and use as a dict key.
    """

    activated_kinds: frozenset[str]
    """Artifact kinds explicitly activated in the project charter.

    Plural form (e.g. ``"directives"``, ``"agent_profiles"``).
    Defaults to all eight built-in kinds when the ``activated_kinds``
    key is absent from ``.kittify/config.yaml``.
    """

    activated_mission_types: frozenset[str]
    """Mission type IDs activated in the project charter.

    Defaults to the four built-in mission type IDs
    (``software-dev``, ``documentation``, ``research``, ``plan``)
    when the ``mission_type_activations`` key is absent or empty in
    ``.kittify/config.yaml``.
    """

    pack_roots: tuple[Path, ...]
    """Ordered pack root paths: built-in first, then org packs in
    config declaration order.
    """

    org_pack_names: tuple[str, ...]
    """Org pack names as declared in ``config.yaml``."""

    repo_root: Path
    """Repository root path (for resolving project-layer overrides)."""

    # ------------------------------------------------------------------
    # Per-kind activation fields (three-state: None / frozenset() / {ids})
    # ------------------------------------------------------------------

    activated_directives: frozenset[str] | None = None
    """Directive IDs activated for this project.

    ``None`` → key absent from config (all built-ins available).
    ``frozenset()`` → key present but empty (nothing activated).
    Non-empty frozenset → explicit set of activated IDs.
    """

    activated_tactics: frozenset[str] | None = None
    """Tactic IDs activated for this project (three-state)."""

    activated_styleguides: frozenset[str] | None = None
    """Styleguide IDs activated for this project (three-state)."""

    activated_toolguides: frozenset[str] | None = None
    """Toolguide IDs activated for this project (three-state)."""

    activated_paradigms: frozenset[str] | None = None
    """Paradigm IDs activated for this project (three-state)."""

    activated_procedures: frozenset[str] | None = None
    """Procedure IDs activated for this project (three-state)."""

    activated_agent_profiles: frozenset[str] | None = None
    """Agent profile IDs activated for this project (three-state)."""

    activated_mission_step_contracts: frozenset[str] | None = None
    """Mission step contract IDs activated for this project (three-state)."""

    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------

    @classmethod
    def from_config(cls, repo_root: Path) -> PackContext:
        """Construct a ``PackContext`` from ``.kittify/config.yaml``.

        Reads the project charter activation state and pack roots.
        When config.yaml is absent or a key is missing, backward-
        compatible defaults are applied (all built-in kinds active;
        all four built-in mission types active; no org packs).

        Parameters
        ----------
        repo_root:
            Repository root containing ``.kittify/config.yaml``.

        Returns
        -------
        PackContext
            Frozen, immutable snapshot ready for the doctrine resolver.
        """
        data = _load_config(repo_root)

        # --- activated_kinds -------------------------------------------
        activated_kinds = _read_activated_kinds(data)

        # --- activated_mission_types -----------------------------------
        activated_mission_types = _read_activated_mission_types(data)

        # --- org packs -------------------------------------------------
        org_pack_names, org_pack_roots = _read_org_packs(repo_root, data)

        # --- pack_roots ------------------------------------------------
        builtin_root = Path(__file__).parent.parent / "doctrine"
        pack_roots: tuple[Path, ...] = (builtin_root, *org_pack_roots)

        return cls(
            activated_kinds=activated_kinds,
            activated_mission_types=activated_mission_types,
            pack_roots=pack_roots,
            org_pack_names=org_pack_names,
            repo_root=repo_root,
            activated_directives=_read_activated_directives(data),
            activated_tactics=_read_activated_tactics(data),
            activated_styleguides=_read_activated_styleguides(data),
            activated_toolguides=_read_activated_toolguides(data),
            activated_paradigms=_read_activated_paradigms(data),
            activated_procedures=_read_activated_procedures(data),
            activated_agent_profiles=_read_activated_agent_profiles(data),
            activated_mission_step_contracts=_read_activated_mission_step_contracts(data),
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _yaml_loader() -> YAML:
    """Return a YAML parser instance (round-trip mode, preserve quotes)."""
    yaml = YAML()
    yaml.preserve_quotes = True
    return yaml


def _config_error(message: str) -> CharterPackConfigError:
    return CharterPackConfigError(f"{message}\nRemediation: fix .kittify/config.yaml or run `spec-kitty upgrade` to restore the default charter pack shape.")


def _load_config(repo_root: Path) -> dict[str, Any]:
    """Read and parse ``.kittify/config.yaml``.

    Returns an empty dict when the file is absent. Invalid YAML or a non-mapping
    root is a hard error: activation filters must not fail open.
    """
    config_path = repo_root / ".kittify" / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        yaml = _yaml_loader()
        raw: Any = yaml.load(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise _config_error(f"Invalid YAML in .kittify/config.yaml: {exc}") from exc
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise _config_error(".kittify/config.yaml root must be a mapping.")
    return dict(raw)


def _read_list_key(data: dict[str, Any], key: str) -> frozenset[str] | None:
    raw = data.get(key)
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise _config_error(f".kittify/config.yaml key '{key}' must be a list, got {type(raw).__name__}.")
    return frozenset(str(item) for item in raw)


def _read_activated_kinds(data: dict[str, Any]) -> frozenset[str]:
    """Extract ``activated_kinds`` from parsed config data.

    Falls back to all eight built-in kinds when the key is absent.
    An explicit empty list ``[]`` returns ``frozenset()`` (FR-039 fix).
    """
    activated = _read_list_key(data, "activated_kinds")
    return _BUILTIN_ARTIFACT_KINDS if activated is None else activated


def _read_activated_mission_types(data: dict[str, Any]) -> frozenset[str]:
    """Extract ``mission_type_activations`` from parsed config data.

    Falls back to the four built-in mission type IDs when the key is
    absent (new project / pre-migration state — FR-019 migration intent).
    An explicit empty list ``[]`` returns ``frozenset()`` (FR-039 fix).
    """
    activated = _read_list_key(data, "mission_type_activations")
    return _BUILTIN_MISSION_TYPE_IDS if activated is None else activated


def _read_activated_directives(data: dict[str, Any]) -> frozenset[str] | None:
    """Extract ``activated_directives`` from parsed config data (three-state).

    ``None`` → key absent (all built-ins available).
    ``frozenset()`` → key present with empty list (nothing activated).
    Non-empty frozenset → explicit set of activated IDs.
    """
    return _read_list_key(data, "activated_directives")


def _read_activated_tactics(data: dict[str, Any]) -> frozenset[str] | None:
    """Extract ``activated_tactics`` from parsed config data (three-state)."""
    return _read_list_key(data, "activated_tactics")


def _read_activated_styleguides(data: dict[str, Any]) -> frozenset[str] | None:
    """Extract ``activated_styleguides`` from parsed config data (three-state)."""
    return _read_list_key(data, "activated_styleguides")


def _read_activated_toolguides(data: dict[str, Any]) -> frozenset[str] | None:
    """Extract ``activated_toolguides`` from parsed config data (three-state)."""
    return _read_list_key(data, "activated_toolguides")


def _read_activated_paradigms(data: dict[str, Any]) -> frozenset[str] | None:
    """Extract ``activated_paradigms`` from parsed config data (three-state)."""
    return _read_list_key(data, "activated_paradigms")


def _read_activated_procedures(data: dict[str, Any]) -> frozenset[str] | None:
    """Extract ``activated_procedures`` from parsed config data (three-state)."""
    return _read_list_key(data, "activated_procedures")


def _read_activated_agent_profiles(data: dict[str, Any]) -> frozenset[str] | None:
    """Extract ``activated_agent_profiles`` from parsed config data (three-state)."""
    return _read_list_key(data, "activated_agent_profiles")


def _read_activated_mission_step_contracts(
    data: dict[str, Any],
) -> frozenset[str] | None:
    """Extract ``activated_mission_step_contracts`` from parsed config data (three-state)."""
    return _read_list_key(data, "activated_mission_step_contracts")


def _read_org_packs(repo_root: Path, _data: dict[str, Any]) -> tuple[tuple[str, ...], tuple[Path, ...]]:
    """Resolve org pack names and root paths from config data.

    Delegates to ``doctrine.drg.org_pack_config.load_pack_registry``
    so that legacy ``organisation_packs`` form and deprecation warnings
    are handled consistently with the rest of the codebase.

    Returns
    -------
    (names, roots)
        ``names`` — org pack names in declaration order.
        ``roots`` — resolved absolute pack root paths in the same order.
    """
    names: list[str] = []
    roots: list[Path] = []
    try:
        from doctrine.drg.org_pack_config import OrgPackSubdirEscapeError, load_pack_registry  # noqa: PLC0415

        registry = load_pack_registry(repo_root)
        # Resolve effective roots inside the try so a resolution-time subdir
        # escape (raised by ``effective_root``) is re-raised below rather than
        # swallowed by the broad ``except`` into a silent empty registry.
        for pack in registry.packs:
            names.append(pack.name)
            roots.append(pack.effective_root(repo_root))
    except OrgPackSubdirEscapeError:
        raise
    except Exception as exc:  # pragma: no cover – defensive
        warnings.warn(
            f"Failed to load org pack registry; org packs disabled: {exc}",
            stacklevel=4,
        )
        return (), ()

    return tuple(names), tuple(roots)
