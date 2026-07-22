"""Contract: the WP-state FSM's review-rejection backward edges are force-free.

WP03 (mission ``sync-batch-400-poison-isolation``) pins question-2's decision:
the CLI transition FSM in ``specify_cli.status.wp_state`` is the *authoritative*
gate for backward review-rejection transitions. These edges are already legal
**without** ``force`` — the entry guards require review *evidence*
(``reason`` / ``review_ref`` / ``review_result``), never a guard-bypass
``force`` override. Forcing them would stamp a false guard-bypass and corrupt
provenance, so the CLI must NOT emit ``force`` on the review-rejection path.

That "the CLI command layer never emits ``force``" invariant is a *caller-side*
property and belongs in an explicitly-named CLI-command-layer test; it cannot be
observed from this status-FSM file, so it is recorded here only as this note.
What this file *does* pin, objectively, via the public transition API
(:meth:`WPState.check_transition` / :meth:`WPState.can_transition_to`), is:

  * these backward edges are legal with a no-force, evidence-only context, and
  * the guard verdict is **force-independent** — identical whether ``ctx.force``
    is left unset (default) or set explicitly to ``False``.

Server-matrix alignment: the server-side transition matrix is the drift here,
not the CLI FSM. It is realigned to this authoritative contract via SaaS#509.

FSM shape actually pinned (as observed through the public API — the prose
"``for_review``/``in_review`` -> earlier-lane, review_ref-only" is imprecise
about *which* states carry these edges; this test encodes the real graph):

  * ``in_progress -> planned`` — force-free, ``reason``-only (T012).
  * ``approved -> in_progress`` / ``approved -> planned`` — force-free,
    ``review_ref``-only (the genuinely review_ref-only backward edges).
  * ``in_review -> in_progress`` / ``in_review -> planned`` — force-free, but
    gated on a full structured ``review_result`` (not ``review_ref`` alone).
  * ``for_review`` has **no** backward edge; rejection routes
    ``for_review -> in_review -> {in_progress, planned}``. Pinned so that
    reintroducing a phantom ``for_review`` backward edge is caught as drift.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import pytest

from specify_cli.status.models import GuardContext, Lane, ReviewResult
from specify_cli.status.wp_state import wp_state_for

pytestmark = pytest.mark.fast

# --- Evidence-only, no-force contexts (force defaults to False on GuardContext) ---

_ACTOR = "claude"
_REVIEW_REF = "feedback://REVIEW-123"


def _reason_only() -> GuardContext:
    """Backward edge gated on a rejection ``reason`` (in_progress -> planned)."""
    return GuardContext(actor=_ACTOR, reason="rejected in review")


def _review_ref_only() -> GuardContext:
    """Backward edge gated on a ``review_ref`` only (approved -> earlier)."""
    return GuardContext(actor=_ACTOR, review_ref=_REVIEW_REF)


def _review_result() -> GuardContext:
    """Backward edge gated on a full structured ``review_result`` (in_review -> earlier)."""
    return GuardContext(
        actor=_ACTOR,
        review_ref=_REVIEW_REF,
        review_result=ReviewResult(
            reviewer="renata",
            verdict="changes_requested",
            reference=_REVIEW_REF,
        ),
    )


# Every force-free legal review-rejection backward edge: (from_lane, to_lane, ctx-factory).
_FORCE_FREE_REJECTION_EDGES = [
    ("in_progress", Lane.PLANNED, _reason_only),
    ("approved", Lane.IN_PROGRESS, _review_ref_only),
    ("approved", Lane.PLANNED, _review_ref_only),
    ("in_review", Lane.IN_PROGRESS, _review_result),
    ("in_review", Lane.PLANNED, _review_result),
]


# ---------------------------------------------------------------------------
# T012 — the core review-rejection backward edge is force-free legal
# ---------------------------------------------------------------------------


def test_t012_in_progress_to_planned_is_force_free_legal() -> None:
    """``in_progress -> planned`` is legal with a reason-only, no-force context."""
    ctx = _reason_only()
    assert ctx.force is False  # evidence-only context carries no force override
    assert wp_state_for("in_progress").check_transition(Lane.PLANNED, ctx) == (True, None)


# ---------------------------------------------------------------------------
# T013 — the review_ref / review_result backward edges are force-free legal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("target", [Lane.IN_PROGRESS, Lane.PLANNED])
def test_t013_approved_review_ref_only_backward_edges_are_force_free_legal(target: Lane) -> None:
    """``approved -> {in_progress, planned}`` legal with review_ref only, no force."""
    ctx = _review_ref_only()
    assert ctx.force is False
    state = wp_state_for("approved")
    assert state.check_transition(target, ctx) == (True, None)
    # Guard-aware boolean check is force-free by contract and agrees.
    assert state.can_transition_to(target, ctx) is True


@pytest.mark.parametrize("target", [Lane.IN_PROGRESS, Lane.PLANNED])
def test_t013_in_review_backward_edges_are_force_free_with_review_result(target: Lane) -> None:
    """``in_review -> {in_progress, planned}`` legal with a review_result, no force."""
    ctx = _review_result()
    assert ctx.force is False
    state = wp_state_for("in_review")
    assert state.check_transition(target, ctx) == (True, None)
    assert state.can_transition_to(target, ctx) is True


@pytest.mark.parametrize("target", [Lane.IN_PROGRESS, Lane.PLANNED])
def test_t013_in_review_rejection_needs_review_evidence_not_force(target: Lane) -> None:
    """``in_review`` rejection is gated on review evidence, NOT force.

    With only a ``review_ref`` (no structured ``review_result``) the guard
    rejects for a *review-evidence* reason — and adding ``force`` is not what
    makes the edge legal (that would be a guard bypass). This pins that the
    gate is review evidence, aligning with the force-free contract.
    """
    state = wp_state_for("in_review")
    ok, error = state.check_transition(target, _review_ref_only())
    assert ok is False
    assert error is not None
    assert "review_result" in error


def test_t013_for_review_has_no_backward_edge() -> None:
    """``for_review`` carries no backward edge; rejection routes via ``in_review``.

    Pinned so a phantom ``for_review -> {planned, in_progress}`` edge (which no
    context, force-free or otherwise, currently satisfies) is caught as drift.
    """
    state = wp_state_for("for_review")
    for target in (Lane.PLANNED, Lane.IN_PROGRESS):
        assert state.may_transition_to(target) is False
        ok, _ = state.check_transition(target, _review_ref_only())
        assert ok is False


# ---------------------------------------------------------------------------
# T014 — force-independence: identical verdict with force unset vs force=False
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("from_lane", "target", "ctx_factory"),
    _FORCE_FREE_REJECTION_EDGES,
    ids=lambda v: v if isinstance(v, str) else getattr(v, "value", v),
)
def test_t014_review_rejection_edges_are_force_independent(
    from_lane: str,
    target: Lane,
    ctx_factory: Callable[[], GuardContext],
) -> None:
    """Guard verdict is identical with ``force`` unset vs ``force=False``.

    Both resolve to ``(True, None)`` — the edge is legal on the non-force
    (guard) path, confirming the guard does not consult ``ctx.force`` to admit
    these backward review-rejection transitions.
    """
    ctx_unset = ctx_factory()
    assert ctx_unset.force is False  # unset -> GuardContext default
    ctx_false = replace(ctx_unset, force=False)

    state = wp_state_for(from_lane)
    verdict_unset = state.check_transition(target, ctx_unset)
    verdict_false = state.check_transition(target, ctx_false)

    assert verdict_unset == verdict_false == (True, None)
    # can_transition_to is force-free by contract and agrees on both contexts.
    assert state.can_transition_to(target, ctx_unset) is True
    assert state.can_transition_to(target, ctx_false) is True
