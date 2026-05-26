"""``spec-kitty charter sync`` command (WP06 per-subcommand split)."""
from __future__ import annotations

import json

import typer

from specify_cli.task_utils import TaskCliError

from specify_cli.cli.commands.charter._app import charter_app, console
from specify_cli.cli.commands.charter._common import _resolve_charter_path

# Test-patch shim — see ``synthesize.py``.
import specify_cli.cli.commands.charter as _charter_pkg

__all__ = ["sync"]


@charter_app.command()
def sync(
    force: bool = typer.Option(False, "--force", "-f", help="Force sync even if not stale"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Sync charter.md to structured YAML config files."""
    from charter.sync import sync as sync_charter

    try:
        repo_root = _charter_pkg.find_repo_root()
        charter_path = _resolve_charter_path(repo_root)
        output_dir = charter_path.parent

        result = sync_charter(charter_path, output_dir, force=force)

        if json_output:
            data = {
                "result": "success" if result.synced else "noop",
                "success": result.synced,
                "stale_before": result.stale_before,
                "files_written": result.files_written,
                "extraction_mode": result.extraction_mode,
                "error": result.error,
            }
            print(json.dumps(data, indent=2))
            return

        if result.error:
            console.print(f"[red]Error:[/red] {result.error}")
            raise typer.Exit(code=1)

        if result.synced:
            console.print("[green]Charter synced successfully[/green]")
            console.print(f"Mode: {result.extraction_mode}")
            console.print("\nFiles written:")
            for filename in result.files_written:
                console.print(f"  ✓ {filename}")
        else:
            console.print("[blue]Charter already in sync[/blue] (use --force to re-extract)")

    except TaskCliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(code=1) from e
