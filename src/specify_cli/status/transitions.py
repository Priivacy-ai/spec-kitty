"""Transition matrix, guard conditions, alias resolution, and validation.

Implements the 7-lane state machine with 17 legal transition pairs,
guard condition functions, alias resolution, and force-override logic.
"""

from __future__ import annotations

from typing import Any

from .models import Lane

CANONICAL_LANES: tuple[str, ...] = (
    "planned",
    "claimed",
    "in_progress",
    "for_review",
    "done",
    "blocked",
    "canceled",
)

LANE_ALIASES: dict[str, str] = {"doing": "in_progress"}

TERMINAL_LANES: frozenset[str] = frozenset({"done", "canceled"})

ALLOWED_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("planned", "claimed"),
        ("claimed", "in_progress"),
        ("in_progress", "for_review"),
        ("for_review", "done"),
        ("for_review", "in_progress"),
        ("for_review", "planned"),
        ("in_progress", "planned"),
        ("planned", "blocked"),
        ("claimed", "blocked"),
        ("in_progress", "blocked"),
        ("for_review", "blocked"),
        ("blocked", "in_progress"),
        ("planned", "canceled"),
        ("claimed", "canceled"),
        ("in_progress", "canceled"),
        ("for_review", "canceled"),
        ("blocked", "canceled"),
    }
)

# Map of (from_lane, to_lane) -> guard function name
_GUARDED_TRANSITIONS: dict[tuple[str, str], str] = {
    ("planned", "claimed"): "actor_required",
    ("claimed", "in_progress"): "workspace_context",
    ("in_progress", "for_review"): "subtasks_complete_or_force",
    ("for_review", "done"): "reviewer_approval",
    ("for_review", "in_progress"): "review_ref_required",
    ("for_review", "planned"): "review_ref_required",
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
    """Guard: planned -> claimed requires actor identity."""
    if not actor or not actor.strip():
        return False, "Transition planned -> claimed requires actor identity"
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
            "Transition in_progress -> for_review requires completed subtasks "
            "or force with reason",
        )
    if implementation_evidence_present is not True:
        return (
            False,
            "Transition in_progress -> for_review requires implementation evidence "
            "or force with reason",
        )
    return True, None


def _guard_reviewer_approval(
    evidence: Any,
) -> tuple[bool, str | None]:
    """Guard: for_review -> done requires reviewer approval evidence."""
    if evidence is None:
        return (
            False,
            "Transition for_review -> done requires evidence "
            "(reviewer identity and approval reference)",
        )
    review = getattr(evidence, "review", None)
    reviewer = getattr(review, "reviewer", None) if review is not None else None
    reference = getattr(review, "reference", None) if review is not None else None
    if not reviewer or not str(reviewer).strip():
        return (
            False,
            "Transition for_review -> done requires evidence "
            "(reviewer identity and approval reference)",
        )
    if not reference or not str(reference).strip():
        return (
            False,
            "Transition for_review -> done requires evidence "
            "(reviewer identity and approval reference)",
        )
    return True, None


def _guard_review_ref_required(
    review_ref: str | None,
) -> tuple[bool, str | None]:
    """Guard: for_review -> in_progress/planned requires review feedback reference."""
    if not review_ref or not review_ref.strip():
        return (
            False,
            "Transition from for_review requires review_ref "
            "(review feedback reference)",
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


def _run_guard(
    from_lane: str,
    to_lane: str,
    *,
    actor: str | None,
    workspace_context: str | None,
    subtasks_complete: bool | None,
    implementation_evidence_present: bool | None,
    reason: str | None,
    review_ref: str | None,
    evidence: Any,
    force: bool,
) -> tuple[bool, str | None]:
    """Run the guard condition for a specific transition, if any."""
    guard_name = _GUARDED_TRANSITIONS.get((from_lane, to_lane))
    if guard_name is None:
        return True, None

    if guard_name == "actor_required":
        return _guard_actor_required(actor)
    elif guard_name == "workspace_context":
        return _guard_workspace_context(workspace_context)
    elif guard_name == "subtasks_complete_or_force":
        return _guard_subtasks_complete_or_force(
            subtasks_complete,
            implementation_evidence_present,
            force,
        )
    elif guard_name == "reviewer_approval":
        return _guard_reviewer_approval(evidence)
    elif guard_name == "review_ref_required":
        return _guard_review_ref_required(review_ref)
    elif guard_name == "reason_required":
        return _guard_reason_required(reason)

    return True, None


def validate_transition(
    from_lane: str,
    to_lane: str,
    *,
    force: bool = False,
    actor: str | None = None,
    workspace_context: str | None = None,
    subtasks_complete: bool | None = None,
    implementation_evidence_present: bool | None = None,
    reason: str | None = None,
    review_ref: str | None = None,
    evidence: Any = None,
) -> tuple[bool, str | None]:
    """Validate a lane transition. Returns (ok, error_message).

    Resolves aliases, checks the transition matrix, runs guard conditions,
    and validates force-override requirements.
    """
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
        if force:
            # Force can override any transition, but requires actor + reason
            if not actor or not actor.strip():
                return (
                    False,
                    "Force transitions require actor and reason",
                )
            if not reason or not reason.strip():
                return (
                    False,
                    "Force transitions require actor and reason",
                )
            return True, None
        return (
            False,
            f"Illegal transition: {resolved_from} -> {resolved_to}",
        )

    # For allowed transitions, run guard conditions
    # Force bypasses guards (but force still requires actor + reason for audit)
    if force:
        if not actor or not actor.strip():
            return False, "Force transitions require actor and reason"
        if not reason or not reason.strip():
            return False, "Force transitions require actor and reason"
        return True, None

    return _run_guard(
        resolved_from,
        resolved_to,
        actor=actor,
        workspace_context=workspace_context,
        subtasks_complete=subtasks_complete,
        implementation_evidence_present=implementation_evidence_present,
        reason=reason,
        review_ref=review_ref,
        evidence=evidence,
        force=force,
    )
