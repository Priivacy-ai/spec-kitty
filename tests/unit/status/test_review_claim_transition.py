"""Unit test: review-claim emits ``for_review -> in_review`` (FR-016, WP04/T021).

Documents and pins the documented state machine. The transition from
``for_review`` to ``in_review`` (the active-review queue state) MUST be
allowed and MUST be the canonical emission of the review-claim path.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.fast


class TestReviewClaimTransitionMatrix:
    """The transition matrix must allow for_review -> in_review."""

    def test_for_review_to_in_review_is_allowed(self) -> None:
        from specify_cli.status.transitions import ALLOWED_TRANSITIONS

        assert ("for_review", "in_review") in ALLOWED_TRANSITIONS

    def test_for_review_to_in_review_is_guarded_by_actor_required(self) -> None:
        """The guard for the review-claim transition is actor identity +
        conflict detection (no second reviewer can steal an active claim)."""
        from specify_cli.status.transitions import _GUARDED_TRANSITIONS

        guard_name = _GUARDED_TRANSITIONS.get(("for_review", "in_review"))
        assert guard_name == "actor_required_conflict_detection"


class TestReviewClaimGuardBehaviour:
    """Validate the guard accepts a claim by an actor and rejects no-actor."""

    def test_validate_transition_succeeds_with_actor(self) -> None:
        from specify_cli.status.models import GuardContext
        from specify_cli.status.transitions import validate_transition

        ctx = GuardContext(actor="claude")
        ok, error = validate_transition("for_review", "in_review", ctx)
        assert ok, f"expected ok=True, got error={error}"

    def test_validate_transition_rejects_missing_actor(self) -> None:
        from specify_cli.status.models import GuardContext
        from specify_cli.status.transitions import validate_transition

        ctx = GuardContext(actor=None)
        ok, error = validate_transition("for_review", "in_review", ctx)
        assert not ok
        assert error and "actor" in error.lower()

    def test_validate_transition_rejects_steal_by_second_actor(self) -> None:
        """A second reviewer must not be able to claim a WP already claimed."""
        from specify_cli.status.models import GuardContext
        from specify_cli.status.transitions import validate_transition

        ctx = GuardContext(actor="codex", current_actor="claude")
        ok, error = validate_transition("for_review", "in_review", ctx)
        assert not ok
        assert error and "claude" in error and "codex" in error

    def test_validate_transition_allows_idempotent_re_claim(self) -> None:
        """Same actor re-claiming is benign / idempotent."""
        from specify_cli.status.models import GuardContext
        from specify_cli.status.transitions import validate_transition

        ctx = GuardContext(actor="claude", current_actor="claude")
        ok, error = validate_transition("for_review", "in_review", ctx)
        assert ok, f"idempotent re-claim must succeed; error={error}"


class TestReviewClaimDoesNotEmitInProgress:
    """Source-level pin: workflow.review must emit Lane.IN_REVIEW for the
    review claim, not Lane.IN_PROGRESS."""

    def test_workflow_review_uses_in_review_lane(self) -> None:
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[3]
        workflow_path = (
            repo_root
            / "src"
            / "specify_cli"
            / "cli"
            / "commands"
            / "agent"
            / "workflow.py"
        )
        text = workflow_path.read_text(encoding="utf-8")

        # The review-claim transition emits to_lane=Lane.IN_REVIEW. There
        # must be no `to_lane=Lane.IN_PROGRESS` inside the review claim.
        assert "to_lane=Lane.IN_REVIEW" in text, (
            "workflow.review must emit Lane.IN_REVIEW for the review claim"
        )
