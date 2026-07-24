"""Focused coverage for the merge executor phase helpers (mission #2057, NFR-002).

Post-review note: the executor seam fell below the NFR-002 >=90% line-coverage
bar — its error-recovery / cleanup / banner branches were exercised only through
broad integration tests, not directly. These tests drive each phase helper with
a real ``_MergeRunState`` and mocked git/IO boundaries so every restore-on-error,
skip, and fail-loud branch is hit (each test fails if its target branch is
removed). Behaviour-preserving: no executor source is modified.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import typer

from specify_cli.merge import executor as ex
from specify_cli.merge.state import MergeState
from specify_cli.post_merge.stale_assertions import (
    Confidence,
    StaleAssertionFinding,
    StaleAssertionReport,
)

pytestmark = pytest.mark.fast


def _make_run(
    tmp_path: Path,
    *,
    done_marked_before_target: bool = False,
    planning_artifact_only: bool = False,
    is_resume: bool = False,
    push: bool = False,
    remove_worktree: bool = True,
    delete_branch: bool = True,
) -> ex._MergeRunState:
    lanes_manifest = SimpleNamespace(
        target_branch="main",
        mission_branch="kitty/mission-m",
        lanes=[SimpleNamespace(lane_id="lane-a", wp_ids=["WP01"])],
    )
    state = MergeState(
        mission_id="01ID", mission_slug="m", target_branch="main", wp_order=["WP01"]
    )
    run = ex._MergeRunState(
        main_repo=tmp_path,
        mission_slug="m",
        canonical_id="01ID",
        canonical_mission_id="01JQANARZAP70V8DVJZ8XN0M3T",
        feature_dir=tmp_path / "kitty-specs" / "m",
        target_feature_dir=tmp_path / "kitty-specs" / "m",
        lanes_manifest=lanes_manifest,
        all_wp_ids=["WP01"],
        push=push,
        delete_branch=delete_branch,
        remove_worktree=remove_worktree,
        strategy=ex.MergeStrategy.SQUASH,
        assume_yes=True,
        planning_artifact_only=planning_artifact_only,
        state=state,
        is_resume=is_resume,
        done_marked_before_target=done_marked_before_target,
    )
    run.canonical_events_path = tmp_path / "kitty-specs" / "m" / "status.events.jsonl"
    run.canonical_status_path = tmp_path / "kitty-specs" / "m" / "status.json"
    run.merge_state_path = tmp_path / "state.json"
    run.target_baseline_sha = "abc123"
    run.baseline_mission_id = "01ID"
    return run


# --- _emit_merge_diff_summary ----------------------------------------------


def test_emit_diff_summary_returns_early_when_git_fails(tmp_path: Path) -> None:
    with (
        patch.object(ex, "run_command", return_value=(1, "", "err")),
        patch.object(ex, "emit_diff_summary_recorded") as emit_mock,
    ):
        ex._emit_merge_diff_summary(
            repo_root=tmp_path, mission_id="01ID", base_ref="abc"
        )
    emit_mock.assert_not_called()


def test_emit_diff_summary_skips_when_zero_changes(tmp_path: Path) -> None:
    # numstat with malformed/short lines only -> files_changed stays 0 -> no emit.
    with (
        patch.object(ex, "run_command", return_value=(0, "badline\n\n", "")),
        patch.object(ex, "emit_diff_summary_recorded") as emit_mock,
    ):
        ex._emit_merge_diff_summary(
            repo_root=tmp_path, mission_id="01ID", base_ref="abc"
        )
    emit_mock.assert_not_called()


def test_emit_diff_summary_emits_parsed_numstat(tmp_path: Path) -> None:
    numstat = "10\t2\tsrc/a.py\n-\t-\tbin\n5\t0\tsrc/b.py\n"
    with (
        patch.object(ex, "run_command", return_value=(0, numstat, "")),
        patch.object(ex, "emit_diff_summary_recorded") as emit_mock,
    ):
        ex._emit_merge_diff_summary(
            repo_root=tmp_path, mission_id="01ID", base_ref="abc"
        )
    emit_mock.assert_called_once()
    kwargs = emit_mock.call_args.kwargs
    # Three numstat rows -> 3 files; binary "-" rows are counted as files but
    # contribute no line totals.
    assert kwargs["files_changed"] == 3
    assert kwargs["lines_added"] == 15
    assert kwargs["lines_deleted"] == 2


# --- _phase_gates_and_state -------------------------------------------------


def test_phase_gates_exits_when_gates_fail(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    gate = SimpleNamespace(verdict="fail", blocking=True, gate_name="g", details="d")
    gate_eval = SimpleNamespace(gates=[gate], overall_pass=False)
    with (
        patch("specify_cli.policy.config.load_policy_config", return_value=SimpleNamespace(merge_gates=[])),
        patch("specify_cli.policy.merge_gates.evaluate_merge_gates", return_value=gate_eval),
        pytest.raises(typer.Exit) as exc,
    ):
        ex._phase_gates_and_state(run)
    assert exc.value.exit_code == 1


def test_phase_gates_passes_and_prints_resume_banner(tmp_path: Path) -> None:
    run = _make_run(tmp_path, is_resume=True)
    run.state.completed_wps = []
    gate = SimpleNamespace(verdict="pass", blocking=False, gate_name="g", details="ok")
    gate_eval = SimpleNamespace(gates=[gate], overall_pass=True)
    with (
        patch("specify_cli.policy.config.load_policy_config", return_value=SimpleNamespace(merge_gates=[])),
        patch("specify_cli.policy.merge_gates.evaluate_merge_gates", return_value=gate_eval),
        patch.object(ex, "_enforce_canonical_status_history") as hist_mock,
        patch.object(ex, "_warn_or_confirm_hollow_reviews") as hollow_mock,
    ):
        ex._phase_gates_and_state(run)
    hist_mock.assert_called_once()
    hollow_mock.assert_called_once()


# --- _phase_merge_lanes -----------------------------------------------------


def test_phase_merge_lanes_skips_already_integrated(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    with (
        patch("specify_cli.lanes.branch_naming.lane_branch_name", return_value="kitty/lane-a"),
        patch("specify_cli.lanes.compute.is_planning_lane", return_value=False),
        patch.object(ex, "_lane_already_integrated", return_value=True),
        patch("specify_cli.lanes.merge.consolidate_lane_into_mission") as merge_mock,
    ):
        ex._phase_merge_lanes(run)
    merge_mock.assert_not_called()
    assert run.any_lane_had_unintegrated_code is False


def test_phase_merge_lanes_success_marks_unintegrated(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    result = SimpleNamespace(success=True, errors=[])
    with (
        patch("specify_cli.lanes.branch_naming.lane_branch_name", return_value="kitty/lane-a"),
        patch("specify_cli.lanes.compute.is_planning_lane", return_value=False),
        patch.object(ex, "_lane_already_integrated", return_value=False),
        patch("specify_cli.lanes.merge.consolidate_lane_into_mission", return_value=result),
    ):
        ex._phase_merge_lanes(run)
    assert run.any_lane_had_unintegrated_code is True


def test_phase_merge_lanes_resume_tolerates_already_merged(tmp_path: Path) -> None:
    run = _make_run(tmp_path, is_resume=True)
    result = SimpleNamespace(success=False, errors=["lane already up to date"])
    with (
        patch("specify_cli.lanes.branch_naming.lane_branch_name", return_value="kitty/lane-a"),
        patch("specify_cli.lanes.compute.is_planning_lane", return_value=False),
        patch.object(ex, "_lane_already_integrated", return_value=False),
        patch("specify_cli.lanes.merge.consolidate_lane_into_mission", return_value=result),
    ):
        # No Exit raised because resume + "already" error is tolerated.
        ex._phase_merge_lanes(run)


def test_phase_merge_lanes_hard_failure_exits(tmp_path: Path) -> None:
    run = _make_run(tmp_path, is_resume=False)
    result = SimpleNamespace(success=False, errors=["conflict in foo.py"])
    with (
        patch("specify_cli.lanes.branch_naming.lane_branch_name", return_value="kitty/lane-a"),
        patch("specify_cli.lanes.compute.is_planning_lane", return_value=False),
        patch.object(ex, "_lane_already_integrated", return_value=False),
        patch("specify_cli.lanes.merge.consolidate_lane_into_mission", return_value=result),
        pytest.raises(typer.Exit) as exc,
    ):
        ex._phase_merge_lanes(run)
    assert exc.value.exit_code == 1


def test_phase_merge_lanes_planning_lane_already_on_target(tmp_path: Path) -> None:
    run = _make_run(tmp_path, planning_artifact_only=True)
    with (
        patch("specify_cli.lanes.compute.is_planning_lane", return_value=True),
        patch("specify_cli.lanes.merge.consolidate_lane_into_mission") as merge_mock,
    ):
        ex._phase_merge_lanes(run)
    merge_mock.assert_not_called()


# --- _phase_baseline_and_surface --------------------------------------------


def test_phase_baseline_and_surface_resolves_paths(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    surface = tmp_path / ".worktrees" / "m-coord" / "kitty-specs" / "m" / "status.events.jsonl"
    with (
        patch.object(ex, "run_command", return_value=(0, "deadbeef\n", "")),
        patch.object(ex, "resolve_mission_identity", return_value=SimpleNamespace(mission_id="01XID")),
        patch.object(ex, "resolve_status_surface", return_value=surface),
        patch.object(ex, "is_under_worktrees_segment", return_value=True),
        patch.object(ex, "get_state_path", return_value=tmp_path / "state.json"),
    ):
        ex._phase_baseline_and_surface(run)
    assert run.target_baseline_sha == "deadbeef"
    assert run.baseline_mission_id == "01XID"
    assert run.done_marked_before_target is True
    assert run.canonical_events_path == surface


def test_phase_baseline_and_surface_handles_missing_identity(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    surface = tmp_path / "kitty-specs" / "m" / "status.events.jsonl"
    with (
        patch.object(ex, "run_command", return_value=(1, "", "fatal")),
        patch.object(ex, "resolve_mission_identity", side_effect=ValueError("no meta")),
        patch.object(ex, "resolve_status_surface", return_value=surface),
        patch.object(ex, "is_under_worktrees_segment", return_value=False),
        patch.object(ex, "get_state_path", return_value=tmp_path / "state.json"),
    ):
        ex._phase_baseline_and_surface(run)
    # git rev-parse failed -> baseline falls back to HEAD~1.
    assert run.target_baseline_sha == "HEAD~1"
    assert run.baseline_mission_id is None
    assert run.done_marked_before_target is False


# --- _phase_bake_and_pre_target_done ----------------------------------------


def test_phase_bake_planning_only_short_circuits(tmp_path: Path) -> None:
    run = _make_run(tmp_path, planning_artifact_only=True)
    with patch.object(ex, "_bake_mission_number_into_mission_branch") as bake_mock:
        ex._phase_bake_and_pre_target_done(run)
    bake_mock.assert_not_called()
    assert run.mission_already_applied is True


def test_phase_bake_pre_target_done_restores_on_record_failure(tmp_path: Path) -> None:
    run = _make_run(tmp_path, done_marked_before_target=True)
    restored: list[dict[Path, bytes | None]] = []
    with (
        patch.object(ex, "_bake_mission_number_into_mission_branch", return_value=None),
        patch.object(ex, "_capture_merge_snapshots", return_value={tmp_path / "x": b"o"}),
        patch.object(ex, "_record_merged_wps_done_for_merge", side_effect=RuntimeError("boom")),
        patch.object(ex, "restore_generated_artifact_snapshots", side_effect=lambda s: restored.append(s)),
        pytest.raises(RuntimeError, match="boom"),
    ):
        ex._phase_bake_and_pre_target_done(run)
    assert restored == [{tmp_path / "x": b"o"}]


def test_phase_bake_pre_target_done_success_records(tmp_path: Path) -> None:
    run = _make_run(tmp_path, done_marked_before_target=True)
    with (
        patch.object(ex, "_bake_mission_number_into_mission_branch", return_value=None),
        patch.object(ex, "_capture_merge_snapshots", return_value={}),
        patch.object(ex, "_record_merged_wps_done_for_merge") as record_mock,
    ):
        ex._phase_bake_and_pre_target_done(run)
    record_mock.assert_called_once()


# --- _phase_mission_to_target / _handle_mission_merge_result ----------------


def test_phase_mission_to_target_planning_only_returns(tmp_path: Path) -> None:
    run = _make_run(tmp_path, planning_artifact_only=True)
    with patch("specify_cli.lanes.merge.integrate_mission_into_target") as merge_mock:
        ex._phase_mission_to_target(run)
    merge_mock.assert_not_called()


def test_phase_mission_to_target_restores_on_exception(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    restored: list[object] = []
    with (
        patch.object(ex, "_branch_trees_equal", return_value=False),
        patch("specify_cli.lanes.merge.integrate_mission_into_target", side_effect=RuntimeError("merge died")),
        patch.object(ex, "_restore_pre_target_if_at_baseline", side_effect=lambda r: restored.append(r)),
        pytest.raises(RuntimeError, match="merge died"),
    ):
        ex._phase_mission_to_target(run)
    assert restored == [run]


def test_phase_mission_to_target_success(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    result = SimpleNamespace(success=True, errors=[], commit="abcdef1234", already_applied=False)
    with (
        patch.object(ex, "_branch_trees_equal", return_value=False),
        patch("specify_cli.lanes.merge.integrate_mission_into_target", return_value=result),
    ):
        ex._phase_mission_to_target(run)
    assert run.mission_already_applied is False


def test_handle_result_rejects_zero_diff_noop_squash(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    run.any_lane_had_unintegrated_code = True
    result = SimpleNamespace(success=True, errors=[], commit=None, already_applied=True)
    with (
        patch.object(ex, "_restore_pre_target_if_at_baseline") as restore_mock,
        pytest.raises(typer.Exit) as exc,
    ):
        ex._handle_mission_merge_result(
            run, result, mission_integrated_into_target=False
        )
    assert exc.value.exit_code == 1
    restore_mock.assert_called_once_with(run)


def test_handle_result_resume_tolerates_already_merged(tmp_path: Path) -> None:
    run = _make_run(tmp_path, is_resume=True)
    result = SimpleNamespace(success=False, errors=["already up to date"], commit=None, already_applied=False)
    # No Exit because resume tolerates the already-merged error.
    ex._handle_mission_merge_result(run, result, mission_integrated_into_target=True)


def test_handle_result_hard_failure_restores_and_exits(tmp_path: Path) -> None:
    run = _make_run(tmp_path, is_resume=False)
    result = SimpleNamespace(success=False, errors=["real conflict"], commit=None, already_applied=False)
    with (
        patch.object(ex, "_restore_pre_target_if_at_baseline") as restore_mock,
        pytest.raises(typer.Exit) as exc,
    ):
        ex._handle_mission_merge_result(run, result, mission_integrated_into_target=False)
    assert exc.value.exit_code == 1
    restore_mock.assert_called_once_with(run)


# --- _restore_pre_target_if_at_baseline -------------------------------------


def test_restore_pre_target_restores_only_when_at_baseline(tmp_path: Path) -> None:
    run = _make_run(tmp_path, done_marked_before_target=True)
    run.pre_target_bookkeeping_snapshots = {tmp_path / "x": b"o"}
    restored: list[object] = []
    with (
        patch.object(ex, "_target_branch_still_at_baseline", return_value=True),
        patch.object(ex, "restore_generated_artifact_snapshots", side_effect=lambda s: restored.append(s)),
    ):
        ex._restore_pre_target_if_at_baseline(run)
    assert restored == [{tmp_path / "x": b"o"}]


def test_restore_pre_target_noop_when_target_advanced(tmp_path: Path) -> None:
    run = _make_run(tmp_path, done_marked_before_target=True)
    with (
        patch.object(ex, "_target_branch_still_at_baseline", return_value=False),
        patch.object(ex, "restore_generated_artifact_snapshots") as restore_mock,
    ):
        ex._restore_pre_target_if_at_baseline(run)
    restore_mock.assert_not_called()


# --- _phase_record_done_and_project -----------------------------------------


def test_phase_record_done_restores_on_record_failure(tmp_path: Path) -> None:
    run = _make_run(tmp_path, done_marked_before_target=False)
    run.final_bookkeeping_snapshots = {tmp_path / "x": b"o"}
    restored: list[object] = []
    with (
        patch.object(ex, "_record_merged_wps_done_for_merge", side_effect=RuntimeError("boom")),
        patch.object(ex, "restore_generated_artifact_snapshots", side_effect=lambda s: restored.append(s)),
        pytest.raises(RuntimeError, match="boom"),
    ):
        ex._phase_record_done_and_project(run)
    assert restored == [{tmp_path / "x": b"o"}]


def test_phase_record_done_restores_on_project_failure(tmp_path: Path) -> None:
    run = _make_run(tmp_path, done_marked_before_target=True)  # skip record path
    run.final_bookkeeping_snapshots = {tmp_path / "x": b"o"}
    restored: list[object] = []
    with (
        patch.object(ex, "_project_status_bookkeeping_to_target", side_effect=RuntimeError("proj")),
        patch.object(ex, "restore_generated_artifact_snapshots", side_effect=lambda s: restored.append(s)),
        pytest.raises(RuntimeError, match="proj"),
    ):
        ex._phase_record_done_and_project(run)
    assert restored == [{tmp_path / "x": b"o"}]


def test_phase_record_done_success_sets_target_paths(tmp_path: Path) -> None:
    run = _make_run(tmp_path, done_marked_before_target=True)
    events_p = tmp_path / "e.jsonl"
    status_p = tmp_path / "s.json"
    with patch.object(ex, "_project_status_bookkeeping_to_target", return_value=(events_p, status_p)):
        ex._phase_record_done_and_project(run)
    assert run.target_events_path == events_p
    assert run.target_status_path == status_p


# --- _phase_porcelain_invariant: git-status-failed skip ----------------------


def test_phase_porcelain_skips_when_git_status_fails(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    with (
        patch.object(ex, "_raw_porcelain_status", return_value=(1, "")),
        patch.object(ex, "restore_generated_artifact_snapshots") as restore_mock,
    ):
        ex._phase_porcelain_invariant(run)
    restore_mock.assert_not_called()


def test_phase_porcelain_clean_tree_passes(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    with (
        patch.object(ex, "_raw_porcelain_status", return_value=(0, "")),
        patch.object(ex, "_classify_porcelain_lines", return_value=([], 0)),
        patch.object(ex, "restore_generated_artifact_snapshots") as restore_mock,
    ):
        ex._phase_porcelain_invariant(run)
    restore_mock.assert_not_called()


# --- _phase_commit_and_assert: no-changes + baseline-assert-failure ----------


def test_phase_commit_skips_when_no_bookkeeping_changes(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    run.target_events_path = tmp_path / "e.jsonl"
    run.target_status_path = tmp_path / "s.json"
    with (
        patch.object(ex, "_paths_have_status_changes", return_value=False),
        patch.object(ex, "commit_merge_bookkeeping") as commit_mock,
        patch.object(ex, "_assert_merged_wps_done_on_target"),
        patch.object(ex, "_assert_baseline_merge_commit_on_target"),
    ):
        ex._phase_commit_and_assert(run)
    commit_mock.assert_not_called()


def test_phase_commit_baseline_assert_failure_exits(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    run.target_events_path = tmp_path / "e.jsonl"
    run.target_status_path = tmp_path / "s.json"
    with (
        patch.object(ex, "_paths_have_status_changes", return_value=False),
        patch.object(ex, "_assert_merged_wps_done_on_target"),
        patch.object(
            ex,
            "_assert_baseline_merge_commit_on_target",
            side_effect=ex.BaselineMergeCommitError("baseline missing"),
        ),
        pytest.raises(typer.Exit) as exc,
    ):
        ex._phase_commit_and_assert(run)
    assert exc.value.exit_code == 1


def test_phase_commit_recovered_safe_commit_does_not_restore(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    run.target_events_path = tmp_path / "e.jsonl"
    run.target_status_path = tmp_path / "s.json"
    run.final_bookkeeping_snapshots = {tmp_path / "x": b"o"}
    recovered = ex.SafeCommitRecoveryFailed("recovered")
    recovered.commit_sha = "abc123"
    with (
        patch.object(ex, "_paths_have_status_changes", return_value=True),
        patch.object(ex, "commit_merge_bookkeeping", side_effect=recovered),
        patch.object(ex, "restore_generated_artifact_snapshots") as restore_mock,
        pytest.raises(ex.SafeCommitRecoveryFailed),
    ):
        ex._phase_commit_and_assert(run)
    # A recovered commit (commit_sha set) must NOT restore — the commit landed.
    restore_mock.assert_not_called()


# --- _phase_dossier_and_stale -----------------------------------------------


def test_phase_dossier_and_stale_swallows_stale_failure(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    with (
        patch.object(ex, "trigger_feature_dossier_sync_if_enabled"),
        patch.object(ex, "run_check", side_effect=RuntimeError("scan crashed")),
    ):
        ex._phase_dossier_and_stale(run)
    assert run.stale_report is None


def test_phase_dossier_and_stale_records_report(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    report = StaleAssertionReport(
        base_ref="a", head_ref="HEAD", repo_root=tmp_path, findings=[],
        elapsed_seconds=0.1, files_scanned=1, findings_per_100_loc=0.0,
    )
    with (
        patch.object(ex, "trigger_feature_dossier_sync_if_enabled"),
        patch.object(ex, "run_check", return_value=report),
    ):
        ex._phase_dossier_and_stale(run)
    assert run.stale_report is report


# --- _phase_push ------------------------------------------------------------


def test_phase_push_noop_without_push_flag(tmp_path: Path) -> None:
    run = _make_run(tmp_path, push=False)
    with patch.object(ex, "run_command") as cmd_mock:
        ex._phase_push(run)
    cmd_mock.assert_not_called()


def test_phase_push_success(tmp_path: Path) -> None:
    run = _make_run(tmp_path, push=True)
    with (
        patch.object(ex, "has_remote", return_value=True),
        patch.object(ex, "run_command", return_value=(0, "", "")),
    ):
        ex._phase_push(run)


def test_phase_push_failure_with_linear_history_hint_exits(tmp_path: Path) -> None:
    run = _make_run(tmp_path, push=True)
    with (
        patch.object(ex, "has_remote", return_value=True),
        patch.object(ex, "run_command", return_value=(1, "", "non-fast-forward")),
        patch.object(ex, "_is_linear_history_rejection", return_value=True),
        patch.object(ex, "_emit_remediation_hint") as hint_mock,
        pytest.raises(typer.Exit) as exc,
    ):
        ex._phase_push(run)
    assert exc.value.exit_code == 1
    hint_mock.assert_called_once()


# --- _phase_cleanup_worktrees_and_branches ----------------------------------


def test_phase_cleanup_removes_worktrees_and_branches(tmp_path: Path) -> None:
    run = _make_run(tmp_path, remove_worktree=True, delete_branch=True)
    wt = tmp_path / ".worktrees" / "m-lane-a"
    wt.mkdir(parents=True)
    calls: list[list[str]] = []

    def _fake_cmd(args: list[str], **kwargs: object) -> tuple[int, str, str]:
        calls.append(list(args))
        # rev-parse --verify -> branch exists (ret 0); everything else ret 0.
        return (0, "", "")

    with (
        patch("specify_cli.lanes.branch_naming.lane_branch_name", return_value="kitty/lane-a"),
        patch("specify_cli.lanes.branch_naming.worktree_path", return_value=wt),
        patch("specify_cli.lanes.compute.is_planning_lane", return_value=False),
        patch.object(ex, "_worktree_removal_delay", return_value=0),
        patch.object(ex, "run_command", side_effect=_fake_cmd),
        patch("specify_cli.mission_metadata.load_meta", return_value={"mid8": "deadbeef"}),
        # WP04 (#2119): coordination teardown now routes through the shared
        # ``teardown_coordination_topology`` seam. Patch the seam's real destroy
        # target (``coordination.workspace``) and stub the persist leg.
        patch("specify_cli.post_merge.retrospective_terminus.run_retrospective_postcondition"),
        patch("specify_cli.coordination.workspace.CoordinationWorkspace") as cw_mock,
    ):
        ex._phase_cleanup_worktrees_and_branches(run)
    # The worktree removal command ran.
    assert any(c[:3] == ["git", "worktree", "remove"] for c in calls)
    # A branch deletion ran (branch existed).
    assert any(c[:3] == ["git", "branch", "-D"] for c in calls)
    cw_mock.teardown.assert_called_once()


def test_phase_cleanup_skips_missing_worktree_and_branch(tmp_path: Path) -> None:
    run = _make_run(tmp_path, remove_worktree=True, delete_branch=True)
    missing_wt = tmp_path / ".worktrees" / "absent"  # does not exist
    calls: list[list[str]] = []

    def _fake_cmd(args: list[str], **kwargs: object) -> tuple[int, str, str]:
        calls.append(list(args))
        # rev-parse --verify -> branch missing (ret 1); other cmds ret 0.
        if list(args)[:3] == ["git", "rev-parse", "--verify"]:
            return (1, "", "not found")
        return (0, "", "")

    with (
        patch("specify_cli.lanes.branch_naming.lane_branch_name", return_value="kitty/lane-a"),
        patch("specify_cli.lanes.branch_naming.worktree_path", return_value=missing_wt),
        patch("specify_cli.lanes.compute.is_planning_lane", return_value=False),
        patch.object(ex, "_worktree_removal_delay", return_value=0),
        patch.object(ex, "run_command", side_effect=_fake_cmd),
        patch("specify_cli.mission_metadata.load_meta", return_value={}),
        # WP04 (#2119): the seam runs the persist leg before the (no-op) destroy;
        # stub it so an empty-meta mission does not hit the real generator.
        patch("specify_cli.post_merge.retrospective_terminus.run_retrospective_postcondition"),
    ):
        ex._phase_cleanup_worktrees_and_branches(run)
    # Worktree absent -> never removed; branch missing -> never deleted.
    assert not any(c[:3] == ["git", "worktree", "remove"] for c in calls)
    assert not any(c[:3] == ["git", "branch", "-D"] for c in calls)


def test_phase_cleanup_coord_teardown_failure_is_non_fatal(tmp_path: Path) -> None:
    # WP04 (#2119): the cleanup phase now routes coordination teardown through the
    # shared ``teardown_coordination_topology`` seam, which persists the
    # retrospective BEFORE destroying the worktree. The DESTROY leg stays
    # best-effort: a worktree-removal failure must NOT raise out of the phase.
    # Patch the seam's real destroy target (``coordination.workspace``) so the
    # fault injection genuinely exercises the swallowed destroy, and stub the
    # persist leg (which runs OUTSIDE the swallow) so it does not interfere.
    run = _make_run(tmp_path, remove_worktree=True, delete_branch=False)
    with (
        patch.object(ex, "_worktree_removal_delay", return_value=0),
        patch.object(ex, "run_command", return_value=(0, "", "")),
        patch("specify_cli.lanes.branch_naming.worktree_path", return_value=tmp_path / "absent"),
        patch("specify_cli.mission_metadata.load_meta", return_value={"mid8": "deadbeef"}),
        patch("specify_cli.post_merge.retrospective_terminus.run_retrospective_postcondition"),
        patch("specify_cli.coordination.workspace.CoordinationWorkspace") as cw_mock,
    ):
        cw_mock.teardown.side_effect = RuntimeError("teardown boom")
        # Must not raise — the destroy leg inside the seam is best-effort.
        ex._phase_cleanup_worktrees_and_branches(run)
        # The destroy leg WAS reached (proves the seam routed to teardown).
        cw_mock.teardown.assert_called_once()


# --- _phase_finalize_and_summary --------------------------------------------


def test_phase_finalize_and_summary_runs_all_steps(tmp_path: Path) -> None:
    run = _make_run(tmp_path)
    with (
        patch.object(ex, "cleanup_merge_workspace") as cleanup_mock,
        patch.object(ex, "clear_state") as clear_mock,
        patch.object(ex, "_emit_merge_diff_summary") as diff_mock,
        patch.object(ex, "emit_mission_closed") as closed_mock,
    ):
        ex._phase_finalize_and_summary(run)
    cleanup_mock.assert_called_once()
    clear_mock.assert_called_once()
    diff_mock.assert_called_once()
    closed_mock.assert_called_once()


# --- _render_stale_findings -------------------------------------------------


def _finding(confidence: Confidence) -> StaleAssertionFinding:
    return StaleAssertionFinding(
        test_file=Path("tests/test_x.py"),
        test_line=10,
        source_file=Path("src/x.py"),
        source_line=5,
        changed_symbol="foo",
        confidence=confidence,
        hint="symbol foo changed",
    )


def test_render_stale_findings_none_report() -> None:
    ex._render_stale_findings(None)


def test_render_stale_findings_no_findings(tmp_path: Path) -> None:
    report = StaleAssertionReport(
        base_ref="a", head_ref="HEAD", repo_root=tmp_path, findings=[],
        elapsed_seconds=0.1, files_scanned=1, findings_per_100_loc=0.0,
    )
    ex._render_stale_findings(report)


def test_render_stale_findings_all_grades(tmp_path: Path) -> None:
    report = StaleAssertionReport(
        base_ref="a", head_ref="HEAD", repo_root=tmp_path,
        findings=[
            _finding("high"),
            _finding("medium"),
            _finding("low"),
            _finding("info"),
        ],
        elapsed_seconds=0.1, files_scanned=2, findings_per_100_loc=1.0,
    )
    ex._render_stale_findings(report)
