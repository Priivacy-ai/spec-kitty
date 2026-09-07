"""TransitionContext unit tests (T027).

Tests construction, frozen semantics, value equality, and all fields.
"""

from __future__ import annotations

import pytest

from specify_cli.status.models import (
    DoneEvidence,
    ReviewApproval,
    ReviewResult,
)
from specify_cli.status.transition_context import TransitionContext


pytestmark = [pytest.mark.unit, pytest.mark.fast]

class TestTransitionContextConstruction:
    """TransitionContext construction and defaults."""

    def test_minimal_construction(self):
        ctx = TransitionContext(actor="agent")
        assert ctx.actor == "agent"
        assert ctx.force is False
        assert ctx.subtasks_complete is False
        assert ctx.workspace_context is None
        assert ctx.evidence is None
        assert ctx.review_ref is None
        assert ctx.review_result is None
        assert ctx.reason is None
        assert ctx.implementation_evidence_present is False

    def test_all_fields(self):
        evidence = DoneEvidence(
            review=ReviewApproval(reviewer="rev", verdict="approved", reference="ref"),
        )
        review_result = ReviewResult(reviewer="rev", verdict="approved", reference="ref")
        ctx = TransitionContext(
            actor="agent",
            workspace_context="worktree",
            subtasks_complete=True,
            evidence=evidence,
            review_ref="review-123",
            review_result=review_result,
            reason="blocked on upstream",
            force=True,
            implementation_evidence_present=True,
        )
        assert ctx.workspace_context == "worktree"
        assert ctx.subtasks_complete is True
        assert ctx.evidence is evidence
        assert ctx.review_ref == "review-123"
        assert ctx.review_result is review_result
        assert ctx.reason == "blocked on upstream"
        assert ctx.force is True
        assert ctx.implementation_evidence_present is True


class TestTransitionContextFrozen:
    """TransitionContext is immutable."""

    def test_frozen(self):
        ctx = TransitionContext(actor="agent")
        with pytest.raises(AttributeError):
            ctx.actor = "changed"  # type: ignore[misc]

    def test_frozen_force(self):
        ctx = TransitionContext(actor="agent", force=False)
        with pytest.raises(AttributeError):
            ctx.force = True  # type: ignore[misc]


class TestTransitionContextEquality:
    """TransitionContext value equality."""

    def test_equality(self):
        ctx1 = TransitionContext(actor="agent", force=True)
        ctx2 = TransitionContext(actor="agent", force=True)
        assert ctx1 == ctx2

    def test_inequality(self):
        ctx1 = TransitionContext(actor="agent", force=True)
        ctx2 = TransitionContext(actor="agent", force=False)
        assert ctx1 != ctx2

    def test_hash_consistency(self):
        ctx1 = TransitionContext(actor="agent", reason="test")
        ctx2 = TransitionContext(actor="agent", reason="test")
        assert hash(ctx1) == hash(ctx2)


class TestDependencyReadyField:
    """fsm-write-path-integrity WP04 (FR-012): the tri-state verdict field."""

    def test_defaults_to_none_no_verdict(self):
        assert TransitionContext(actor="agent").dependency_ready is None

    @pytest.mark.parametrize("verdict", [True, False, None])
    def test_round_trips_all_three_states(self, verdict):
        assert TransitionContext(actor="agent", dependency_ready=verdict).dependency_ready is verdict

    def test_participates_in_equality(self):
        assert TransitionContext(actor="agent", dependency_ready=False) != TransitionContext(actor="agent", dependency_ready=None)
