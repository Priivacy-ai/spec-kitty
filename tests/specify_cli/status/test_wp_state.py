"""Property tests: WPState transition matrix and guard equivalence.

T025 — Transition matrix equivalence: proves that WPState.allowed_targets()
produces the identical transition matrix as the existing ALLOWED_TRANSITIONS.

T026 — Guard equivalence: proves that WPState.can_transition_to() guard
outcomes match _run_guard() for all guarded transition combinations.
"""

from __future__ import annotations

import pytest

from specify_cli.status.models import (
    DoneEvidence,
    Lane,
    RepoEvidence,
    ReviewApproval,
    ReviewResult,
)
from specify_cli.status.transition_context import TransitionContext
from specify_cli.status.transitions import ALLOWED_TRANSITIONS, _run_guard
from specify_cli.status.wp_state import (
    InReviewState,
    InvalidTransitionError,
    WPState,
    wp_state_for,
)

ALL_LANES = list(Lane)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _mock_done_evidence() -> DoneEvidence:
    return DoneEvidence(
        review=ReviewApproval(
            reviewer="test-reviewer",
            verdict="approved",
            reference="review-ref-123",
        ),
        repos=[
            RepoEvidence(
                repo="test-repo",
                branch="main",
                commit="abc1234",
            ),
        ],
    )


def _mock_review_result(
    verdict: str = "approved",
) -> ReviewResult:
    return ReviewResult(
        reviewer="test-reviewer",
        verdict=verdict,
        reference="review-ref-123",
    )


def _minimal_context_for(source: Lane, target: Lane) -> TransitionContext:
    """Build a TransitionContext that satisfies guards for the given pair."""
    kwargs: dict = {"actor": "test-agent"}

    # planned -> claimed: actor_required (already set)
    # claimed -> in_progress: workspace_context
    if source == Lane.CLAIMED and target == Lane.IN_PROGRESS:
        kwargs["workspace_context"] = "worktree"

    # in_progress -> for_review: subtasks_complete + implementation_evidence_present
    if source == Lane.IN_PROGRESS and target == Lane.FOR_REVIEW:
        kwargs["subtasks_complete"] = True
        kwargs["implementation_evidence_present"] = True

    # in_progress -> approved: reviewer_approval (evidence)
    if source == Lane.IN_PROGRESS and target == Lane.APPROVED:
        kwargs["evidence"] = _mock_done_evidence()

    # in_progress -> planned: reason_required
    if source == Lane.IN_PROGRESS and target == Lane.PLANNED:
        kwargs["reason"] = "test regression reason"

    # for_review -> in_review: actor_required (already set)

    # in_review -> *: review_result required (FR-012c)
    if source == Lane.IN_REVIEW:
        kwargs["review_result"] = _mock_review_result()

    # approved -> done: reviewer_approval (evidence)
    if source == Lane.APPROVED and target == Lane.DONE:
        kwargs["evidence"] = _mock_done_evidence()

    # approved -> in_progress/planned: review_ref_required
    if source == Lane.APPROVED and target in (Lane.IN_PROGRESS, Lane.PLANNED):
        kwargs["review_ref"] = "review-ref-456"

    return TransitionContext(**kwargs)


# ---------------------------------------------------------------------------
# T025: Transition matrix equivalence
# ---------------------------------------------------------------------------


class TestTransitionMatrixEquivalence:
    """WPState.allowed_targets() matches ALLOWED_TRANSITIONS exactly."""

    def test_allowed_targets_matches_allowed_transitions(self):
        """Every state's allowed_targets() matches ALLOWED_TRANSITIONS exactly."""
        for source_lane in ALL_LANES:
            state = wp_state_for(source_lane)
            # Derive expected targets from ALLOWED_TRANSITIONS
            expected = frozenset(Lane(to_lane) for from_lane, to_lane in ALLOWED_TRANSITIONS if from_lane == source_lane.value)
            actual = state.allowed_targets()
            assert actual == expected, (
                f"Mismatch for {source_lane}: WPState says {sorted(str(l) for l in actual)}, ALLOWED_TRANSITIONS says {sorted(str(l) for l in expected)}"
            )

    def test_all_allowed_pairs(self):
        """Enumerate all allowed pairs; each state.can_transition_to returns True."""
        for from_lane_str, to_lane_str in ALLOWED_TRANSITIONS:
            source_lane = Lane(from_lane_str)
            target_lane = Lane(to_lane_str)
            state = wp_state_for(source_lane)
            ctx = _minimal_context_for(source_lane, target_lane)
            assert state.can_transition_to(target_lane, ctx), f"{source_lane} -> {target_lane} should be allowed (ctx: actor={ctx.actor}, force={ctx.force})"

    def test_disallowed_pairs(self):
        """All pairs NOT in ALLOWED_TRANSITIONS are rejected."""
        allowed_set = {(Lane(f), Lane(t)) for f, t in ALLOWED_TRANSITIONS}
        for source_lane in ALL_LANES:
            state = wp_state_for(source_lane)
            for target_lane in ALL_LANES:
                if (source_lane, target_lane) not in allowed_set:
                    ctx = _minimal_context_for(source_lane, target_lane)
                    assert not state.can_transition_to(target_lane, ctx), f"{source_lane} -> {target_lane} should be disallowed"

    def test_transition_count(self):
        """Total transition count from WPState matches ALLOWED_TRANSITIONS."""
        wp_state_count = sum(len(wp_state_for(lane).allowed_targets()) for lane in ALL_LANES)
        assert wp_state_count == len(ALLOWED_TRANSITIONS)


class TestInReviewPromotion:
    """in_review is a first-class lane, not an alias."""

    def test_in_review_is_first_class_lane(self):
        """in_review has its own InReviewState, not aliased to ForReviewState."""
        state = wp_state_for("in_review")
        assert isinstance(state, InReviewState)
        assert state.lane == Lane.IN_REVIEW
        assert state.progress_bucket() == "review"
        assert state.display_category() == "In Progress"

    def test_for_review_outbound_restricted(self):
        """for_review can only transition to in_review, blocked, canceled."""
        state = wp_state_for("for_review")
        allowed = state.allowed_targets()
        assert Lane.IN_REVIEW in allowed
        assert Lane.BLOCKED in allowed
        assert Lane.CANCELED in allowed
        # for_review should NOT directly transition to done, approved, etc.
        assert Lane.DONE not in allowed
        assert Lane.APPROVED not in allowed
        assert Lane.IN_PROGRESS not in allowed
        assert Lane.PLANNED not in allowed

    def test_in_review_outbound_all_require_review_result(self):
        """All outbound from in_review require ReviewResult in context."""
        state = wp_state_for("in_review")
        # Without review_result, all transitions should fail
        ctx_no_result = TransitionContext(actor="test-agent")
        for target in state.allowed_targets():
            assert not state.can_transition_to(target, ctx_no_result), f"in_review -> {target} should require review_result"

    def test_doing_alias_resolves_to_in_progress(self):
        """doing alias resolves to InProgressState, not a DoingState."""
        state = wp_state_for("doing")
        assert state.lane == Lane.IN_PROGRESS
        assert state.__class__.__name__ == "InProgressState"

    def test_in_review_in_lane_enum(self):
        """Lane.IN_REVIEW exists as a proper enum member."""
        assert Lane.IN_REVIEW.value == "in_review"
        assert Lane("in_review") == Lane.IN_REVIEW


class TestStateProperties:
    """Verify properties of all 9 concrete states."""

    @pytest.mark.parametrize(
        "lane_str,expected_terminal",
        [
            ("planned", False),
            ("claimed", False),
            ("in_progress", False),
            ("for_review", False),
            ("in_review", False),
            ("approved", False),
            ("done", True),
            ("blocked", False),
            ("canceled", True),
        ],
    )
    def test_is_terminal(self, lane_str: str, expected_terminal: bool):
        state = wp_state_for(lane_str)
        assert state.is_terminal == expected_terminal

    @pytest.mark.parametrize(
        "lane_str,expected_blocked",
        [
            ("planned", False),
            ("claimed", False),
            ("in_progress", False),
            ("for_review", False),
            ("in_review", False),
            ("approved", False),
            ("done", False),
            ("blocked", True),
            ("canceled", False),
        ],
    )
    def test_is_blocked(self, lane_str: str, expected_blocked: bool):
        state = wp_state_for(lane_str)
        assert state.is_blocked == expected_blocked

    @pytest.mark.parametrize(
        "lane_str,expected_bucket",
        [
            ("planned", "not_started"),
            ("claimed", "in_flight"),
            ("in_progress", "in_flight"),
            ("for_review", "review"),
            ("in_review", "review"),
            ("approved", "review"),
            ("done", "terminal"),
            ("blocked", "in_flight"),
            ("canceled", "terminal"),
        ],
    )
    def test_progress_bucket(self, lane_str: str, expected_bucket: str):
        state = wp_state_for(lane_str)
        assert state.progress_bucket() == expected_bucket

    @pytest.mark.parametrize(
        "lane_str,expected_category",
        [
            ("planned", "Planned"),
            ("claimed", "In Progress"),
            ("in_progress", "In Progress"),
            ("for_review", "Review"),
            ("in_review", "In Progress"),
            ("approved", "Approved"),
            ("done", "Done"),
            ("blocked", "Blocked"),
            ("canceled", "Canceled"),
        ],
    )
    def test_display_category(self, lane_str: str, expected_category: str):
        state = wp_state_for(lane_str)
        assert state.display_category() == expected_category

    def test_unknown_lane_raises(self):
        """wp_state_for raises ValueError for unknown lane."""
        with pytest.raises(ValueError, match="Unknown lane"):
            wp_state_for("nonexistent")


class TestTransitionMethod:
    """WPState.transition() returns new state or raises InvalidTransitionError."""

    def test_valid_transition_returns_new_state(self):
        state = wp_state_for("planned")
        ctx = TransitionContext(actor="test-agent")
        new_state = state.transition(Lane.CLAIMED, ctx)
        assert new_state.lane == Lane.CLAIMED

    def test_invalid_transition_raises(self):
        state = wp_state_for("planned")
        ctx = TransitionContext(actor="test-agent")
        with pytest.raises(InvalidTransitionError) as exc_info:
            state.transition(Lane.DONE, ctx)
        assert exc_info.value.source == Lane.PLANNED
        assert exc_info.value.target == Lane.DONE

    def test_terminal_state_cannot_transition(self):
        state = wp_state_for("done")
        ctx = TransitionContext(actor="test-agent")
        for target in ALL_LANES:
            with pytest.raises(InvalidTransitionError):
                state.transition(target, ctx)


# ---------------------------------------------------------------------------
# T026: Guard equivalence
# ---------------------------------------------------------------------------


class TestGuardEquivalence:
    """WPState.can_transition_to() matches _run_guard() for all guarded combos."""

    def test_planned_to_claimed_actor_required(self):
        """planned -> claimed requires actor."""
        state = wp_state_for("planned")
        # With actor
        ctx = TransitionContext(actor="test-agent")
        assert state.can_transition_to(Lane.CLAIMED, ctx) is True
        old_ok, _ = _run_guard(
            "planned",
            "claimed",
            actor="test-agent",
            workspace_context=None,
            subtasks_complete=None,
            implementation_evidence_present=None,
            reason=None,
            review_ref=None,
            evidence=None,
            force=False,
        )
        assert old_ok is True

        # Without actor
        ctx_no_actor = TransitionContext(actor="")
        assert state.can_transition_to(Lane.CLAIMED, ctx_no_actor) is False
        old_ok2, _ = _run_guard(
            "planned",
            "claimed",
            actor="",
            workspace_context=None,
            subtasks_complete=None,
            implementation_evidence_present=None,
            reason=None,
            review_ref=None,
            evidence=None,
            force=False,
        )
        assert old_ok2 is False

    def test_claimed_to_in_progress_workspace_required(self):
        """claimed -> in_progress requires workspace_context."""
        state = wp_state_for("claimed")
        # With workspace
        ctx = TransitionContext(actor="test", workspace_context="worktree")
        assert state.can_transition_to(Lane.IN_PROGRESS, ctx) is True
        old_ok, _ = _run_guard(
            "claimed",
            "in_progress",
            actor="test",
            workspace_context="worktree",
            subtasks_complete=None,
            implementation_evidence_present=None,
            reason=None,
            review_ref=None,
            evidence=None,
            force=False,
        )
        assert old_ok is True

        # Without workspace
        ctx_no_ws = TransitionContext(actor="test")
        assert state.can_transition_to(Lane.IN_PROGRESS, ctx_no_ws) is False
        old_ok2, _ = _run_guard(
            "claimed",
            "in_progress",
            actor="test",
            workspace_context=None,
            subtasks_complete=None,
            implementation_evidence_present=None,
            reason=None,
            review_ref=None,
            evidence=None,
            force=False,
        )
        assert old_ok2 is False

    def test_in_progress_to_for_review_subtasks_required(self):
        """in_progress -> for_review requires subtasks complete and evidence."""
        state = wp_state_for("in_progress")

        # Both satisfied
        ctx_ok = TransitionContext(
            actor="test",
            subtasks_complete=True,
            implementation_evidence_present=True,
        )
        assert state.can_transition_to(Lane.FOR_REVIEW, ctx_ok) is True

        # Missing subtasks
        ctx_no_sub = TransitionContext(
            actor="test",
            subtasks_complete=False,
            implementation_evidence_present=True,
        )
        assert state.can_transition_to(Lane.FOR_REVIEW, ctx_no_sub) is False

        # Missing evidence
        ctx_no_ev = TransitionContext(
            actor="test",
            subtasks_complete=True,
            implementation_evidence_present=False,
        )
        assert state.can_transition_to(Lane.FOR_REVIEW, ctx_no_ev) is False

        # Force bypasses
        ctx_force = TransitionContext(
            actor="test",
            force=True,
        )
        assert state.can_transition_to(Lane.FOR_REVIEW, ctx_force) is True

    def test_in_progress_to_approved_reviewer_approval(self):
        """in_progress -> approved requires reviewer approval evidence."""
        state = wp_state_for("in_progress")
        evidence = _mock_done_evidence()

        ctx_ok = TransitionContext(actor="test", evidence=evidence)
        assert state.can_transition_to(Lane.APPROVED, ctx_ok) is True

        ctx_no_ev = TransitionContext(actor="test")
        assert state.can_transition_to(Lane.APPROVED, ctx_no_ev) is False

    def test_in_progress_to_planned_reason_required(self):
        """in_progress -> planned requires reason."""
        state = wp_state_for("in_progress")

        ctx_ok = TransitionContext(actor="test", reason="test reason")
        assert state.can_transition_to(Lane.PLANNED, ctx_ok) is True

        ctx_no_reason = TransitionContext(actor="test")
        assert state.can_transition_to(Lane.PLANNED, ctx_no_reason) is False

    def test_for_review_to_in_review_actor_required(self):
        """for_review -> in_review requires actor (FR-012b)."""
        state = wp_state_for("for_review")

        ctx_ok = TransitionContext(actor="reviewer-agent")
        assert state.can_transition_to(Lane.IN_REVIEW, ctx_ok) is True

        ctx_no_actor = TransitionContext(actor="")
        assert state.can_transition_to(Lane.IN_REVIEW, ctx_no_actor) is False

    def test_for_review_to_in_review_conflict_detection_rejects_double_claim(self):
        """for_review -> in_review rejects a second reviewer when another already holds it."""
        state = wp_state_for("for_review")

        ctx_conflict = TransitionContext(
            actor="reviewer-B",
            current_actor="reviewer-A",
        )
        assert state.can_transition_to(Lane.IN_REVIEW, ctx_conflict) is False

    def test_for_review_to_in_review_same_actor_reclaim_allowed(self):
        """for_review -> in_review permits idempotent re-claim by the same actor."""
        state = wp_state_for("for_review")

        ctx_same = TransitionContext(
            actor="reviewer-A",
            current_actor="reviewer-A",
        )
        assert state.can_transition_to(Lane.IN_REVIEW, ctx_same) is True

    def test_for_review_to_in_review_no_current_actor_allowed(self):
        """for_review -> in_review succeeds when no prior reviewer is recorded."""
        state = wp_state_for("for_review")

        ctx_fresh = TransitionContext(actor="reviewer-A")
        assert state.can_transition_to(Lane.IN_REVIEW, ctx_fresh) is True

    def test_for_review_to_in_review_conflict_detection_guard_equivalence(self):
        """Guard equivalence: _run_guard and WPState agree on conflict detection."""
        state = wp_state_for("for_review")

        # Case 1: different actor -> both reject
        ctx_conflict = TransitionContext(actor="reviewer-B", current_actor="reviewer-A")
        assert state.can_transition_to(Lane.IN_REVIEW, ctx_conflict) is False
        old_ok, _ = _run_guard(
            "for_review",
            "in_review",
            actor="reviewer-B",
            workspace_context=None,
            subtasks_complete=None,
            implementation_evidence_present=None,
            reason=None,
            review_ref=None,
            evidence=None,
            force=False,
            current_actor="reviewer-A",
        )
        assert old_ok is False

        # Case 2: same actor -> both accept
        ctx_same = TransitionContext(actor="reviewer-A", current_actor="reviewer-A")
        assert state.can_transition_to(Lane.IN_REVIEW, ctx_same) is True
        old_ok2, _ = _run_guard(
            "for_review",
            "in_review",
            actor="reviewer-A",
            workspace_context=None,
            subtasks_complete=None,
            implementation_evidence_present=None,
            reason=None,
            review_ref=None,
            evidence=None,
            force=False,
            current_actor="reviewer-A",
        )
        assert old_ok2 is True

        # Case 3: no current_actor -> both accept
        ctx_fresh2 = TransitionContext(actor="reviewer-A")
        assert state.can_transition_to(Lane.IN_REVIEW, ctx_fresh2) is True
        old_ok3, _ = _run_guard(
            "for_review",
            "in_review",
            actor="reviewer-A",
            workspace_context=None,
            subtasks_complete=None,
            implementation_evidence_present=None,
            reason=None,
            review_ref=None,
            evidence=None,
            force=False,
        )
        assert old_ok3 is True

    @pytest.mark.parametrize(
        "target",
        [
            Lane.APPROVED,
            Lane.DONE,
            Lane.IN_PROGRESS,
            Lane.PLANNED,
            Lane.BLOCKED,
            Lane.CANCELED,
        ],
    )
    def test_in_review_outbound_requires_review_result(self, target: Lane):
        """All in_review outbound transitions require ReviewResult (FR-012c)."""
        state = wp_state_for("in_review")

        # With review_result
        ctx_ok = TransitionContext(actor="test", review_result=_mock_review_result())
        assert state.can_transition_to(target, ctx_ok) is True

        # Without review_result
        ctx_no_rr = TransitionContext(actor="test")
        assert state.can_transition_to(target, ctx_no_rr) is False

    def test_in_review_review_result_requires_all_fields(self):
        """ReviewResult must have reviewer, verdict, and reference."""
        state = wp_state_for("in_review")

        # Missing reviewer
        rr_no_reviewer = ReviewResult(reviewer="", verdict="approved", reference="ref")
        ctx = TransitionContext(actor="test", review_result=rr_no_reviewer)
        assert state.can_transition_to(Lane.APPROVED, ctx) is False

        # Missing verdict
        rr_no_verdict = ReviewResult(reviewer="agent", verdict="", reference="ref")
        ctx2 = TransitionContext(actor="test", review_result=rr_no_verdict)
        assert state.can_transition_to(Lane.APPROVED, ctx2) is False

        # Missing reference
        rr_no_ref = ReviewResult(reviewer="agent", verdict="approved", reference="")
        ctx3 = TransitionContext(actor="test", review_result=rr_no_ref)
        assert state.can_transition_to(Lane.APPROVED, ctx3) is False

    def test_approved_to_done_requires_evidence(self):
        """approved -> done requires reviewer approval evidence."""
        state = wp_state_for("approved")

        ctx_ok = TransitionContext(actor="test", evidence=_mock_done_evidence())
        assert state.can_transition_to(Lane.DONE, ctx_ok) is True

        ctx_no_ev = TransitionContext(actor="test")
        assert state.can_transition_to(Lane.DONE, ctx_no_ev) is False

    def test_approved_to_in_progress_requires_review_ref(self):
        """approved -> in_progress requires review_ref."""
        state = wp_state_for("approved")

        ctx_ok = TransitionContext(actor="test", review_ref="ref-123")
        assert state.can_transition_to(Lane.IN_PROGRESS, ctx_ok) is True

        ctx_no_ref = TransitionContext(actor="test")
        assert state.can_transition_to(Lane.IN_PROGRESS, ctx_no_ref) is False

    def test_approved_to_planned_requires_review_ref(self):
        """approved -> planned requires review_ref."""
        state = wp_state_for("approved")

        ctx_ok = TransitionContext(actor="test", review_ref="ref-456")
        assert state.can_transition_to(Lane.PLANNED, ctx_ok) is True

        ctx_no_ref = TransitionContext(actor="test")
        assert state.can_transition_to(Lane.PLANNED, ctx_no_ref) is False

    def test_unguarded_transitions_always_pass(self):
        """Transitions without guards pass with minimal context."""
        unguarded_pairs = [
            (Lane.PLANNED, Lane.BLOCKED),
            (Lane.PLANNED, Lane.CANCELED),
            (Lane.CLAIMED, Lane.BLOCKED),
            (Lane.CLAIMED, Lane.CANCELED),
            (Lane.IN_PROGRESS, Lane.BLOCKED),
            (Lane.IN_PROGRESS, Lane.CANCELED),
            (Lane.FOR_REVIEW, Lane.BLOCKED),
            (Lane.FOR_REVIEW, Lane.CANCELED),
            (Lane.APPROVED, Lane.BLOCKED),
            (Lane.APPROVED, Lane.CANCELED),
            (Lane.BLOCKED, Lane.IN_PROGRESS),
            (Lane.BLOCKED, Lane.CANCELED),
        ]
        ctx = TransitionContext(actor="test")
        for source, target in unguarded_pairs:
            state = wp_state_for(source)
            assert state.can_transition_to(target, ctx), f"{source} -> {target} should be unguarded and allowed"
