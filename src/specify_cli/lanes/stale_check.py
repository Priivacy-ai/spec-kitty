"""Stale-lane merge blocker.

A lane branch is stale when:
1. The mission branch has advanced since the lane last incorporated it.
2. The changed files in the mission overlap with the lane's changed files.

This uses file-level intersection (git diff --name-only) rather than
glob-level matching to avoid false positives.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from specify_cli.lanes.models import ExecutionLane


@dataclass
class StaleCheckResult:
    """Result of a stale-lane check."""

    is_stale: bool
    stale_files: list[str] = field(default_factory=list)
    remediation: str | None = None


def check_lane_staleness(
    lane: ExecutionLane,
    lane_branch: str,
    mission_branch: str,
    repo_root: Path,
) -> StaleCheckResult:
    """Check if a lane branch has diverged from the mission branch on overlapping files.

    Algorithm:
    1. Find the merge-base between lane and mission branches.
    2. Diff mission branch from merge-base → files mission has changed.
    3. Diff lane branch from merge-base → files lane has changed.
    4. Intersect the two sets.
    5. If non-empty, the lane is stale.

    Args:
        lane: The ExecutionLane being checked.
        lane_branch: Git branch name of the lane.
        mission_branch: Git branch name of the mission integration branch.
        repo_root: Path to the main repository.

    Returns:
        StaleCheckResult with is_stale, overlapping files, and remediation.
    """
    # Find merge-base.
    merge_base = _git_merge_base(repo_root, lane_branch, mission_branch)
    if merge_base is None:
        # No common ancestor — branches are unrelated. Not stale.
        return StaleCheckResult(is_stale=False)

    # Files changed in mission since merge-base.
    mission_files = _git_diff_names(repo_root, merge_base, mission_branch)

    if not mission_files:
        # Mission hasn't advanced with any file changes. Not stale.
        return StaleCheckResult(is_stale=False)

    # Files changed in lane since merge-base.
    lane_files = _git_diff_names(repo_root, merge_base, lane_branch)

    # Intersection = files both sides changed.
    overlap = sorted(mission_files & lane_files)

    if not overlap:
        return StaleCheckResult(is_stale=False)

    return StaleCheckResult(
        is_stale=True,
        stale_files=overlap,
        remediation=(f"Lane {lane.lane_id} must incorporate mission changes before merging. Run: cd .worktrees/*-{lane.lane_id} && git merge {mission_branch}"),
    )


def _git_merge_base(repo_root: Path, ref_a: str, ref_b: str) -> str | None:
    """Return the merge-base commit between two refs, or None."""
    result = subprocess.run(
        ["git", "merge-base", ref_a, ref_b],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _git_diff_names(repo_root: Path, base: str, head: str) -> set[str]:
    """Return the set of files changed between base and head."""
    result = subprocess.run(
        ["git", "diff", "--name-only", base, head],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}
