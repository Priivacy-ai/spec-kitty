"""Shared utility for resolving --mission-type flag ambiguity."""

from __future__ import annotations

import typer


def resolve_mission_type(
    mission_type: str | None,
    mission: str | None,
) -> str | None:
    """Resolve --mission-type (canonical) vs --mission (removed alias for type selection).

    Returns mission_type if set; raises a hard error if the removed --mission alias is used
    (to surface any missed call sites quickly); returns None if neither set.
    """
    if mission_type is not None:
        return mission_type
    if mission is not None:
        typer.echo(
            "Error: --mission is no longer accepted for mission-type selection. Use --mission-type instead (e.g., --mission-type software-dev).",
            err=True,
        )
        raise typer.Exit(code=1)
    return None
