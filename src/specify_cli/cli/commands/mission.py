"""Mission management CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

import typer
from rich.panel import Panel
from rich.table import Table

from specify_cli.cli.helpers import console, get_project_root_or_exit
from specify_cli.guards import GuardValidationError, validate_git_clean
from specify_cli.mission import (
    Mission,
    MissionError,
    MissionNotFoundError,
    get_active_mission,
    get_mission_by_name,
    list_available_missions,
    set_active_mission,
)
from specify_cli.validators.paths import validate_mission_paths

app = typer.Typer(
    name="mission",
    help="Manage project-wide Spec Kitty missions (workflow modes)",
    no_args_is_help=True,
)


def _resolve_primary_repo_root(project_root: Path) -> Path:
    """Return the primary repository root even when invoked from a worktree."""
    resolved = project_root.resolve()
    parts = list(resolved.parts)
    if ".worktrees" not in parts:
        return resolved

    idx = parts.index(".worktrees")
    # Rebuild the path up to (but excluding) ".worktrees"
    base = Path(parts[0])
    for segment in parts[1:idx]:
        base /= segment
    return base


def _list_active_worktrees(repo_root: Path) -> List[str]:
    """Return list of active worktree directories relative to the repo root."""
    worktrees_dir = repo_root / ".worktrees"
    if not worktrees_dir.exists():
        return []

    active: List[str] = []
    for entry in sorted(worktrees_dir.iterdir()):
        if not entry.is_dir():
            continue
        try:
            rel = entry.relative_to(repo_root)
        except ValueError:
            rel = entry
        active.append(str(rel))
    return active


def _mission_details_lines(mission: Mission, include_description: bool = True) -> List[str]:
    """Return formatted mission details."""
    details: List[str] = [
        f"[cyan]Name:[/cyan] {mission.name}",
        f"[cyan]Domain:[/cyan] {mission.domain}",
        f"[cyan]Version:[/cyan] {mission.version}",
        f"[cyan]Path:[/cyan] {mission.path}",
    ]
    if include_description and mission.description:
        details.append(f"[cyan]Description:[/cyan] {mission.description}")
    details.extend(["", "[cyan]Workflow Phases:[/cyan]"])
    for phase in mission.config.workflow.phases:
        details.append(f"  • {phase.name} – {phase.description}")

    details.extend(["", "[cyan]Required Artifacts:[/cyan]"])
    if mission.config.artifacts.required:
        for artifact in mission.config.artifacts.required:
            details.append(f"  • {artifact}")
    else:
        details.append("  • (none)")

    if mission.config.artifacts.optional:
        details.extend(["", "[cyan]Optional Artifacts:[/cyan]"])
        for artifact in mission.config.artifacts.optional:
            details.append(f"  • {artifact}")

    details.extend(["", "[cyan]Validation Checks:[/cyan]"])
    if mission.config.validation.checks:
        for check in mission.config.validation.checks:
            details.append(f"  • {check}")
    else:
        details.append("  • (none)")

    if mission.config.paths:
        details.extend(["", "[cyan]Path Conventions:[/cyan]"])
        for key, value in mission.config.paths.items():
            details.append(f"  • {key}: {value}")

    if mission.config.mcp_tools:
        details.extend(["", "[cyan]MCP Tools:[/cyan]"])
        details.append(f"  • Required: {', '.join(mission.config.mcp_tools.required) or 'none'}")
        details.append(f"  • Recommended: {', '.join(mission.config.mcp_tools.recommended) or 'none'}")
        details.append(f"  • Optional: {', '.join(mission.config.mcp_tools.optional) or 'none'}")

    return details


def _print_available_missions(kittify_dir: Path) -> None:
    missions = list_available_missions(kittify_dir)
    if not missions:
        console.print("[yellow]No missions found in .kittify/missions/[/yellow]")
        return

    try:
        active = get_active_mission(kittify_dir.parent)
        active_name = active.path.name
    except MissionError:
        active_name = None

    table = Table(title="Available Missions", show_header=True)
    table.add_column("Mission", style="cyan")
    table.add_column("Domain", style="magenta")
    table.add_column("Description", overflow="fold")
    table.add_column("Active", justify="center", style="green")

    for mission_name in missions:
        try:
            mission = get_mission_by_name(mission_name, kittify_dir)
            active_marker = "✓" if mission_name == active_name else ""
            table.add_row(mission.name, mission.domain, mission.description, active_marker)
        except Exception as exc:  # pragma: no cover - defensive logging
            table.add_row(mission_name, "[red]error[/red]", str(exc), "")

    console.print(table)


@app.command("list")
def list_cmd() -> None:
    """List all available missions."""
    project_root = get_project_root_or_exit()
    kittify_dir = project_root / ".kittify"
    if not kittify_dir.exists():
        console.print(f"[red]Spec Kitty project not initialized at:[/red] {project_root}")
        console.print("[dim]Run 'spec-kitty init <project-name>' or execute this command from a feature worktree created under .worktrees/<feature>/.[/dim]")
        raise typer.Exit(1)

    try:
        _print_available_missions(kittify_dir)
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error listing missions:[/red] {exc}")
        raise typer.Exit(1)


@app.command("current")
def current_cmd() -> None:
    """Show currently active mission."""
    project_root = get_project_root_or_exit()
    try:
        mission = get_active_mission(project_root)
    except MissionNotFoundError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)
    except MissionError as exc:
        console.print(f"[red]Failed to load active mission:[/red] {exc}")
        raise typer.Exit(1)

    panel = Panel(
        "\n".join(_mission_details_lines(mission)),
        title="Active Mission",
        border_style="cyan",
    )
    console.print(panel)


@app.command("info")
def info_cmd(
    mission_name: str = typer.Argument(..., help="Mission name to display details for"),
) -> None:
    """Show details for a specific mission without switching."""
    project_root = get_project_root_or_exit()
    kittify_dir = project_root / ".kittify"

    try:
        mission = get_mission_by_name(mission_name, kittify_dir)
    except MissionNotFoundError:
        console.print(f"[red]Mission not found:[/red] {mission_name}")
        available = list_available_missions(kittify_dir)
        if available:
            console.print("\n[yellow]Available missions:[/yellow]")
            for name in available:
                console.print(f"  • {name}")
        raise typer.Exit(1)
    except MissionError as exc:
        console.print(f"[red]Error loading mission '{mission_name}':[/red] {exc}")
        raise typer.Exit(1)

    panel = Panel(
        "\n".join(_mission_details_lines(mission, include_description=True)),
        title=f"Mission Details · {mission.name}",
        border_style="cyan",
    )
    console.print(panel)


def _print_active_worktrees(active_worktrees: Iterable[str]) -> None:
    console.print("[red]Cannot switch missions: active features exist[/red]")
    console.print("\n[yellow]Active worktrees:[/yellow]")
    for wt in active_worktrees:
        console.print(f"  • {wt}")
    console.print(
        "\n[cyan]Suggestion:[/cyan] Complete, merge, or remove these worktrees before switching missions."
    )


@app.command("switch")
def switch_cmd(
    mission_name: str = typer.Argument(..., help="Mission name to switch to"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompts"),
) -> None:
    """Switch to a different mission after validation."""
    project_root = get_project_root_or_exit()
    primary_repo_root = _resolve_primary_repo_root(project_root)
    kittify_dir = project_root / ".kittify"

    active_worktrees = _list_active_worktrees(primary_repo_root)
    if active_worktrees:
        _print_active_worktrees(active_worktrees)
        raise typer.Exit(1)

    try:
        git_clean_result = validate_git_clean(project_root)
    except GuardValidationError as exc:
        console.print(f"[red]Error checking git status:[/red] {exc}")
        raise typer.Exit(1)

    if not git_clean_result.is_valid:
        console.print("[red]Cannot switch missions: uncommitted changes detected[/red]")
        for error in git_clean_result.errors:
            console.print(f"  [yellow]{error}[/yellow]")
        console.print("\n[cyan]Suggestion:[/cyan] Commit or stash changes before switching.")
        raise typer.Exit(1)

    try:
        target_mission = get_mission_by_name(mission_name, kittify_dir)
    except MissionNotFoundError:
        console.print(f"[red]Mission not found:[/red] {mission_name}")
        available = list_available_missions(kittify_dir)
        if available:
            console.print("\n[yellow]Available missions:[/yellow]")
            for name in available:
                console.print(f"  • {name}")
        raise typer.Exit(1)

    current_name: Optional[str] = None
    current_display = "Unknown"
    try:
        current_mission = get_active_mission(project_root)
        current_name = current_mission.path.name
        current_display = current_mission.name
    except MissionError:
        current_mission = None

    if current_name == mission_name:
        console.print(f"[yellow]Already using mission:[/yellow] {target_mission.name}")
        raise typer.Exit(0)

    warnings: List[str] = []
    artifact_warnings: List[str] = []
    for artifact in target_mission.config.artifacts.required:
        artifact_path = project_root / artifact
        if not artifact_path.exists():
            message = f"Required artifact missing: {artifact}"
            warnings.append(message)
            artifact_warnings.append(message)

    path_warning_text = ""
    if target_mission.config.paths:
        path_result = validate_mission_paths(
            target_mission,
            project_root,
            strict=False,
        )
        if not path_result.is_valid:
            warnings.extend(path_result.warnings)
            path_warning_text = path_result.format_warnings()

    console.print("\n[cyan]Switch Summary[/cyan]")
    console.print(f"  From: {current_display}")
    console.print(f"  To:   {target_mission.name}")
    console.print(f"  Domain: {target_mission.domain}")

    if artifact_warnings:
        console.print("\n[yellow]Warnings:[/yellow]")
        for warning in artifact_warnings:
            console.print(f"  • {warning}")
        console.print("[dim]You can create these artifacts after switching.[/dim]")

    if path_warning_text:
        console.print("")
        console.print(path_warning_text)
        console.print("\n[dim]You can create these directories after switching.[/dim]")

    if not force:
        typer.echo("")
        confirm = typer.confirm("Proceed with mission switch?")
        if not confirm:
            console.print("[yellow]Mission switch cancelled[/yellow]")
            raise typer.Exit(0)

    console.print("\n[cyan]Switching mission...[/cyan]")
    set_active_mission(mission_name, kittify_dir)
    console.print(f"[green]✓ Switched to mission:[/green] {target_mission.name}")
    console.print(
        "\n[cyan]Next steps:[/cyan]\n"
        "  • Run /spec-kitty.specify to start a new feature\n"
        "  • Verify the active mission with: spec-kitty mission current"
    )
