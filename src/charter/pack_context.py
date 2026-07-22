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

from charter.charter_yaml_io import load_charter_yaml

__all__ = ["CharterPackConfigError", "PackContext", "resolve_charter_yaml_pointer"]

#: The single ``config.yaml`` key naming the active charter (consolidate-
#: charter-bundle WP02, data-model.md "Entity: .kittify/config.yaml (after
#: relocation)"). Absent -> legacy/un-migrated project (activation stays in
#: ``config.yaml`` itself). Present -> the resolver follows it to
#: ``charter.yaml`` (INV-2).
_CHARTER_POINTER_KEY = "charter"


class CharterPackConfigError(KittyInternalConsistencyError):
    """Raised when ``.kittify/config.yaml`` has invalid charter pack shape."""

    def __init__(self, body: str) -> None:
        super().__init__("CHARTER_PACK_CONFIG_INVALID", body)


# ---------------------------------------------------------------------------
# Built-in constants
# ---------------------------------------------------------------------------

#: All built-in artifact kinds (plural form used by DoctrineService).
#: Mirrors ``charter.activations._ALLOWED_KINDS`` and
#: ``doctrine.drg.org_pack_loader._ORG_DRG_CANONICAL_KINDS``. ``templates``
#: and ``assets`` move in lockstep with those two mirrors — the drift guard in
#: ``tests/doctrine/test_org_pack_augmentation.py`` fails if any one of the
#: three is updated alone.
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
        "templates",
        "assets",
        "glossary_packs",
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

    activated_glossary_packs: frozenset[str] | None = None
    """Glossary pack IDs activated for this project (three-state)."""

    activated_anti_patterns: frozenset[str] | None = None
    """Anti-pattern node IDs activated for this project (three-state)."""

    # ------------------------------------------------------------------
    # Derived accessors
    # ------------------------------------------------------------------

    @property
    def org_roots(self) -> tuple[Path, ...]:
        """Org/project pack roots -- every :attr:`pack_roots` entry after the
        built-in root at index 0.

        Named accessor so new call sites (the activation gate, WP01 --
        mission ``drg-relation-parity-activation-gate-01KY48PD``) don't
        re-open-code the ``pack_roots[1:]`` slice already duplicated at
        ``charter/compiler.py:144`` and ``charter/consistency_check.py:940``.
        Those two existing sites are left as-is (out of scope for WP01).
        """
        return self.pack_roots[1:]

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

        # --- activation source (two-file read, INV-2) -------------------
        # Absent `charter:` pointer -> legacy/un-migrated project: activation
        # keys are read directly from the already-loaded config.yaml mapping
        # (unchanged pre-relocation behavior). Present pointer -> the
        # resolved charter.yaml supplies the flat activation keys instead;
        # `org_pack_names`/`pack_roots` below STILL read from `data`
        # (config.yaml), never from the activation source.
        activation = _load_charter_activation_source(repo_root, data)

        # --- activated_kinds -------------------------------------------
        activated_kinds = _read_activated_kinds(activation)

        # --- activated_mission_types -----------------------------------
        activated_mission_types = _read_activated_mission_types(activation)

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
            activated_directives=_read_activated_directives(activation),
            activated_tactics=_read_activated_tactics(activation),
            activated_styleguides=_read_activated_styleguides(activation),
            activated_toolguides=_read_activated_toolguides(activation),
            activated_paradigms=_read_activated_paradigms(activation),
            activated_procedures=_read_activated_procedures(activation),
            activated_agent_profiles=_read_activated_agent_profiles(activation),
            activated_mission_step_contracts=_read_activated_mission_step_contracts(activation),
            activated_glossary_packs=_read_activated_glossary_packs(activation),
            activated_anti_patterns=_read_activated_anti_patterns(activation),
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
    return CharterPackConfigError(
        f"{message}\nRemediation: fix .kittify/config.yaml (or the charter.yaml "
        f"it points to) or run `spec-kitty upgrade` to restore the default "
        f"charter pack shape."
    )


def resolve_charter_yaml_pointer(repo_root: Path, config_data: dict[str, Any]) -> Path | None:
    """Resolve the ``charter:`` pointer key from parsed ``config.yaml`` data.

    Returns ``None`` when the key is absent — the legacy/un-migrated state,
    where callers fall back to reading/writing activation directly in
    ``config.yaml`` (INV-2). Also returns ``None`` when the key is present but
    its value is NOT a string (e.g. a ``charter:`` mapping namespace holding
    the pre-#2773 inline ``synthesis_inputs`` block): a mapping/list/scalar
    value is the legacy inline shape, not a charter.yaml pointer, so it MUST
    NOT be stringified into a bogus filesystem path. This mirrors
    ``charter.evidence.orchestrator.load_url_list_from_config``, which likewise
    reads ``url_list`` out of a mapping-shaped ``charter:`` key and treats the
    path-string shape as "no inline mapping". Only a *string* value is a
    pointer. Returns the resolved (repo-root-relative or absolute) path when a
    string pointer is present, WITHOUT checking existence: callers apply their
    own fail-loud policy so the "missing file" error can name the calling
    operation (read vs write).

    Shared by :meth:`PackContext.from_config` (read) and
    ``charter.pack_manager`` (write) so pointer resolution has exactly one
    implementation (INV-5).
    """
    pointer = config_data.get(_CHARTER_POINTER_KEY)
    if not isinstance(pointer, str):
        # Absent (None) OR a non-string legacy inline mapping/namespace ->
        # no pointer to resolve; callers use the legacy config.yaml read.
        return None
    pointer_path = Path(pointer)
    return pointer_path if pointer_path.is_absolute() else repo_root / pointer_path


def _load_charter_activation_source(repo_root: Path, data: dict[str, Any]) -> dict[str, Any]:
    """Return the mapping ``_read_activated_*`` reads activation keys from.

    Two-state resolution keyed on the ``charter:`` pointer (INV-2/INV-5):

    * Pointer absent -> legacy/un-migrated project. Activation is read
      directly from ``config.yaml`` (the pre-relocation behavior, preserved
      byte-for-byte for projects that have not yet run the charter-bundle
      migration).
    * Pointer present -> the project has been migrated. The pointer MUST
      resolve to a readable ``charter.yaml``; a dangling/unreadable pointer
      is a fail-loud error (INV-5, re-homed #2530) — never a silent
      fallback to the legacy config-embedded keys.
    """
    charter_path = resolve_charter_yaml_pointer(repo_root, data)
    if charter_path is None:
        return data
    if not charter_path.exists():
        raise _config_error(
            f".kittify/config.yaml 'charter:' pointer names {charter_path}, "
            f"which does not exist."
        )
    try:
        loaded = load_charter_yaml(charter_path)
    except Exception as exc:
        raise _config_error(f"Invalid YAML in {charter_path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise _config_error(f"{charter_path} root must be a mapping.")
    return dict(loaded)


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
        raise _config_error(f"Activation key '{key}' must be a list, got {type(raw).__name__}.")
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

    Falls back to the built-in mission type IDs when the key is absent
    (new project / pre-migration state — FR-019 migration intent). An
    explicit empty list ``[]`` returns ``frozenset()`` (FR-039 fix).

    The default is derived lazily from the single canonical accessor
    (:func:`doctrine.missions.mission_type_repository.builtin_mission_type_id_set`,
    #2669 Roster B) rather than a hardcoded literal — importing this module
    must not read ``mission_types/`` off disk (NFR-001), so the import is
    function-local and only fires when the key is actually absent.
    """
    from doctrine.missions.mission_type_repository import (  # noqa: PLC0415 — lazy; import-time-I/O timing (NFR-001), not cycle avoidance
        builtin_mission_type_id_set,
    )

    activated = _read_list_key(data, "mission_type_activations")
    return builtin_mission_type_id_set() if activated is None else activated


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


def _read_activated_glossary_packs(data: dict[str, Any]) -> frozenset[str] | None:
    """Extract ``activated_glossary_packs`` from parsed config data (three-state)."""
    return _read_list_key(data, "activated_glossary_packs")


def _read_activated_anti_patterns(data: dict[str, Any]) -> frozenset[str] | None:
    """Extract ``activated_anti_patterns`` from parsed config data (three-state)."""
    return _read_list_key(data, "activated_anti_patterns")



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
        from doctrine.drg.org_pack_config import (  # noqa: PLC0415
            OrgPackEnvVarUnsetError,
            OrgPackSubdirEscapeError,
            load_pack_registry,
        )

        registry = load_pack_registry(repo_root)
        # Resolve effective roots inside the try so a resolution-time subdir
        # escape or unset-env-var failure (raised by ``effective_root``) is
        # re-raised below rather than swallowed by the broad ``except`` into
        # a silent empty registry.
        for pack in registry.packs:
            names.append(pack.name)
            roots.append(pack.effective_root(repo_root))
    except (OrgPackSubdirEscapeError, OrgPackEnvVarUnsetError):
        raise
    except Exception as exc:  # pragma: no cover – defensive
        warnings.warn(
            f"Failed to load org pack registry; org packs disabled: {exc}",
            stacklevel=4,
        )
        return (), ()

    return tuple(names), tuple(roots)
