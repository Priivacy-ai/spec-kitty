"""Task metadata validation command for Spec Kitty CLI."""

from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from specify_cli.acceptance import AcceptanceError, detect_mission_slug
from specify_cli.cli.helpers import check_version_compatibility, console, get_project_root_or_exit
from specify_cli.core.project_resolver import resolve_worktree_aware_mission_dir
from specify_cli.task_metadata_validation import (
    repair_lane_mismatch,
    scan_all_tasks_for_mismatches,
)
from specify_cli.tasks_support import TaskCliError, find_repo_root


def validate_tasks(
    mission: str | None = typer.Option(None, "--mission", help="Mission slug to validate (auto-detected when omitted)"),
    fix: bool = typer.Option(False, "--fix", help="Automatically repair metadata inconsistencies"),
    check_all: bool = typer.Option(False, "--all", help="Check all missions, not just one"),
    agent: str | None = typer.Option(None, "--agent", help="Agent name for activity log"),
    shell_pid: str | None = typer.Option(None, "--shell-pid", help="Shell PID for activity log"),
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
    check_version_compatibility(project_root, "validate-tasks")

    # Get agent and shell_pid from environment if not provided
    if not agent:
        agent = os.environ.get("SPEC_KITTY_AGENT", "system")
    if not shell_pid:
        shell_pid = str(os.getpid())

    if check_all:
        # Validate all missions
        kitty_specs = repo_root / "kitty-specs"
        worktrees = repo_root / ".worktrees"

        mission_dirs = []
        if kitty_specs.exists():
            mission_dirs.extend([d for d in kitty_specs.iterdir() if d.is_dir()])
        if worktrees.exists():
            for wt_dir in worktrees.iterdir():
                if wt_dir.is_dir():
                    wt_specs = wt_dir / "kitty-specs"
                    if wt_specs.exists():
                        mission_dirs.extend([d for d in wt_specs.iterdir() if d.is_dir()])

        if not mission_dirs:
            console.print("[yellow]No mission directories found.[/yellow]")
            raise typer.Exit(0)

        console.print(f"[cyan]Checking task metadata for {len(mission_dirs)} missions...[/cyan]")
        console.print()

        total_mismatches = 0
        total_fixed = 0

        for mission_dir in sorted(mission_dirs, key=lambda d: d.name):
            mismatches, fixed = _validate_mission_tasks(mission_dir, fix=fix, agent=agent, shell_pid=shell_pid)
            total_mismatches += mismatches
            total_fixed += fixed

        console.print()
        console.print(
            Panel(
                f"[bold]Summary:[/bold]\nTotal mismatches found: [yellow]{total_mismatches}[/yellow]\nTotal mismatches fixed: [green]{total_fixed}[/green]",
                title="Task Metadata Validation Complete",
                border_style="cyan" if total_mismatches == 0 else "yellow",
            )
        )

        raise typer.Exit(0 if total_mismatches == 0 or fix else 1)

    # Validate single mission
    try:
        mission_slug = (mission or detect_mission_slug(repo_root, cwd=Path.cwd())).strip()
    except AcceptanceError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    mission_dir = resolve_worktree_aware_mission_dir(repo_root, mission_slug, Path.cwd(), console)

    if not mission_dir.exists():
        console.print(f"[red]Error:[/red] Mission directory not found: {mission_dir}")
        raise typer.Exit(1)

    console.print(f"[cyan]Validating task metadata for mission:[/cyan] {mission_slug}")
    console.print()

    mismatches, fixed = _validate_mission_tasks(mission_dir, fix=fix, agent=agent, shell_pid=shell_pid)

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


def _validate_mission_tasks(mission_dir: Path, *, fix: bool, agent: str, shell_pid: str) -> tuple[int, int]:
    """Validate task metadata for a single mission directory.

    Returns:
        Tuple of (mismatches_found, mismatches_fixed)
    """
    console.print(f"[cyan]Checking:[/cyan] {mission_dir.name}")

    mismatches_dict = scan_all_tasks_for_mismatches(mission_dir)

    if not mismatches_dict:
        console.print("  [green]✓[/green] No metadata mismatches")
        return 0, 0

    # Display mismatches in a table
    table = Table(title=f"Task Metadata Mismatches: {mission_dir.name}", show_header=True)
    table.add_column("File", style="cyan")
    table.add_column("Expected Lane", style="green")
    table.add_column("Actual Lane", style="yellow")
    table.add_column("Status", style="white")

    fixed_count = 0
    for file_path, (_, expected, actual) in mismatches_dict.items():
        full_path = mission_dir / file_path

        status = "[yellow]Needs Fix[/yellow]"
        if fix:
            was_repaired, error = repair_lane_mismatch(full_path, agent=agent, shell_pid=shell_pid, add_history=True, dry_run=False)
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
