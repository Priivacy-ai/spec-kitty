"""Transition matrix, guard conditions, alias resolution, and validation.

Implements the 9-lane state machine, its legal transition pairs,
guard condition functions, alias resolution, and force-override logic.
"""

from __future__ import annotations

from typing import Any

from specify_cli.status_lanes import CANONICAL_LANES as CANONICAL_LANES
from specify_cli.status_lanes import LANE_ALIASES, TERMINAL_LANES

from .models import GuardContext, Lane

# Boy Scout (DIRECTIVE_025): Extract duplicated error messages to constants.
_FORCE_REQUIRES_ACTOR_AND_REASON = "Force transitions require actor and reason"
_REVIEWER_APPROVAL_REQUIRED = "Transition to approved/done requires evidence (reviewer identity and approval reference)"

def _derive_allowed_transitions() -> frozenset[tuple[str, str]]:
    """Project the structural transition matrix from the State-pattern FSM.

    The concrete ``WPState`` classes (``status.wp_state``) each own their
    outbound edges via ``allowed_targets()``; this matrix is derived from them
    so the FSM is the single source of truth — there is no parallel,
    hand-maintained transition list to drift out of sync. Genesis seeds
    (``genesis -> planned`` / ``genesis -> canceled``) and every other edge
    are contributed by the corresponding state object.

    Guard conditions (actor, subtasks-complete, review result, done evidence,
    force) are a separate concern layered on top by :func:`validate_transition`
    via ``_GUARDED_TRANSITIONS``; this projection captures only edge existence.
    """
    from specify_cli.status.wp_state import wp_state_for  # noqa: PLC0415 -- avoid import cycle at module top

    return frozenset(
        (lane.value, target.value)
        for lane in Lane
        for target in wp_state_for(lane).allowed_targets()
    )


# Single source of truth: derived from the WPState FSM, not hand-maintained.
ALLOWED_TRANSITIONS: frozenset[tuple[str, str]] = _derive_allowed_transitions()

# Map of (from_lane, to_lane) -> guard function name
_GUARDED_TRANSITIONS: dict[tuple[str, str], str] = {
    ("planned", "claimed"): "actor_required",
    ("claimed", "in_progress"): "workspace_context",
    ("in_progress", "for_review"): "subtasks_complete_or_force",
    ("in_progress", "approved"): "reviewer_approval",
    # for_review -> in_review: reviewer must claim (actor-required with conflict detection)
    ("for_review", "in_review"): "actor_required_conflict_detection",
    # in_review outbound: all require ReviewResult
    ("in_review", "approved"): "review_result_required",
    ("in_review", "done"): "review_result_required",
    ("in_review", "in_progress"): "review_result_required",
    ("in_review", "planned"): "review_result_required",
    ("in_review", "blocked"): "review_result_required",
    ("in_review", "canceled"): "review_result_required",
    ("approved", "done"): "reviewer_approval",
    ("approved", "in_progress"): "review_ref_required",
    ("approved", "planned"): "review_ref_required",
    ("in_progress", "planned"): "reason_required",
}


def resolve_lane_alias(lane: str) -> str:
    """Resolve alias to canonical lane name. Returns input if not an alias."""
    normalized = lane.strip().lower()
    return LANE_ALIASES.get(normalized, normalized)


def is_terminal(lane: str) -> bool:
    """Check if a lane is terminal (done or canceled)."""
    return resolve_lane_alias(lane) in TERMINAL_LANES


def _guard_actor_required(actor: str | None) -> tuple[bool, str | None]:
    """Guard: planned -> claimed / for_review -> in_review requires actor identity."""
    if not actor or not actor.strip():
        return False, "Transition requires actor identity"
    return True, None


def _guard_actor_required_conflict_detection(
    actor: str | None,
    current_actor: str | None,
) -> tuple[bool, str | None]:
    """Guard: for_review -> in_review requires actor identity AND conflict check.

    Prevents a second reviewer from claiming a WP that is already being
    reviewed by a different actor.  When ``current_actor`` matches the
    requesting ``actor`` the transition is treated as a benign re-claim
    (idempotent).
    """
    if not actor or not actor.strip():
        return False, "Transition requires actor identity"
    if current_actor and current_actor.strip() and current_actor.strip() != actor.strip():
        return (
            False,
            f"WP already claimed for review by {current_actor.strip()}; cannot be claimed by {actor.strip()}",
        )
    return True, None


def _guard_workspace_context(
    workspace_context: str | None,
) -> tuple[bool, str | None]:
    """Guard: claimed -> in_progress requires active workspace context."""
    if not workspace_context or not workspace_context.strip():
        return (
            False,
            "Transition claimed -> in_progress requires workspace context",
        )
    return True, None


def _guard_subtasks_complete_or_force(
    subtasks_complete: bool | None,
    implementation_evidence_present: bool | None,
    force: bool,
) -> tuple[bool, str | None]:
    """Guard: in_progress -> for_review requires subtask completion and evidence."""
    if force:
        return True, None
    if subtasks_complete is not True:
        return (
            False,
            "Transition in_progress -> for_review requires completed subtasks or force with reason",
        )
    if implementation_evidence_present is not True:
        return (
            False,
            "Transition in_progress -> for_review requires implementation evidence or force with reason",
        )
    return True, None


def _guard_reviewer_approval(
    evidence: Any,
) -> tuple[bool, str | None]:
    """Guard: approval and done transitions require reviewer approval evidence."""
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


def _guard_review_ref_required(
    review_ref: str | None,
) -> tuple[bool, str | None]:
    """Guard: approved -> in_progress/planned requires review feedback reference."""
    if not review_ref or not review_ref.strip():
        return (
            False,
            "Transition requires review_ref (review feedback reference)",
        )
    return True, None


def _guard_reason_required(
    reason: str | None,
) -> tuple[bool, str | None]:
    """Guard: in_progress -> planned requires a reason."""
    if not reason or not reason.strip():
        return (
            False,
            "Transition in_progress -> planned requires reason",
        )
    return True, None


def _guard_review_result_required(
    review_result: Any,
) -> tuple[bool, str | None]:
    """Guard: all outbound in_review transitions require a ReviewResult."""
    if review_result is None:
        return (
            False,
            "Transition from in_review requires review_result (structured review outcome)",
        )
    reviewer = getattr(review_result, "reviewer", None)
    verdict = getattr(review_result, "verdict", None)
    reference = getattr(review_result, "reference", None)
    if not reviewer or not str(reviewer).strip():
        return (
            False,
            "Transition from in_review requires review_result with reviewer",
        )
    if not verdict or not str(verdict).strip():
        return (
            False,
            "Transition from in_review requires review_result with verdict",
        )
    if not reference or not str(reference).strip():
        return (
            False,
            "Transition from in_review requires review_result with reference",
        )
    return True, None


def _run_guard(
    from_lane: str,
    to_lane: str,
    ctx: GuardContext | None = None,
    /,
    **legacy_kwargs: Any,
) -> tuple[bool, str | None]:
    """Run the guard condition for a specific transition, if any."""
    if ctx is not None and legacy_kwargs:
        raise TypeError("_run_guard accepts either a GuardContext or legacy keyword arguments, not both")
    if ctx is None:
        ctx = GuardContext(**legacy_kwargs)
    elif not isinstance(ctx, GuardContext):
        raise TypeError("_run_guard expects a GuardContext or legacy keyword arguments")

    guard_name = _GUARDED_TRANSITIONS.get((from_lane, to_lane))
    if guard_name is None:
        return True, None

    if guard_name == "actor_required":
        return _guard_actor_required(ctx.actor)
    elif guard_name == "actor_required_conflict_detection":
        return _guard_actor_required_conflict_detection(ctx.actor, ctx.current_actor)
    elif guard_name == "workspace_context":
        return _guard_workspace_context(ctx.workspace_context)
    elif guard_name == "subtasks_complete_or_force":
        return _guard_subtasks_complete_or_force(
            ctx.subtasks_complete,
            ctx.implementation_evidence_present,
            ctx.force,
        )
    elif guard_name == "reviewer_approval":
        return _guard_reviewer_approval(ctx.evidence)
    elif guard_name == "review_ref_required":
        return _guard_review_ref_required(ctx.review_ref)
    elif guard_name == "reason_required":
        return _guard_reason_required(ctx.reason)
    elif guard_name == "review_result_required":
        return _guard_review_result_required(ctx.review_result)

    return True, None


def validate_transition(
    from_lane: str,
    to_lane: str,
    ctx: GuardContext | None = None,
) -> tuple[bool, str | None]:
    """Validate a lane transition. Returns (ok, error_message).

    Resolves aliases, checks the transition matrix, runs guard conditions,
    and validates force-override requirements.
    """
    ctx = ctx or GuardContext()
    resolved_from = resolve_lane_alias(from_lane)
    resolved_to = resolve_lane_alias(to_lane)

    # Validate that resolved lanes are canonical
    try:
        Lane(resolved_from)
    except ValueError:
        return False, f"Unknown lane: {from_lane}"
    try:
        Lane(resolved_to)
    except ValueError:
        return False, f"Unknown lane: {to_lane}"

    pair = (resolved_from, resolved_to)

    if pair not in ALLOWED_TRANSITIONS:
        if ctx.force:
            # Force can override any transition, but requires actor + reason
            if not ctx.actor or not ctx.actor.strip():
                return (
                    False,
                    _FORCE_REQUIRES_ACTOR_AND_REASON,
                )
            if not ctx.reason or not ctx.reason.strip():
                return (
                    False,
                    _FORCE_REQUIRES_ACTOR_AND_REASON,
                )
            return True, None
        return (
            False,
            f"Illegal transition: {resolved_from} -> {resolved_to}",
        )

    # For allowed transitions, run guard conditions
    # Force bypasses guards (but force still requires actor + reason for audit)
    if ctx.force:
        if not ctx.actor or not ctx.actor.strip():
            return False, _FORCE_REQUIRES_ACTOR_AND_REASON
        if not ctx.reason or not ctx.reason.strip():
            return False, _FORCE_REQUIRES_ACTOR_AND_REASON
        return True, None

    return _run_guard(resolved_from, resolved_to, ctx)
