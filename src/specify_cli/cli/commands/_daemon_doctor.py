"""Daemon health cluster for ``doctor`` (WP10, #2059).

Extracts Cluster I — ``orphan-daemons`` (orphan owner-record scan) and
``restart-daemon`` (four-state restart) — into a cohesive standalone module. The
@app.command shells stay in ``doctor.py`` (the ``add_typer`` target) and delegate
to :func:`run_orphan_daemons` / :func:`run_restart_daemon`.

The ``restart-daemon`` subcommand name is byte-preserved (I-7): the
``__init__`` ``_is_doctor_restart_daemon_invocation`` argv fast-path keys on it.

Import discipline (one-way, I-2): imports shared infra from
:mod:`._doctor_shared`; never imports the CLI ``doctor`` module. Daemon-domain
imports (``specify_cli.sync.*``) stay function-local per the existing pattern.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.table import Table

from ._doctor_shared import _STARTED_AT_COLUMN, console

__all__ = ["run_orphan_daemons", "run_restart_daemon"]


def _render_orphan_daemons_table(orphans: list[object], retire_hint: str) -> None:
    """Render the orphan daemon records table + retirement hint (human output)."""
    console.print(f"\n[bold]Orphan Daemons[/bold] — {len(orphans)} record(s)\n")
    table = Table(box=None, padding=(0, 2), show_edge=False)
    table.add_column("PID", style="yellow", justify="right", min_width=6)
    table.add_column("Port", justify="right", min_width=6)
    table.add_column("Version", min_width=10)
    table.add_column("Executable", overflow="fold")
    table.add_column(_STARTED_AT_COLUMN, min_width=20)
    for record in orphans:
        table.add_row(
            str(record.pid),  # type: ignore[attr-defined]
            str(record.port),  # type: ignore[attr-defined]
            record.package_version,  # type: ignore[attr-defined]
            record.executable_path,  # type: ignore[attr-defined]
            record.started_at,  # type: ignore[attr-defined]
        )
    console.print(table)
    console.print()
    console.print(f"[bold]Retirement hint:[/bold] [cyan]{retire_hint}[/cyan]")
    console.print()


def run_orphan_daemons(json_output: bool) -> None:
    """Entry point for ``doctor orphan-daemons`` (0 no-orphans / 1 orphans)."""
    from specify_cli.sync.owner import list_orphan_records, owner_record_path

    orphans = list_orphan_records()
    record_path = owner_record_path()
    retire_hint = f"rm {record_path}"

    if json_output:
        payload = {
            "orphan_count": len(orphans),
            "owner_record_path": str(record_path),
            "retirement_command": retire_hint if orphans else None,
            "orphans": [
                {
                    "pid": r.pid,
                    "port": r.port,
                    "package_version": r.package_version,
                    "executable_path": r.executable_path,
                    "source_checkout_path": r.source_checkout_path,
                    "server_url": r.server_url,
                    "auth_scope": r.auth_scope,
                    "queue_db_path": r.queue_db_path,
                    "started_at": r.started_at,
                }
                for r in orphans
            ],
        }
        console.print_json(json.dumps(payload, indent=2, sort_keys=True))
        raise typer.Exit(1 if orphans else 0)

    if not orphans:
        console.print(
            "[green]Orphan Daemons[/green]: no orphan daemon owner records detected."
        )
        raise typer.Exit(0)

    _render_orphan_daemons_table(orphans, retire_hint)
    raise typer.Exit(1)


def run_restart_daemon(json_output: bool) -> None:
    """Entry point for ``doctor restart-daemon`` (four-state 0/1/2/3 contract)."""
    from specify_cli.core.paths import locate_project_root
    from specify_cli.sync.restart import render_restart_result, restart_daemon

    # ``repo_root`` is accepted by ``restart_daemon`` for API symmetry with the
    # rest of the preflight surface; the function does not currently consult the
    # repo for any field. We resolve it best-effort so a future refactor that
    # reads repo-relative state picks it up automatically without a CLI change.
    repo_root: Path
    try:
        located = locate_project_root()
    except Exception:  # noqa: BLE001 — restart never needs a repo today
        located = None
    repo_root = located if located is not None else Path.cwd()

    result = restart_daemon(repo_root)
    output = render_restart_result(result, json_output=json_output)
    # Use stdout directly so ``--json`` emits one line, no Rich markup.
    sys.stdout.write(output + "\n")
    sys.stdout.flush()
    raise typer.Exit(code=result.exit_code)
