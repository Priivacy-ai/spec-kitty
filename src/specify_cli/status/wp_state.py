"""WPState ABC, 9 concrete lane state classes, and wp_state_for() factory.

Implements the State Pattern for work-package lane behavior. Each lane
has a frozen dataclass subclass that owns its allowed transitions,
guard conditions, progress bucket, and display category.

See ADR: architecture/2.x/adr/2026-04-06-1-wp-state-pattern-for-lane-behavior.md
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from specify_cli.status.models import Lane

if TYPE_CHECKING:
    from specify_cli.status.transition_context import TransitionContext


class InvalidTransitionError(Exception):
    """Raised when a state transition is not allowed."""

    def __init__(self, source: Lane, target: Lane) -> None:
        self.source = source
        self.target = target
        super().__init__(f"Cannot transition from {source!r} to {target!r}")


@dataclass(frozen=True)
class WPState(ABC):
    """Abstract base for lane-specific work package behaviour."""

    @property
    @abstractmethod
    def lane(self) -> Lane: ...

    @property
    def is_terminal(self) -> bool:
        """Return True for terminal lanes (done, canceled).

        Terminal lanes require ``force=True`` to leave. Note that merge
        validation uses an explicit ``approved|done`` check, NOT this property.
        """
        return False

    @property
    def is_blocked(self) -> bool:
        return False

    @property
    def is_run_affecting(self) -> bool:
        """Return True if this WP affects execution progress.

        A WP is "run-affecting" if it is active (planned through approved).
        Does not include terminal lanes (done, canceled) or the blocked lane.

        Distinction from related properties:
        - ``is_run_affecting``: True for active lanes (planned through approved)
        - ``is_terminal``:      True for cleanup-only lanes (done, canceled)
        - ``is_blocked``:       True only for the blocked lane

        Returns:
            True  if lane in {planned, claimed, in_progress, for_review, in_review, approved}
            False if lane in {done, blocked, canceled}

        Usage::

            if state.is_run_affecting:
                # Route to implementation or review
        """
        return self.lane in {
            Lane.PLANNED,
            Lane.CLAIMED,
            Lane.IN_PROGRESS,
            Lane.FOR_REVIEW,
            Lane.IN_REVIEW,
            Lane.APPROVED,
        }

    @abstractmethod
    def allowed_targets(self) -> frozenset[Lane]: ...

    @abstractmethod
    def can_transition_to(self, target: Lane, ctx: TransitionContext) -> bool: ...

    def transition(self, target: Lane, ctx: TransitionContext) -> WPState:
        """Return the new state after a validated transition."""
        if not self.can_transition_to(target, ctx):
            raise InvalidTransitionError(self.lane, target)
        return wp_state_for(target)

    @abstractmethod
    def progress_bucket(self) -> str:
        """One of: 'not_started', 'in_flight', 'review', 'terminal'."""
        ...

    @abstractmethod
    def display_category(self) -> str:
        """Kanban column label (e.g., 'Planned', 'In Progress', 'Done')."""
        ...


# ---------------------------------------------------------------------------
# Helper: check actor is present
# ---------------------------------------------------------------------------


def _has_actor(ctx: TransitionContext) -> bool:
    return bool(ctx.actor and ctx.actor.strip())


# ---------------------------------------------------------------------------
# Concrete state classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlannedState(WPState):
    """Work package is planned but not yet started."""

    @property
    def lane(self) -> Lane:
        return Lane.PLANNED

    def allowed_targets(self) -> frozenset[Lane]:
        return frozenset({Lane.CLAIMED, Lane.BLOCKED, Lane.CANCELED})

    def can_transition_to(self, target: Lane, ctx: TransitionContext) -> bool:
        if target not in self.allowed_targets():
            return False
        if target == Lane.CLAIMED:
            return _has_actor(ctx)
        return True

    def progress_bucket(self) -> str:
        return "not_started"

    def display_category(self) -> str:
        return "Planned"


@dataclass(frozen=True)
class ClaimedState(WPState):
    """Work package has been claimed by an agent/actor."""

    @property
    def lane(self) -> Lane:
        return Lane.CLAIMED

    def allowed_targets(self) -> frozenset[Lane]:
        return frozenset({Lane.IN_PROGRESS, Lane.BLOCKED, Lane.CANCELED})

    def can_transition_to(self, target: Lane, ctx: TransitionContext) -> bool:
        if target not in self.allowed_targets():
            return False
        if target == Lane.IN_PROGRESS:
            return bool(ctx.workspace_context and ctx.workspace_context.strip())
        return True

    def progress_bucket(self) -> str:
        return "in_flight"

    def display_category(self) -> str:
        return "In Progress"


@dataclass(frozen=True)
class InProgressState(WPState):
    """Work package is actively being implemented."""

    @property
    def lane(self) -> Lane:
        return Lane.IN_PROGRESS

    def allowed_targets(self) -> frozenset[Lane]:
        return frozenset(
            {
                Lane.FOR_REVIEW,
                Lane.APPROVED,
                Lane.PLANNED,
                Lane.BLOCKED,
                Lane.CANCELED,
            }
        )

    def can_transition_to(self, target: Lane, ctx: TransitionContext) -> bool:
        if target not in self.allowed_targets():
            return False
        if target == Lane.FOR_REVIEW:
            if ctx.force:
                return True
            return ctx.subtasks_complete is True and ctx.implementation_evidence_present is True
        if target == Lane.APPROVED:
            return _has_reviewer_approval(ctx)
        if target == Lane.PLANNED:
            return bool(ctx.reason and ctx.reason.strip())
        return True

    def progress_bucket(self) -> str:
        return "in_flight"

    def display_category(self) -> str:
        return "In Progress"


@dataclass(frozen=True)
class ForReviewState(WPState):
    """Work package is queued for review (not yet claimed by a reviewer)."""

    @property
    def lane(self) -> Lane:
        return Lane.FOR_REVIEW

    def allowed_targets(self) -> frozenset[Lane]:
        return frozenset({Lane.IN_REVIEW, Lane.BLOCKED, Lane.CANCELED})

    def can_transition_to(self, target: Lane, ctx: TransitionContext) -> bool:
        if target not in self.allowed_targets():
            return False
        if target == Lane.IN_REVIEW:
            return _has_actor(ctx) and _no_review_conflict(ctx)
        return True

    def progress_bucket(self) -> str:
        return "review"

    def display_category(self) -> str:
        return "Review"


@dataclass(frozen=True)
class InReviewState(WPState):
    """Work package is actively being reviewed by a specific reviewer."""

    @property
    def lane(self) -> Lane:
        return Lane.IN_REVIEW

    def allowed_targets(self) -> frozenset[Lane]:
        return frozenset(
            {
                Lane.APPROVED,
                Lane.DONE,
                Lane.IN_PROGRESS,
                Lane.PLANNED,
                Lane.BLOCKED,
                Lane.CANCELED,
            }
        )

    def can_transition_to(self, target: Lane, ctx: TransitionContext) -> bool:
        if target not in self.allowed_targets():
            return False
        # FR-012c: ALL outbound transitions from in_review require ReviewResult
        return _has_review_result(ctx)

    def progress_bucket(self) -> str:
        return "review"

    def display_category(self) -> str:
        return "In Progress"


@dataclass(frozen=True)
class ApprovedState(WPState):
    """Work package review is approved, pending completion."""

    @property
    def lane(self) -> Lane:
        return Lane.APPROVED

    def allowed_targets(self) -> frozenset[Lane]:
        return frozenset(
            {
                Lane.DONE,
                Lane.IN_PROGRESS,
                Lane.PLANNED,
                Lane.BLOCKED,
                Lane.CANCELED,
            }
        )

    def can_transition_to(self, target: Lane, ctx: TransitionContext) -> bool:
        if target not in self.allowed_targets():
            return False
        if target == Lane.DONE:
            return _has_reviewer_approval(ctx)
        if target in (Lane.IN_PROGRESS, Lane.PLANNED):
            return bool(ctx.review_ref and ctx.review_ref.strip())
        return True

    def progress_bucket(self) -> str:
        return "review"

    def display_category(self) -> str:
        return "Approved"


@dataclass(frozen=True)
class DoneState(WPState):
    """Work package is complete (terminal)."""

    @property
    def lane(self) -> Lane:
        return Lane.DONE

    @property
    def is_terminal(self) -> bool:
        return True

    def allowed_targets(self) -> frozenset[Lane]:
        return frozenset()

    def can_transition_to(self, target: Lane, ctx: TransitionContext) -> bool:  # noqa: ARG002
        return False

    def progress_bucket(self) -> str:
        return "terminal"

    def display_category(self) -> str:
        return "Done"


@dataclass(frozen=True)
class BlockedState(WPState):
    """Work package is blocked on an external dependency."""

    @property
    def lane(self) -> Lane:
        return Lane.BLOCKED

    @property
    def is_blocked(self) -> bool:
        return True

    def allowed_targets(self) -> frozenset[Lane]:
        return frozenset({Lane.IN_PROGRESS, Lane.CANCELED})

    def can_transition_to(self, target: Lane, ctx: TransitionContext) -> bool:  # noqa: ARG002
        return target in self.allowed_targets()

    def progress_bucket(self) -> str:
        return "in_flight"

    def display_category(self) -> str:
        return "Blocked"


@dataclass(frozen=True)
class CanceledState(WPState):
    """Work package has been canceled (terminal)."""

    @property
    def lane(self) -> Lane:
        return Lane.CANCELED

    @property
    def is_terminal(self) -> bool:
        return True

    def allowed_targets(self) -> frozenset[Lane]:
        return frozenset()

    def can_transition_to(self, target: Lane, ctx: TransitionContext) -> bool:  # noqa: ARG002
        return False

    def progress_bucket(self) -> str:
        return "terminal"

    def display_category(self) -> str:
        return "Canceled"


# ---------------------------------------------------------------------------
# Guard helpers (used by concrete classes)
# ---------------------------------------------------------------------------


def _has_reviewer_approval(ctx: TransitionContext) -> bool:
    """Check that ctx.evidence contains valid reviewer approval."""
    if ctx.evidence is None:
        return False
    review = getattr(ctx.evidence, "review", None)
    reviewer = getattr(review, "reviewer", None) if review is not None else None
    reference = getattr(review, "reference", None) if review is not None else None
    if not reviewer or not str(reviewer).strip():
        return False
    return bool(reference and str(reference).strip())


def _no_review_conflict(ctx: TransitionContext) -> bool:
    """Check that no other actor already holds the review claim.

    Returns True if:
    - No current_actor is set (no existing claim), OR
    - current_actor matches the requesting actor (idempotent re-claim).
    """
    if not ctx.current_actor or not ctx.current_actor.strip():
        return True
    return ctx.current_actor.strip() == ctx.actor.strip()


def _has_review_result(ctx: TransitionContext) -> bool:
    """Check that ctx.review_result is a valid ReviewResult."""
    rr = ctx.review_result
    if rr is None:
        return False
    reviewer = getattr(rr, "reviewer", None)
    verdict = getattr(rr, "verdict", None)
    reference = getattr(rr, "reference", None)
    if not reviewer or not str(reviewer).strip():
        return False
    if not verdict or not str(verdict).strip():
        return False
    return bool(reference and str(reference).strip())


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_STATE_MAP: dict[str, type[WPState]] = {
    "planned": PlannedState,
    "claimed": ClaimedState,
    "in_progress": InProgressState,
    "for_review": ForReviewState,
    "in_review": InReviewState,
    "approved": ApprovedState,
    "done": DoneState,
    "blocked": BlockedState,
    "canceled": CanceledState,
}

# Alias resolution for the factory (only "doing" remains; "in_review" is first-class)
_FACTORY_ALIASES: dict[str, str] = {
    "doing": "in_progress",
}


def wp_state_for(lane: Lane | str) -> WPState:
    """Instantiate the correct concrete WPState for a given lane value."""
    lane_str = str(lane)
    lane_str = _FACTORY_ALIASES.get(lane_str, lane_str)
    cls = _STATE_MAP.get(lane_str)
    if cls is None:
        raise ValueError(f"Unknown lane: {lane_str!r}")
    return cls()
