"""The ``status`` command family, relocated out of ``tasks.py`` (WP07, #2058).

Mission ``tasks-py-degod-wave2-01KWH9EQ`` FR-001/FR-012: ``_do_status`` + the
14 ``_st_*`` phase helpers + ``_StatusState`` + ``_default_status_ports`` live
here, moved VERBATIM from ``tasks.py``. The module is named
``tasks_status_cmd`` (``_cmd`` suffix) to keep it distinct from the existing
``tasks_status_view`` module, which holds the WP05 PURE aggregation core
(``build_status_view`` / ``build_stale_fallback_results``) this command
orchestrates over. The ``@app.command`` Typer wrapper (``status``) stays in
``tasks.py`` and delegates to :func:`_do_status` (the byte-frozen ``--help``
surface is the registration shim's).

**Orchestration shape** (unchanged): the phase helpers run in the SAME order
as the original single body — resolve → load → flag → render — so the WP05
byte-identical aggregation and the git/clock staleness I/O sequence are intact
(NFR-002). ``_default_status_ports`` constructs ``RealRender(console=console,
indent=2)`` — the ONE indent=2 ``--json`` envelope (WP04 render-seam
unification, C-004); the ``print(ports.render.json_envelope(result))`` emission
moved verbatim inside ``_st_emit_json``.

**Seam bridge** (research.md D1/D7): the relocated bodies reach every patched
seam symbol through a lazy in-function import of the ``tasks`` module
(``from specify_cli.cli.commands.agent import tasks as _tasks``) and call
``_tasks.<attr>(...)``, so every historical ``@patch("...agent.tasks.<sym>")``
/ ``monkeypatch.setattr(tasks, ...)`` keeps INTERCEPTING after the move —
including the ``build_status_view`` sentinel seam
(test_tasks_status_view.py ×2), the conftest ``console`` rebinding, and the
port-adapter construction inside ``_default_status_ports``. ``tasks.py``
re-imports the family in the explicit ``as`` re-export form, so
``tasks.<name>`` stays a module attribute. Symbols with ZERO patch sites and a
canonical home outside ``tasks.py`` are imported directly at module scope
(cycle-safe: none of those modules import ``tasks``).

Per-symbol routing/interception evidence:
``kitty-specs/tasks-py-degod-wave2-01KWH9EQ/seam-checklist.md`` (Layer 4 of
the parity contract).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer

from mission_runtime import MissionArtifactKind
from specify_cli.agent_tasks_ports import TasksPorts
from specify_cli.cli.commands.agent.tasks_parsing_validation import (
    _apply_review_status_flags,
)
from specify_cli.cli.commands.agent.tasks_status_view import (
    StatusRequest,
    StatusView,
    build_stale_fallback_results,
)
from specify_cli.lanes.persistence import MissingLanesError

if TYPE_CHECKING:
    from doctrine.agent_profiles.repository import AgentProfileRepository

    from specify_cli.core.stale_detection import StaleCheckResult
from specify_cli.missions._read_path_resolver import (
    candidate_feature_dir_for_mission,
    resolve_planning_read_dir,
)
from specify_cli.status import (
    PROGRESS_SEMANTICS,
    Lane,
    StatusEvent,
    StatusSnapshot,
    resolve_lane_alias,
)
from specify_cli.task_utils import extract_scalar, split_frontmatter
from specify_cli.workspace.context import get_normalized_wp


def _default_status_ports() -> TasksPorts:
    """Production port bundle for ``status`` (render bound to the module console).

    The ``--json`` leg is the ONE indent=2 envelope, absorbed by the single
    production adapter's constructor (WP04 render-seam unification; C-004
    one-adapter-per-port). Binding the module ``console`` keeps the byte-frozen
    human render AND the ``@patch("...tasks.console.print")`` seams intercepting.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    return TasksPorts(
        fs=_tasks.RealFsReader(),
        coord=_tasks.RealCoordCommitRouter(),
        git=_tasks.RealGitOps(),
        render=_tasks.RealRender(console=_tasks.console, indent=2),
    )


@dataclass
class _StatusState:
    """Mutable orchestration state threaded through ``status``'s phases.

    The single-body command tracked ~20 loose locals across resolve → load →
    flag → render; the phase helpers exchange this one value object instead. Not
    frozen: each phase fills its own slice in the SAME order the original body
    did, so the git/clock staleness I/O — and its exact sequence — stays inside
    the shell (WP05 aggregation parity, NFR-002).
    """

    # --- raw command inputs ---
    mission: str | None
    json_output: bool
    stale_threshold: int
    # --- phase A: resolved dirs ---
    cwd: Path = field(default_factory=Path)
    repo_root: Path = field(default_factory=Path)
    mission_slug: str = ""
    main_repo_root: Path = field(default_factory=Path)
    feature_dir: Path = field(default_factory=Path)
    tasks_dir: Path = field(default_factory=Path)
    # --- phase B: loaded work packages + reduced snapshot ---
    events: list[StatusEvent] = field(default_factory=list)
    snapshot: StatusSnapshot | None = None
    work_packages: list[dict[str, object]] = field(default_factory=list)
    wp_dependencies: dict[str, list[str]] = field(default_factory=dict)
    # --- phase C: review-status flags ---
    review_stall_threshold: int = 0
    stale_verdicts: list[dict[str, object]] = field(default_factory=list)
    stalled_wps: list[dict[str, object]] = field(default_factory=list)


def _st_resolve_dirs(st: _StatusState) -> None:
    """Phase A: repo/mission resolution + the CWD-independent read-dir resolution.

    Write path keeps main-repo-root resolution so canonical serialization pins to
    the primary checkout; the read path routes through the canonical resolver
    (WP08 T037, FR-030) with the legacy worktree-aware fallback preserved.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    st.cwd = Path.cwd().resolve()
    repo_root = _tasks.locate_project_root(st.cwd)
    if repo_root is None:
        raise typer.Exit(1)
    st.repo_root = repo_root

    st.mission_slug = _tasks._find_mission_slug(
        explicit_mission=st.mission, json_output=st.json_output, repo_root=repo_root
    )
    st.main_repo_root, _ = _tasks._ensure_target_branch_checked_out(
        repo_root, st.mission_slug, st.json_output
    )

    # Route through the single guarded read-side seam (WP01/IC-01; FR-002, C-007).
    from specify_cli.missions._read_path_resolver import (
        resolve_handle_to_read_path,
    )

    feature_dir = resolve_handle_to_read_path(st.main_repo_root, st.mission_slug)
    if not feature_dir.exists():
        # Last-ditch fallback to the original worktree-aware path so tests /
        # projects that stand up status files in unusual places still work.
        status_read_root = _tasks.get_status_read_root(st.cwd)
        legacy_dir = candidate_feature_dir_for_mission(status_read_root, st.mission_slug)
        if legacy_dir.exists():
            feature_dir = legacy_dir
        else:
            _tasks.console.print(f"[red]Error:[/red] Mission directory not found: {feature_dir}")
            raise typer.Exit(1)
    st.feature_dir = feature_dir

    # PRIMARY leg — tasks/ is PRIMARY-partition (FR-001 / C-001 per-leg split —
    # WP03 T009). The STATUS leg stays on the coord-aware ``feature_dir`` above.
    st.tasks_dir = resolve_planning_read_dir(
        st.main_repo_root, st.mission_slug, kind=MissionArtifactKind.WORK_PACKAGE_TASK
    ) / "tasks"
    if not st.tasks_dir.exists():
        _tasks.console.print(f"[red]Error:[/red] Tasks directory not found: {st.tasks_dir}")
        raise typer.Exit(1)


def _st_resolve_execution_mode(
    front: str, main_repo_root: Path, mission_slug: str, wp_id: str | None
) -> tuple[str, str]:
    """Resolve ``(execution_mode, workspace_kind)`` for one WP row (verbatim fallbacks)."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    if wp_id is None:
        # No work_package_id in frontmatter — the workspace resolvers require a
        # WP id, so classification is impossible. Take the same frontmatter →
        # default path as the "resolver could not classify" arm below.
        return extract_scalar(front, "execution_mode") or "code_change", "unknown"
    try:
        workspace = _tasks.resolve_workspace_for_wp(main_repo_root, mission_slug, wp_id)
        return workspace.execution_mode, workspace.resolution_kind
    except MissingLanesError:
        # Without lanes.json the resolver cannot return a workspace, but we still
        # want a meaningful execution_mode. Prefer the explicit frontmatter value,
        # then the normalized default, and only fall back to "code_change" if both
        # are missing — never blank.
        execution_mode = extract_scalar(front, "execution_mode") or ""
        if not execution_mode:
            try:
                normalized = get_normalized_wp(main_repo_root, mission_slug, wp_id)
                execution_mode = normalized.metadata.execution_mode or "code_change"
            except Exception:
                execution_mode = "code_change"
        return execution_mode, "unknown"
    except (ValueError, FileNotFoundError):
        # Resolver could not classify; fall back to frontmatter and default.
        return extract_scalar(front, "execution_mode") or "code_change", "unknown"


def _st_load_work_packages(st: _StatusState) -> None:
    """Phase B: reduce the event log + collect the per-WP status rows.

    Loads canonical lanes from the event log (lane is event-log-only), then reads
    each WP's frontmatter into a status row and freezes the declared dependencies
    for the pure ``build_status_view`` readiness map.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    _st_lanes: dict[str, Lane] = {}
    try:
        from specify_cli.status import read_events as _st_read_events
        from specify_cli.status import reduce as _st_reduce

        st.events = _st_read_events(st.feature_dir)
        st.snapshot = _st_reduce(st.events) if st.events else None
        if st.snapshot:
            for _st_wp_id, _st_state in st.snapshot.work_packages.items():
                _st_lanes[_st_wp_id] = Lane(_st_state.get("lane", Lane.GENESIS))
    except Exception:
        st.events = []
        _st_lanes = {}

    # WP05: declared dependencies per WP id, frozen from the SAME frontmatter parse
    # already performed here (no extra file read).
    for wp_file in sorted(st.tasks_dir.glob("WP*.md")):
        front, body, padding = split_frontmatter(wp_file.read_text(encoding="utf-8"))

        wp_id = extract_scalar(front, "work_package_id")
        title = extract_scalar(front, "title")
        deps_raw = extract_scalar(front, "dependencies")
        if isinstance(deps_raw, list):
            wp_deps = [str(dep) for dep in deps_raw]
        elif deps_raw:
            wp_deps = [str(deps_raw)]
        else:
            wp_deps = []
        st.wp_dependencies[wp_id or wp_file.stem] = wp_deps
        lane = resolve_lane_alias(_st_lanes.get(wp_id or wp_file.stem, Lane.GENESIS))
        execution_mode, workspace_kind = _st_resolve_execution_mode(
            front, st.main_repo_root, st.mission_slug, wp_id
        )
        st.work_packages.append(
            {
                "id": wp_id,
                "title": title,
                "lane": lane,
                "phase": extract_scalar(front, "phase") or "Unknown Phase",
                "file": wp_file.name,
                "agent": extract_scalar(front, "agent") or "",
                "agent_profile": extract_scalar(front, "agent_profile") or "",
                "shell_pid": extract_scalar(front, "shell_pid") or "",
                "execution_mode": execution_mode,
                "workspace_kind": workspace_kind,
            }
        )

    if not st.work_packages:
        _tasks.console.print(f"[yellow]No work packages found in {st.tasks_dir}[/yellow]")
        raise typer.Exit(0)


def _st_apply_review_flags(st: _StatusState) -> None:
    """Phase C: annotate rows with stale-verdict + stalled-review warnings."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    st.review_stall_threshold = _tasks._review_stall_threshold_minutes(st.main_repo_root)
    st.stale_verdicts, st.stalled_wps = _apply_review_status_flags(
        st.work_packages,
        tasks_dir=st.tasks_dir,
        events=st.events,
        stall_threshold_minutes=st.review_stall_threshold,
    )


def _st_emit_json(st: _StatusState, ports: TasksPorts) -> None:
    """JSON leg: apply the git-staleness I/O, run the WP05 core, emit via the Render port.

    T031: the ``--json`` envelope is assembled from the pure ``build_status_view``
    aggregation and serialised through ``ports.render.json_envelope`` (``indent=2``
    for ``status``'s own render binding — byte-identical to the pre-rewire dump).
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    from specify_cli.core.stale_detection import check_doing_wps_for_staleness

    doing_wps = [wp for wp in st.work_packages if wp["lane"] == Lane.IN_PROGRESS]
    try:
        stale_results = check_doing_wps_for_staleness(
            main_repo_root=st.main_repo_root,
            mission_slug=st.mission_slug,
            doing_wps=doing_wps,
            threshold_minutes=st.stale_threshold,
        )
    except MissingLanesError as exc:
        stale_results = build_stale_fallback_results(doing_wps, exc)

    for wp in st.work_packages:
        if wp["lane"] == Lane.IN_PROGRESS and wp["id"] in stale_results:
            _tasks._apply_stale_status_fields(wp, stale_results[wp["id"]])

    auto_commit_enabled = _tasks.get_auto_commit_default(st.main_repo_root)
    # WP05: the pure aggregation core owns the kanban rollup + counts + percentages.
    view = _tasks.build_status_view(
        StatusRequest(
            work_packages=st.work_packages,
            snapshot=st.snapshot,
            wp_dependencies=st.wp_dependencies,
        )
    )
    result: dict[str, object] = {
        **_tasks._mission_identity_payload(st.feature_dir),
        "total_wps": view.total_wps,
        "by_lane": dict(view.lane_counts),
        "work_packages": st.work_packages,
        "progress_percentage": view.progress_percentage,
        "progress_semantics": PROGRESS_SEMANTICS,
        "weighted_percentage": view.progress_percentage,
        "done_count": view.done_count,
        "done_percentage": view.done_percentage,
        "stale_wps": view.stale_count,
        "stale_verdicts": st.stale_verdicts,
        "stalled_wps": st.stalled_wps,
        "auto_commit": auto_commit_enabled,
    }
    print(ports.render.json_envelope(result))


def _st_board_cell(
    wp: Any, lane: Lane, main_repo_root: Path, profile_repo: AgentProfileRepository | None
) -> str:
    """Build one kanban cell string (marker + stale/claimed/review decoration)."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    title_truncated = wp["title"][:22] + "..." if len(wp["title"]) > 22 else wp["title"]
    marker = _tasks._get_hic_marker(wp.get("agent_profile"), main_repo_root, repo=profile_repo)
    display_id = f"{marker}{wp['id']}"
    if wp.get("_stale_verdict"):
        return f"[yellow]⚠ {display_id}[/yellow]\n{title_truncated}"
    if lane == Lane.IN_PROGRESS and wp.get("is_stale"):
        return f"[red]⚠️ {display_id}[/red]\n{title_truncated}"
    if wp.get("_stall_label"):
        return f"[yellow]⚠ {display_id} (review)[/yellow]\n{title_truncated}"
    if wp.get("_display_claimed"):
        return f"[blue]{display_id} (claimed)[/blue]\n{title_truncated}"
    if wp.get("_display_in_review"):
        return f"[bright_cyan]{display_id} (review)[/bright_cyan]\n{title_truncated}"
    return f"{display_id}\n{title_truncated}"


def _st_render_overview(ports: TasksPorts, st: _StatusState, view: StatusView) -> None:
    """Render the title panel + done/weighted progress bar via the Render port."""
    from rich.panel import Panel
    from rich.text import Text

    title_text = Text()
    title_text.append("📊 Work Package Status: ", style="bold cyan")
    title_text.append(st.mission_slug, style="bold white")

    ports.render.human("")
    ports.render.human(Panel(title_text, border_style="cyan"))

    progress_text = Text()
    progress_text.append("Done progress: ", style="bold")
    progress_text.append(f"{view.done_count}/{view.total_wps}", style="bold green")
    progress_text.append(f" ({view.done_percentage}%)", style="dim")
    progress_text.append("\nWeighted readiness: ", style="bold")
    progress_text.append(f"{view.progress_percentage}%", style="bold cyan")

    bar_width = 40
    filled = int(bar_width * view.progress_percentage / 100)
    bar = "█" * filled + "░" * (bar_width - filled)
    progress_text.append(f"\n{bar}", style="green")

    ports.render.human(progress_text)
    ports.render.human("")


def _st_render_board(
    ports: TasksPorts, st: _StatusState, view: StatusView, profile_repo: AgentProfileRepository | None
) -> None:
    """Render the kanban board table via the Render port.

    Folds claimed + in_review WPs into the "Doing" column with markers; the row
    objects are the SAME ``view.lanes`` objects, so display-marker mutations
    propagate. GENESIS is excluded; off-board rows land in the "other" bucket.
    """
    from rich.table import Table

    by_lane = view.lanes
    display_in_progress = []
    for wp in by_lane[Lane.CLAIMED]:
        wp["_display_claimed"] = True
        display_in_progress.append(wp)
    display_in_progress.extend(by_lane[Lane.IN_PROGRESS])
    for wp in by_lane.get(Lane.IN_REVIEW, []):
        wp["_display_in_review"] = True
        display_in_progress.append(wp)

    table = Table(title="Kanban Board", show_header=True, header_style="bold magenta", border_style="dim")
    table.add_column("📋 Planned", style="yellow", no_wrap=False, width=25)
    table.add_column("🔄 Doing", style="blue", no_wrap=False, width=25)
    table.add_column("👀 For Review", style="cyan", no_wrap=False, width=25)
    table.add_column("👍 Approved", style="magenta", no_wrap=False, width=25)
    table.add_column("✅ Done", style="green", no_wrap=False, width=25)

    max_rows = max(len(by_lane[Lane.PLANNED]), len(display_in_progress), len(by_lane[Lane.FOR_REVIEW]), len(by_lane[Lane.APPROVED]), len(by_lane[Lane.DONE]))

    display_columns = [
        (Lane.PLANNED, by_lane[Lane.PLANNED]),
        (Lane.IN_PROGRESS, display_in_progress),
        (Lane.FOR_REVIEW, by_lane[Lane.FOR_REVIEW]),
        (Lane.APPROVED, by_lane[Lane.APPROVED]),
        (Lane.DONE, by_lane[Lane.DONE]),
    ]

    for i in range(max_rows):
        row = []
        for lane, lane_list in display_columns:
            if i < len(lane_list):
                row.append(_st_board_cell(lane_list[i], lane, st.main_repo_root, profile_repo))
            else:
                row.append("")
        table.add_row(*row)

    table.add_row(
        f"[bold]{len(by_lane[Lane.PLANNED])} WPs[/bold]",
        f"[bold]{len(display_in_progress)} WPs[/bold]",
        f"[bold]{len(by_lane[Lane.FOR_REVIEW])} WPs[/bold]",
        f"[bold]{len(by_lane[Lane.APPROVED])} WPs[/bold]",
        f"[bold]{len(by_lane[Lane.DONE])} WPs[/bold]",
        style="dim",
    )

    ports.render.human(table)
    ports.render.human("")


def _st_render_arbiter(ports: TasksPorts, st: _StatusState) -> None:
    """Render the arbiter-override history section via the Render port (T034)."""
    try:
        from specify_cli.review.arbiter import get_arbiter_overrides_for_wp

        arbiter_lines: list[str] = []
        for wp in st.work_packages:
            wp_id_raw = wp.get("id")
            wp_id_val = wp_id_raw if isinstance(wp_id_raw, str) else ""
            if not wp_id_val:
                continue
            overrides = get_arbiter_overrides_for_wp(st.feature_dir, wp_id_val)
            for idx, override in enumerate(overrides, start=1):
                cat = override.get("category", "custom")
                arbiter_lines.append(f"  • {wp_id_val} Cycle {idx}: rejected → [yellow]overridden[/yellow] ({cat})")

        if arbiter_lines:
            ports.render.human("[bold yellow]⚖️  Arbiter Override History:[/bold yellow]")
            for line in arbiter_lines:
                ports.render.human(line)
            ports.render.human("")
    except ImportError:
        pass  # review package not yet available


def _st_render_review_queues(
    ports: TasksPorts, st: _StatusState, view: StatusView, profile_repo: AgentProfileRepository | None
) -> None:
    """Render the for_review / approved / done-with-stale-verdict sections."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    by_lane = view.lanes
    if by_lane[Lane.FOR_REVIEW]:
        ports.render.human("[bold cyan]👀 Ready for Review:[/bold cyan]")
        for wp in by_lane[Lane.FOR_REVIEW]:
            marker = _tasks._get_hic_marker(wp.get("agent_profile"), st.main_repo_root, repo=profile_repo)
            ports.render.human(f"  • {marker}{wp['id']} - {wp['title']}")
        ports.render.human("")

    if by_lane[Lane.APPROVED]:
        ports.render.human("[bold magenta]👍 Approved (merge when all WPs approved):[/bold magenta]")
        for wp in by_lane[Lane.APPROVED]:
            marker = _tasks._get_hic_marker(wp.get("agent_profile"), st.main_repo_root, repo=profile_repo)
            line = f"  • {marker}{wp['id']} - {wp['title']}"
            if wp.get("_stale_verdict"):
                line += "  [bold yellow]⚠ review artifact: verdict=rejected[/bold yellow]"
            ports.render.human(line)
        ports.render.human("[dim]   Approved WPs stay here until feature merge. Dependents can start immediately.[/dim]")
        ports.render.human("")

    done_stale = [wp for wp in by_lane[Lane.DONE] if wp.get("_stale_verdict")]
    if done_stale:
        ports.render.human("[bold green]✅ Done (with stale verdict warnings):[/bold green]")
        for wp in done_stale:
            marker = _tasks._get_hic_marker(wp.get("agent_profile"), st.main_repo_root, repo=profile_repo)
            ports.render.human(
                f"  • {marker}{wp['id']} - {wp['title']}"
                "  [bold yellow]⚠ review artifact: verdict=rejected[/bold yellow]"
            )
        ports.render.human("")


def _st_render_active(
    ports: TasksPorts,
    st: _StatusState,
    view: StatusView,
    stale_results: Any,
    profile_repo: AgentProfileRepository | None,
) -> None:
    """Render the claimed / in_progress / in_review sections via the Render port."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    by_lane = view.lanes
    if by_lane[Lane.CLAIMED]:
        ports.render.human("[bold blue]🔄 Claimed (shown in Doing column):[/bold blue]")
        for wp in by_lane[Lane.CLAIMED]:
            marker = _tasks._get_hic_marker(wp.get("agent_profile"), st.main_repo_root, repo=profile_repo)
            agent = wp.get("agent", "unknown")
            ports.render.human(f"  • {marker}{wp['id']} - {wp['title']} [dim](agent: {agent})[/dim]")
        ports.render.human("")

    if by_lane[Lane.IN_PROGRESS]:
        ports.render.human("[bold blue]🔄 In Progress:[/bold blue]")
        stale_wps = []
        for wp in by_lane[Lane.IN_PROGRESS]:
            marker = _tasks._get_hic_marker(wp.get("agent_profile"), st.main_repo_root, repo=profile_repo)
            stale_label = _tasks._render_stale_status(stale_results.get(wp["id"]))
            agent = wp.get("agent", "unknown")
            if wp.get("is_stale"):
                ports.render.human(f"  • [red]⚠️ {marker}{wp['id']}[/red] - {wp['title']} [dim]({stale_label}, agent: {agent})[/dim]")
                stale_wps.append(wp)
            elif stale_label:
                ports.render.human(f"  • {marker}{wp['id']} - {wp['title']} [dim]({stale_label}, agent: {agent})[/dim]")
            else:
                ports.render.human(f"  • {marker}{wp['id']} - {wp['title']}")
        ports.render.human("")

        if stale_wps:
            ports.render.human(f"[yellow]⚠️  {len(stale_wps)} stale WP(s) detected - agents may have stopped without transitioning[/yellow]")
            ports.render.human("[dim]   Run: spec-kitty agent tasks move-task <WP_ID> --to for_review[/dim]")
            ports.render.human("")

    if by_lane.get(Lane.IN_REVIEW):
        ports.render.human("[bold bright_cyan]🔍 In Review (shown in Doing column):[/bold bright_cyan]")
        for wp in by_lane[Lane.IN_REVIEW]:
            marker = _tasks._get_hic_marker(wp.get("agent_profile"), st.main_repo_root, repo=profile_repo)
            line = f"  • {marker}{wp['id']} - {wp['title']}"
            if wp.get("_stall_label"):
                line += f"  [bold yellow]⚠ {wp['_stall_label']}[/bold yellow]"
            ports.render.human(line)
        ports.render.human("")


def _st_render_planned(
    ports: TasksPorts, st: _StatusState, view: StatusView, profile_repo: AgentProfileRepository | None
) -> None:
    """Render the "Next Up (Planned)" section via the Render port."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    by_lane = view.lanes
    if by_lane[Lane.PLANNED]:
        ports.render.human("[bold yellow]📋 Next Up (Planned):[/bold yellow]")
        for wp in by_lane[Lane.PLANNED][:3]:
            marker = _tasks._get_hic_marker(wp.get("agent_profile"), st.main_repo_root, repo=profile_repo)
            ports.render.human(f"  • {marker}{wp['id']} - {wp['title']}")
        if len(by_lane[Lane.PLANNED]) > 3:
            ports.render.human(f"  [dim]... and {len(by_lane[Lane.PLANNED]) - 3} more[/dim]")
        ports.render.human("")


def _st_render_summary(ports: TasksPorts, st: _StatusState, view: StatusView) -> None:
    """Render the summary panel + the "Next action" hint via the Render port."""
    from specify_cli.cli.commands.agent import tasks as _tasks
    from rich.panel import Panel
    from rich.table import Table

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column()
    summary.add_row("Total WPs:", str(view.total_wps))
    summary.add_row("Completed:", f"[green]{view.done_count}[/green] ({view.done_percentage}%)")
    summary.add_row("Weighted readiness:", f"[cyan]{view.progress_percentage}%[/cyan]")
    summary.add_row("In Progress:", f"[blue]{view.in_progress_count}[/blue]")
    summary.add_row("Planned:", f"[yellow]{view.planned_count}[/yellow]")

    auto_commit_enabled = _tasks.get_auto_commit_default(st.main_repo_root)
    auto_commit_label = "[green]enabled[/green]" if auto_commit_enabled else "[yellow]disabled[/yellow]"
    summary.add_row("Auto-commit:", auto_commit_label)

    ports.render.human(Panel(summary, title="[bold]Summary[/bold]", border_style="dim"))

    ports.render.human("[bold]▶ Next action:[/bold]")
    ports.render.human(f"  [cyan]spec-kitty next --agent <your-name> --mission {st.mission_slug}[/cyan]")
    ports.render.human("[dim]  This command tells you exactly what to do next based on the dependency graph.[/dim]")
    ports.render.human("")


def _st_render_human(st: _StatusState, ports: TasksPorts) -> None:
    """Human leg: run the WP05 core, apply staleness, render the board via the Render port.

    T031: every emission routes through ``ports.render.human`` (bound to the module
    ``console`` in production — byte-identical + patch-seam-preserving). The pure
    ``build_status_view`` owns the rollup/counts; the shell owns only the
    git/clock staleness I/O and the drawing.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    from specify_cli.core.stale_detection import check_doing_wps_for_staleness

    view = _tasks.build_status_view(
        StatusRequest(
            work_packages=st.work_packages,
            snapshot=st.snapshot,
            wp_dependencies=st.wp_dependencies,
        )
    )
    by_lane = view.lanes

    try:
        stale_results = check_doing_wps_for_staleness(
            main_repo_root=st.main_repo_root,
            mission_slug=st.mission_slug,
            doing_wps=by_lane[Lane.IN_PROGRESS],
            threshold_minutes=st.stale_threshold,
        )
    except MissingLanesError as exc:
        stale_results = build_stale_fallback_results(by_lane[Lane.IN_PROGRESS], exc)

    try:
        from doctrine.agent_profiles.repository import AgentProfileRepository

        profile_repo: AgentProfileRepository | None = AgentProfileRepository(
            built_in_dir=st.main_repo_root / "src" / "doctrine" / "agent_profiles" / "built-in"
        )
    except Exception:
        profile_repo = None

    for wp in by_lane[Lane.IN_PROGRESS]:
        wp_id = wp["id"]
        if wp_id in stale_results:
            _tasks._apply_stale_status_fields(wp, stale_results[wp_id])
        else:
            wp["is_stale"] = False

    _st_render_overview(ports, st, view)
    _st_render_board(ports, st, view, profile_repo)
    _st_render_arbiter(ports, st)
    _st_render_review_queues(ports, st, view, profile_repo)
    _st_render_active(ports, st, view, stale_results, profile_repo)
    _st_render_planned(ports, st, view, profile_repo)
    _st_render_summary(ports, st, view)


def _do_status(
    mission: str | None,
    json_output: bool,
    stale_threshold: int,
    *,
    ports: TasksPorts | None = None,
) -> None:
    """Orchestrate ``status`` over the WP05 ``build_status_view`` core + the Render port.

    ``ports=None`` builds the production bundle (Render bound to the module
    ``console`` with an ``indent=2`` JSON envelope). Tests inject a Fake bundle to
    observe the rendered views/envelopes (T032). The phase helpers run in the SAME
    order as the original single body: resolve → load → flag → render — so the
    WP05 byte-identical aggregation and the git/clock staleness sequence are intact.
    """
    from specify_cli.cli.commands.agent import tasks as _tasks
    ports = ports or _default_status_ports()
    st = _StatusState(mission=mission, json_output=json_output, stale_threshold=stale_threshold)
    try:
        _st_resolve_dirs(st)
        _st_load_work_packages(st)
        _st_apply_review_flags(st)
        if st.json_output:
            _st_emit_json(st, ports)
            return
        _st_render_human(st, ports)
    except typer.Exit:
        raise
    except Exception as e:
        _tasks._output_error(json_output, str(e))
        raise typer.Exit(1) from None


# ===========================================================================
# WP09 (tasks-py-degod-wave2-01KWH9EQ / FR-008, IC-07): the final
# registration-shim sweep relocates the status-family stragglers that remained
# ``tasks.py``-resident after WP07 — the review-stall threshold reader
# (``_review_stall_threshold_minutes``), the human-in-charge marker
# (``_get_hic_marker``) and the staleness shapers
# (``_apply_stale_status_fields`` / ``_render_stale_status``). Moved VERBATIM
# (no patched seam symbol appears in their bodies — the lazy ``yaml`` /
# doctrine-repository imports stay in-function). The family call sites above
# keep routing through ``_tasks.<attr>``, so the historical
# ``@patch("...agent.tasks.<sym>")`` contracts keep INTERCEPTING; ``tasks.py``
# re-imports each name in the explicit ``as`` re-export form (NFR-002).
# ===========================================================================


def _review_stall_threshold_minutes(repo_root: Path) -> int:
    """Read review.stall_threshold_minutes from .kittify/config.yaml."""
    config_file = repo_root / ".kittify" / "config.yaml"
    if not config_file.exists():
        return 30
    try:
        import yaml  # noqa: PLC0415

        config: dict[str, Any] = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
        value = config.get("review", {}).get("stall_threshold_minutes", 30)
        return int(value)
    except (AttributeError, OSError, TypeError, ValueError):
        return 30


def _get_hic_marker(
    agent_profile: object,
    repo_root: Path,
    *,
    repo: AgentProfileRepository | None = None,
) -> str:
    """Return a marker when the work package profile is a human-run sentinel.

    Accepts ``object`` because the callers read ``agent_profile`` out of the
    heterogeneous ``dict[str, object]`` status rows; a non-``str`` (or falsy)
    value yields no marker, exactly as the historical ``if not agent_profile``
    guard did for ``None``/empty strings.
    """
    if not isinstance(agent_profile, str) or not agent_profile:
        return ""

    try:
        from doctrine.agent_profiles.repository import AgentProfileRepository

        profile_repo = repo
        if profile_repo is None:
            built_in_dir = repo_root / "src" / "doctrine" / "agent_profiles" / "built-in"
            profile_repo = AgentProfileRepository(built_in_dir=built_in_dir)

        profile = profile_repo.get(agent_profile)
        if profile and profile.sentinel:
            return "👤 "
    except Exception:
        return ""

    return ""


def _apply_stale_status_fields(wp: dict[str, Any], stale_result: StaleCheckResult) -> None:
    """Populate canonical and deprecated stale fields from one source of truth."""
    stale_payload = stale_result.stale.to_dict()
    wp["stale"] = stale_payload
    wp["is_stale"] = stale_result.is_stale
    wp["minutes_since_commit"] = stale_payload["minutes_since_commit"]
    wp["worktree_exists"] = stale_result.worktree_exists


def _render_stale_status(stale_result: StaleCheckResult | None) -> str | None:
    """Return a human-readable stale label for in-progress work packages."""
    if stale_result is None:
        return None

    if stale_result.stale.status == "not_applicable" and stale_result.stale.reason == "planning_artifact_repo_root_shared_workspace":
        return "stale: n/a (repo-root planning work)"

    if getattr(stale_result, "error", None):
        return "stale: unavailable"

    if stale_result.is_stale:
        mins = stale_result.minutes_since_commit
        return f"stale: {mins}m"

    return None
