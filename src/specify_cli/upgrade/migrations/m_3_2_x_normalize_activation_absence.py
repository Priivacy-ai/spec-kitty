"""Migration ``normalize_activation_absence``: absent ``activated_<kind>`` -> explicit ``[]``.

Contract: ``kitty-specs/doctrine-delivery-reachability-01KYMXD6/contracts/
activation-delivery.md`` §1 (V-3), spec FR-018. This is WP07/T037.

FR-018 retires the three-state absence contract at the delivery boundary: an
*omitted* per-artifact ``activated_<kind>`` key used to mean "all built-ins
available", which is a fail-open — once delivery works, a project that never
activated procedures would silently receive all of them. This migration writes
an explicit empty list for every per-artifact activation key that is absent from
the project's *resolved* activation store, so absence becomes ``[]`` (nothing
activated) rather than "everything". It also ensures the ``.kittify/config.yaml``
``charter:`` pointer is present when a ``charter.yaml`` store exists.

Scope (NFR-001 — bounded consumer mutation): the ONLY consumer file this
migration writes is the charter/config activation surface, and only to normalize
absence. It never touches ``activated_kinds`` or ``mission_type_activations``
(coarser gates with their own still-valid built-in-default semantics), never
removes an explicit ``[]`` or a populated list, and installs nothing.

Reconciliation of the two prior migrations (WP07/T041)
------------------------------------------------------
Two migrations already fought over this surface, in opposite directions, and the
config-embedded ``activated_*`` mirror survived both:

1. ``m_unify_charter_activation.py`` (``target_version = "3.2.6"``) made
   ``config.activated_<kind>`` the single activation authority — it *wrote*
   activation INTO ``config.yaml``.
2. ``m_unify_charter_activation_finalize.py``
   (``consolidate_charter_bundle_fold``, ``target_version = "3.2.6"``) reversed
   that: it folded activation into a git-tracked ``charter.yaml`` and minted the
   ``config.yaml`` ``charter:`` pointer, then stripped the ``activated_*`` keys
   from ``config.yaml``.

Why the finalize pass did not take (the mirror is still present on checkouts):

* **Deliberate absence preservation.** The finalize migration copies activation
  VERBATIM and *explicitly refuses to invent* ``[]`` for an absent key
  (``_compose_charter_yaml_document``: "an absent key stays absent ... never
  invented as ``[]``, which would flip 'all built-ins active' to 'none active',
  MG1 / SC-008"). Under the THEN-current three-state contract that was correct.
  FR-018 REVERSES that contract, so absence was never normalized — this
  migration is the reversal.
* **Same-version gating.** ``MigrationRegistry.get_applicable`` includes a
  migration only when ``from_version < target_version <= to_version``, or when
  ``target_version == from_version`` *and* ``detect()`` is true on an explicit
  upgrade run. A project already stamped at the finalize migration's own
  ``3.2.6`` target (e.g. via the seed migration that shares that version, or via
  hand-authored dogfood config) reaches ``3.2.6`` with no ``from < to`` window,
  so the mirror-removal (``_rewrite_config``) only fires if an upgrade is
  explicitly invoked at that exact version. That timing gap left a
  hand-/seed-maintained ``config.yaml`` ``activated_*`` mirror co-existing with
  ``charter.yaml``'s copy.

FR-017 is therefore the third pass: rather than rely on a version-gated fold that
can silently no-op on a same-version project, it repoints the in-code reader onto
the resolved authority (T035) and removes the mirror directly (T036); this
migration (T037/FR-018) then normalizes absence in the resolved store.

**Ordering constraint** (declared, mirroring the finalize migration's own
docstring): this migration is safe to run in any order relative to the finalize
fold because it operates on the *resolved* store — ``charter.yaml`` when the
``charter:`` pointer is present, else the legacy ``config.yaml``. It is idempotent
(MG2): once every per-artifact key is explicit, ``detect()``/``apply()`` report a
clean no-op.

Body pattern mirrors ``m_unify_charter_activation_finalize.py``. Registered via
``@MigrationRegistry.register``; ``runs_on_worktrees = False`` (a
project-identity/config-level normalization, not a worktree concern).
``charter.*`` imports are lazy inside the methods so registry discovery stays
import-cheap (C-002).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

MIGRATION_ID = "normalize_activation_absence"
TARGET_VERSION = "3.2.6"

_KITTIFY_DIRNAME = ".kittify"
_CONFIG_FILENAME = "config.yaml"
_CHARTER_POINTER_KEY = "charter"

#: The per-artifact activation keys FR-018 normalizes. ``activated_kinds`` and
#: ``mission_type_activations`` are intentionally EXCLUDED: they are coarser
#: gates with their own still-valid built-in-default absence semantics.
#: Duplicated (not imported from ``charter``) so registry discovery stays
#: import-cheap (C-002).
_PER_ARTIFACT_ACTIVATION_KEYS: tuple[str, ...] = (
    "activated_directives",
    "activated_tactics",
    "activated_styleguides",
    "activated_toolguides",
    "activated_paradigms",
    "activated_procedures",
    "activated_agent_profiles",
    "activated_mission_step_contracts",
    "activated_glossary_packs",
)


# ---------------------------------------------------------------------------
# Path + YAML helpers
# ---------------------------------------------------------------------------


def _config_path(project_path: Path) -> Path:
    return project_path / _KITTIFY_DIRNAME / _CONFIG_FILENAME


def _yaml_roundtrip_loader() -> YAML:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    return yaml


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Safe-load a YAML mapping. Returns ``{}`` for absent/empty/non-mapping."""
    if not path.exists():
        return {}
    data = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _load_config_roundtrip(config_path: Path) -> tuple[dict[str, Any], YAML]:
    yaml = _yaml_roundtrip_loader()
    if not config_path.exists():
        return {}, yaml
    with config_path.open("r", encoding="utf-8") as fh:
        data = yaml.load(fh)
    return (data if isinstance(data, dict) else {}), yaml


def _resolved_charter_yaml(project_path: Path, config_data: dict[str, Any]) -> Path | None:
    """Resolve the ``charter:`` pointer to an existing ``charter.yaml``, else ``None``.

    Delegates to the single pointer resolver (INV-5) so pointer semantics have
    exactly one implementation. Returns ``None`` when the pointer is absent, is a
    non-string legacy inline mapping, or names a file that does not exist — in
    every such case the legacy ``config.yaml`` is the activation store.
    """
    from charter.pack_context import resolve_charter_yaml_pointer  # noqa: PLC0415 -- lazy (C-002)

    charter_path: Path | None = resolve_charter_yaml_pointer(project_path, config_data)
    if charter_path is None or not charter_path.exists():
        return None
    return charter_path


def _store_activation_mapping(project_path: Path, config_data: dict[str, Any]) -> dict[str, Any]:
    """Return the activation mapping of the *resolved* store (charter.yaml or config)."""
    charter_path = _resolved_charter_yaml(project_path, config_data)
    if charter_path is not None:
        return _load_yaml_mapping(charter_path)
    return config_data


def _missing_per_artifact_keys(activation: dict[str, Any]) -> list[str]:
    """Per-artifact activation keys absent from *activation* (FR-018 targets)."""
    return [key for key in _PER_ARTIFACT_ACTIVATION_KEYS if key not in activation]


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------


def _normalize_charter_yaml(charter_path: Path, missing: list[str]) -> None:
    """Write explicit ``[]`` for each *missing* per-artifact key into charter.yaml.

    Routed through the shared INV-9 write helper so governance / directives /
    catalog / metadata and already-present activation keys survive byte-for-byte.
    """
    from charter.charter_yaml_io import update_charter_yaml_section  # noqa: PLC0415 -- lazy (C-002)

    update_charter_yaml_section(charter_path, "activation", {key: [] for key in missing})


def _normalize_config_yaml(config_path: Path, missing: list[str]) -> None:
    """Write explicit ``[]`` for each *missing* per-artifact key into config.yaml.

    Comment-preserving round-trip write: only the absent activation keys are
    added; every other key and its comments survive untouched.
    """
    config_data, yaml_inst = _load_config_roundtrip(config_path)
    for key in missing:
        config_data[key] = []
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as fh:
        yaml_inst.dump(config_data, fh)


def _ensure_pointer(config_path: Path, project_path: Path, charter_path: Path) -> bool:
    """Mint the ``charter:`` pointer when a charter.yaml store exists but it is absent.

    Returns True when a change was written.
    """
    config_data, yaml_inst = _load_config_roundtrip(config_path)
    if _CHARTER_POINTER_KEY in config_data:
        return False
    try:
        pointer = charter_path.resolve(strict=False).relative_to(project_path.resolve(strict=False)).as_posix()
    except ValueError:
        pointer = str(charter_path)
    config_data[_CHARTER_POINTER_KEY] = pointer
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as fh:
        yaml_inst.dump(config_data, fh)
    return True


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------


@MigrationRegistry.register
class NormalizeActivationAbsenceMigration(BaseMigration):
    """Normalize absent per-artifact activation keys to explicit ``[]`` (FR-018)."""

    migration_id = MIGRATION_ID
    description = (
        "Write an explicit empty list for every per-artifact activated_<kind> "
        "key absent from the resolved activation store (charter.yaml when the "
        "charter: pointer is present, else config.yaml), so absence means "
        "'nothing activated' rather than 'all built-ins' (FR-018); ensure the "
        "config.yaml 'charter:' pointer is present."
    )
    target_version = TARGET_VERSION
    runs_on_worktrees = False

    def detect(self, project_path: Path) -> bool:
        """True when the resolved store omits any per-artifact activation key,
        or a charter.yaml store exists without a config ``charter:`` pointer."""
        config_data = _load_yaml_mapping(_config_path(project_path))
        activation = _store_activation_mapping(project_path, config_data)
        if _missing_per_artifact_keys(activation):
            return True
        charter_path = _resolved_charter_yaml(project_path, config_data)
        return charter_path is not None and _CHARTER_POINTER_KEY not in config_data

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        if self.detect(project_path):
            return True, ""
        return (
            False,
            "every per-artifact activated_<kind> key is already explicit and "
            "the charter: pointer is present; nothing to normalize",
        )

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        config_path = _config_path(project_path)
        config_data = _load_yaml_mapping(config_path)
        charter_path = _resolved_charter_yaml(project_path, config_data)
        activation = _store_activation_mapping(project_path, config_data)
        missing = _missing_per_artifact_keys(activation)
        pointer_missing = charter_path is not None and _CHARTER_POINTER_KEY not in config_data

        if not missing and not pointer_missing:
            return MigrationResult(success=True, changes_made=[])

        store_name = str(charter_path) if charter_path is not None else str(config_path)
        if dry_run:
            summary: list[str] = []
            if missing:
                summary.append(f"dry-run: would set {sorted(missing)} to [] in {store_name}")
            if pointer_missing:
                summary.append("dry-run: would add config.yaml 'charter:' pointer")
            return MigrationResult(success=True, changes_made=summary)

        changes: list[str] = []
        if missing:
            if charter_path is not None:
                _normalize_charter_yaml(charter_path, missing)
            else:
                _normalize_config_yaml(config_path, missing)
            changes.append(f"Normalized absent activation keys to [] in {store_name}: {sorted(missing)}")
        if pointer_missing and charter_path is not None and _ensure_pointer(config_path, project_path, charter_path):
            changes.append("Added .kittify/config.yaml 'charter:' pointer")

        return MigrationResult(success=True, changes_made=changes)
