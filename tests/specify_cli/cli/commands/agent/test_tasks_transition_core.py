"""Per-branch unit tests for the pure ``move_task`` transition decision core (WP03).

The failing-first (charter C-011 / research D7) artifact for this pure-parity
extraction is *this* unit test: it is RED on the mission base (the core does not
yet exist) and GREEN once ``decide_transition`` reproduces ``move_task``'s exact
current decision behaviour.

Every branch enumerated here maps 1:1 to a NAMED decision branch that the WP01
golden harness (``test_tasks_cli_contract.py``) freezes at the CLI boundary —
Emit / the coord skip arm (``skip_primary``) / RefuseExit1, plus each guard
(agent-ownership, rejected-verdict, protected-branch-without-skip,
feedback-required, done-override, arbiter-override, planning-artifact arm,
review-currency, force). ``--cov-branch`` on ``tasks_transition_core`` ratchets
that no decision branch is extracted unguarded (NFR-002).

FR-004 / NFR-001: the core REPRODUCES the current behaviour verbatim — including
the skip-vs-refuse divergence that ``#2300`` defers. Nothing here encodes an
intended behaviour change.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import tasks as tasks_module
from specify_cli.cli.commands.agent.tasks import app
from specify_cli.cli.commands.agent.tasks_transition_core import (
    Emit,
    MoveTaskRequest,
    RefuseExit1,
    TransitionPlan,
    arbiter_persist_signal,
    build_transition_plan,
    decide_transition,
    override_persist_signal,
)
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event
from tests.mocked_env import setup_mocked_env

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# A neutral, fully-passing request the per-branch tests perturb via ``replace``.
# A simple forward ``in_progress -> for_review`` move that clears every guard.
# ---------------------------------------------------------------------------


def _base_request(**overrides: Any) -> MoveTaskRequest:
    req = MoveTaskRequest(
        task_id="WP01",
        target_lane="for_review",
        old_lane="in_progress",
        force=False,
        agent=None,
        current_agent=None,
        note=None,
        auto_commit=False,
        target_branch="feature/work",
        skip_target_branch_commit=False,
        tracker_ref_values=(),
        assignee=None,
        shell_pid=None,
        self_review_fallback=False,
        intended_reviewer=None,
        reviewer_failure_reason=None,
        protected_error=None,
        review_verdict=None,
        review_artifact_name=None,
        skip_review_artifact_check=False,
        feedback_provided=False,
        feedback_source=None,
        feedback_exists=False,
        feedback_is_file=False,
        feedback_content=None,
        unchecked_subtasks=(),
        review_ready=True,
        review_guidance=(),
        done_execution_mode=None,
        done_merged=False,
        done_merge_msg="",
        done_override_reason=None,
        issue_matrix_blocker=None,
        is_arbiter_override=False,
        effective_reviewer=None,
        effective_approval_ref=None,
    )
    return replace(req, **overrides)


# ---------------------------------------------------------------------------
# Emit (happy path) + the coord skip arm (``skip_primary``)
# ---------------------------------------------------------------------------


def test_plain_forward_move_emits() -> None:
    outcome = decide_transition(_base_request())
    assert isinstance(outcome, Emit)
    assert outcome.skip_primary is False
    assert outcome.plan.canonical_lane == "for_review"
    # Non-force forward from in_progress hops through the single next lane.
    assert outcome.plan.transition_targets == ["for_review"]
    assert outcome.plan.emit_force is False
    assert outcome.evidence_dict is None
    assert outcome.authorize_review_override is False
    assert outcome.planned_rollback is False
    assert outcome.arbiter_forward is False


def test_coord_skip_arm_sets_skip_primary() -> None:
    """The coord + protected-primary skip arm is Emit(skip_primary=True).

    ``move_task`` still EMITS the transition (to the coordination branch) and
    exits 0 — the skip is of the *primary* WP-file commit, not the emission. So
    the faithful encoding is ``skip_primary`` on Emit, never a no-emit terminal.
    """
    outcome = decide_transition(
        _base_request(auto_commit=True, skip_target_branch_commit=True)
    )
    assert isinstance(outcome, Emit)
    assert outcome.skip_primary is True


def test_skip_primary_false_when_not_coord_skip() -> None:
    outcome = decide_transition(_base_request(auto_commit=True))
    assert isinstance(outcome, Emit)
    assert outcome.skip_primary is False


# ---------------------------------------------------------------------------
# self-review-fallback option error (first guard)
# ---------------------------------------------------------------------------


def test_self_review_fallback_without_force_refuses() -> None:
    outcome = decide_transition(
        _base_request(
            target_lane="approved",
            old_lane="for_review",
            self_review_fallback=True,
            intended_reviewer="reviewer-renata",
            reviewer_failure_reason="offline",
            force=False,
        )
    )
    assert isinstance(outcome, RefuseExit1)
    assert "--self-review-fallback requires --force" in outcome.error


def test_self_review_metadata_without_enable_refuses() -> None:
    outcome = decide_transition(_base_request(intended_reviewer="reviewer-renata"))
    assert isinstance(outcome, RefuseExit1)
    assert "require --self-review-fallback" in outcome.error


# ---------------------------------------------------------------------------
# unsupported-skip-metadata (protected coord branch)
# ---------------------------------------------------------------------------


def test_unsupported_skip_metadata_refuses_with_diagnostic() -> None:
    outcome = decide_transition(
        _base_request(
            auto_commit=True,
            skip_target_branch_commit=True,
            target_branch="main",
            tracker_ref_values=("#1298",),
            assignee="claude",
            shell_pid="4242",
            note="a note",
        )
    )
    assert isinstance(outcome, RefuseExit1)
    assert "WP frontmatter/activity metadata on protected" in outcome.error
    assert outcome.diagnostic is not None
    assert outcome.diagnostic["error"] == "WP_METADATA_UNSUPPORTED_ON_PROTECTED_COORD_BRANCH"
    assert outcome.diagnostic["target_branch"] == "main"
    # Order matches the current inline sequence: tracker_refs, assignee, shell_pid, activity_log.
    assert outcome.diagnostic["fields"] == ["tracker_refs", "assignee", "shell_pid", "activity_log"]


# ---------------------------------------------------------------------------
# protected-branch-without-skip
# ---------------------------------------------------------------------------


def test_protected_branch_without_skip_refuses() -> None:
    outcome = decide_transition(
        _base_request(
            auto_commit=True,
            skip_target_branch_commit=False,
            protected_error="Refusing status commit to protected branch 'main' (auto-commit).",
        )
    )
    assert isinstance(outcome, RefuseExit1)
    assert outcome.error == "Refusing status commit to protected branch 'main' (auto-commit)."


def test_protected_error_ignored_when_skip_active() -> None:
    """The protected refusal is suppressed under the coord skip arm (divergence #2300)."""
    outcome = decide_transition(
        _base_request(
            auto_commit=True,
            skip_target_branch_commit=True,
            protected_error="should be ignored",
        )
    )
    assert isinstance(outcome, Emit)
    assert outcome.skip_primary is True


# ---------------------------------------------------------------------------
# agent-ownership
# ---------------------------------------------------------------------------


def test_agent_mismatch_refuses_with_console_warning() -> None:
    outcome = decide_transition(
        _base_request(agent="other-agent", current_agent="testbot", force=False)
    )
    assert isinstance(outcome, RefuseExit1)
    assert "Agent mismatch" in outcome.error
    assert "testbot" in outcome.error and "other-agent" in outcome.error
    # The rich ownership warning is carried as data for the shell to print.
    assert outcome.console_warning, "agent-ownership refusal must carry the console warning lines"


def test_agent_mismatch_bypassed_by_force() -> None:
    outcome = decide_transition(
        _base_request(agent="other-agent", current_agent="testbot", force=True)
    )
    assert isinstance(outcome, Emit)


def test_agent_match_proceeds() -> None:
    outcome = decide_transition(
        _base_request(agent="testbot", current_agent="testbot")
    )
    assert isinstance(outcome, Emit)


# ---------------------------------------------------------------------------
# rejected-verdict guard (APPROVED/DONE)
# ---------------------------------------------------------------------------


def _approve_request(**overrides: Any) -> MoveTaskRequest:
    return _base_request(
        target_lane="approved",
        old_lane="for_review",
        force=True,  # bypass subtasks + currency to isolate the verdict guard
        effective_reviewer="reviewer-renata",
        effective_approval_ref="PR#42",
        **overrides,
    )


def test_unparseable_verdict_refuses() -> None:
    outcome = decide_transition(
        _approve_request(review_verdict=None, review_artifact_name="review-cycle-1.md")
    )
    assert isinstance(outcome, RefuseExit1)
    assert "no parseable review verdict" in outcome.error


def test_rejected_verdict_without_skip_refuses() -> None:
    outcome = decide_transition(
        _approve_request(review_verdict="rejected", review_artifact_name="review-cycle-1.md")
    )
    assert isinstance(outcome, RefuseExit1)
    assert "rejected review artifact" in outcome.error
    assert "--skip-review-artifact-check" in outcome.error


def test_rejected_verdict_skip_without_note_refuses() -> None:
    outcome = decide_transition(
        _approve_request(
            review_verdict="rejected",
            review_artifact_name="review-cycle-1.md",
            skip_review_artifact_check=True,
            note="   ",
        )
    )
    assert isinstance(outcome, RefuseExit1)
    assert "requires --note" in outcome.error


def test_rejected_verdict_override_authorizes_and_emits() -> None:
    outcome = decide_transition(
        _approve_request(
            review_verdict="rejected",
            review_artifact_name="review-cycle-1.md",
            skip_review_artifact_check=True,
            note="arbiter release: rejection superseded",
        )
    )
    assert isinstance(outcome, Emit)
    assert outcome.authorize_review_override is True
    # Approval evidence is part of the transition decision.
    assert outcome.evidence_dict is not None
    assert outcome.evidence_dict["review"]["reviewer"] == "reviewer-renata"


def test_approved_verdict_proceeds_without_override() -> None:
    outcome = decide_transition(
        _approve_request(review_verdict="approved", review_artifact_name="review-cycle-1.md")
    )
    assert isinstance(outcome, Emit)
    assert outcome.authorize_review_override is False


# ---------------------------------------------------------------------------
# feedback-required (planned rollback) + generic feedback-file guards
# ---------------------------------------------------------------------------


def test_feedback_file_not_found_refuses(tmp_path: Path) -> None:
    outcome = decide_transition(
        _base_request(
            feedback_provided=True,
            feedback_source=str(tmp_path / "missing.md"),
            feedback_exists=False,
        )
    )
    assert isinstance(outcome, RefuseExit1)
    assert "Review feedback file not found" in outcome.error


def test_feedback_path_not_a_file_refuses(tmp_path: Path) -> None:
    outcome = decide_transition(
        _base_request(
            feedback_provided=True,
            feedback_source=str(tmp_path / "dir"),
            feedback_exists=True,
            feedback_is_file=False,
        )
    )
    assert isinstance(outcome, RefuseExit1)
    assert "not a file" in outcome.error


def test_planned_without_feedback_refuses_even_with_force() -> None:
    outcome = decide_transition(
        _base_request(
            target_lane="planned",
            old_lane="in_review",
            force=True,
            feedback_provided=False,
        )
    )
    assert isinstance(outcome, RefuseExit1)
    assert "requires review feedback" in outcome.error
    assert "cannot be bypassed with --force" in outcome.error


def test_planned_with_empty_feedback_refuses(tmp_path: Path) -> None:
    outcome = decide_transition(
        _base_request(
            target_lane="planned",
            old_lane="in_review",
            feedback_provided=True,
            feedback_source=str(tmp_path / "empty.md"),
            feedback_exists=True,
            feedback_is_file=True,
            feedback_content="",
        )
    )
    assert isinstance(outcome, RefuseExit1)
    assert "Review feedback file is empty" in outcome.error


def test_planned_with_valid_feedback_is_planned_rollback(tmp_path: Path) -> None:
    outcome = decide_transition(
        _base_request(
            target_lane="planned",
            old_lane="in_review",
            feedback_provided=True,
            feedback_source=str(tmp_path / "fb.md"),
            feedback_exists=True,
            feedback_is_file=True,
            feedback_content="**Issue**: rework",
        )
    )
    assert isinstance(outcome, Emit)
    assert outcome.planned_rollback is True


# ---------------------------------------------------------------------------
# subtasks
# ---------------------------------------------------------------------------


def test_unchecked_subtasks_refuse_without_force() -> None:
    outcome = decide_transition(
        _base_request(unchecked_subtasks=("T001", "T002"), force=False)
    )
    assert isinstance(outcome, RefuseExit1)
    assert "unchecked subtasks" in outcome.error
    assert "T001" in outcome.error


def test_unchecked_subtasks_bypassed_by_force() -> None:
    outcome = decide_transition(
        _base_request(unchecked_subtasks=("T001",), force=True)
    )
    assert isinstance(outcome, Emit)


# ---------------------------------------------------------------------------
# review-currency
# ---------------------------------------------------------------------------


def test_review_currency_not_ready_refuses() -> None:
    outcome = decide_transition(
        _base_request(
            review_ready=False,
            review_guidance=("Review branch is stale relative to base",),
        )
    )
    assert isinstance(outcome, RefuseExit1)
    assert "stale" in outcome.error


# ---------------------------------------------------------------------------
# done-ancestry / planning-artifact arm (FR-008a)
# ---------------------------------------------------------------------------


def _done_request(**overrides: Any) -> MoveTaskRequest:
    return _base_request(
        target_lane="done",
        old_lane="approved",
        force=True,
        effective_reviewer="reviewer-renata",
        effective_approval_ref="PR#42",
        **overrides,
    )


def test_code_change_done_without_ancestry_refuses() -> None:
    outcome = decide_transition(
        _done_request(done_execution_mode="code_change", done_merged=False, done_merge_msg="no merge")
    )
    assert isinstance(outcome, RefuseExit1)
    assert "without verified merge ancestry" in outcome.error


def test_code_change_done_override_proceeds() -> None:
    outcome = decide_transition(
        _done_request(
            done_execution_mode="code_change",
            done_merged=False,
            done_override_reason="branch deleted after hotfix merge",
        )
    )
    assert isinstance(outcome, Emit)
    assert outcome.done_override_note is True
    # The override reason is folded into the emit reason (recorded in history/events).
    assert outcome.plan.emit_reason is not None
    assert "Done override" in outcome.plan.emit_reason


def test_planning_artifact_done_skips_ancestry() -> None:
    """FR-008a: a planning-artifact WP reaches done WITHOUT ancestry (no refuse)."""
    outcome = decide_transition(
        _done_request(done_execution_mode="planning_artifact", done_merged=False)
    )
    assert isinstance(outcome, Emit)
    assert outcome.done_override_note is False


def test_code_change_done_with_ancestry_proceeds() -> None:
    outcome = decide_transition(
        _done_request(done_execution_mode="code_change", done_merged=True)
    )
    assert isinstance(outcome, Emit)


# ---------------------------------------------------------------------------
# issue-matrix blocker
# ---------------------------------------------------------------------------


def test_issue_matrix_blocker_refuses() -> None:
    outcome = decide_transition(
        _approve_request(issue_matrix_blocker="Issue #7 must be resolved before approval.")
    )
    assert isinstance(outcome, RefuseExit1)
    assert outcome.error == "Issue #7 must be resolved before approval."


# ---------------------------------------------------------------------------
# arbiter-override + force paths (build_transition_plan)
# ---------------------------------------------------------------------------


def test_arbiter_override_sets_arbiter_forward() -> None:
    outcome = decide_transition(
        _base_request(
            target_lane="for_review",
            old_lane="planned",
            force=True,
            is_arbiter_override=True,
        )
    )
    assert isinstance(outcome, Emit)
    assert outcome.arbiter_forward is True


def test_for_review_to_in_progress_force_sets_force_override_ref() -> None:
    plan = build_transition_plan(
        old_lane="for_review",
        target_lane="in_progress",
        force=True,
        review_feedback_pointer=None,
        arb_review_ref=None,
        note_text=None,
    )
    assert plan.emit_force is True
    assert plan.emit_review_ref == "force-override"
    assert plan.transition_targets == ["in_progress"]


def test_non_force_backward_is_rewound_and_forced() -> None:
    plan = build_transition_plan(
        old_lane="approved",
        target_lane="in_progress",
        force=False,
        review_feedback_pointer=None,
        arb_review_ref=None,
        note_text=None,
    )
    # A backward move is auto-promoted to force with a canonical rewind reason.
    assert plan.emit_force is True
    assert plan.emit_reason is not None
    assert plan.emit_reason.startswith("backward rewind: approved -> in_progress")


def test_backward_reason_appends_user_note() -> None:
    plan = build_transition_plan(
        old_lane="approved",
        target_lane="in_progress",
        force=False,
        review_feedback_pointer=None,
        arb_review_ref=None,
        note_text="operator: rewind for rework",
    )
    assert plan.emit_reason is not None
    assert plan.emit_reason.startswith("backward rewind: approved -> in_progress")
    assert plan.emit_reason.endswith("operator: rewind for rework")


def test_planned_backward_reason_includes_feedback_pointer() -> None:
    plan = build_transition_plan(
        old_lane="in_review",
        target_lane="planned",
        force=False,
        review_feedback_pointer="feedback://WP01/review-cycle-1.md",
        arb_review_ref=None,
        note_text=None,
    )
    assert plan.emit_review_ref == "feedback://WP01/review-cycle-1.md"
    assert "feedback://WP01/review-cycle-1.md" in (plan.emit_reason or "")


def test_arbiter_ref_fills_review_ref_when_base_absent() -> None:
    plan = build_transition_plan(
        old_lane="planned",
        target_lane="for_review",
        force=True,
        review_feedback_pointer=None,
        arb_review_ref="feedback://arbiter/WP01/review-cycle-1.md",
        note_text=None,
    )
    assert plan.emit_review_ref == "feedback://arbiter/WP01/review-cycle-1.md"


def test_non_force_forward_hops_through_intermediate_lanes() -> None:
    plan = build_transition_plan(
        old_lane="planned",
        target_lane="for_review",
        force=False,
        review_feedback_pointer=None,
        arb_review_ref=None,
        note_text=None,
    )
    assert plan.transition_targets == ["claimed", "in_progress", "for_review"]
    assert plan.emit_force is False


def test_force_move_reason_defaults_to_force_shape() -> None:
    plan = build_transition_plan(
        old_lane="in_progress",
        target_lane="for_review",
        force=True,
        review_feedback_pointer=None,
        arb_review_ref=None,
        note_text=None,
    )
    assert plan.emit_reason == "Force move to for_review"


def test_purity_same_request_same_outcome() -> None:
    req = _approve_request(review_verdict="approved", review_artifact_name="review-cycle-1.md")
    first = decide_transition(req)
    second = decide_transition(req)
    assert first == second


# ---------------------------------------------------------------------------
# T017 -- fake-core sentinel: the core's RETURN VALUE drives the command.
# ---------------------------------------------------------------------------
#
# The anti-shadow-code guard the mission demands: a "called-but-result-discarded"
# core would pass a grep-for-callers check while the old inline logic still ran.
# These tests inject a SENTINEL outcome that CONTRADICTS what the real decision
# would produce and assert the command's observable result follows the sentinel —
# proving ``decide_transition`` genuinely DRIVES ``move_task``, not merely that a
# caller exists.

_MID8 = "01KW2E7A"
_REVIEW_GATE_BYPASS: dict[str, Any] = {
    "_validate_ready_for_review": (True, []),
    "_check_unchecked_subtasks": [],
}


def _sentinel_mission(root: Path, slug: str) -> Path:
    feature_dir = root / "kitty-specs" / slug
    (feature_dir / "tasks").mkdir(parents=True)
    (root / ".kittify").mkdir(exist_ok=True)
    (feature_dir / "tasks" / "WP01-fixture.md").write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Fixture WP01\n"
        "execution_mode: code_change\n"
        "agent: testbot\n"
        "---\n\n# WP01\n\n## Activity Log\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "# Work Packages\n\n## WP01 - fixture\n- [ ] T001 do a thing\n", encoding="utf-8"
    )
    (feature_dir / "spec.md").write_text("# Spec\n\nFR-001 do a thing.\n", encoding="utf-8")
    for ordinal, (frm, to) in enumerate(
        [("planned", "claimed"), ("claimed", "in_progress")], start=1
    ):
        append_event(
            feature_dir,
            StatusEvent(
                event_id=f"{_MID8}FC00000000000000{ordinal:04d}",
                mission_slug=slug,
                wp_id="WP01",
                from_lane=Lane(frm),
                to_lane=Lane(to),
                at=f"2026-01-01T00:00:{ordinal:02d}+00:00",
                actor="test",
                force=True,
                execution_mode="worktree",
            ),
        )
    return feature_dir


def test_sentinel_refusal_drives_the_command_to_exit_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A sentinel RefuseExit1 flips a would-succeed move to exit 1 with its message."""
    fd = _sentinel_mission(tmp_path, f"sentinel-refuse-{_MID8}")

    def _fake(_req: MoveTaskRequest) -> RefuseExit1:
        return RefuseExit1("SENTINEL-REFUSAL-8f2a")

    monkeypatch.setattr(tasks_module, "decide_transition", _fake)
    with setup_mocked_env(
        fd.parent.parent, mission_slug=fd.name, extra_patches=_REVIEW_GATE_BYPASS
    ):
        result = CliRunner().invoke(
            app,
            ["move-task", "WP01", "--to", "for_review", "--mission", fd.name, "--no-auto-commit"],
        )
    # The real decision would EMIT + exit 0; the sentinel refusal drives exit 1.
    assert result.exit_code == 1, result.output
    assert "SENTINEL-REFUSAL-8f2a" in result.output


def test_sentinel_skip_primary_drives_the_json_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A sentinel ``Emit(skip_primary=True)`` flips the ``--json`` envelope.

    On this NON-coord tree the real decision returns ``skip_primary=False`` (no
    ``wp_file_update`` key). The sentinel forces ``skip_primary=True`` — so the
    command's ``--json`` envelope gains ``wp_file_update="skipped"`` ONLY because
    the core's return value drives the polymorphic output.
    """
    fd = _sentinel_mission(tmp_path, f"sentinel-skip-{_MID8}")

    sentinel = Emit(
        plan=TransitionPlan(
            canonical_lane="for_review",
            transition_targets=["for_review"],
            emit_force=False,
            emit_reason=None,
            emit_review_ref=None,
        ),
        skip_primary=True,
        evidence_dict=None,
        note_text=None,
    )

    def _fake(_req: MoveTaskRequest) -> Emit:
        return sentinel

    monkeypatch.setattr(tasks_module, "decide_transition", _fake)
    with setup_mocked_env(
        fd.parent.parent, mission_slug=fd.name, extra_patches=_REVIEW_GATE_BYPASS
    ):
        result = CliRunner().invoke(
            app,
            ["move-task", "WP01", "--to", "for_review", "--mission", fd.name, "--no-auto-commit", "--json"],
        )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["wp_file_update"] == "skipped"
    assert payload["new_lane"] == "for_review"


# ---------------------------------------------------------------------------
# OLD-timing persist signals (FR-004 partial-write-on-refusal)
# ---------------------------------------------------------------------------
#
# The shell fires the two durable proceed persists at their ORIGINAL guard
# positions via these pure signals, so a LATER guard's refusal still leaves the
# OLD partial write on disk. Each signal is True only when the guards that
# precede its persist position clear AND the persist is authorised — reproducing
# the un-refactored command's short-circuit.


def _rejected_override_request(**overrides: Any) -> MoveTaskRequest:
    """A rejected-verdict override request whose guards 1-4 all clear."""
    fields: dict[str, Any] = {
        "target_lane": "approved",
        "review_artifact_name": "review-cycle-1.md",
        "review_verdict": "rejected",
        "skip_review_artifact_check": True,
        "note": "Arbiter override reason",
    }
    fields.update(overrides)
    return _base_request(**fields)


def test_override_persist_signal_true_when_preceding_guards_clear() -> None:
    assert override_persist_signal(_rejected_override_request()) is True


def test_override_persist_signal_false_when_earlier_guard_would_refuse() -> None:
    # Agent-ownership guard (position 4) refuses BEFORE the rejected-verdict arm,
    # so OLD never reached the persist.
    req = _rejected_override_request(current_agent="alice", agent="bob", force=False)
    assert override_persist_signal(req) is False


def test_override_persist_signal_false_when_not_authorized() -> None:
    # Missing --skip-review-artifact-check → not the proceed-override arm.
    req = _rejected_override_request(skip_review_artifact_check=False)
    assert override_persist_signal(req) is False


def test_override_persist_signal_false_without_note() -> None:
    req = _rejected_override_request(note="   ")
    assert override_persist_signal(req) is False


def _arbiter_request(**overrides: Any) -> MoveTaskRequest:
    """A forward arbiter-override request whose guards 1-10 all clear."""
    fields: dict[str, Any] = {
        "old_lane": "planned",
        "target_lane": "approved",
        "force": True,
        "is_arbiter_override": True,
    }
    fields.update(overrides)
    return _base_request(**fields)


def test_arbiter_persist_signal_true_when_preceding_guards_clear() -> None:
    assert arbiter_persist_signal(_arbiter_request()) is True


def test_arbiter_persist_signal_false_when_not_arbiter() -> None:
    assert arbiter_persist_signal(_arbiter_request(is_arbiter_override=False)) is False


def test_arbiter_persist_signal_false_when_done_ancestry_refuses() -> None:
    # done-ancestry guard (position 10) refuses BEFORE the arbiter persist, so OLD
    # never reached it.
    req = _arbiter_request(
        target_lane="done",
        done_execution_mode="code_change",
        done_merged=False,
        done_override_reason=None,
    )
    assert arbiter_persist_signal(req) is False


def test_arbiter_persist_signal_true_ignores_issue_matrix_blocker() -> None:
    # An issue-matrix blocker refuses AFTER the arbiter persist position, so the
    # signal still fires (partial write survives the later refusal).
    req = _arbiter_request(issue_matrix_blocker="blocked by open issues")
    assert arbiter_persist_signal(req) is True
