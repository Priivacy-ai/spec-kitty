"""``spec-kitty charter mission-type`` command group (FR-016).

Exposes activated mission types for the current project via:

* ``spec-kitty charter mission-type list [--json]``
  Lists all mission types that are activated in this project (charter-filtered).

  Unlike ``spec-kitty doctrine mission-type list`` (WP13 / FR-013), this
  command returns only types that are explicitly activated for the project.

Implementation notes
--------------------
The ``charter`` API is the entry point for activation state
(``charter.existing_mission_types``, ``charter.resolve_action_sequence``).
Display metadata (``display_name``) is loaded from
:class:`doctrine.missions.mission_type_repository.MissionTypeRepository`
via a lazy import; ``specify_cli`` modules may import ``doctrine.*``
directly (layer direction: kernel <- doctrine <- charter <- specify_cli).
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from charter.mission_type_profiles import UnknownMissionTypeError, existing_mission_types, resolve_action_sequence

__all__ = [
    "charter_mission_type_app",
    "charter_mission_type_list",
]

charter_mission_type_app = typer.Typer(
    name="mission-type",
    help="Mission type commands (activated types only).",
    no_args_is_help=True,
)

console = Console()


@charter_mission_type_app.command("list")
def charter_mission_type_list(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON.",
    ),
) -> None:
    """List activated mission types for the current project (FR-016).

    Returns only mission types that are explicitly activated in this
    project's charter.  To see all doctrine-layer types regardless of
    activation state, use ``spec-kitty doctrine mission-type list``.

    Output columns (table): ID, SOURCE, DISPLAY NAME, ACTION SEQUENCE.
    """
    from doctrine.missions.mission_type_repository import MissionTypeRepository  # noqa: PLC0415

    repo_root = Path.cwd()
    activated_ids = existing_mission_types(repo_root)
    repo = MissionTypeRepository.default()

    rows: list[dict[str, object]] = []
    for mt_id in activated_ids:
        mt = repo.get(mt_id)
        if mt is None:
            # Activated but not in built-in bundle — surface it anyway.
            rows.append(
                {
                    "id": mt_id,
                    "source_layer": "unknown",
                    "display_name": mt_id,
                    "action_sequence": [],
                }
            )
            continue
        try:
            action_seq = resolve_action_sequence(mt_id, repo_root)
        except UnknownMissionTypeError:
            action_seq = list(mt.action_sequence)

        rows.append(
            {
                "id": mt_id,
                "source_layer": "built-in",
                "display_name": mt.display_name,
                "action_sequence": action_seq,
            }
        )

    if json_output:
        console.print_json(json.dumps(rows))
        raise typer.Exit(0)

    if not rows:
        console.print("[yellow]No activated mission types found for this project.[/yellow]")
        raise typer.Exit(0)

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="cyan")
    table.add_column("SOURCE", style="green")
    table.add_column("DISPLAY NAME")
    table.add_column("ACTION SEQUENCE")

    for row in rows:
        seq = row["action_sequence"]
        seq_str = ", ".join(seq) if isinstance(seq, list) else str(seq)
        table.add_row(
            str(row["id"]),
            str(row["source_layer"]),
            str(row["display_name"]),
            seq_str,
        )

    console.print(table)
    raise typer.Exit(0)
