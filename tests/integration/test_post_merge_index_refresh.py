"""WP01/T003 — post-merge index refresh (FR-003).

After the post-merge ``git checkout HEAD -- .`` reconciles working-tree
content with HEAD, the cached stat info in the git index can still trail real
on-disk state. The fix calls ``git update-index --refresh`` to reconcile the
index stats with the working tree without touching any blobs.

This test pins:

1. The merge flow invokes ``git update-index --refresh`` between the
   working-tree refresh and the per-WP done-recording pass.
2. A non-zero return from refresh does NOT abort the merge (informational
   only — refresh divergence is expected, e.g. when the two status files
   are about to be safe_commit'd).
"""

from __future__ import annotations

import contextlib
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.cli.commands.merge import _run_lane_based_merge
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


def _drive_merge(tmp_path: Path, slug: str, *, refresh_returncode: int = 0):
    manifest = _make_manifest(slug)
    feature_dir = tmp_path / "kitty-specs" / slug
    feature_dir.mkdir(parents=True, exist_ok=True)

    lane_result = MagicMock()
    lane_result.success = True
    lane_result.errors = []

    mission_result = MagicMock()
    mission_result.success = True
    mission_result.commit = "abc1234"
    mission_result.errors = []

    call_log: list[tuple[str, ...]] = []

    def fake_run_command(cmd, *args, **kwargs):  # noqa: ANN001
        call_log.append(tuple(cmd))
        if "merge-base" in cmd:
            return (0, "abc123\n", "")
        if "update-index" in cmd and "--refresh" in cmd:
            # Allow caller to simulate divergence via non-zero return.
            return (refresh_returncode, "", "stat info differs")
        if "status" in cmd and "--porcelain" in cmd:
            return (0, "", "")
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

        _run_lane_based_merge(
            repo_root=tmp_path,
            mission_slug=slug,
            push=False,
            delete_branch=False,
            remove_worktree=False,
            strategy=MergeStrategy.SQUASH,
        )

    return call_log


class TestPostMergeIndexRefresh:
    def test_merge_invokes_update_index_refresh(self, tmp_path: Path) -> None:
        slug = "test-index-refresh"
        _init_git_repo(tmp_path)
        call_log = _drive_merge(tmp_path, slug)

        refresh_calls = [c for c in call_log if c[:2] == ("git", "update-index") or "update-index" in c]
        assert refresh_calls, (
            "FR-003 regression: merge did not invoke `git update-index --refresh`. "
            "After post-merge `git checkout HEAD -- .`, the index stat cache must "
            "be reconciled against the working tree to prevent phantom deletions."
        )

        # The exact command shape we expect.
        assert any(
            "update-index" in c and "--refresh" in c for c in call_log
        ), f"Did not see `git update-index --refresh`: {call_log!r}"

    def test_refresh_runs_after_checkout_before_status_check(self, tmp_path: Path) -> None:
        """Order matters: the refresh must run AFTER `checkout HEAD -- .` and
        BEFORE the post-merge `git status --porcelain` invariant check, so
        the invariant assertion sees a clean stat-cache."""
        slug = "test-index-refresh-order"
        _init_git_repo(tmp_path)
        call_log = _drive_merge(tmp_path, slug)

        def _idx(predicate):
            for i, cmd in enumerate(call_log):
                if predicate(cmd):
                    return i
            return -1

        checkout_idx = _idx(lambda cmd: "checkout" in cmd and "HEAD" in cmd and "--" in cmd)
        refresh_idx = _idx(lambda cmd: "update-index" in cmd and "--refresh" in cmd)
        status_idx = _idx(lambda cmd: "status" in cmd and "--porcelain" in cmd)

        assert checkout_idx >= 0 and refresh_idx >= 0 and status_idx >= 0, (
            f"Missing one of checkout/refresh/status in call log: {call_log!r}"
        )
        assert checkout_idx < refresh_idx < status_idx, (
            f"Wrong order: checkout={checkout_idx}, refresh={refresh_idx}, "
            f"status={status_idx}. Expected checkout < refresh < status. "
            f"Full log: {call_log!r}"
        )

    def test_nonzero_refresh_does_not_abort_merge(self, tmp_path: Path) -> None:
        """A non-zero return from `git update-index --refresh` is informational
        only (it indicates the working tree differs from the index, which is
        expected when status files are about to be committed). The merge
        must NOT raise on this."""
        slug = "test-refresh-tolerates-divergence"
        _init_git_repo(tmp_path)
        # refresh_returncode=1 simulates "stat info differs" — must not raise.
        call_log = _drive_merge(tmp_path, slug, refresh_returncode=1)
        # safe_commit should still have been wired (proxy: status check ran).
        assert any("status" in c and "--porcelain" in c for c in call_log), (
            "Merge aborted before reaching the post-merge invariant check, "
            "indicating that a divergent `update-index --refresh` was treated "
            "as fatal. FR-003 requires it to be informational."
        )
