"""Orchestrate command for autonomous multi-agent feature implementation.

This module implements the `spec-kitty orchestrate` CLI command with:
    - --feature: Start new orchestration for a feature (T038)
    - --status: Show current orchestration progress (T039)
    - --resume: Resume paused orchestration (T040)
    - --abort: Stop orchestration and cleanup (T041)
    - Help text and documentation (T042)

WP08: Initial CLI structure
WP09: Full integration with real agent execution
"""

from __future__ import annotations

import asyncio
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from specify_cli.cli.helpers import get_project_root_or_exit
from specify_cli.core.feature_detection import (
    detect_feature,
    FeatureDetectionError,
)
from specify_cli.orchestrator.config import (
    OrchestrationStatus,
    OrchestratorConfig,
    WPStatus,
    load_config,
)
from specify_cli.orchestrator.integration import (
    CircularDependencyError,
    NoAgentsError,
    ValidationError,
    print_summary,
    run_orchestration_loop,
    validate_agents,
    validate_feature,
)
from specify_cli.orchestrator.scheduler import (
    build_wp_graph,
    get_topological_order,
    validate_wp_graph,
)
from specify_cli.orchestrator.state import (
    OrchestrationRun,
    WPExecution,
    clear_state,
    has_active_orchestration,
    load_state,
    save_state,
)

if TYPE_CHECKING:
    pass

console = Console()


# =============================================================================
# App Definition (T042)
# =============================================================================


app = typer.Typer(
    name="orchestrate",
    help="""
    Orchestrate autonomous feature implementation using multiple AI agents.

    This command coordinates multiple AI coding agents to implement work
    packages in parallel, with automatic review, retry, and fallback handling.

    \b
    USAGE EXAMPLES:
      spec-kitty orchestrate --feature 020-my-feature
      spec-kitty orchestrate --status
      spec-kitty orchestrate --resume
      spec-kitty orchestrate --abort

    \b
    WORKFLOW:
      1. Plan feature with tasks.md and work packages
      2. Configure agents in .kittify/agents.yaml (or use auto-detected defaults)
      3. Run: spec-kitty orchestrate --feature <slug>
      4. Monitor progress: spec-kitty orchestrate --status
      5. If paused due to failure: fix issue and --resume
    """,
    no_args_is_help=True,
)


# =============================================================================
# Helper Functions
# =============================================================================


def detect_current_feature() -> str | None:
    """Auto-detect feature slug from current directory using centralized detection.

    This function uses lenient mode to return None on failure (UI convenience).

    Returns:
        Feature slug or None if not detected.
    """
    try:
        project_root = get_project_root_or_exit(Path.cwd())
        ctx = detect_feature(
            project_root,
            cwd=Path.cwd(),
            mode="lenient"  # Return None instead of raising error
        )
        return ctx.slug if ctx else None
    except Exception:
        # Catch any unexpected errors and return None (lenient behavior)
        return None


def format_elapsed(seconds: float) -> str:
    """Format elapsed time in human-readable format."""
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m"


# =============================================================================
# Status Display (T039)
# =============================================================================


def show_status(repo_root: Path | None = None) -> None:
    """Display current orchestration status.

    Shows progress, active WPs, and agent assignments.
    """
    if repo_root is None:
        repo_root = get_project_root_or_exit()

    state = load_state(repo_root)

    if state is None:
        console.print("[yellow]No orchestration in progress[/yellow]")
        console.print("\nStart with: spec-kitty orchestrate --feature <slug>")
        return

    # Calculate stats
    total = state.wps_total
    completed = state.wps_completed
    failed = state.wps_failed
    pending = total - completed - failed

    progress_pct = (completed / total * 100) if total > 0 else 0

    # Create progress bar
    filled = int(progress_pct / 5)  # 20 chars total
    bar = "[green]" + "█" * filled + "[/green]" + "░" * (20 - filled)

    # Status color
    status_color = {
        OrchestrationStatus.PENDING: "yellow",
        OrchestrationStatus.RUNNING: "green",
        OrchestrationStatus.PAUSED: "red",
        OrchestrationStatus.COMPLETED: "bright_green",
        OrchestrationStatus.FAILED: "red",
    }.get(state.status, "white")

    # Calculate elapsed time
    elapsed = (datetime.now(timezone.utc) - state.started_at).total_seconds()

    # Print header
    console.print()
    console.print(Panel(
        f"[bold]Feature:[/bold] {state.feature_slug}\n"
        f"[bold]Status:[/bold] [{status_color}]{state.status.value}[/{status_color}]\n"
        f"[bold]Progress:[/bold] {bar} {completed}/{total} ({progress_pct:.1f}%)\n"
        f"[bold]Elapsed:[/bold] {format_elapsed(elapsed)}",
        title="Orchestration Status",
        border_style="blue",
    ))

    # Show active WPs
    active_wps = [
        (wp_id, wp)
        for wp_id, wp in state.work_packages.items()
        if wp.status in [WPStatus.IMPLEMENTATION, WPStatus.REVIEW]
    ]

    if active_wps:
        console.print("\n[bold]Active Work Packages:[/bold]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("WP")
        table.add_column("Phase")
        table.add_column("Agent")
        table.add_column("Elapsed")

        for wp_id, wp in active_wps:
            if wp.status == WPStatus.IMPLEMENTATION:
                phase = "implementation"
                agent = wp.implementation_agent or "?"
                started = wp.implementation_started
            else:
                phase = "review"
                agent = wp.review_agent or "?"
                started = wp.review_started

            if started:
                wp_elapsed = (datetime.now(timezone.utc) - started).total_seconds()
                elapsed_str = format_elapsed(wp_elapsed)
            else:
                elapsed_str = "-"

            table.add_row(wp_id, phase, agent, elapsed_str)

        console.print(table)

    # Show completed
    completed_wps = [
        wp_id for wp_id, wp in state.work_packages.items()
        if wp.status == WPStatus.COMPLETED
    ]
    if completed_wps:
        console.print(f"\n[green]Completed:[/green] {', '.join(sorted(completed_wps))}")

    # Show failed
    failed_wps = [
        wp_id for wp_id, wp in state.work_packages.items()
        if wp.status == WPStatus.FAILED
    ]
    if failed_wps:
        console.print(f"[red]Failed:[/red] {', '.join(sorted(failed_wps))}")

    # Show pending
    pending_wps = [
        wp_id for wp_id, wp in state.work_packages.items()
        if wp.status in [WPStatus.PENDING, WPStatus.READY]
    ]
    if pending_wps:
        console.print(f"[yellow]Pending:[/yellow] {', '.join(sorted(pending_wps))}")

    # Show hint for paused state
    if state.status == OrchestrationStatus.PAUSED:
        console.print()
        console.print("[bold red]Orchestration is paused.[/bold red]")
        console.print("Fix any issues and run: spec-kitty orchestrate --resume")

    console.print()


# =============================================================================
# Start Orchestration (T038)
# =============================================================================


async def start_orchestration_async(
    feature_slug: str,
    repo_root: Path,
    impl_agent: str | None = None,
    review_agent: str | None = None,
) -> None:
    """Start new orchestration for a feature (async implementation)."""
    feature_dir = repo_root / "kitty-specs" / feature_slug

    # Validate feature and build graph (T046 - edge case handling)
    console.print(f"Validating feature [bold]{feature_slug}[/bold]...")
    try:
        graph = validate_feature(feature_dir)
    except CircularDependencyError as e:
        console.print(f"[red]Error: Circular dependency detected[/red]")
        console.print(str(e))
        console.print("\nFix the dependency cycle in your tasks.md and WP frontmatter.")
        raise typer.Exit(1)
    except ValidationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Check for existing orchestration
    if has_active_orchestration(repo_root):
        console.print("[red]Error:[/red] An orchestration is already in progress.")
        console.print("Use --status to check progress, --resume to continue, or --abort to cancel.")
        raise typer.Exit(1)

    # Load and validate config
    config_path = repo_root / ".kittify" / "agents.yaml"
    try:
        config = load_config(config_path)
    except Exception as e:
        console.print(f"[red]Error loading config:[/red] {e}")
        console.print("\nCreate config with: spec-kitty agent config init")
        raise typer.Exit(1)

    # Validate agents are available (T046 - no agents installed)
    try:
        available_agents = validate_agents(config)
        console.print(f"Available agents: {', '.join(available_agents)}")
    except NoAgentsError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    # Get topological order
    wp_order = get_topological_order(graph)
    console.print(f"Work packages: {', '.join(wp_order)}")

    # Initialize state
    state = OrchestrationRun(
        run_id=str(uuid.uuid4()),
        feature_slug=feature_slug,
        started_at=datetime.now(timezone.utc),
        status=OrchestrationStatus.PENDING,
        config_hash="",  # TODO: compute hash
        concurrency_limit=config.global_concurrency,
        wps_total=len(wp_order),
        work_packages={
            wp_id: WPExecution(wp_id=wp_id, status=WPStatus.PENDING)
            for wp_id in wp_order
        },
    )

    # Save initial state
    save_state(state, repo_root)

    console.print()
    console.print(Panel(
        f"Starting orchestration for [bold]{feature_slug}[/bold]\n\n"
        f"Work packages: {len(wp_order)}\n"
        f"Concurrency: {config.global_concurrency}\n"
        f"Agents: {', '.join(available_agents)}",
        title="Orchestration Started",
        border_style="green",
    ))

    # Run the full orchestration loop (T043)
    await run_orchestration_loop(
        state, config, feature_dir, repo_root, console,
        override_impl_agent=impl_agent,
        override_review_agent=review_agent,
    )


def start_orchestration(
    feature_slug: str,
    impl_agent: str | None = None,
    review_agent: str | None = None,
) -> None:
    """Start new orchestration for a feature."""
    repo_root = get_project_root_or_exit()
    asyncio.run(start_orchestration_async(feature_slug, repo_root, impl_agent, review_agent))


# =============================================================================
# Resume Orchestration (T040)
# =============================================================================


async def resume_orchestration_async(
    repo_root: Path,
    impl_agent: str | None = None,
    review_agent: str | None = None,
) -> None:
    """Resume paused orchestration (async implementation)."""
    state = load_state(repo_root)

    if state is None:
        console.print("[red]Error:[/red] No orchestration to resume.")
        console.print("Start with: spec-kitty orchestrate --feature <slug>")
        raise typer.Exit(1)

    if state.status == OrchestrationStatus.COMPLETED:
        console.print("[green]Orchestration already completed.[/green]")
        return

    if state.status == OrchestrationStatus.RUNNING:
        console.print("[yellow]Orchestration is already running.[/yellow]")
        console.print("Use --status to check progress.")
        return

    # Set to running
    state.status = OrchestrationStatus.RUNNING
    save_state(state, repo_root)

    # Load config
    config_path = repo_root / ".kittify" / "agents.yaml"
    config = load_config(config_path)

    # Get feature directory
    feature_dir = repo_root / "kitty-specs" / state.feature_slug

    console.print(f"Resuming orchestration for [bold]{state.feature_slug}[/bold]...")
    console.print(f"Progress: {state.wps_completed}/{state.wps_total} completed")

    # Continue orchestration loop with full integration
    await run_orchestration_loop(
        state, config, feature_dir, repo_root, console,
        override_impl_agent=impl_agent,
        override_review_agent=review_agent,
    )


def resume_orchestration(
    impl_agent: str | None = None,
    review_agent: str | None = None,
) -> None:
    """Resume paused orchestration."""
    repo_root = get_project_root_or_exit()
    asyncio.run(resume_orchestration_async(repo_root, impl_agent, review_agent))


# =============================================================================
# Abort Orchestration (T041)
# =============================================================================


def abort_orchestration(cleanup: bool = False) -> None:
    """Abort orchestration and optionally cleanup worktrees."""
    repo_root = get_project_root_or_exit()
    state = load_state(repo_root)

    if state is None:
        console.print("[yellow]No orchestration to abort.[/yellow]")
        return

    console.print(f"Aborting orchestration for [bold]{state.feature_slug}[/bold]...")

    # Update state
    state.status = OrchestrationStatus.FAILED
    state.completed_at = datetime.now(timezone.utc)
    save_state(state, repo_root)

    # Ask about cleanup if not specified
    if not cleanup:
        cleanup = typer.confirm(
            "Remove created worktrees?",
            default=False,
        )

    if cleanup:
        console.print("Cleaning up worktrees...")
        for wp_id, wp in state.work_packages.items():
            if wp.worktree_path and wp.worktree_path.exists():
                try:
                    subprocess.run(
                        ["git", "worktree", "remove", str(wp.worktree_path), "--force"],
                        cwd=repo_root,
                        capture_output=True,
                    )
                    console.print(f"  Removed: {wp.worktree_path.name}")
                except Exception as e:
                    console.print(f"  [yellow]Failed to remove {wp.worktree_path.name}: {e}[/yellow]")

    # Clear state file
    clear_state(repo_root)

    console.print("[yellow]Orchestration aborted.[/yellow]")


# =============================================================================
# Skip WP (T041 extension)
# =============================================================================


def skip_wp(wp_id: str) -> None:
    """Skip a failed WP and continue orchestration."""
    repo_root = get_project_root_or_exit()
    state = load_state(repo_root)

    if state is None:
        console.print("[red]Error:[/red] No orchestration in progress.")
        raise typer.Exit(1)

    if wp_id not in state.work_packages:
        console.print(f"[red]Error:[/red] Unknown work package: {wp_id}")
        raise typer.Exit(1)

    wp = state.work_packages[wp_id]
    if wp.status != WPStatus.FAILED:
        console.print(f"[yellow]WP {wp_id} is not failed (status: {wp.status.value})[/yellow]")
        return

    # Mark as completed (skipped)
    wp.status = WPStatus.COMPLETED
    state.wps_failed -= 1
    state.wps_completed += 1
    save_state(state, repo_root)

    console.print(f"[yellow]Skipped {wp_id}[/yellow]")
    console.print("Use --resume to continue orchestration.")


# =============================================================================
# Main Command (T042)
# =============================================================================


@app.callback(invoke_without_command=True)
def orchestrate(
    ctx: typer.Context,
    feature: str = typer.Option(
        None,
        "--feature",
        "-f",
        help="Feature slug to orchestrate (e.g., 020-my-feature)",
    ),
    status: bool = typer.Option(
        False,
        "--status",
        "-s",
        help="Show current orchestration status and progress",
    ),
    resume: bool = typer.Option(
        False,
        "--resume",
        "-r",
        help="Resume a paused orchestration",
    ),
    abort: bool = typer.Option(
        False,
        "--abort",
        "-a",
        help="Abort orchestration and optionally cleanup worktrees",
    ),
    skip: str = typer.Option(
        None,
        "--skip",
        help="Skip a failed WP and continue (e.g., --skip WP03)",
    ),
    cleanup: bool = typer.Option(
        False,
        "--cleanup",
        help="Also remove worktrees when aborting",
    ),
    impl_agent: str = typer.Option(
        None,
        "--impl-agent",
        "--implementer",
        help="Override implementation agent (e.g., claude, codex, opencode)",
    ),
    review_agent: str = typer.Option(
        None,
        "--review-agent",
        "--reviewer",
        help="Override review agent (e.g., claude, codex, opencode)",
    ),
) -> None:
    """Orchestrate autonomous feature implementation.

    Coordinates multiple AI coding agents to implement work packages
    in parallel, with automatic review, retry, and fallback handling.

    \b
    EXAMPLES:
      Start orchestration for a feature:
        spec-kitty orchestrate --feature 020-my-feature

      Check progress:
        spec-kitty orchestrate --status

      Resume after fixing an issue:
        spec-kitty orchestrate --resume

      Skip a problematic WP and continue:
        spec-kitty orchestrate --skip WP03

      Stop orchestration:
        spec-kitty orchestrate --abort

      Stop and remove worktrees:
        spec-kitty orchestrate --abort --cleanup
    """
    # Handle mutual exclusivity
    options_count = sum([bool(feature), status, resume, abort, bool(skip)])

    if options_count == 0:
        # Auto-detect feature
        detected = detect_current_feature()
        if detected:
            if typer.confirm(f"Start orchestration for {detected}?"):
                start_orchestration(detected, impl_agent=impl_agent, review_agent=review_agent)
                return
        console.print("[red]Error:[/red] No feature specified.")
        console.print("Use: spec-kitty orchestrate --feature <slug>")
        console.print("Or check status: spec-kitty orchestrate --status")
        raise typer.Exit(1)

    if options_count > 1:
        console.print("[red]Error:[/red] Only one of --feature, --status, --resume, --abort, --skip can be used.")
        raise typer.Exit(1)

    # Dispatch to appropriate handler
    if status:
        show_status()
    elif resume:
        resume_orchestration(impl_agent=impl_agent, review_agent=review_agent)
    elif abort:
        abort_orchestration(cleanup=cleanup)
    elif skip:
        skip_wp(skip)
    elif feature:
        start_orchestration(feature, impl_agent=impl_agent, review_agent=review_agent)


__all__ = [
    "app",
    "orchestrate",
    "show_status",
    "start_orchestration",
    "resume_orchestration",
    "abort_orchestration",
    "skip_wp",
]
