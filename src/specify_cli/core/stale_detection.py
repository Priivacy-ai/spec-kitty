"""
Stale Work Package Detection
============================

Detects work packages that are in "doing" lane but have no recent VCS activity,
indicating the agent may have stopped without transitioning the WP.

Uses git/jj commit timestamps as a "heartbeat" - if no commits for a threshold
period, the WP is considered stale.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from specify_cli.core.vcs import get_vcs, VCSError


@dataclass
class StaleCheckResult:
    """Result of checking a work package for staleness."""

    wp_id: str
    is_stale: bool
    last_commit_time: datetime | None
    minutes_since_commit: float | None
    worktree_exists: bool
    error: str | None = None


def get_last_meaningful_commit_time(worktree_path: Path) -> datetime | None:
    """
    Get the timestamp of the most recent meaningful commit in a worktree.

    For worktrees, we always use git to check the branch-specific history,
    even in jj colocated repos. This is because:
    - jj's shared history includes commits from ALL workspaces
    - jj continuously auto-snapshots the working copy
    - We need the last commit on THIS worktree's branch, not the shared history

    Args:
        worktree_path: Path to the worktree

    Returns:
        datetime of last meaningful commit, or None if unable to determine
    """
    import subprocess

    if not worktree_path.exists():
        return None

    try:
        # Always use git for worktree branch history
        # This works for both pure git and jj colocated repos
        # because jj colocated repos maintain a .git directory
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0 or not result.stdout.strip():
            return None

        # Parse ISO format timestamp
        timestamp_str = result.stdout.strip()
        return datetime.fromisoformat(timestamp_str)

    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None


def check_wp_staleness(
    wp_id: str,
    worktree_path: Path,
    threshold_minutes: int = 10,
) -> StaleCheckResult:
    """
    Check if a work package is stale based on VCS activity.

    A WP is considered stale if:
    - Its worktree exists
    - The last commit is older than threshold_minutes

    Args:
        wp_id: Work package ID (e.g., "WP01")
        worktree_path: Path to the WP's worktree
        threshold_minutes: Minutes of inactivity before considered stale

    Returns:
        StaleCheckResult with staleness status
    """
    if not worktree_path.exists():
        return StaleCheckResult(
            wp_id=wp_id,
            is_stale=False,
            last_commit_time=None,
            minutes_since_commit=None,
            worktree_exists=False,
        )

    try:
        last_commit = get_last_meaningful_commit_time(worktree_path)

        if last_commit is None:
            # Can't determine - don't flag as stale
            return StaleCheckResult(
                wp_id=wp_id,
                is_stale=False,
                last_commit_time=None,
                minutes_since_commit=None,
                worktree_exists=True,
                error="Could not determine last commit time",
            )

        now = datetime.now(timezone.utc)
        # Ensure last_commit is timezone-aware
        if last_commit.tzinfo is None:
            last_commit = last_commit.replace(tzinfo=timezone.utc)

        delta = now - last_commit
        minutes_since = delta.total_seconds() / 60

        is_stale = minutes_since > threshold_minutes

        return StaleCheckResult(
            wp_id=wp_id,
            is_stale=is_stale,
            last_commit_time=last_commit,
            minutes_since_commit=round(minutes_since, 1),
            worktree_exists=True,
        )

    except Exception as e:
        return StaleCheckResult(
            wp_id=wp_id,
            is_stale=False,
            last_commit_time=None,
            minutes_since_commit=None,
            worktree_exists=True,
            error=str(e),
        )


def find_worktree_for_wp(
    main_repo_root: Path,
    feature_slug: str,
    wp_id: str,
) -> Path | None:
    """
    Find the worktree path for a given work package.

    Args:
        main_repo_root: Root of the main repository
        feature_slug: Feature slug (e.g., "001-my-feature")
        wp_id: Work package ID (e.g., "WP01")

    Returns:
        Path to worktree if found, None otherwise
    """
    worktrees_dir = main_repo_root / ".worktrees"
    if not worktrees_dir.exists():
        return None

    # Expected pattern: feature_slug-WP01
    expected_name = f"{feature_slug}-{wp_id}"
    worktree_path = worktrees_dir / expected_name

    if worktree_path.exists():
        return worktree_path

    # Try case-insensitive search
    for item in worktrees_dir.iterdir():
        if item.is_dir() and item.name.lower() == expected_name.lower():
            return item

    return None


def check_doing_wps_for_staleness(
    main_repo_root: Path,
    feature_slug: str,
    doing_wps: list[dict],
    threshold_minutes: int = 10,
) -> dict[str, StaleCheckResult]:
    """
    Check all WPs in "doing" lane for staleness.

    Args:
        main_repo_root: Root of the main repository
        feature_slug: Feature slug
        doing_wps: List of WP dicts with at least 'id' key
        threshold_minutes: Minutes of inactivity threshold

    Returns:
        Dict mapping WP ID to StaleCheckResult
    """
    results = {}

    for wp in doing_wps:
        wp_id = wp.get("id") or wp.get("work_package_id")
        if not wp_id:
            continue

        worktree_path = find_worktree_for_wp(main_repo_root, feature_slug, wp_id)

        if worktree_path:
            result = check_wp_staleness(wp_id, worktree_path, threshold_minutes)
        else:
            result = StaleCheckResult(
                wp_id=wp_id,
                is_stale=False,
                last_commit_time=None,
                minutes_since_commit=None,
                worktree_exists=False,
            )

        results[wp_id] = result

    return results
