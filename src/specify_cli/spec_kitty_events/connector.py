"""Connector Lifecycle Event Contracts domain module.

Provides enums, event type constants, payload models,
the ReducedConnectorState output model, and a deterministic reducer
for the Connector Lifecycle contract.

Covers FR-001, FR-002, FR-003, FR-006.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple, Union
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from .models import Event
from .status import dedup_events, status_event_sort_key

# ── Section 1: Schema Version ─────────────────────────────────────────────────

CONNECTOR_SCHEMA_VERSION: str = "2.8.0"

# ── Section 2: Event Type Constants (FR-001) ─────────────────────────────────

CONNECTOR_PROVISIONED: str = "ConnectorProvisioned"
CONNECTOR_HEALTH_CHECKED: str = "ConnectorHealthChecked"
CONNECTOR_DEGRADED: str = "ConnectorDegraded"
CONNECTOR_REVOKED: str = "ConnectorRevoked"
CONNECTOR_RECONNECTED: str = "ConnectorReconnected"
USER_CONNECTED: str = "UserConnected"
USER_DISCONNECTED: str = "UserDisconnected"

CONNECTOR_EVENT_TYPES: FrozenSet[str] = frozenset({
    CONNECTOR_PROVISIONED,
    CONNECTOR_HEALTH_CHECKED,
    CONNECTOR_DEGRADED,
    CONNECTOR_REVOKED,
    CONNECTOR_RECONNECTED,
    USER_CONNECTED,
    USER_DISCONNECTED,
})

# User-level event types (skip binding-level state transitions)
_USER_LEVEL_EVENT_TYPES: FrozenSet[str] = frozenset({
    USER_CONNECTED,
    USER_DISCONNECTED,
})

# ── Section 3: Enums (FR-001) ────────────────────────────────────────────────


class ConnectorState(str, Enum):
    PROVISIONED = "provisioned"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    REVOKED = "revoked"
    RECONNECTED = "reconnected"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"


class ReconnectStrategy(str, Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    BACKOFF = "backoff"


# Map event types to states
_EVENT_TO_STATE: Dict[str, ConnectorState] = {
    CONNECTOR_PROVISIONED: ConnectorState.PROVISIONED,
    CONNECTOR_HEALTH_CHECKED: ConnectorState.HEALTHY,
    CONNECTOR_DEGRADED: ConnectorState.DEGRADED,
    CONNECTOR_REVOKED: ConnectorState.REVOKED,
    CONNECTOR_RECONNECTED: ConnectorState.RECONNECTED,
    USER_CONNECTED: ConnectorState.PROVISIONED,
    USER_DISCONNECTED: ConnectorState.REVOKED,
}

# Allowed transitions: from_state -> set of valid to_states (FR-006)
_ALLOWED_TRANSITIONS: Dict[Optional[ConnectorState], FrozenSet[ConnectorState]] = {
    None: frozenset({ConnectorState.PROVISIONED}),
    ConnectorState.PROVISIONED: frozenset({
        ConnectorState.HEALTHY,
        ConnectorState.DEGRADED,
        ConnectorState.REVOKED,
    }),
    ConnectorState.HEALTHY: frozenset({
        ConnectorState.DEGRADED,
        ConnectorState.REVOKED,
    }),
    ConnectorState.DEGRADED: frozenset({
        ConnectorState.HEALTHY,
        ConnectorState.REVOKED,
        ConnectorState.RECONNECTED,
    }),
    ConnectorState.REVOKED: frozenset({
        ConnectorState.RECONNECTED,
    }),
    ConnectorState.RECONNECTED: frozenset({
        ConnectorState.HEALTHY,
        ConnectorState.DEGRADED,
        ConnectorState.REVOKED,
    }),
}

# ── Section 4: Anomaly Model ─────────────────────────────────────────────────


class ConnectorAnomaly(BaseModel):
    """Non-fatal issue recorded during Connector reduction.

    Valid kind values: "invalid_transition", "unknown_event_type",
    "malformed_payload".
    """

    model_config = ConfigDict(frozen=True)

    kind: str
    event_id: str
    message: str


class UserConnectionStatus(BaseModel):
    """Per-user connection state entry in ReducedConnectorState roster."""

    model_config = ConfigDict(frozen=True)

    user_id: str
    state: ConnectorState
    last_event_at: Optional[datetime] = None


# ── Section 5: Payload Models (FR-002) ───────────────────────────────────────


class ConnectorProvisionedPayload(BaseModel):
    """Payload for ConnectorProvisioned events."""

    model_config = ConfigDict(frozen=True)

    connector_id: str = Field(..., min_length=1)
    connector_type: str = Field(..., min_length=1)
    provider: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    project_uuid: UUID
    actor_id: str = Field(..., min_length=1)
    actor_type: str = Field(..., pattern=r"^(human|service|system)$")
    endpoint_url: AnyHttpUrl
    recorded_at: datetime
    credentials_ref: str = Field(..., min_length=1)
    config_hash: str = Field(..., min_length=1)
    user_id: Optional[str] = None


class ConnectorHealthCheckedPayload(BaseModel):
    """Payload for ConnectorHealthChecked events."""

    model_config = ConfigDict(frozen=True)

    connector_id: str = Field(..., min_length=1)
    connector_type: str = Field(..., min_length=1)
    provider: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    project_uuid: UUID
    actor_id: str = Field(..., min_length=1)
    actor_type: str = Field(..., pattern=r"^(human|service|system)$")
    endpoint_url: AnyHttpUrl
    recorded_at: datetime
    health_status: HealthStatus
    latency_ms: float = Field(..., ge=0)
    user_id: Optional[str] = None


class ConnectorDegradedPayload(BaseModel):
    """Payload for ConnectorDegraded events."""

    model_config = ConfigDict(frozen=True)

    connector_id: str = Field(..., min_length=1)
    connector_type: str = Field(..., min_length=1)
    provider: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    project_uuid: UUID
    actor_id: str = Field(..., min_length=1)
    actor_type: str = Field(..., pattern=r"^(human|service|system)$")
    endpoint_url: AnyHttpUrl
    recorded_at: datetime
    degradation_reason: str = Field(..., min_length=1)
    last_healthy_at: datetime
    user_id: Optional[str] = None


class ConnectorRevokedPayload(BaseModel):
    """Payload for ConnectorRevoked events."""

    model_config = ConfigDict(frozen=True)

    connector_id: str = Field(..., min_length=1)
    connector_type: str = Field(..., min_length=1)
    provider: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    project_uuid: UUID
    actor_id: str = Field(..., min_length=1)
    actor_type: str = Field(..., pattern=r"^(human|service|system)$")
    endpoint_url: AnyHttpUrl
    recorded_at: datetime
    revocation_reason: str = Field(..., min_length=1)
    user_id: Optional[str] = None


class ConnectorReconnectedPayload(BaseModel):
    """Payload for ConnectorReconnected events."""

    model_config = ConfigDict(frozen=True)

    connector_id: str = Field(..., min_length=1)
    connector_type: str = Field(..., min_length=1)
    provider: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    project_uuid: UUID
    actor_id: str = Field(..., min_length=1)
    actor_type: str = Field(..., pattern=r"^(human|service|system)$")
    endpoint_url: AnyHttpUrl
    recorded_at: datetime
    previous_state: ConnectorState
    reconnect_strategy: ReconnectStrategy
    user_id: Optional[str] = None


class UserConnectedPayload(BaseModel):
    """Payload for UserConnected events."""

    model_config = ConfigDict(frozen=True)

    connector_id: str = Field(..., min_length=1)
    connector_type: str = Field(..., min_length=1)
    provider: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    project_uuid: UUID
    actor_id: str = Field(..., min_length=1)
    actor_type: str = Field(..., pattern=r"^(human|service|system)$")
    endpoint_url: AnyHttpUrl
    recorded_at: datetime
    user_id: str = Field(..., min_length=1)


class UserDisconnectedPayload(BaseModel):
    """Payload for UserDisconnected events."""

    model_config = ConfigDict(frozen=True)

    connector_id: str = Field(..., min_length=1)
    connector_type: str = Field(..., min_length=1)
    provider: str = Field(..., min_length=1)
    mission_id: str = Field(..., min_length=1)
    project_uuid: UUID
    actor_id: str = Field(..., min_length=1)
    actor_type: str = Field(..., pattern=r"^(human|service|system)$")
    endpoint_url: AnyHttpUrl
    recorded_at: datetime
    user_id: str = Field(..., min_length=1)
    reason: str = ""


# Union of all connector payload types
ConnectorPayload = Union[
    ConnectorProvisionedPayload,
    ConnectorHealthCheckedPayload,
    ConnectorDegradedPayload,
    ConnectorRevokedPayload,
    ConnectorReconnectedPayload,
    UserConnectedPayload,
    UserDisconnectedPayload,
]

# Map event types to their payload models
_EVENT_TO_PAYLOAD: Dict[str, type[ConnectorPayload]] = {
    CONNECTOR_PROVISIONED: ConnectorProvisionedPayload,
    CONNECTOR_HEALTH_CHECKED: ConnectorHealthCheckedPayload,
    CONNECTOR_DEGRADED: ConnectorDegradedPayload,
    CONNECTOR_REVOKED: ConnectorRevokedPayload,
    CONNECTOR_RECONNECTED: ConnectorReconnectedPayload,
    USER_CONNECTED: UserConnectedPayload,
    USER_DISCONNECTED: UserDisconnectedPayload,
}

# ── Section 6: Reducer Output Model ──────────────────────────────────────────


class ReducedConnectorState(BaseModel):
    """Deterministic projection output of reduce_connector_events()."""

    model_config = ConfigDict(frozen=True)

    connector_id: Optional[str] = None
    current_state: Optional[ConnectorState] = None
    provider: Optional[str] = None
    last_health_check: Optional[datetime] = None
    anomalies: Tuple[ConnectorAnomaly, ...] = ()
    event_count: int = 0
    transition_log: Tuple[Tuple[str, str], ...] = ()
    user_connections: Tuple[UserConnectionStatus, ...] = ()


# ── Section 7: Reducer (FR-006) ──────────────────────────────────────────────


def reduce_connector_events(
    events: Sequence[Event],
) -> ReducedConnectorState:
    """Deterministic reducer: Sequence[Event] -> ReducedConnectorState.

    Pipeline: sort -> dedup -> filter(CONNECTOR_EVENT_TYPES) -> fold -> freeze.

    Transition rules (FR-006):
      None -> provisioned
      provisioned -> healthy | degraded | revoked
      healthy -> degraded | revoked
      degraded -> healthy | revoked | reconnected
      revoked -> reconnected
      reconnected -> healthy | degraded | revoked

    User-level events (UserConnected, UserDisconnected) update the per-user
    roster only and do not participate in binding-level state transitions.
    """
    # Step 1: Sort for determinism
    sorted_events = sorted(events, key=status_event_sort_key)

    # Step 2: Deduplicate by event_id
    deduped = dedup_events(sorted_events)

    # Step 3: Count post-dedup (before filter)
    event_count = len(deduped)

    # Step 4: Filter to Connector family
    conn_events = [e for e in deduped if e.event_type in CONNECTOR_EVENT_TYPES]

    # Step 5: Mutable accumulator for fold
    anomalies: List[ConnectorAnomaly] = []
    current_state: Optional[ConnectorState] = None
    connector_id: Optional[str] = None
    provider: Optional[str] = None
    last_health_check: Optional[datetime] = None
    transition_log: List[Tuple[str, str]] = []
    user_roster: Dict[str, Tuple[ConnectorState, Optional[datetime]]] = {}

    for event in conn_events:
        event_type = event.event_type
        event_id = event.event_id
        payload_dict = event.payload if isinstance(event.payload, dict) else {}

        # Determine target state from event type
        target_state = _EVENT_TO_STATE.get(event_type)
        if target_state is None:
            anomalies.append(ConnectorAnomaly(
                kind="unknown_event_type",
                event_id=event_id,
                message=f"Unknown event type in Connector family: {event_type!r}",
            ))
            continue

        # Parse payload
        payload_cls = _EVENT_TO_PAYLOAD[event_type]
        try:
            payload: ConnectorPayload = payload_cls.model_validate(payload_dict)
        except Exception as exc:
            anomalies.append(ConnectorAnomaly(
                kind="malformed_payload",
                event_id=event_id,
                message=f"Payload validation failed for {event_type!r}: {exc}",
            ))
            continue

        # User-level events: update roster only, skip binding-level transitions
        if event_type in _USER_LEVEL_EVENT_TYPES:
            user_id_val = getattr(payload, "user_id", None)
            if isinstance(user_id_val, str) and user_id_val:
                if event_type == USER_DISCONNECTED and user_id_val not in user_roster:
                    anomalies.append(ConnectorAnomaly(
                        kind="invalid_transition",
                        event_id=event_id,
                        message=(
                            f"UserDisconnected for user {user_id_val!r} "
                            f"who has no prior connection event"
                        ),
                    ))
                user_roster[user_id_val] = (
                    target_state,
                    payload.recorded_at,
                )
            continue

        # Check: valid binding-level transition
        allowed = _ALLOWED_TRANSITIONS.get(current_state, frozenset())
        if target_state not in allowed:
            anomalies.append(ConnectorAnomaly(
                kind="invalid_transition",
                event_id=event_id,
                message=(
                    f"Invalid transition: "
                    f"{current_state.value if current_state else 'None'} "
                    f"-> {target_state.value}"
                ),
            ))
            continue

        # Apply binding-level transition
        current_state = target_state
        connector_id = payload.connector_id
        provider = payload.provider
        transition_log.append((event_id, target_state.value))

        # Track health checks
        if isinstance(payload, ConnectorHealthCheckedPayload):
            last_health_check = payload.recorded_at

        # Update per-user roster if user_id is present on binding-level event
        payload_user_id = getattr(payload, "user_id", None)
        if isinstance(payload_user_id, str) and payload_user_id:
            user_roster[payload_user_id] = (target_state, payload.recorded_at)

    # Step 6: Freeze and return
    frozen_roster = tuple(
        UserConnectionStatus(user_id=uid, state=st, last_event_at=ts)
        for uid, (st, ts) in sorted(user_roster.items())
    )

    return ReducedConnectorState(
        connector_id=connector_id,
        current_state=current_state,
        provider=provider,
        last_health_check=last_health_check,
        anomalies=tuple(anomalies),
        event_count=event_count,
        transition_log=tuple(transition_log),
        user_connections=frozen_roster,
    )
