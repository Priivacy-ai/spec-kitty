"""Upgrade command implementation for Spec Kitty CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel
from rich.table import Table

from specify_cli.cli.helpers import console, show_banner


def upgrade(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview changes without applying"
    ),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompts"),
    target: Optional[str] = typer.Option(
        None, "--target", help="Target version (defaults to current CLI version)"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed migration information"
    ),
    no_worktrees: bool = typer.Option(
        False, "--no-worktrees", help="Skip upgrading worktrees"
    ),
) -> None:
    """Upgrade a Spec Kitty project to the current version.

    Detects the project's current version and applies all necessary migrations
    to bring it up to date with the installed CLI version.

    Examples:
        spec-kitty upgrade              # Upgrade to current version
        spec-kitty upgrade --dry-run    # Preview changes
        spec-kitty upgrade --target 0.6.5  # Upgrade to specific version
    """
    if not json_output:
        show_banner()

    project_path = Path.cwd()
    kittify_dir = project_path / ".kittify"
    specify_dir = project_path / ".specify"  # Old name

    # Check if this is a Spec Kitty project
    if not kittify_dir.exists() and not specify_dir.exists():
        if json_output:
            console.print(json.dumps({"error": "Not a Spec Kitty project"}))
        else:
            console.print("[red]Error:[/red] Not a Spec Kitty project.")
            console.print(
                "[dim]Run 'spec-kitty init' to initialize a project.[/dim]"
            )
        raise typer.Exit(1)

    # Import upgrade system (lazy to avoid circular imports)
    from specify_cli.upgrade.detector import VersionDetector
    from specify_cli.upgrade.registry import MigrationRegistry
    from specify_cli.upgrade.runner import MigrationRunner

    # Import migrations to register them
    from specify_cli.upgrade import migrations  # noqa: F401

    # Detect current version
    detector = VersionDetector(project_path)
    current_version = detector.detect_version()

    # Determine target version
    if target is None:
        from specify_cli import __version__

        target_version = __version__
    else:
        target_version = target

    if not json_output:
        console.print(f"[cyan]Current version:[/cyan] {current_version}")
        console.print(f"[cyan]Target version:[/cyan]  {target_version}")
        console.print()

    # Get needed migrations
    migrations_needed = MigrationRegistry.get_applicable(current_version, target_version)

    if not migrations_needed:
        if json_output:
            console.print(
                json.dumps(
                    {
                        "status": "up_to_date",
                        "current_version": current_version,
                        "target_version": target_version,
                    }
                )
            )
        else:
            console.print("[green]Project is already up to date![/green]")
        return

    # Show migration plan
    if not json_output:
        table = Table(
            title="Migration Plan", show_lines=False, header_style="bold cyan"
        )
        table.add_column("Migration", style="bright_white")
        table.add_column("Description", style="dim")
        table.add_column("Target", style="cyan")

        for migration in migrations_needed:
            table.add_row(
                migration.migration_id,
                migration.description,
                migration.target_version,
            )

        console.print(table)
        console.print()

        if verbose:
            # Show detection results
            console.print("[dim]Detection results:[/dim]")
            for migration in migrations_needed:
                detected = migration.detect(project_path)
                can_apply, reason = migration.can_apply(project_path)
                status = "[green]ready[/green]" if detected and can_apply else "[yellow]skipped[/yellow]"
                console.print(f"  {migration.migration_id}: {status}")
                if not can_apply and reason:
                    console.print(f"    [dim]{reason}[/dim]")
            console.print()

    # Confirm if not dry-run and not forced
    if not dry_run and not force:
        proceed = typer.confirm(
            f"Apply {len(migrations_needed)} migration(s)?",
            default=True,
        )
        if not proceed:
            console.print("[yellow]Upgrade cancelled.[/yellow]")
            raise typer.Exit(0)

    # Run migrations
    runner = MigrationRunner(project_path, console)
    result = runner.upgrade(
        target_version,
        dry_run=dry_run,
        force=force,
        include_worktrees=not no_worktrees,
    )

    if json_output:
        # Build detailed migrations array
        migrations_detail = []
        for migration in migrations_needed:
            status = "applied" if migration.migration_id in result.migrations_applied else (
                "skipped" if migration.migration_id in result.migrations_skipped else "pending"
            )
            migrations_detail.append({
                "id": migration.migration_id,
                "description": migration.description,
                "target_version": migration.target_version,
                "status": status,
            })

        output = {
            "status": "success" if result.success else "failed",
            "current_version": result.from_version,
            "target_version": result.to_version,
            "dry_run": result.dry_run,
            "migrations": migrations_detail,
            "migrations_applied": result.migrations_applied,
            "migrations_skipped": result.migrations_skipped,
            "success": result.success,
            "errors": result.errors,
            "warnings": result.warnings,
        }
        console.print(json.dumps(output, indent=2))
        return

    # Display results
    console.print()

    if result.dry_run:
        console.print(
            Panel(
                "[yellow]DRY RUN[/yellow] - No changes were made",
                border_style="yellow",
            )
        )

    if result.migrations_applied:
        console.print("[green]Migrations applied:[/green]")
        for m in result.migrations_applied:
            console.print(f"  [green]✓[/green] {m}")

    if result.migrations_skipped:
        console.print("[dim]Migrations skipped (already applied or not needed):[/dim]")
        for m in result.migrations_skipped:
            console.print(f"  [dim]○[/dim] {m}")

    if result.warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for w in result.warnings:
            console.print(f"  [yellow]![/yellow] {w}")

    if result.errors:
        console.print("[red]Errors:[/red]")
        for e in result.errors:
            console.print(f"  [red]✗[/red] {e}")

    console.print()
    if result.success:
        console.print(
            f"[bold green]Upgrade complete![/bold green] {result.from_version} -> {result.to_version}"
        )
    else:
        console.print("[bold red]Upgrade failed.[/bold red]")
        raise typer.Exit(1)


__all__ = ["upgrade"]
