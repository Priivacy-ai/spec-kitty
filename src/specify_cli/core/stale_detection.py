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

from specify_cli.workspace_context import resolve_workspace_for_wp

PLANNING_ARTIFACT_REPO_ROOT_REASON = "planning_artifact_repo_root_shared_workspace"


@dataclass(frozen=True)
class StaleState:
    """Canonical stale-state payload for machine-facing status surfaces."""

    status: str
    reason: str | None = None
    minutes_since_commit: float | None = None
    last_commit_time: datetime | None = None

    def to_dict(self) -> dict[str, str | float | None]:
        """Serialize to the canonical JSON-compatible stale object."""
        return {
            "status": self.status,
            "reason": self.reason,
            "minutes_since_commit": self.minutes_since_commit,
            "last_commit_time": self.last_commit_time.isoformat() if self.last_commit_time else None,
        }


@dataclass
class StaleCheckResult:
    """Result of checking a work package for staleness."""

    wp_id: str
    stale: StaleState
    workspace_exists: bool
    workspace_kind: str
    error: str | None = None

    @property
    def is_stale(self) -> bool:
        """Deprecated flat compatibility field derived from the stale object."""
        return self.stale.status == "stale"

    @property
    def last_commit_time(self) -> datetime | None:
        """Deprecated flat compatibility field derived from the stale object."""
        return self.stale.last_commit_time

    @property
    def minutes_since_commit(self) -> float | None:
        """Deprecated flat compatibility field derived from the stale object."""
        return self.stale.minutes_since_commit

    @property
    def worktree_exists(self) -> bool:
        """Deprecated flat compatibility field derived from the stale object."""
        return self.workspace_kind != "repo_root" and self.workspace_exists


def get_default_branch(repo_path: Path) -> str:
    """
    Get the default/base branch name for the repository (for stale detection).

    This is used to find the branch that feature branches diverged FROM.
    Unlike resolve_primary_branch() in git_ops, this does NOT use the current
    branch because stale detection always runs from worktrees where the current
    branch is always the feature branch, never the base branch.

    Tries multiple methods to detect the default branch:
    1. Check origin's HEAD symbolic ref
    2. Check which common branch exists (main, master, develop)
    3. Fallback to "main"

    Args:
        repo_path: Path to the repository

    Returns:
        Default branch name (e.g., "main", "master", "develop")
    """
    import subprocess

    # Method 1: Get from origin's HEAD
    result = subprocess.run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=5,
    )

    if result.returncode == 0:
        # Output: "refs/remotes/origin/main" → extract "main"
        ref = result.stdout.strip()
        return ref.split("/")[-1]

    # Method 2: Check which common branch exists
    for branch in ["main", "master", "develop"]:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", branch],
            cwd=repo_path,
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            return branch

    # Method 3: Fallback
    return "main"


def get_last_meaningful_commit_time(worktree_path: Path) -> tuple[datetime | None, bool]:
    """
    Get the timestamp of the most recent meaningful commit in a worktree.

    A "meaningful" commit is one made ON THIS BRANCH since it diverged from main.
    This prevents false staleness when a worktree is just created but no commits
    have been made yet (HEAD points to parent branch's old commit).

    For worktrees, we always use git to check the branch-specific history,
    even in jj colocated repos. This is because:
    - jj's shared history includes commits from ALL workspaces
    - jj continuously auto-snapshots the working copy
    - We need the last commit on THIS worktree's branch, not the shared history

    Args:
        worktree_path: Path to the worktree

    Returns:
        Tuple of (datetime of last commit on this branch, has_own_commits).
        has_own_commits is False if the branch has no commits since diverging from main.
    """
    import subprocess

    if not worktree_path.exists():
        return None, False

    try:
        # Detect the actual default branch name (main, master, develop, etc.)
        default_branch = get_default_branch(worktree_path)

        # First, check if this branch has any commits since diverging from the default branch
        # This prevents false staleness when worktree was just created
        merge_base_result = subprocess.run(
            ["git", "merge-base", "HEAD", default_branch],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )

        if merge_base_result.returncode != 0:
            # Merge-base failed - branch might not exist, detached HEAD, etc.
            # Return None to avoid using wrong commit timestamp from parent branch
            return None, False

        merge_base = merge_base_result.stdout.strip()

        # Count commits on this branch since the merge base
        count_result = subprocess.run(
            ["git", "rev-list", "--count", f"{merge_base}..HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )

        if count_result.returncode == 0:
            commit_count = int(count_result.stdout.strip())
            if commit_count == 0:
                # No commits on this branch yet - worktree just created
                # Don't flag as stale since agent just started
                return None, False

        # Get the last commit time on this branch
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )

        if result.returncode != 0 or not result.stdout.strip():
            return None, False

        # Parse ISO format timestamp
        timestamp_str = result.stdout.strip()
        return datetime.fromisoformat(timestamp_str), True

    except subprocess.TimeoutExpired:
        return None, False
    except Exception:
        return None, False


def check_wp_staleness(
    wp_id: str,
    worktree_path: Path,
    threshold_minutes: int = 10,
) -> StaleCheckResult:
    """
    Check if a work package is stale based on VCS activity.

    A WP is considered stale if:
    - Its worktree exists
    - The branch has commits since diverging from main (agent has done work)
    - The last commit is older than threshold_minutes

    A WP with a worktree but NO commits since diverging is NOT stale - the agent
    just started and hasn't committed yet.

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
            stale=StaleState(status="fresh"),
            workspace_exists=False,
            workspace_kind="lane_workspace",
        )

    try:
        last_commit, has_own_commits = get_last_meaningful_commit_time(worktree_path)

        if last_commit is None:
            # Can't determine commit time, or no commits on this branch yet
            # If no commits yet (has_own_commits=False), agent just started - not stale
            return StaleCheckResult(
                wp_id=wp_id,
                stale=StaleState(status="fresh"),
                workspace_exists=True,
                workspace_kind="lane_workspace",
                error=None if not has_own_commits else "Could not determine last commit time",
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
            stale=StaleState(
                status="stale" if is_stale else "fresh",
                minutes_since_commit=round(minutes_since, 1),
                last_commit_time=last_commit,
            ),
            workspace_exists=True,
            workspace_kind="lane_workspace",
        )

    except Exception as e:
        return StaleCheckResult(
            wp_id=wp_id,
            stale=StaleState(status="fresh"),
            workspace_exists=True,
            workspace_kind="lane_workspace",
            error=str(e),
        )


def check_doing_wps_for_staleness(
    main_repo_root: Path,
    mission_slug: str,
    doing_wps: list[dict],
    threshold_minutes: int = 10,
) -> dict[str, StaleCheckResult]:
    """
    Check all WPs in "doing" lane for staleness.

    Args:
        main_repo_root: Root of the main repository
        mission_slug: Feature slug
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

        workspace = resolve_workspace_for_wp(main_repo_root, mission_slug, wp_id)

        if workspace.resolution_kind == "repo_root":
            result = StaleCheckResult(
                wp_id=wp_id,
                stale=StaleState(
                    status="not_applicable",
                    reason=PLANNING_ARTIFACT_REPO_ROOT_REASON,
                ),
                workspace_exists=workspace.exists,
                workspace_kind=workspace.resolution_kind,
            )
            results[wp_id] = result
            continue

        if workspace.exists:
            result = check_wp_staleness(wp_id, workspace.worktree_path, threshold_minutes)
        else:
            result = StaleCheckResult(
                wp_id=wp_id,
                stale=StaleState(status="fresh"),
                workspace_exists=False,
                workspace_kind=workspace.resolution_kind,
            )

        results[wp_id] = result

    return results
