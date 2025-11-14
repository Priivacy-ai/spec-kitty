"""Task metadata validation command for Spec Kitty CLI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel
from rich.table import Table

from specify_cli.acceptance import AcceptanceError, detect_feature_slug
from specify_cli.cli.helpers import console, get_project_root_or_exit
from specify_cli.core.project_resolver import resolve_worktree_aware_feature_dir
from specify_cli.task_metadata_validation import (
    detect_lane_mismatch,
    repair_lane_mismatch,
    scan_all_tasks_for_mismatches,
    validate_task_metadata,
)
from specify_cli.tasks_support import TaskCliError, find_repo_root


def validate_tasks(
    feature: Optional[str] = typer.Option(
        None, "--feature", help="Feature slug to validate (auto-detected when omitted)"
    ),
    fix: bool = typer.Option(False, "--fix", help="Automatically repair metadata inconsistencies"),
    check_all: bool = typer.Option(False, "--all", help="Check all features, not just one"),
    agent: Optional[str] = typer.Option(None, "--agent", help="Agent name for activity log"),
    shell_pid: Optional[str] = typer.Option(None, "--shell-pid", help="Shell PID for activity log"),
) -> None:
    """Validate and optionally fix task metadata inconsistencies.

    Detects when work package frontmatter doesn't match file location:
    - File in tasks/for_review/ but lane: "planned" in frontmatter
    - File in tasks/doing/ but lane: "done" in frontmatter
    - etc.

    Can automatically fix by updating frontmatter to match directory.
    """
    try:
        repo_root = find_repo_root()
    except TaskCliError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    project_root = get_project_root_or_exit(repo_root)

    # Get agent and shell_pid from environment if not provided
    if not agent:
        agent = os.environ.get("SPEC_KITTY_AGENT", "system")
    if not shell_pid:
        shell_pid = str(os.getpid())

    if check_all:
        # Validate all features
        kitty_specs = repo_root / "kitty-specs"
        worktrees = repo_root / ".worktrees"

        feature_dirs = []
        if kitty_specs.exists():
            feature_dirs.extend([d for d in kitty_specs.iterdir() if d.is_dir()])
        if worktrees.exists():
            for wt_dir in worktrees.iterdir():
                if wt_dir.is_dir():
                    wt_specs = wt_dir / "kitty-specs"
                    if wt_specs.exists():
                        feature_dirs.extend([d for d in wt_specs.iterdir() if d.is_dir()])

        if not feature_dirs:
            console.print("[yellow]No feature directories found.[/yellow]")
            raise typer.Exit(0)

        console.print(f"[cyan]Checking task metadata for {len(feature_dirs)} features...[/cyan]")
        console.print()

        total_mismatches = 0
        total_fixed = 0

        for feature_dir in sorted(feature_dirs, key=lambda d: d.name):
            mismatches, fixed = _validate_feature_tasks(
                feature_dir, fix=fix, agent=agent, shell_pid=shell_pid
            )
            total_mismatches += mismatches
            total_fixed += fixed

        console.print()
        console.print(
            Panel(
                f"[bold]Summary:[/bold]\n"
                f"Total mismatches found: [yellow]{total_mismatches}[/yellow]\n"
                f"Total mismatches fixed: [green]{total_fixed}[/green]",
                title="Task Metadata Validation Complete",
                border_style="cyan" if total_mismatches == 0 else "yellow",
            )
        )

        raise typer.Exit(0 if total_mismatches == 0 or fix else 1)

    # Validate single feature
    try:
        feature_slug = (feature or detect_feature_slug(repo_root, cwd=Path.cwd())).strip()
    except AcceptanceError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    feature_dir = resolve_worktree_aware_feature_dir(repo_root, feature_slug, Path.cwd(), console)

    if not feature_dir.exists():
        console.print(f"[red]Error:[/red] Feature directory not found: {feature_dir}")
        raise typer.Exit(1)

    console.print(f"[cyan]Validating task metadata for feature:[/cyan] {feature_slug}")
    console.print()

    mismatches, fixed = _validate_feature_tasks(
        feature_dir, fix=fix, agent=agent, shell_pid=shell_pid
    )

    if mismatches == 0:
        console.print("[green]✓ All task metadata is consistent![/green]")
        raise typer.Exit(0)
    elif fix and fixed > 0:
        console.print()
        console.print(f"[green]✓ Fixed {fixed} metadata mismatch(es).[/green]")
        raise typer.Exit(0)
    else:
        console.print()
        console.print(f"[yellow]Found {mismatches} metadata mismatch(es).[/yellow]")
        console.print("[dim]Run with --fix to automatically repair these mismatches.[/dim]")
        raise typer.Exit(1)


def _validate_feature_tasks(
    feature_dir: Path, *, fix: bool, agent: str, shell_pid: str
) -> tuple[int, int]:
    """Validate task metadata for a single feature directory.

    Returns:
        Tuple of (mismatches_found, mismatches_fixed)
    """
    console.print(f"[cyan]Checking:[/cyan] {feature_dir.name}")

    mismatches_dict = scan_all_tasks_for_mismatches(feature_dir)

    if not mismatches_dict:
        console.print(f"  [green]✓[/green] No metadata mismatches")
        return 0, 0

    # Display mismatches in a table
    table = Table(title=f"Task Metadata Mismatches: {feature_dir.name}", show_header=True)
    table.add_column("File", style="cyan")
    table.add_column("Expected Lane", style="green")
    table.add_column("Actual Lane", style="yellow")
    table.add_column("Status", style="white")

    fixed_count = 0
    for file_path, (_, expected, actual) in mismatches_dict.items():
        full_path = feature_dir / file_path

        status = "[yellow]Needs Fix[/yellow]"
        if fix:
            was_repaired, error = repair_lane_mismatch(
                full_path, agent=agent, shell_pid=shell_pid, add_history=True, dry_run=False
            )
            if was_repaired:
                status = "[green]Fixed[/green]"
                fixed_count += 1
            elif error:
                status = f"[red]Error: {error}[/red]"

        table.add_row(file_path, expected or "?", actual or "?", status)

    console.print(table)

    if fix:
        console.print()
        console.print(f"  [green]Fixed {fixed_count} of {len(mismatches_dict)} mismatches[/green]")

    return len(mismatches_dict), fixed_count


__all__ = ["validate_tasks"]
