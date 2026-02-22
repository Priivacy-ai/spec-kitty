"""Centralized git hook management commands."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.table import Table

from specify_cli.cli.helpers import check_version_compatibility, console, get_project_root_or_exit
from specify_cli.hooks import (
    HookStatus,
    get_project_hook_status,
    install_or_update_hooks,
    remove_project_hook_shims,
)

app = typer.Typer(
    name="hooks",
    help="Manage Spec Kitty git hook shims and centralized hook scripts.",
    no_args_is_help=True,
)


def _status_payload(project_root: Path, statuses: tuple[HookStatus, ...]) -> dict[str, object]:
    return {
        "project_root": str(project_root),
        "hooks": [
            {
                "name": item.name,
                "global_path": str(item.global_path),
                "global_exists": item.global_exists,
                "project_path": str(item.project_path),
                "project_exists": item.project_exists,
                "project_managed": item.project_managed,
                "project_points_to_global": item.project_points_to_global,
            }
            for item in statuses
        ],
    }


def _print_status_table(statuses: tuple[HookStatus, ...]) -> None:
    table = Table(title="Spec Kitty Hook Status", show_header=True)
    table.add_column("Hook", style="cyan")
    table.add_column("Global", style="magenta")
    table.add_column("Project", style="green")
    table.add_column("Managed", style="yellow")
    table.add_column("Wired", style="blue")

    for item in statuses:
        global_state = "present" if item.global_exists else "missing"
        if not item.project_exists:
            project_state = "missing"
        elif item.project_managed:
            project_state = "shim"
        else:
            project_state = "custom"
        managed_state = "yes" if item.project_managed else "no"
        wired_state = "yes" if item.project_points_to_global else "no"
        table.add_row(item.name, global_state, project_state, managed_state, wired_state)

    console.print(table)


@app.command("install")
def install_cmd(
    force: bool = typer.Option(False, "--force", help="Overwrite existing non-managed project hooks"),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON"),
) -> None:
    """Install centralized hooks and per-project shims."""
    project_root = get_project_root_or_exit()
    check_version_compatibility(project_root, "hooks")

    try:
        result = install_or_update_hooks(project_root, force=force)
    except FileNotFoundError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    payload = {
        "project_root": str(project_root),
        "global_home": str(result.global_home),
        "global_hooks_dir": str(result.global_hooks_dir),
        "global_hooks_updated": list(result.global_hooks),
        "project_hooks_dir": str(result.project.hooks_dir),
        "installed": list(result.project.installed),
        "updated": list(result.project.updated),
        "unchanged": list(result.project.unchanged),
        "skipped_custom": list(result.project.skipped_custom),
        "missing_global_targets": list(result.project.missing_global_targets),
    }

    if json_output:
        typer.echo(json.dumps(payload, indent=2))
        return

    console.print(
        f"[green]Installed centralized hooks:[/green] {len(result.global_hooks)} file(s) at {result.global_hooks_dir}"
    )
    console.print(
        f"[green]Project shims:[/green] +{len(result.project.installed)} installed, "
        f"{len(result.project.updated)} updated, {len(result.project.unchanged)} unchanged"
    )
    if result.project.skipped_custom:
        console.print(
            "[yellow]Skipped custom hooks:[/yellow] "
            + ", ".join(sorted(result.project.skipped_custom))
            + " (use --force to overwrite)"
        )
    if result.project.missing_global_targets:
        console.print(
            "[yellow]Missing global targets:[/yellow] "
            + ", ".join(sorted(result.project.missing_global_targets))
        )


@app.command("update")
def update_cmd(
    force: bool = typer.Option(False, "--force", help="Overwrite existing non-managed project hooks"),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON"),
) -> None:
    """Update centralized hook scripts and refresh project shims."""
    install_cmd(force=force, json_output=json_output)


@app.command("status")
def status_cmd(
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON"),
) -> None:
    """Show global hook assets and project shim status."""
    project_root = get_project_root_or_exit()
    check_version_compatibility(project_root, "hooks")

    try:
        statuses = get_project_hook_status(project_root)
    except FileNotFoundError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    if json_output:
        typer.echo(json.dumps(_status_payload(project_root, statuses), indent=2))
        return

    _print_status_table(statuses)


@app.command("remove")
def remove_cmd(
    force: bool = typer.Option(False, "--force", help="Also remove non-managed project hooks for managed hook names"),
    json_output: bool = typer.Option(False, "--json", help="Output machine-readable JSON"),
) -> None:
    """Remove per-project hook shims (does not delete ~/.kittify/hooks)."""
    project_root = get_project_root_or_exit()
    check_version_compatibility(project_root, "hooks")

    try:
        result = remove_project_hook_shims(project_root, force=force)
    except FileNotFoundError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    payload = {
        "project_root": str(project_root),
        "project_hooks_dir": str(result.hooks_dir),
        "removed": list(result.removed),
        "skipped_custom": list(result.skipped_custom),
        "missing": list(result.missing),
    }

    if json_output:
        typer.echo(json.dumps(payload, indent=2))
        return

    console.print(f"[green]Removed hook shims:[/green] {', '.join(result.removed) if result.removed else 'none'}")
    if result.skipped_custom:
        console.print(
            "[yellow]Skipped custom hooks:[/yellow] "
            + ", ".join(sorted(result.skipped_custom))
            + " (use --force to remove)"
        )
