"""Repair command to fix broken templates."""

import typer
from pathlib import Path
from rich.console import Console

from specify_cli.upgrade.migrations.m_0_10_9_repair_templates import RepairTemplatesMigration

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
