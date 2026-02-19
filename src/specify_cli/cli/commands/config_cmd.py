"""Top-level ``spec-kitty config`` command.

Provides the ``--show-origin`` flag (FR-013) to display where each
resolved asset comes from in the 4-tier resolution chain.
"""

from __future__ import annotations


import typer
from rich.console import Console
from rich.table import Table

from specify_cli.tasks_support import find_repo_root

console = Console()


def config(
    show_origin: bool = typer.Option(
        False,
        "--show-origin",
        help="Show where each resolved asset comes from (tier label + path)",
    ),
    mission: str = typer.Option(
        "software-dev",
        "--mission",
        "-m",
        help="Mission to resolve assets for",
    ),
) -> None:
    """Display project configuration and asset resolution information."""
    if not show_origin:
        console.print(
            "[yellow]Use --show-origin to display asset resolution details.[/yellow]"
        )
        raise typer.Exit(0)

    try:
        repo_root = find_repo_root()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    from specify_cli.runtime.show_origin import collect_origins

    entries = collect_origins(repo_root, mission=mission)

    # Build a rich table
    table = Table(title="Asset Resolution Origins", show_lines=True)
    table.add_column("Type", style="cyan", width=10)
    table.add_column("Name", style="bold")
    table.add_column("Tier", style="magenta")
    table.add_column("Resolved Path")

    for entry in entries:
        if entry.resolved_path is not None:
            tier_display = _format_tier(entry.tier)
            # Show path relative to repo root if possible
            try:
                rel_path = entry.resolved_path.relative_to(repo_root)
                path_display = str(rel_path)
            except ValueError:
                path_display = str(entry.resolved_path)
            table.add_row(
                entry.asset_type.title(),
                entry.name,
                tier_display,
                path_display,
            )
        else:
            table.add_row(
                entry.asset_type.title(),
                entry.name,
                "[red]not found[/red]",
                f"[dim]{entry.error}[/dim]" if entry.error else "",
            )

    console.print(table)

    # Check for version pin
    from specify_cli.runtime.bootstrap import check_version_pin

    check_version_pin(repo_root)


def _format_tier(tier: str | None) -> str:
    """Format a tier label for display with color coding."""
    if tier is None:
        return "[red]not found[/red]"
    colors = {
        "override": "green",
        "legacy": "yellow",
        "global": "blue",
        "project": "bright_cyan",
        "package_default": "dim",
    }
    color = colors.get(tier, "white")
    return f"[{color}]{tier}[/{color}]"
