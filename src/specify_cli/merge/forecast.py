"""Conflict prediction for merge dry-run.

Implements FR-005 through FR-007: predicting which files will conflict
during merge and identifying auto-resolvable status files.
"""

from __future__ import annotations

import fnmatch
import subprocess
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.table import Table

__all__ = [
    "ConflictPrediction",
    "predict_conflicts",
    "is_status_file",
    "build_file_wp_mapping",
    "display_conflict_forecast",
]


# Patterns for status files that can be auto-resolved
STATUS_FILE_PATTERNS = [
    "kitty-specs/*/tasks/*.md",  # WP files: kitty-specs/017-feature/tasks/WP01.md
    "kitty-specs/*/tasks.md",  # Main tasks: kitty-specs/017-feature/tasks.md
    "kitty-specs/*/*/tasks/*.md",  # Nested: kitty-specs/features/017/tasks/WP01.md
    "kitty-specs/*/*/tasks.md",  # Nested main
]


@dataclass
class ConflictPrediction:
    """Predicted conflict for a file.

    Attributes:
        file_path: Path to the file that may conflict
        conflicting_wps: List of WP IDs that modify this file
        is_status_file: True if file matches status file pattern
        confidence: Prediction confidence ("certain", "likely", "possible")
    """

    file_path: str
    conflicting_wps: list[str]
    is_status_file: bool
    confidence: str  # "certain", "likely", "possible"

    @property
    def auto_resolvable(self) -> bool:
        """Status files can be auto-resolved."""
        return self.is_status_file


def is_status_file(file_path: str) -> bool:
    """Check if file matches status file patterns.

    Status files contain lane/checkbox/history that can be auto-resolved
    during merge because their content is procedurally generated.

    Args:
        file_path: Path to check (relative to repo root)

    Returns:
        True if file matches a status file pattern
    """
    for pattern in STATUS_FILE_PATTERNS:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    return False


def build_file_wp_mapping(
    wp_workspaces: list[tuple[Path, str, str]],
    target_branch: str,
    repo_root: Path,
) -> dict[str, list[str]]:
    """Build mapping of file paths to WPs that modify them.

    Uses git diff to identify which files each WP branch modifies
    relative to the target branch.

    Args:
        wp_workspaces: List of (worktree_path, wp_id, branch_name) tuples
        target_branch: Branch being merged into (e.g., "main")
        repo_root: Repository root for running git commands

    Returns:
        Dict mapping file_path → [wp_ids that modify it]
    """
    file_to_wps: dict[str, list[str]] = {}

    for _, wp_id, branch_name in wp_workspaces:
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", f"{target_branch}...{branch_name}"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        if line not in file_to_wps:
                            file_to_wps[line] = []
                        file_to_wps[line].append(wp_id)
        except Exception:
            continue  # Skip this WP if diff fails

    return file_to_wps


def predict_conflicts(
    wp_workspaces: list[tuple[Path, str, str]],
    target_branch: str,
    repo_root: Path,
) -> list[ConflictPrediction]:
    """Predict which files will conflict during merge.

    Identifies files modified by multiple WPs, which may result in
    merge conflicts. Status files are marked as auto-resolvable.

    Args:
        wp_workspaces: Ordered list of (worktree_path, wp_id, branch_name) tuples
        target_branch: Branch being merged into (e.g., "main")
        repo_root: Repository root for running git commands

    Returns:
        List of ConflictPrediction for files with potential conflicts
    """
    file_to_wps = build_file_wp_mapping(wp_workspaces, target_branch, repo_root)

    predictions = []
    for file_path, wp_ids in sorted(file_to_wps.items()):
        if len(wp_ids) >= 2:
            predictions.append(
                ConflictPrediction(
                    file_path=file_path,
                    conflicting_wps=wp_ids,
                    is_status_file=is_status_file(file_path),
                    confidence="possible",  # Can enhance with merge-tree in future
                )
            )

    return predictions


def display_conflict_forecast(
    predictions: list[ConflictPrediction],
    console: Console,
) -> None:
    """Display conflict predictions with Rich formatting.

    Groups predictions into auto-resolvable (status files) and
    manual-required categories for clear user guidance.

    Args:
        predictions: List of ConflictPrediction objects
        console: Rich Console instance for output
    """
    if not predictions:
        console.print("\n[green]No conflicts predicted[/green]\n")
        return

    console.print("\n[bold]Conflict Forecast[/bold]\n")

    auto_resolvable = [p for p in predictions if p.auto_resolvable]
    manual_required = [p for p in predictions if not p.auto_resolvable]

    # Summary counts
    total = len(predictions)
    auto_count = len(auto_resolvable)
    manual_count = len(manual_required)

    console.print(f"[dim]Found {total} potential conflict(s): {auto_count} auto-resolvable, {manual_count} manual[/dim]\n")

    # Create table for conflicts
    if manual_required:
        table = Table(show_header=True, header_style="bold yellow")
        table.add_column("File")
        table.add_column("WPs")
        table.add_column("Confidence")

        for pred in manual_required:
            wps = ", ".join(pred.conflicting_wps)
            table.add_row(pred.file_path, wps, pred.confidence)

        console.print("[yellow]May require manual resolution:[/yellow]")
        console.print(table)
        console.print()

    if auto_resolvable:
        table = Table(show_header=True, header_style="bold dim")
        table.add_column("Status File")
        table.add_column("WPs")

        for pred in auto_resolvable:
            wps = ", ".join(pred.conflicting_wps)
            table.add_row(pred.file_path, wps)

        console.print("[dim]Auto-resolvable (status files):[/dim]")
        console.print(table)
        console.print()

    # Summary guidance
    if manual_count == 0:
        console.print("[green]All conflicts can be auto-resolved.[/green]\n")
    else:
        console.print(
            f"[yellow]Prepare to resolve {manual_count} conflict(s) manually during merge.[/yellow]\n"
        )
