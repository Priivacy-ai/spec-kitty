"""Lane-based merge operations.

Two-tier merge flow:
1. Lane → Mission: merge a lane branch into the mission integration branch.
2. Mission → Target: merge the mission branch into the target (e.g. main).

Both operations use temporary merge workspaces and the stale-lane
blocker to prevent overlapping file conflicts.

Strategy note (FR-006, FR-007):
- Lane→mission always uses merge commits (no-ff) regardless of strategy.
- Mission→target honors the ``strategy`` parameter (default: SQUASH).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from specify_cli.lanes.branch_naming import lane_branch_name
from specify_cli.lanes.models import LanesManifest
from specify_cli.lanes.persistence import read_lanes_json
from specify_cli.lanes.stale_check import StaleCheckResult, check_lane_staleness
from specify_cli.merge.config import MergeStrategy


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
    mission_slug: str,
    lane_id: str,
    lanes_manifest: LanesManifest | None = None,
) -> LaneMergeResult:
    """Merge a lane branch into the mission integration branch.

    Performs stale-lane check before merging. If the lane is stale
    (overlapping files changed in mission), the merge is blocked.

    Args:
        repo_root: Repository root.
        mission_slug: Feature slug.
        lane_id: Lane to merge (e.g., "lane-a").
        lanes_manifest: Pre-loaded manifest (loaded from disk if None).

    Returns:
        LaneMergeResult with success/error status.
    """
    if lanes_manifest is None:
        feature_dir = repo_root / "kitty-specs" / mission_slug
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

    branch = lane_branch_name(mission_slug, lane_id)
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
    mission_slug: str,
    lanes_manifest: LanesManifest | None = None,
    *,
    strategy: MergeStrategy = MergeStrategy.SQUASH,
) -> MissionMergeResult:
    """Merge the mission integration branch into the target branch (e.g., main).

    This is the final step: only the mission branch may merge to main.

    Args:
        repo_root: Repository root.
        mission_slug: Feature slug.
        lanes_manifest: Pre-loaded manifest (loaded from disk if None).
        strategy: Merge strategy for the mission→target step (FR-006/T010).
            Defaults to SQUASH. Lane→mission is NOT affected by this parameter.

    Returns:
        MissionMergeResult with success/error status.
    """
    if lanes_manifest is None:
        feature_dir = repo_root / "kitty-specs" / mission_slug
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
        # T010: honor strategy for mission→target only; lane→mission is not touched
        _merge_branch_into(repo_root, mission_branch, target_branch, strategy=strategy)
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
    repo_root: Path,
    source_branch: str,
    target_branch: str,
    *,
    strategy: MergeStrategy = MergeStrategy.MERGE,
) -> None:
    """Merge source_branch into target_branch using a temporary worktree.

    Creates a detached worktree at the target branch tip, merges source
    into it using the specified strategy, then fast-forwards the target branch
    ref to the result. The main repo's checkout is never changed.

    Uses --detach to avoid "branch already checked out" errors when
    target_branch is the currently checked-out branch.

    Strategy behavior:
    - MERGE (default for lane→mission): ``git merge --no-ff``  — preserves structure
    - SQUASH: ``git merge --squash`` + explicit commit
    - REBASE: ``git rebase`` then fast-forward

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

        if strategy == MergeStrategy.SQUASH:
            # Squash all commits from source into a single new commit.
            result = subprocess.run(
                ["git", "merge", "--squash", source_branch],
                cwd=str(tmp_path), capture_output=True, text=True,
            )
            if result.returncode != 0:
                subprocess.run(
                    ["git", "merge", "--abort"],
                    cwd=str(tmp_path), capture_output=True,
                )
                raise RuntimeError(
                    f"Squash merge of {source_branch} into {target_branch} failed: "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )
            # Commit the squashed result.
            result = subprocess.run(
                [
                    "git", "-c", "commit.gpgsign=false",
                    "commit", "-m",
                    f"feat({source_branch}): squash merge of mission",
                ],
                cwd=str(tmp_path), capture_output=True, text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Squash commit into {target_branch} failed: "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )
        elif strategy == MergeStrategy.REBASE:
            # Rebase source onto target then fast-forward target.
            # We work in a temporary clone of source branch, rebase onto target.
            result = subprocess.run(
                ["git", "rebase", "HEAD", source_branch],
                cwd=str(repo_root), capture_output=True, text=True,
            )
            # Rebase approach: checkout source in the worktree and rebase onto target.
            # Simpler: just do a rebase in the tmp worktree.
            # First checkout source_branch in tmp worktree.
            result = subprocess.run(
                ["git", "checkout", source_branch],
                cwd=str(tmp_path), capture_output=True, text=True,
            )
            # Rebase source on top of target.
            result = subprocess.run(
                ["git", "rebase", target_branch],
                cwd=str(tmp_path), capture_output=True, text=True,
            )
            if result.returncode != 0:
                subprocess.run(
                    ["git", "rebase", "--abort"],
                    cwd=str(tmp_path), capture_output=True,
                )
                raise RuntimeError(
                    f"Rebase of {source_branch} onto {target_branch} failed: "
                    f"{result.stderr.strip() or result.stdout.strip()}"
                )
            # Get the rebased HEAD SHA.
            rebased_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(tmp_path), capture_output=True, text=True, check=True,
            ).stdout.strip()
            # Fast-forward the target branch to the rebased tip.
            result = subprocess.run(
                ["git", "update-ref", f"refs/heads/{target_branch}", rebased_sha],
                cwd=str(repo_root), capture_output=True, text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Failed to fast-forward {target_branch} after rebase: "
                    f"{result.stderr.strip()}"
                )
            return  # early return — ref already updated
        else:
            # MERGE strategy (default for lane→mission): no-ff merge commit.
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
