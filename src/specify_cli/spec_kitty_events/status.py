"""Status state model contracts for work-package lane transitions."""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, Dict, FrozenSet, List, Literal, Mapping, Optional, Sequence, Set, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import Event, SpecKittyEventsError, ValidationError

logger = logging.getLogger(__name__)


class Lane(str, Enum):
    """Work-package lifecycle lanes."""

    PLANNED = "planned"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    FOR_REVIEW = "for_review"
    APPROVED = "approved"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELED = "canceled"


class SyncLaneV1(str, Enum):
    """V1 compatibility sync lanes for downstream consumers."""

    PLANNED = "planned"
    DOING = "doing"
    FOR_REVIEW = "for_review"
    DONE = "done"


class SyncLaneV2(str, Enum):
    """V2 sync lanes preserving the explicit approved review outcome."""

    PLANNED = "planned"
    DOING = "doing"
    FOR_REVIEW = "for_review"
    APPROVED = "approved"
    DONE = "done"


CANONICAL_TO_SYNC_V1: Mapping[Lane, SyncLaneV1] = MappingProxyType({
    Lane.PLANNED: SyncLaneV1.PLANNED,
    Lane.CLAIMED: SyncLaneV1.PLANNED,
    Lane.IN_PROGRESS: SyncLaneV1.DOING,
    Lane.FOR_REVIEW: SyncLaneV1.FOR_REVIEW,
    Lane.APPROVED: SyncLaneV1.DONE,
    Lane.DONE: SyncLaneV1.DONE,
    Lane.BLOCKED: SyncLaneV1.DOING,
    Lane.CANCELED: SyncLaneV1.PLANNED,
})


CANONICAL_TO_SYNC_V2: Mapping[Lane, SyncLaneV2] = MappingProxyType({
    Lane.PLANNED: SyncLaneV2.PLANNED,
    Lane.CLAIMED: SyncLaneV2.PLANNED,
    Lane.IN_PROGRESS: SyncLaneV2.DOING,
    Lane.FOR_REVIEW: SyncLaneV2.FOR_REVIEW,
    Lane.APPROVED: SyncLaneV2.APPROVED,
    Lane.DONE: SyncLaneV2.DONE,
    Lane.BLOCKED: SyncLaneV2.DOING,
    Lane.CANCELED: SyncLaneV2.PLANNED,
})


def canonical_to_sync_v1(lane: Lane) -> SyncLaneV1:
    """Apply the V1 canonical-to-sync lane mapping.

    Args:
        lane: A canonical Lane enum value.

    Returns:
        The corresponding SyncLaneV1 value.

    Raises:
        KeyError: If lane is not in the V1 mapping.
    """
    return CANONICAL_TO_SYNC_V1[lane]


def canonical_to_sync_v2(lane: Lane) -> SyncLaneV2:
    """Apply the V2 canonical-to-sync lane mapping."""
    return CANONICAL_TO_SYNC_V2[lane]


class ExecutionMode(str, Enum):
    """How a work-package is being executed."""

    WORKTREE = "worktree"
    DIRECT_REPO = "direct_repo"


TERMINAL_LANES: FrozenSet[Lane] = frozenset({Lane.DONE, Lane.CANCELED})

LANE_ALIASES: Dict[str, Lane] = {"doing": Lane.IN_PROGRESS}

WP_STATUS_CHANGED: str = "WPStatusChanged"


def normalize_lane(value: str) -> Lane:
    """Resolve a string to a Lane, handling aliases.

    Args:
        value: A lane value string, either a canonical Lane member value
            or a known alias.

    Returns:
        The corresponding Lane enum member.

    Raises:
        ValidationError: If value is not a valid lane or alias.
    """
    # Check if value is already a Lane member value
    for member in Lane:
        if member.value == value:
            return member

    # Check aliases
    if value in LANE_ALIASES:
        return LANE_ALIASES[value]

    raise ValidationError(
        f"Unknown lane value: {value!r}. "
        f"Valid values: {[m.value for m in Lane]}. "
        f"Aliases: {list(LANE_ALIASES.keys())}"
    )


# ---------------------------------------------------------------------------
# Evidence models
# ---------------------------------------------------------------------------


class RepoEvidence(BaseModel):
    """Evidence of repository changes for a completed work-package."""

    model_config = ConfigDict(frozen=True)

    repo: str = Field(..., min_length=1, description="Repository identifier")
    branch: str = Field(..., min_length=1, description="Branch name")
    commit: str = Field(..., min_length=1, description="Commit SHA or reference")
    files_touched: Optional[List[str]] = Field(
        None, description="List of files modified"
    )


class VerificationEntry(BaseModel):
    """A single verification step (e.g. test run, lint check)."""

    model_config = ConfigDict(frozen=True)

    command: str = Field(..., min_length=1, description="Command that was executed")
    result: str = Field(..., min_length=1, description="Outcome of the command")
    summary: Optional[str] = Field(None, description="Human-readable summary")


class ReviewVerdict(BaseModel):
    """Verdict from a human or automated reviewer."""

    model_config = ConfigDict(frozen=True)

    reviewer: str = Field(..., min_length=1, description="Who reviewed")
    verdict: str = Field(..., min_length=1, description="Verdict string")
    reference: Optional[str] = Field(
        None, description="URL or reference for the review"
    )


class DoneEvidence(BaseModel):
    """Evidence bundle required when a WP transitions to DONE."""

    model_config = ConfigDict(frozen=True)

    repos: List[RepoEvidence] = Field(
        ..., min_length=1, description="At least one repo with changes"
    )
    verification: List[VerificationEntry] = Field(
        default_factory=list, description="Verification steps executed"
    )
    review: ReviewVerdict = Field(..., description="Review verdict")


# ---------------------------------------------------------------------------
# Transition models
# ---------------------------------------------------------------------------


class ForceMetadata(BaseModel):
    """Metadata attached when a transition is forced."""

    model_config = ConfigDict(frozen=True)

    force: Literal[True] = Field(True, description="Always True for forced transitions")
    actor: str = Field(..., min_length=1, description="Who forced the transition")
    reason: str = Field(..., min_length=1, description="Why the transition was forced")


class StatusTransitionPayload(BaseModel):
    """Payload for a WPStatusChanged event describing a lane transition."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_slug: str = Field(..., min_length=1, description="Mission identifier")
    wp_id: str = Field(..., min_length=1, description="Work-package identifier")
    from_lane: Optional[Lane] = Field(
        None, description="Lane the WP is transitioning from (None for initial)"
    )
    to_lane: Lane = Field(..., description="Lane the WP is transitioning to")
    actor: Union[str, Dict[str, Any]] = Field(
        ...,
        description=(
            "Who initiated the transition. Accepts either a plain string identifier "
            "(e.g. 'claude', 'user', 'migration') or a structured dict carrying "
            "richer audit fields such as {role, profile, tool, model}. Use "
            "``actor_label`` for a canonical string form."
        ),
    )
    force: bool = Field(False, description="Whether this is a forced transition")
    reason: Optional[str] = Field(
        None, description="Reason for the transition (required when force=True)"
    )
    execution_mode: ExecutionMode = Field(
        ..., description="How the work-package is being executed"
    )
    review_ref: Optional[str] = Field(
        None, description="Reference to an external review"
    )
    evidence: Optional[DoneEvidence] = Field(
        None, description="Evidence bundle (required when to_lane=DONE)"
    )

    @field_validator("from_lane", "to_lane", mode="before")
    @classmethod
    def _normalize_lane_aliases(cls, v: Optional[str]) -> Optional[str]:
        """Resolve lane aliases before Pydantic coerces to Lane enum."""
        if v is None:
            return v
        if isinstance(v, str) and v in LANE_ALIASES:
            return LANE_ALIASES[v].value
        return v

    @field_validator("actor", mode="after")
    @classmethod
    def _validate_actor(cls, v: Union[str, Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
        """Ensure actor is a non-empty string or non-empty dict."""
        if isinstance(v, str):
            if not v.strip():
                raise ValueError("actor string must be non-empty")
            return v
        if isinstance(v, dict):
            if not v:
                raise ValueError("actor dict must be non-empty")
            return v
        raise ValueError("actor must be a string or dict")

    @property
    def actor_label(self) -> str:
        """Canonical string form of ``actor`` for reducers, logs, and display.

        Returns the string itself if ``actor`` is a string. For dict actors,
        prefers ``profile`` then ``role`` then ``display_name`` then ``actor_id``
        then the first non-empty string value, falling back to ``"unknown"``.

        Intentionally a plain ``@property`` rather than ``@computed_field`` so
        that the derived value is not round-tripped through ``model_dump()``
        (which would conflict with ``extra="forbid"`` on reload).
        """
        if isinstance(self.actor, str):
            return self.actor
        for key in ("profile", "role", "display_name", "actor_id"):
            value = self.actor.get(key)
            if isinstance(value, str) and value:
                return value
        for value in self.actor.values():
            if isinstance(value, str) and value:
                return value
        return "unknown"

    @model_validator(mode="after")
    def _check_business_rules(self) -> "StatusTransitionPayload":
        """Enforce business rules on the transition payload."""
        if self.force and (self.reason is None or self.reason.strip() == ""):
            raise ValueError(
                "force=True requires a non-empty reason"
            )
        if self.to_lane in {Lane.APPROVED, Lane.DONE} and self.evidence is None:
            raise ValueError(
                "to_lane in {'approved', 'done'} requires evidence"
            )
        return self


class TransitionError(SpecKittyEventsError):
    """Raised when a status transition violates business rules."""

    def __init__(self, violations: Tuple[str, ...]) -> None:
        self.violations = violations
        super().__init__(f"Invalid transition: {'; '.join(violations)}")


# ---------------------------------------------------------------------------
# Section 4: Validation
# ---------------------------------------------------------------------------

_ALLOWED_TRANSITIONS: FrozenSet[Tuple[Optional[Lane], Lane]] = frozenset({
    # Initial
    (None, Lane.PLANNED),
    # Happy path
    (Lane.PLANNED, Lane.CLAIMED),
    (Lane.CLAIMED, Lane.IN_PROGRESS),
    (Lane.IN_PROGRESS, Lane.FOR_REVIEW),
    (Lane.IN_PROGRESS, Lane.APPROVED),
    (Lane.FOR_REVIEW, Lane.APPROVED),
    (Lane.FOR_REVIEW, Lane.DONE),
    (Lane.APPROVED, Lane.DONE),
    # Review rollback
    (Lane.FOR_REVIEW, Lane.IN_PROGRESS),
    (Lane.FOR_REVIEW, Lane.PLANNED),
    (Lane.APPROVED, Lane.IN_PROGRESS),
    (Lane.APPROVED, Lane.PLANNED),
    # Abandon/reassign
    (Lane.IN_PROGRESS, Lane.PLANNED),
    # Unblock
    (Lane.BLOCKED, Lane.IN_PROGRESS),
})


@dataclass(frozen=True)
class TransitionValidationResult:
    """Result of validating a proposed status transition."""

    valid: bool
    violations: Tuple[str, ...] = ()


def validate_transition(payload: StatusTransitionPayload) -> TransitionValidationResult:
    """Validate a proposed status transition against business rules.

    This function NEVER raises exceptions for business rule violations.
    It always returns a TransitionValidationResult.

    Args:
        payload: The transition payload to validate.

    Returns:
        A TransitionValidationResult indicating whether the transition is valid,
        and any violations found.
    """
    violations: List[str] = []

    # Terminal lane check
    if payload.from_lane is not None and payload.from_lane in TERMINAL_LANES and not payload.force:
        violations.append(
            f"{payload.from_lane.value} is terminal; requires force=True to exit"
        )

    # Force check — if force is True, skip matrix check
    if not payload.force:
        # Matrix check
        pair = (payload.from_lane, payload.to_lane)
        in_matrix = pair in _ALLOWED_TRANSITIONS
        to_blocked = (
            payload.to_lane is Lane.BLOCKED
            and payload.from_lane is not None
            and payload.from_lane not in TERMINAL_LANES
        )
        to_canceled = (
            payload.to_lane is Lane.CANCELED
            and payload.from_lane is not None
            and payload.from_lane not in TERMINAL_LANES
        )
        if not (in_matrix or to_blocked or to_canceled):
            violations.append(
                f"Transition {payload.from_lane} -> {payload.to_lane} is not allowed"
            )

    # Guard conditions (checked regardless of force)
    if (
        payload.from_lane in {Lane.FOR_REVIEW, Lane.APPROVED}
        and payload.to_lane in {Lane.IN_PROGRESS, Lane.PLANNED}
        and (payload.review_ref is None or payload.review_ref.strip() == "")
    ):
        violations.append(
            f"{payload.from_lane.value} -> {payload.to_lane.value} requires review_ref"
        )

    if (
        payload.from_lane is Lane.IN_PROGRESS
        and payload.to_lane is Lane.PLANNED
        and (payload.reason is None or payload.reason.strip() == "")
    ):
        violations.append("in_progress -> planned requires reason")

    return TransitionValidationResult(
        valid=len(violations) == 0,
        violations=tuple(violations),
    )


# ---------------------------------------------------------------------------
# Section 5: Ordering
# ---------------------------------------------------------------------------


def status_event_sort_key(event: Event) -> Tuple[int, str, str]:
    """Deterministic sort key for status events.

    Returns (lamport_clock, timestamp_isoformat, event_id).
    """
    return (event.lamport_clock, event.timestamp.isoformat(), event.event_id)


def dedup_events(events: Sequence[Event]) -> List[Event]:
    """Remove duplicate events by event_id, preserving first occurrence."""
    seen: Set[str] = set()
    result: List[Event] = []
    for event in events:
        if event.event_id not in seen:
            seen.add(event.event_id)
            result.append(event)
    return result


# ---------------------------------------------------------------------------
# Section 6: Reducer
# ---------------------------------------------------------------------------


class WPState(BaseModel):
    """Per-work-package current state from reducer."""

    model_config = ConfigDict(frozen=True)

    wp_id: str = Field(..., min_length=1)
    current_lane: Lane
    last_event_id: str = Field(..., min_length=1)
    last_transition_at: datetime
    evidence: Optional[DoneEvidence] = None


class TransitionAnomaly(BaseModel):
    """Records an invalid transition encountered during reduction."""

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(..., min_length=1)
    wp_id: str = Field(..., min_length=1)
    from_lane: Optional[Lane] = None
    to_lane: Optional[Lane] = None
    reason: str = Field(..., min_length=1)


class ReducedStatus(BaseModel):
    """Output of the reference reducer."""

    model_config = ConfigDict(frozen=True)

    wp_states: Dict[str, WPState] = Field(default_factory=dict)
    anomalies: List[TransitionAnomaly] = Field(default_factory=list)
    event_count: int = Field(default=0, ge=0)
    last_processed_event_id: Optional[str] = None


def _rollback_aware_order(
    group: List[Tuple[Event, StatusTransitionPayload]],
) -> List[Tuple[Event, StatusTransitionPayload]]:
    """Within a concurrent group, ensure reviewer rollbacks are applied last."""

    def _is_rollback(payload: StatusTransitionPayload) -> bool:
        return (
            payload.from_lane == Lane.FOR_REVIEW
            and payload.to_lane == Lane.IN_PROGRESS
            and payload.review_ref is not None
        )

    non_rollbacks: List[Tuple[Event, StatusTransitionPayload]] = [
        (e, p) for e, p in group if not _is_rollback(p)
    ]
    rollbacks: List[Tuple[Event, StatusTransitionPayload]] = [
        (e, p) for e, p in group if _is_rollback(p)
    ]
    return non_rollbacks + rollbacks


def reduce_status_events(events: Sequence[Event]) -> ReducedStatus:
    """Reduce status events to per-WP current lane state.

    Pipeline: filter -> sort -> dedup -> rollback-aware reduce.
    Pure function, no I/O. Deterministic for any permutation.
    """
    # 1. Filter: keep only WPStatusChanged events
    status_events = [e for e in events if e.event_type == WP_STATUS_CHANGED]

    # 2. Sort: deterministic ordering
    sorted_events = sorted(status_events, key=status_event_sort_key)

    # 3. Dedup
    unique_events = dedup_events(sorted_events)

    if not unique_events:
        return ReducedStatus()

    anomalies: List[TransitionAnomaly] = []

    def _safe_lane(raw_lane: object) -> Optional[Lane]:
        if isinstance(raw_lane, Lane):
            return raw_lane
        if isinstance(raw_lane, str):
            try:
                return normalize_lane(raw_lane)
            except ValidationError:
                return None
        return None

    # 4. Parse payloads
    parsed: List[Tuple[Event, StatusTransitionPayload]] = []
    for event in unique_events:
        try:
            payload = StatusTransitionPayload.model_validate(event.payload)
            parsed.append((event, payload))
        except Exception as exc:
            payload_dict = event.payload if isinstance(event.payload, dict) else {}
            wp_id_raw = payload_dict.get("wp_id")
            wp_id = wp_id_raw if isinstance(wp_id_raw, str) and wp_id_raw else "<unknown>"
            anomalies.append(
                TransitionAnomaly(
                    event_id=event.event_id,
                    wp_id=wp_id,
                    from_lane=_safe_lane(payload_dict.get("from_lane")),
                    to_lane=_safe_lane(payload_dict.get("to_lane")),
                    reason=f"payload validation failed: {exc}",
                )
            )
            continue

    if not parsed:
        return ReducedStatus(
            anomalies=anomalies,
            event_count=len(unique_events),
            last_processed_event_id=unique_events[-1].event_id,
        )

    # 5. Rollback-aware reordering: group by (wp_id, lamport_clock)
    # Use insertion-order dict grouping to handle interleaving keys correctly.
    grouped: List[List[Tuple[Event, StatusTransitionPayload]]] = []
    grouped_by_key: Dict[
        Tuple[str, int], List[Tuple[Event, StatusTransitionPayload]]
    ] = {}
    for event, payload in parsed:
        key = (payload.wp_id, event.lamport_clock)
        grouped_by_key.setdefault(key, []).append((event, payload))
    for group in grouped_by_key.values():
        grouped.append(_rollback_aware_order(group))

    # 6. Sequential reduce with concurrent-group awareness
    wp_states: Dict[str, WPState] = {}

    for group in grouped:
        # Snapshot state at the start of each concurrent group.
        # Within a group, all events are validated against the snapshot,
        # and the last valid transition wins (overwriting earlier ones).
        snapshot: Dict[str, Optional[WPState]] = {}
        for _evt, p in group:
            if p.wp_id not in snapshot:
                snapshot[p.wp_id] = wp_states.get(p.wp_id)

        for event, payload in group:
            wp_id = payload.wp_id
            snapped = snapshot[wp_id]

            # Check from_lane matches state at group start
            expected_lane = snapped.current_lane if snapped else None
            if payload.from_lane != expected_lane:
                if payload.force:
                    # Historical/bootstrap migration events (e.g. frontmatter-to-JSONL
                    # backfill) legitimately carry mid-lifecycle from_lane values.
                    # StatusTransitionPayload requires a non-empty reason when
                    # force=true (see validator below), which provides the audit trail.
                    logger.warning(
                        "forced transition bypassing from_lane mismatch: "
                        "wp=%s event=%s expected=%s got=%s reason=%s",
                        wp_id,
                        event.event_id,
                        expected_lane,
                        payload.from_lane,
                        payload.reason,
                    )
                else:
                    anomalies.append(
                        TransitionAnomaly(
                            event_id=event.event_id,
                            wp_id=wp_id,
                            from_lane=payload.from_lane,
                            to_lane=payload.to_lane,
                            reason=(
                                f"from_lane mismatch: expected {expected_lane}, "
                                f"got {payload.from_lane}"
                            ),
                        )
                    )
                    continue

            # Validate transition
            validation = validate_transition(payload)
            if not validation.valid:
                anomalies.append(
                    TransitionAnomaly(
                        event_id=event.event_id,
                        wp_id=wp_id,
                        from_lane=payload.from_lane,
                        to_lane=payload.to_lane,
                        reason="; ".join(validation.violations),
                    )
                )
                continue

            # Apply transition (last valid in group wins)
            evidence = payload.evidence if payload.to_lane == Lane.DONE else None
            wp_states[wp_id] = WPState(
                wp_id=wp_id,
                current_lane=payload.to_lane,
                last_event_id=event.event_id,
                last_transition_at=event.timestamp,
                evidence=evidence,
            )

    # 7. Return
    return ReducedStatus(
        wp_states=wp_states,
        anomalies=anomalies,
        event_count=len(unique_events),
        last_processed_event_id=unique_events[-1].event_id,
    )
