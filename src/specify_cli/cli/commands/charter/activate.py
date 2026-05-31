"""spec-kitty charter activate — activate a doctrine artifact (FR-004, FR-008)."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from charter.invocation_context import ProjectContext
from charter.pack_manager import YAML_KEY_MAP, CharterPackManager

__all__ = ["charter_activate_app", "activate_cmd"]

charter_activate_app = typer.Typer(
    name="activate",
    help="Activate a doctrine artifact for this project.",
    no_args_is_help=True,
    invoke_without_command=True,
)
console = Console()


@charter_activate_app.callback(invoke_without_command=True)
def activate_cmd(
    ctx: typer.Context,
    kind: str | None = typer.Argument(None, help="Activation kind (e.g. directive, agent-profile)."),
    artifact_id: str | None = typer.Argument(None, help="Artifact ID to activate."),
    cascade: str | None = typer.Option(
        None,
        "--cascade",
        help="Enable cascade activation of referenced artifacts.",
    ),
    repo_root: Path = typer.Option(Path("."), hidden=True),
) -> None:
    """Activate a doctrine artifact by kind and ID (FR-004)."""
    if ctx.invoked_subcommand is not None:
        return
    if kind is None or artifact_id is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)
    if kind not in YAML_KEY_MAP:
        console.print(
            f"[red]Error:[/red] Unknown kind '{kind}'. "
            f"Valid kinds: {', '.join(sorted(YAML_KEY_MAP))}."
        )
        raise typer.Exit(1)
    ctx_project = ProjectContext.from_repo(repo_root)
    # WP04 API: cascade is bool. --cascade <any-value> enables it.
    cascade_bool: bool = bool(cascade)
    result = CharterPackManager().activate(ctx_project, kind, artifact_id, cascade=cascade_bool)
    for msg in result.activated:
        console.print(f"[green]Activated[/green]: {msg}")
    # result.cascade_activated is dict[str, list[str]] — kind -> list of IDs
    for kind_name, ids in result.cascade_activated.items():
        for cid in ids:
            console.print(f"[cyan]Cascade-activated[/cyan]: {kind_name}/{cid}")
    for warn in result.warnings:
        console.print(f"[yellow]Warning[/yellow]: {warn}")
