"""``spec-kitty charter activate`` — activate a mission-type override (FR-008).

Activates a project-level mission-type override by writing a YAML file to
``.kittify/overrides/mission-types/<id>.yaml``.

Before completing activation, emits a structured warning for each in-flight
WP that lives in a lane corresponding to a step that the incoming
``action_sequence`` removes.  The warning is non-blocking: activation always
completes after warning emission.

Usage
-----
.. code-block:: text

    spec-kitty charter activate software-dev --action-sequence specify plan tasks implement merge

"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from specify_cli.charter_activate import activate_mission_type_override

__all__ = [
    "charter_activate_app",
    "activate_cmd",
]

charter_activate_app = typer.Typer(
    name="activate",
    help="Activate a mission-type override for this project (FR-008).",
    no_args_is_help=True,
)

console = Console()


@charter_activate_app.command("mission-type")
def activate_cmd(
    mission_type_id: str = typer.Argument(
        ...,
        help="Mission type to override (e.g. software-dev).",
    ),
    action_sequence: list[str] = typer.Option(
        ...,
        "--action-sequence",
        "-s",
        help="Ordered action step IDs for the override (repeat or space-separated).",
    ),
) -> None:
    """Activate a mission-type override (FR-008).

    Writes ``.kittify/overrides/mission-types/<id>.yaml`` with the supplied
    ``action_sequence``.  Before writing, computes removed steps and emits
    a warning for each in-flight WP affected by the removal.

    The warning is non-blocking: the override is always written.
    """
    repo_root = Path.cwd()

    try:
        activate_mission_type_override(
            mission_type_id=mission_type_id,
            incoming_sequence=action_sequence,
            repo_root=repo_root,
            console=console,
        )
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
