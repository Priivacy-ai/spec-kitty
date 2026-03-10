"""CLI command for migrating per-project .kittify/ to centralized model.

Usage:
    spec-kitty migrate              # Migrate with confirmation
    spec-kitty migrate --dry-run    # Preview changes without modifying
    spec-kitty migrate --force      # Skip confirmation prompt
    spec-kitty migrate --verbose    # Show file-by-file detail

The migrate command performs two operations:

1. **Global runtime install** -- ensures ``~/.kittify/`` is populated with
   up-to-date package assets (idempotent; uses ``ensure_runtime()``).
2. **Per-project cleanup** -- classifies per-project ``.kittify/`` files as
   identical (removed), customized (moved to overrides/), or project-specific
   (kept).

After a successful migration, legacy-tier warnings are fully suppressed
during normal template resolution.
"""

from __future__ import annotations

import typer
from rich.console import Console

from specify_cli.core.paths import locate_project_root
from specify_cli.runtime.bootstrap import ensure_runtime
from specify_cli.runtime.migrate import execute_migration

console = Console()


def migrate(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change without modifying the filesystem"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show file-by-file detail"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt"),
) -> None:
    """Migrate project .kittify/ to centralized model.

    First ensures the global runtime (~/.kittify/) is up to date, then
    classifies per-project files as identical (removed), customized
    (moved to overrides/), or project-specific (kept). Use --dry-run
    to preview changes before applying.

    Running this command multiple times is safe (idempotent). After the
    first successful run, subsequent invocations are a near-instant no-op.

    Examples:
        spec-kitty migrate --dry-run    # Preview
        spec-kitty migrate --force      # Apply without confirmation
    """
    project_dir = locate_project_root()
    if project_dir is None:
        console.print("[red]Could not locate project root. No .kittify/ directory found in any parent directory.[/red]")
        raise typer.Exit(1)

    if not (project_dir / ".kittify").exists():
        console.print("[red]No .kittify/ directory found in current project.[/red]")
        raise typer.Exit(1)

    if not dry_run and not force:
        confirmed = typer.confirm("Migrate .kittify/ to centralized model?")
        if not confirmed:
            raise typer.Abort()

    # Step 1: Ensure global runtime is installed and current.
    # This is idempotent -- fast-path returns immediately if version matches.
    if dry_run:
        console.print("[bold]Step 1:[/bold] Global runtime check (no changes in dry-run)")
    else:
        console.print("[bold]Step 1:[/bold] Ensuring global runtime (~/.kittify/) is up to date...")
        ensure_runtime()
        console.print("  [green]Global runtime is current.[/green]")

    # Step 2: Per-project migration.
    console.print("[bold]Step 2:[/bold] Per-project .kittify/ cleanup...")
    report = execute_migration(project_dir, dry_run=dry_run, verbose=verbose)

    # Display results
    if dry_run:
        console.print("[bold]Dry run -- no changes made[/bold]")

    action_removed = "would remove" if dry_run else "removed"
    action_moved = "would move" if dry_run else "moved"

    console.print(f"  {len(report.removed)} files identical to global -- {action_removed}")
    console.print(f"  {len(report.moved)} files customized -- {action_moved} to overrides/")
    console.print(f"  {len(report.kept)} files project-specific -- kept")

    if report.unknown:
        console.print(f"  [yellow]{len(report.unknown)} files unknown -- kept with warning[/yellow]")

    if verbose:
        for path in report.removed:
            console.print(f"    [dim]removed: {path}[/dim]")
        for src, dst in report.moved:
            console.print(f"    [blue]moved: {src} -> {dst}[/blue]")
        for path in report.kept:
            console.print(f"    [green]kept: {path}[/green]")
        for path in report.unknown:
            console.print(f"    [yellow]unknown: {path}[/yellow]")

    if not dry_run:
        console.print(
            "\n[green]Migration complete.[/green] Zero legacy warnings expected. "
            "Run `spec-kitty config --show-origin` to verify resolution tiers."
        )

    # Credential path decision: ~/.spec-kitty/credentials stays separate.
    # This is a security boundary decision -- credentials have a different
    # lifecycle and permission model from runtime assets.  Documented here
    # per WP08 acceptance criteria.
