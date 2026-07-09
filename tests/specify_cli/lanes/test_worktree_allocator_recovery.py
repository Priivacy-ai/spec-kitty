"""#2512: crash-recovery path for allocate_lane_worktree.

When an agent process is killed mid-session the lane worktree directory may
be lost (e.g. macOS idle-sleep), but the lane branch survives in the git
object store.  A subsequent ``allocate_lane_worktree`` call must re-attach to
the existing branch (``git worktree add <path> <branch>``) rather than
trying to create a new one (``git worktree add -b <branch>``), which would
fail with "branch already exists".

Prior to this fix the allocator took the creation path unconditionally when
the worktree directory was absent, producing a ``RuntimeError`` that surfaced
to the orchestrator as ``LANE_ALLOCATION_FAILED`` with no actionable reason.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.worktree_allocator import allocate_lane_worktree

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

MISSION_SLUG = "review-context-depth-01KX2EQ9"
MISSION_BRANCH = f"kitty/mission-{MISSION_SLUG}"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _make_manifest(*, lane_id: str = "lane-1", wp_id: str = "WP03") -> LanesManifest:
    return LanesManifest(
        version=1,
        mission_slug=MISSION_SLUG,
        mission_id=None,
        mission_branch=MISSION_BRANCH,
        target_branch="main",
        lanes=[ExecutionLane(
            lane_id=lane_id,
            wp_ids=(wp_id,),
            write_scope=(),
            predicted_surfaces=(),
            depends_on_lanes=(),
            parallel_group=0,
        )],
        computed_at=datetime.now(UTC).isoformat(),
        computed_from="test",
    )


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Minimal git repo with an initial commit."""
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "README.md").write_text("# test\n")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-m", "init")
    return tmp_path


def _first_allocation(repo: Path, manifest: LanesManifest) -> tuple[Path, str]:
    """Simulate the first (fresh) allocation — creates branch + worktree."""
    return allocate_lane_worktree(
        repo_root=repo,
        mission_slug=MISSION_SLUG,
        wp_id=manifest.lanes[0].wp_ids[0],
        lanes_manifest=manifest,
    )


def test_fresh_allocation_creates_worktree(git_repo: Path) -> None:
    """Baseline: first allocation creates the worktree and returns its path."""
    manifest = _make_manifest()
    worktree_path, branch = _first_allocation(git_repo, manifest)
    assert worktree_path.exists()
    assert "lane-1" in str(worktree_path)


def test_crash_recovery_reattaches_when_worktree_gone(git_repo: Path) -> None:
    """#2512: allocator re-attaches when branch exists but worktree directory is gone.

    Sequence:
    1. First allocation creates branch + worktree.
    2. Worktree directory is deleted (simulates OS kill/sleep).
    3. ``allocate_lane_worktree`` is called again — must succeed, returning
       the same path (re-created via ``git worktree add <path> <branch>``).
    """
    manifest = _make_manifest()
    worktree_path, branch = _first_allocation(git_repo, manifest)

    # Simulate the directory being lost (OS kill during sleep, manual rm, etc.).
    import shutil
    shutil.rmtree(worktree_path)
    assert not worktree_path.exists(), "pre-condition: worktree gone"

    # Recovery allocation must succeed — not raise RuntimeError.
    recovered_path, recovered_branch = allocate_lane_worktree(
        repo_root=git_repo,
        mission_slug=MISSION_SLUG,
        wp_id="WP03",
        lanes_manifest=manifest,
    )
    assert recovered_path == worktree_path
    assert recovered_branch == branch
    assert recovered_path.exists(), "worktree directory must be re-created"


def test_crash_recovery_worktree_is_clean_after_reattach(git_repo: Path) -> None:
    """Recovered worktree is clean — the branch tip has no uncommitted changes."""
    manifest = _make_manifest()
    worktree_path, _ = _first_allocation(git_repo, manifest)

    # Add a commit in the worktree so the branch has work.
    (worktree_path / "work.txt").write_text("done\n")
    _git(worktree_path, "add", "work.txt")
    _git(worktree_path, "commit", "-m", "wip work")

    import shutil
    shutil.rmtree(worktree_path)

    recovered_path, _ = allocate_lane_worktree(
        repo_root=git_repo,
        mission_slug=MISSION_SLUG,
        wp_id="WP03",
        lanes_manifest=manifest,
    )
    # work.txt must be present (from the committed state of the branch).
    assert (recovered_path / "work.txt").exists()


def test_reuse_path_still_works_when_worktree_exists(git_repo: Path) -> None:
    """Reuse path is unchanged: existing clean worktree is returned directly."""
    manifest = _make_manifest()
    worktree_path, branch = _first_allocation(git_repo, manifest)

    # Second call with directory intact → reuse path.
    reused_path, reused_branch = allocate_lane_worktree(
        repo_root=git_repo,
        mission_slug=MISSION_SLUG,
        wp_id="WP03",
        lanes_manifest=manifest,
    )
    assert reused_path == worktree_path
    assert reused_branch == branch
