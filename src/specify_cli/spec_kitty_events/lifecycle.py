"""Mission lifecycle event contracts for the canonical event schema.

This module defines typed payload models for all mission-level lifecycle
events, the MissionStatus enum, event type constants, and the SCHEMA_VERSION
constant. It is part of the canonical event contract (Feature 004).

Sections:
    1. Constants (SCHEMA_VERSION, event type strings)
    2. MissionStatus Enum
    3. Lifecycle Payload Models
    4. Lifecycle Reducer Output Models (added in WP03)
    5. Lifecycle Reducer (added in WP03)
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field

# ── Section 1: Constants ─────────────────────────────────────────────────────

SCHEMA_VERSION: str = "3.0.0"

# Event type string constants
MISSION_CREATED: str = "MissionCreated"
MISSION_CLOSED: str = "MissionClosed"
MISSION_STARTED: str = "MissionStarted"
MISSION_COMPLETED: str = "MissionCompleted"
MISSION_CANCELLED: str = "MissionCancelled"
PHASE_ENTERED: str = "PhaseEntered"
REVIEW_ROLLBACK: str = "ReviewRollback"

MISSION_EVENT_TYPES: FrozenSet[str] = frozenset({
    MISSION_CREATED,
    MISSION_CLOSED,
    MISSION_STARTED,
    MISSION_COMPLETED,
    MISSION_CANCELLED,
    PHASE_ENTERED,
    REVIEW_ROLLBACK,
})

# ── Section 2: MissionStatus Enum ────────────────────────────────────────────


class MissionStatus(str, Enum):
    """Mission lifecycle states."""

    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


TERMINAL_MISSION_STATUSES: FrozenSet[MissionStatus] = frozenset({
    MissionStatus.COMPLETED,
    MissionStatus.CANCELLED,
})

# ── Section 3: Lifecycle Payload Models ──────────────────────────────────────


class MissionStartedPayload(BaseModel):
    """Typed payload for MissionStarted events."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(
        ..., min_length=1, description="Mission identifier"
    )
    mission_type: str = Field(
        ...,
        min_length=1,
        description="Mission type (e.g., 'software-dev', 'research', 'plan')",
    )
    initial_phase: str = Field(
        ..., min_length=1, description="First phase of the mission"
    )
    actor: str = Field(
        ..., min_length=1, description="Actor who started the mission"
    )


class MissionCreatedPayload(BaseModel):
    """Typed payload for MissionCreated catalog events."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_id: Optional[str] = Field(
        None, min_length=1, description="Canonical machine-facing mission identity (ULID)"
    )
    mission_slug: str = Field(
        ..., min_length=1, description="Canonical mission slug"
    )
    mission_number: Optional[int] = Field(
        ..., ge=1, description="Canonical mission number"
    )
    mission_type: str = Field(
        ..., min_length=1, description="Canonical mission workflow/template type"
    )
    target_branch: str = Field(
        ..., min_length=1, description="Target branch for the mission planning artifacts"
    )
    wp_count: int = Field(
        ..., ge=0, description="Work-package count at mission creation time"
    )
    friendly_name: str = Field(
        ..., min_length=1, description="Human-friendly mission title"
    )
    purpose_tldr: str = Field(
        ..., min_length=1, description="One-line stakeholder-facing mission summary"
    )
    purpose_context: str = Field(
        ..., min_length=1, description="Short stakeholder-facing context paragraph"
    )
    created_at: Optional[str] = Field(
        None, min_length=1, description="Mission creation timestamp"
    )


class MissionClosedPayload(BaseModel):
    """Typed payload for MissionClosed catalog events."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_slug: str = Field(
        ..., min_length=1, description="Canonical mission slug"
    )
    mission_number: int = Field(
        ..., ge=1, description="Canonical mission number"
    )
    mission_type: str = Field(
        ..., min_length=1, description="Canonical mission workflow/template type"
    )


class MissionCompletedPayload(BaseModel):
    """Typed payload for MissionCompleted events."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(
        ..., min_length=1, description="Mission identifier"
    )
    mission_type: str = Field(
        ..., min_length=1, description="Mission type"
    )
    final_phase: str = Field(
        ..., min_length=1, description="Last phase before completion"
    )
    actor: str = Field(
        ..., min_length=1, description="Actor who completed the mission"
    )


class MissionCancelledPayload(BaseModel):
    """Typed payload for MissionCancelled events."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(
        ..., min_length=1, description="Mission identifier"
    )
    reason: str = Field(
        ..., min_length=1, description="Reason for cancellation (required)"
    )
    actor: str = Field(
        ..., min_length=1, description="Actor who cancelled the mission"
    )
    cancelled_wp_ids: List[str] = Field(
        default_factory=list,
        description="WP IDs affected by cancellation",
    )


class PhaseEnteredPayload(BaseModel):
    """Typed payload for PhaseEntered events."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(
        ..., min_length=1, description="Mission identifier"
    )
    phase_name: str = Field(
        ..., min_length=1, description="Phase being entered"
    )
    previous_phase: Optional[str] = Field(
        None, min_length=1, description="Phase being exited (None for initial)"
    )
    actor: str = Field(
        ..., min_length=1, description="Actor triggering phase transition"
    )


class ReviewRollbackPayload(BaseModel):
    """Typed payload for ReviewRollback events."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(
        ..., min_length=1, description="Mission identifier"
    )
    review_ref: str = Field(
        ...,
        min_length=1,
        description="Reference to the review that triggered rollback",
    )
    target_phase: str = Field(
        ..., min_length=1, description="Phase to roll back to"
    )
    affected_wp_ids: List[str] = Field(
        default_factory=list,
        description="WP IDs affected by rollback",
    )
    actor: str = Field(
        ..., min_length=1, description="Actor triggering rollback"
    )


# ── Section 4: Lifecycle Reducer Output Models ───────────────────────────────


class LifecycleAnomaly(BaseModel):
    """Flagged issue during lifecycle reduction.

    Anomalies are non-fatal — the reducer continues processing but records
    the issue for observability.
    """

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(..., description="Event that caused the anomaly")
    event_type: str = Field(..., description="Type of the problematic event")
    reason: str = Field(..., description="Human-readable explanation")


class ReducedMissionState(BaseModel):
    """Projected mission state from lifecycle event reduction.

    Produced by reduce_lifecycle_events(). Contains both mission-level
    state (status, phase) and delegated WP-level state (via reduce_status_events).
    """

    model_config = ConfigDict(frozen=True)

    mission_id: Optional[str] = Field(
        None, description="Mission ID from MissionStarted"
    )
    mission_status: Optional[MissionStatus] = Field(
        None, description="Current mission status"
    )
    mission_type: Optional[str] = Field(
        None, description="Mission type from MissionStarted"
    )
    current_phase: Optional[str] = Field(
        None, description="Current phase from PhaseEntered"
    )
    phases_entered: Tuple[str, ...] = Field(
        default_factory=tuple, description="Ordered list of phases entered"
    )
    wp_states: Dict[str, WPState] = Field(
        default_factory=dict, description="WP states from delegated reduction"
    )
    anomalies: Tuple[LifecycleAnomaly, ...] = Field(
        default_factory=tuple, description="Flagged issues"
    )
    event_count: int = Field(0, description="Total events processed")
    last_processed_event_id: Optional[str] = Field(
        None, description="Last event ID processed"
    )


# ── Section 5: Lifecycle Reducer ─────────────────────────────────────────────


def _cancel_last_key(event: Event) -> Tuple[int, str]:
    """Sort key: MissionCancelled events sort last within concurrent groups."""
    is_cancel = 1 if event.event_type == MISSION_CANCELLED else 0
    return (is_cancel, event.event_id)


def _process_mission_event(
    event: Event,
    mission_id: Optional[str],
    mission_status: Optional[MissionStatus],
    mission_type: Optional[str],
    current_phase: Optional[str],
    phases_entered: List[str],
    anomalies: List[LifecycleAnomaly],
) -> Tuple[Optional[str], Optional[MissionStatus], Optional[str], Optional[str]]:
    """Process a single mission-level event, updating state in-place for lists.

    Returns (mission_id, mission_status, mission_type, current_phase).
    """
    if event.event_type == MISSION_CREATED:
        try:
            MissionCreatedPayload(**event.payload)
        except Exception:
            anomalies.append(
                LifecycleAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason="Invalid MissionCreated payload",
                )
            )
        return mission_id, mission_status, mission_type, current_phase

    if event.event_type == MISSION_CLOSED:
        try:
            MissionClosedPayload(**event.payload)
        except Exception:
            anomalies.append(
                LifecycleAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason="Invalid MissionClosed payload",
                )
            )
        return mission_id, mission_status, mission_type, current_phase

    # Check: event after terminal state
    if mission_status in TERMINAL_MISSION_STATUSES:
        anomalies.append(
            LifecycleAnomaly(
                event_id=event.event_id,
                event_type=event.event_type,
                reason=f"Event after terminal state ({mission_status})",
            )
        )
        return mission_id, mission_status, mission_type, current_phase

    if event.event_type == MISSION_STARTED:
        if mission_id is not None:
            anomalies.append(
                LifecycleAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason="Duplicate MissionStarted (first one wins)",
                )
            )
            return mission_id, mission_status, mission_type, current_phase
        try:
            payload = MissionStartedPayload(**event.payload)
            mission_id = payload.mission_id
            mission_type = payload.mission_type
            mission_status = MissionStatus.ACTIVE
            current_phase = payload.initial_phase
            phases_entered.append(payload.initial_phase)
        except Exception:
            anomalies.append(
                LifecycleAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason="Invalid MissionStarted payload",
                )
            )
        return mission_id, mission_status, mission_type, current_phase

    # Check: event before MissionStarted
    if mission_id is None:
        anomalies.append(
            LifecycleAnomaly(
                event_id=event.event_id,
                event_type=event.event_type,
                reason="Event before MissionStarted",
            )
        )
        return mission_id, mission_status, mission_type, current_phase

    if event.event_type == PHASE_ENTERED:
        try:
            phase_payload = PhaseEnteredPayload(**event.payload)
            current_phase = phase_payload.phase_name
            phases_entered.append(phase_payload.phase_name)
        except Exception:
            anomalies.append(
                LifecycleAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason="Invalid PhaseEntered payload",
                )
            )

    elif event.event_type == MISSION_COMPLETED:
        try:
            MissionCompletedPayload(**event.payload)
            mission_status = MissionStatus.COMPLETED
        except Exception:
            anomalies.append(
                LifecycleAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason="Invalid MissionCompleted payload",
                )
            )

    elif event.event_type == MISSION_CANCELLED:
        try:
            MissionCancelledPayload(**event.payload)
            mission_status = MissionStatus.CANCELLED
        except Exception:
            anomalies.append(
                LifecycleAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason="Invalid MissionCancelled payload",
                )
            )

    elif event.event_type == REVIEW_ROLLBACK:
        try:
            rollback_payload = ReviewRollbackPayload(**event.payload)
            current_phase = rollback_payload.target_phase
            phases_entered.append(rollback_payload.target_phase)
        except Exception:
            anomalies.append(
                LifecycleAnomaly(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    reason="Invalid ReviewRollback payload",
                )
            )

    return mission_id, mission_status, mission_type, current_phase


def reduce_lifecycle_events(events: Sequence[Event]) -> ReducedMissionState:
    """Fold a sequence of lifecycle events into projected mission state.

    Pipeline:
    1. Sort by (lamport_clock, timestamp, event_id)
    2. Deduplicate by event_id
    3. Partition into mission-level and WP-level events
    4. Reduce mission events with cancel-beats-re-open precedence
    5. Delegate WP events to reduce_status_events()
    6. Merge results

    Pure function. No I/O. Deterministic for any causal-order-preserving
    permutation.
    """
    from .status import (
        ReducedStatus,
        dedup_events,
        reduce_status_events,
        status_event_sort_key,
        WP_STATUS_CHANGED,
    )

    if not events:
        return ReducedMissionState(
            mission_id=None,
            mission_status=None,
            mission_type=None,
            current_phase=None,
            phases_entered=(),
            wp_states={},
            anomalies=(),
            event_count=0,
            last_processed_event_id=None,
        )

    # 1. Sort
    sorted_events = sorted(events, key=status_event_sort_key)

    # 2. Dedup
    unique_events = dedup_events(sorted_events)

    # 3. Partition
    mission_events = [
        e for e in unique_events if e.event_type in MISSION_EVENT_TYPES
    ]
    wp_events = [
        e for e in unique_events if e.event_type == WP_STATUS_CHANGED
    ]

    # 4. Reduce mission events with cancel-beats-re-open precedence
    mission_id: Optional[str] = None
    mission_status: Optional[MissionStatus] = None
    mission_type: Optional[str] = None
    current_phase: Optional[str] = None
    phases_entered: List[str] = []
    anomalies: List[LifecycleAnomaly] = []

    # Group by lamport_clock for concurrent group handling
    clock_groups: Dict[int, List[Event]] = {}
    for event in mission_events:
        clock_groups.setdefault(event.lamport_clock, []).append(event)

    for clock in sorted(clock_groups.keys()):
        group = clock_groups[clock]
        # Cancel-beats-re-open: sort so MissionCancelled is applied last
        group.sort(key=_cancel_last_key)
        for event in group:
            mission_id, mission_status, mission_type, current_phase = (
                _process_mission_event(
                    event,
                    mission_id,
                    mission_status,
                    mission_type,
                    current_phase,
                    phases_entered,
                    anomalies,
                )
            )

    # 5. Delegate WP events
    wp_result: ReducedStatus = reduce_status_events(wp_events)

    # 6. Merge: combine WP anomalies as lifecycle anomalies
    wp_anomaly_list: List[LifecycleAnomaly] = []
    for wa in wp_result.anomalies:
        wp_anomaly_list.append(
            LifecycleAnomaly(
                event_id=wa.event_id,
                event_type=WP_STATUS_CHANGED,
                reason=f"WP {wa.wp_id}: {wa.reason}",
            )
        )

    all_anomalies = tuple(anomalies + wp_anomaly_list)

    last_event_id: Optional[str] = None
    if unique_events:
        last_event_id = unique_events[-1].event_id

    return ReducedMissionState(
        mission_id=mission_id,
        mission_status=mission_status,
        mission_type=mission_type,
        current_phase=current_phase,
        phases_entered=tuple(phases_entered),
        wp_states=dict(wp_result.wp_states),
        anomalies=all_anomalies,
        event_count=len(unique_events),
        last_processed_event_id=last_event_id,
    )


# Late import to avoid circular dependency
from .models import Event  # noqa: E402
from .status import WPState  # noqa: E402, F401
