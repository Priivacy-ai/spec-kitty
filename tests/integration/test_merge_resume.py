"""WP01/T002 — ``spec-kitty merge --resume`` is resumable and bounded.

Pins two contracts on resume:

1. **Idempotence**: when ``MergeState.completed_wps`` already covers every WP in
   ``wp_order``, re-running the merge does NOT re-call the per-WP done-recording
   pipeline. This is what protects an operator who ran merge to completion and
   then unintentionally re-runs it: nothing should happen.

2. **Resume after interruption**: when state shows partial progress, the
   resumed pass picks up exactly the remaining WPs and skips the completed
   ones — both at the lane-merge step and the mark-done step.

3. **Bounded**: the resumed run completes well within the NFR-005 30s budget
   for a 10-lane fixture (with the heavy work mocked out, this is also the
   default tolerance — we assert it is not pathologically slow).
"""

from __future__ import annotations

import contextlib
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.cli.commands.merge import _run_lane_based_merge
from specify_cli.merge.config import MergeStrategy
from specify_cli.merge.state import MergeState


pytestmark = [pytest.mark.git_repo, pytest.mark.non_sandbox]


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_git_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-qb", "main", str(repo)])
    _run(["git", "-C", str(repo), "config", "user.email", "test@test.com"])
    _run(["git", "-C", str(repo), "config", "user.name", "Test"])
    _run(["git", "-C", str(repo), "config", "commit.gpgsign", "false"])
    (repo / "README.md").write_text("init\n")
    _run(["git", "-C", str(repo), "add", "."])
    _run(["git", "-C", str(repo), "commit", "-m", "init"])


def _make_manifest(slug: str, lane_count: int = 10) -> MagicMock:
    manifest = MagicMock()
    manifest.target_branch = "main"
    manifest.mission_branch = f"kitty/mission-{slug}"
    lanes = []
    for i in range(lane_count):
        lane = MagicMock()
        lane.lane_id = f"lane-{chr(ord('a') + i)}"
        lane.wp_ids = [f"WP{i + 1:02d}"]
        lanes.append(lane)
    manifest.lanes = lanes
    return manifest


def _patches(
    *,
    tmp_path: Path,
    manifest: MagicMock,
    initial_state: MergeState | None,
    mark_done_calls: list[str],
    lane_merge_calls: list[str],
):
    lane_result = MagicMock()
    lane_result.success = True
    lane_result.errors = []

    mission_result = MagicMock()
    mission_result.success = True
    mission_result.commit = "abc1234"
    mission_result.errors = []

    def fake_run_command(cmd, *args, **kwargs):  # noqa: ANN001
        if "merge-base" in cmd:
            return (0, "abc123\n", "")
        return (0, "", "")

    def fake_lane_merge(repo_root, mission_slug, lane_id, lanes_manifest):  # noqa: ANN001
        lane_merge_calls.append(lane_id)
        return lane_result

    def fake_mark_done(repo_root, mission_slug, wp_id, target_branch):  # noqa: ANN001
        mark_done_calls.append(wp_id)

    return [
        patch("specify_cli.cli.commands.merge.require_lanes_json", return_value=manifest),
        patch("specify_cli.cli.commands.merge.load_state", return_value=initial_state),
        patch("specify_cli.cli.commands.merge.save_state"),
        patch("specify_cli.cli.commands.merge.get_main_repo_root", return_value=tmp_path),
        patch("specify_cli.cli.commands.merge.require_no_sparse_checkout"),
        patch("specify_cli.lanes.merge.merge_lane_to_mission", side_effect=fake_lane_merge),
        patch("specify_cli.lanes.merge.merge_mission_to_target", return_value=mission_result),
        patch("specify_cli.cli.commands.merge._mark_wp_merged_done", side_effect=fake_mark_done),
        patch("specify_cli.cli.commands.merge.safe_commit"),
        patch("specify_cli.cli.commands.merge._assert_merged_wps_reached_done"),
        patch("specify_cli.post_merge.stale_assertions.run_check"),
        patch("specify_cli.policy.merge_gates.evaluate_merge_gates"),
        patch("specify_cli.policy.config.load_policy_config"),
        patch("specify_cli.cli.commands.merge.run_command", side_effect=fake_run_command),
        patch("specify_cli.cli.commands.merge.has_remote", return_value=False),
        patch("specify_cli.cli.commands.merge.cleanup_merge_workspace"),
        patch("specify_cli.cli.commands.merge.clear_state"),
        patch("specify_cli.cli.commands.merge._bake_mission_number_into_mission_branch"),
        patch("specify_cli.cli.commands.merge.trigger_feature_dossier_sync_if_enabled"),
        patch("specify_cli.cli.commands.merge.emit_mission_closed"),
        patch("specify_cli.cli.commands.merge._emit_merge_diff_summary"),
    ]


def _wire_default_returns(stack):
    """Configure the policy/gate/run_check mocks that several patches need."""
    # Indices match _patches() above; pull the named ones out.
    # Simpler: walk the active mocks looking for the right names.
    for m in stack:
        target = getattr(m, "_mock_name", "") or ""
        if "run_check" in target or "evaluate_merge_gates" in target or "load_policy_config" in target:
            pass


class TestMergeResumeIdempotence:
    """When state shows full completion, re-running merge is a no-op for per-WP work."""

    def test_resume_full_state_is_no_op_for_mark_done(self, tmp_path: Path) -> None:
        slug = "test-resume-idempotent"
        _init_git_repo(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / slug
        feature_dir.mkdir(parents=True)

        manifest = _make_manifest(slug, lane_count=3)

        # State says all three WPs are completed already.
        existing = MergeState(
            mission_id=slug,
            mission_slug=slug,
            target_branch="main",
            wp_order=["WP01", "WP02", "WP03"],
            completed_wps=["WP01", "WP02", "WP03"],
        )

        mark_done_calls: list[str] = []
        lane_merge_calls: list[str] = []

        patches = _patches(
            tmp_path=tmp_path,
            manifest=manifest,
            initial_state=existing,
            mark_done_calls=mark_done_calls,
            lane_merge_calls=lane_merge_calls,
        )

        with contextlib.ExitStack() as stack:
            mocks = [stack.enter_context(p) for p in patches]
            # Wire default returns for run_check/policy/gates.
            stale_report = MagicMock()
            stale_report.findings = []
            mocks[10].return_value = stale_report  # run_check

            gate_eval = MagicMock()
            gate_eval.overall_pass = True
            gate_eval.gates = []
            mocks[11].return_value = gate_eval  # evaluate_merge_gates

            policy = MagicMock()
            policy.merge_gates = []
            mocks[12].return_value = policy  # load_policy_config

            _run_lane_based_merge(
                repo_root=tmp_path,
                mission_slug=slug,
                push=False,
                delete_branch=False,
                remove_worktree=False,
                strategy=MergeStrategy.SQUASH,
            )

        # Idempotence contract: every WP was already in completed_wps, so
        # _mark_wp_merged_done MUST NOT have been called for any of them.
        assert mark_done_calls == [], (
            f"FR-002/NFR-005 idempotence regression: re-running merge with a "
            f"fully-completed MergeState re-marked {mark_done_calls!r}. "
            "The per-WP done pipeline must skip already-completed WPs."
        )

        # Lane-merge step is also skipped per-lane when all WPs in a lane are done.
        assert lane_merge_calls == [], (
            f"Idempotence regression at the lane step: lanes "
            f"{lane_merge_calls!r} were re-merged even though every WP in each "
            "lane was already in completed_wps. See _run_lane_based_merge_locked "
            "lane-skip guard."
        )


class TestMergeResumeAfterInterruption:
    """When state shows partial completion, the resume pass picks up the rest only."""

    def test_resume_skips_completed_marks_remaining(self, tmp_path: Path) -> None:
        slug = "test-resume-partial"
        _init_git_repo(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / slug
        feature_dir.mkdir(parents=True)

        manifest = _make_manifest(slug, lane_count=3)
        # WP01 completed; WP02 and WP03 remaining.
        existing = MergeState(
            mission_id=slug,
            mission_slug=slug,
            target_branch="main",
            wp_order=["WP01", "WP02", "WP03"],
            completed_wps=["WP01"],
        )

        mark_done_calls: list[str] = []
        lane_merge_calls: list[str] = []

        patches = _patches(
            tmp_path=tmp_path,
            manifest=manifest,
            initial_state=existing,
            mark_done_calls=mark_done_calls,
            lane_merge_calls=lane_merge_calls,
        )

        with contextlib.ExitStack() as stack:
            mocks = [stack.enter_context(p) for p in patches]
            stale_report = MagicMock()
            stale_report.findings = []
            mocks[10].return_value = stale_report

            gate_eval = MagicMock()
            gate_eval.overall_pass = True
            gate_eval.gates = []
            mocks[11].return_value = gate_eval

            policy = MagicMock()
            policy.merge_gates = []
            mocks[12].return_value = policy

            _run_lane_based_merge(
                repo_root=tmp_path,
                mission_slug=slug,
                push=False,
                delete_branch=False,
                remove_worktree=False,
                strategy=MergeStrategy.SQUASH,
            )

        # WP01 already done — must not be re-marked.
        assert "WP01" not in mark_done_calls, f"Resume re-marked already-completed WP01: {mark_done_calls!r}"
        # WP02 + WP03 must be marked.
        assert "WP02" in mark_done_calls and "WP03" in mark_done_calls, f"Resume failed to finish remaining WPs: {mark_done_calls!r}"

        # Lane-a (WP01) skipped, lane-b/lane-c merged.
        assert "lane-a" not in lane_merge_calls, f"Resume re-merged completed lane-a: {lane_merge_calls!r}"
        assert "lane-b" in lane_merge_calls and "lane-c" in lane_merge_calls


class TestMergeResumeBounded:
    """NFR-005: resumed merge of a 10-lane fixture is fast."""

    def test_resume_completes_within_30s_budget(self, tmp_path: Path) -> None:
        slug = "test-resume-bounded"
        _init_git_repo(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / slug
        feature_dir.mkdir(parents=True)

        manifest = _make_manifest(slug, lane_count=10)
        wp_ids = [f"WP{i + 1:02d}" for i in range(10)]

        existing = MergeState(
            mission_id=slug,
            mission_slug=slug,
            target_branch="main",
            wp_order=wp_ids,
            completed_wps=[],  # full re-run
        )

        mark_done_calls: list[str] = []
        lane_merge_calls: list[str] = []

        patches = _patches(
            tmp_path=tmp_path,
            manifest=manifest,
            initial_state=existing,
            mark_done_calls=mark_done_calls,
            lane_merge_calls=lane_merge_calls,
        )

        start = time.monotonic()
        with contextlib.ExitStack() as stack:
            mocks = [stack.enter_context(p) for p in patches]
            stale_report = MagicMock()
            stale_report.findings = []
            mocks[10].return_value = stale_report

            gate_eval = MagicMock()
            gate_eval.overall_pass = True
            gate_eval.gates = []
            mocks[11].return_value = gate_eval

            policy = MagicMock()
            policy.merge_gates = []
            mocks[12].return_value = policy

            _run_lane_based_merge(
                repo_root=tmp_path,
                mission_slug=slug,
                push=False,
                delete_branch=False,
                remove_worktree=False,
                strategy=MergeStrategy.SQUASH,
            )
        elapsed = time.monotonic() - start

        assert elapsed < 30.0, f"NFR-005 budget regression: 10-lane resume took {elapsed:.2f}s (budget 30s). The merge code path is doing pathological work."
        # All 10 WPs eventually marked done.
        assert set(mark_done_calls) == set(wp_ids)
