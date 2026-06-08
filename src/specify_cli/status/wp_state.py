"""WPState ABC, 10 concrete lane state classes, and wp_state_for() factory.

Implements the State Pattern for work-package lane behavior. Each lane
has a frozen dataclass subclass that owns its allowed transitions,
guard conditions, progress bucket, and display category.

Single-ownership (WP01, DM-01KTH03G): the WPState objects are the SOLE
authority for BOTH the transition edge graph AND the act of transitioning
(structural edge + guards + force-override). ``transitions.validate_transition``
is a thin delegator over :meth:`WPState.transition_to`; no edge/guard/force
logic lives outside these state objects, and no production code consults a
parallel ``(from, to)`` table as a gate.

See ADR: architecture/2.x/adr/2026-04-06-1-wp-state-pattern-for-lane-behavior.md
See also: architecture/3.x/adr/2026-06-07-1-wp-lane-fsm-genesis-and-finalize-clobber.md
(genesis lane, guard/force migration into the state objects, finalize clobber fix)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol

from specify_cli.status.models import Lane

# Shared error message constants (single source for parity with the historical
# ``transitions.py`` implementation these guards were migrated from).
_FORCE_REQUIRES_ACTOR_AND_REASON = "Force transitions require actor and reason"
_REVIEWER_APPROVAL_REQUIRED = "Transition to approved/done requires evidence (reviewer identity and approval reference)"


class TransitionInputs(Protocol):
    """Structural protocol over the guard inputs a transition consults.

    Both :class:`specify_cli.status.transition_context.TransitionContext` and
    :class:`specify_cli.status.models.GuardContext` satisfy this protocol, so
    the FSM can own guard + force evaluation for callers of either context
    without coupling to a single concrete type.
    """

    actor: str | None
    workspace_context: str | None
    subtasks_complete: bool | None
    implementation_evidence_present: bool | None
    reason: str | None
    review_ref: str | None
    evidence: object
    force: bool
    review_result: object
    current_actor: str | None


class InvalidTransitionError(Exception):
    """Raised when a state transition is not allowed."""

    def __init__(self, source: Lane, target: Lane, reason: str | None = None) -> None:
        self.source = source
        self.target = target
        self.reason = reason
        message = f"Cannot transition from {source!r} to {target!r}"
        if reason:
            message = f"{message}: {reason}"
        super().__init__(message)


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
            False if lane in {genesis, done, blocked, canceled}

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

    @property
    def current_lane(self) -> Lane:
        """The lane this state represents (State-pattern FSM accessor).

        Alias of :attr:`lane` using the canonical FSM vocabulary.
        """
        return self.lane

    def may_transition_to(self, target: Lane) -> bool:
        """Structural edge check only (guard-free, force-free).

        This is the single authority for the lane-adjacency graph: a target is
        reachable iff it is in this state's ``allowed_targets()``. Production
        edge-legality questions route here instead of consulting any parallel
        ``(from, to)`` table.
        """
        return target in self.allowed_targets()

    def guard_for(self, target: Lane, ctx: TransitionInputs) -> tuple[bool, str | None]:  # noqa: ARG002 -- target/ctx are the contract every override consumes; the default hook is unguarded
        """Evaluate this state's entry guard for ``target``.

        Subclasses with guarded outbound edges override this. The default is
        unguarded (any structurally-allowed target is permitted). Returns the
        ``(ok, error_message)`` decision; ``error_message`` is the parity
        message the historical ``transitions._run_guard`` produced.
        """
        return True, None

    def can_transition_to(self, target: Lane, ctx: TransitionInputs) -> bool:
        """Guard-aware boolean edge check (no force-override).

        Returns True iff the structural edge exists AND this state's entry
        guard for ``target`` is satisfied by ``ctx``. Force is NOT consulted
        here — use :meth:`check_transition` / :meth:`transition_to` for the
        full force-aware decision.
        """
        if not self.may_transition_to(target):
            return False
        ok, _ = self.guard_for(target, ctx)
        return ok

    def check_transition(self, target: Lane, ctx: TransitionInputs) -> tuple[bool, str | None]:
        """Full transition decision: structural edge + guard + force-override.

        Returns ``(ok, error_message)`` with the exact parity messages of the
        historical ``validate_transition``. ``force`` (with actor + reason)
        overrides both the edge check and the guards — including terminal
        force-exit from ``done``/``canceled`` to any display lane. ``genesis``
        remains a non-display seed source and is never a valid target.
        """
        if target == Lane.GENESIS:
            # Genesis is a seed source, not a persisted/display target. Force may
            # bypass edges and guards, but it must not create a current genesis WP.
            return False, f"Illegal transition: {self.lane.value} -> {target.value}"
        if not self.may_transition_to(target):
            # Edge does not exist: only force (with actor + reason) can override.
            if ctx.force:
                return self._check_force(ctx)
            return False, f"Illegal transition: {self.lane.value} -> {target.value}"

        # Structurally-allowed edge. Force bypasses the guard but still requires
        # actor + reason for audit; otherwise run this state's entry guard.
        if ctx.force:
            return self._check_force(ctx)
        return self.guard_for(target, ctx)

    @staticmethod
    def _check_force(ctx: TransitionInputs) -> tuple[bool, str | None]:
        """Force-override gate: requires a non-empty actor AND reason."""
        if not ctx.actor or not ctx.actor.strip():
            return False, _FORCE_REQUIRES_ACTOR_AND_REASON
        if not ctx.reason or not ctx.reason.strip():
            return False, _FORCE_REQUIRES_ACTOR_AND_REASON
        return True, None

    def transition_to(self, target: Lane, ctx: TransitionInputs) -> WPState:
        """Return the new state after a full edge + guard + force transition.

        Canonical FSM name. Honours ``ctx.force`` (requires actor + reason)
        exactly where the historical ``validate_transition`` force branch
        permitted it, including terminal force-exit. Raises
        :class:`InvalidTransitionError` on rejection.
        """
        ok, error = self.check_transition(target, ctx)
        if not ok:
            raise InvalidTransitionError(self.lane, target, error)
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
# Guard helpers (used by concrete classes)
# ---------------------------------------------------------------------------


def _has_actor(ctx: TransitionInputs) -> bool:
    return bool(ctx.actor and ctx.actor.strip())


# ---------------------------------------------------------------------------
# Concrete state classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GenesisState(WPState):
    """Work package created but not yet seeded into the lane lifecycle.

    Pre-finalize, non-display state. ``finalize-tasks`` performs the explicit
    ``genesis -> planned`` seed. A genesis WP has no lane events and so never
    materializes into a snapshot or onto the board; this state exists to make
    the seed transition explicit rather than an implied ``planned -> planned``.
    """

    @property
    def lane(self) -> Lane:
        return Lane.GENESIS

    def allowed_targets(self) -> frozenset[Lane]:
        return frozenset({Lane.PLANNED, Lane.CANCELED})

    def progress_bucket(self) -> str:
        return "not_started"

    def display_category(self) -> str:
        # Non-display lane: group under Planned so no separate board column is
        # ever introduced for the transient genesis state.
        return "Planned"


@dataclass(frozen=True)
class PlannedState(WPState):
    """Work package is planned but not yet started."""

    @property
    def lane(self) -> Lane:
        return Lane.PLANNED

    def allowed_targets(self) -> frozenset[Lane]:
        return frozenset({Lane.CLAIMED, Lane.BLOCKED, Lane.CANCELED})

    def guard_for(self, target: Lane, ctx: TransitionInputs) -> tuple[bool, str | None]:
        if target == Lane.CLAIMED and not _has_actor(ctx):
            return False, "Transition requires actor identity"
        return True, None

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

    def guard_for(self, target: Lane, ctx: TransitionInputs) -> tuple[bool, str | None]:
        if target == Lane.IN_PROGRESS and not (ctx.workspace_context and ctx.workspace_context.strip()):
            return False, "Transition claimed -> in_progress requires workspace context"
        return True, None

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

    def guard_for(self, target: Lane, ctx: TransitionInputs) -> tuple[bool, str | None]:
        # NB: guards must NOT consult ``ctx.force`` — force is handled once, at the
        # caller (``check_transition._check_force``), which bypasses the guard
        # entirely. A force branch here is dead on the canonical path and breaks
        # the ``can_transition_to`` contract ("Force is NOT consulted here"), making
        # ``can_transition_to(FOR_REVIEW, force=True)`` disagree with
        # ``check_transition`` (#1775 review M2).
        if target == Lane.FOR_REVIEW:
            if ctx.subtasks_complete is not True:
                return (
                    False,
                    "Transition in_progress -> for_review requires completed subtasks or force with reason",
                )
            if ctx.implementation_evidence_present is not True:
                return (
                    False,
                    "Transition in_progress -> for_review requires implementation evidence or force with reason",
                )
            return True, None
        if target == Lane.APPROVED:
            return _check_reviewer_approval(ctx)
        if target == Lane.PLANNED:
            if not (ctx.reason and ctx.reason.strip()):
                return False, "Transition in_progress -> planned requires reason"
            return True, None
        return True, None

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

    def guard_for(self, target: Lane, ctx: TransitionInputs) -> tuple[bool, str | None]:
        if target == Lane.IN_REVIEW:
            if not _has_actor(ctx):
                return False, "Transition requires actor identity"
            return _check_no_review_conflict(ctx)
        return True, None

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

    def guard_for(self, target: Lane, ctx: TransitionInputs) -> tuple[bool, str | None]:  # noqa: ARG002 -- FR-012c applies the same guard to every outbound target, so ``target`` is intentionally not branched on
        # FR-012c: ALL outbound transitions from in_review require ReviewResult.
        return _check_review_result(ctx)

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

    def guard_for(self, target: Lane, ctx: TransitionInputs) -> tuple[bool, str | None]:
        if target == Lane.DONE:
            return _check_reviewer_approval(ctx)
        if target in (Lane.IN_PROGRESS, Lane.PLANNED):
            if not (ctx.review_ref and ctx.review_ref.strip()):
                return False, "Transition requires review_ref (review feedback reference)"
            return True, None
        return True, None

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

    def progress_bucket(self) -> str:
        return "terminal"

    def display_category(self) -> str:
        return "Canceled"


# ---------------------------------------------------------------------------
# Guard helpers (evidence / review-result / conflict) — own the parity messages
# ---------------------------------------------------------------------------


def _check_reviewer_approval(ctx: TransitionInputs) -> tuple[bool, str | None]:
    """Guard: approval/done transitions require reviewer approval evidence."""
    evidence = ctx.evidence
    if evidence is None:
        return False, _REVIEWER_APPROVAL_REQUIRED
    review = getattr(evidence, "review", None)
    reviewer = getattr(review, "reviewer", None) if review is not None else None
    reference = getattr(review, "reference", None) if review is not None else None
    if not reviewer or not str(reviewer).strip():
        return False, _REVIEWER_APPROVAL_REQUIRED
    if not reference or not str(reference).strip():
        return False, _REVIEWER_APPROVAL_REQUIRED
    return True, None


def _check_no_review_conflict(ctx: TransitionInputs) -> tuple[bool, str | None]:
    """Guard: for_review -> in_review rejects a conflicting reviewer claim.

    Permits an idempotent re-claim when ``current_actor`` matches ``actor``.
    """
    current_actor = ctx.current_actor
    actor = ctx.actor or ""
    if current_actor and current_actor.strip() and current_actor.strip() != actor.strip():
        return (
            False,
            f"WP already claimed for review by {current_actor.strip()}; cannot be claimed by {actor.strip()}",
        )
    return True, None


def _check_review_result(ctx: TransitionInputs) -> tuple[bool, str | None]:
    """Guard: all outbound in_review transitions require a ReviewResult."""
    rr = ctx.review_result
    if rr is None:
        return (
            False,
            "Transition from in_review requires review_result (structured review outcome)",
        )
    reviewer = getattr(rr, "reviewer", None)
    verdict = getattr(rr, "verdict", None)
    reference = getattr(rr, "reference", None)
    if not reviewer or not str(reviewer).strip():
        return False, "Transition from in_review requires review_result with reviewer"
    if not verdict or not str(verdict).strip():
        return False, "Transition from in_review requires review_result with verdict"
    if not reference or not str(reference).strip():
        return False, "Transition from in_review requires review_result with reference"
    return True, None


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_STATE_MAP: dict[str, type[WPState]] = {
    "genesis": GenesisState,
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
