"""WP05/T006/T007 — post-merge refresh and invariant assertion.

FR-013: After a successful mission→target merge, the primary checkout must be
refreshed against HEAD so any paths git left out (e.g. legacy sparse-checkout)
are restored before the housekeeping commit runs.

FR-014: After the refresh, ``git status --porcelain`` in the primary checkout
MUST report at most the status files that the immediately-following
``safe_commit`` is about to persist. Any other divergence is an invariant
violation and must raise a merge-specific error.

These tests drive ``_run_lane_based_merge_locked`` indirectly through
``_run_lane_based_merge`` with the heavy merge helpers patched out, so we can
verify the two git subprocess calls (``git checkout HEAD -- .`` and
``git status --porcelain``) fire between ``merge_mission_to_target`` and
``safe_commit``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.cli.commands.merge import _run_lane_based_merge
from specify_cli.merge.config import MergeStrategy


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


class TestPostMergeRefreshAndInvariant:
    def _make_manifest(self, slug: str) -> MagicMock:
        manifest = MagicMock()
        manifest.target_branch = "main"
        manifest.mission_branch = f"kitty/mission-{slug}"
        lane_a = MagicMock()
        lane_a.lane_id = "lane-a"
        lane_a.wp_ids = ["WP01"]
        manifest.lanes = [lane_a]
        return manifest

    def test_refresh_and_invariant_run_in_correct_order(self, tmp_path: Path) -> None:
        """FR-013/FR-014: refresh happens before done events, then status check, then safe_commit."""
        slug = "test-refresh-invariant"
        _init_git_repo(tmp_path)

        feature_dir = tmp_path / "kitty-specs" / slug
        feature_dir.mkdir(parents=True)

        manifest = self._make_manifest(slug)

        lane_result = MagicMock()
        lane_result.success = True
        lane_result.errors = []

        mission_result = MagicMock()
        mission_result.success = True
        mission_result.commit = "abc1234"
        mission_result.errors = []

        call_log: list[str] = []
        ordered_calls: list[tuple[str, tuple[object, ...]]] = []

        def fake_run_command(cmd, *args, **kwargs):  # noqa: ANN001
            ordered_calls.append(("run_command", tuple(cmd)))
            if "checkout" in cmd and "HEAD" in cmd:
                call_log.append("checkout_refresh")
                return (0, "", "")
            if "status" in cmd and "--porcelain" in cmd:
                call_log.append("status_check")
                # Clean working tree — no offending lines.
                return (0, "", "")
            if "merge-base" in cmd:
                return (0, "abc123\n", "")
            return (0, "", "")

        def fake_safe_commit(**kwargs):  # noqa: ANN001
            call_log.append("safe_commit")
            return True

        def fake_mark_wp_merged_done(*args, **kwargs):  # noqa: ANN001
            call_log.append("mark_done")

        with (
            patch("specify_cli.cli.commands.merge.require_lanes_json", return_value=manifest),
            patch("specify_cli.cli.commands.merge.load_state", return_value=None),
            patch("specify_cli.cli.commands.merge.save_state"),
            patch("specify_cli.cli.commands.merge.get_main_repo_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.merge.require_no_sparse_checkout"),
            patch("specify_cli.status.lane_reader.get_wp_lane", return_value="done"),
            patch("specify_cli.lanes.merge.merge_lane_to_mission", return_value=lane_result),
            patch("specify_cli.lanes.merge.merge_mission_to_target", return_value=mission_result),
            patch("specify_cli.cli.commands.merge._mark_wp_merged_done", side_effect=fake_mark_wp_merged_done),
            patch("specify_cli.cli.commands.merge.safe_commit", side_effect=fake_safe_commit),
            patch("specify_cli.post_merge.stale_assertions.run_check") as mock_run_check,
            patch("specify_cli.policy.merge_gates.evaluate_merge_gates") as mock_gates,
            patch("specify_cli.policy.config.load_policy_config") as mock_policy,
            patch("specify_cli.cli.commands.merge.run_command", side_effect=fake_run_command),
            patch("specify_cli.cli.commands.merge.has_remote", return_value=False),
            patch("specify_cli.cli.commands.merge.cleanup_merge_workspace"),
            patch("specify_cli.cli.commands.merge.clear_state"),
            patch("specify_cli.merge.state.MergeState"),
            patch("specify_cli.cli.commands.merge._bake_mission_number_into_mission_branch"),
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
                mission_slug=slug,
                push=False,
                delete_branch=False,
                remove_worktree=False,
                strategy=MergeStrategy.SQUASH,
            )

        # Required ordering: checkout_refresh → mark_done → status_check → safe_commit.
        assert "checkout_refresh" in call_log, (
            f"FR-013: post-merge `git checkout HEAD -- .` must fire; call_log={call_log}"
        )
        assert "mark_done" in call_log, "Merged WPs must be recorded as done after refresh"
        assert "status_check" in call_log, (
            f"FR-014: post-merge `git status --porcelain` must fire; call_log={call_log}"
        )
        assert "safe_commit" in call_log, "safe_commit must still fire after refresh/invariant"

        refresh_idx = call_log.index("checkout_refresh")
        mark_done_idx = call_log.index("mark_done")
        status_idx = call_log.index("status_check")
        commit_idx = call_log.index("safe_commit")
        assert refresh_idx < mark_done_idx < status_idx < commit_idx, (
            f"Expected refresh → mark_done → status → safe_commit, got {call_log}"
        )

    def test_invariant_violation_aborts_before_safe_commit(self, tmp_path: Path) -> None:
        """FR-014: an unexpected diverging path aborts the merge before safe_commit."""
        slug = "test-invariant-violation"
        _init_git_repo(tmp_path)

        feature_dir = tmp_path / "kitty-specs" / slug
        feature_dir.mkdir(parents=True)

        manifest = self._make_manifest(slug)

        lane_result = MagicMock()
        lane_result.success = True
        lane_result.errors = []

        mission_result = MagicMock()
        mission_result.success = True
        mission_result.commit = "abc1234"
        mission_result.errors = []

        call_log: list[str] = []

        def fake_run_command(cmd, *args, **kwargs):  # noqa: ANN001
            if "checkout" in cmd and "HEAD" in cmd:
                call_log.append("checkout_refresh")
                return (0, "", "")
            if "status" in cmd and "--porcelain" in cmd:
                call_log.append("status_check")
                # Simulate an offending diverging path that is NOT one of the
                # two expected status files. This must trigger the invariant.
                return (0, " M src/unexpected_file.py\n", "")
            if "merge-base" in cmd:
                return (0, "abc123\n", "")
            return (0, "", "")

        def fake_safe_commit(**kwargs):  # noqa: ANN001
            call_log.append("safe_commit")
            return True

        import click

        with (
            patch("specify_cli.cli.commands.merge.require_lanes_json", return_value=manifest),
            patch("specify_cli.cli.commands.merge.load_state", return_value=None),
            patch("specify_cli.cli.commands.merge.save_state"),
            patch("specify_cli.cli.commands.merge.get_main_repo_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.merge.require_no_sparse_checkout"),
            patch("specify_cli.status.lane_reader.get_wp_lane", return_value="done"),
            patch("specify_cli.lanes.merge.merge_lane_to_mission", return_value=lane_result),
            patch("specify_cli.lanes.merge.merge_mission_to_target", return_value=mission_result),
            patch("specify_cli.cli.commands.merge._mark_wp_merged_done"),
            patch("specify_cli.cli.commands.merge.safe_commit", side_effect=fake_safe_commit),
            patch("specify_cli.post_merge.stale_assertions.run_check") as mock_run_check,
            patch("specify_cli.policy.merge_gates.evaluate_merge_gates") as mock_gates,
            patch("specify_cli.policy.config.load_policy_config") as mock_policy,
            patch("specify_cli.cli.commands.merge.run_command", side_effect=fake_run_command),
            patch("specify_cli.cli.commands.merge.has_remote", return_value=False),
            patch("specify_cli.cli.commands.merge.cleanup_merge_workspace"),
            patch("specify_cli.cli.commands.merge.clear_state"),
            patch("specify_cli.merge.state.MergeState"),
            patch("specify_cli.cli.commands.merge._bake_mission_number_into_mission_branch"),
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

            with pytest.raises(click.exceptions.Exit):
                _run_lane_based_merge(
                    repo_root=tmp_path,
                    mission_slug=slug,
                    push=False,
                    delete_branch=False,
                    remove_worktree=False,
                    strategy=MergeStrategy.SQUASH,
                )

        assert "status_check" in call_log, "status check must have run"
        assert "safe_commit" not in call_log, (
            "FR-014: safe_commit must NOT fire when invariant is violated; "
            f"call_log={call_log}"
        )
