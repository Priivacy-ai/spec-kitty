"""Repair command to fix broken templates and diagnose worktrees."""

import typer
from pathlib import Path
from rich.console import Console
from typing import Optional

from specify_cli.upgrade.migrations.m_0_10_9_repair_templates import RepairTemplatesMigration
from specify_cli.core.paths import locate_project_root, get_main_repo_root, is_worktree_context

app = typer.Typer()
console = Console()


@app.command()
def repair(
    project_path: Path = typer.Option(
        Path.cwd(),
        "--project-path",
        "-p",
        help="Path to project to repair"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be changed without making changes"
    )
):
    """Repair broken templates caused by v0.10.0-0.10.8 bundling bug.

    This command fixes templates that reference non-existent bash scripts
    by regenerating them from the correct source. Run this if you see errors
    like "scripts/bash/check-prerequisites.sh: No such file or directory".
    """
    console.print("[bold]Spec Kitty Template Repair[/bold]")
    console.print()

    migration = RepairTemplatesMigration()

    # Detect if repair needed
    needs_repair = migration.detect(project_path)

    if not needs_repair:
        console.print("[green]✓ No broken templates detected - project is healthy![/green]")
        return

    console.print("[yellow]⚠ Broken templates detected[/yellow]")
    console.print("Found bash script references in slash commands")
    console.print()

    if dry_run:
        console.print("[cyan]Dry run mode - showing what would be changed:[/cyan]")

    # Apply repair
    result = migration.apply(project_path, dry_run=dry_run)

    if result.success:
        console.print()
        console.print("[green]✓ Repair completed successfully[/green]")
        for change in result.changes_made:
            console.print(f"  • {change}")
    else:
        console.print()
        console.print("[red]✗ Repair failed[/red]")
        for error in result.errors:
            console.print(f"  • [red]{error}[/red]")

    if result.warnings:
        console.print()
        console.print("[yellow]Warnings:[/yellow]")
        for warning in result.warnings:
            console.print(f"  • {warning}")


@app.command(name="worktree")
def repair_worktree(
    all_worktrees: bool = typer.Option(
        False,
        "--all",
        help="Check all worktrees in .worktrees/ directory"
    ),
    worktree_path: Optional[Path] = typer.Argument(
        None,
        help="Specific worktree path to check (defaults to current directory if in a worktree)"
    ),
):
    """Diagnose worktree kitty-specs/ status.

    This command checks if worktrees have kitty-specs/ directories and explains
    how WP operations work:

    - WP lane changes (move-task) ALWAYS use main repo's kitty-specs/
    - Research artifacts can be added to worktree's kitty-specs/
    - Stale WP files in worktrees don't affect lane operations

    Examples:
        spec-kitty repair worktree           # Check current worktree
        spec-kitty repair worktree --all     # Check all worktrees
    """
    console.print("[bold]Spec Kitty Worktree Diagnostics[/bold]")
    console.print()

    # Find project root
    cwd = Path.cwd().resolve()
    repo_root = locate_project_root(cwd)

    if repo_root is None:
        console.print("[red]Error:[/red] Could not locate project root")
        raise typer.Exit(1)

    main_root = get_main_repo_root(repo_root)

    worktrees_to_check: list[Path] = []

    if all_worktrees:
        # Check all worktrees in .worktrees/
        worktrees_dir = main_root / ".worktrees"
        if worktrees_dir.exists():
            for item in worktrees_dir.iterdir():
                if item.is_dir() and (item / ".git").exists():
                    worktrees_to_check.append(item)
        if not worktrees_to_check:
            console.print("[yellow]No worktrees found in .worktrees/[/yellow]")
            return
    elif worktree_path:
        # Use specified path
        worktree_path = worktree_path.resolve()
        if not worktree_path.exists():
            console.print(f"[red]Error:[/red] Worktree path does not exist: {worktree_path}")
            raise typer.Exit(1)
        worktrees_to_check.append(worktree_path)
    else:
        # Try current directory
        if is_worktree_context(cwd):
            # Find the worktree root
            current = cwd
            while current != current.parent:
                if (current / ".git").exists():
                    worktrees_to_check.append(current)
                    break
                current = current.parent
            if not worktrees_to_check:
                console.print("[red]Error:[/red] Could not find worktree root")
                raise typer.Exit(1)
        else:
            console.print("[yellow]Not in a worktree. Use --all to check all worktrees.[/yellow]")
            return

    console.print(f"Found {len(worktrees_to_check)} worktree(s) to check")
    console.print()

    for wt_path in worktrees_to_check:
        has_kitty_specs = (wt_path / "kitty-specs").exists()
        has_tasks = (wt_path / "kitty-specs").exists() and any(
            (wt_path / "kitty-specs").rglob("tasks/*.md")
        )

        console.print(f"[bold]{wt_path.name}[/bold]")

        if not has_kitty_specs:
            console.print("  [dim]No kitty-specs/ directory[/dim]")
        else:
            console.print(f"  kitty-specs/: [green]present[/green]")
            if has_tasks:
                console.print(f"  tasks/*.md: [yellow]present (stale copies)[/yellow]")
            else:
                console.print(f"  tasks/*.md: [dim]none[/dim]")

    console.print()
    console.print("[bold cyan]How WP operations work:[/bold cyan]")
    console.print("  • [green]move-task[/green] always updates [bold]main repo's[/bold] kitty-specs/")
    console.print("  • Research artifacts can be added to worktree's kitty-specs/")
    console.print("  • Stale WP files in worktrees are [dim]ignored[/dim] by lane operations")
    console.print()
    console.print("[dim]No repair needed - this is informational only.[/dim]")
