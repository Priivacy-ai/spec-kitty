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
        """The guard for the review-claim transition is actor-presence only.

        Re-pointed (WP01): the ``for_review -> in_review`` guard is allow-only —
        it enforces actor identity but never blocks a distinct actor (the
        cross-profile false-positive this mission removes). The reviewer-vs-
        reviewer reject lives at the ``in_review`` re-claim, not this guard."""
        from specify_cli.status.models import GuardContext, Lane
        from specify_cli.status.wp_state import wp_state_for

        state = wp_state_for(Lane.FOR_REVIEW)
        assert state.can_transition_to(Lane.IN_REVIEW, GuardContext(actor=None)) is False
        assert state.can_transition_to(Lane.IN_REVIEW, GuardContext(actor="claude")) is True
        assert state.can_transition_to(Lane.IN_REVIEW, GuardContext(actor="codex", current_actor="claude")) is True


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

    def test_validate_transition_allows_distinct_actor_at_for_review(self) -> None:
        """Re-pointed (WP01): the allow-only ``for_review`` guard permits a
        distinct actor. This surface carries no role and never invokes the
        collision predicate, so no role-carrying reject can be expressed here —
        the genuine reject is the ``in_review`` re-claim lifecycle test."""
        from specify_cli.status.models import GuardContext
        from specify_cli.status.transitions import validate_transition

        ctx = GuardContext(actor="codex", current_actor="claude")
        ok, error = validate_transition("for_review", "in_review", ctx)
        assert ok is True, f"allow-only guard must permit a distinct actor; error={error}"

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
        # The review command's implementation spans the thin Typer shell
        # (workflow.py) and its extracted executor (workflow_executor.py) after
        # the coord-authority trio degod (#2464). The delegation call to the
        # shared review lifecycle lives wherever the review body sits, so scan
        # both surfaces rather than pinning the pre-degod file location.
        agent_dir = repo_root / "src" / "specify_cli" / "cli" / "commands" / "agent"
        review_impl_text = "\n".join((agent_dir / name).read_text(encoding="utf-8") for name in ("workflow.py", "workflow_executor.py"))

        assert "start_review_status(" in review_impl_text, "workflow.review must delegate the review claim to the shared review lifecycle"

        lifecycle_path = repo_root / "src" / "specify_cli" / "status" / "work_package_lifecycle.py"
        lifecycle_text = lifecycle_path.read_text(encoding="utf-8")
        assert "to_lane=Lane.IN_REVIEW" in lifecycle_text, "shared review lifecycle must emit Lane.IN_REVIEW for the review claim"
