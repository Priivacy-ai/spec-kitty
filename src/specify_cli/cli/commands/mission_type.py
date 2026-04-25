"""Mission management CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from collections.abc import Iterable
from typing import Annotated, Any

import typer
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from specify_cli.cli.helpers import check_version_compatibility, console, get_project_root_or_exit
from specify_cli.cli.selector_resolution import resolve_selector
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
    name="mission-type",
    help="View available Spec Kitty mission types. Mission types are selected per mission run during /spec-kitty.specify.",
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
    console.print("[dim]Mission types are selected per mission run during /spec-kitty.specify[/dim]")


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
    """Return None — no auto-detection (requires explicit --mission).

    Args:
        project_root: Project root path (unused)

    Returns:
        Always None; caller must provide --mission explicitly.
    """
    return None


@app.command("current")
def current_cmd(
    mission: Annotated[str | None, typer.Option("--mission", "-f", help="Mission slug")] = None,
    feature: Annotated[
        str | None,
        typer.Option("--feature", hidden=True, help="(deprecated) Use --mission"),
    ] = None,
) -> None:
    """Show currently active mission for a mission (auto-detects mission from cwd)."""
    project_root = get_project_root_or_exit()
    check_version_compatibility(project_root, "mission")

    detected_mission = _detect_current_feature(project_root)

    if mission is None and feature is None and not detected_mission:
        console.print(
            "[yellow]No active mission detected.[/yellow]\n"
            "\nUse [cyan]--mission <slug>[/cyan] to specify one, "
            "or run from within a mission worktree."
        )
        # Optionally list available missions
        kitty_specs = project_root / "kitty-specs"
        if kitty_specs.is_dir():
            missions = sorted(
                d.name for d in kitty_specs.iterdir()
                if d.is_dir() and d.name[0:1].isdigit()
            )
            if missions:
                console.print("\n[cyan]Available missions:[/cyan]")
                for slug in missions[:10]:
                    console.print(f"  - {slug}")
                if len(missions) > 10:
                    console.print(f"  ... and {len(missions) - 10} more")
        raise typer.Exit(1)

    mission_slug: str
    if mission is None and feature is None:
        # Neither flag was explicitly provided — use auto-detected mission as-is.
        # (We already exited above when detected_mission was also None.)
        mission_slug = detected_mission  # type: ignore[assignment]
    else:
        try:
            resolved = resolve_selector(
                canonical_value=mission,
                canonical_flag="--mission",
                alias_value=feature,
                alias_flag="--feature",
                suppress_env_var="SPEC_KITTY_SUPPRESS_FEATURE_DEPRECATION",
                command_hint="--mission <slug>",
            )
            mission_slug = resolved.canonical_value
        except typer.BadParameter as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc

    try:
        feature_dir = project_root / "kitty-specs" / mission_slug
        if not feature_dir.exists():
            console.print(f"[red]Mission not found:[/red] {mission_slug}")
            raise typer.Exit(1)

        mission = get_mission_for_feature(feature_dir, project_root)
        context = f"Mission: {mission_slug}"

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


@app.command("create")
def create_cmd(
    from_ticket: Annotated[
        str,
        typer.Option(
            "--from-ticket",
            help="Tracker ticket reference in provider:KEY format (e.g. linear:PRI-42)",
        ),
    ],
) -> None:
    """Fetch a tracker ticket and prepare it as a mission brief.

    Writes the ticket content to .kittify/ticket-context.md so the LLM can
    read it and run /spec-kitty.specify. Records a pending origin so the
    mission-to-ticket link is established automatically when specify completes.

    Example:
        spec-kitty mission create --from-ticket linear:PRI-42
    """
    from specify_cli.sync.feature_flags import is_saas_sync_enabled, saas_sync_disabled_message
    from specify_cli.tracker.config import load_tracker_config, require_repo_root
    from specify_cli.tracker.saas_client import SaaSTrackerClientError
    from specify_cli.tracker.service import TrackerService, TrackerServiceError
    from specify_cli.tracker.ticket_context import write_pending_origin, write_ticket_context

    if not is_saas_sync_enabled():
        typer.secho(saas_sync_disabled_message(), err=True, fg=typer.colors.RED)
        raise typer.Exit(1)

    # Parse provider:KEY
    if ":" not in from_ticket:
        typer.secho(
            "Error: --from-ticket requires format provider:KEY (e.g. linear:PRI-42)",
            err=True, fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    provider, issue_key = from_ticket.split(":", 1)
    provider = provider.strip().lower()
    issue_key = issue_key.strip()

    if not provider or not issue_key:
        typer.secho("Error: Both provider and issue key are required.", err=True, fg=typer.colors.RED)
        raise typer.Exit(1)

    # Locate repo root and load tracker config
    try:
        repo_root = require_repo_root()
    except Exception as exc:  # noqa: BLE001
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc

    config = load_tracker_config(repo_root)
    if config.provider and config.provider != provider:
        typer.secho(
            f"Error: This repo is bound to '{config.provider}', not '{provider}'. "
            f"Run: spec-kitty tracker bind --provider {provider}",
            err=True, fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    # Fetch ticket via the SaaS service
    try:
        service = TrackerService(repo_root)
        results = service.issue_search(provider=provider, query=issue_key, limit=5)
    except (TrackerServiceError, SaaSTrackerClientError) as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc

    # Find exact match on identifier
    ticket = next(
        (t for t in results if (t.get("identifier") or "").upper() == issue_key.upper()),
        results[0] if results else None,
    )
    if ticket is None:
        typer.secho(
            f"Error: Ticket '{issue_key}' not found in {provider}. Check the key and try again.",
            err=True, fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    # Write artefacts
    context_path = write_ticket_context(repo_root, ticket)
    write_pending_origin(repo_root, ticket, provider)

    # Handoff
    console.print()
    console.print(
        f"[green]✓[/green] Ticket [bold]{ticket.get('identifier', issue_key)}[/bold] "
        f"fetched → [dim]{context_path.relative_to(repo_root)}[/dim]"
    )
    console.print(f"  [dim]{ticket.get('title', '')}[/dim]")
    console.print()
    console.print(
        "Run [cyan]/spec-kitty.specify[/cyan] to create the mission from this ticket."
    )
    console.print(
        "The mission will be linked to "
        f"[bold]{provider}:{ticket.get('identifier', issue_key)}[/bold] "
        "automatically on completion."
    )
    console.print()


@app.command("run")
def run_cmd(
    mission_key: Annotated[
        str,
        typer.Argument(help="The reusable custom mission key."),
    ],
    mission_slug: Annotated[
        str,
        typer.Option("--mission", help="Tracked mission slug."),
    ],
    json_output: Annotated[
        bool,
        typer.Option(
            "--json/--no-json",
            help="Emit JSON envelope to stdout instead of a rich panel.",
        ),
    ] = False,
) -> None:
    """Start (or attach to) a runtime for a project-authored custom mission definition."""
    from specify_cli.mission_loader.command import run_custom_mission

    project_root = get_project_root_or_exit()
    result = run_custom_mission(mission_key, mission_slug, project_root)
    _render_envelope(result.envelope, json_output)
    raise typer.Exit(code=result.exit_code)


def _render_envelope(envelope: dict[str, Any], json_output: bool) -> None:
    """Render the mission-run envelope to stdout.

    With ``json_output`` true, prints a stable JSON dump (no key
    sorting; the contract pins the field order). Without it, builds a
    rich :class:`Panel` mirroring the same fields.
    """
    if json_output:
        print(json.dumps(envelope, indent=2, sort_keys=False))
        return
    _render_human(envelope)


def _render_human(envelope: dict[str, Any]) -> None:
    """Render the envelope as a :class:`rich.panel.Panel`."""
    if envelope.get("result") == "success":
        title = "Mission Run Started"
        border = "green"
        body = Text()
        body.append(f"mission_key:  {envelope.get('mission_key')}\n")
        body.append(f"mission_slug: {envelope.get('mission_slug')}\n")
        mission_id = envelope.get("mission_id")
        if mission_id:
            body.append(f"mission_id:   {mission_id}\n")
        body.append(f"feature_dir:  {envelope.get('feature_dir')}\n")
        body.append(f"run_dir:      {envelope.get('run_dir')}")
    else:
        title = str(envelope.get("error_code") or "ERROR")
        border = "red"
        body = Text(str(envelope.get("message") or ""))
        details = envelope.get("details") or {}
        if isinstance(details, dict):
            for key, value in details.items():
                body.append(f"\n  {key}: {value}")

    for warn in envelope.get("warnings", []) or []:
        if isinstance(warn, dict):
            body.append(
                f"\n[warn] {warn.get('code', '')}: {warn.get('message', '')}"
            )

    console.print(Panel(body, title=title, border_style=border))


@app.command("switch", deprecated=True)
def switch_cmd(
    mission_name: str = typer.Argument(..., help="Mission name (no longer supported)"),  # noqa: ARG001
    force: bool = typer.Option(False, "--force", help="(ignored)"),  # noqa: ARG001
) -> None:
    """[REMOVED] Switch active mission - this command was removed in v0.8.0."""
    console.print("[bold red]Error:[/bold red] The 'mission switch' command was removed in v0.8.0.")
    console.print()
    console.print("Mission types are now selected [bold]per mission run[/bold] during [cyan]/spec-kitty.specify[/cyan].")
    console.print()
    console.print("[cyan]New workflow:[/cyan]")
    console.print("  1. Run [bold]/spec-kitty.specify[/bold] to start a new feature")
    console.print("  2. The system will infer and confirm the appropriate mission")
    console.print("  3. Mission is stored in the feature's [dim]meta.json[/dim]")
    console.print()
    console.print("[cyan]To see available missions:[/cyan]")
    console.print("  spec-kitty mission list")
    console.print()
    console.print("[dim]See: https://github.com/your-org/spec-kitty#mission-types[/dim]")
    raise typer.Exit(1)
