"""Status board utilities for AI agents.

This module provides functions that agents can import and call directly
to display beautiful status boards without going through the CLI.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from specify_cli.core.paths import locate_project_root, get_main_repo_root
from specify_cli.status.progress import compute_weighted_progress
from specify_cli.tasks_support import extract_scalar, split_frontmatter

console = Console()


def show_kanban_status(mission_slug: Optional[str] = None) -> dict:
    """Display kanban status board for work packages in a feature.

    This function can be called directly by agents to get a beautiful
    status display without running a CLI command.

    Args:
        mission_slug: Feature slug (e.g., "012-documentation-mission").
                     If None, attempts to auto-detect from current directory.

    Returns:
        dict: Status data including work packages, metrics, and progress

    Example:
        >>> from specify_cli.agent_utils.status import show_kanban_status
        >>> show_kanban_status("012-documentation-mission")
    """
    try:
        cwd = Path.cwd().resolve()
        repo_root = locate_project_root(cwd)

        if repo_root is None:
            console.print("[red]Error:[/red] Not in a spec-kitty project")
            return {"error": "Not in a spec-kitty project"}

        # mission_slug is required; no auto-detection
        if not mission_slug:
            msg = (
                "mission_slug is required. "
                "Pass it explicitly: show_kanban_status('057-my-feature')"
            )
            console.print(f"[red]Error:[/red] {msg}")
            return {"error": msg}

        # Get main repo root for correct path resolution
        main_repo_root = get_main_repo_root(repo_root)

        # Locate feature directory
        feature_dir = main_repo_root / "kitty-specs" / mission_slug

        if not feature_dir.exists():
            console.print(f"[red]Error:[/red] Feature directory not found: {feature_dir}")
            return {"error": f"Feature directory not found: {feature_dir}"}

        tasks_dir = feature_dir / "tasks"

        if not tasks_dir.exists():
            console.print(f"[red]Error:[/red] Tasks directory not found: {tasks_dir}")
            return {"error": f"Tasks directory not found: {tasks_dir}"}

        # Build lane map from event log (canonical source of truth)
        from specify_cli.status.reducer import reduce
        from specify_cli.status.store import read_events
        events = read_events(feature_dir)
        snapshot = reduce(events)
        # snapshot.work_packages: {wp_id: {"lane": ..., ...}}
        event_log_lanes: dict[str, str] = {
            wp_id: str(state.get("lane", "planned"))
            for wp_id, state in snapshot.work_packages.items()
        }

        # Collect all work packages with dependencies (static metadata from frontmatter)
        import re
        work_packages = []
        for wp_file in sorted(tasks_dir.glob("WP*.md")):
            front, body, padding = split_frontmatter(wp_file.read_text(encoding="utf-8-sig"))

            wp_id = extract_scalar(front, "work_package_id")
            title = extract_scalar(front, "title")
            phase = extract_scalar(front, "phase") or "Unknown Phase"

            # Lane comes from event log; default to "planned" for WPs not yet in the log
            lane = event_log_lanes.get(wp_id or "", "planned")

            # Parse dependencies
            dependencies = []
            if "dependencies:" in front:
                dep_match = re.search(r'dependencies:\s*\n((?:\s+-\s+"[^"]+"\s*\n)*)', front, re.MULTILINE)
                if dep_match:
                    dep_text = dep_match.group(1)
                    dependencies = re.findall(r'"([^"]+)"', dep_text)

            work_packages.append({
                "id": wp_id,
                "title": title,
                "lane": lane,
                "phase": phase,
                "file": wp_file.name,
                "dependencies": dependencies
            })

        if not work_packages:
            console.print(f"[yellow]No work packages found in {tasks_dir}[/yellow]")
            return {"error": "No work packages found", "work_packages": []}

        # Group by lane
        by_lane: dict[str, list] = {
            "planned": [], "claimed": [], "in_progress": [], "in_review": [],
            "for_review": [], "approved": [], "done": [], "blocked": [], "canceled": [],
        }
        for wp in work_packages:
            lane = wp["lane"]
            if lane in by_lane:
                by_lane[lane].append(wp)
            else:
                by_lane.setdefault("other", []).append(wp)

        # Calculate metrics
        total = len(work_packages)
        done_count = len(by_lane["done"])
        in_progress = len(by_lane["claimed"]) + len(by_lane["in_progress"]) + len(by_lane["in_review"]) + len(by_lane["for_review"])
        planned_count = len(by_lane["planned"])
        blocked_count = len(by_lane["blocked"])
        canceled_count = len(by_lane["canceled"])
        progress_result = compute_weighted_progress(snapshot)
        progress_pct = round(progress_result.percentage, 1)

        # Analyze parallelization opportunities
        done_wp_ids = {wp["id"] for wp in by_lane["done"]}
        parallel_info = _analyze_parallelization(work_packages, done_wp_ids)

        # Display the status board
        _display_status_board(mission_slug, work_packages, by_lane, total, done_count,
                            in_progress, planned_count, progress_pct, parallel_info)

        # Return structured data
        lane_counts = Counter(wp["lane"] for wp in work_packages)
        return {
            "feature": mission_slug,
            "total_wps": total,
            "by_lane": dict(lane_counts),
            "work_packages": work_packages,
            "progress_percentage": progress_pct,
            "done_count": done_count,
            "in_progress": in_progress,
            "planned_count": planned_count,
            "parallelization": parallel_info
        }

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        return {"error": str(e)}


def _analyze_parallelization(work_packages: list, done_wp_ids: set) -> dict:
    """Analyze which work packages can be started and parallelized.

    Args:
        work_packages: List of all work packages with dependencies
        done_wp_ids: Set of WP IDs that are already done

    Returns:
        dict with 'ready' (WPs that can start now) and 'parallel_groups' (groups that can run together)
    """
    # Find WPs that are ready (all dependencies satisfied)
    ready_wps = []
    for wp in work_packages:
        # Skip if already done or in progress
        if wp["lane"] in ["done", "approved", "in_progress", "claimed", "for_review", "in_review", "canceled"]:
            continue

        # Check if all dependencies are satisfied
        deps = wp.get("dependencies", [])
        if all(dep in done_wp_ids for dep in deps):
            ready_wps.append(wp)

    # Group ready WPs by parallelization potential
    # WPs can run in parallel if they don't depend on each other
    parallel_groups = []
    if ready_wps:
        # Build dependency relationships among ready WPs
        ready_ids = {wp["id"] for wp in ready_wps}

        # Check which ready WPs don't depend on any other ready WPs
        independent = []
        dependent = []

        for wp in ready_wps:
            wp_deps = set(wp.get("dependencies", []))
            if not (wp_deps & ready_ids):  # No dependencies on other ready WPs
                independent.append(wp)
            else:
                dependent.append(wp)

        if independent:
            if len(independent) > 1:
                parallel_groups.append({
                    "type": "parallel",
                    "wps": independent,
                    "note": f"These {len(independent)} WPs can run in parallel"
                })
            else:
                parallel_groups.append({
                    "type": "single",
                    "wps": independent,
                    "note": "Ready to start"
                })

        if dependent:
            parallel_groups.append({
                "type": "sequential",
                "wps": dependent,
                "note": "Must wait for other ready WPs to complete first"
            })

    return {
        "ready_wps": ready_wps,
        "parallel_groups": parallel_groups,
        "can_parallelize": len(ready_wps) > 1 and any(g["type"] == "parallel" for g in parallel_groups)
    }


def _display_status_board(mission_slug: str, work_packages: list, by_lane: dict,
                         total: int, done_count: int, in_progress: int,
                         planned_count: int, progress_pct: float, parallel_info: dict) -> None:
    """Display the rich-formatted status board."""
    # Create title panel
    title_text = Text()
    title_text.append(f"📊 Work Package Status: ", style="bold cyan")
    title_text.append(mission_slug, style="bold white")

    console.print()
    console.print(Panel(title_text, border_style="cyan"))

    # Progress bar
    progress_text = Text()
    progress_text.append(f"Progress: ", style="bold")
    progress_text.append(f"{done_count}/{total}", style="bold green")
    progress_text.append(f" ({progress_pct}%)", style="dim")

    # Create visual progress bar
    bar_width = 40
    filled = int(bar_width * progress_pct / 100)
    bar = "█" * filled + "░" * (bar_width - filled)
    progress_text.append(f"\n{bar}", style="green")

    console.print(progress_text)
    console.print()

    # Kanban board table
    # Note: in_review does NOT get its own column — it folds into "In Progress"
    # with a bright_cyan colour marker to distinguish it visually.

    # Merge in_review WPs into the in_progress display list with a marker
    display_in_progress = list(by_lane.get("in_progress", []))
    in_review_wps = by_lane.get("in_review", [])
    for wp in in_review_wps:
        wp["_display_in_review"] = True
        display_in_progress.append(wp)

    kanban_lanes = [
        ("planned", "Planned", "yellow"),
        ("claimed", "Claimed", "bright_yellow"),
        ("in_progress", "In Progress", "blue"),
        ("for_review", "For Review", "cyan"),
        ("approved", "Approved", "magenta"),
        ("done", "Done", "green"),
        ("blocked", "Blocked", "red"),
        ("canceled", "Canceled", "dim"),
    ]

    table = Table(title="Kanban Board", show_header=True, header_style="bold magenta", border_style="dim")
    for _, label, style in kanban_lanes:
        table.add_column(label, style=style, no_wrap=False, width=16)

    # Find max length for rows
    max_rows = max(
        (len(display_in_progress) if lk == "in_progress" else len(by_lane[lk]))
        for lk, _, _ in kanban_lanes
    ) if work_packages else 0

    # Add rows
    for i in range(max_rows):
        row = []
        for lane_key, _, _ in kanban_lanes:
            lane_data = display_in_progress if lane_key == "in_progress" else by_lane[lane_key]
            if i < len(lane_data):
                wp = lane_data[i]
                title_part = f"{wp['title'][:14]}..." if len(wp['title']) > 14 else wp['title']
                # in_review WPs folded into "In Progress" get bright_cyan colour
                if wp.get("_display_in_review"):
                    cell = f"[bright_cyan]{wp['id']} (review)[/bright_cyan]\n{title_part}"
                else:
                    cell = f"{wp['id']}\n{title_part}"
                row.append(cell)
            else:
                row.append("")
        table.add_row(*row)

    # Add count row
    count_row = [f"[bold]{len(display_in_progress) if lane_key == 'in_progress' else len(by_lane[lane_key])} WPs[/bold]" for lane_key, _, _ in kanban_lanes]
    table.add_row(*count_row, style="dim")

    console.print(table)
    console.print()

    # Next steps section
    if by_lane["for_review"]:
        console.print("[bold cyan]👀 Ready for Review:[/bold cyan]")
        for wp in by_lane["for_review"]:
            console.print(f"  • {wp['id']} - {wp['title']}")
        console.print()

    if by_lane["approved"]:
        console.print("[bold magenta]👍 Approved Awaiting Merge:[/bold magenta]")
        for wp in by_lane["approved"]:
            console.print(f"  • {wp['id']} - {wp['title']}")
        console.print()

    if by_lane["in_progress"]:
        console.print("[bold blue]🔄 In Progress:[/bold blue]")
        for wp in by_lane["in_progress"]:
            console.print(f"  • {wp['id']} - {wp['title']}")
        console.print()

    if by_lane["claimed"]:
        console.print("[bold bright_yellow]🤝 Claimed:[/bold bright_yellow]")
        for wp in by_lane["claimed"]:
            console.print(f"  • {wp['id']} - {wp['title']}")
        console.print()

    if by_lane["blocked"]:
        console.print("[bold red]🚫 Blocked:[/bold red]")
        for wp in by_lane["blocked"]:
            console.print(f"  • {wp['id']} - {wp['title']}")
        console.print()

    if by_lane.get("in_review"):
        console.print("[bold bright_cyan]🔍 In Review (shown in In Progress column):[/bold bright_cyan]")
        for wp in by_lane["in_review"]:
            console.print(f"  • {wp['id']} - {wp['title']}")
        console.print()

    if by_lane["planned"]:
        console.print("[bold yellow]📋 Next Up (Planned):[/bold yellow]")
        # Show first 3 planned items
        for wp in by_lane["planned"][:3]:
            console.print(f"  • {wp['id']} - {wp['title']}")
        if len(by_lane["planned"]) > 3:
            console.print(f"  [dim]... and {len(by_lane['planned']) - 3} more[/dim]")
        console.print()

    # Parallelization opportunities
    if parallel_info["ready_wps"]:
        console.print("[bold magenta]🔀 Parallelization Strategy:[/bold magenta]")

        for group in parallel_info["parallel_groups"]:
            if group["type"] == "parallel":
                console.print(f"\n  [bold green]✨ Can run in PARALLEL:[/bold green]")
                for wp in group["wps"]:
                    console.print(f"     • {wp['id']} - {wp['title']}")
                console.print(f"  [dim]  → All dependencies satisfied, no inter-dependencies[/dim]")

                # Show implementation commands
                console.print(f"\n  [bold]Start commands:[/bold]")
                for wp in group["wps"]:
                    console.print(f"     spec-kitty implement {wp['id']} &")

            elif group["type"] == "single":
                console.print(f"\n  [bold yellow]▶️  Ready to start:[/bold yellow]")
                for wp in group["wps"]:
                    console.print(f"     • {wp['id']} - {wp['title']}")
                    console.print(f"     spec-kitty implement {wp['id']}")

            elif group["type"] == "sequential":
                console.print(f"\n  [bold blue]⏭️  Sequential (blocked by other ready WPs):[/bold blue]")
                for wp in group["wps"]:
                    deps_in_ready = [d for d in wp.get("dependencies", [])
                                    if d in {w["id"] for w in parallel_info["ready_wps"]}]
                    console.print(f"     • {wp['id']} - {wp['title']}")
                    console.print(f"       [dim]Waiting for: {', '.join(deps_in_ready)}[/dim]")

        console.print()
    elif by_lane["planned"] and not by_lane["in_progress"] and not by_lane["claimed"] and not by_lane["for_review"] and not by_lane.get("in_review") and not by_lane["approved"]:
        # All planned WPs are blocked
        console.print("[bold red]⚠️  All remaining WPs are blocked[/bold red]")
        console.print("  Check dependency status above\n")

    # Summary metrics
    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column()
    summary.add_row("Total WPs:", str(total))
    summary.add_row("Completed:", f"[green]{done_count}[/green] ({progress_pct}%)")
    summary.add_row("In Progress:", f"[blue]{in_progress}[/blue]")
    summary.add_row("Planned:", f"[yellow]{planned_count}[/yellow]")

    console.print(Panel(summary, title="[bold]Summary[/bold]", border_style="dim"))
    console.print()
