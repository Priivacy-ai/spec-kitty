"""Migration helpers for Spec Kitty canonical context architecture.

Provides schema version gate (WP11), one-shot migration steps (WP12), and
the state rebuild + atomic runner (WP13).
"""

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

# WP13: state rebuild and atomic runner
from .rebuild_state import RebuildResult, rebuild_event_log
from .runner import MigrationReport, run_migration

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
