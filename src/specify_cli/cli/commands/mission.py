"""Mission management CLI commands."""

from __future__ import annotations

from pathlib import Path
from collections.abc import Iterable

import typer
from rich.panel import Panel
from rich.table import Table

from specify_cli.cli.helpers import check_version_compatibility, console, get_project_root_or_exit
from specify_cli.mission import (
    Mission,
    MissionError,
    MissionNotFoundError,
    discover_missions,
    get_mission_by_name,
    get_mission_for_feature,
    list_available_missions,
)

app = typer.Typer(
    name="mission",
    help="View available Spec Kitty mission types. A mission type is the reusable blueprint selected when a mission is created. Legacy create-feature surfaces may still use feature wording.",
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


def _list_active_worktrees(repo_root: Path) -> list[str]:
    """Return list of active worktree directories relative to the repo root."""
    worktrees_dir = repo_root / ".worktrees"
    if not worktrees_dir.exists():
        return []

    active: list[str] = []
    for entry in sorted(worktrees_dir.iterdir()):
        if not entry.is_dir():
            continue
        try:
            rel = entry.relative_to(repo_root)
        except ValueError:
            rel = entry
        active.append(str(rel))
    return active


def _mission_details_lines(mission: Mission, include_description: bool = True) -> list[str]:
    """Return formatted mission details."""
    details: list[str] = [
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
    console.print("[dim]Mission types are selected when /spec-kitty.specify creates a mission. Legacy compatibility surfaces may still say feature.[/dim]")


@app.command("list")
def list_cmd() -> None:
    """List all available missions with their source (project/built-in)."""
    project_root = get_project_root_or_exit()
    check_version_compatibility(project_root, "mission")
    kittify_dir = project_root / ".kittify"
    if not kittify_dir.exists():
        console.print(f"[red]Spec Kitty project not initialized at:[/red] {project_root}")
        console.print(
            "[dim]Run 'spec-kitty init <project-name>' or execute this command from a feature worktree created under .worktrees/<feature>/.[/dim]"  # noqa: E501
        )
        raise typer.Exit(1)

    try:
        _print_available_missions(project_root)
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error listing missions:[/red] {exc}")
        raise typer.Exit(1) from exc


def _detect_current_feature(project_root: Path) -> str | None:
    """Return None — no auto-detection (requires explicit --feature).

    Args:
        project_root: Project root path (unused)

    Returns:
        Always None; caller must provide --feature explicitly.
    """
    return None


@app.command("current")
def current_cmd(
    feature: str | None = typer.Option(
        None,
        "--feature",
        "-f",
        help="Mission slug (legacy flag name; auto-detects from current directory if omitted)",
    ),
) -> None:
    """Show the active mission type for a mission (auto-detects mission from cwd)."""
    project_root = get_project_root_or_exit()
    check_version_compatibility(project_root, "mission")

    # Detect feature if not explicitly provided
    feature_slug = feature if feature else _detect_current_feature(project_root)

    if not feature_slug:
        console.print(
            "[yellow]No active feature detected.[/yellow]\n"
            "\nUse [cyan]--feature <slug>[/cyan] to specify one, "
            "or run from within a feature worktree."
        )
        # Optionally list available missions
        kitty_specs = project_root / "kitty-specs"
        if kitty_specs.is_dir():
            features = sorted(
                d.name for d in kitty_specs.iterdir()
                if d.is_dir() and d.name[0:1].isdigit()
            )
            if features:
                console.print("\n[cyan]Available missions:[/cyan]")
                for feat in features[:10]:
                    console.print(f"  - {feat}")
                if len(features) > 10:
                    console.print(f"  ... and {len(features) - 10} more")
        raise typer.Exit(1)

    try:
        feature_dir = project_root / "kitty-specs" / feature_slug
        if not feature_dir.exists():
            console.print(f"[red]Feature not found:[/red] {feature_slug}")
            raise typer.Exit(1)

        mission = get_mission_for_feature(feature_dir, project_root)
        context = f"Mission: {feature_slug}"

    except MissionNotFoundError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except MissionError as exc:
        console.print(f"[red]Failed to load active mission:[/red] {exc}")
        raise typer.Exit(1) from exc

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
        raise typer.Exit(1) from None
    except MissionError as exc:
        console.print(f"[red]Error loading mission '{mission_name}':[/red] {exc}")
        raise typer.Exit(1) from exc

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
    console.print("\n[cyan]Suggestion:[/cyan] Complete, merge, or remove these worktrees before switching missions.")


@app.command("switch", deprecated=True)
def switch_cmd(
    mission_name: str = typer.Argument(..., help="Mission name (no longer supported)"),  # noqa: ARG001
    force: bool = typer.Option(False, "--force", help="(ignored)"),  # noqa: ARG001
) -> None:
    """[REMOVED] Switch active mission - this command was removed in v0.8.0."""
    console.print("[bold red]Error:[/bold red] The 'mission switch' command was removed in v0.8.0.")
    console.print()
    console.print("Mission types are now selected [bold]per mission[/bold] during [cyan]/spec-kitty.specify[/cyan].")
    console.print()
    console.print("[cyan]New workflow:[/cyan]")
    console.print("  1. Run [bold]/spec-kitty.specify[/bold] to start a new mission")
    console.print("  2. The system will infer and confirm the appropriate mission type")
    console.print("  3. The selected mission type is stored in the mission's [dim]meta.json[/dim]")
    console.print()
    console.print("[cyan]To see available missions:[/cyan]")
    console.print("  spec-kitty mission list")
    console.print()
    console.print("[dim]See: architecture/2.x/adr/2026-04-04-2-mission-type-mission-and-mission-run-terminology-boundary.md[/dim]")
    raise typer.Exit(1)
