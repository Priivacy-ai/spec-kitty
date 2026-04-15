"""Unit tests for the transition matrix, alias resolution, and guard conditions.

These tests verify the 9-lane model constants and basic validate_transition
behaviour. Exhaustive transition-matrix and guard-equivalence coverage is
provided by the property tests in tests/specify_cli/status/test_wp_state.py.
"""

from __future__ import annotations

import pytest

from specify_cli.status.models import DoneEvidence, GuardContext, ReviewApproval, ReviewResult
from specify_cli.status.transitions import (
    ALLOWED_TRANSITIONS,
    CANONICAL_LANES,
    LANE_ALIASES,
    TERMINAL_LANES,
    is_terminal,
    resolve_lane_alias,
    validate_transition,
)

pytestmark = pytest.mark.fast


class TestConstants:
    def test_canonical_lanes_count(self) -> None:
        assert len(CANONICAL_LANES) == 9

    def test_allowed_transitions_count(self) -> None:
        assert len(ALLOWED_TRANSITIONS) == 27

    def test_terminal_lanes(self) -> None:
        assert frozenset({"done", "canceled"}) == TERMINAL_LANES

    def test_doing_alias(self) -> None:
        assert LANE_ALIASES == {
            "doing": "in_progress",
        }


class TestResolveAlias:
    def test_doing_resolves_to_in_progress(self) -> None:
        assert resolve_lane_alias("doing") == "in_progress"

    def test_in_review_is_first_class_lane(self) -> None:
        """in_review is no longer an alias — it resolves to itself."""
        assert resolve_lane_alias("in_review") == "in_review"

    def test_passthrough_canonical_lane(self) -> None:
        assert resolve_lane_alias("planned") == "planned"
        assert resolve_lane_alias("claimed") == "claimed"
        assert resolve_lane_alias("in_progress") == "in_progress"

    def test_case_insensitive(self) -> None:
        assert resolve_lane_alias("Doing") == "in_progress"
        assert resolve_lane_alias("DOING") == "in_progress"

    def test_strips_whitespace(self) -> None:
        assert resolve_lane_alias("  doing  ") == "in_progress"
        assert resolve_lane_alias("  planned  ") == "planned"


class TestIsTerminal:
    def test_done_is_terminal(self) -> None:
        assert is_terminal("done") is True

    def test_canceled_is_terminal(self) -> None:
        assert is_terminal("canceled") is True

    def test_in_progress_not_terminal(self) -> None:
        assert is_terminal("in_progress") is False

    def test_planned_not_terminal(self) -> None:
        assert is_terminal("planned") is False

    def test_doing_alias_not_terminal(self) -> None:
        assert is_terminal("doing") is False


class TestLegalTransitions:
    """Smoke tests for representative legal transitions.

    Full matrix coverage is in test_wp_state.py property tests.
    """

    @pytest.mark.parametrize(
        "from_lane,to_lane,kwargs",
        [
            ("planned", "claimed", {"actor": "agent-1"}),
            ("claimed", "in_progress", {"workspace_context": "worktree:/tmp/wt1"}),
            (
                "in_progress",
                "for_review",
                {
                    "subtasks_complete": True,
                    "implementation_evidence_present": True,
                },
            ),
            # for_review -> in_review (reviewer claims review)
            ("for_review", "in_review", {"actor": "reviewer-1"}),
            # in_review outbound (all require review_result)
            (
                "in_review",
                "approved",
                {
                    "review_result": ReviewResult(reviewer="r", verdict="approved", reference="ref"),
                },
            ),
            (
                "in_review",
                "done",
                {
                    "review_result": ReviewResult(reviewer="r", verdict="approved", reference="ref"),
                },
            ),
            (
                "in_review",
                "in_progress",
                {
                    "review_result": ReviewResult(reviewer="r", verdict="changes_requested", reference="feedback://1"),
                },
            ),
            (
                "in_review",
                "planned",
                {
                    "review_result": ReviewResult(reviewer="r", verdict="changes_requested", reference="feedback://2"),
                },
            ),
            (
                "approved",
                "done",
                {"evidence": DoneEvidence(review=ReviewApproval(reviewer="r", verdict="approved", reference="ref"))},
            ),
            ("approved", "in_progress", {"review_ref": "feedback-789"}),
            ("approved", "planned", {"review_ref": "feedback-999"}),
            ("in_progress", "planned", {"reason": "reassigning"}),
            ("planned", "blocked", {}),
            ("claimed", "blocked", {}),
            ("in_progress", "blocked", {}),
            ("for_review", "blocked", {}),
            ("in_review", "blocked", {"review_result": ReviewResult(reviewer="r", verdict="blocked", reference="ref")}),
            ("approved", "blocked", {}),
            ("blocked", "in_progress", {}),
            ("planned", "canceled", {}),
            ("claimed", "canceled", {}),
            ("in_progress", "canceled", {}),
            ("for_review", "canceled", {}),
            ("in_review", "canceled", {"review_result": ReviewResult(reviewer="r", verdict="canceled", reference="ref")}),
            ("approved", "canceled", {}),
            ("blocked", "canceled", {}),
        ],
    )
    def test_legal_transition_accepted(
        self,
        from_lane: str,
        to_lane: str,
        kwargs: dict,
    ) -> None:
        ok, error = validate_transition(from_lane, to_lane, GuardContext(**kwargs))
        assert ok is True, f"Expected ok for {from_lane}->{to_lane}: {error}"
        assert error is None


class TestIllegalTransitions:
    @pytest.mark.parametrize(
        "from_lane,to_lane",
        [
            ("planned", "done"),
            ("planned", "in_progress"),
            ("planned", "for_review"),
            ("planned", "approved"),
            ("claimed", "for_review"),
            ("claimed", "approved"),
            ("claimed", "done"),
            ("claimed", "planned"),
            # for_review outbound: only in_review, blocked, canceled are legal
            ("for_review", "approved"),
            ("for_review", "done"),
            ("for_review", "in_progress"),
            ("for_review", "planned"),
            ("done", "planned"),
            ("done", "in_progress"),
            ("done", "for_review"),
            ("done", "approved"),
            ("canceled", "planned"),
            ("canceled", "in_progress"),
            ("blocked", "planned"),
            ("blocked", "for_review"),
            ("blocked", "approved"),
            ("blocked", "done"),
        ],
    )
    def test_illegal_transition_rejected(self, from_lane: str, to_lane: str) -> None:
        ok, error = validate_transition(from_lane, to_lane, GuardContext())
        assert ok is False
        assert error is not None
        assert "Illegal transition" in error


class TestForceOverride:
    def test_force_allows_terminal_exit(self) -> None:
        ok, error = validate_transition(
            "done",
            "planned",
            GuardContext(force=True, actor="admin", reason="reopening"),
        )
        assert ok is True
        assert error is None

    def test_force_without_actor_rejected(self) -> None:
        ok, error = validate_transition("done", "planned", GuardContext(force=True, reason="reopening"))
        assert ok is False
        assert "actor and reason" in error

    def test_force_without_reason_rejected(self) -> None:
        ok, error = validate_transition("done", "planned", GuardContext(force=True, actor="admin"))
        assert ok is False
        assert "actor and reason" in error

    def test_force_with_empty_actor_rejected(self) -> None:
        ok, error = validate_transition("done", "planned", GuardContext(force=True, actor="", reason="reopening"))
        assert ok is False

    def test_force_with_empty_reason_rejected(self) -> None:
        ok, error = validate_transition("done", "planned", GuardContext(force=True, actor="admin", reason=""))
        assert ok is False

    def test_force_on_legal_transition_bypasses_guards(self) -> None:
        # in_review -> done normally requires review_result, but force bypasses
        ok, error = validate_transition(
            "in_review",
            "done",
            GuardContext(force=True, actor="admin", reason="emergency override"),
        )
        assert ok is True
        assert error is None


class TestGuardConditions:
    def test_actor_required_for_claim(self) -> None:
        ok, error = validate_transition("planned", "claimed", GuardContext())
        assert ok is False
        assert "actor" in error.lower()

    def test_actor_required_for_claim_empty_string(self) -> None:
        ok, error = validate_transition("planned", "claimed", GuardContext(actor=""))
        assert ok is False

    def test_review_result_for_in_review_to_in_progress(self) -> None:
        """in_review -> in_progress requires review_result."""
        ok, error = validate_transition("in_review", "in_progress", GuardContext())
        assert ok is False
        assert "review_result" in error.lower()

    def test_review_result_for_in_review_to_planned(self) -> None:
        """in_review -> planned requires review_result."""
        ok, error = validate_transition("in_review", "planned", GuardContext())
        assert ok is False
        assert "review_result" in error.lower()

    def test_review_result_for_in_review_to_planned_accepted(self) -> None:
        ok, error = validate_transition(
            "in_review",
            "planned",
            GuardContext(review_result=ReviewResult(reviewer="r", verdict="changes_requested", reference="feedback://1")),
        )
        assert ok is True
        assert error is None

    def test_review_result_for_in_review_to_planned_empty_reviewer_rejected(self) -> None:
        ok, error = validate_transition(
            "in_review",
            "planned",
            GuardContext(review_result=ReviewResult(reviewer="", verdict="changes_requested", reference="feedback://1")),
        )
        assert ok is False
        assert "reviewer" in error.lower()

    def test_review_result_for_in_review_to_planned_empty_reference_rejected(self) -> None:
        ok, error = validate_transition(
            "in_review",
            "planned",
            GuardContext(review_result=ReviewResult(reviewer="r", verdict="changes_requested", reference="   ")),
        )
        assert ok is False
        assert "reference" in error.lower()

    def test_review_result_for_in_review_to_approved(self) -> None:
        """in_review -> approved requires review_result."""
        ok, error = validate_transition("in_review", "approved", GuardContext())
        assert ok is False
        assert "review_result" in error.lower()

    def test_review_result_for_in_review_to_approved_with_result(self) -> None:
        ok, error = validate_transition(
            "in_review",
            "approved",
            GuardContext(review_result=ReviewResult(reviewer="r", verdict="approved", reference="PR#42")),
        )
        assert ok is True

    def test_workspace_context_required_for_claimed_to_in_progress(self) -> None:
        ok, error = validate_transition("claimed", "in_progress", GuardContext())
        assert ok is False
        assert "workspace context" in error.lower()

    def test_workspace_context_provided(self) -> None:
        ok, error = validate_transition(
            "claimed",
            "in_progress",
            GuardContext(workspace_context="worktree:/tmp/wt1"),
        )
        assert ok is True

    def test_subtasks_required_for_in_progress_to_for_review(self) -> None:
        ok, error = validate_transition(
            "in_progress",
            "for_review",
            GuardContext(implementation_evidence_present=True),
        )
        assert ok is False
        assert "completed subtasks" in error.lower()

    def test_implementation_evidence_required_for_in_progress_to_for_review(self) -> None:
        ok, error = validate_transition(
            "in_progress",
            "for_review",
            GuardContext(subtasks_complete=True),
        )
        assert ok is False
        assert "implementation evidence" in error.lower()

    def test_subtasks_and_implementation_evidence_allow_for_review(self) -> None:
        ok, error = validate_transition(
            "in_progress",
            "for_review",
            GuardContext(subtasks_complete=True, implementation_evidence_present=True),
        )
        assert ok is True

    def test_reason_required_for_abandon(self) -> None:
        ok, error = validate_transition("in_progress", "planned", GuardContext())
        assert ok is False
        assert "reason" in error.lower()

    def test_reason_for_abandon_provided(self) -> None:
        ok, error = validate_transition("in_progress", "planned", GuardContext(reason="reassigning to other agent"))
        assert ok is True

    def test_conflict_detection_rejects_double_claim(self) -> None:
        """for_review -> in_review rejects when a different actor already holds the review."""
        ok, error = validate_transition(
            "for_review",
            "in_review",
            GuardContext(actor="reviewer-B", current_actor="reviewer-A"),
        )
        assert ok is False
        assert "already claimed" in error.lower()

    def test_conflict_detection_allows_same_actor_reclaim(self) -> None:
        """for_review -> in_review permits idempotent re-claim by the same actor."""
        ok, error = validate_transition(
            "for_review",
            "in_review",
            GuardContext(actor="reviewer-A", current_actor="reviewer-A"),
        )
        assert ok is True

    def test_conflict_detection_no_current_actor(self) -> None:
        """for_review -> in_review succeeds when no prior actor is set."""
        ok, error = validate_transition(
            "for_review",
            "in_review",
            GuardContext(actor="reviewer-A"),
        )
        assert ok is True


class TestAliasInTransitions:
    def test_doing_alias_in_from_lane(self) -> None:
        ok, error = validate_transition(
            "doing",
            "for_review",
            GuardContext(subtasks_complete=True, implementation_evidence_present=True),
        )
        assert ok is True

    def test_doing_alias_in_to_lane(self) -> None:
        ok, error = validate_transition(
            "claimed",
            "doing",
            GuardContext(workspace_context="worktree:/tmp/wt1"),
        )
        assert ok is True

    def test_doing_alias_both_lanes(self) -> None:
        # doing -> doing means in_progress -> in_progress — not a legal transition
        ok, error = validate_transition("doing", "doing", GuardContext())
        assert ok is False


class TestUnknownLanes:
    def test_unknown_from_lane(self) -> None:
        ok, error = validate_transition("nonexistent", "planned", GuardContext())
        assert ok is False
        assert "Unknown lane" in error

    def test_unknown_to_lane(self) -> None:
        ok, error = validate_transition("planned", "nonexistent", GuardContext())
        assert ok is False
        assert "Unknown lane" in error
