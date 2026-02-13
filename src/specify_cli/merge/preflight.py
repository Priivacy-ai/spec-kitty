"""Pre-flight validation for merge operations.

Implements FR-001 through FR-004: checking worktree status and target branch
divergence before any merge operation begins.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.table import Table

from specify_cli.core.dependency_graph import build_dependency_graph

__all__ = [
    "WPStatus",
    "PreflightResult",
    "check_worktree_status",
    "check_target_divergence",
    "run_preflight",
    "display_preflight_result",
]


@dataclass
class WPStatus:
    """Status of a single WP worktree during pre-flight."""

    wp_id: str
    worktree_path: Path
    branch_name: str
    is_clean: bool
    error: str | None = None


@dataclass
class PreflightResult:
    """Result of pre-merge validation checks."""

    passed: bool
    wp_statuses: list[WPStatus] = field(default_factory=list)
    target_diverged: bool = False
    target_divergence_msg: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def check_worktree_status(worktree_path: Path, wp_id: str, branch_name: str) -> WPStatus:
    """Check if a worktree has uncommitted changes.

    Args:
        worktree_path: Path to the worktree directory
        wp_id: Work package ID (e.g., "WP01")
        branch_name: Name of the branch

    Returns:
        WPStatus with is_clean=True if no uncommitted changes
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(worktree_path),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        is_clean = not result.stdout.strip()
        error = None if is_clean else f"Uncommitted changes in {worktree_path.name}"
        return WPStatus(
            wp_id=wp_id,
            worktree_path=worktree_path,
            branch_name=branch_name,
            is_clean=is_clean,
            error=error,
        )
    except Exception as e:
        return WPStatus(
            wp_id=wp_id,
            worktree_path=worktree_path,
            branch_name=branch_name,
            is_clean=False,
            error=str(e),
        )


def check_target_divergence(target_branch: str, repo_root: Path) -> tuple[bool, str | None]:
    """Check if target branch has diverged from origin.

    Args:
        target_branch: Name of the target branch (e.g., "main")
        repo_root: Path to the repository root

    Returns:
        Tuple of (has_diverged, remediation_message)
        - has_diverged: True if local branch is behind origin
        - remediation_message: Instructions for fixing divergence
    """
    try:
        # Fetch latest refs (optional, may fail if offline)
        subprocess.run(
            ["git", "fetch", "origin", target_branch],
            cwd=str(repo_root),
            capture_output=True,
            check=False,
        )

        # Count commits ahead/behind
        result = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", f"{target_branch}...origin/{target_branch}"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

        if result.returncode != 0:
            return False, None  # No remote tracking, assume OK

        parts = result.stdout.strip().split()
        if len(parts) != 2:
            return False, None  # Unexpected output, assume OK

        ahead, behind = map(int, parts)

        if behind > 0:
            return True, f"{target_branch} is {behind} commit(s) behind origin. Run: git checkout {target_branch} && git pull"

        return False, None

    except Exception:
        return False, None  # Assume OK if check fails


def run_preflight(
    feature_slug: str,
    target_branch: str,
    repo_root: Path,
    wp_workspaces: list[tuple[Path, str, str]],
) -> PreflightResult:
    """Run all pre-flight checks before merge.

    Args:
        feature_slug: Feature identifier (e.g., "017-smarter-feature-merge")
        target_branch: Branch to merge into (e.g., "main")
        repo_root: Repository root path
        wp_workspaces: List of (worktree_path, wp_id, branch_name) tuples

    Returns:
        PreflightResult with all check outcomes
    """
    result = PreflightResult(passed=True)

    # Check for missing worktrees based on tasks in kitty-specs
    expected_graph = build_dependency_graph(repo_root / "kitty-specs" / feature_slug)
    expected_wps = set(expected_graph.keys())
    discovered_wps = {wp_id for _, wp_id, _ in wp_workspaces}
    missing_wps = sorted(expected_wps - discovered_wps)
    if missing_wps:
        result.passed = False
        for wp_id in missing_wps:
            expected_path = repo_root / ".worktrees" / f"{feature_slug}-{wp_id}"
            error = f"Missing worktree for {wp_id}. Expected at {expected_path.name}. Run: spec-kitty agent workflow implement {wp_id}"
            result.wp_statuses.append(
                WPStatus(
                    wp_id=wp_id,
                    worktree_path=expected_path,
                    branch_name=f"{feature_slug}-{wp_id}",
                    is_clean=False,
                    error=error,
                )
            )
            result.errors.append(error)

    # Check all worktrees
    for wt_path, wp_id, branch in wp_workspaces:
        status = check_worktree_status(wt_path, wp_id, branch)
        result.wp_statuses.append(status)
        if not status.is_clean:
            result.passed = False
            result.errors.append(status.error or f"{wp_id} has uncommitted changes")

    # Check target divergence
    diverged, msg = check_target_divergence(target_branch, repo_root)
    result.target_diverged = diverged
    result.target_divergence_msg = msg
    if diverged:
        result.passed = False
        result.errors.append(msg or f"{target_branch} has diverged from origin")

    return result


def display_preflight_result(result: PreflightResult, console: Console) -> None:
    """Display pre-flight results with Rich formatting.

    Args:
        result: PreflightResult to display
        console: Rich Console instance for output
    """
    console.print("\n[bold]Pre-flight Check[/bold]\n")

    # WP status table
    table = Table(show_header=True, header_style="bold")
    table.add_column("WP")
    table.add_column("Status")
    table.add_column("Issue")

    for status in result.wp_statuses:
        icon = "[green]✓[/green]" if status.is_clean else "[red]✗[/red]"
        issue = status.error or ""
        table.add_row(status.wp_id, icon, issue)

    # Target branch status
    if result.target_diverged:
        table.add_row("Target", "[red]✗[/red]", result.target_divergence_msg or "Diverged")
    else:
        table.add_row("Target", "[green]✓[/green]", "Up to date")

    console.print(table)

    if not result.passed:
        console.print("\n[bold red]Pre-flight failed.[/bold red] Fix these issues before merging:\n")
        for i, error in enumerate(result.errors, 1):
            console.print(f"  {i}. {error}")
        console.print()
    else:
        console.print("\n[green]Pre-flight passed.[/green] Ready to merge.\n")
