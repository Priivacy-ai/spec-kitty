"""Tests for FR-019 (safe_commit insertion) and FR-020 (done events in git history).

The most important test is test_done_events_committed_to_git which uses
git show HEAD: to prove the events are durably committed after _run_lane_based_merge
returns (the canonical mechanically-correct assertion — NOT git reset --hard HEAD).

Note on patching: merge_lane_to_mission/merge_mission_to_target are imported locally inside
_run_lane_based_merge, so they must be patched at the source module level
(specify_cli.lanes.merge.*) not at specify_cli.cli.commands.merge.*.
evaluate_merge_gates and load_policy_config are similarly patched at their source paths.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from specify_cli.cli.commands.merge import _run_lane_based_merge
from specify_cli.merge.config import MergeStrategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_git_repo(path: Path, branch: str = "main") -> None:
    """Initialize a git repo with a signed-off initial commit."""
    subprocess.run(["git", "init", f"-b{branch}"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=path, check=True, capture_output=True
    )
    (path / "README.md").write_text("init\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "commit", "-m", "init"],
        cwd=path, check=True, capture_output=True,
    )


def _write_wp_file(tasks_dir: Path, wp_id: str, *, review_status: str = "approved", reviewed_by: str = "reviewer-1") -> None:
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / f"{wp_id}-impl.md").write_text(
        f"---\nwork_package_id: \"{wp_id}\"\nreview_status: \"{review_status}\"\nreviewed_by: \"{reviewed_by}\"\n---\n# {wp_id}\n",
        encoding="utf-8",
    )


def _seed_status_event(feature_dir: Path, mission_slug: str, wp_id: str, to_lane: str) -> None:
    """Write a minimal status event JSON line to status.events.jsonl."""
    event = {
        "actor": "test",
        "at": "2026-04-07T00:00:00+00:00",
        "event_id": f"TEST{wp_id}000",
        "evidence": None,
        "execution_mode": "direct_repo",
        "feature_slug": mission_slug,
        "force": True,
        "from_lane": "planned",
        "reason": "test seed",
        "review_ref": None,
        "to_lane": to_lane,
        "wp_id": wp_id,
    }
    jsonl_path = feature_dir / "status.events.jsonl"
    with jsonl_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# FR-019 unit test — safe_commit is called after _mark_wp_merged_done loop
# ---------------------------------------------------------------------------


class TestSafeCommitCalledAfterMarkDoneLoop:
    """FR-019: safe_commit is called with the correct args after the mark-done loop."""

    def test_safe_commit_is_called_with_correct_files(self, tmp_path: Path) -> None:
        mission_slug = "068-test-sc"
        feature_dir = tmp_path / "kitty-specs" / mission_slug
        feature_dir.mkdir(parents=True)

        manifest = MagicMock()
        manifest.target_branch = "main"
        manifest.mission_branch = f"kitty/mission-{mission_slug}"

        lane_a = MagicMock()
        lane_a.lane_id = "lane-a"
        lane_a.wp_ids = ["WP01"]
        manifest.lanes = [lane_a]

        lane_result = MagicMock()
        lane_result.success = True
        lane_result.errors = []

        mission_result = MagicMock()
        mission_result.success = True
        mission_result.commit = "abc1234"
        mission_result.errors = []

        with (
            patch("specify_cli.cli.commands.merge.require_lanes_json", return_value=manifest),
            patch("specify_cli.cli.commands.merge.load_state", return_value=None),
            patch("specify_cli.cli.commands.merge.save_state"),
            patch("specify_cli.cli.commands.merge.get_main_repo_root", return_value=tmp_path),
            patch("specify_cli.status.lane_reader.get_wp_lane", return_value="done"),
            patch("specify_cli.lanes.merge.merge_lane_to_mission", return_value=lane_result),
            patch("specify_cli.lanes.merge.merge_mission_to_target", return_value=mission_result),
            patch("specify_cli.cli.commands.merge._mark_wp_merged_done"),
            patch("specify_cli.cli.commands.merge.safe_commit", return_value=True) as mock_safe_commit,
            patch("specify_cli.post_merge.stale_assertions.run_check") as mock_run_check,
            patch("specify_cli.policy.merge_gates.evaluate_merge_gates") as mock_gates,
            patch("specify_cli.policy.config.load_policy_config") as mock_policy,
            patch("specify_cli.cli.commands.merge.run_command", return_value=(0, "abc123", "")),
            patch("specify_cli.cli.commands.merge.has_remote", return_value=False),
            patch("specify_cli.cli.commands.merge.cleanup_merge_workspace"),
            patch("specify_cli.cli.commands.merge.clear_state"),
            patch("specify_cli.merge.state.MergeState"),
        ):
            stale_report = MagicMock()
            stale_report.findings = []
            mock_run_check.return_value = stale_report

            gate_eval = MagicMock()
            gate_eval.overall_pass = True
            gate_eval.gates = []
            mock_gates.return_value = gate_eval

            policy = MagicMock()
            policy.merge_gates = []
            mock_policy.return_value = policy

            _run_lane_based_merge(
                repo_root=tmp_path,
                mission_slug=mission_slug,
                push=False,
                delete_branch=False,
                remove_worktree=False,
                strategy=MergeStrategy.SQUASH,
            )

        # Verify safe_commit was called once with the correct files
        mock_safe_commit.assert_called_once()
        kwargs = mock_safe_commit.call_args.kwargs
        assert kwargs["repo_path"] == tmp_path
        assert kwargs["allow_empty"] is False
        assert mission_slug in kwargs["commit_message"]
        # Verify both status files are in the payload
        files = kwargs["files_to_commit"]
        file_names = [f.name for f in files]
        assert "status.events.jsonl" in file_names
        assert "status.json" in file_names

    def test_safe_commit_called_before_worktree_removal(self, tmp_path: Path) -> None:
        """FR-019: safe_commit must precede any worktree removal step."""
        mission_slug = "068-test-order"
        feature_dir = tmp_path / "kitty-specs" / mission_slug
        feature_dir.mkdir(parents=True)

        call_order: list[str] = []

        manifest = MagicMock()
        manifest.target_branch = "main"
        manifest.mission_branch = f"kitty/mission-{mission_slug}"

        lane_a = MagicMock()
        lane_a.lane_id = "lane-a"
        lane_a.wp_ids = ["WP01"]
        wt_path = tmp_path / ".worktrees" / f"{mission_slug}-lane-a"
        wt_path.mkdir(parents=True)
        manifest.lanes = [lane_a]

        lane_result = MagicMock()
        lane_result.success = True
        lane_result.errors = []

        mission_result = MagicMock()
        mission_result.success = True
        mission_result.commit = "abc1234"
        mission_result.errors = []

        def record_safe_commit(**kwargs):  # noqa: ANN001
            call_order.append("safe_commit")
            return True

        def record_worktree_remove(cmd, **kwargs):  # noqa: ANN001
            if "worktree" in cmd and "remove" in cmd:
                call_order.append("worktree_remove")
            return (0, "", "")

        with (
            patch("specify_cli.cli.commands.merge.require_lanes_json", return_value=manifest),
            patch("specify_cli.cli.commands.merge.load_state", return_value=None),
            patch("specify_cli.cli.commands.merge.save_state"),
            patch("specify_cli.cli.commands.merge.get_main_repo_root", return_value=tmp_path),
            patch("specify_cli.status.lane_reader.get_wp_lane", return_value="done"),
            patch("specify_cli.lanes.merge.merge_lane_to_mission", return_value=lane_result),
            patch("specify_cli.lanes.merge.merge_mission_to_target", return_value=mission_result),
            patch("specify_cli.cli.commands.merge._mark_wp_merged_done"),
            patch("specify_cli.cli.commands.merge.safe_commit", side_effect=record_safe_commit),
            patch("specify_cli.post_merge.stale_assertions.run_check") as mock_run_check,
            patch("specify_cli.policy.merge_gates.evaluate_merge_gates") as mock_gates,
            patch("specify_cli.policy.config.load_policy_config") as mock_policy,
            patch("specify_cli.cli.commands.merge.run_command", side_effect=record_worktree_remove),
            patch("specify_cli.cli.commands.merge.has_remote", return_value=False),
            patch("specify_cli.cli.commands.merge.cleanup_merge_workspace"),
            patch("specify_cli.cli.commands.merge.clear_state"),
            patch("specify_cli.merge.state.MergeState"),
        ):
            stale_report = MagicMock()
            stale_report.findings = []
            mock_run_check.return_value = stale_report

            gate_eval = MagicMock()
            gate_eval.overall_pass = True
            gate_eval.gates = []
            mock_gates.return_value = gate_eval

            policy = MagicMock()
            policy.merge_gates = []
            mock_policy.return_value = policy

            _run_lane_based_merge(
                repo_root=tmp_path,
                mission_slug=mission_slug,
                push=False,
                delete_branch=False,
                remove_worktree=True,  # enable worktree removal to test ordering
                strategy=MergeStrategy.SQUASH,
            )

        # safe_commit must appear before any worktree_remove in the call order
        if "worktree_remove" in call_order:
            sc_idx = call_order.index("safe_commit")
            wr_idx = call_order.index("worktree_remove")
            assert sc_idx < wr_idx, (
                f"safe_commit (idx={sc_idx}) must precede worktree_remove (idx={wr_idx}). "
                "FR-019: persist events before destroying worktree."
            )


# ---------------------------------------------------------------------------
# FR-020 — done events committed to git (the canonical regression test)
# ---------------------------------------------------------------------------


class TestDoneEventsCommittedToGit:
    """FR-020: after _run_lane_based_merge, done events are in git history at HEAD.

    Uses git show HEAD: — the mechanically-correct assertion.
    Does NOT use git reset --hard HEAD (that would be a no-op).
    """

    def test_done_events_committed_to_git(self, tmp_path: Path) -> None:
        """FR-019/FR-020 regression: safe_commit must persist status.events.jsonl to git."""
        mission_slug = "068-done-events-test"
        wps = ["WP01", "WP02"]

        # Set up a real git repo
        _init_git_repo(tmp_path)

        feature_dir = tmp_path / "kitty-specs" / mission_slug
        feature_dir.mkdir(parents=True)
        tasks_dir = feature_dir / "tasks"

        for wp_id in wps:
            _write_wp_file(tasks_dir, wp_id)

        # Commit the initial feature directory to git (without status files)
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "-c", "commit.gpgsign=false", "commit", "-m", "initial feature"],
            cwd=tmp_path, check=True, capture_output=True,
        )

        # Seed event log entries (approved state for each WP, as they would be pre-merge)
        for wp_id in wps:
            _seed_status_event(feature_dir, mission_slug, wp_id, "approved")

        # Materialize status.json
        from specify_cli.status.reducer import materialize
        materialize(feature_dir)

        manifest = MagicMock()
        manifest.target_branch = "main"
        manifest.mission_branch = f"kitty/mission-{mission_slug}"

        lane_a = MagicMock()
        lane_a.lane_id = "lane-a"
        lane_a.wp_ids = ["WP01"]

        lane_b = MagicMock()
        lane_b.lane_id = "lane-b"
        lane_b.wp_ids = ["WP02"]

        manifest.lanes = [lane_a, lane_b]

        lane_result = MagicMock()
        lane_result.success = True
        lane_result.errors = []

        mission_result = MagicMock()
        mission_result.success = True
        mission_result.commit = "deadbeef"
        mission_result.errors = []

        with (
            patch("specify_cli.cli.commands.merge.require_lanes_json", return_value=manifest),
            patch("specify_cli.cli.commands.merge.load_state", return_value=None),
            patch("specify_cli.cli.commands.merge.save_state"),
            patch("specify_cli.cli.commands.merge.get_main_repo_root", return_value=tmp_path),
            patch("specify_cli.lanes.merge.merge_lane_to_mission", return_value=lane_result),
            patch("specify_cli.lanes.merge.merge_mission_to_target", return_value=mission_result),
            patch("specify_cli.post_merge.stale_assertions.run_check") as mock_run_check,
            patch("specify_cli.policy.merge_gates.evaluate_merge_gates") as mock_gates,
            patch("specify_cli.policy.config.load_policy_config") as mock_policy,
            patch("specify_cli.cli.commands.merge.run_command", return_value=(0, "abc123", "")),
            patch("specify_cli.cli.commands.merge.has_remote", return_value=False),
            patch("specify_cli.cli.commands.merge.cleanup_merge_workspace"),
            patch("specify_cli.cli.commands.merge.clear_state"),
            patch("specify_cli.merge.state.MergeState"),
        ):
            stale_report = MagicMock()
            stale_report.findings = []
            mock_run_check.return_value = stale_report

            gate_eval = MagicMock()
            gate_eval.overall_pass = True
            gate_eval.gates = []
            mock_gates.return_value = gate_eval

            policy = MagicMock()
            policy.merge_gates = []
            mock_policy.return_value = policy

            # Run the full merge
            _run_lane_based_merge(
                repo_root=tmp_path,
                mission_slug=mission_slug,
                push=False,
                delete_branch=False,
                remove_worktree=False,
                strategy=MergeStrategy.SQUASH,
            )

        # FR-020: read status.events.jsonl from git history, NOT from the working tree
        result = subprocess.run(
            ["git", "show", f"HEAD:kitty-specs/{mission_slug}/status.events.jsonl"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        )
        events = [
            json.loads(line)
            for line in result.stdout.splitlines()
            if line.strip()
        ]
        done_wps = {e["wp_id"] for e in events if e.get("to_lane") == "done"}

        assert done_wps == set(wps), (
            f"Expected done events for every merged WP in git history. "
            f"Got {done_wps}, expected {set(wps)}. "
            "This regression means the FR-019 safe_commit step was missed or failed."
        )
        # Explicitly: do NOT use git reset --hard HEAD here — that would be a no-op
        # (the file is already at HEAD) and proves nothing about the commit having occurred.
