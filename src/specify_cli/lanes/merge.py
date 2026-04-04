"""Lane-based merge operations.

Two-tier merge flow:
1. Lane → Mission: merge a lane branch into the mission integration branch.
2. Mission → Target: merge the mission branch into the target (e.g. main).

Both operations use temporary merge workspaces and the stale-lane
blocker to prevent overlapping file conflicts.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from specify_cli.lanes.branch_naming import lane_branch_name
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import read_lanes_json
from specify_cli.lanes.stale_check import StaleCheckResult, check_lane_staleness


@dataclass
class LaneMergeResult:
    """Outcome of a lane merge operation."""

    success: bool
    lane_id: str
    merged_into: str
    errors: list[str] = field(default_factory=list)
    stale_check: StaleCheckResult | None = None


@dataclass
class MissionMergeResult:
    """Outcome of a mission-to-target merge."""

    success: bool
    mission_branch: str
    target_branch: str
    commit: str | None = None
    errors: list[str] = field(default_factory=list)


def merge_lane_to_mission(
    repo_root: Path,
    feature_slug: str,
    lane_id: str,
    lanes_manifest: LanesManifest | None = None,
) -> LaneMergeResult:
    """Merge a lane branch into the mission integration branch.

    Performs stale-lane check before merging. If the lane is stale
    (overlapping files changed in mission), the merge is blocked.

    Args:
        repo_root: Repository root.
        feature_slug: Feature slug.
        lane_id: Lane to merge (e.g., "lane-a").
        lanes_manifest: Pre-loaded manifest (loaded from disk if None).

    Returns:
        LaneMergeResult with success/error status.
    """
    if lanes_manifest is None:
        feature_dir = repo_root / "kitty-specs" / feature_slug
        lanes_manifest = read_lanes_json(feature_dir)
        if lanes_manifest is None:
            return LaneMergeResult(
                success=False, lane_id=lane_id, merged_into="",
                errors=["No lanes.json found for this feature"],
            )

    # Find the lane.
    lane = None
    for candidate in lanes_manifest.lanes:
        if candidate.lane_id == lane_id:
            lane = candidate
            break
    if lane is None:
        return LaneMergeResult(
            success=False, lane_id=lane_id, merged_into="",
            errors=[f"Lane {lane_id} not found in lanes.json"],
        )

    branch = lane_branch_name(feature_slug, lane_id)
    mission_branch = lanes_manifest.mission_branch

    # Verify the lane branch exists.
    if not _branch_exists(repo_root, branch):
        return LaneMergeResult(
            success=False, lane_id=lane_id, merged_into=mission_branch,
            errors=[f"Lane branch {branch} does not exist"],
        )

    # Stale-lane check.
    stale = check_lane_staleness(lane, branch, mission_branch, repo_root)
    if stale.is_stale:
        return LaneMergeResult(
            success=False, lane_id=lane_id, merged_into=mission_branch,
            errors=[
                f"Lane {lane_id} is stale: overlapping files {stale.stale_files}. "
                f"{stale.remediation}"
            ],
            stale_check=stale,
        )

    # Merge lane branch into mission branch.
    # We checkout the mission branch in a temporary worktree, merge, then clean up.
    try:
        _merge_branch_into(repo_root, branch, mission_branch)
    except RuntimeError as e:
        return LaneMergeResult(
            success=False, lane_id=lane_id, merged_into=mission_branch,
            errors=[str(e)],
        )

    return LaneMergeResult(
        success=True, lane_id=lane_id, merged_into=mission_branch,
    )


def merge_mission_to_target(
    repo_root: Path,
    feature_slug: str,
    lanes_manifest: LanesManifest | None = None,
) -> MissionMergeResult:
    """Merge the mission integration branch into the target branch (e.g., main).

    This is the final step: only the mission branch may merge to main.

    Args:
        repo_root: Repository root.
        feature_slug: Feature slug.
        lanes_manifest: Pre-loaded manifest (loaded from disk if None).

    Returns:
        MissionMergeResult with success/error status.
    """
    if lanes_manifest is None:
        feature_dir = repo_root / "kitty-specs" / feature_slug
        lanes_manifest = read_lanes_json(feature_dir)
        if lanes_manifest is None:
            return MissionMergeResult(
                success=False, mission_branch="", target_branch="",
                errors=["No lanes.json found for this feature"],
            )

    mission_branch = lanes_manifest.mission_branch
    target_branch = lanes_manifest.target_branch

    if not _branch_exists(repo_root, mission_branch):
        return MissionMergeResult(
            success=False, mission_branch=mission_branch,
            target_branch=target_branch,
            errors=[f"Mission branch {mission_branch} does not exist"],
        )

    try:
        _merge_branch_into(repo_root, mission_branch, target_branch)
    except RuntimeError as e:
        return MissionMergeResult(
            success=False, mission_branch=mission_branch,
            target_branch=target_branch, errors=[str(e)],
        )

    # Get the merge commit.
    commit = _rev_parse(repo_root, target_branch)

    return MissionMergeResult(
        success=True, mission_branch=mission_branch,
        target_branch=target_branch, commit=commit,
    )


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _branch_exists(repo_root: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/heads/{branch}"],
        cwd=str(repo_root), capture_output=True, text=True,
    )
    return result.returncode == 0


def _rev_parse(repo_root: Path, ref: str) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", ref],
        cwd=str(repo_root), capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _merge_branch_into(
    repo_root: Path, source_branch: str, target_branch: str,
) -> None:
    """Merge source_branch into target_branch using a temporary worktree.

    Creates a detached worktree at the target branch tip, merges source
    into it, then fast-forwards the target branch ref to the result.
    The main repo's checkout is never changed.

    Uses --detach to avoid "branch already checked out" errors when
    target_branch is the currently checked-out branch.

    Raises RuntimeError on merge failure (including conflicts).
    """
    import tempfile

    tmp_dir = tempfile.mkdtemp(prefix="kitty-merge-")
    tmp_path = Path(tmp_dir)

    try:
        # Create detached worktree at target branch tip.
        result = subprocess.run(
            ["git", "worktree", "add", "--detach", str(tmp_path), target_branch],
            cwd=str(repo_root), capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to create merge worktree: {result.stderr.strip()}"
            )

        # Merge source into the detached HEAD.
        result = subprocess.run(
            ["git", "merge", source_branch, "--no-edit",
             "-m", f"Merge {source_branch} into {target_branch}"],
            cwd=str(tmp_path), capture_output=True, text=True,
        )
        if result.returncode != 0:
            subprocess.run(
                ["git", "merge", "--abort"],
                cwd=str(tmp_path), capture_output=True,
            )
            raise RuntimeError(
                f"Merge of {source_branch} into {target_branch} failed: "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )

        # Get the resulting commit SHA.
        merge_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(tmp_path), capture_output=True, text=True, check=True,
        ).stdout.strip()

        # Update the target branch ref to point to the merge commit.
        result = subprocess.run(
            ["git", "update-ref", f"refs/heads/{target_branch}", merge_commit],
            cwd=str(repo_root), capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to update {target_branch} ref: {result.stderr.strip()}"
            )
    finally:
        subprocess.run(
            ["git", "worktree", "remove", str(tmp_path), "--force"],
            cwd=str(repo_root), capture_output=True,
        )
