"""Lane worktree allocation.

Allocates or reuses worktrees for execution lanes. Each lane gets
exactly one worktree and one branch. Sequential WPs in the same
lane share the worktree — no recreation between WPs.

The mission integration branch is created (if absent) when the
first lane worktree is allocated.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from specify_cli.lanes.branch_naming import lane_branch_name, mission_branch_name
from specify_cli.lanes.models import LanesManifest


class DirtyWorktreeError(Exception):
    """Raised when a lane worktree has uncommitted changes during handoff."""


class LaneNotFoundError(Exception):
    """Raised when a WP is not assigned to any lane."""


def allocate_lane_worktree(
    repo_root: Path,
    mission_slug: str,
    wp_id: str,
    lanes_manifest: LanesManifest,
) -> tuple[Path, str]:
    """Allocate or reuse the worktree for the lane containing wp_id.

    Returns (worktree_path, branch_name).

    If the lane worktree already exists (from a prior WP in the same lane),
    validates it is clean and returns the existing path.

    If the lane worktree does not exist, creates the mission branch (if
    needed) and then creates the lane worktree branching from it.

    Args:
        repo_root: Absolute path to the main repository.
        mission_slug: Feature slug for branch naming.
        wp_id: Work package ID to allocate a worktree for.
        lanes_manifest: The computed lanes manifest.

    Returns:
        Tuple of (worktree_path, branch_name).

    Raises:
        LaneNotFoundError: If wp_id is not in any lane.
        DirtyWorktreeError: If reusing a worktree that has uncommitted changes.
        RuntimeError: If git operations fail.
    """
    lane = lanes_manifest.lane_for_wp(wp_id)
    if lane is None:
        raise LaneNotFoundError(
            f"{wp_id} is not assigned to any execution lane in lanes.json"
        )

    branch = lane_branch_name(mission_slug, lane.lane_id)
    worktree_path = repo_root / ".worktrees" / f"{mission_slug}-{lane.lane_id}"

    if worktree_path.exists():
        # Reuse existing lane worktree — validate it is clean first.
        _validate_worktree_clean(worktree_path, lane.lane_id)
        return worktree_path, branch

    # Ensure mission branch exists before creating lane worktree.
    mission_branch = lanes_manifest.mission_branch
    _ensure_mission_branch(repo_root, mission_branch, lanes_manifest.target_branch)

    # Create the lane worktree branching from the mission branch.
    _create_lane_worktree(repo_root, worktree_path, branch, mission_branch)

    return worktree_path, branch


def _validate_worktree_clean(worktree_path: Path, lane_id: str) -> None:
    """Fail if the worktree has uncommitted changes.

    This prevents a WP from inheriting dirty state from a prior WP
    in the same lane.
    """
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(worktree_path),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git status failed in {worktree_path}: {result.stderr.strip()}"
        )
    if result.stdout.strip():
        raise DirtyWorktreeError(
            f"Lane {lane_id} worktree at {worktree_path} has uncommitted changes. "
            f"Commit or stash before starting the next WP."
        )


def _ensure_mission_branch(
    repo_root: Path, mission_branch: str, target_branch: str,
) -> None:
    """Create the mission integration branch if it doesn't exist.

    The mission branch is created from the target branch (e.g., main).
    It is a regular branch, not backed by a worktree.
    """
    # Check if branch already exists.
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/heads/{mission_branch}"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return  # Already exists.

    # Create from target branch.
    result = subprocess.run(
        ["git", "branch", mission_branch, target_branch],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to create mission branch {mission_branch} from {target_branch}: "
            f"{result.stderr.strip()}"
        )


def _create_lane_worktree(
    repo_root: Path, worktree_path: Path, branch: str, base_branch: str,
) -> None:
    """Create a git worktree for a lane branch."""
    worktree_path.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(worktree_path), base_branch],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to create lane worktree at {worktree_path}: "
            f"{result.stderr.strip()}"
        )


def _recover_lane_worktree(
    repo_root: Path, worktree_path: Path, existing_branch: str,
) -> None:
    """Recreate worktree from existing branch (recovery mode).

    Uses ``git worktree add <path> <branch>`` WITHOUT ``-b`` to attach
    to an already-existing branch. This is the recovery path for when
    the agent process crashed and the branch survived but the worktree
    was lost.

    Raises:
        RuntimeError: If the git worktree add command fails.
    """
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "worktree", "add", str(worktree_path), existing_branch],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to recover worktree at {worktree_path}: "
            f"{result.stderr.strip()}"
        )
