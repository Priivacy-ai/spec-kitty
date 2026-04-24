"""Collaboration event contracts for Feature 006.

Defines event type constants, identity models, payload models,
reducer output models, and the collaboration reducer for
multi-participant mission coordination.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, FrozenSet, List, Literal, Optional, Sequence, Set, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import SpecKittyEventsError

# ── Section 1: Constants ─────────────────────────────────────────────────────

PARTICIPANT_INVITED: str = "ParticipantInvited"
PARTICIPANT_JOINED: str = "ParticipantJoined"
PARTICIPANT_LEFT: str = "ParticipantLeft"
PRESENCE_HEARTBEAT: str = "PresenceHeartbeat"
DRIVE_INTENT_SET: str = "DriveIntentSet"
FOCUS_CHANGED: str = "FocusChanged"
PROMPT_STEP_EXECUTION_STARTED: str = "PromptStepExecutionStarted"
PROMPT_STEP_EXECUTION_COMPLETED: str = "PromptStepExecutionCompleted"
CONCURRENT_DRIVER_WARNING: str = "ConcurrentDriverWarning"
POTENTIAL_STEP_COLLISION_DETECTED: str = "PotentialStepCollisionDetected"
WARNING_ACKNOWLEDGED: str = "WarningAcknowledged"
COMMENT_POSTED: str = "CommentPosted"
DECISION_CAPTURED: str = "DecisionCaptured"
SESSION_LINKED: str = "SessionLinked"

COLLABORATION_EVENT_TYPES: FrozenSet[str] = frozenset({
    PARTICIPANT_INVITED,
    PARTICIPANT_JOINED,
    PARTICIPANT_LEFT,
    PRESENCE_HEARTBEAT,
    DRIVE_INTENT_SET,
    FOCUS_CHANGED,
    PROMPT_STEP_EXECUTION_STARTED,
    PROMPT_STEP_EXECUTION_COMPLETED,
    CONCURRENT_DRIVER_WARNING,
    POTENTIAL_STEP_COLLISION_DETECTED,
    WARNING_ACKNOWLEDGED,
    COMMENT_POSTED,
    DECISION_CAPTURED,
    SESSION_LINKED,
})

# ── Section 2: Identity and Target Models ────────────────────────────────────


class ParticipantExternalRefs(BaseModel):
    """Optional cross-channel identity references for a ParticipantIdentity."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    slack_user_id: Optional[str] = Field(None, min_length=1)
    slack_team_id: Optional[str] = Field(None, min_length=1)
    teamspace_member_id: Optional[str] = Field(None, min_length=1)

    @model_validator(mode="after")
    def _at_least_one(self) -> "ParticipantExternalRefs":
        if not any((self.slack_user_id, self.slack_team_id, self.teamspace_member_id)):
            raise ValueError(
                "ParticipantExternalRefs must populate at least one of "
                "slack_user_id, slack_team_id, teamspace_member_id"
            )
        return self


class ParticipantIdentity(BaseModel):
    """SaaS-minted, mission-scoped participant identity."""

    model_config = ConfigDict(frozen=True)

    participant_id: str = Field(
        ..., min_length=1, description="SaaS-minted, mission-scoped unique identifier"
    )
    participant_type: Literal["human", "llm_context"] = Field(
        ..., description="Participant category"
    )
    display_name: Optional[str] = Field(
        None, description="Human-readable name for display"
    )
    session_id: Optional[str] = Field(
        None, description="SaaS-issued session identifier"
    )
    external_refs: Optional[ParticipantExternalRefs] = Field(
        None, description="Optional cross-channel identity references (V1)"
    )


class AuthPrincipalBinding(BaseModel):
    """Roster-level auth principal to participant binding."""

    model_config = ConfigDict(frozen=True)

    auth_principal_id: str = Field(
        ..., min_length=1, description="Authenticated identity (opaque to this package)"
    )
    participant_id: str = Field(
        ..., min_length=1, description="Mission-scoped participant identifier"
    )
    bound_at: datetime = Field(
        ..., description="Timestamp when binding was created"
    )


class FocusTarget(BaseModel):
    """Structured focus reference. Hashable for use as dict key."""

    model_config = ConfigDict(frozen=True)

    target_type: Literal["wp", "step", "file"] = Field(
        ..., description="Category of focus target"
    )
    target_id: str = Field(
        ..., min_length=1, description="Identifier within the target type"
    )


class UnknownParticipantError(SpecKittyEventsError):
    """Raised in strict mode for events from non-rostered participants."""

    def __init__(
        self, participant_id: str, event_id: str, event_type: str
    ) -> None:
        self.participant_id = participant_id
        self.event_id = event_id
        self.event_type = event_type
        super().__init__(
            f"Unknown participant {participant_id!r} in event {event_id} "
            f"(type={event_type}). Not in mission roster."
        )


# ── Section 3: Payload Models ──  (populated by WP02-WP04)


class ParticipantInvitedPayload(BaseModel):
    """Typed payload for ParticipantInvited events."""

    model_config = ConfigDict(frozen=True)

    participant_id: str = Field(
        ..., min_length=1, description="Invited participant"
    )
    participant_identity: ParticipantIdentity = Field(
        ..., description="Full structured identity"
    )
    invited_by: str = Field(
        ..., min_length=1, description="participant_id of inviter"
    )
    mission_id: str = Field(
        ..., min_length=1, description="Target mission"
    )


class ParticipantJoinedPayload(BaseModel):
    """Typed payload for ParticipantJoined events."""

    model_config = ConfigDict(frozen=True)

    participant_id: str = Field(
        ..., min_length=1, description="Joining participant"
    )
    participant_identity: ParticipantIdentity = Field(
        ..., description="Full structured identity"
    )
    mission_id: str = Field(
        ..., min_length=1, description="Target mission"
    )
    auth_principal_id: Optional[str] = Field(
        None, description="Auth principal bound at join time (present in live traffic)"
    )


class ParticipantLeftPayload(BaseModel):
    """Typed payload for ParticipantLeft events."""

    model_config = ConfigDict(frozen=True)

    participant_id: str = Field(
        ..., min_length=1, description="Departing participant"
    )
    mission_id: str = Field(
        ..., min_length=1, description="Mission being left"
    )
    reason: Optional[str] = Field(
        None, description="Departure reason (e.g., 'disconnect', 'explicit')"
    )


class PresenceHeartbeatPayload(BaseModel):
    """Typed payload for PresenceHeartbeat events."""

    model_config = ConfigDict(frozen=True)

    participant_id: str = Field(
        ..., min_length=1, description="Heartbeat source"
    )
    mission_id: str = Field(
        ..., min_length=1, description="Mission context"
    )
    session_id: Optional[str] = Field(
        None, description="Specific session sending heartbeat"
    )


class DriveIntentSetPayload(BaseModel):
    """Typed payload for DriveIntentSet events."""

    model_config = ConfigDict(frozen=True)

    participant_id: str = Field(
        ..., min_length=1, description="Participant declaring intent"
    )
    mission_id: str = Field(
        ..., min_length=1, description="Mission context"
    )
    intent: Literal["active", "inactive"] = Field(
        ..., description="Drive intent state"
    )


class FocusChangedPayload(BaseModel):
    """Typed payload for FocusChanged events."""

    model_config = ConfigDict(frozen=True)

    participant_id: str = Field(
        ..., min_length=1, description="Participant changing focus"
    )
    mission_id: str = Field(
        ..., min_length=1, description="Mission context"
    )
    focus_target: FocusTarget = Field(
        ..., description="New focus target"
    )
    previous_focus_target: Optional[FocusTarget] = Field(
        None, description="Previous focus (if any)"
    )


class PromptStepExecutionStartedPayload(BaseModel):
    """Typed payload for PromptStepExecutionStarted events."""

    model_config = ConfigDict(frozen=True)

    participant_id: str = Field(
        ..., min_length=1, description="Executing participant"
    )
    mission_id: str = Field(
        ..., min_length=1, description="Mission context"
    )
    step_id: str = Field(
        ..., min_length=1, description="Step identifier"
    )
    wp_id: Optional[str] = Field(
        None, description="Work package being targeted"
    )
    step_description: Optional[str] = Field(
        None, description="Human-readable step description"
    )


class PromptStepExecutionCompletedPayload(BaseModel):
    """Typed payload for PromptStepExecutionCompleted events."""

    model_config = ConfigDict(frozen=True)

    participant_id: str = Field(
        ..., min_length=1, description="Completing participant"
    )
    mission_id: str = Field(
        ..., min_length=1, description="Mission context"
    )
    step_id: str = Field(
        ..., min_length=1, description="Step identifier"
    )
    wp_id: Optional[str] = Field(
        None, description="Work package targeted"
    )
    outcome: Literal["success", "failure", "skipped"] = Field(
        ..., description="Step outcome"
    )


class ConcurrentDriverWarningPayload(BaseModel):
    """Typed payload for ConcurrentDriverWarning events."""

    model_config = ConfigDict(frozen=True)

    warning_id: str = Field(
        ..., min_length=1, description="Unique warning identifier"
    )
    mission_id: str = Field(
        ..., min_length=1, description="Mission context"
    )
    participant_ids: List[str] = Field(
        ..., min_length=2, description="All concurrent active drivers on overlapping target"
    )
    focus_target: FocusTarget = Field(
        ..., description="Shared focus target triggering warning"
    )
    severity: Literal["info", "warning"] = Field(
        ..., description="Warning severity level"
    )


class PotentialStepCollisionDetectedPayload(BaseModel):
    """Typed payload for PotentialStepCollisionDetected events."""

    model_config = ConfigDict(frozen=True)

    warning_id: str = Field(
        ..., min_length=1, description="Unique warning identifier"
    )
    mission_id: str = Field(
        ..., min_length=1, description="Mission context"
    )
    participant_ids: List[str] = Field(
        ..., min_length=2, description="Colliding participants"
    )
    step_id: str = Field(
        ..., min_length=1, description="Colliding step"
    )
    wp_id: Optional[str] = Field(
        None, description="Work package context"
    )
    severity: Literal["info", "warning"] = Field(
        ..., description="Warning severity level"
    )


class WarningAcknowledgedPayload(BaseModel):
    """Typed payload for WarningAcknowledged events."""

    model_config = ConfigDict(frozen=True)

    participant_id: str = Field(
        ..., min_length=1, description="Acknowledging participant"
    )
    mission_id: str = Field(
        ..., min_length=1, description="Mission context"
    )
    warning_id: str = Field(
        ..., min_length=1, description="Warning being acknowledged"
    )
    acknowledgement: Literal["continue", "hold", "reassign", "defer"] = Field(
        ..., description="Response action"
    )


class CommentPostedPayload(BaseModel):
    """Typed payload for CommentPosted events."""

    model_config = ConfigDict(frozen=True)

    participant_id: str = Field(
        ..., min_length=1, description="Comment author"
    )
    mission_id: str = Field(
        ..., min_length=1, description="Mission context"
    )
    comment_id: str = Field(
        ..., min_length=1, description="Unique comment identifier"
    )
    content: str = Field(
        ..., min_length=1, description="Comment text"
    )
    reply_to: Optional[str] = Field(
        None, description="Parent comment_id for threading"
    )


class DecisionCapturedPayload(BaseModel):
    """Typed payload for DecisionCaptured events."""

    model_config = ConfigDict(frozen=True)

    participant_id: str = Field(
        ..., min_length=1, description="Decision author"
    )
    mission_id: str = Field(
        ..., min_length=1, description="Mission context"
    )
    decision_id: str = Field(
        ..., min_length=1, description="Unique decision identifier"
    )
    topic: str = Field(
        ..., min_length=1, description="Decision topic/question"
    )
    chosen_option: str = Field(
        ..., min_length=1, description="Selected option"
    )
    rationale: Optional[str] = Field(
        None, description="Reasoning for the decision"
    )
    referenced_warning_id: Optional[str] = Field(
        None, description="Warning that prompted this decision"
    )


class SessionLinkedPayload(BaseModel):
    """Typed payload for SessionLinked events."""

    model_config = ConfigDict(frozen=True)

    participant_id: str = Field(
        ..., min_length=1, description="Participant linking sessions"
    )
    mission_id: str = Field(
        ..., min_length=1, description="Mission context"
    )
    primary_session_id: str = Field(
        ..., min_length=1, description="Primary session"
    )
    linked_session_id: str = Field(
        ..., min_length=1, description="Session being linked"
    )
    link_type: Literal["cli_to_saas", "saas_to_cli"] = Field(
        ..., description="Direction of link"
    )


# ── Section 4: Reducer Output Models ──────────────────────────────────────


class CollaborationAnomaly(BaseModel):
    """Non-fatal issue encountered during collaboration event reduction."""

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(..., description="Event that caused the anomaly")
    event_type: str = Field(..., description="Type of the problematic event")
    reason: str = Field(..., description="Human-readable anomaly description")


class WarningEntry(BaseModel):
    """Warning timeline entry in reduced collaboration state."""

    model_config = ConfigDict(frozen=True)

    warning_id: str = Field(..., description="Warning identifier")
    event_id: str = Field(..., description="Event that created this warning")
    warning_type: str = Field(
        ...,
        description="'ConcurrentDriverWarning' or 'PotentialStepCollisionDetected'",
    )
    participant_ids: Tuple[str, ...] = Field(
        ..., description="Affected participants"
    )
    acknowledgements: Dict[str, str] = Field(
        default_factory=dict,
        description="participant_id -> acknowledgement action",
    )


class DecisionEntry(BaseModel):
    """Decision history entry in reduced collaboration state."""

    model_config = ConfigDict(frozen=True)

    decision_id: str = Field(..., description="Decision identifier")
    event_id: str = Field(..., description="Event that captured this decision")
    participant_id: str = Field(..., description="Decision author")
    topic: str = Field(..., description="Decision topic")
    chosen_option: str = Field(..., description="Selected option")
    referenced_warning_id: Optional[str] = Field(
        None, description="Related warning"
    )


class CommentEntry(BaseModel):
    """Comment history entry in reduced collaboration state."""

    model_config = ConfigDict(frozen=True)

    comment_id: str = Field(..., description="Comment identifier")
    event_id: str = Field(..., description="Event that posted this comment")
    participant_id: str = Field(..., description="Comment author")
    content: str = Field(..., description="Comment text")
    reply_to: Optional[str] = Field(None, description="Parent comment_id")


class ReducedCollaborationState(BaseModel):
    """Materialized collaboration state from event reduction."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(
        ..., description="Mission this state represents"
    )
    participants: Dict[str, ParticipantIdentity] = Field(
        default_factory=dict,
        description="Active participant roster (participant_id -> identity)",
    )
    departed_participants: Dict[str, ParticipantIdentity] = Field(
        default_factory=dict,
        description="Historical departed participants",
    )
    presence: Dict[str, datetime] = Field(
        default_factory=dict,
        description="Last heartbeat timestamp per participant_id",
    )
    active_drivers: FrozenSet[str] = Field(
        default_factory=frozenset,
        description="participant_ids with active drive intent",
    )
    focus_by_participant: Dict[str, FocusTarget] = Field(
        default_factory=dict,
        description="Current focus per participant",
    )
    participants_by_focus: Dict[str, FrozenSet[str]] = Field(
        default_factory=dict,
        description="Reverse index: focus_key -> participant set",
    )
    warnings: Tuple[WarningEntry, ...] = Field(
        default_factory=tuple,
        description="Ordered warning timeline",
    )
    decisions: Tuple[DecisionEntry, ...] = Field(
        default_factory=tuple,
        description="Ordered decision history",
    )
    comments: Tuple[CommentEntry, ...] = Field(
        default_factory=tuple,
        description="Ordered comment history",
    )
    active_executions: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="In-flight step_ids per participant_id",
    )
    linked_sessions: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Linked session_ids per participant_id",
    )
    anomalies: Tuple[CollaborationAnomaly, ...] = Field(
        default_factory=tuple,
        description="Non-fatal issues encountered",
    )
    event_count: int = Field(
        default=0, description="Total events processed"
    )
    last_processed_event_id: Optional[str] = Field(
        None, description="Last event_id in processed sequence"
    )


# ── Section 5: Collaboration Reducer ──────────────────────────────────────


def _focus_key(target: FocusTarget) -> str:
    """Build a string key for the participants_by_focus reverse index."""
    return f"{target.target_type}:{target.target_id}"


def reduce_collaboration_events(
    events: Sequence[Event],
    *,
    mode: Literal["strict", "permissive"] = "strict",
    roster: Optional[Dict[str, ParticipantIdentity]] = None,
) -> ReducedCollaborationState:
    """Fold collaboration events into projected collaboration state.

    Pipeline:
    1. Filter to collaboration event types only
    2. Sort by (lamport_clock, timestamp, event_id)
    3. Deduplicate by event_id
    4. Process each event, mutating intermediate state
    5. Assemble frozen ReducedCollaborationState

    Pure function. No I/O. Deterministic for any causal-order-preserving
    permutation.

    Args:
        events: Sequence of Event instances (may include non-collaboration types).
        mode: ``"strict"`` raises UnknownParticipantError for non-rostered
            participants. ``"permissive"`` records anomalies instead.
        roster: Optional seeded participant roster. When provided, participants
            are pre-populated and events can reference them without a prior
            ParticipantJoined event.

    Returns:
        A frozen ReducedCollaborationState reflecting the processed events.

    Raises:
        UnknownParticipantError: In strict mode, when an event references a
            participant not in the active roster.
        SpecKittyEventsError: In strict mode, for reducer integrity violations
            such as acknowledgement of unknown warning IDs or completion
            without a matching started execution.
    """
    from .status import dedup_events, status_event_sort_key

    if not events:
        return ReducedCollaborationState(mission_id="", last_processed_event_id=None)

    # 1. Filter
    collab_events = [e for e in events if e.event_type in COLLABORATION_EVENT_TYPES]

    if not collab_events:
        return ReducedCollaborationState(mission_id="", last_processed_event_id=None)

    # 2. Sort
    sorted_events = sorted(collab_events, key=status_event_sort_key)

    # 3. Dedup
    unique_events = dedup_events(sorted_events)

    # -- Mutable intermediate state --
    participants: Dict[str, ParticipantIdentity] = {}
    invited_participants: Dict[str, ParticipantIdentity] = {}
    departed_participants: Dict[str, ParticipantIdentity] = {}
    presence: Dict[str, datetime] = {}
    active_drivers: Set[str] = set()
    focus_by_participant: Dict[str, FocusTarget] = {}
    participants_by_focus: Dict[str, Set[str]] = {}
    warning_map: Dict[str, _MutableWarningEntry] = {}
    decisions: List[DecisionEntry] = []
    comments: List[CommentEntry] = []
    active_executions: Dict[str, List[str]] = {}
    linked_sessions: Dict[str, List[str]] = {}
    anomalies: List[CollaborationAnomaly] = []

    # Seed roster if provided
    if roster is not None:
        for pid, identity in roster.items():
            participants[pid] = identity

    # Extract mission_id from first event's payload
    first_payload = unique_events[0].payload
    mission_id: str = ""
    if isinstance(first_payload, dict):
        raw_mid = first_payload.get("mission_id")
        if isinstance(raw_mid, str) and raw_mid:
            mission_id = raw_mid

    # -- Helper functions --

    def _check_active_participant(
        participant_id: str, event_id: str, event_type: str
    ) -> bool:
        """Check participant is in active roster. Returns True if valid."""
        if participant_id in participants:
            return True
        if participant_id in departed_participants:
            if mode == "strict":
                raise SpecKittyEventsError(
                    f"Participant {participant_id!r} has departed "
                    f"(event_id={event_id}, event_type={event_type})"
                )
            anomalies.append(
                CollaborationAnomaly(
                    event_id=event_id,
                    event_type=event_type,
                    reason=f"Participant {participant_id!r} has departed",
                )
            )
            return False
        if mode == "strict":
            raise UnknownParticipantError(participant_id, event_id, event_type)
        anomalies.append(
            CollaborationAnomaly(
                event_id=event_id,
                event_type=event_type,
                reason=f"Unknown participant {participant_id!r}",
            )
        )
        return False

    def _check_active_participants(
        participant_ids: List[str], event_id: str, event_type: str
    ) -> bool:
        """Check all participant_ids are in roster. Returns True if all valid."""
        all_valid = True
        for pid in participant_ids:
            if not _check_active_participant(pid, event_id, event_type):
                all_valid = False
        return all_valid

    def _remove_from_focus_index(pid: str) -> None:
        """Remove participant from the focus reverse index."""
        old_focus = focus_by_participant.get(pid)
        if old_focus is not None:
            key = _focus_key(old_focus)
            focus_set = participants_by_focus.get(key)
            if focus_set is not None:
                focus_set.discard(pid)
                if not focus_set:
                    del participants_by_focus[key]

    # 4. Process each event
    for event in unique_events:
        et = event.event_type
        payload = event.payload if isinstance(event.payload, dict) else {}

        if et == PARTICIPANT_INVITED:
            # Invitation is pre-activation metadata; it does not activate roster membership.
            pid = payload.get("participant_id", "")
            if not isinstance(pid, str) or not pid:
                anomalies.append(
                    CollaborationAnomaly(
                        event_id=event.event_id,
                        event_type=et,
                        reason="Missing participant_id in payload",
                    )
                )
                continue
            try:
                identity_data = payload.get("participant_identity", {})
                identity = ParticipantIdentity(**identity_data)
            except Exception:
                anomalies.append(
                    CollaborationAnomaly(
                        event_id=event.event_id,
                        event_type=et,
                        reason="Invalid participant_identity in payload",
                    )
                )
                continue
            if pid in participants or pid in invited_participants:
                anomalies.append(
                    CollaborationAnomaly(
                        event_id=event.event_id,
                        event_type=et,
                        reason=f"Participant {pid!r} already invited or active (duplicate invite)",
                    )
                )
                continue
            invited_participants[pid] = identity

        elif et == PARTICIPANT_JOINED:
            pid = payload.get("participant_id", "")
            if not isinstance(pid, str) or not pid:
                anomalies.append(
                    CollaborationAnomaly(
                        event_id=event.event_id,
                        event_type=et,
                        reason="Missing participant_id in payload",
                    )
                )
                continue
            try:
                identity_data = payload.get("participant_identity", {})
                identity = ParticipantIdentity(**identity_data)
            except Exception:
                anomalies.append(
                    CollaborationAnomaly(
                        event_id=event.event_id,
                        event_type=et,
                        reason="Invalid participant_identity in payload",
                    )
                )
                continue
            if pid in participants and pid not in departed_participants:
                # Duplicate join
                anomalies.append(
                    CollaborationAnomaly(
                        event_id=event.event_id,
                        event_type=et,
                        reason=f"Duplicate join for participant {pid!r}",
                    )
                )
                continue
            # Re-join after leave: remove from departed
            if pid in departed_participants:
                del departed_participants[pid]
            if pid in invited_participants:
                del invited_participants[pid]
            participants[pid] = identity

        elif et == PARTICIPANT_LEFT:
            pid = payload.get("participant_id", "")
            if not isinstance(pid, str) or not pid:
                anomalies.append(
                    CollaborationAnomaly(
                        event_id=event.event_id,
                        event_type=et,
                        reason="Missing participant_id in payload",
                    )
                )
                continue
            if pid not in participants:
                # Duplicate leave or unknown
                anomalies.append(
                    CollaborationAnomaly(
                        event_id=event.event_id,
                        event_type=et,
                        reason=f"Participant {pid!r} not in roster (duplicate leave or unknown)",
                    )
                )
                continue
            # Move to departed
            departed_participants[pid] = participants.pop(pid)
            # Clean up state
            active_drivers.discard(pid)
            _remove_from_focus_index(pid)
            focus_by_participant.pop(pid, None)
            presence.pop(pid, None)
            active_executions.pop(pid, None)

        elif et == PRESENCE_HEARTBEAT:
            pid = payload.get("participant_id", "")
            if not isinstance(pid, str) or not pid:
                continue
            if pid in departed_participants and pid not in participants:
                if mode == "strict":
                    raise SpecKittyEventsError(
                        f"Participant {pid!r} has departed "
                        f"(event_id={event.event_id}, event_type={et})"
                    )
                anomalies.append(
                    CollaborationAnomaly(
                        event_id=event.event_id,
                        event_type=et,
                        reason=f"Participant {pid!r} has departed",
                    )
                )
                # Permissive mode keeps the timestamp for replay/import forensics.
                presence[pid] = event.timestamp
                continue
            if not _check_active_participant(pid, event.event_id, et):
                continue
            presence[pid] = event.timestamp

        elif et == DRIVE_INTENT_SET:
            pid = payload.get("participant_id", "")
            if not isinstance(pid, str) or not pid:
                continue
            if not _check_active_participant(pid, event.event_id, et):
                continue
            intent = payload.get("intent")
            if intent == "active":
                active_drivers.add(pid)
            elif intent == "inactive":
                active_drivers.discard(pid)

        elif et == FOCUS_CHANGED:
            pid = payload.get("participant_id", "")
            if not isinstance(pid, str) or not pid:
                continue
            if not _check_active_participant(pid, event.event_id, et):
                continue
            try:
                focus_data = payload.get("focus_target", {})
                focus_target = FocusTarget(**focus_data)
            except Exception:
                anomalies.append(
                    CollaborationAnomaly(
                        event_id=event.event_id,
                        event_type=et,
                        reason="Invalid focus_target in payload",
                    )
                )
                continue
            # Remove old focus index entry
            _remove_from_focus_index(pid)
            # Set new focus
            focus_by_participant[pid] = focus_target
            key = _focus_key(focus_target)
            if key not in participants_by_focus:
                participants_by_focus[key] = set()
            participants_by_focus[key].add(pid)

        elif et == PROMPT_STEP_EXECUTION_STARTED:
            pid = payload.get("participant_id", "")
            step_id = payload.get("step_id", "")
            if not isinstance(pid, str) or not pid:
                continue
            if not _check_active_participant(pid, event.event_id, et):
                continue
            if pid not in active_executions:
                active_executions[pid] = []
            active_executions[pid].append(step_id)

        elif et == PROMPT_STEP_EXECUTION_COMPLETED:
            pid = payload.get("participant_id", "")
            step_id = payload.get("step_id", "")
            if not isinstance(pid, str) or not pid:
                continue
            if not _check_active_participant(pid, event.event_id, et):
                continue
            # Check matching started exists
            pid_execs = active_executions.get(pid, [])
            if step_id not in pid_execs:
                if mode == "strict":
                    raise SpecKittyEventsError(
                        f"No matching PromptStepExecutionStarted for step {step_id!r} "
                        f"by participant {pid!r} "
                        f"(event_id={event.event_id}, event_type={et})"
                    )
                anomalies.append(
                    CollaborationAnomaly(
                        event_id=event.event_id,
                        event_type=et,
                        reason=(
                            f"No matching PromptStepExecutionStarted for "
                            f"step {step_id!r} by participant {pid!r}"
                        ),
                    )
                )
                continue
            pid_execs.remove(step_id)

        elif et == CONCURRENT_DRIVER_WARNING:
            warning_id = payload.get("warning_id", "")
            pids = payload.get("participant_ids", [])
            if not isinstance(warning_id, str) or not warning_id:
                continue
            if not isinstance(pids, list):
                continue
            _check_active_participants(pids, event.event_id, et)
            existing = warning_map.get(warning_id)
            existing_acks = (
                dict(existing.acknowledgements) if existing is not None else {}
            )
            warning_map[warning_id] = _MutableWarningEntry(
                warning_id=warning_id,
                event_id=event.event_id,
                warning_type=CONCURRENT_DRIVER_WARNING,
                participant_ids=tuple(pids),
                acknowledgements=existing_acks,
            )

        elif et == POTENTIAL_STEP_COLLISION_DETECTED:
            warning_id = payload.get("warning_id", "")
            pids = payload.get("participant_ids", [])
            if not isinstance(warning_id, str) or not warning_id:
                continue
            if not isinstance(pids, list):
                continue
            _check_active_participants(pids, event.event_id, et)
            existing = warning_map.get(warning_id)
            existing_acks = (
                dict(existing.acknowledgements) if existing is not None else {}
            )
            warning_map[warning_id] = _MutableWarningEntry(
                warning_id=warning_id,
                event_id=event.event_id,
                warning_type=POTENTIAL_STEP_COLLISION_DETECTED,
                participant_ids=tuple(pids),
                acknowledgements=existing_acks,
            )

        elif et == WARNING_ACKNOWLEDGED:
            pid = payload.get("participant_id", "")
            warning_id = payload.get("warning_id", "")
            ack_action = payload.get("acknowledgement", "")
            if not isinstance(pid, str) or not pid:
                continue
            if not _check_active_participant(pid, event.event_id, et):
                continue
            if warning_id not in warning_map:
                if mode == "strict":
                    raise SpecKittyEventsError(
                        f"Warning {warning_id!r} not found "
                        f"(event_id={event.event_id}, event_type={et})"
                    )
                anomalies.append(
                    CollaborationAnomaly(
                        event_id=event.event_id,
                        event_type=et,
                        reason=f"Warning {warning_id!r} not found",
                    )
                )
                # Permissive mode keeps acknowledgement state even if the warning
                # event is missing from the window; if the warning arrives later,
                # the acknowledgement map is preserved by the warning handlers.
                warning_map[warning_id] = _MutableWarningEntry(
                    warning_id=warning_id,
                    event_id=event.event_id,
                    warning_type="UnknownWarning",
                    participant_ids=(pid,),
                    acknowledgements={pid: ack_action},
                )
                continue
            warning_map[warning_id].acknowledgements[pid] = ack_action

        elif et == COMMENT_POSTED:
            pid = payload.get("participant_id", "")
            if not isinstance(pid, str) or not pid:
                continue
            if not _check_active_participant(pid, event.event_id, et):
                continue
            comments.append(
                CommentEntry(
                    comment_id=payload.get("comment_id", ""),
                    event_id=event.event_id,
                    participant_id=pid,
                    content=payload.get("content", ""),
                    reply_to=payload.get("reply_to"),
                )
            )

        elif et == DECISION_CAPTURED:
            pid = payload.get("participant_id", "")
            if not isinstance(pid, str) or not pid:
                continue
            if not _check_active_participant(pid, event.event_id, et):
                continue
            decisions.append(
                DecisionEntry(
                    decision_id=payload.get("decision_id", ""),
                    event_id=event.event_id,
                    participant_id=pid,
                    topic=payload.get("topic", ""),
                    chosen_option=payload.get("chosen_option", ""),
                    referenced_warning_id=payload.get("referenced_warning_id"),
                )
            )

        elif et == SESSION_LINKED:
            pid = payload.get("participant_id", "")
            linked_sid = payload.get("linked_session_id", "")
            if not isinstance(pid, str) or not pid:
                continue
            if not _check_active_participant(pid, event.event_id, et):
                continue
            if pid not in linked_sessions:
                linked_sessions[pid] = []
            linked_sessions[pid].append(linked_sid)

    # 5. Assemble frozen state
    frozen_warnings: List[WarningEntry] = []
    for mw in warning_map.values():
        frozen_warnings.append(
            WarningEntry(
                warning_id=mw.warning_id,
                event_id=mw.event_id,
                warning_type=mw.warning_type,
                participant_ids=mw.participant_ids,
                acknowledgements=dict(mw.acknowledgements),
            )
        )

    frozen_focus_index: Dict[str, FrozenSet[str]] = {
        k: frozenset(v) for k, v in participants_by_focus.items()
    }

    last_event_id: Optional[str] = None
    if unique_events:
        last_event_id = unique_events[-1].event_id

    return ReducedCollaborationState(
        mission_id=mission_id,
        participants=dict(participants),
        departed_participants=dict(departed_participants),
        presence=dict(presence),
        active_drivers=frozenset(active_drivers),
        focus_by_participant=dict(focus_by_participant),
        participants_by_focus=frozen_focus_index,
        warnings=tuple(frozen_warnings),
        decisions=tuple(decisions),
        comments=tuple(comments),
        active_executions=dict(active_executions),
        linked_sessions=dict(linked_sessions),
        anomalies=tuple(anomalies),
        event_count=len(unique_events),
        last_processed_event_id=last_event_id,
    )


class _MutableWarningEntry:
    """Mutable helper for building WarningEntry during reduction."""

    __slots__ = (
        "warning_id",
        "event_id",
        "warning_type",
        "participant_ids",
        "acknowledgements",
    )

    def __init__(
        self,
        warning_id: str,
        event_id: str,
        warning_type: str,
        participant_ids: Tuple[str, ...],
        acknowledgements: Dict[str, str],
    ) -> None:
        self.warning_id = warning_id
        self.event_id = event_id
        self.warning_type = warning_type
        self.participant_ids = participant_ids
        self.acknowledgements = acknowledgements


# Late import to avoid circular dependency
from .models import Event  # noqa: E402
