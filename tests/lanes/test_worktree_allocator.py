"""Tests for lane worktree allocator.

These tests use real git repos (not mocks) since the allocator
exercises git worktree and branch operations.
"""

import subprocess

import pytest

from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.worktree_allocator import (
    DirtyWorktreeError,
    LaneNotFoundError,
    allocate_lane_worktree,
)

pytestmark = pytest.mark.git_repo


def _make_git_repo(path):
    """Create a minimal git repo with an initial commit."""
    subprocess.run(["git", "init", str(path)], capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(path),
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(path),
        capture_output=True,
        check=True,
    )
    (path / "README.md").write_text("init\n")
    subprocess.run(["git", "add", "."], cwd=str(path), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(path),
        capture_output=True,
        check=True,
    )


def _make_manifest(mission_slug="010-feat", target_branch="main"):
    return LanesManifest(
        version=1,
        mission_slug=mission_slug,
        mission_id=mission_slug,
        mission_branch=f"kitty/mission-{mission_slug}",
        target_branch=target_branch,
        lanes=[
            ExecutionLane(
                lane_id="lane-a",
                wp_ids=("WP01", "WP02"),
                write_scope=("src/**",),
                predicted_surfaces=(),
                depends_on_lanes=(),
                parallel_group=0,
            ),
            ExecutionLane(
                lane_id="lane-b",
                wp_ids=("WP03",),
                write_scope=("tests/**",),
                predicted_surfaces=(),
                depends_on_lanes=(),
                parallel_group=0,
            ),
        ],
        computed_at="2026-04-03T12:00:00+00:00",
        computed_from="test",
    )


class TestAllocateLaneWorktree:
    def test_creates_mission_branch_and_lane_worktree(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        # Rename default branch to "main" for consistency
        subprocess.run(
            ["git", "branch", "-M", "main"],
            cwd=str(repo),
            capture_output=True,
            check=True,
        )

        manifest = _make_manifest()
        wt_path, branch = allocate_lane_worktree(repo, "010-feat", "WP01", manifest)

        assert wt_path == repo / ".worktrees" / "010-feat-lane-a"
        assert wt_path.exists()
        assert branch == "kitty/mission-010-feat-lane-a"

        # Mission branch should also exist
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "refs/heads/kitty/mission-010-feat"],
            cwd=str(repo),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_reuses_existing_clean_worktree(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        subprocess.run(
            ["git", "branch", "-M", "main"],
            cwd=str(repo),
            capture_output=True,
            check=True,
        )

        manifest = _make_manifest()

        # First WP creates the worktree
        wt_path1, branch1 = allocate_lane_worktree(repo, "010-feat", "WP01", manifest)

        # Second WP in same lane reuses it
        wt_path2, branch2 = allocate_lane_worktree(repo, "010-feat", "WP02", manifest)

        assert wt_path1 == wt_path2
        assert branch1 == branch2

    def test_rejects_dirty_worktree(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        subprocess.run(
            ["git", "branch", "-M", "main"],
            cwd=str(repo),
            capture_output=True,
            check=True,
        )

        manifest = _make_manifest()
        wt_path, _ = allocate_lane_worktree(repo, "010-feat", "WP01", manifest)

        # Dirty the worktree
        (wt_path / "dirty.txt").write_text("uncommitted\n")

        with pytest.raises(DirtyWorktreeError, match="uncommitted changes"):
            allocate_lane_worktree(repo, "010-feat", "WP02", manifest)

    def test_different_lanes_get_different_worktrees(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        subprocess.run(
            ["git", "branch", "-M", "main"],
            cwd=str(repo),
            capture_output=True,
            check=True,
        )

        manifest = _make_manifest()

        wt_a, branch_a = allocate_lane_worktree(repo, "010-feat", "WP01", manifest)
        wt_b, branch_b = allocate_lane_worktree(repo, "010-feat", "WP03", manifest)

        assert wt_a != wt_b
        assert branch_a != branch_b
        assert "lane-a" in str(wt_a)
        assert "lane-b" in str(wt_b)

    def test_wp_not_in_any_lane_raises(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)

        manifest = _make_manifest()

        with pytest.raises(LaneNotFoundError, match="WP99"):
            allocate_lane_worktree(repo, "010-feat", "WP99", manifest)

    def test_mission_branch_not_recreated(self, tmp_path):
        """Mission branch is created once, not on every lane allocation."""
        repo = tmp_path / "repo"
        repo.mkdir()
        _make_git_repo(repo)
        subprocess.run(
            ["git", "branch", "-M", "main"],
            cwd=str(repo),
            capture_output=True,
            check=True,
        )

        manifest = _make_manifest()

        # First lane creates mission branch
        allocate_lane_worktree(repo, "010-feat", "WP01", manifest)

        # Get mission branch commit
        result1 = subprocess.run(
            ["git", "rev-parse", "kitty/mission-010-feat"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            check=True,
        )

        # Second lane should NOT recreate it
        allocate_lane_worktree(repo, "010-feat", "WP03", manifest)

        result2 = subprocess.run(
            ["git", "rev-parse", "kitty/mission-010-feat"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            check=True,
        )

        assert result1.stdout.strip() == result2.stdout.strip()
