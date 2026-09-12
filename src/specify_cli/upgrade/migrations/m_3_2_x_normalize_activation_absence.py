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
(coarser gates whose absence semantics are owned elsewhere — note that
``mission_type_activations`` no longer carries a built-in default: mission
resolution-activation-foundation-01KZ9FKG WP04 retired that implicit default and
made an absent key fail closed, so this migration deliberately leaves that key
to the create/use boundary rather than normalizing it here), never removes an
explicit ``[]`` or a populated list, and installs nothing.

Reconciliation of the two prior migrations (WP07/T041)
------------------------------------------------------
Two migrations already fought over this surface, in opposite directions, and the
config-embedded ``activated_*`` mirror survived both:

1. ``m_unify_charter_activation.py`` (``target_version = "3.2.6rc1"``) made
   ``config.activated_<kind>`` the single activation authority — it *wrote*
   activation INTO ``config.yaml``.
2. ``m_unify_charter_activation_finalize.py``
   (``consolidate_charter_bundle_fold``, ``target_version = "3.2.6rc1"``) reversed
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
  ``3.2.6rc1`` target (e.g. via the seed migration that shares that version, or via
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

Two-invocation churn guard (NFR-006, landing-fold fix for #3070)
------------------------------------------------------------------
``MigrationRegistry.get_applicable`` builds a SAME-VERSION (``target ==
from_version``) migration's inclusion in the applicable list from
``detect()`` evaluated ONCE, against the project's state *before any
migration in this same upgrade invocation has run*. That means a
same-version migration whose applicability only becomes true as a
*consequence* of an earlier same-version migration's write is not picked up
until the *next* ``spec-kitty upgrade`` call.

On a project whose ``config.yaml`` carries **zero** activation keys and no
``charter.yaml`` yet (the common freshly-``init``-ed shape, before a charter
interview ever runs), this migration is that earlier write: writing all nine
explicit ``[]`` per-artifact keys directly into ``config.yaml`` makes
``m_unify_charter_activation_finalize.ConsolidateCharterBundleMigration``'s
own ``_config_has_activation`` trigger true — but one invocation too late,
so a fold that should have happened alongside this normalization instead
lands on the *second* ``upgrade --yes`` call, breaking "a second consecutive
upgrade changes zero bytes" (NFR-006).

``_should_defer_bare_config_write`` closes this gap: when config.yaml is the
resolved store (no ``charter.yaml`` yet) and nothing else already visible
this pass would trigger the fold anyway (no legacy bundle, no existing
config-embedded activation, no pending answers-only promotion), writing the
normalized ``[]`` values here would be the SOLE, premature trigger — so the
write is deferred entirely rather than split across two invocations. Nothing
is lost by deferring: FR-017 already repoints the runtime activation reader
onto "absence means nothing activated," so an un-materialized absent key
reads identically to an explicit ``[]``; the values get materialized once
there is real activation data (or a legacy bundle / ``charter generate``)
for the fold to relocate. When something else already arms the fold this
pass, the write proceeds immediately so the fold's live per-item ``detect()``
picks it up in the SAME invocation (single-pass convergence, matching how a
genuinely-old project's rc35 seed migrations already converge in one pass).
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult

MIGRATION_ID = "normalize_activation_absence"
TARGET_VERSION = "3.2.6rc1"

_KITTIFY_DIRNAME = ".kittify"
_CONFIG_FILENAME = "config.yaml"
_CHARTER_POINTER_KEY = "charter"

#: The coarser activation gates (own built-in-default absence semantics,
#: never normalized by this migration -- see :func:`_per_artifact_activation_keys`
#: below) plus the four legacy bundle filenames. Duplicated (not imported)
#: from ``m_unify_charter_activation_finalize`` for the same C-002 reason
#: that module states for its own ``ACTIVATION_KEYS``/``LEGACY_BUNDLE_FILENAMES``
#: duplication: importing the sibling migration module at collection time
#: would pull its (non-lazy) ``charter.*`` imports into registry discovery.
#: Used only by the bare-config-write defer guard below and to derive
#: :func:`_per_artifact_activation_keys`.
_COARSE_ACTIVATION_KEYS: tuple[str, ...] = ("activated_kinds", "mission_type_activations")


@functools.lru_cache(maxsize=1)
def _per_artifact_activation_keys() -> tuple[str, ...]:
    """Return the per-artifact activation keys FR-018 normalizes, derived from
    the authority.

    ``activated_kinds`` and ``mission_type_activations`` (:data:`_COARSE_ACTIVATION_KEYS`)
    are excluded: they are coarser gates with their own still-valid
    built-in-default absence semantics.

    Lazy, function-scoped import of :data:`charter.activation.pack_manager.ACTIVATION_YAML_KEYS`
    -- mirrors the established idiom in :func:`charter.activation.charter_yaml_io._activation_keys`
    and :func:`charter.activation.compiler._legacy_activation_keys` -- so registry discovery
    stays import-cheap (C-002): a module-level import would pull ``charter.*``
    machinery into every migration-registry scan. A hand-listed tuple here
    previously risked the same drift FR-010/SC-005 fixed for the other two
    copies; deriving it keeps all three in lockstep with the authority.
    """
    from charter.activation.pack_manager import (  # noqa: PLC0415 -- avoids import cycle / keeps registry discovery cheap
        ACTIVATION_YAML_KEYS,
    )

    return tuple(key for key in ACTIVATION_YAML_KEYS if key not in _COARSE_ACTIVATION_KEYS)
_LEGACY_BUNDLE_FILENAMES: tuple[str, ...] = (
    "governance.yaml",
    "directives.yaml",
    "metadata.yaml",
    "references.yaml",
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
    from charter.activation.pack_context import resolve_charter_yaml_pointer  # noqa: PLC0415 -- lazy (C-002)

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
    return [key for key in _per_artifact_activation_keys() if key not in activation]


# ---------------------------------------------------------------------------
# Two-invocation churn guard (see module docstring)
# ---------------------------------------------------------------------------


def _legacy_bundle_present(project_path: Path) -> bool:
    """True when any of the four legacy charter bundle files still exist.

    Mirrors ``m_unify_charter_activation_finalize.legacy_bundle_present``.
    """
    charter_dir = project_path / _KITTIFY_DIRNAME / "charter"
    return any((charter_dir / name).exists() for name in _LEGACY_BUNDLE_FILENAMES)


def _config_carries_any_activation(config_data: dict[str, Any]) -> bool:
    """True when config.yaml already carries ANY activation key (coarse or per-artifact).

    Mirrors ``m_unify_charter_activation_finalize._config_has_activation`` --
    the fold migration's own trigger predicate -- so this migration can tell
    whether the fold is ALREADY armed this pass by a pre-existing signal,
    before deciding whether writing fresh ``[]`` values into a bare
    config.yaml would be the sole, premature trigger for a LATER invocation.
    """
    return any(
        key in config_data
        for key in (*_COARSE_ACTIVATION_KEYS, *_per_artifact_activation_keys())
    )


def _unify_promotion_pending(project_path: Path) -> bool:
    """True when the answers-only promotion migration still has real work to do.

    Lazy import (C-002): pulls in ``charter.*`` machinery this module
    otherwise avoids at collection time. Cheap on the common path -- the
    promotion migration's own ``detect()`` short-circuits when
    ``answers.yaml`` is absent, which is true for a bare/freshly-``init``-ed
    project.
    """
    from .m_unify_charter_activation import UnifyCharterActivationMigration  # noqa: PLC0415

    return UnifyCharterActivationMigration().detect(project_path)


def _should_defer_bare_config_write(
    project_path: Path, config_data: dict[str, Any], charter_path: Path | None
) -> bool:
    """True when normalizing into config.yaml now would arm the fold too late.

    Only relevant when config.yaml itself is the resolved activation store
    (``charter_path is None``); once ``charter.yaml`` exists this migration
    always writes there directly and this guard never applies. See the
    module docstring's "Two-invocation churn guard" section for the full
    rationale.
    """
    if charter_path is not None:
        return False
    if _legacy_bundle_present(project_path):
        return False
    if _config_carries_any_activation(config_data):
        return False
    return not _unify_promotion_pending(project_path)


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------


def _normalize_charter_yaml(charter_path: Path, missing: list[str]) -> None:
    """Write explicit ``[]`` for each *missing* per-artifact key into charter.yaml.

    Routed through the shared INV-9 write helper so governance / directives /
    catalog / metadata and already-present activation keys survive byte-for-byte.
    """
    from charter.activation.charter_yaml_io import update_charter_yaml_section  # noqa: PLC0415 -- lazy (C-002)

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
        "Write an empty list for each absent per-artifact activated_<kind> key "
        "in the resolved store (charter.yaml if pointer set, else config.yaml): "
        "absence means 'nothing activated' not 'all built-ins' (FR-018). "
        "Ensures the config.yaml charter: pointer exists."
    )
    target_version = TARGET_VERSION
    runs_on_worktrees = False

    def detect(self, project_path: Path) -> bool:
        """True when the resolved store omits any per-artifact activation key,
        or a charter.yaml store exists without a config ``charter:`` pointer.

        The per-artifact check is skipped for a bare config.yaml store (no
        ``charter.yaml`` yet) when nothing else already visible this pass
        would trigger the fold migration anyway -- see
        ``_should_defer_bare_config_write`` / the module docstring's
        "Two-invocation churn guard" (NFR-006).
        """
        config_data = _load_yaml_mapping(_config_path(project_path))
        charter_path = _resolved_charter_yaml(project_path, config_data)
        activation = _store_activation_mapping(project_path, config_data)
        if _missing_per_artifact_keys(activation) and not _should_defer_bare_config_write(
            project_path, config_data, charter_path
        ):
            return True
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
        if missing and _should_defer_bare_config_write(project_path, config_data, charter_path):
            missing = []
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
