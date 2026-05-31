"""spec-kitty charter list — show activated doctrine artifacts per kind."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from charter.invocation_context import ProjectContext
from charter.pack_manager import CharterPackManager

__all__ = ["charter_list_app", "list_cmd"]

charter_list_app = typer.Typer(
    name="list",
    help="List activated doctrine artifacts by kind.",
    no_args_is_help=False,
    invoke_without_command=True,
)
console = Console()

#: Display order for the 9 kinds.
_KIND_ORDER: list[str] = [
    "directive",
    "tactic",
    "styleguide",
    "toolguide",
    "paradigm",
    "procedure",
    "agent-profile",
    "mission-step-contract",
    "mission-type",
]


@charter_list_app.callback()
def list_cmd(
    show_available: bool = typer.Option(
        False,
        "--show-available",
        help="Also show available-but-not-activated artifacts.",
    ),
    repo_root: Path = typer.Option(Path("."), hidden=True),
) -> None:
    """List activated doctrine artifacts for each of the 9 kinds."""
    ctx = ProjectContext.from_repo(repo_root)
    manager = CharterPackManager()
    activated_map = manager.list_activated(ctx)

    table = Table(title="Charter Activation State", show_lines=True)
    table.add_column("Kind", style="bold cyan", no_wrap=True)
    table.add_column("Activated", style="white")
    if show_available:
        table.add_column("Available (not activated)", style="dim")

    for kind in _KIND_ORDER:
        value = activated_map.get(kind)
        if value is None:
            activated_str = "[dim](All built-ins — no explicit activation)[/dim]"
        elif len(value) == 0:
            activated_str = "[yellow](Nothing activated — explicit restriction)[/yellow]"
        else:
            activated_str = ", ".join(sorted(value))

        if show_available:
            available = manager.list_available(ctx, kind)
            activated_set = value or frozenset()
            not_activated = sorted(available - activated_set) if available else []
            available_str = ", ".join(not_activated) if not_activated else "[dim]—[/dim]"
            table.add_row(kind, activated_str, available_str)
        else:
            table.add_row(kind, activated_str)

    console.print(table)
