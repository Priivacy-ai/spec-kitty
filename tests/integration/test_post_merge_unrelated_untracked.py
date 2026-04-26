"""WP01/T004 — post-merge bookkeeping tolerates untracked files (FR-004).

Untracked ``.worktrees/`` and unrelated untracked files (e.g. a stray
``tmp.txt``) must not block the post-merge bookkeeping pass. The contract is:

* **Untracked entries** (``??`` in porcelain v1) — silently dropped. Untracked
  files cannot diverge from HEAD, so they are not a merge concern.
* **Tracked diverging entries** outside of the two expected status files —
  surfaced as a structured error. NO silent suppression.

This test pins both halves of the contract through ``_classify_porcelain_lines``
(the helper that the merge invariant uses) and through a full
``_run_lane_based_merge`` drive-through.
"""

from __future__ import annotations

import contextlib
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import pytest

from specify_cli.cli.commands.merge import (
    _classify_porcelain_lines,
    _run_lane_based_merge,
)
from specify_cli.merge.config import MergeStrategy


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


def _make_manifest(slug: str) -> MagicMock:
    manifest = MagicMock()
    manifest.target_branch = "main"
    manifest.mission_branch = f"kitty/mission-{slug}"
    lane = MagicMock()
    lane.lane_id = "lane-a"
    lane.wp_ids = ["WP01"]
    manifest.lanes = [lane]
    return manifest


class TestClassifyPorcelainLines:
    """Pin the contract on the helper directly."""

    def test_untracked_worktrees_dir_dropped(self):
        lines = ["?? .worktrees/scratch/", "?? tmp.txt"]
        offending, skipped = _classify_porcelain_lines(lines, expected_paths=set())
        assert offending == [], (
            f"Untracked entries must be silently dropped (FR-004), got: {offending!r}"
        )
        assert skipped == 2

    def test_expected_status_files_dropped(self):
        lines = [
            " M kitty-specs/test/status.events.jsonl",
            " M kitty-specs/test/status.json",
        ]
        offending, _ = _classify_porcelain_lines(
            lines,
            expected_paths={
                "kitty-specs/test/status.events.jsonl",
                "kitty-specs/test/status.json",
            },
        )
        assert offending == [], (
            f"The two status files in expected_paths must be allowlisted: {offending!r}"
        )

    def test_tracked_unrelated_modification_is_offending(self):
        """No silent suppression: a tracked change outside the allowlist must surface."""
        lines = [" M src/unexpected_file.py"]
        offending, _ = _classify_porcelain_lines(
            lines,
            expected_paths={"kitty-specs/test/status.events.jsonl"},
        )
        assert offending == [" M src/unexpected_file.py"], (
            "Tracked diverging changes outside expected_paths MUST be reported. "
            "FR-004 forbids silent suppression of operator-supplied tracked changes."
        )

    def test_mixed_untracked_and_tracked(self):
        """Untracked entries are dropped; tracked diverging entries surface."""
        lines = [
            "?? .worktrees/",
            "?? scratch.txt",
            " D src/important.py",  # tracked deletion — must surface
        ]
        offending, skipped = _classify_porcelain_lines(lines, expected_paths=set())
        assert offending == [" D src/important.py"]
        assert skipped == 2


class TestMergeToleratesUntrackedFiles:
    """End-to-end: merge succeeds when only untracked entries are present."""

    def test_merge_succeeds_with_untracked_worktrees_and_tmp(self, tmp_path: Path) -> None:
        slug = "test-untracked-tolerance"
        _init_git_repo(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / slug
        feature_dir.mkdir(parents=True)

        manifest = _make_manifest(slug)

        lane_result = MagicMock()
        lane_result.success = True
        lane_result.errors = []

        mission_result = MagicMock()
        mission_result.success = True
        mission_result.commit = "abc1234"
        mission_result.errors = []

        # Simulate `git status --porcelain` reporting two untracked entries:
        # an untracked .worktrees/ directory and a stray tmp.txt.
        def fake_run_command(cmd, *args, **kwargs):  # noqa: ANN001
            if "merge-base" in cmd:
                return (0, "abc123\n", "")
            if "status" in cmd and "--porcelain" in cmd:
                return (0, "?? .worktrees/scratch/\n?? tmp.txt\n", "")
            return (0, "", "")

        patches = [
            patch("specify_cli.cli.commands.merge.require_lanes_json", return_value=manifest),
            patch("specify_cli.cli.commands.merge.load_state", return_value=None),
            patch("specify_cli.cli.commands.merge.save_state"),
            patch("specify_cli.cli.commands.merge.get_main_repo_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.merge.require_no_sparse_checkout"),
            patch("specify_cli.lanes.merge.merge_lane_to_mission", return_value=lane_result),
            patch("specify_cli.lanes.merge.merge_mission_to_target", return_value=mission_result),
            patch("specify_cli.cli.commands.merge._mark_wp_merged_done"),
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

        with contextlib.ExitStack() as stack:
            mocks = [stack.enter_context(p) for p in patches]
            stale = MagicMock()
            stale.findings = []
            mocks[10].return_value = stale

            gate_eval = MagicMock()
            gate_eval.overall_pass = True
            gate_eval.gates = []
            mocks[11].return_value = gate_eval

            policy = MagicMock()
            policy.merge_gates = []
            mocks[12].return_value = policy

            # No exception: the untracked entries are tolerated.
            _run_lane_based_merge(
                repo_root=tmp_path,
                mission_slug=slug,
                push=False,
                delete_branch=False,
                remove_worktree=False,
                strategy=MergeStrategy.SQUASH,
            )

    def test_merge_aborts_on_unrelated_tracked_change(self, tmp_path: Path) -> None:
        """Operator-supplied tracked changes still cause a clear, structured error."""
        slug = "test-unrelated-tracked"
        _init_git_repo(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / slug
        feature_dir.mkdir(parents=True)

        manifest = _make_manifest(slug)

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
            if "status" in cmd and "--porcelain" in cmd:
                # Mix: untracked tolerated, but a tracked modification is real.
                return (0, "?? .worktrees/\n M src/operator_change.py\n", "")
            return (0, "", "")

        patches = [
            patch("specify_cli.cli.commands.merge.require_lanes_json", return_value=manifest),
            patch("specify_cli.cli.commands.merge.load_state", return_value=None),
            patch("specify_cli.cli.commands.merge.save_state"),
            patch("specify_cli.cli.commands.merge.get_main_repo_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.merge.require_no_sparse_checkout"),
            patch("specify_cli.lanes.merge.merge_lane_to_mission", return_value=lane_result),
            patch("specify_cli.lanes.merge.merge_mission_to_target", return_value=mission_result),
            patch("specify_cli.cli.commands.merge._mark_wp_merged_done"),
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

        with contextlib.ExitStack() as stack:
            mocks = [stack.enter_context(p) for p in patches]
            stale = MagicMock()
            stale.findings = []
            mocks[10].return_value = stale

            gate_eval = MagicMock()
            gate_eval.overall_pass = True
            gate_eval.gates = []
            mocks[11].return_value = gate_eval

            policy = MagicMock()
            policy.merge_gates = []
            mocks[12].return_value = policy

            with pytest.raises(click.exceptions.Exit):
                _run_lane_based_merge(
                    repo_root=tmp_path,
                    mission_slug=slug,
                    push=False,
                    delete_branch=False,
                    remove_worktree=False,
                    strategy=MergeStrategy.SQUASH,
                )
