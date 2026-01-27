"""Mission management CLI commands."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

import typer
from rich.panel import Panel
from rich.table import Table

from specify_cli.cli.helpers import check_version_compatibility, console, get_project_root_or_exit
from specify_cli.mission import (
    Mission,
    MissionError,
    MissionNotFoundError,
    discover_missions,
    get_active_mission,
    get_mission_by_name,
    get_mission_for_feature,
    list_available_missions,
)
from specify_cli.core.feature_detection import (
    detect_feature,
    FeatureDetectionError,
)

app = typer.Typer(
    name="mission",
    help="View available Spec Kitty missions. Missions are selected per-feature during /spec-kitty.specify.",
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


def _print_available_missions(project_root: Path) -> None:
    """Print available missions with source indicators (project/built-in)."""
    missions = discover_missions(project_root)
    if not missions:
        console.print("[yellow]No missions found in .kittify/missions/[/yellow]")
        return

    table = Table(title="Available Missions", show_header=True)
    table.add_column("Key", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Domain", style="magenta")
    table.add_column("Description", overflow="fold")
    table.add_column("Source", style="dim")

    for key, (mission, source) in sorted(missions.items()):
        table.add_row(
            key,
            mission.name,
            mission.domain,
            mission.description or "",
            source,
        )

    console.print(table)
    console.print()
    console.print("[dim]Missions are selected per-feature during /spec-kitty.specify[/dim]")


@app.command("list")
def list_cmd() -> None:
    """List all available missions with their source (project/built-in)."""
    project_root = get_project_root_or_exit()
    check_version_compatibility(project_root, "mission")
    kittify_dir = project_root / ".kittify"
    if not kittify_dir.exists():
        console.print(f"[red]Spec Kitty project not initialized at:[/red] {project_root}")
        console.print("[dim]Run 'spec-kitty init <project-name>' or execute this command from a feature worktree created under .worktrees/<feature>/.[/dim]")
        raise typer.Exit(1)

    try:
        _print_available_missions(project_root)
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error listing missions:[/red] {exc}")
        raise typer.Exit(1)


def _detect_current_feature(project_root: Path) -> Optional[str]:
    """Detect feature slug from current working directory using centralized detection.

    This function uses lenient mode to return None on failure (UI convenience).

    Args:
        project_root: Project root path

    Returns:
        Feature slug if detected, None otherwise
    """
    try:
        ctx = detect_feature(
            project_root,
            cwd=Path.cwd(),
            mode="lenient"  # Return None instead of raising error
        )
        return ctx.slug if ctx else None
    except Exception:
        # Catch any unexpected errors and return None (lenient behavior)
        return None


@app.command("current")
def current_cmd(
    feature: Optional[str] = typer.Option(
        None,
        "--feature",
        "-f",
        help="Feature slug (auto-detects from current directory if omitted)",
    )
) -> None:
    """Show currently active mission for a feature (auto-detects feature from cwd)."""
    project_root = get_project_root_or_exit()
    check_version_compatibility(project_root, "mission")

    # Detect feature if not explicitly provided
    feature_slug = feature if feature else _detect_current_feature(project_root)

    try:
        if feature_slug:
            # Use feature-level detection (CORRECT)
            feature_dir = project_root / "kitty-specs" / feature_slug
            if not feature_dir.exists():
                console.print(f"[red]Feature not found:[/red] {feature_slug}")
                raise typer.Exit(1)

            mission = get_mission_for_feature(feature_dir, project_root)
            context = f"Feature: {feature_slug}"
        else:
            # No feature context - show project default
            # Still use get_active_mission() for backward compat with project-level
            mission = get_active_mission(project_root)
            context = "Project Default"

    except MissionNotFoundError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)
    except MissionError as exc:
        console.print(f"[red]Failed to load active mission:[/red] {exc}")
        raise typer.Exit(1)

    panel = Panel(
        "\n".join(_mission_details_lines(mission)),
        title=f"Active Mission ({context})",
        border_style="cyan",
    )
    console.print(panel)


@app.command("info")
def info_cmd(
    mission_name: str = typer.Argument(..., help="Mission name to display details for"),
) -> None:
    """Show details for a specific mission without switching."""
    project_root = get_project_root_or_exit()
    check_version_compatibility(project_root, "mission")
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


@app.command("switch", deprecated=True)
def switch_cmd(
    mission_name: str = typer.Argument(..., help="Mission name (no longer supported)"),
    force: bool = typer.Option(False, "--force", help="(ignored)"),
) -> None:
    """[REMOVED] Switch active mission - this command was removed in v0.8.0."""
    console.print("[bold red]Error:[/bold red] The 'mission switch' command was removed in v0.8.0.")
    console.print()
    console.print("Missions are now selected [bold]per-feature[/bold] during [cyan]/spec-kitty.specify[/cyan].")
    console.print()
    console.print("[cyan]New workflow:[/cyan]")
    console.print("  1. Run [bold]/spec-kitty.specify[/bold] to start a new feature")
    console.print("  2. The system will infer and confirm the appropriate mission")
    console.print("  3. Mission is stored in the feature's [dim]meta.json[/dim]")
    console.print()
    console.print("[cyan]To see available missions:[/cyan]")
    console.print("  spec-kitty mission list")
    console.print()
    console.print("[dim]See: https://github.com/your-org/spec-kitty#per-feature-missions[/dim]")
    raise typer.Exit(1)
