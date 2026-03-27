"""Migration helpers for Spec Kitty canonical context architecture.

Provides schema version gate (WP11) and one-shot migration steps (WP12):
identity backfill, ownership inference, frontmatter stripping, and shim
rewriting.
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
from .strip_frontmatter import StripResult, strip_mutable_fields
from .rewrite_shims import RewriteResult, rewrite_agent_shims

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
    # frontmatter strip (WP12)
    "StripResult",
    "strip_mutable_fields",
    # shim rewrite (WP12)
    "RewriteResult",
    "rewrite_agent_shims",
]
