"""Multi-parent dependency handling via automatic merge commits.

This module provides deterministic base branch calculation for work packages
with multiple dependencies. Instead of forcing the user to pick one dependency
as base and manually merge others, we automatically create a merge commit
combining all dependencies.

Example:
    WP04 depends on both WP02 and WP03:

    Before (ambiguous):
        spec-kitty implement WP04 --base WP03  # Why WP03? Why not WP02?
        cd .worktrees/010-feature-WP04/
        git merge 010-feature-WP02  # Manual merge required

    After (deterministic):
        spec-kitty implement WP04  # Auto-detects multi-parent, creates merge
        # WP04 branches from merge commit combining WP02 + WP03
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

console = Console()


@dataclass
class MergeResult:
    """Result of creating a multi-parent merge base."""

    success: bool
    branch_name: str | None  # Temporary branch name (e.g., "010-feature-WP04-merge-base")
    commit_sha: str | None  # SHA of merge commit
    error: str | None  # Error message if failed
    conflicts: list[str]  # List of files with conflicts (if any)


def create_multi_parent_base(
    feature_slug: str,
    wp_id: str,
    dependencies: list[str],
    repo_root: Path,
    target_branch: str | None = None,
) -> MergeResult:
    """Create a merge commit combining all dependencies for a work package.

    This function:
    1. Creates a temporary branch from the first dependency
    2. Merges all remaining dependencies into it
    3. Returns the merge commit SHA for use as base branch

    Args:
        feature_slug: Feature slug (e.g., "010-workspace-per-wp")
        wp_id: Work package ID (e.g., "WP04")
        dependencies: List of dependency WP IDs (e.g., ["WP02", "WP03"])
        repo_root: Repository root path

    Returns:
        MergeResult with success status and merge commit details

    Example:
        result = create_multi_parent_base(
            feature_slug="010-feature",
            wp_id="WP04",
            dependencies=["WP02", "WP03"],
            repo_root=Path("."),
        )
        if result.success:
            # Branch WP04 from result.branch_name or result.commit_sha
            print(f"Merge base: {result.commit_sha}")
    """
    if len(dependencies) < 2:
        return MergeResult(
            success=False,
            branch_name=None,
            commit_sha=None,
            error="Multi-parent merge requires at least 2 dependencies",
            conflicts=[],
        )

    # Resolve target branch dynamically if not provided
    if target_branch is None:
        from specify_cli.core.git_ops import resolve_primary_branch
        target_branch = resolve_primary_branch(repo_root)

    # Sort dependencies for deterministic ordering
    sorted_deps = sorted(dependencies)

    # Temporary branch name
    temp_branch = f"{feature_slug}-{wp_id}-merge-base"

    # Dependency branch names
    dep_branches = [f"{feature_slug}-{dep}" for dep in sorted_deps]

    try:
        # Step 1: Validate all dependency branches exist
        for dep, branch in zip(sorted_deps, dep_branches):
            result = subprocess.run(
                ["git", "rev-parse", "--verify", branch],
                cwd=repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if result.returncode != 0:
                return MergeResult(
                    success=False,
                    branch_name=None,
                    commit_sha=None,
                    error=f"Dependency branch {branch} does not exist (implement {dep} first)",
                    conflicts=[],
                )

        # Step 1.5: Check if each dependency branch has unique commits
        # (Warn if branch is empty - may indicate incomplete work)
        for dep, branch in zip(sorted_deps, dep_branches):
            try:
                # Get merge-base between dep branch and main (WITH TIMEOUT)
                merge_base_result = subprocess.run(
                    ["git", "merge-base", branch, target_branch],
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                    timeout=10,  # 10 second timeout
                )

                if merge_base_result.returncode == 0:
                    merge_base = merge_base_result.stdout.strip()

                    # Get branch tip (WITH TIMEOUT)
                    branch_tip_result = subprocess.run(
                        ["git", "rev-parse", branch],
                        cwd=repo_root,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        check=False,
                        timeout=10,  # 10 second timeout
                    )

                    if branch_tip_result.returncode == 0:
                        branch_tip = branch_tip_result.stdout.strip()

                        # If merge-base == branch tip, branch has no unique commits
                        if merge_base == branch_tip:
                            # Bug #1 Fix: Write to stderr to avoid corrupting JSON output
                            print(f"⚠️  Warning: Dependency branch '{branch}' has no commits beyond {target_branch}", file=sys.stderr)
                            print(f"   This may indicate incomplete work or uncommitted changes", file=sys.stderr)
                            print(f"   The merge-base will not include any work from this branch\n", file=sys.stderr)

            except subprocess.TimeoutExpired:
                # Git command took too long - skip this check
                print(f"⚠️  Warning: Timeout checking dependency branch '{branch}' (git taking >10s)", file=sys.stderr)
                continue
            except Exception as e:
                # Unexpected error - log and continue
                print(f"⚠️  Warning: Error checking dependency branch '{branch}': {e}", file=sys.stderr)
                continue

        # Step 2: Check if temp branch already exists (cleanup from previous run)
        result = subprocess.run(
            ["git", "rev-parse", "--verify", temp_branch],
            cwd=repo_root,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            # Delete existing temp branch
            subprocess.run(
                ["git", "branch", "-D", temp_branch],
                cwd=repo_root,
                capture_output=True,
                check=False,
            )

        # Step 3: Create temp branch from first dependency
        base_branch = dep_branches[0]
        result = subprocess.run(
            ["git", "branch", temp_branch, base_branch],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            return MergeResult(
                success=False,
                branch_name=None,
                commit_sha=None,
                error=f"Failed to create temp branch from {base_branch}: {result.stderr}",
                conflicts=[],
            )

        # Step 4: Checkout temp branch
        result = subprocess.run(
            ["git", "checkout", temp_branch],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            return MergeResult(
                success=False,
                branch_name=None,
                commit_sha=None,
                error=f"Failed to checkout temp branch: {result.stderr}",
                conflicts=[],
            )

        # Step 5: Merge remaining dependencies
        conflicts = []
        for dep_branch in dep_branches[1:]:
            result = subprocess.run(
                ["git", "merge", "--no-edit", dep_branch, "-m",
                 f"Merge {dep_branch} into multi-parent base for {wp_id}"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )

            if result.returncode != 0:
                # Check if merge conflicts
                conflict_result = subprocess.run(
                    ["git", "diff", "--name-only", "--diff-filter=U"],
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                if conflict_result.returncode == 0 and conflict_result.stdout.strip():
                    conflicts = conflict_result.stdout.strip().split("\n")

                # Abort merge
                subprocess.run(
                    ["git", "merge", "--abort"],
                    cwd=repo_root,
                    capture_output=True,
                    check=False,
                )

                # Cleanup: delete temp branch
                subprocess.run(
                    ["git", "checkout", "-"],  # Return to previous branch
                    cwd=repo_root,
                    capture_output=True,
                    check=False,
                )
                subprocess.run(
                    ["git", "branch", "-D", temp_branch],
                    cwd=repo_root,
                    capture_output=True,
                    check=False,
                )

                return MergeResult(
                    success=False,
                    branch_name=None,
                    commit_sha=None,
                    error=f"Merge conflict when merging {dep_branch}",
                    conflicts=conflicts,
                )

        # Step 6: Get merge commit SHA
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            return MergeResult(
                success=False,
                branch_name=temp_branch,
                commit_sha=None,
                error="Failed to get merge commit SHA",
                conflicts=[],
            )

        merge_commit_sha = result.stdout.strip()

        # Step 7: Return to previous branch
        subprocess.run(
            ["git", "checkout", "-"],
            cwd=repo_root,
            capture_output=True,
            check=False,
        )

        console.print(f"[cyan]→ Created merge base: {temp_branch} ({merge_commit_sha[:7]})[/cyan]")
        console.print(f"[cyan]  Combined dependencies: {', '.join(sorted_deps)}[/cyan]")

        return MergeResult(
            success=True,
            branch_name=temp_branch,
            commit_sha=merge_commit_sha,
            error=None,
            conflicts=[],
        )

    except Exception as e:
        # Cleanup on exception
        subprocess.run(
            ["git", "checkout", "-"],
            cwd=repo_root,
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["git", "branch", "-D", temp_branch],
            cwd=repo_root,
            capture_output=True,
            check=False,
        )

        return MergeResult(
            success=False,
            branch_name=None,
            commit_sha=None,
            error=f"Unexpected error: {e}",
            conflicts=[],
        )


def cleanup_merge_base_branch(
    feature_slug: str,
    wp_id: str,
    repo_root: Path,
) -> bool:
    """Delete temporary merge base branch after workspace creation.

    Args:
        feature_slug: Feature slug (e.g., "010-workspace-per-wp")
        wp_id: Work package ID (e.g., "WP04")
        repo_root: Repository root path

    Returns:
        True if deleted, False if branch didn't exist
    """
    temp_branch = f"{feature_slug}-{wp_id}-merge-base"

    # Check if branch exists
    result = subprocess.run(
        ["git", "rev-parse", "--verify", temp_branch],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        return False  # Branch doesn't exist

    # Delete branch
    result = subprocess.run(
        ["git", "branch", "-D", temp_branch],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )

    return result.returncode == 0


__all__ = [
    "MergeResult",
    "create_multi_parent_base",
    "cleanup_merge_base_branch",
]
