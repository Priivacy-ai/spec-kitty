"""Hidden git merge-driver entrypoints for Spec Kitty repositories."""

from __future__ import annotations

from pathlib import Path

import typer

from specify_cli.status.event_log_merge import EventLogMergeError, merge_event_log_files


def merge_driver_event_log(
    base_path: str = typer.Argument(..., metavar="BASE"),
    ours_path: str = typer.Argument(..., metavar="OURS"),
    theirs_path: str = typer.Argument(..., metavar="THEIRS"),
) -> None:
    """Merge ``status.events.jsonl`` conflict inputs using event-log semantics."""
    try:
        merge_event_log_files(
            base_path=Path(base_path),
            ours_path=Path(ours_path),
            theirs_path=Path(theirs_path),
        )
    except EventLogMergeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
