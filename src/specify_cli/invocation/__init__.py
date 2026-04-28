"""Public API for the invocation package.

This package provides the core primitives for profile-governed invocations:
- ProfileInvocationExecutor — the single execution entry point
- InvocationRecord — the v1 JSONL audit trail event model
- ProfileRegistry — thin wrapper over AgentProfileRepository
- InvocationWriter — append-only JSONL writer
- Structured error types
- MinimalViableTrailPolicy — three-tier trail contract
- tier_eligible / promote_to_evidence — tier helpers
"""

from __future__ import annotations

from specify_cli.invocation.errors import (
    AlreadyClosedError,
    ContextUnavailableError,
    InvocationError,
    InvocationWriteError,
    ProfileNotFoundError,
    RouterAmbiguityError,
)
from specify_cli.invocation.executor import InvocationPayload, ProfileInvocationExecutor
from specify_cli.invocation.lifecycle import (
    LIFECYCLE_LOG_RELATIVE_PATH,
    LifecycleGroup,
    append_lifecycle_record,
    compute_pairing_rate,
    doctor_orphan_report,
    find_latest_unpaired_started,
    find_orphans,
    group_by_action,
    lifecycle_log_path,
    make_canonical_action_id,
    read_lifecycle_records,
    write_paired_completion,
    write_started,
)
from specify_cli.invocation.record import (
    EvidenceArtifact,
    InvocationRecord,
    MINIMAL_VIABLE_TRAIL_POLICY,
    MinimalViableTrailPolicy,
    ProfileInvocationPhase,
    ProfileInvocationRecord,
    TIER_3_ACTIONS,
    TierEligibility,
    TierPolicy,
    promote_to_evidence,
    tier_eligible,
)
from specify_cli.invocation.registry import ProfileRegistry
from specify_cli.invocation.writer import InvocationWriter

__all__ = [
    "AlreadyClosedError",
    "ContextUnavailableError",
    "EvidenceArtifact",
    "InvocationError",
    "InvocationPayload",
    "InvocationRecord",
    "InvocationWriteError",
    "InvocationWriter",
    "LIFECYCLE_LOG_RELATIVE_PATH",
    "LifecycleGroup",
    "MINIMAL_VIABLE_TRAIL_POLICY",
    "MinimalViableTrailPolicy",
    "ProfileInvocationExecutor",
    "ProfileInvocationPhase",
    "ProfileInvocationRecord",
    "ProfileNotFoundError",
    "ProfileRegistry",
    "RouterAmbiguityError",
    "TIER_3_ACTIONS",
    "TierEligibility",
    "TierPolicy",
    "append_lifecycle_record",
    "compute_pairing_rate",
    "doctor_orphan_report",
    "find_latest_unpaired_started",
    "find_orphans",
    "group_by_action",
    "lifecycle_log_path",
    "make_canonical_action_id",
    "promote_to_evidence",
    "read_lifecycle_records",
    "tier_eligible",
    "write_paired_completion",
    "write_started",
]
