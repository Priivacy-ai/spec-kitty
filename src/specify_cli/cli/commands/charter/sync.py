"""``spec-kitty charter sync`` command (WP06 per-subcommand split)."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

import typer

from specify_cli.task_utils import TaskCliError

from specify_cli.cli.commands.charter._app import charter_app, console
from specify_cli.cli.commands.charter._common import _emit_error, _resolve_charter_path

# Test-patch shim — see ``synthesize.py``.
import specify_cli.cli.commands.charter as _charter_pkg

if TYPE_CHECKING:
    from charter.sync import SyncResult

__all__ = ["sync"]


def _sync_json_payload(result: SyncResult) -> dict[str, object]:
    """Return stable JSON output for ``charter sync``."""
    return {
        "result": "success" if result.synced else "noop",
        "success": result.synced,
        "stale_before": result.stale_before,
        "files_written": result.files_written,
        "extraction_mode": result.extraction_mode,
        "error": result.error,
        "warnings": result.warnings,
    }


def _emit_sync_human_result(result: SyncResult) -> None:
    """Render the non-JSON ``charter sync`` result."""
    if result.error:
        console.print(f"[red]Error:[/red] {result.error}")
        raise typer.Exit(code=1)

    if not result.synced:
        console.print("[blue]Charter already in sync[/blue] (use --force to re-extract)")
        return

    console.print("[green]Charter synced successfully[/green]")
    console.print(f"Mode: {result.extraction_mode}")
    if result.warnings:
        console.print("\nWarnings:")
        for warning in result.warnings:
            console.print(f"  ! {warning}")
    console.print("\nFiles written:")
    for filename in result.files_written:
        console.print(f"  ✓ {filename}")


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
            if result.error:
                _emit_error(console, json_output=True, message=str(result.error))
                raise typer.Exit(code=1)
            print(json.dumps(_sync_json_payload(result), indent=2))
            return

        _emit_sync_human_result(result)

    except typer.Exit:
        raise
    except TaskCliError as e:
        _emit_error(console, json_output=json_output, message=str(e))
        raise typer.Exit(code=1) from e
    except Exception as e:
        _emit_error(console, json_output=json_output, message=str(e), unexpected=True)
        raise typer.Exit(code=1) from e
