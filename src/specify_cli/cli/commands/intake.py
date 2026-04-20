"""``spec-kitty intake`` command — ingest a plan document as a mission brief."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from specify_cli.mission_brief import (
    MISSION_BRIEF_FILENAME,
    read_brief_source,
    read_mission_brief,
    write_mission_brief,
)

console = Console()
err_console = Console(stderr=True)


def intake(
    path: Optional[str] = typer.Argument(
        None,
        help="Path to plan document, or '-' to read from stdin. Omit when using --show.",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing brief."),
    show: bool = typer.Option(False, "--show", help="Print current brief and provenance; no writes."),
) -> None:
    """Ingest a plan document as a mission brief for /spec-kitty.specify."""
    repo_root = Path.cwd()

    # --show branch: print and exit, no writes
    if show:
        brief = read_mission_brief(repo_root)
        source = read_brief_source(repo_root)
        if brief is None and source is None:
            err_console.print("[red]No brief found at .kittify/mission-brief.md[/red]")
            raise typer.Exit(1)
        if source is not None:
            console.print(
                f"[bold]Source:[/bold] {source.get('source_file', '')} "
                f"  [bold]Ingested:[/bold] {source.get('ingested_at', '')} "
                f"  [bold]Hash:[/bold] {source.get('brief_hash', '')[:16]}..."
            )
        if brief is not None:
            console.print(brief)
        return

    # No path and no --show: print usage hint and exit 1
    if path is None:
        err_console.print("[red]Provide a file path, '-' for stdin, or --show[/red]")
        raise typer.Exit(1)

    # Normal write branch
    brief_path = repo_root / ".kittify" / MISSION_BRIEF_FILENAME
    if brief_path.exists() and not force:
        err_console.print(
            "Brief already exists at .kittify/mission-brief.md. Use --force to overwrite."
        )
        raise typer.Exit(1)

    # Read content from file or stdin
    if path == "-":
        content = sys.stdin.read()
        source_file = "stdin"
    else:
        try:
            content = Path(path).read_text(encoding="utf-8")
            source_file = path
        except FileNotFoundError:
            err_console.print(f"[red]File not found: {path}[/red]")
            raise typer.Exit(1)
        except OSError as exc:
            err_console.print(f"[red]Could not read file: {exc}[/red]")
            raise typer.Exit(1)

    write_mission_brief(repo_root, content, source_file)
    console.print("[green]\u2713[/green] Brief written to .kittify/mission-brief.md")
    console.print("[green]\u2713[/green] Provenance written to .kittify/brief-source.yaml")
