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
from specify_cli.invocation.record import (
    EvidenceArtifact,
    InvocationRecord,
    MINIMAL_VIABLE_TRAIL_POLICY,
    MinimalViableTrailPolicy,
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
    "MINIMAL_VIABLE_TRAIL_POLICY",
    "MinimalViableTrailPolicy",
    "ProfileInvocationExecutor",
    "ProfileNotFoundError",
    "ProfileRegistry",
    "RouterAmbiguityError",
    "TIER_3_ACTIONS",
    "TierEligibility",
    "TierPolicy",
    "promote_to_evidence",
    "tier_eligible",
]
