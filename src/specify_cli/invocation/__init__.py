"""Public API for the invocation package.

This package provides the core primitives for profile-governed invocations:
- ProfileInvocationExecutor — the single execution entry point
- OpStartedEvent / OpCompletedEvent — the v2 JSONL audit trail event models
- ProfileRegistry — thin wrapper over AgentProfileRepository
- InvocationWriter — append-only JSONL writer
- Structured error types
- MinimalViableTrailPolicy — three-tier trail contract
- tier_eligible / promote_to_evidence — tier helpers
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from specify_cli.invocation.adapters import (
    get_saas_client,
    register_saas_client_factory,
    register_sync_routing_resolver,
    reset_adapters,
    resolve_sync_routing,
)
from specify_cli.invocation.errors import (
    AlreadyClosedError,
    ContextUnavailableError,
    InvocationError,
    InvocationWriteError,
    LegacyRecordError,
    ProfileNotFoundError,
    RouterAmbiguityError,
)
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
    MINIMAL_VIABLE_TRAIL_POLICY,
    MinimalViableTrailPolicy,
    OpCompletedEvent,
    OpStartedEvent,
    ProfileInvocationPhase,
    ProfileInvocationRecord,
    TIER_3_ACTIONS,
    TierEligibility,
    TierPolicy,
    parse_op_event,
    promote_to_evidence,
    tier_eligible,
)
from specify_cli.invocation.writer import InvocationWriter

# ``executor`` and ``registry`` are the heavy submodules of this package: the
# executor (~224 ms cold) transitively pulls the action router + doctrine
# machinery, and ``registry`` (~143 ms cold) wraps ``AgentProfileRepository``,
# which pulls the agent-profile/tool-surface/doctrine stack. Importing ANY
# submodule of this package runs this ``__init__``; eagerly re-exporting from
# those modules here dragged the whole router/doctrine stack into CLI
# cold-start the moment ``sync`` (an INTEGRATION leaf that registers into
# ``invocation.adapters`` at import) was loaded on the ``next`` hot path
# (NFR-003 regression, #614). Defer those re-exports via PEP 562 so the cheap
# submodules (adapters, errors, record, writer, lifecycle) stay eager while the
# executor/registry stacks load only when an actual profile invocation accesses
# them. Registration timing is untouched — only the import cost moves.
if TYPE_CHECKING:
    from specify_cli.invocation.executor import (
        InvocationPayload,
        ProfileInvocationExecutor,
    )
    from specify_cli.invocation.registry import ProfileRegistry

_LAZY_EXPORTS: dict[str, str] = {
    "InvocationPayload": "executor",
    "ProfileInvocationExecutor": "executor",
    "ProfileRegistry": "registry",
}


def __getattr__(name: str) -> Any:
    """Lazily resolve the heavy ``executor`` / ``registry`` re-exports (PEP 562)."""
    submodule = _LAZY_EXPORTS.get(name)
    if submodule is not None:
        import importlib

        module = importlib.import_module(f"specify_cli.invocation.{submodule}")
        value = getattr(module, name)
        globals()[name] = value  # cache so __getattr__ fires at most once per name
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AlreadyClosedError",
    "get_saas_client",
    "register_saas_client_factory",
    "register_sync_routing_resolver",
    "reset_adapters",
    "resolve_sync_routing",
    "ContextUnavailableError",
    "EvidenceArtifact",
    "InvocationError",
    "InvocationPayload",
    "InvocationWriteError",
    "InvocationWriter",
    "LIFECYCLE_LOG_RELATIVE_PATH",
    "LegacyRecordError",
    "LifecycleGroup",
    "MINIMAL_VIABLE_TRAIL_POLICY",
    "MinimalViableTrailPolicy",
    "OpCompletedEvent",
    "OpStartedEvent",
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
    "parse_op_event",
    "promote_to_evidence",
    "read_lifecycle_records",
    "tier_eligible",
    "write_paired_completion",
    "write_started",
]
