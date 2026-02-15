"""Mission management CLI commands."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

import httpx
import typer
from rich.panel import Panel
from rich.table import Table

from specify_cli.cli.helpers import check_version_compatibility, console, get_project_root_or_exit
from specify_cli.mission_system import (
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
from specify_cli.collaboration.service import (
    join_mission,
    set_focus,
    set_drive,
    acknowledge_warning,
)
from specify_cli.collaboration.session import resolve_mission_id, ensure_joined
from specify_cli.collaboration.state import get_mission_roster
from specify_cli.events.ulid_utils import generate_event_id
from specify_cli.events.store import emit_event
from specify_cli.events.lamport import LamportClock
from specify_cli.spec_kitty_events.models import Event
from rich.prompt import Prompt

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


# ============================================================================
# Collaboration Commands
# ============================================================================


def join_command(mission_id: str, role: str) -> None:
    """Join mission with specified role."""
    try:
        # Load SaaS config from env
        saas_api_url = os.getenv("SAAS_API_URL", "https://api.spec-kitty-saas.com")
        auth_token = os.getenv("SAAS_AUTH_TOKEN", "")

        if not auth_token:
            console.print("[red]❌ SAAS_AUTH_TOKEN environment variable not set[/red]")
            console.print("[dim]Set your authentication token to join missions:[/dim]")
            console.print("  export SAAS_AUTH_TOKEN=your_token_here")
            raise typer.Exit(1)

        result = join_mission(mission_id, role, saas_api_url, auth_token)

        console.print(f"✅ Joined mission [bold]{mission_id}[/bold] as [bold]{role}[/bold]")
        console.print(f"Participant ID: [cyan]{result['participant_id']}[/cyan]")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)
    except httpx.HTTPStatusError as e:
        console.print(f"[red]❌ HTTP {e.response.status_code}: {e.response.text}[/red]")
        raise typer.Exit(1)
    except httpx.HTTPError as e:
        console.print(f"[red]❌ Network error: {e}[/red]")
        raise typer.Exit(1)


@app.command(name="join")
def join_cmd(
    mission_id: str = typer.Argument(..., help="Mission ID"),
    role: str = typer.Option(..., "--role", help="Participant role label (SaaS-validated)"),
) -> None:
    """Join mission as participant."""
    join_command(mission_id, role)


def focus_set_command(focus: str, mission_id: str | None = None) -> None:
    """Set focus target."""
    try:
        resolved_mission_id = resolve_mission_id(mission_id)
        set_focus(resolved_mission_id, focus)

        console.print(f"✅ Focus set to [bold]{focus}[/bold]")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


# Focus sub-commands
focus_app = typer.Typer(name="focus", help="Focus management commands")


@focus_app.command(name="set")
def set_focus_cmd(
    focus: str = typer.Argument(..., help="Focus target: wp:<id>, step:<id>, or none"),
    mission: Optional[str] = typer.Option(None, "--mission", help="Mission ID (default: active mission)"),
) -> None:
    """Set focus target."""
    focus_set_command(focus, mission)


# Register focus sub-app
app.add_typer(focus_app)


def drive_set_command(state: str, mission_id: str | None = None) -> None:
    """Set drive intent with collision check."""
    try:
        resolved_mission_id = resolve_mission_id(mission_id)
        result = set_drive(resolved_mission_id, state)

        # Handle collision
        if "collision" in result:
            collision = result["collision"]

            # Display warning panel
            participants_text = "\n".join(
                f"- {p['participant_id'][:8]}... on {p['focus']} (last: {p['last_activity_at']})"
                for p in collision["conflicting_participants"]
            )

            panel = Panel(
                f"[yellow]{collision['type']}[/yellow]\n\n"
                f"Active drivers on same focus:\n{participants_text}\n\n"
                f"Choose action:\n"
                f"[c] Continue (parallel work, high collision risk)\n"
                f"[h] Hold (set drive=inactive)\n"
                f"[r] Reassign (advisory suggestion)\n"
                f"[d] Defer (exit without change)",
                title=f"⚠️  Collision Detected ({collision['severity']} severity)"
            )
            console.print(panel)

            # Prompt acknowledgement
            action_map = {"c": "continue", "h": "hold", "r": "reassign", "d": "defer"}
            choice = Prompt.ask("Action", choices=list(action_map.keys()))
            acknowledgement = action_map[choice]

            # Handle action
            acknowledge_warning(
                resolved_mission_id,
                collision.get("warning_id", ""),
                acknowledgement,
            )

            if acknowledgement == "continue":
                # Re-call set_drive with bypass flag to skip collision check
                result = set_drive(resolved_mission_id, state, bypass_collision=True)
                console.print(f"✅ Drive intent set to [bold]{state}[/bold] (collision acknowledged)")
            elif acknowledgement == "hold":
                console.print("⏸️  Drive remains inactive")
            elif acknowledgement == "defer":
                console.print("Deferred")
                raise typer.Exit(0)

        else:
            console.print(f"✅ Drive intent set to [bold]{state}[/bold]")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


# Drive sub-commands
drive_app = typer.Typer(name="drive", help="Drive management commands")


@drive_app.command(name="set")
def set_drive_cmd(
    state: str = typer.Argument(..., help="Drive state: active or inactive"),
    mission: Optional[str] = typer.Option(None, "--mission", help="Mission ID (default: active mission)"),
) -> None:
    """Set drive intent."""
    drive_set_command(state, mission)


# Register drive sub-app
app.add_typer(drive_app)


def status_command(mission_id: str | None = None, verbose: bool = False) -> None:
    """Display mission status."""
    try:
        resolved_mission_id = resolve_mission_id(mission_id)
        roster = get_mission_roster(resolved_mission_id)

        table = Table(title=f"Mission {resolved_mission_id}")
        table.add_column("Role")
        table.add_column("Participant ID")
        table.add_column("Focus")
        table.add_column("Drive")
        table.add_column("Last Activity")

        for p in roster:
            pid = p.participant_id if verbose else f"{p.participant_id[:8]}..."
            table.add_row(
                (p.role or "unspecified").upper(),
                pid,
                p.focus or "none",
                p.drive_intent,
                p.last_activity_at.strftime("%H:%M:%S")
            )

        console.print(table)
        console.print(f"\n⚠️  {len([p for p in roster if p.drive_intent == 'active'])} active drivers")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command(name="status")
def status_cmd(
    mission: Optional[str] = typer.Option(None, "--mission", help="Mission ID (default: active mission)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full participant IDs"),
) -> None:
    """Display mission roster and status."""
    status_command(mission, verbose)


def comment_command(text: str | None = None, mission_id: str | None = None) -> None:
    """Post comment."""
    try:
        resolved_mission_id = resolve_mission_id(mission_id)

        if text is None:
            text = typer.prompt("Comment text")

        if len(text.strip()) == 0:
            console.print("[red]❌ Comment cannot be empty[/red]")
            raise typer.Exit(1)

        if len(text) > 500:
            console.print("[yellow]⚠️  Truncating comment to 500 chars[/yellow]")
            text = text[:500]

        state = ensure_joined(resolved_mission_id)
        comment_id = generate_event_id()

        # Emit CommentPosted event
        clock = LamportClock("cli-local")
        import uuid
        event = Event(
            event_id=comment_id,
            event_type="CommentPosted",
            aggregate_id=f"mission/{resolved_mission_id}",
            payload={
                "participant_id": state.participant_id,
                "mission_id": resolved_mission_id,
                "comment_id": comment_id,
                "content": text,
                "reply_to": None,
            },
            timestamp=datetime.now().isoformat(),
            node_id="cli-local",
            lamport_clock=clock.increment(),
            correlation_id=state.mission_run_id,
            causation_id=None,
            project_uuid=uuid.UUID(state.mission_run_id) if state.mission_run_id else uuid.uuid4(),
            project_slug=resolved_mission_id,
            schema_version="1.0.0",
            data_tier=0,
        )
        emit_event(resolved_mission_id, event, "", "")

        console.print(f"✅ Comment posted (ID: {comment_id[:8]}...)")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command(name="comment")
def comment_cmd(
    text: Optional[str] = typer.Argument(None, help="Comment text (prompts if omitted)"),
    mission: Optional[str] = typer.Option(None, "--mission", help="Mission ID (default: active mission)"),
) -> None:
    """Post a comment to the mission."""
    comment_command(text, mission)


def decide_command(text: str | None = None, mission_id: str | None = None) -> None:
    """Capture decision."""
    try:
        resolved_mission_id = resolve_mission_id(mission_id)
        state = ensure_joined(resolved_mission_id)

        if text is None:
            text = typer.prompt("Decision text")

        if len(text.strip()) == 0:
            console.print("[red]❌ Decision cannot be empty[/red]")
            raise typer.Exit(1)

        decision_id = generate_event_id()

        # Emit DecisionCaptured event
        clock = LamportClock("cli-local")
        import uuid
        event = Event(
            event_id=decision_id,
            event_type="DecisionCaptured",
            aggregate_id=f"mission/{resolved_mission_id}",
            payload={
                "participant_id": state.participant_id,
                "mission_id": resolved_mission_id,
                "decision_id": decision_id,
                "topic": state.focus or "mission",
                "chosen_option": text,
                "rationale": None,
                "referenced_warning_id": None,
            },
            timestamp=datetime.now().isoformat(),
            node_id="cli-local",
            lamport_clock=clock.increment(),
            correlation_id=state.mission_run_id,
            causation_id=None,
            project_uuid=uuid.UUID(state.mission_run_id) if state.mission_run_id else uuid.uuid4(),
            project_slug=resolved_mission_id,
            schema_version="1.0.0",
            data_tier=0,
        )
        emit_event(resolved_mission_id, event, "", "")

        console.print(f"✅ Decision captured (ID: {decision_id[:8]}...)")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command(name="decide")
def decide_cmd(
    text: Optional[str] = typer.Argument(None, help="Decision text (prompts if omitted)"),
    mission: Optional[str] = typer.Option(None, "--mission", help="Mission ID (default: active mission)"),
) -> None:
    """Capture a decision."""
    decide_command(text, mission)
