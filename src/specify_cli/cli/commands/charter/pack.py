"""spec-kitty charter pack — charter pack management commands (FR-011).

``list`` / ``path`` / ``apply`` (#3064 follow-up) are the on-demand pack CLI
for the built-in charter packs shipped at ``src/charter/packs/`` (``default``
and ``minimal``). The pack -> ``config.yaml`` merge logic is shared with the
``3.2.0rc35_default_charter_pack`` upgrade migration via
``specify_cli.charter_pack_registry`` — see that module's docstring.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from ruamel.yaml import YAML
from specify_cli.cli.console import console

from charter.invocation_context import ProjectContext
from specify_cli.charter_pack_registry import (
    BUILTIN_PACKS,
    UnknownPackError,
    load_pack_yaml,
    merge_pack_into_config,
    resolve_builtin_pack_path,
)

__all__ = ["charter_pack_app"]

charter_pack_app = typer.Typer(
    name="pack",
    help="Charter pack management commands.",
    no_args_is_help=True,
)


@charter_pack_app.command("consistency-check")
def consistency_check_cmd(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    repo_root: Path = typer.Option(Path("."), hidden=True),
) -> None:
    """Run consistency check against activated doctrine artifacts (FR-011)."""
    from charter.consistency_check import run_consistency_check  # noqa: PLC0415

    ctx = ProjectContext.from_repo(repo_root)
    report = run_consistency_check(ctx)
    if json_output:
        typer.echo(report.to_json())
    else:
        if report.coherent:
            console.print("[green]Charter pack is coherent.[/green]")
        else:
            console.print("[red]Consistency issues found:[/red]")
            for ref in report.unknown_references:
                console.print(f"  [red]Unknown reference:[/red] {ref}")
            for ref in report.missing_from_doctrine:
                console.print(f"  [yellow]Missing from doctrine:[/yellow] {ref}")
            for v in report.kind_violations:
                console.print(f"  [red]Kind violation:[/red] {v}")
            for ref in report.reference_id_divergences:
                console.print(f"  [red]Reference ID divergence:[/red] {ref}")
            for kind in report.graph_kind_gaps:
                console.print(f"  [red]Graph kind gap:[/red] {kind}")
            for s in report.suggestions:
                console.print(f"  [dim]Suggestion:[/dim] {s}")
    raise typer.Exit(0 if report.coherent else 1)


@charter_pack_app.command("list")
def list_cmd(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """List the built-in charter packs shipped with spec-kitty (#3064)."""
    try:
        packs = [
            {
                "name": name,
                "path": str(resolve_builtin_pack_path(name)),
                "description": description,
            }
            for name, description in sorted(BUILTIN_PACKS.items())
        ]
    except FileNotFoundError as exc:
        if json_output:
            typer.echo(json.dumps({"error": str(exc)}))
        else:
            console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    if json_output:
        typer.echo(json.dumps({"packs": packs}, indent=2))
        return

    console.print("[bold]Built-in charter packs:[/bold]")
    for pack in packs:
        console.print(f"  [cyan]{pack['name']}[/cyan] — {pack['description']}")
    console.print(
        "\n[dim]Resolve a path with `spec-kitty charter pack path <name>`, "
        "apply one with `spec-kitty charter pack apply <name>`.[/dim]"
    )


@charter_pack_app.command("path")
def path_cmd(
    name: str = typer.Argument(..., help="Built-in pack name (e.g. 'default', 'minimal')."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Resolve a built-in charter pack name to its shipped filesystem path (#3064).

    Fails closed (exit 1) on an unknown pack name, naming it and the valid set.
    """
    try:
        resolved = resolve_builtin_pack_path(name)
    except (UnknownPackError, FileNotFoundError) as exc:
        if json_output:
            typer.echo(json.dumps({"error": str(exc)}))
        else:
            console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    if json_output:
        typer.echo(json.dumps({"name": name, "path": str(resolved)}))
    else:
        typer.echo(str(resolved))


@charter_pack_app.command("apply")
def apply_cmd(
    name: str = typer.Argument(..., help="Built-in pack name to apply (e.g. 'default', 'minimal')."),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite activation keys already present in config.yaml (default: leave them untouched).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    repo_root: Path = typer.Option(Path("."), hidden=True),
) -> None:
    """Apply a built-in charter pack's activation keys into .kittify/config.yaml (#3064).

    User Customization Preservation: by default this is an additive merge —
    a ``config.yaml`` key the pack declares is only written when it is
    currently absent. An already-present key (even an empty list a user
    explicitly authored) is left untouched unless ``--force`` is passed, in
    which case every key the pack declares is overwritten.
    """
    try:
        pack_path = resolve_builtin_pack_path(name)
    except (UnknownPackError, FileNotFoundError) as exc:
        if json_output:
            typer.echo(json.dumps({"error": str(exc)}))
        else:
            console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    config_path = repo_root / ".kittify" / "config.yaml"
    yaml = YAML()
    yaml.preserve_quotes = True
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as fh:
            data = yaml.load(fh) or {}
    else:
        data = {}
    if not isinstance(data, dict):
        console.print("[red]Error:[/red] .kittify/config.yaml root must be a mapping.")
        raise typer.Exit(1)

    pack_data = load_pack_yaml(pack_path)
    keys_written, keys_skipped = merge_pack_into_config(data, pack_data, force=force)

    if keys_written:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("w", encoding="utf-8") as fh:
            yaml.dump(data, fh)

    result = {
        "pack": name,
        "path": str(pack_path),
        "config_path": str(config_path),
        "keys_written": keys_written,
        "keys_skipped": keys_skipped,
        "force": force,
    }
    if json_output:
        typer.echo(json.dumps(result, indent=2))
        return

    if keys_written:
        console.print(
            f"[green]Applied charter pack '{name}':[/green] wrote {', '.join(keys_written)}"
        )
    else:
        console.print(
            f"[yellow]No keys written for pack '{name}'.[/yellow] All target keys "
            "already present in config.yaml; pass --force to overwrite them."
        )
    if keys_skipped:
        console.print(
            f"[dim]Skipped (already present; use --force to overwrite):[/dim] "
            f"{', '.join(keys_skipped)}"
        )
    console.print(
        "[dim]Next:[/dim] review activations with `spec-kitty charter list`. "
        "The baseline is now recorded in config.yaml -- agent-profile "
        "activation and a charter compile may still be needed for full "
        "governance."
    )
