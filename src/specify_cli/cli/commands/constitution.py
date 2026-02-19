"""Constitution management commands."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from specify_cli.constitution.hasher import is_stale
from specify_cli.constitution.sync import sync as sync_constitution
from specify_cli.tasks_support import TaskCliError, find_repo_root

app = typer.Typer(
    name="constitution",
    help="Constitution management commands",
    no_args_is_help=True,
)

console = Console()


def _resolve_constitution_path(repo_root: Path) -> Path:
    """Find constitution.md in project, trying new and legacy locations.

    Args:
        repo_root: Repository root directory

    Returns:
        Path to constitution.md

    Raises:
        TaskCliError: If constitution.md not found
    """
    # Try new location first
    new_path = repo_root / ".kittify" / "constitution" / "constitution.md"
    if new_path.exists():
        return new_path

    # Fall back to legacy location
    legacy_path = repo_root / ".kittify" / "memory" / "constitution.md"
    if legacy_path.exists():
        return legacy_path

    raise TaskCliError(
        "Constitution not found. Expected:\n"
        f"  - {new_path}\n"
        f"  - {legacy_path} (legacy)"
    )


@app.command()
def sync(
    force: bool = typer.Option(
        False, "--force", "-f", help="Force sync even if not stale"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Sync constitution.md to structured YAML config files."""
    try:
        repo_root = find_repo_root()
        constitution_path = _resolve_constitution_path(repo_root)
        output_dir = constitution_path.parent

        result = sync_constitution(constitution_path, output_dir, force=force)

        if json_output:
            data = {
                "success": result.synced,
                "stale_before": result.stale_before,
                "files_written": result.files_written,
                "extraction_mode": result.extraction_mode,
                "error": result.error,
            }
            console.print(json.dumps(data, indent=2))
            return

        # Human-readable output
        if result.error:
            console.print(f"[red]❌ Error:[/red] {result.error}")
            raise typer.Exit(code=1)

        if result.synced:
            console.print("[green]✅ Constitution synced successfully[/green]")
            console.print(f"Mode: {result.extraction_mode}")
            console.print("\nFiles written:")
            for filename in result.files_written:
                console.print(f"  ✓ {filename}")
        else:
            console.print(
                "[blue]ℹ️  Constitution already in sync[/blue] "
                "(use --force to re-extract)"
            )

    except TaskCliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def status(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Display constitution sync status."""
    try:
        repo_root = find_repo_root()
        constitution_path = _resolve_constitution_path(repo_root)
        output_dir = constitution_path.parent
        metadata_path = output_dir / "metadata.yaml"

        # Check staleness
        stale, current_hash, stored_hash = is_stale(constitution_path, metadata_path)

        # Get file info
        files_info: list[dict[str, str | bool | float]] = []
        for filename in ["governance.yaml", "agents.yaml", "directives.yaml", "metadata.yaml"]:
            file_path = output_dir / filename
            if file_path.exists():
                size = file_path.stat().st_size
                size_kb = size / 1024
                files_info.append({"name": filename, "exists": True, "size_kb": size_kb})
            else:
                files_info.append({"name": filename, "exists": False, "size_kb": 0.0})

        # Get last sync timestamp from metadata
        last_sync = None
        if metadata_path.exists():
            from ruamel.yaml import YAML

            yaml = YAML()
            metadata = yaml.load(metadata_path)
            if metadata:
                last_sync = metadata.get("timestamp_utc")

        if json_output:
            data = {
                "constitution_path": str(constitution_path.relative_to(repo_root)),
                "status": "stale" if stale else "synced",
                "current_hash": current_hash,
                "stored_hash": stored_hash,
                "last_sync": last_sync,
                "files": files_info,
            }
            console.print(json.dumps(data, indent=2))
            return

        # Human-readable output
        console.print(f"Constitution: {constitution_path.relative_to(repo_root)}")

        if stale:
            console.print("Status: [yellow]⚠️  STALE[/yellow] (modified since last sync)")
            if stored_hash:
                console.print(f"Expected hash: {stored_hash}")
            console.print(f"Current hash:  {current_hash}")
            console.print("\n[dim]Run: spec-kitty constitution sync[/dim]")
        else:
            console.print("Status: [green]✅ SYNCED[/green]")
            if last_sync:
                console.print(f"Last sync: {last_sync}")
            console.print(f"Hash: {current_hash}")

        # File listing table
        console.print("\nExtracted files:")
        table = Table(show_header=True, header_style="bold")
        table.add_column("File", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Size", justify="right")

        for file_info in files_info:
            name = str(file_info["name"])
            exists = bool(file_info["exists"])
            size_kb = float(file_info["size_kb"])

            if exists:
                status_icon = "[green]✓[/green]"
                size_str = f"{size_kb:.1f} KB"
            else:
                status_icon = "[red]✗[/red]"
                size_str = "[dim]—[/dim]"

            table.add_row(name, status_icon, size_str)

        console.print(table)

    except TaskCliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1)
