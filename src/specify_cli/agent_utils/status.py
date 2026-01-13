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

from specify_cli.core.paths import locate_project_root
from specify_cli.tasks_support import extract_scalar, split_frontmatter

console = Console()


def show_kanban_status(feature_slug: Optional[str] = None) -> dict:
    """Display kanban status board for work packages in a feature.

    This function can be called directly by agents to get a beautiful
    status display without running a CLI command.

    Args:
        feature_slug: Feature slug (e.g., "012-documentation-mission").
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

        # Auto-detect feature if not provided
        if not feature_slug:
            feature_slug = _auto_detect_feature(repo_root)
            if not feature_slug:
                console.print("[red]Error:[/red] Could not auto-detect feature")
                return {"error": "Could not auto-detect feature"}

        # Get main repo root for correct path resolution
        main_repo_root = _get_main_repo_root(repo_root)

        # Locate feature directory
        feature_dir = main_repo_root / "kitty-specs" / feature_slug

        if not feature_dir.exists():
            console.print(f"[red]Error:[/red] Feature directory not found: {feature_dir}")
            return {"error": f"Feature directory not found: {feature_dir}"}

        tasks_dir = feature_dir / "tasks"

        if not tasks_dir.exists():
            console.print(f"[red]Error:[/red] Tasks directory not found: {tasks_dir}")
            return {"error": f"Tasks directory not found: {tasks_dir}"}

        # Collect all work packages with dependencies
        work_packages = []
        for wp_file in sorted(tasks_dir.glob("WP*.md")):
            front, body, padding = split_frontmatter(wp_file.read_text(encoding="utf-8"))

            wp_id = extract_scalar(front, "work_package_id")
            title = extract_scalar(front, "title")
            lane = extract_scalar(front, "lane") or "unknown"
            phase = extract_scalar(front, "phase") or "Unknown Phase"

            # Parse dependencies
            dependencies = []
            if "dependencies:" in front:
                import re
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
        by_lane = {"planned": [], "doing": [], "for_review": [], "done": []}
        for wp in work_packages:
            lane = wp["lane"]
            if lane in by_lane:
                by_lane[lane].append(wp)
            else:
                by_lane.setdefault("other", []).append(wp)

        # Calculate metrics
        total = len(work_packages)
        done_count = len(by_lane["done"])
        in_progress = len(by_lane["doing"]) + len(by_lane["for_review"])
        planned_count = len(by_lane["planned"])
        progress_pct = round((done_count / total * 100), 1) if total > 0 else 0

        # Analyze parallelization opportunities
        done_wp_ids = {wp["id"] for wp in by_lane["done"]}
        parallel_info = _analyze_parallelization(work_packages, done_wp_ids)

        # Display the status board
        _display_status_board(feature_slug, work_packages, by_lane, total, done_count,
                            in_progress, planned_count, progress_pct, parallel_info)

        # Return structured data
        lane_counts = Counter(wp["lane"] for wp in work_packages)
        return {
            "feature": feature_slug,
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
        if wp["lane"] in ["done", "doing", "for_review"]:
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


def _display_status_board(feature_slug: str, work_packages: list, by_lane: dict,
                         total: int, done_count: int, in_progress: int,
                         planned_count: int, progress_pct: float, parallel_info: dict) -> None:
    """Display the rich-formatted status board."""
    # Create title panel
    title_text = Text()
    title_text.append(f"📊 Work Package Status: ", style="bold cyan")
    title_text.append(feature_slug, style="bold white")

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
    table = Table(title="Kanban Board", show_header=True, header_style="bold magenta", border_style="dim")
    table.add_column("📋 Planned", style="yellow", no_wrap=False, width=25)
    table.add_column("🔄 Doing", style="blue", no_wrap=False, width=25)
    table.add_column("👀 For Review", style="cyan", no_wrap=False, width=25)
    table.add_column("✅ Done", style="green", no_wrap=False, width=25)

    # Find max length for rows
    max_rows = max(len(by_lane["planned"]), len(by_lane["doing"]),
                   len(by_lane["for_review"]), len(by_lane["done"]))

    # Add rows
    for i in range(max_rows):
        row = []
        for lane in ["planned", "doing", "for_review", "done"]:
            if i < len(by_lane[lane]):
                wp = by_lane[lane][i]
                cell = f"{wp['id']}\n{wp['title'][:22]}..." if len(wp['title']) > 22 else f"{wp['id']}\n{wp['title']}"
                row.append(cell)
            else:
                row.append("")
        table.add_row(*row)

    # Add count row
    table.add_row(
        f"[bold]{len(by_lane['planned'])} WPs[/bold]",
        f"[bold]{len(by_lane['doing'])} WPs[/bold]",
        f"[bold]{len(by_lane['for_review'])} WPs[/bold]",
        f"[bold]{len(by_lane['done'])} WPs[/bold]",
        style="dim"
    )

    console.print(table)
    console.print()

    # Next steps section
    if by_lane["for_review"]:
        console.print("[bold cyan]👀 Ready for Review:[/bold cyan]")
        for wp in by_lane["for_review"]:
            console.print(f"  • {wp['id']} - {wp['title']}")
        console.print()

    if by_lane["doing"]:
        console.print("[bold blue]🔄 In Progress:[/bold blue]")
        for wp in by_lane["doing"]:
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
                    console.print(f"     spec-kitty implement {wp['id']} --base WP08 &")

            elif group["type"] == "single":
                console.print(f"\n  [bold yellow]▶️  Ready to start:[/bold yellow]")
                for wp in group["wps"]:
                    console.print(f"     • {wp['id']} - {wp['title']}")
                    console.print(f"     spec-kitty implement {wp['id']} --base WP08")

            elif group["type"] == "sequential":
                console.print(f"\n  [bold blue]⏭️  Sequential (blocked by other ready WPs):[/bold blue]")
                for wp in group["wps"]:
                    deps_in_ready = [d for d in wp.get("dependencies", [])
                                    if d in {w["id"] for w in parallel_info["ready_wps"]}]
                    console.print(f"     • {wp['id']} - {wp['title']}")
                    console.print(f"       [dim]Waiting for: {', '.join(deps_in_ready)}[/dim]")

        console.print()
    elif by_lane["planned"] and not by_lane["doing"] and not by_lane["for_review"]:
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


def _get_main_repo_root(current_path: Path) -> Path:
    """Get the main repository root, even if called from a worktree."""
    git_file = current_path / ".git"

    if git_file.is_file():
        git_content = git_file.read_text().strip()
        if git_content.startswith("gitdir:"):
            gitdir = Path(git_content.split(":", 1)[1].strip())
            main_git_dir = gitdir.parent.parent
            main_repo_root = main_git_dir.parent
            return main_repo_root

    return current_path


def _auto_detect_feature(repo_root: Path) -> Optional[str]:
    """Auto-detect feature slug from git branch or current directory."""
    import re
    import subprocess

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True
        )
        branch_name = result.stdout.strip()

        # Strip -WPxx suffix if present
        match = re.match(r"(\d{3}-[\w-]+)", branch_name)
        if match:
            return match.group(1)

    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return None
