"""Additional edge case tests for transitions.py to increase mutation test coverage."""

from __future__ import annotations


from specify_cli.status.models import DoneEvidence, ReviewApproval
from specify_cli.status.transitions import validate_transition


class TestReviewerApprovalEdgeCases:
    """Test edge cases in _guard_reviewer_approval."""

    def test_evidence_with_none_review(self) -> None:
        """Evidence object with review=None should fail."""

        class FakeEvidence:
            review = None

        ok, error = validate_transition("for_review", "done", evidence=FakeEvidence())
        assert ok is False
        assert "evidence" in error.lower()
        assert "reviewer identity and approval reference" in error

    def test_evidence_with_empty_reviewer(self) -> None:
        """Evidence with empty reviewer string should fail."""
        evidence = DoneEvidence(review=ReviewApproval(reviewer="", verdict="approved", reference="ref"))
        ok, error = validate_transition("for_review", "done", evidence=evidence)
        assert ok is False
        assert "reviewer identity" in error.lower()

    def test_evidence_with_whitespace_reviewer(self) -> None:
        """Evidence with whitespace-only reviewer should fail."""
        evidence = DoneEvidence(review=ReviewApproval(reviewer="   ", verdict="approved", reference="ref"))
        ok, error = validate_transition("for_review", "done", evidence=evidence)
        assert ok is False
        assert "reviewer identity" in error.lower()

    def test_evidence_with_empty_reference(self) -> None:
        """Evidence with empty reference string should fail."""
        evidence = DoneEvidence(review=ReviewApproval(reviewer="reviewer1", verdict="approved", reference=""))
        ok, error = validate_transition("for_review", "done", evidence=evidence)
        assert ok is False
        assert "approval reference" in error.lower()

    def test_evidence_with_whitespace_reference(self) -> None:
        """Evidence with whitespace-only reference should fail."""
        evidence = DoneEvidence(review=ReviewApproval(reviewer="reviewer1", verdict="approved", reference="   "))
        ok, error = validate_transition("for_review", "done", evidence=evidence)
        assert ok is False
        assert "approval reference" in error.lower()


class TestWorkspaceContextEdgeCases:
    """Test edge cases in _guard_workspace_context."""

    def test_workspace_context_empty_string(self) -> None:
        """Empty workspace context should fail."""
        ok, error = validate_transition("claimed", "in_progress", workspace_context="")
        assert ok is False
        assert "workspace context" in error.lower()

    def test_workspace_context_whitespace_only(self) -> None:
        """Whitespace-only workspace context should fail."""
        ok, error = validate_transition("claimed", "in_progress", workspace_context="   ")
        assert ok is False
        assert "workspace context" in error.lower()


class TestSubtasksForceEdgeCases:
    """Test edge cases in _guard_subtasks_complete_or_force."""

    def test_force_bypasses_subtasks_check(self) -> None:
        """Force flag should bypass subtasks_complete check."""
        ok, error = validate_transition(
            "in_progress",
            "for_review",
            force=True,
            actor="agent1",
            reason="emergency deploy",
            subtasks_complete=False,
            implementation_evidence_present=False,
        )
        assert ok is True
        assert error is None

    def test_subtasks_false_explicitly_fails(self) -> None:
        """Explicitly False subtasks_complete should fail."""
        ok, error = validate_transition(
            "in_progress",
            "for_review",
            subtasks_complete=False,
            implementation_evidence_present=True,
        )
        assert ok is False
        assert "completed subtasks" in error.lower()

    def test_implementation_evidence_false_explicitly_fails(self) -> None:
        """Explicitly False implementation_evidence_present should fail."""
        ok, error = validate_transition(
            "in_progress",
            "for_review",
            subtasks_complete=True,
            implementation_evidence_present=False,
        )
        assert ok is False
        assert "implementation evidence" in error.lower()

    def test_both_none_fails(self) -> None:
        """Both None (not provided) should fail."""
        ok, error = validate_transition(
            "in_progress",
            "for_review",
            subtasks_complete=None,
            implementation_evidence_present=None,
        )
        assert ok is False


class TestReasonEdgeCases:
    """Test edge cases in _guard_reason_required."""

    def test_reason_empty_string_fails(self) -> None:
        """Empty reason string should fail."""
        ok, error = validate_transition("in_progress", "planned", reason="")
        assert ok is False
        assert "reason" in error.lower()

    def test_reason_whitespace_only_fails(self) -> None:
        """Whitespace-only reason should fail."""
        ok, error = validate_transition("in_progress", "planned", reason="   ")
        assert ok is False
        assert "reason" in error.lower()


class TestReviewRefEdgeCases:
    """Test edge cases in _guard_review_ref_required."""

    def test_review_ref_for_rollback_to_in_progress_empty(self) -> None:
        """Empty review_ref for for_review -> in_progress should fail."""
        ok, error = validate_transition("for_review", "in_progress", review_ref="")
        assert ok is False
        assert "review_ref" in error.lower()

    def test_review_ref_for_rollback_to_in_progress_whitespace(self) -> None:
        """Whitespace-only review_ref should fail."""
        ok, error = validate_transition("for_review", "in_progress", review_ref="   ")
        assert ok is False
        assert "review_ref" in error.lower()


class TestForceTransitionEdgeCases:
    """Test force transition edge cases."""

    def test_force_on_illegal_transition_with_actor_and_reason(self) -> None:
        """Force should allow any transition with actor and reason."""
        ok, error = validate_transition(
            "done",
            "planned",
            force=True,
            actor="admin",
            reason="reopening ticket",
        )
        assert ok is True
        assert error is None

    def test_force_with_whitespace_actor_rejected(self) -> None:
        """Force with whitespace-only actor should fail."""
        ok, error = validate_transition(
            "done",
            "planned",
            force=True,
            actor="   ",
            reason="reopening",
        )
        assert ok is False
        assert "actor and reason" in error.lower()

    def test_force_with_whitespace_reason_rejected(self) -> None:
        """Force with whitespace-only reason should fail."""
        ok, error = validate_transition(
            "done",
            "planned",
            force=True,
            actor="admin",
            reason="   ",
        )
        assert ok is False
        assert "actor and reason" in error.lower()

    def test_force_on_legal_transition_still_requires_actor_and_reason(self) -> None:
        """Force on a legal transition still requires actor and reason."""
        ok, error = validate_transition(
            "planned",
            "claimed",
            force=True,
            # Missing actor and reason
        )
        assert ok is False
        assert "actor and reason" in error.lower()


class TestActorEdgeCases:
    """Test actor guard edge cases."""

    def test_actor_whitespace_only_fails(self) -> None:
        """Whitespace-only actor for planned -> claimed should fail."""
        ok, error = validate_transition("planned", "claimed", actor="   ")
        assert ok is False
        assert "actor" in error.lower()


class TestTransitionMatrixCoverage:
    """Ensure all 17 allowed transitions are tested."""

    def test_blocked_to_in_progress_without_guards(self) -> None:
        """blocked -> in_progress has no guards, should pass without extra params."""
        ok, error = validate_transition("blocked", "in_progress")
        assert ok is True
        assert error is None

    def test_planned_to_blocked_without_guards(self) -> None:
        """planned -> blocked has no guards."""
        ok, error = validate_transition("planned", "blocked")
        assert ok is True

    def test_claimed_to_blocked_without_guards(self) -> None:
        """claimed -> blocked has no guards."""
        ok, error = validate_transition("claimed", "blocked")
        assert ok is True

    def test_in_progress_to_blocked_without_guards(self) -> None:
        """in_progress -> blocked has no guards."""
        ok, error = validate_transition("in_progress", "blocked")
        assert ok is True

    def test_for_review_to_blocked_without_guards(self) -> None:
        """for_review -> blocked has no guards."""
        ok, error = validate_transition("for_review", "blocked")
        assert ok is True

    def test_planned_to_canceled_without_guards(self) -> None:
        """planned -> canceled has no guards."""
        ok, error = validate_transition("planned", "canceled")
        assert ok is True

    def test_claimed_to_canceled_without_guards(self) -> None:
        """claimed -> canceled has no guards."""
        ok, error = validate_transition("claimed", "canceled")
        assert ok is True

    def test_in_progress_to_canceled_without_guards(self) -> None:
        """in_progress -> canceled has no guards."""
        ok, error = validate_transition("in_progress", "canceled")
        assert ok is True

    def test_for_review_to_canceled_without_guards(self) -> None:
        """for_review -> canceled has no guards."""
        ok, error = validate_transition("for_review", "canceled")
        assert ok is True

    def test_blocked_to_canceled_without_guards(self) -> None:
        """blocked -> canceled has no guards."""
        ok, error = validate_transition("blocked", "canceled")
        assert ok is True
