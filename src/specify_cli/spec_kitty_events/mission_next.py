"""Mission-next runtime event contracts.

Defines event type constants, value objects, payload models,
reducer output models, and the mission-next reducer for
run-scoped mission execution state materialization.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field

from .models import Event

# ── Section 1: Constants ─────────────────────────────────────────────────────

MISSION_RUN_STARTED: str = "MissionRunStarted"
NEXT_STEP_PLANNED: str = "NextStepPlanned"  # Reserved — payload contract deferred until runtime emits
NEXT_STEP_ISSUED: str = "NextStepIssued"
NEXT_STEP_AUTO_COMPLETED: str = "NextStepAutoCompleted"
DECISION_INPUT_REQUESTED: str = "DecisionInputRequested"
DECISION_INPUT_ANSWERED: str = "DecisionInputAnswered"
MISSION_RUN_COMPLETED: str = "MissionRunCompleted"

MISSION_NEXT_EVENT_TYPES: FrozenSet[str] = frozenset({
    MISSION_RUN_STARTED,
    NEXT_STEP_PLANNED,
    NEXT_STEP_ISSUED,
    NEXT_STEP_AUTO_COMPLETED,
    DECISION_INPUT_REQUESTED,
    DECISION_INPUT_ANSWERED,
    MISSION_RUN_COMPLETED,
})

# ── Section 2: Value Objects ─────────────────────────────────────────────────


class RuntimeActorIdentity(BaseModel):
    """Identity of a runtime actor (human, LLM, or service)."""

    model_config = ConfigDict(frozen=True)

    actor_id: str = Field(
        ..., min_length=1, description="Unique actor identifier"
    )
    actor_type: str = Field(
        ..., description="Actor category",
        pattern=r"^(human|llm|service)$",
    )
    display_name: str = Field(
        default="", description="Human-readable display name"
    )
    provider: Optional[str] = Field(
        None, description="Provider (e.g., 'anthropic', 'openai')"
    )
    model: Optional[str] = Field(
        None, description="Model identifier (e.g., 'claude-opus-4-6')"
    )
    tool: Optional[str] = Field(
        None, description="Tool identifier"
    )


# ── Section 3: Enum ──────────────────────────────────────────────────────────


class MissionRunStatus(str, Enum):
    """Mission run execution states."""

    RUNNING = "running"
    COMPLETED = "completed"


TERMINAL_RUN_STATUSES: FrozenSet[MissionRunStatus] = frozenset({
    MissionRunStatus.COMPLETED,
})

# ── Section 4: Payload Models ────────────────────────────────────────────────


class MissionRunStartedPayload(BaseModel):
    """Payload for MissionRunStarted event."""

    model_config = ConfigDict(frozen=True)

    run_id: str = Field(..., min_length=1, description="Unique run identifier")
    mission_type: str = Field(
        ..., min_length=1, description="Mission workflow/template type being executed"
    )
    actor: RuntimeActorIdentity = Field(
        ..., description="Actor who started the run"
    )


class NextStepIssuedPayload(BaseModel):
    """Payload for NextStepIssued event."""

    model_config = ConfigDict(frozen=True)

    run_id: str = Field(..., min_length=1, description="Run identifier")
    step_id: str = Field(..., min_length=1, description="Step being issued")
    agent_id: str = Field(
        ..., min_length=1, description="Agent handling the step"
    )
    actor: RuntimeActorIdentity = Field(
        ..., description="Actor who issued the step"
    )


class NextStepAutoCompletedPayload(BaseModel):
    """Payload for NextStepAutoCompleted event."""

    model_config = ConfigDict(frozen=True)

    run_id: str = Field(..., min_length=1, description="Run identifier")
    step_id: str = Field(..., min_length=1, description="Step that completed")
    agent_id: str = Field(
        ..., min_length=1, description="Agent that completed the step"
    )
    result: str = Field(
        ..., min_length=1, description="Step result (e.g., 'success', 'failed')"
    )
    actor: RuntimeActorIdentity = Field(
        ..., description="Actor context for the completion"
    )


class DecisionInputRequestedPayload(BaseModel):
    """Payload for DecisionInputRequested event."""

    model_config = ConfigDict(frozen=True)

    run_id: str = Field(..., min_length=1, description="Run identifier")
    decision_id: str = Field(
        ..., min_length=1, description="Unique decision identifier"
    )
    step_id: str = Field(
        ..., min_length=1, description="Step requiring the decision"
    )
    question: str = Field(
        ..., min_length=1, description="Question posed to the decision maker"
    )
    options: Tuple[str, ...] = Field(
        default_factory=tuple, description="Suggested answer options"
    )
    input_key: Optional[str] = Field(
        None, description="Input key for input-keyed decisions"
    )
    actor: RuntimeActorIdentity = Field(
        ..., description="Actor who requested the decision"
    )


class DecisionInputAnsweredPayload(BaseModel):
    """Payload for DecisionInputAnswered event."""

    model_config = ConfigDict(frozen=True)

    run_id: str = Field(..., min_length=1, description="Run identifier")
    decision_id: str = Field(
        ..., min_length=1, description="Decision being answered"
    )
    answer: str = Field(
        ..., min_length=1, description="The answer provided"
    )
    actor: RuntimeActorIdentity = Field(
        ..., description="Actor who answered the decision"
    )


class MissionRunCompletedPayload(BaseModel):
    """Payload for MissionRunCompleted event."""

    model_config = ConfigDict(frozen=True)

    run_id: str = Field(..., min_length=1, description="Run identifier")
    mission_type: str = Field(
        ..., min_length=1, description="Mission workflow/template type that completed"
    )
    actor: RuntimeActorIdentity = Field(
        ..., description="Actor context for the completion"
    )


# ── Section 5: Reducer Output Models ─────────────────────────────────────────


class MissionNextAnomaly(BaseModel):
    """Non-fatal issue encountered during mission-next event reduction."""

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(..., description="ID of the event that caused the anomaly")
    event_type: str = Field(..., description="Type of the problematic event")
    reason: str = Field(..., description="Human-readable explanation")


class ReducedMissionRunState(BaseModel):
    """Projected mission run state from reduce_mission_next_events()."""

    model_config = ConfigDict(frozen=True)

    run_id: Optional[str] = Field(
        default=None, description="Run ID from MissionRunStarted"
    )
    mission_type: Optional[str] = Field(
        default=None, description="Mission workflow/template type from MissionRunStarted"
    )
    run_status: Optional[MissionRunStatus] = Field(
        default=None, description="Current run status"
    )
    current_step_id: Optional[str] = Field(
        default=None, description="Currently issued step (None if idle or completed)"
    )
    completed_steps: Tuple[str, ...] = Field(
        default_factory=tuple, description="Ordered list of completed step IDs"
    )
    pending_decisions: Dict[str, DecisionInputRequestedPayload] = Field(
        default_factory=dict,
        description="decision_id → pending request payload",
    )
    answered_decisions: Dict[str, DecisionInputAnsweredPayload] = Field(
        default_factory=dict,
        description="decision_id → answered payload",
    )
    anomalies: Tuple[MissionNextAnomaly, ...] = Field(
        default_factory=tuple, description="Non-fatal issues encountered"
    )
    event_count: int = Field(default=0, description="Total events processed")
    last_processed_event_id: Optional[str] = Field(
        default=None, description="Last event_id in processed sequence"
    )


# ── Section 6: Reducer ───────────────────────────────────────────────────────


def reduce_mission_next_events(
    events: Sequence[Event],
) -> ReducedMissionRunState:
    """Fold mission-next events into projected run state.

    Pipeline:
    1. Filter to canonical mission-next event types
    2. Sort by (lamport_clock, timestamp, event_id)
    3. Deduplicate by event_id
    4. Process each event
    5. Assemble frozen ReducedMissionRunState

    Pure function. No I/O. Deterministic for any causal-order-preserving
    permutation.
    """
    from .status import dedup_events, status_event_sort_key

    if not events:
        return ReducedMissionRunState()

    # 1. Filter
    next_events = [
        e
        for e in events
        if e.event_type in MISSION_NEXT_EVENT_TYPES
    ]

    if not next_events:
        return ReducedMissionRunState()

    # 2. Sort
    sorted_events = sorted(next_events, key=status_event_sort_key)

    # 3. Dedup
    unique_events = dedup_events(sorted_events)

    # 4. Process (mutable intermediates)
    run_id: Optional[str] = None
    mission_type: Optional[str] = None
    run_status: Optional[MissionRunStatus] = None
    current_step_id: Optional[str] = None
    completed_steps: List[str] = []
    pending_decisions: Dict[str, DecisionInputRequestedPayload] = {}
    answered_decisions: Dict[str, DecisionInputAnsweredPayload] = {}
    anomalies: List[MissionNextAnomaly] = []

    for event in unique_events:
        etype = event.event_type

        # Skip reserved event type (no payload, no anomaly)
        if etype == NEXT_STEP_PLANNED:
            continue

        # Check: event after terminal state
        if run_status in TERMINAL_RUN_STATUSES:
            if etype == MISSION_RUN_COMPLETED:
                # Terminal idempotency: duplicate completion → anomaly
                anomalies.append(MissionNextAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason="Duplicate completion (terminal idempotency)",
                ))
            else:
                anomalies.append(MissionNextAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason=f"Event after terminal state ({run_status})",
                ))
            continue

        if etype == MISSION_RUN_STARTED:
            if run_id is not None:
                # Duplicate start: first wins
                anomalies.append(MissionNextAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason="Duplicate MissionRunStarted (first one wins)",
                ))
                continue
            try:
                payload_started = MissionRunStartedPayload(**event.payload)
            except Exception:
                anomalies.append(MissionNextAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason="Invalid MissionRunStarted payload",
                ))
                continue
            run_id = payload_started.run_id
            mission_type = payload_started.mission_type
            run_status = MissionRunStatus.RUNNING
            continue

        # Check: event before start
        if run_id is None:
            anomalies.append(MissionNextAnomaly(
                event_id=event.event_id,
                event_type=event.event_type,
                reason="Event before MissionRunStarted",
            ))
            continue

        if etype == NEXT_STEP_ISSUED:
            try:
                payload_issued = NextStepIssuedPayload(**event.payload)
            except Exception:
                anomalies.append(MissionNextAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason="Invalid NextStepIssued payload",
                ))
                continue
            if payload_issued.run_id != run_id:
                anomalies.append(MissionNextAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason=f"run_id mismatch: expected '{run_id}', got '{payload_issued.run_id}'",
                ))
                continue
            current_step_id = payload_issued.step_id

        elif etype == NEXT_STEP_AUTO_COMPLETED:
            try:
                payload_completed = NextStepAutoCompletedPayload(**event.payload)
            except Exception:
                anomalies.append(MissionNextAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason="Invalid NextStepAutoCompleted payload",
                ))
                continue
            if payload_completed.run_id != run_id:
                anomalies.append(MissionNextAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason=f"run_id mismatch: expected '{run_id}', got '{payload_completed.run_id}'",
                ))
                continue
            if payload_completed.step_id not in completed_steps:
                completed_steps.append(payload_completed.step_id)
            if current_step_id == payload_completed.step_id:
                current_step_id = None

        elif etype == DECISION_INPUT_REQUESTED:
            try:
                payload_req = DecisionInputRequestedPayload(**event.payload)
            except Exception:
                anomalies.append(MissionNextAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason="Invalid DecisionInputRequested payload",
                ))
                continue
            if payload_req.run_id != run_id:
                anomalies.append(MissionNextAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason=f"run_id mismatch: expected '{run_id}', got '{payload_req.run_id}'",
                ))
                continue
            if payload_req.decision_id in pending_decisions:
                # Duplicate decision request → anomaly (idempotent)
                anomalies.append(MissionNextAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason=f"Duplicate decision request '{payload_req.decision_id}'",
                ))
            else:
                pending_decisions[payload_req.decision_id] = payload_req

        elif etype == DECISION_INPUT_ANSWERED:
            try:
                payload_ans = DecisionInputAnsweredPayload(**event.payload)
            except Exception:
                anomalies.append(MissionNextAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason="Invalid DecisionInputAnswered payload",
                ))
                continue
            if payload_ans.run_id != run_id:
                anomalies.append(MissionNextAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason=f"run_id mismatch: expected '{run_id}', got '{payload_ans.run_id}'",
                ))
                continue
            answered_decisions[payload_ans.decision_id] = payload_ans
            # Clear from pending when answered
            pending_decisions.pop(payload_ans.decision_id, None)

        elif etype == MISSION_RUN_COMPLETED:
            try:
                payload_done = MissionRunCompletedPayload(**event.payload)
            except Exception:
                anomalies.append(MissionNextAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason="Invalid MissionRunCompleted payload",
                ))
                continue
            if payload_done.run_id != run_id:
                anomalies.append(MissionNextAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason=f"run_id mismatch: expected '{run_id}', got '{payload_done.run_id}'",
                ))
                continue
            run_status = MissionRunStatus.COMPLETED

    # 5. Assemble frozen state
    last_event = unique_events[-1]

    return ReducedMissionRunState(
        run_id=run_id,
        mission_type=mission_type,
        run_status=run_status,
        current_step_id=current_step_id,
        completed_steps=tuple(completed_steps),
        pending_decisions=pending_decisions,
        answered_decisions=answered_decisions,
        anomalies=tuple(anomalies),
        event_count=len(unique_events),
        last_processed_event_id=last_event.event_id,
    )
