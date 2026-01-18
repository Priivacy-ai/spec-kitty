"""Core merge execution logic.

Provides the main entry point for merge operations, orchestrating
pre-flight validation, conflict forecasting, ordering, and execution.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from specify_cli.cli import StepTracker
from specify_cli.cli.helpers import console
from specify_cli.core.git_ops import run_command
from specify_cli.merge.ordering import (
    MergeOrderError,
    display_merge_order,
    get_merge_order,
)
from specify_cli.merge.preflight import (
    PreflightResult,
    display_preflight_result,
    run_preflight,
)
from specify_cli.merge.forecast import (
    display_conflict_forecast,
    predict_conflicts,
)

__all__ = ["execute_merge", "MergeResult", "MergeExecutionError"]


class MergeExecutionError(Exception):
    """Error during merge execution."""

    pass


@dataclass
class MergeResult:
    """Result of merge execution."""

    success: bool
    merged_wps: list[str] = field(default_factory=list)
    failed_wp: str | None = None
    error: str | None = None
    preflight_result: PreflightResult | None = None


def execute_merge(
    wp_workspaces: list[tuple[Path, str, str]],
    feature_slug: str,
    feature_dir: Path | None,
    target_branch: str,
    strategy: str,
    repo_root: Path,
    merge_root: Path,
    tracker: StepTracker,
    delete_branch: bool = True,
    remove_worktree: bool = True,
    push: bool = False,
    dry_run: bool = False,
    on_wp_merged: Callable[[str], None] | None = None,
) -> MergeResult:
    """Execute merge for all WPs with preflight and ordering.

    This is the main entry point for workspace-per-WP merges, coordinating:
    1. Pre-flight validation (all worktrees clean, target not diverged)
    2. Dependency-based ordering (topological sort)
    3. Sequential merge execution
    4. Cleanup (worktree removal, branch deletion)

    Args:
        wp_workspaces: List of (worktree_path, wp_id, branch_name) tuples
        feature_slug: Feature identifier (e.g., "010-feature-name")
        feature_dir: Path to feature directory (for dependency info), or None
        target_branch: Branch to merge into (e.g., "main")
        strategy: "merge", "squash", or "rebase"
        repo_root: Repository root path
        merge_root: Directory to execute merge from (main repo)
        tracker: StepTracker for progress display
        delete_branch: Whether to delete branches after merge
        remove_worktree: Whether to remove worktrees after merge
        push: Whether to push to remote after merge
        dry_run: If True, show what would be done without executing
        on_wp_merged: Callback after each WP merges (for state updates)

    Returns:
        MergeResult with success status and details
    """
    result = MergeResult(success=False)

    if not wp_workspaces:
        result.error = "No WP workspaces provided"
        return result

    # Step 1: Run preflight checks
    tracker.start("preflight")
    preflight_result = run_preflight(
        feature_slug=feature_slug,
        target_branch=target_branch,
        repo_root=repo_root,
        wp_workspaces=wp_workspaces,
    )
    result.preflight_result = preflight_result
    display_preflight_result(preflight_result, console)

    if not preflight_result.passed:
        tracker.error("preflight", "validation failed")
        result.error = "Pre-flight validation failed"
        return result
    tracker.complete("preflight", "all checks passed")

    # Step 2: Determine merge order based on dependencies
    if feature_dir and feature_dir.exists():
        try:
            ordered_workspaces = get_merge_order(wp_workspaces, feature_dir)
            display_merge_order(ordered_workspaces, console)
        except MergeOrderError as e:
            tracker.error("preflight", f"ordering failed: {e}")
            result.error = str(e)
            return result
    else:
        # No feature dir - use as-is (already sorted by WP ID)
        ordered_workspaces = sorted(wp_workspaces, key=lambda x: x[1])
        console.print("\n[dim]Merge order: numerical (no dependency info)[/dim]")

    # Step 3: Validate all WP workspaces are ready
    tracker.start("verify")
    errors = []
    for wt_path, wp_id, branch in ordered_workspaces:
        is_valid, error_msg = _validate_wp_ready(repo_root, wt_path, branch)
        if not is_valid:
            errors.append(f"  - {wp_id}: {error_msg}")

    if errors:
        tracker.error("verify", "WP workspaces not ready")
        result.error = "WP workspaces not ready:\n" + "\n".join(errors)
        return result

    tracker.complete("verify", f"validated {len(ordered_workspaces)} workspaces")

    # Step 4: Dry run - show what would be done
    if dry_run:
        # Predict conflicts before showing dry-run steps
        predictions = predict_conflicts(ordered_workspaces, target_branch, repo_root)
        display_conflict_forecast(predictions, console)

        _show_dry_run(
            ordered_workspaces,
            target_branch,
            strategy,
            feature_slug,
            push,
            remove_worktree,
            delete_branch,
        )
        result.success = True
        result.merged_wps = [wp_id for _, wp_id, _ in ordered_workspaces]
        return result

    # Step 5: Checkout and update target branch
    tracker.start("checkout")
    try:
        os.chdir(merge_root)
        _, target_status, _ = run_command(["git", "status", "--porcelain"], capture=True)
        if target_status.strip():
            raise MergeExecutionError(
                f"Target repository at {merge_root} has uncommitted changes."
            )
        run_command(["git", "checkout", target_branch])
        tracker.complete("checkout", f"using {merge_root}")
    except Exception as exc:
        tracker.error("checkout", str(exc))
        result.error = f"Checkout failed: {exc}"
        return result

    tracker.start("pull")
    try:
        run_command(["git", "pull", "--ff-only"])
        tracker.complete("pull")
    except Exception as exc:
        tracker.error("pull", str(exc))
        result.error = f"Pull failed: {exc}. You may need to resolve conflicts manually."
        return result

    # Step 6: Merge all WP branches in dependency order
    tracker.start("merge")
    try:
        for wt_path, wp_id, branch in ordered_workspaces:
            console.print(f"[cyan]Merging {wp_id} ({branch})...[/cyan]")

            if strategy == "squash":
                run_command(["git", "merge", "--squash", branch])
                run_command(
                    ["git", "commit", "-m", f"Merge {wp_id} from {feature_slug}"]
                )
            elif strategy == "rebase":
                result.error = "Rebase strategy not supported for workspace-per-WP."
                tracker.skip("merge", "rebase not supported")
                return result
            else:  # merge (default)
                run_command(
                    [
                        "git",
                        "merge",
                        "--no-ff",
                        branch,
                        "-m",
                        f"Merge {wp_id} from {feature_slug}",
                    ]
                )

            result.merged_wps.append(wp_id)
            console.print(f"[green]\u2713[/green] {wp_id} merged")

            if on_wp_merged:
                on_wp_merged(wp_id)

        tracker.complete("merge", f"merged {len(ordered_workspaces)} work packages")
    except Exception as exc:
        tracker.error("merge", str(exc))
        result.failed_wp = wp_id if "wp_id" in dir() else None
        result.error = f"Merge failed: {exc}"
        return result

    # Step 7: Push if requested
    if push:
        tracker.start("push")
        try:
            run_command(["git", "push", "origin", target_branch])
            tracker.complete("push")
        except Exception as exc:
            tracker.error("push", str(exc))
            console.print(
                f"\n[yellow]Warning:[/yellow] Merge succeeded but push failed."
            )
            console.print(f"Run manually: git push origin {target_branch}")

    # Step 8: Remove worktrees
    if remove_worktree:
        tracker.start("worktree")
        failed_removals = []
        for wt_path, wp_id, branch in ordered_workspaces:
            try:
                run_command(["git", "worktree", "remove", str(wt_path), "--force"])
                console.print(f"[green]\u2713[/green] Removed worktree: {wp_id}")
            except Exception:
                failed_removals.append((wp_id, wt_path))

        if failed_removals:
            tracker.error(
                "worktree", f"could not remove {len(failed_removals)} worktrees"
            )
            console.print(
                f"\n[yellow]Warning:[/yellow] Could not remove some worktrees:"
            )
            for wp_id, wt_path in failed_removals:
                console.print(f"  {wp_id}: git worktree remove {wt_path}")
        else:
            tracker.complete("worktree", f"removed {len(ordered_workspaces)} worktrees")

    # Step 9: Delete branches
    if delete_branch:
        tracker.start("branch")
        failed_deletions = []
        for wt_path, wp_id, branch in ordered_workspaces:
            try:
                run_command(["git", "branch", "-d", branch])
                console.print(f"[green]\u2713[/green] Deleted branch: {branch}")
            except Exception:
                # Try force delete
                try:
                    run_command(["git", "branch", "-D", branch])
                    console.print(f"[green]\u2713[/green] Force deleted branch: {branch}")
                except Exception:
                    failed_deletions.append((wp_id, branch))

        if failed_deletions:
            tracker.error(
                "branch", f"could not delete {len(failed_deletions)} branches"
            )
            console.print(
                f"\n[yellow]Warning:[/yellow] Could not delete some branches:"
            )
            for wp_id, branch in failed_deletions:
                console.print(f"  {wp_id}: git branch -D {branch}")
        else:
            tracker.complete("branch", f"deleted {len(ordered_workspaces)} branches")

    result.success = True
    return result


def _validate_wp_ready(
    repo_root: Path, worktree_path: Path, branch_name: str
) -> tuple[bool, str]:
    """Validate WP workspace is ready to merge.

    Args:
        repo_root: Repository root
        worktree_path: Path to worktree
        branch_name: Branch name to verify

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check 1: Branch exists in git
    result = subprocess.run(
        ["git", "rev-parse", "--verify", branch_name],
        cwd=str(repo_root),
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return False, f"Branch {branch_name} does not exist"

    # Check 2: No uncommitted changes in worktree
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(worktree_path),
        capture_output=True,
        text=True,
    )
    if result.stdout.strip():
        return False, f"Worktree {worktree_path.name} has uncommitted changes"

    return True, ""


def _show_dry_run(
    ordered_workspaces: list[tuple[Path, str, str]],
    target_branch: str,
    strategy: str,
    feature_slug: str,
    push: bool,
    remove_worktree: bool,
    delete_branch: bool,
) -> None:
    """Display dry run output showing what would be executed.

    Args:
        ordered_workspaces: Ordered list of (path, wp_id, branch) tuples
        target_branch: Target branch name
        strategy: Merge strategy
        feature_slug: Feature identifier
        push: Whether push is enabled
        remove_worktree: Whether worktree removal is enabled
        delete_branch: Whether branch deletion is enabled
    """
    console.print("\n[cyan]Dry run - would execute:[/cyan]")
    steps = [
        f"git checkout {target_branch}",
        "git pull --ff-only",
    ]

    for wt_path, wp_id, branch in ordered_workspaces:
        if strategy == "squash":
            steps.extend(
                [
                    f"git merge --squash {branch}",
                    f"git commit -m 'Merge {wp_id} from {feature_slug}'",
                ]
            )
        else:
            steps.append(
                f"git merge --no-ff {branch} -m 'Merge {wp_id} from {feature_slug}'"
            )

    if push:
        steps.append(f"git push origin {target_branch}")

    if remove_worktree:
        for wt_path, wp_id, branch in ordered_workspaces:
            steps.append(f"git worktree remove {wt_path}")

    if delete_branch:
        for wt_path, wp_id, branch in ordered_workspaces:
            steps.append(f"git branch -d {branch}")

    for idx, step in enumerate(steps, start=1):
        console.print(f"  {idx}. {step}")
