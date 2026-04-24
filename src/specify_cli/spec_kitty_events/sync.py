"""Sync Lifecycle Event Contracts domain module.

Provides enums, event type constants, payload models (with idempotent ingest
markers), the ExternalReferenceLinkedPayload model, the ReducedSyncState
output model, and a deterministic reducer for the Sync Lifecycle contract.

Covers FR-001, FR-002, FR-003, FR-004, FR-005, FR-007.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Sequence, Set, Tuple, Union

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from .models import Event
from .status import dedup_events, status_event_sort_key

# ── Section 1: Schema Version ─────────────────────────────────────────────────

SYNC_SCHEMA_VERSION: str = "2.7.0"

# ── Section 2: Event Type Constants (FR-001) ─────────────────────────────────

SYNC_INGEST_ACCEPTED: str = "SyncIngestAccepted"
SYNC_INGEST_REJECTED: str = "SyncIngestRejected"
SYNC_RETRY_SCHEDULED: str = "SyncRetryScheduled"
SYNC_DEAD_LETTERED: str = "SyncDeadLettered"
SYNC_REPLAY_COMPLETED: str = "SyncReplayCompleted"

SYNC_EVENT_TYPES: FrozenSet[str] = frozenset({
    SYNC_INGEST_ACCEPTED,
    SYNC_INGEST_REJECTED,
    SYNC_RETRY_SCHEDULED,
    SYNC_DEAD_LETTERED,
    SYNC_REPLAY_COMPLETED,
})

# External Reference Linked constant (FR-005)
EXTERNAL_REFERENCE_LINKED: str = "ExternalReferenceLinked"

# ── Section 3: Enums (FR-001) ────────────────────────────────────────────────


class SyncOutcome(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    RETRY_SCHEDULED = "retry_scheduled"
    DEAD_LETTERED = "dead_lettered"
    REPLAY_COMPLETED = "replay_completed"


# Map event types to outcomes
_EVENT_TO_OUTCOME: Dict[str, SyncOutcome] = {
    SYNC_INGEST_ACCEPTED: SyncOutcome.ACCEPTED,
    SYNC_INGEST_REJECTED: SyncOutcome.REJECTED,
    SYNC_RETRY_SCHEDULED: SyncOutcome.RETRY_SCHEDULED,
    SYNC_DEAD_LETTERED: SyncOutcome.DEAD_LETTERED,
    SYNC_REPLAY_COMPLETED: SyncOutcome.REPLAY_COMPLETED,
}

# ── Section 4: Anomaly Model ─────────────────────────────────────────────────


class SyncAnomaly(BaseModel):
    """Non-fatal issue recorded during Sync reduction.

    Valid kind values: "duplicate_delivery_pair", "malformed_payload",
    "unknown_event_type".
    """

    model_config = ConfigDict(frozen=True)

    kind: str
    event_id: str
    message: str


# ── Section 5: Payload Models (FR-002, FR-004) ──────────────────────────────


class SyncIngestAcceptedPayload(BaseModel):
    """Payload for SyncIngestAccepted events."""

    model_config = ConfigDict(frozen=True)

    # Idempotency base fields
    delivery_id: str = Field(..., min_length=1)
    source_event_fingerprint: str = Field(..., min_length=1)
    connector_id: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    recorded_at: datetime
    # Event-specific fields
    ingest_batch_id: str = Field(..., min_length=1)
    ingested_count: int = Field(..., gt=0)


class SyncIngestRejectedPayload(BaseModel):
    """Payload for SyncIngestRejected events."""

    model_config = ConfigDict(frozen=True)

    # Idempotency base fields
    delivery_id: str = Field(..., min_length=1)
    source_event_fingerprint: str = Field(..., min_length=1)
    connector_id: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    recorded_at: datetime
    # Event-specific fields
    rejection_reason: str = Field(..., min_length=1)
    rejected_payload_ref: str = Field(..., min_length=1)


class SyncRetryScheduledPayload(BaseModel):
    """Payload for SyncRetryScheduled events."""

    model_config = ConfigDict(frozen=True)

    # Idempotency base fields
    delivery_id: str = Field(..., min_length=1)
    source_event_fingerprint: str = Field(..., min_length=1)
    connector_id: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    recorded_at: datetime
    # Event-specific fields
    retry_attempt: int = Field(..., ge=1)
    max_retries: int = Field(..., ge=1)
    next_retry_at: datetime


class SyncDeadLetteredPayload(BaseModel):
    """Payload for SyncDeadLettered events."""

    model_config = ConfigDict(frozen=True)

    # Idempotency base fields
    delivery_id: str = Field(..., min_length=1)
    source_event_fingerprint: str = Field(..., min_length=1)
    connector_id: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    recorded_at: datetime
    # Event-specific fields
    failure_reason: str = Field(..., min_length=1)
    total_attempts: int = Field(..., ge=1)
    dead_letter_ref: str = Field(..., min_length=1)


class SyncReplayCompletedPayload(BaseModel):
    """Payload for SyncReplayCompleted events."""

    model_config = ConfigDict(frozen=True)

    # Idempotency base fields
    delivery_id: str = Field(..., min_length=1)
    source_event_fingerprint: str = Field(..., min_length=1)
    connector_id: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    recorded_at: datetime
    # Event-specific fields
    replay_id: str = Field(..., min_length=1)
    replayed_count: int = Field(..., ge=0)
    replay_source: str = Field(..., min_length=1)


# ── Section 6: External Reference Linked Model (FR-005) ─────────────────────


class ExternalReferenceLinkedPayload(BaseModel):
    """Payload for ExternalReferenceLinked events."""

    model_config = ConfigDict(frozen=True)

    link_id: str = Field(..., min_length=1)
    connector_id: str = Field(..., min_length=1)
    external_provider: str = Field(..., min_length=1)
    external_ref_type: str = Field(..., min_length=1)
    external_ref_id: str = Field(..., min_length=1)
    external_ref_url: AnyHttpUrl
    internal_aggregate_type: str = Field(..., min_length=1)
    internal_aggregate_id: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    linked_by: str = Field(..., min_length=1)
    recorded_at: datetime


# Union of all sync payload types
SyncPayload = Union[
    SyncIngestAcceptedPayload,
    SyncIngestRejectedPayload,
    SyncRetryScheduledPayload,
    SyncDeadLetteredPayload,
    SyncReplayCompletedPayload,
]

# Map event types to their payload models
_EVENT_TO_PAYLOAD: Dict[str, type[SyncPayload]] = {
    SYNC_INGEST_ACCEPTED: SyncIngestAcceptedPayload,
    SYNC_INGEST_REJECTED: SyncIngestRejectedPayload,
    SYNC_RETRY_SCHEDULED: SyncRetryScheduledPayload,
    SYNC_DEAD_LETTERED: SyncDeadLetteredPayload,
    SYNC_REPLAY_COMPLETED: SyncReplayCompletedPayload,
}


# ── Section 7: Reducer Output Model ──────────────────────────────────────────


class ReducedSyncState(BaseModel):
    """Deterministic projection output of reduce_sync_events()."""

    model_config = ConfigDict(frozen=True)

    connector_id: Optional[str] = None
    outcome_counts: Dict[str, int] = Field(default_factory=dict)
    outcome_log: Tuple[Tuple[str, str, str], ...] = ()
    seen_delivery_pairs: FrozenSet[Tuple[str, str]] = Field(default_factory=frozenset)
    anomalies: Tuple[SyncAnomaly, ...] = ()
    event_count: int = 0


# ── Section 8: Reducer (FR-007) ──────────────────────────────────────────────


def reduce_sync_events(
    events: Sequence[Event],
) -> ReducedSyncState:
    """Deterministic reducer: Sequence[Event] -> ReducedSyncState.

    Pipeline: sort -> dedup -> filter(SYNC_EVENT_TYPES) -> fold outcomes.

    Idempotent ingest tracking (FR-007):
      Deduplicates on (delivery_id, source_event_fingerprint) pairs.
      If a pair is seen more than once, skip the duplicate and record a SyncAnomaly.
    """
    # Step 1: Sort for determinism
    sorted_events = sorted(events, key=status_event_sort_key)

    # Step 2: Deduplicate by event_id
    deduped = dedup_events(sorted_events)

    # Step 3: Count post-dedup (before filter)
    event_count = len(deduped)

    # Step 4: Filter to Sync family
    sync_events = [e for e in deduped if e.event_type in SYNC_EVENT_TYPES]

    # Step 5: Mutable accumulator for fold
    anomalies: List[SyncAnomaly] = []
    connector_id: Optional[str] = None
    outcome_counts: Dict[str, int] = {
        "accepted_count": 0,
        "rejected_count": 0,
        "retry_count": 0,
        "dead_letter_count": 0,
        "replay_count": 0,
    }
    outcome_log: List[Tuple[str, str, str]] = []
    seen_delivery_pairs: Set[Tuple[str, str]] = set()

    _OUTCOME_TO_COUNT_KEY: Dict[SyncOutcome, str] = {
        SyncOutcome.ACCEPTED: "accepted_count",
        SyncOutcome.REJECTED: "rejected_count",
        SyncOutcome.RETRY_SCHEDULED: "retry_count",
        SyncOutcome.DEAD_LETTERED: "dead_letter_count",
        SyncOutcome.REPLAY_COMPLETED: "replay_count",
    }

    for event in sync_events:
        event_type = event.event_type
        event_id = event.event_id
        payload_dict = event.payload if isinstance(event.payload, dict) else {}

        # Determine outcome from event type
        outcome = _EVENT_TO_OUTCOME.get(event_type)
        if outcome is None:
            anomalies.append(SyncAnomaly(
                kind="unknown_event_type",
                event_id=event_id,
                message=f"Unknown event type in Sync family: {event_type!r}",
            ))
            continue

        # Parse payload
        payload_cls = _EVENT_TO_PAYLOAD[event_type]
        try:
            payload: SyncPayload = payload_cls.model_validate(payload_dict)
        except Exception as exc:
            anomalies.append(SyncAnomaly(
                kind="malformed_payload",
                event_id=event_id,
                message=f"Payload validation failed for {event_type!r}: {exc}",
            ))
            continue

        # Idempotent dedup on (delivery_id, source_event_fingerprint) (FR-007)
        delivery_pair = (
            payload.delivery_id,
            payload.source_event_fingerprint,
        )
        if delivery_pair in seen_delivery_pairs:
            anomalies.append(SyncAnomaly(
                kind="duplicate_delivery_pair",
                event_id=event_id,
                message=(
                    f"Duplicate (delivery_id, source_event_fingerprint) pair: "
                    f"{delivery_pair!r}"
                ),
            ))
            continue

        seen_delivery_pairs.add(delivery_pair)

        # Apply outcome
        connector_id = payload.connector_id
        count_key = _OUTCOME_TO_COUNT_KEY[outcome]
        outcome_counts[count_key] += 1
        outcome_log.append((
            event_id,
            outcome.value,
            payload.delivery_id,
        ))

    # Step 6: Freeze and return
    return ReducedSyncState(
        connector_id=connector_id,
        outcome_counts=outcome_counts,
        outcome_log=tuple(outcome_log),
        seen_delivery_pairs=frozenset(seen_delivery_pairs),
        anomalies=tuple(anomalies),
        event_count=event_count,
    )
