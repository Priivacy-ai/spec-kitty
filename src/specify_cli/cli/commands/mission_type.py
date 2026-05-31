"""Mission management CLI commands.

The top-level ``spec-kitty mission-type`` group exposes:

* ``mission-type list [--json]``   — alias for ``charter mission-type list``
  (activated types only, charter-filtered).
* ``mission-type show <id> [--json]`` — fully resolved doctrine MissionType
  definition for an activated mission type.

The older commands in this module (``current``, ``info``, ``create``,
``run``, ``close``, ``switch``) remain on the ``spec-kitty mission``
surface; they operate on per-mission metadata, not doctrine mission types.
"""

from __future__ import annotations

import json
from pathlib import Path
from collections.abc import Iterable
from typing import Annotated, Any

import typer
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from specify_cli.cli.helpers import console, get_project_root_or_exit
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
    help=(
        "Inspect mission types for this project.\n\n"
        "Use 'list' to see activated types (charter-filtered) and "
        "'show <id>' for a full resolved definition.\n\n"
        "Mission types are selected per mission run during /spec-kitty.specify."
    ),
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
        assert detected_mission is not None
        mission_slug = detected_mission
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

        loaded_mission = get_mission_for_feature(feature_dir, project_root)
        context = f"Mission: {mission_slug}"

    except MissionNotFoundError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except MissionError as exc:
        console.print(f"[red]Failed to load active mission:[/red] {exc}")
        raise typer.Exit(1) from exc

    panel = Panel(
        "\n".join(_mission_details_lines(loaded_mission)),
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
    except Exception as exc:  # noqa: BLE001 — repo-root resolution failure is reported to stderr then converted to Exit(1)
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
        body = _build_success_body(envelope)
    else:
        title = str(envelope.get("error_code") or "ERROR")
        border = "red"
        body = _build_error_body(envelope)

    _append_warning_lines(body, envelope.get("warnings"))

    console.print(Panel(body, title=title, border_style=border))


def _build_success_body(envelope: dict[str, Any]) -> Text:
    body = Text()
    body.append(f"mission_key:  {envelope.get('mission_key')}\n")
    body.append(f"mission_slug: {envelope.get('mission_slug')}\n")
    mission_id = envelope.get("mission_id")
    if mission_id:
        body.append(f"mission_id:   {mission_id}\n")
    body.append(f"feature_dir:  {envelope.get('feature_dir')}\n")
    body.append(f"run_dir:      {envelope.get('run_dir')}")
    return body


def _build_error_body(envelope: dict[str, Any]) -> Text:
    body = Text(str(envelope.get("message") or ""))
    details = envelope.get("details") or {}
    if not isinstance(details, dict):
        return body
    for key, value in details.items():
        body.append(f"\n  {key}: {value}")
    return body


def _append_warning_lines(body: Text, warnings: Any) -> None:
    for warn in warnings or []:
        if not isinstance(warn, dict):
            continue
        body.append(f"\n[warn] {warn.get('code', '')}: {warn.get('message', '')}")


@app.command("close")
def close_cmd(
    mission: Annotated[
        str | None,
        typer.Option("--mission", "-f", help="Mission slug (auto-detected from cwd if omitted)"),
    ] = None,
    discard: Annotated[
        bool,
        typer.Option(
            "--discard",
            help="Discard the mission mid-flight: delete the coordination "
                 "branch + all lane branches and tear down all worktrees. "
                 "Without --discard, requires that the mission has already "
                 "been merged (no-op cleanup otherwise).",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Skip the confirmation prompt when --discard is set.",
        ),
    ] = False,
) -> None:
    """Close a mission. Wraps FR-016 lifecycle teardown.

    Without ``--discard``: tear down the coordination worktree only.
    This is a safe no-op after a successful ``spec-kitty merge`` (the
    merge command already runs the same teardown); useful when the
    teardown was skipped (e.g. legacy merge path) or interrupted.

    With ``--discard``: abandon the mission mid-flight. Deletes the
    coordination branch and every lane branch named in
    ``lanes.json``, then tears down the coordination worktree and the
    operator-visible lane worktrees. Requires confirmation unless
    ``--force`` is also passed. The coordination + lane branches are
    deleted with ``git branch -D`` (force-delete) because mid-flight
    abandonment by definition leaves uncommitted or unmerged work.

    Implements FR-016 from
    ``kitty-specs/mission-coordination-branch-atomic-event-log-01KSPTVW``.
    """
    project_root = get_project_root_or_exit()
    repo_root = _resolve_primary_repo_root(project_root)

    # Resolve mission slug.
    mission_slug = mission or _detect_current_feature(project_root)
    if not mission_slug:
        console.print(
            "[red]Error:[/red] No mission specified and no active mission "
            "detected. Use [cyan]--mission <slug>[/cyan]."
        )
        raise typer.Exit(1)

    feature_dir = repo_root / "kitty-specs" / mission_slug
    if not feature_dir.exists():
        console.print(f"[red]Mission not found:[/red] {mission_slug}")
        raise typer.Exit(1)

    # Load meta to get mid8 (required for coordination worktree teardown).
    meta_path = feature_dir / "meta.json"
    mid8_value: str = ""
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if isinstance(meta, dict):
                mid8_value = str(meta.get("mid8") or "").strip()
                if not mid8_value:
                    mission_id_meta = str(meta.get("mission_id") or "").strip()
                    if len(mission_id_meta) >= 8:
                        mid8_value = mission_id_meta[:8]
        except (OSError, json.JSONDecodeError):
            pass

    if discard:
        # Confirm unless --force.
        if not force:
            confirm = typer.confirm(
                f"Discard mission {mission_slug}? This deletes the coordination "
                f"branch, every lane branch, and all worktrees. Unmerged work "
                f"on those branches WILL BE LOST.",
                default=False,
            )
            if not confirm:
                console.print("[yellow]Aborted.[/yellow]")
                raise typer.Exit(1)

        # Load lanes.json (if present) so we know which branches to delete.
        lanes_manifest = None
        try:
            from specify_cli.lanes.persistence import (
                CorruptLanesError,
                MissingLanesError,
                require_lanes_json,
            )

            lanes_manifest = require_lanes_json(feature_dir)
        except (MissingLanesError, CorruptLanesError):
            lanes_manifest = None

        # Delete every lane branch + the coordination/mission branch.
        if lanes_manifest is not None:
            from specify_cli.lanes.branch_naming import lane_branch_name
            try:
                from specify_cli.lanes.merge import PLANNING_LANE_ID
            except ImportError:
                PLANNING_LANE_ID = "lane-planning"  # historical fallback

            for lane in lanes_manifest.lanes:
                if lane.lane_id == PLANNING_LANE_ID:
                    continue
                branch_name = lane_branch_name(mission_slug, lane.lane_id)
                _force_delete_branch_if_exists(repo_root, branch_name)

            _force_delete_branch_if_exists(repo_root, lanes_manifest.mission_branch)
            console.print(
                f"  Deleted {len(lanes_manifest.lanes)} lane branch(es) + "
                f"mission/coordination branch"
            )
        else:
            # No lanes.json -- legacy mission. Best-effort: try the canonical
            # coordination_branch from meta if present.
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    coord_branch = (
                        meta.get("coordination_branch") if isinstance(meta, dict) else None
                    )
                except (OSError, json.JSONDecodeError):
                    coord_branch = None
                if coord_branch:
                    _force_delete_branch_if_exists(repo_root, str(coord_branch))
                    console.print(f"  Deleted coordination branch {coord_branch}")

        # Remove operator-visible lane worktrees.
        if lanes_manifest is not None:
            _remove_lane_worktrees(repo_root, mission_slug, mid8_value, lanes_manifest)

    # Teardown the coordination worktree. Same path as merge.py:1568.
    # Idempotent: no-ops on legacy missions / when already torn down.
    if mid8_value:
        try:
            from specify_cli.coordination import CoordinationWorkspace

            CoordinationWorkspace.teardown(repo_root, mission_slug, mid8_value)
            if CoordinationWorkspace.is_present(repo_root, mission_slug, mid8_value):
                console.print(
                    "[yellow]Warning:[/yellow] coordination worktree still "
                    "present after teardown; manual cleanup may be required."
                )
            else:
                console.print(
                    f"[green]✓[/green] Coordination worktree torn down for "
                    f"{mission_slug}-{mid8_value}"
                )
        except Exception as exc:  # noqa: BLE001 — teardown is best-effort
            console.print(
                f"[yellow]Warning:[/yellow] coordination worktree teardown "
                f"failed (non-fatal): {exc}"
            )

    if discard:
        console.print(f"[green]✓[/green] Mission {mission_slug} discarded.")
    else:
        console.print(f"[green]✓[/green] Mission {mission_slug} closed.")


def _force_delete_branch_if_exists(repo_root: Path, branch_name: str) -> None:
    """Delete a branch with ``git branch -D`` if it exists. No-op otherwise."""
    import subprocess as _subprocess

    rev_parse = _subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/heads/{branch_name}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if rev_parse.returncode != 0:
        return
    _subprocess.run(
        ["git", "branch", "-D", branch_name],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def _remove_lane_worktrees(
    repo_root: Path,
    mission_slug: str,
    mid8_value: str,
    lanes_manifest: Any,
) -> None:
    """Remove every operator-visible lane worktree for this mission."""
    import subprocess as _subprocess

    # Lane worktrees are at .worktrees/<slug>-<mid8>-<lane_id>/ by convention.
    worktrees_root = repo_root / ".worktrees"
    if not worktrees_root.exists():
        return

    # Best-effort: scan worktrees that start with the mission slug.
    prefix_with_mid8 = f"{mission_slug}-{mid8_value}-" if mid8_value else f"{mission_slug}-"
    prefix_legacy = f"{mission_slug}-"
    removed = 0
    for entry in worktrees_root.iterdir():
        if not entry.is_dir():
            continue
        name = entry.name
        if name.endswith("-coord"):
            # Coordination worktree is handled separately.
            continue
        if not (name.startswith(prefix_with_mid8) or name.startswith(prefix_legacy)):
            continue
        _subprocess.run(
            ["git", "-C", str(repo_root), "worktree", "remove", str(entry), "--force"],
            capture_output=True,
            text=True,
            check=False,
        )
        removed += 1
    if removed:
        console.print(f"  Removed {removed} lane worktree(s)")


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


# ---------------------------------------------------------------------------
# FR-016: spec-kitty mission-type list (alias for charter mission-type list)
# FR-017: spec-kitty mission-type show <id>
# ---------------------------------------------------------------------------


@app.command("list")
def list_mission_types(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON.",
    ),
) -> None:
    """List activated mission types for the current project (FR-016).

    Alias for ``spec-kitty charter mission-type list``.

    Returns only mission types that are explicitly activated in this
    project's charter (activation-filtered).  For all doctrine-layer
    types regardless of activation, use ``spec-kitty doctrine mission-type list``.
    """
    from specify_cli.cli.commands.charter.mission_type import (  # noqa: PLC0415
        charter_mission_type_list,
    )

    charter_mission_type_list(json_output=json_output)


@app.command("show")
def show_mission_type(
    mission_type_id: str = typer.Argument(..., help="Mission type ID (e.g. software-dev)."),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON.",
    ),
) -> None:
    """Show the fully resolved MissionType definition for this project (FR-017).

    Displays all fields of the activated mission type:
    id, display_name, action_sequence, governance_refs, template_set,
    source_layer, extends.

    Exits with code 1 and lists registered IDs when ``mission_type_id``
    is not an activated type.
    """
    from charter.mission_type_profiles import (  # noqa: PLC0415
        UnknownMissionTypeError,
        existing_mission_types,
        resolve_action_sequence,
    )
    from doctrine.missions.mission_type_repository import MissionTypeRepository  # noqa: PLC0415

    repo_root = Path.cwd()
    activated_ids = existing_mission_types(repo_root)

    if mission_type_id not in activated_ids:
        err = UnknownMissionTypeError(mission_type_id, registered_ids=activated_ids)
        console.print(f"[red]Error:[/red] {err}")
        raise typer.Exit(1)

    repo = MissionTypeRepository.default()
    mt = repo.get(mission_type_id)
    if mt is None:
        err = UnknownMissionTypeError(mission_type_id, registered_ids=activated_ids)
        console.print(f"[red]Error:[/red] {err}")
        raise typer.Exit(1)

    try:
        action_seq = resolve_action_sequence(mission_type_id, repo_root)
    except UnknownMissionTypeError:
        action_seq = list(mt.action_sequence)

    if json_output:
        data = {
            "id": mt.id,
            "display_name": mt.display_name,
            "action_sequence": action_seq,
            "governance_refs": list(mt.governance_refs),
            "template_set": mt.template_set,
            "source_layer": "built-in",
            "extends": mt.extends,
        }
        print(json.dumps(data, indent=2))
        raise typer.Exit(0)

    # Human-readable panel output.
    from rich.panel import Panel as _Panel  # noqa: PLC0415

    lines: list[str] = [
        f"[cyan]ID:[/cyan] {mt.id}",
        f"[cyan]Display Name:[/cyan] {mt.display_name}",
        "[cyan]Source Layer:[/cyan] built-in",
    ]
    if mt.extends:
        lines.append(f"[cyan]Extends:[/cyan] {mt.extends}")
    lines.append(f"[cyan]Action Sequence:[/cyan] {', '.join(action_seq)}")
    if mt.governance_refs:
        lines.append(f"[cyan]Governance Refs:[/cyan] {', '.join(mt.governance_refs)}")
    else:
        lines.append("[cyan]Governance Refs:[/cyan] (none)")
    if mt.template_set:
        tset_parts = [f"{k}={v}" for k, v in sorted(mt.template_set.items())]
        lines.append(f"[cyan]Template Set:[/cyan] {', '.join(tset_parts)}")
    else:
        lines.append("[cyan]Template Set:[/cyan] (none)")

    console.print(
        _Panel(
            "\n".join(lines),
            title=f"Mission Type · {mt.id}",
            border_style="cyan",
        )
    )
    raise typer.Exit(0)
