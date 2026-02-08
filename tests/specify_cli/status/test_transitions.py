"""Unit tests for the transition matrix, alias resolution, and guard conditions."""

from __future__ import annotations

import pytest

from specify_cli.status.models import DoneEvidence, ReviewApproval
from specify_cli.status.transitions import (
    ALLOWED_TRANSITIONS,
    CANONICAL_LANES,
    LANE_ALIASES,
    TERMINAL_LANES,
    is_terminal,
    resolve_lane_alias,
    validate_transition,
)


class TestConstants:
    def test_canonical_lanes_count(self) -> None:
        assert len(CANONICAL_LANES) == 7

    def test_allowed_transitions_count(self) -> None:
        assert len(ALLOWED_TRANSITIONS) == 16

    def test_terminal_lanes(self) -> None:
        assert TERMINAL_LANES == frozenset({"done", "canceled"})

    def test_doing_alias(self) -> None:
        assert LANE_ALIASES == {"doing": "in_progress"}


class TestResolveAlias:
    def test_doing_resolves_to_in_progress(self) -> None:
        assert resolve_lane_alias("doing") == "in_progress"

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
            (
                "for_review",
                "done",
                {
                    "evidence": DoneEvidence(
                        review=ReviewApproval(
                            reviewer="r", verdict="approved", reference="ref"
                        )
                    )
                },
            ),
            ("for_review", "in_progress", {"review_ref": "feedback-123"}),
            ("in_progress", "planned", {"reason": "reassigning"}),
            ("planned", "blocked", {}),
            ("claimed", "blocked", {}),
            ("in_progress", "blocked", {}),
            ("for_review", "blocked", {}),
            ("blocked", "in_progress", {}),
            ("planned", "canceled", {}),
            ("claimed", "canceled", {}),
            ("in_progress", "canceled", {}),
            ("for_review", "canceled", {}),
            ("blocked", "canceled", {}),
        ],
    )
    def test_legal_transition_accepted(
        self,
        from_lane: str,
        to_lane: str,
        kwargs: dict,
    ) -> None:
        ok, error = validate_transition(from_lane, to_lane, **kwargs)
        assert ok is True, f"Expected ok for {from_lane}->{to_lane}: {error}"
        assert error is None


class TestIllegalTransitions:
    @pytest.mark.parametrize(
        "from_lane,to_lane",
        [
            ("planned", "done"),
            ("planned", "in_progress"),
            ("planned", "for_review"),
            ("claimed", "for_review"),
            ("claimed", "done"),
            ("claimed", "planned"),
            ("done", "planned"),
            ("done", "in_progress"),
            ("done", "for_review"),
            ("canceled", "planned"),
            ("canceled", "in_progress"),
            ("blocked", "planned"),
            ("blocked", "for_review"),
            ("blocked", "done"),
        ],
    )
    def test_illegal_transition_rejected(
        self, from_lane: str, to_lane: str
    ) -> None:
        ok, error = validate_transition(from_lane, to_lane)
        assert ok is False
        assert error is not None
        assert "Illegal transition" in error


class TestForceOverride:
    def test_force_allows_terminal_exit(self) -> None:
        ok, error = validate_transition(
            "done",
            "planned",
            force=True,
            actor="admin",
            reason="reopening",
        )
        assert ok is True
        assert error is None

    def test_force_without_actor_rejected(self) -> None:
        ok, error = validate_transition(
            "done", "planned", force=True, reason="reopening"
        )
        assert ok is False
        assert "actor and reason" in error

    def test_force_without_reason_rejected(self) -> None:
        ok, error = validate_transition(
            "done", "planned", force=True, actor="admin"
        )
        assert ok is False
        assert "actor and reason" in error

    def test_force_with_empty_actor_rejected(self) -> None:
        ok, error = validate_transition(
            "done", "planned", force=True, actor="", reason="reopening"
        )
        assert ok is False

    def test_force_with_empty_reason_rejected(self) -> None:
        ok, error = validate_transition(
            "done", "planned", force=True, actor="admin", reason=""
        )
        assert ok is False

    def test_force_on_legal_transition_bypasses_guards(self) -> None:
        # for_review -> done normally requires evidence, but force bypasses
        ok, error = validate_transition(
            "for_review",
            "done",
            force=True,
            actor="admin",
            reason="emergency override",
        )
        assert ok is True
        assert error is None


class TestGuardConditions:
    def test_actor_required_for_claim(self) -> None:
        ok, error = validate_transition("planned", "claimed")
        assert ok is False
        assert "actor" in error.lower()

    def test_actor_required_for_claim_empty_string(self) -> None:
        ok, error = validate_transition("planned", "claimed", actor="")
        assert ok is False

    def test_review_ref_for_rollback(self) -> None:
        ok, error = validate_transition("for_review", "in_progress")
        assert ok is False
        assert "review_ref" in error.lower()

    def test_evidence_for_done(self) -> None:
        ok, error = validate_transition("for_review", "done")
        assert ok is False
        assert "evidence" in error.lower()

    def test_evidence_for_done_with_evidence(self) -> None:
        evidence = DoneEvidence(
            review=ReviewApproval(
                reviewer="r", verdict="approved", reference="ref"
            )
        )
        ok, error = validate_transition(
            "for_review", "done", evidence=evidence
        )
        assert ok is True

    def test_workspace_context_required_for_claimed_to_in_progress(self) -> None:
        ok, error = validate_transition("claimed", "in_progress")
        assert ok is False
        assert "workspace context" in error.lower()

    def test_workspace_context_provided(self) -> None:
        ok, error = validate_transition(
            "claimed",
            "in_progress",
            workspace_context="worktree:/tmp/wt1",
        )
        assert ok is True

    def test_subtasks_required_for_in_progress_to_for_review(self) -> None:
        ok, error = validate_transition(
            "in_progress",
            "for_review",
            implementation_evidence_present=True,
        )
        assert ok is False
        assert "completed subtasks" in error.lower()

    def test_implementation_evidence_required_for_in_progress_to_for_review(self) -> None:
        ok, error = validate_transition(
            "in_progress",
            "for_review",
            subtasks_complete=True,
        )
        assert ok is False
        assert "implementation evidence" in error.lower()

    def test_subtasks_and_implementation_evidence_allow_for_review(self) -> None:
        ok, error = validate_transition(
            "in_progress",
            "for_review",
            subtasks_complete=True,
            implementation_evidence_present=True,
        )
        assert ok is True

    def test_reason_required_for_abandon(self) -> None:
        ok, error = validate_transition("in_progress", "planned")
        assert ok is False
        assert "reason" in error.lower()

    def test_reason_for_abandon_provided(self) -> None:
        ok, error = validate_transition(
            "in_progress", "planned", reason="reassigning to other agent"
        )
        assert ok is True


class TestAliasInTransitions:
    def test_doing_alias_in_from_lane(self) -> None:
        ok, error = validate_transition(
            "doing",
            "for_review",
            subtasks_complete=True,
            implementation_evidence_present=True,
        )
        assert ok is True

    def test_doing_alias_in_to_lane(self) -> None:
        ok, error = validate_transition(
            "claimed",
            "doing",
            workspace_context="worktree:/tmp/wt1",
        )
        assert ok is True

    def test_doing_alias_both_lanes(self) -> None:
        # doing -> doing means in_progress -> in_progress — not a legal transition
        ok, error = validate_transition("doing", "doing")
        assert ok is False


class TestUnknownLanes:
    def test_unknown_from_lane(self) -> None:
        ok, error = validate_transition("nonexistent", "planned")
        assert ok is False
        assert "Unknown lane" in error

    def test_unknown_to_lane(self) -> None:
        ok, error = validate_transition("planned", "nonexistent")
        assert ok is False
        assert "Unknown lane" in error
