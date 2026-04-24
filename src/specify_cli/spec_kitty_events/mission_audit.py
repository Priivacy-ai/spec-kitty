"""Mission Audit Lifecycle Event Contracts domain module.

Provides enums, event type constants, value objects, payload models,
the ReducedMissionAuditState output model, and a reducer stub for the
Mission Audit Lifecycle contract.
"""
from __future__ import annotations

from enum import Enum
from typing import FrozenSet, List, Literal, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field

from .dossier import ContentHashRef, ProvenanceRef
from .models import Event
from .status import dedup_events, status_event_sort_key

# ── Section 1: Schema Version ─────────────────────────────────────────────────

AUDIT_SCHEMA_VERSION: str = "2.5.0"

# ── Section 2: Event Type Constants ──────────────────────────────────────────

MISSION_AUDIT_REQUESTED: str = "MissionAuditRequested"
MISSION_AUDIT_STARTED: str = "MissionAuditStarted"
MISSION_AUDIT_DECISION_REQUESTED: str = "MissionAuditDecisionRequested"
MISSION_AUDIT_COMPLETED: str = "MissionAuditCompleted"
MISSION_AUDIT_FAILED: str = "MissionAuditFailed"

MISSION_AUDIT_EVENT_TYPES: FrozenSet[str] = frozenset({
    MISSION_AUDIT_REQUESTED,
    MISSION_AUDIT_STARTED,
    MISSION_AUDIT_DECISION_REQUESTED,
    MISSION_AUDIT_COMPLETED,
    MISSION_AUDIT_FAILED,
})

# ── Section 3: Enums ──────────────────────────────────────────────────────────


class AuditVerdict(str, Enum):
    PASS = "pass"
    PASS_WITH_WARNINGS = "pass_with_warnings"
    FAIL = "fail"
    BLOCKED_DECISION_REQUIRED = "blocked_decision_required"


class AuditSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_DECISION = "awaiting_decision"
    COMPLETED = "completed"
    FAILED = "failed"


TERMINAL_AUDIT_STATUSES: FrozenSet[AuditStatus] = frozenset({
    AuditStatus.COMPLETED,
    AuditStatus.FAILED,
})

# ── Section 4: Value Objects ──────────────────────────────────────────────────


class AuditArtifactRef(BaseModel):
    """Links an audit report to its content hash and provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    report_path: str = Field(..., min_length=1)
    content_hash: ContentHashRef
    provenance: ProvenanceRef


class PendingDecision(BaseModel):
    """Tracks an unresolved decision checkpoint within the reducer."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: str = Field(..., min_length=1)
    question: str
    context_summary: str
    severity: AuditSeverity


class MissionAuditAnomaly(BaseModel):
    """Non-fatal issue recorded during reduction.

    Valid kind values: "event_before_requested", "event_after_terminal",
    "duplicate_decision_id", "unrecognized_event_type".
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str
    event_id: str
    message: str


# ── Section 5: Payload Models ─────────────────────────────────────────────────


class MissionAuditRequestedPayload(BaseModel):
    """Payload for MissionAuditRequested events (FR-003)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    mission_slug: str = Field(..., min_length=1)
    mission_number: int = Field(..., ge=1)
    mission_type: str = Field(..., min_length=1)
    actor: str = Field(..., min_length=1)
    trigger_mode: Literal["manual", "post_merge"]
    audit_scope: List[str] = Field(..., min_length=1)
    enforcement_mode: Literal["advisory", "blocking"]


class MissionAuditStartedPayload(BaseModel):
    """Payload for MissionAuditStarted events (FR-004)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    mission_slug: str = Field(..., min_length=1)
    mission_number: int = Field(..., ge=1)
    mission_type: str = Field(..., min_length=1)
    actor: str = Field(..., min_length=1)
    audit_scope_hash: str = Field(..., min_length=1)


class MissionAuditDecisionRequestedPayload(BaseModel):
    """Payload for MissionAuditDecisionRequested events (FR-005)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    mission_slug: str = Field(..., min_length=1)
    mission_number: int = Field(..., ge=1)
    mission_type: str = Field(..., min_length=1)
    actor: str = Field(..., min_length=1)
    decision_id: str = Field(..., min_length=1)
    question: str
    context_summary: str
    severity: AuditSeverity


class MissionAuditCompletedPayload(BaseModel):
    """Payload for MissionAuditCompleted events (FR-006).

    artifact_ref is required — not Optional. If artifact generation fails,
    the emitter MUST emit MissionAuditFailed instead.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    mission_slug: str = Field(..., min_length=1)
    mission_number: int = Field(..., ge=1)
    mission_type: str = Field(..., min_length=1)
    actor: str = Field(..., min_length=1)
    verdict: AuditVerdict
    severity: AuditSeverity
    findings_count: int = Field(..., ge=0)
    artifact_ref: AuditArtifactRef
    summary: str


class MissionAuditFailedPayload(BaseModel):
    """Payload for MissionAuditFailed events (FR-007)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    mission_slug: str = Field(..., min_length=1)
    mission_number: int = Field(..., ge=1)
    mission_type: str = Field(..., min_length=1)
    actor: str = Field(..., min_length=1)
    error_code: str = Field(..., min_length=1)
    error_message: str
    partial_artifact_ref: Optional[AuditArtifactRef] = None


# ── Section 6: Reducer Output Model ──────────────────────────────────────────


class ReducedMissionAuditState(BaseModel):
    """Deterministic projection output of reduce_mission_audit_events() (FR-012–FR-014, R-005)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    audit_status: AuditStatus = AuditStatus.PENDING
    verdict: Optional[AuditVerdict] = None
    severity: Optional[AuditSeverity] = None
    findings_count: Optional[int] = None
    artifact_ref: Optional[AuditArtifactRef] = None
    partial_artifact_ref: Optional[AuditArtifactRef] = None
    summary: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    pending_decisions: Tuple[PendingDecision, ...] = ()
    mission_id: Optional[str] = None
    run_id: Optional[str] = None
    mission_slug: Optional[str] = None
    mission_number: Optional[int] = None
    mission_type: Optional[str] = None
    trigger_mode: Optional[str] = None
    enforcement_mode: Optional[str] = None
    audit_scope: Optional[Tuple[str, ...]] = None
    audit_scope_hash: Optional[str] = None
    anomalies: Tuple[MissionAuditAnomaly, ...] = ()
    event_count: int = 0


# ── Section 7: Reducer Stub ───────────────────────────────────────────────────


def reduce_mission_audit_events(events: Sequence[Event]) -> ReducedMissionAuditState:
    """Deterministic reducer: Sequence[Event] → ReducedMissionAuditState.

    Pipeline: sort → dedup → filter(MISSION_AUDIT_EVENT_TYPES) → reduce → freeze.
    """
    # Step 1: Sort by (timestamp, lamport_clock) for determinism
    sorted_events = sorted(events, key=status_event_sort_key)

    # Step 2: Deduplicate by event_id
    deduped_events = dedup_events(sorted_events)

    # Step 3: Count events after dedup (before filter) — event_count is post-dedup
    event_count = len(deduped_events)

    # Step 4: Filter to mission-audit family only
    audit_events = [e for e in deduped_events if e.event_type in MISSION_AUDIT_EVENT_TYPES]

    # Step 5: Mutable accumulator for the fold
    pending_decisions_list: List[PendingDecision] = []
    anomalies_list: List[MissionAuditAnomaly] = []
    audit_status: AuditStatus = AuditStatus.PENDING
    verdict: Optional[AuditVerdict] = None
    severity: Optional[AuditSeverity] = None
    findings_count: Optional[int] = None
    artifact_ref: Optional[AuditArtifactRef] = None
    partial_artifact_ref: Optional[AuditArtifactRef] = None
    summary: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    mission_id: Optional[str] = None
    run_id: Optional[str] = None
    mission_slug: Optional[str] = None
    mission_number: Optional[int] = None
    mission_type: Optional[str] = None
    trigger_mode: Optional[str] = None
    enforcement_mode: Optional[str] = None
    audit_scope: Optional[Tuple[str, ...]] = None
    audit_scope_hash: Optional[str] = None
    requested_seen = False
    terminal_seen = False

    for event in audit_events:
        event_type = event.event_type
        event_id = event.event_id
        payload_dict = event.payload if isinstance(event.payload, dict) else {}

        # Anomaly: event after terminal
        if terminal_seen:
            anomalies_list.append(MissionAuditAnomaly(
                kind="event_after_terminal",
                event_id=event_id,
                message=f"Event {event_type!r} arrived after terminal state",
            ))
            continue

        # Anomaly: event before Requested (except Requested itself)
        if not requested_seen and event_type != MISSION_AUDIT_REQUESTED:
            anomalies_list.append(MissionAuditAnomaly(
                kind="event_before_requested",
                event_id=event_id,
                message=f"Event {event_type!r} arrived before MissionAuditRequested",
            ))
            # Still process state transitions for robustness — do not skip

        if event_type == MISSION_AUDIT_REQUESTED:
            requested_seen = True
            req_payload: MissionAuditRequestedPayload = MissionAuditRequestedPayload.model_validate(payload_dict)
            mission_id = req_payload.mission_id
            run_id = req_payload.run_id
            mission_slug = req_payload.mission_slug
            mission_number = req_payload.mission_number
            mission_type = req_payload.mission_type
            trigger_mode = req_payload.trigger_mode
            enforcement_mode = req_payload.enforcement_mode
            audit_scope = tuple(req_payload.audit_scope)
            # status stays PENDING after Requested

        elif event_type == MISSION_AUDIT_STARTED:
            started_payload: MissionAuditStartedPayload = MissionAuditStartedPayload.model_validate(payload_dict)
            audit_scope_hash = started_payload.audit_scope_hash
            if not mission_id:
                mission_id = started_payload.mission_id
                run_id = started_payload.run_id
                mission_slug = started_payload.mission_slug
                mission_number = started_payload.mission_number
                mission_type = started_payload.mission_type
            audit_status = AuditStatus.RUNNING

        elif event_type == MISSION_AUDIT_DECISION_REQUESTED:
            dec_payload: MissionAuditDecisionRequestedPayload = MissionAuditDecisionRequestedPayload.model_validate(payload_dict)
            # Anomaly: duplicate decision_id
            existing_ids = [d.decision_id for d in pending_decisions_list]
            if dec_payload.decision_id in existing_ids:
                anomalies_list.append(MissionAuditAnomaly(
                    kind="duplicate_decision_id",
                    event_id=event_id,
                    message=f"Duplicate decision_id: {dec_payload.decision_id!r}",
                ))
            else:
                pending_decisions_list.append(PendingDecision(
                    decision_id=dec_payload.decision_id,
                    question=dec_payload.question,
                    context_summary=dec_payload.context_summary,
                    severity=dec_payload.severity,
                ))
            if mission_id is None:
                mission_id = dec_payload.mission_id
                run_id = dec_payload.run_id
                mission_slug = dec_payload.mission_slug
                mission_number = dec_payload.mission_number
                mission_type = dec_payload.mission_type
            audit_status = AuditStatus.AWAITING_DECISION

        elif event_type == MISSION_AUDIT_COMPLETED:
            comp_payload: MissionAuditCompletedPayload = MissionAuditCompletedPayload.model_validate(payload_dict)
            verdict = comp_payload.verdict
            severity = comp_payload.severity
            findings_count = comp_payload.findings_count
            artifact_ref = comp_payload.artifact_ref
            summary = comp_payload.summary
            if mission_id is None:
                mission_id = comp_payload.mission_id
                run_id = comp_payload.run_id
                mission_slug = comp_payload.mission_slug
                mission_number = comp_payload.mission_number
                mission_type = comp_payload.mission_type
            pending_decisions_list = []  # implicit resolution on terminal
            audit_status = AuditStatus.COMPLETED
            terminal_seen = True

        elif event_type == MISSION_AUDIT_FAILED:
            fail_payload: MissionAuditFailedPayload = MissionAuditFailedPayload.model_validate(payload_dict)
            error_code = fail_payload.error_code
            error_message = fail_payload.error_message
            partial_artifact_ref = fail_payload.partial_artifact_ref
            if mission_id is None:
                mission_id = fail_payload.mission_id
                run_id = fail_payload.run_id
                mission_slug = fail_payload.mission_slug
                mission_number = fail_payload.mission_number
                mission_type = fail_payload.mission_type
            pending_decisions_list = []  # implicit resolution on terminal
            audit_status = AuditStatus.FAILED
            terminal_seen = True

    # Step 6: Freeze and return
    return ReducedMissionAuditState(
        audit_status=audit_status,
        verdict=verdict,
        severity=severity,
        findings_count=findings_count,
        artifact_ref=artifact_ref,
        partial_artifact_ref=partial_artifact_ref,
        summary=summary,
        error_code=error_code,
        error_message=error_message,
        pending_decisions=tuple(pending_decisions_list),
        mission_id=mission_id,
        run_id=run_id,
        mission_slug=mission_slug,
        mission_number=mission_number,
        mission_type=mission_type,
        trigger_mode=trigger_mode,
        enforcement_mode=enforcement_mode,
        audit_scope=audit_scope,
        audit_scope_hash=audit_scope_hash,
        anomalies=tuple(anomalies_list),
        event_count=event_count,
    )
