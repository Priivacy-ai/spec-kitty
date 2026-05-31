"""spec-kitty charter deactivate — deactivate a doctrine artifact (FR-005)."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from charter.invocation_context import ProjectContext
from charter.pack_manager import YAML_KEY_MAP, CharterPackManager

__all__ = ["charter_deactivate_app", "deactivate_cmd"]

charter_deactivate_app = typer.Typer(
    name="deactivate",
    help="Deactivate a doctrine artifact from this project.",
    no_args_is_help=True,
    invoke_without_command=True,
)
console = Console()


@charter_deactivate_app.callback(invoke_without_command=True)
def deactivate_cmd(
    ctx: typer.Context,
    kind: str | None = typer.Argument(None, help="Activation kind (e.g. directive, agent-profile)."),
    artifact_id: str | None = typer.Argument(None, help="Artifact ID to deactivate."),
    cascade: str | None = typer.Option(
        None,
        "--cascade",
        help="Enable cascade deactivation of exclusively-referenced artifacts.",
    ),
    repo_root: Path = typer.Option(Path("."), hidden=True),
) -> None:
    """Deactivate a doctrine artifact by kind and ID (FR-005)."""
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
    try:
        result = CharterPackManager().deactivate(ctx_project, kind, artifact_id, cascade=cascade_bool)
    except SystemExit:
        # None-state kind: config key absent, migration not yet run.
        # CharterPackManager.deactivate() calls sys.exit(1) for None-state.
        console.print(
            "[red]Error:[/red] Kind has no explicit activation set. "
            "Run 'spec-kitty upgrade' first."
        )
        raise typer.Exit(1) from None
    except ValueError as exc:
        # None-state kind: config key absent, migration not yet run
        console.print(f"[red]Error:[/red] {exc}")
        console.print(
            "Kind has no explicit activation set. "
            "Run 'spec-kitty upgrade' first."
        )
        raise typer.Exit(1) from exc
    for msg in result.deactivated:
        console.print(f"[green]Deactivated[/green]: {msg}")
    # result.cascade_deactivated is dict[str, list[str]] — kind -> list of IDs
    for kind_name, ids in result.cascade_deactivated.items():
        for cid in ids:
            console.print(f"[cyan]Cascade-deactivated[/cyan]: {kind_name}/{cid}")
    # result.skipped_shared is dict[str, list[str]] — kind -> list of IDs
    for kind_name, ids in result.skipped_shared.items():
        for cid in ids:
            console.print(f"[yellow]Skipped (shared artifact)[/yellow]: {kind_name}/{cid}")
    for warn in result.warnings:
        console.print(f"[yellow]Warning[/yellow]: {warn}")
