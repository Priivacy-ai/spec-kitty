"""Lane worktree allocation.

Allocates or reuses worktrees for execution lanes. Each lane gets
exactly one worktree and one branch. Sequential WPs in the same
lane share the worktree — no recreation between WPs.

The mission integration branch is created (if absent) when the
first lane worktree is allocated.

#1348 (WP04): when the mission carries a ``coordination_branch`` field
in ``meta.json`` (new-topology missions, WP03+), the lane branch is
parented on the coordination branch rather than the legacy
``mission_branch`` field, and the lane worktree gets a sparse-checkout
policy registered so it cannot see ``status.events.jsonl`` or
``status.json`` (FR-024 / FR-025 / FR-029).
"""

from __future__ import annotations

from specify_cli.missions.feature_dir_resolver import candidate_feature_dir_for_mission
import json
import subprocess
from pathlib import Path

from specify_cli.coordination import register_lane_sparse_checkout
from specify_cli.lanes.branch_naming import lane_branch_name, mid8
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

    # #1348 (WP04): pick the parent branch.
    #
    #   New-topology missions (meta.json has ``coordination_branch``):
    #     parent the lane on the coordination branch and register the
    #     status-files sparse-checkout exclusion.
    #
    #   Legacy missions (no ``coordination_branch``): fall back to the
    #     ``mission_branch`` field. No sparse-checkout. WP08 will harden
    #     the legacy path further; for now we preserve existing behaviour.
    coordination_branch = _read_coordination_branch(repo_root, mission_slug)

    if coordination_branch is not None:
        _ensure_branch_exists(
            repo_root, coordination_branch, lanes_manifest.target_branch,
        )
        _create_lane_worktree(repo_root, worktree_path, branch, coordination_branch)
        # Register the sparse-checkout policy so the lane filesystem does
        # NOT contain status.events.jsonl / status.json. Only meaningful
        # when we have a mid8; new-topology missions always do because
        # WP03 mints the coord branch only when mission_id is present.
        try:
            short_id = mid8(lanes_manifest.mission_id)
        except ValueError:
            short_id = None
        if short_id is not None:
            register_lane_sparse_checkout(worktree_path, mission_slug, short_id)
        return worktree_path, branch

    # Legacy path: parent on the mission_branch field.
    mission_branch = lanes_manifest.mission_branch
    _ensure_mission_branch(repo_root, mission_branch, lanes_manifest.target_branch)
    _create_lane_worktree(repo_root, worktree_path, branch, mission_branch)

    return worktree_path, branch


def _read_coordination_branch(
    repo_root: Path, mission_slug: str,
) -> str | None:
    """Return the ``coordination_branch`` field from ``meta.json``.

    Returns ``None`` for legacy missions (no field, or no meta.json).

    The meta.json is in the main checkout under
    ``kitty-specs/<mission_slug>/meta.json`` — the same place WP03's
    mission_create writes it.
    """
    meta_path = candidate_feature_dir_for_mission(repo_root, mission_slug) / "meta.json"
    if not meta_path.exists():
        return None
    try:
        data = json.loads(meta_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    value = data.get("coordination_branch")
    if isinstance(value, str) and value:
        return value
    return None


def _ensure_branch_exists(
    repo_root: Path, branch: str, fallback_parent: str,
) -> None:
    """Create ``branch`` from ``fallback_parent`` if it does not exist.

    Used for the coordination-branch path: WP03 normally creates the
    coordination branch at ``mission create`` time, but legacy
    upgrade-in-place projects may still hit this code path with the
    branch missing. We defensively recreate from the target branch
    rather than crashing.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/heads/{branch}"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return
    result = subprocess.run(
        ["git", "branch", branch, fallback_parent],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to create branch {branch} from {fallback_parent}: "
            f"{result.stderr.strip()}"
        )


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
