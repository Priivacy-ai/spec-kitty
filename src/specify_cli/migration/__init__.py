"""Migration helpers for Spec Kitty canonical context architecture.

Provides schema version gate (WP11), one-shot migration steps (WP12), and
the state rebuild + atomic runner (WP13).
"""

from typing import TYPE_CHECKING

# WP11: schema version gate
from .schema_version import (
    REQUIRED_SCHEMA_VERSION,
    SCHEMA_CAPABILITIES,
    CompatibilityResult,
    CompatibilityStatus,
    check_compatibility,
    get_project_schema_version,
)
from .gate import check_schema_version

# WP12: one-shot migration helpers
from .backfill_identity import (
    backfill_mission_ids,
    backfill_project_uuid,
    backfill_wp_ids,
)
from .backfill_ownership import backfill_ownership
from .normalize_mission_lifecycle import (
    NormalizeMissionLifecycleResult,
    normalize_repo as normalize_mission_lifecycle_repo,
)
from .strip_frontmatter import StripResult, strip_mutable_fields
from .rewrite_shims import RewriteResult, rewrite_agent_shims

# WP13: atomic runner. ``RebuildResult`` / ``rebuild_event_log`` live in the
# deprecated ``rebuild_state`` module (superseded by
# ``mission_state.repair_repo``) and are re-exported lazily via ``__getattr__``
# below, so importing this package does not emit the module's import-time
# DeprecationWarning for unrelated consumers.
from .runner import MigrationReport, run_migration

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .rebuild_state import RebuildResult, rebuild_event_log

__all__ = [
    # schema version (WP11)
    "REQUIRED_SCHEMA_VERSION",
    "SCHEMA_CAPABILITIES",
    "CompatibilityResult",
    "CompatibilityStatus",
    "check_compatibility",
    "get_project_schema_version",
    "check_schema_version",
    # identity backfill (WP12)
    "backfill_project_uuid",
    "backfill_mission_ids",
    "backfill_wp_ids",
    # ownership backfill (WP12)
    "backfill_ownership",
    # lifecycle normalization
    "NormalizeMissionLifecycleResult",
    "normalize_mission_lifecycle_repo",
    # frontmatter strip (WP12)
    "StripResult",
    "strip_mutable_fields",
    # shim rewrite (WP12)
    "RewriteResult",
    "rewrite_agent_shims",
    # state rebuild (WP13)
    "RebuildResult",
    "rebuild_event_log",
    # atomic runner (WP13)
    "MigrationReport",
    "run_migration",
]

_DEPRECATED_REBUILD_EXPORTS = frozenset({"RebuildResult", "rebuild_event_log"})


def __getattr__(name: str) -> object:
    """Lazily re-export deprecated ``rebuild_state`` symbols (PEP 562).

    Deferring the import keeps ``from specify_cli.migration import
    rebuild_event_log`` working while ensuring the ``rebuild_state`` module's
    import-time ``DeprecationWarning`` fires only when a symbol is actually
    accessed — not for every importer of this package.
    """
    if name in _DEPRECATED_REBUILD_EXPORTS:
        from . import rebuild_state

        return getattr(rebuild_state, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
