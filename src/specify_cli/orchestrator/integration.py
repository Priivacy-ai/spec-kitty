"""Integration module for connecting orchestration components.

This module integrates all orchestrator components into a working system:
    - Main orchestration loop (T043)
    - Progress display with Rich Live (T044)
    - Summary report on completion (T045)
    - Edge case handling (T046)

Implemented in WP09.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from specify_cli.orchestrator.agents import detect_installed_agents, get_invoker, InvocationResult
from specify_cli.orchestrator.config import (
    OrchestrationStatus,
    OrchestratorConfig,
    WPStatus,
)
from specify_cli.orchestrator.executor import (
    ExecutionContext,
    WorktreeCreationError,
    create_worktree,
    execute_with_logging,
    get_log_path,
    get_worktree_path,
    worktree_exists,
)
from specify_cli.orchestrator.monitor import (
    apply_fallback,
    escalate_to_human,
    execute_with_retry,
    is_success,
    transition_wp_lane,
    update_wp_progress,
)
from specify_cli.orchestrator.scheduler import (
    ConcurrencyManager,
    DependencyGraphError,
    SchedulerState,
    build_wp_graph,
    get_ready_wps,
    is_single_agent_mode,
    select_agent,
    select_agent_from_user_config,
    select_review_agent,
    select_review_agent_from_user_config,
    single_agent_review_delay,
    validate_wp_graph,
)
from specify_cli.orchestrator.state import (
    OrchestrationRun,
    WPExecution,
    save_state,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions (T046)
# =============================================================================


class OrchestrationError(Exception):
    """Base exception for orchestration errors."""

    pass


class CircularDependencyError(OrchestrationError):
    """Raised when circular dependencies detected in WP graph."""

    pass


class NoAgentsError(OrchestrationError):
    """Raised when no agents are available for orchestration."""

    pass


class ValidationError(OrchestrationError):
    """Raised when pre-flight validation fails."""

    pass


# =============================================================================
# Validation (T046)
# =============================================================================


def validate_feature(feature_dir: Path) -> dict[str, list[str]]:
    """Validate feature directory and build dependency graph.

    Args:
        feature_dir: Path to feature directory.

    Returns:
        Validated dependency graph.

    Raises:
        ValidationError: If feature is invalid.
        CircularDependencyError: If circular dependencies detected.
    """
    if not feature_dir.exists():
        raise ValidationError(f"Feature directory not found: {feature_dir}")

    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists():
        raise ValidationError(
            f"No tasks directory found. Run /spec-kitty.tasks first."
        )

    # Build and validate graph
    try:
        graph = build_wp_graph(feature_dir)
    except Exception as e:
        raise ValidationError(f"Failed to build dependency graph: {e}")

    if not graph:
        raise ValidationError("No work packages found in tasks directory.")

    try:
        validate_wp_graph(graph)
    except DependencyGraphError as e:
        if "Circular" in str(e):
            raise CircularDependencyError(str(e))
        raise ValidationError(str(e))

    return graph


def validate_agents(config: OrchestratorConfig) -> list[str]:
    """Validate that required agents are available.

    Args:
        config: Orchestrator configuration.

    Returns:
        List of available agent IDs.

    Raises:
        NoAgentsError: If no agents are available.
    """
    installed = detect_installed_agents()
    enabled = [
        aid for aid, ac in config.agents.items()
        if ac.enabled and aid in installed
    ]

    if not enabled:
        raise NoAgentsError(
            "No agents available for orchestration.\n\n"
            "Install at least one agent:\n"
            "  npm install -g @anthropic-ai/claude-code\n"
            "  npm install -g codex\n"
            "  npm install -g opencode\n\n"
            "Or enable an installed agent in .kittify/agents.yaml"
        )

    return enabled


# =============================================================================
# Progress Display (T044)
# =============================================================================


def create_status_table(state: OrchestrationRun) -> Table:
    """Create status table for live display.

    Args:
        state: Current orchestration state.

    Returns:
        Rich Table with WP statuses.
    """
    table = Table(
        title=f"[bold]Orchestration: {state.feature_slug}[/bold]",
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("WP", style="cyan", width=8)
    table.add_column("Status", width=14)
    table.add_column("Agent", style="green", width=15)
    table.add_column("Time", style="yellow", width=10)

    # Sort WPs by ID for consistent display
    sorted_wps = sorted(state.work_packages.items(), key=lambda x: x[0])

    for wp_id, wp in sorted_wps:
        # Status with color
        status_styles = {
            WPStatus.PENDING: "[dim]pending[/dim]",
            WPStatus.READY: "[yellow]ready[/yellow]",
            WPStatus.IMPLEMENTATION: "[blue]implementing[/blue]",
            WPStatus.REVIEW: "[magenta]reviewing[/magenta]",
            WPStatus.REWORK: "[yellow]rework[/yellow]",
            WPStatus.COMPLETED: "[green]done[/green]",
            WPStatus.FAILED: "[red]failed[/red]",
        }
        status = status_styles.get(wp.status, wp.status.value)

        # Agent info
        if wp.status == WPStatus.IMPLEMENTATION:
            agent = wp.implementation_agent or "-"
            started = wp.implementation_started
        elif wp.status == WPStatus.REVIEW:
            agent = wp.review_agent or "-"
            started = wp.review_started
        else:
            agent = "-"
            started = None

        # Elapsed time
        if started:
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            if elapsed < 60:
                time_str = f"{int(elapsed)}s"
            elif elapsed < 3600:
                time_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
            else:
                time_str = f"{int(elapsed // 3600)}h {int((elapsed % 3600) // 60)}m"
        else:
            time_str = "-"

        table.add_row(wp_id, status, agent, time_str)

    return table


def create_progress_panel(state: OrchestrationRun) -> Panel:
    """Create progress panel with overall status.

    Args:
        state: Current orchestration state.

    Returns:
        Rich Panel with progress info.
    """
    total = state.wps_total
    completed = state.wps_completed
    failed = state.wps_failed
    in_progress = sum(
        1 for wp in state.work_packages.values()
        if wp.status in [WPStatus.IMPLEMENTATION, WPStatus.REVIEW]
    )
    pending = total - completed - failed - in_progress

    # Progress bar
    pct = (completed / total * 100) if total > 0 else 0
    filled = int(pct / 5)  # 20 chars
    bar = "[green]" + "█" * filled + "[/green]" + "░" * (20 - filled)

    # Elapsed time
    elapsed = (datetime.now(timezone.utc) - state.started_at).total_seconds()
    if elapsed < 60:
        elapsed_str = f"{int(elapsed)}s"
    elif elapsed < 3600:
        elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
    else:
        elapsed_str = f"{int(elapsed // 3600)}h {int((elapsed % 3600) // 60)}m"

    # Status color
    status_color = {
        OrchestrationStatus.RUNNING: "green",
        OrchestrationStatus.PAUSED: "yellow",
        OrchestrationStatus.COMPLETED: "bright_green",
        OrchestrationStatus.FAILED: "red",
    }.get(state.status, "white")

    content = (
        f"[bold]Status:[/bold] [{status_color}]{state.status.value}[/{status_color}]\n"
        f"[bold]Progress:[/bold] {bar} {completed}/{total} ({pct:.0f}%)\n"
        f"[bold]Elapsed:[/bold] {elapsed_str}\n"
        f"[bold]Active:[/bold] {in_progress}  [bold]Pending:[/bold] {pending}  "
        f"[bold]Failed:[/bold] {failed}"
    )

    return Panel(content, border_style="blue")


def create_live_display(state: OrchestrationRun) -> Table:
    """Create combined live display.

    Args:
        state: Current orchestration state.

    Returns:
        Rich Table combining progress and status.
    """
    from rich.layout import Layout

    # Just return the status table for simplicity
    # Progress is shown in the table title area
    table = create_status_table(state)

    # Add progress summary row
    total = state.wps_total
    completed = state.wps_completed
    pct = (completed / total * 100) if total > 0 else 0
    elapsed = (datetime.now(timezone.utc) - state.started_at).total_seconds()
    elapsed_str = f"{int(elapsed)}s" if elapsed < 60 else f"{int(elapsed // 60)}m"

    table.caption = f"Progress: {completed}/{total} ({pct:.0f}%) | Elapsed: {elapsed_str}"

    return table


# =============================================================================
# Summary Report (T045)
# =============================================================================


def print_summary(state: OrchestrationRun, console: Console) -> None:
    """Print orchestration summary report.

    Args:
        state: Completed orchestration state.
        console: Rich console for output.
    """
    # Calculate duration
    if state.completed_at:
        duration = (state.completed_at - state.started_at).total_seconds()
    else:
        duration = (datetime.now(timezone.utc) - state.started_at).total_seconds()

    # Format duration
    if duration < 60:
        duration_str = f"{duration:.1f} seconds"
    elif duration < 3600:
        duration_str = f"{duration / 60:.1f} minutes"
    else:
        duration_str = f"{duration / 3600:.1f} hours"

    # Collect agent usage stats
    agents_used: set[str] = set()
    for wp in state.work_packages.values():
        if wp.implementation_agent:
            agents_used.add(wp.implementation_agent)
        if wp.review_agent:
            agents_used.add(wp.review_agent)

    # Status color
    if state.status == OrchestrationStatus.COMPLETED and state.wps_failed == 0:
        status_color = "green"
        status_text = "COMPLETED SUCCESSFULLY"
    elif state.status == OrchestrationStatus.COMPLETED:
        status_color = "yellow"
        status_text = "COMPLETED WITH FAILURES"
    elif state.status == OrchestrationStatus.PAUSED:
        status_color = "yellow"
        status_text = "PAUSED"
    else:
        status_color = "red"
        status_text = "FAILED"

    # Build summary content
    content = (
        f"[bold {status_color}]{status_text}[/bold {status_color}]\n\n"
        f"[bold]Feature:[/bold] {state.feature_slug}\n"
        f"[bold]Duration:[/bold] {duration_str}\n"
        f"\n"
        f"[bold]Work Packages:[/bold]\n"
        f"  Total:     {state.wps_total}\n"
        f"  Completed: {state.wps_completed}\n"
        f"  Failed:    {state.wps_failed}\n"
        f"\n"
        f"[bold]Execution Stats:[/bold]\n"
        f"  Agents Used:     {', '.join(sorted(agents_used)) if agents_used else 'None'}\n"
        f"  Peak Parallelism: {state.parallel_peak}\n"
        f"  Total Invocations: {state.total_agent_invocations}"
    )

    console.print()
    console.print("=" * 60)
    console.print(
        Panel(
            content,
            title="Orchestration Summary",
            border_style=status_color,
        )
    )

    # Show failed WPs if any
    failed_wps = [
        (wp_id, wp)
        for wp_id, wp in state.work_packages.items()
        if wp.status == WPStatus.FAILED
    ]
    if failed_wps:
        console.print(f"\n[red]Failed Work Packages:[/red]")
        for wp_id, wp in failed_wps:
            error = wp.last_error or "Unknown error"
            if len(error) > 80:
                error = error[:80] + "..."
            console.print(f"  {wp_id}: {error}")
        console.print("\nCheck logs in .kittify/logs/ for details")

    console.print()


# =============================================================================
# WP Processing
# =============================================================================


async def process_wp_implementation(
    wp_id: str,
    state: OrchestrationRun,
    config: OrchestratorConfig,
    feature_dir: Path,
    repo_root: Path,
    agent_id: str,
    console: Console,
) -> bool:
    """Process implementation phase for a single WP.

    Args:
        wp_id: Work package ID.
        state: Orchestration state.
        config: Orchestrator config.
        feature_dir: Feature directory path.
        repo_root: Repository root.
        agent_id: Agent to use.
        console: Rich console.

    Returns:
        True if implementation succeeded.
    """
    wp = state.work_packages[wp_id]
    feature_slug = feature_dir.name

    # Transition lane FIRST (atomic)
    await transition_wp_lane(wp, "start_implementation", repo_root)

    # THEN update state
    wp.status = WPStatus.IMPLEMENTATION
    wp.implementation_agent = agent_id
    wp.implementation_started = datetime.now(timezone.utc)
    state.total_agent_invocations += 1
    save_state(state, repo_root)

    logger.info(f"Starting implementation of {wp_id} with {agent_id}")

    # Get or create worktree
    worktree_path = get_worktree_path(feature_slug, wp_id, repo_root)
    if not worktree_path.exists():
        try:
            # Determine base WP from dependencies
            from specify_cli.core.dependency_graph import build_dependency_graph

            graph = build_dependency_graph(feature_dir)
            deps = graph.get(wp_id, [])

            # Use most recently completed dependency as base
            base_wp = None
            for dep_id in deps:
                dep_state = state.work_packages.get(dep_id)
                if dep_state and dep_state.status == WPStatus.COMPLETED:
                    base_wp = dep_id

            worktree_path = await create_worktree(
                feature_slug, wp_id, base_wp, repo_root
            )
            wp.worktree_path = worktree_path
        except WorktreeCreationError as e:
            logger.error(f"Failed to create worktree for {wp_id}: {e}")
            wp.status = WPStatus.FAILED
            wp.last_error = str(e)
            state.wps_failed += 1
            save_state(state, repo_root)
            return False

    # Get invoker and prompt
    invoker = get_invoker(agent_id)
    prompt_path = feature_dir / "tasks" / f"{wp_id}-*.md"

    # Find actual prompt file
    prompt_files = list((feature_dir / "tasks").glob(f"{wp_id}-*.md"))
    if not prompt_files:
        logger.error(f"No prompt file found for {wp_id}")
        wp.status = WPStatus.FAILED
        wp.last_error = f"No prompt file found for {wp_id}"
        state.wps_failed += 1
        save_state(state, repo_root)
        return False

    prompt_path = prompt_files[0]
    prompt_content = prompt_path.read_text()

    # If this is a re-implementation after review rejection, include the feedback
    if wp.review_feedback and wp.implementation_retries > 0:
        rework_header = f"""
## ⚠️ RE-IMPLEMENTATION REQUIRED (Attempt {wp.implementation_retries + 1})

The previous implementation was reviewed and **rejected**. Please address the following feedback:

---
{wp.review_feedback}
---

Fix the issues described above and ensure all requirements are met.
"""
        prompt_content = rework_header + "\n\n" + prompt_content
        logger.info(f"{wp_id} re-implementation with feedback from review")

    # Get log path
    log_path = get_log_path(repo_root, wp_id, "implementation", datetime.now())
    wp.log_file = log_path

    # Execute with retry
    async def execute_fn():
        return await execute_with_logging(
            invoker,
            prompt_content,
            worktree_path,
            "implementation",
            config.global_timeout,
            log_path,
        )

    result = await execute_with_retry(execute_fn, wp, config, "implementation", agent_id)

    # Update progress
    update_wp_progress(wp, result, "implementation")
    wp.implementation_completed = datetime.now(timezone.utc)

    if is_success(result):
        logger.info(f"{wp_id} implementation completed successfully")
        # Move to for_review lane for dashboard visibility
        await transition_wp_lane(wp, "complete_implementation", repo_root)
        save_state(state, repo_root)
        return True

    # Handle failure - try fallback
    logger.warning(f"{wp_id} implementation failed with {agent_id}")
    next_agent = apply_fallback(wp_id, "implementation", agent_id, config, state)

    if next_agent:
        # Reset and retry with fallback agent
        wp.status = WPStatus.PENDING
        wp.implementation_started = None
        wp.implementation_completed = None
        save_state(state, repo_root)

        return await process_wp_implementation(
            wp_id, state, config, feature_dir, repo_root, next_agent, console
        )

    # No fallback - escalate to human
    await escalate_to_human(wp_id, "implementation", state, repo_root, console)
    return False


class ReviewResult:
    """Result of a review phase."""

    APPROVED = "approved"
    REJECTED = "rejected"
    ERROR = "error"

    def __init__(self, outcome: str, feedback: str | None = None):
        self.outcome = outcome
        self.feedback = feedback

    @property
    def is_approved(self) -> bool:
        return self.outcome == self.APPROVED

    @property
    def is_rejected(self) -> bool:
        return self.outcome == self.REJECTED


def parse_review_outcome(result: InvocationResult, log_path: Path | None = None) -> ReviewResult:
    """Parse review result to determine if approved or rejected.

    Looks for rejection signals in the output:
    - Explicit "REJECTED" or "CHANGES_REQUESTED" markers
    - "needs work", "please fix", "issues found" phrases
    - Non-zero exit code with feedback

    Args:
        result: InvocationResult from agent execution.
        log_path: Optional path to log file for detailed output.

    Returns:
        ReviewResult with outcome and feedback.
    """
    exit_code = result.exit_code
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    output = stdout + "\n" + stderr

    # Check for explicit markers (case-insensitive)
    output_lower = output.lower()

    # Rejection patterns
    rejection_patterns = [
        "rejected",
        "changes_requested",
        "changes requested",
        "needs rework",
        "needs work",
        "please fix",
        "issues found",
        "not approved",
        "review failed",
        "failing tests",
        "tests failing",
    ]

    # Approval patterns
    approval_patterns = [
        "approved",
        "lgtm",
        "looks good",
        "review complete",
        "review passed",
        "all tests pass",
        "no issues found",
    ]

    # Check patterns
    is_rejected = any(p in output_lower for p in rejection_patterns)
    is_approved = any(p in output_lower for p in approval_patterns)

    # If both or neither, use exit code
    if is_rejected and not is_approved:
        # Extract feedback - look for content after rejection marker
        feedback = output.strip()
        if len(feedback) > 500:
            feedback = feedback[:500] + "..."
        return ReviewResult(ReviewResult.REJECTED, feedback)

    if is_approved and not is_rejected:
        return ReviewResult(ReviewResult.APPROVED)

    # Fall back to exit code
    if exit_code == 0:
        return ReviewResult(ReviewResult.APPROVED)

    # Non-zero exit with no clear pattern - treat as error, not rejection
    return ReviewResult(ReviewResult.ERROR, output.strip()[:500] if output else None)


async def process_wp_review(
    wp_id: str,
    state: OrchestrationRun,
    config: OrchestratorConfig,
    feature_dir: Path,
    repo_root: Path,
    agent_id: str,
    console: Console,
) -> ReviewResult:
    """Process review phase for a single WP.

    Args:
        wp_id: Work package ID.
        state: Orchestration state.
        config: Orchestrator config.
        feature_dir: Feature directory path.
        repo_root: Repository root.
        agent_id: Agent to use.
        console: Rich console.

    Returns:
        ReviewResult indicating approved, rejected, or error.
    """
    wp = state.work_packages[wp_id]
    feature_slug = feature_dir.name

    # Transition lane FIRST (atomic)
    await transition_wp_lane(wp, "complete_implementation", repo_root)

    # THEN update state
    wp.status = WPStatus.REVIEW
    wp.review_agent = agent_id
    wp.review_started = datetime.now(timezone.utc)
    state.total_agent_invocations += 1
    save_state(state, repo_root)

    logger.info(f"Starting review of {wp_id} with {agent_id}")

    # Get worktree
    worktree_path = get_worktree_path(feature_slug, wp_id, repo_root)
    if not worktree_path.exists():
        logger.error(f"Worktree not found for {wp_id} review")
        wp.last_error = "Worktree not found for review"
        return ReviewResult(ReviewResult.ERROR, "Worktree not found")

    # Get invoker
    invoker = get_invoker(agent_id)

    # Build review prompt - ask for explicit approval/rejection signal
    review_prompt = f"""Review the implementation in this workspace for work package {wp_id}.

Check for:
- Code correctness and completeness
- Test coverage
- Documentation
- Following project conventions

IMPORTANT: At the end of your review, you MUST output one of these markers:
- If implementation is good: "APPROVED - review complete"
- If changes are needed: "REJECTED - <reason>" and describe what needs to be fixed

If you find issues, describe them clearly so they can be addressed in re-implementation.
Do NOT fix issues yourself during review - just identify them.
"""

    # Get log path
    log_path = get_log_path(repo_root, wp_id, "review", datetime.now())

    # Execute with retry
    async def execute_fn():
        return await execute_with_logging(
            invoker,
            review_prompt,
            worktree_path,
            "review",
            config.global_timeout,
            log_path,
        )

    result = await execute_with_retry(execute_fn, wp, config, "review", agent_id)

    # Update progress
    update_wp_progress(wp, result, "review")
    wp.review_completed = datetime.now(timezone.utc)

    # Parse the outcome
    review_result = parse_review_outcome(result, log_path)
    logger.info(f"{wp_id} review outcome: {review_result.outcome}")

    save_state(state, repo_root)
    return review_result


async def process_wp(
    wp_id: str,
    state: OrchestrationRun,
    config: OrchestratorConfig,
    feature_dir: Path,
    repo_root: Path,
    concurrency: ConcurrencyManager,
    console: Console,
    override_impl_agent: str | None = None,
    override_review_agent: str | None = None,
) -> bool:
    """Process a single WP through the implement→review state machine.

    This is the core state machine loop that continues until:
    - WP is COMPLETED (review approved)
    - WP is FAILED (max retries exceeded or unrecoverable error)

    State machine:
        READY/PENDING/REWORK → IMPLEMENTATION → REVIEW
                                                  ↓
                            COMPLETED ← (approved)
                                  or
                            REWORK ← (rejected) → back to IMPLEMENTATION
                                  or
                            FAILED ← (max retries exceeded)

    Args:
        wp_id: Work package ID.
        state: Orchestration state.
        config: Orchestrator config.
        feature_dir: Feature directory path.
        repo_root: Repository root.
        concurrency: Concurrency manager.
        console: Rich console.
        override_impl_agent: CLI override for implementation agent.
        override_review_agent: CLI override for review agent.

    Returns:
        True if WP completed successfully.
    """
    wp = state.work_packages[wp_id]
    max_review_cycles = config.max_retries

    # State machine loop
    while wp.status not in [WPStatus.COMPLETED, WPStatus.FAILED]:
        logger.info(f"{wp_id} state machine: current status = {wp.status.value}")

        # ===== IMPLEMENTATION PHASE =====
        if wp.status in [WPStatus.READY, WPStatus.PENDING, WPStatus.REWORK]:
            # Check max retries before starting
            if wp.implementation_retries >= max_review_cycles:
                logger.error(f"{wp_id} exceeded max review cycles ({max_review_cycles})")
                wp.status = WPStatus.FAILED
                wp.last_error = f"Exceeded max review cycles ({max_review_cycles})"
                state.wps_failed += 1
                save_state(state, repo_root)
                return False

            # Select implementation agent using user config from spec-kitty init
            impl_agent = select_agent_from_user_config(
                repo_root, "implementation", override_agent=override_impl_agent
            )
            if not impl_agent:
                # Fall back to legacy config-based selection
                impl_agent = select_agent(config, "implementation", state=state)
            if not impl_agent:
                logger.error(f"No agent available for {wp_id} implementation")
                wp.status = WPStatus.FAILED
                wp.last_error = "No agent available"
                state.wps_failed += 1
                save_state(state, repo_root)
                return False

            # Run implementation
            async with concurrency.throttle(impl_agent):
                impl_success = await process_wp_implementation(
                    wp_id, state, config, feature_dir, repo_root, impl_agent, console
                )

            if not impl_success:
                # Implementation failed (not rejection - actual error)
                wp.status = WPStatus.FAILED
                state.wps_failed += 1
                save_state(state, repo_root)
                return False

            # Implementation succeeded - move to review
            # (status is already updated by process_wp_implementation)
            continue

        # ===== REVIEW PHASE =====
        if wp.status == WPStatus.IMPLEMENTATION:
            # Implementation just completed, start review

            # Check if review is needed (skip in single-agent mode with no review config)
            skip_review = is_single_agent_mode(config) and not config.defaults.get("review")

            if skip_review:
                # Transition lane FIRST (atomic)
                await transition_wp_lane(wp, "complete_review", repo_root)

                # THEN mark as completed without review
                wp.status = WPStatus.COMPLETED
                state.wps_completed += 1
                save_state(state, repo_root)
                return True

            # Single-agent delay before review
            if is_single_agent_mode(config):
                await single_agent_review_delay(config.single_agent_delay)

            # Select review agent using user config (prefers different agent for cross-review)
            review_agent = select_review_agent_from_user_config(
                repo_root, wp.implementation_agent, override_agent=override_review_agent
            )
            if not review_agent:
                # Fall back to legacy config-based selection
                review_agent = select_review_agent(config, wp.implementation_agent, state=state)
            if not review_agent:
                logger.warning(f"No review agent available for {wp_id}, marking as complete")
                wp.status = WPStatus.COMPLETED
                state.wps_completed += 1
                save_state(state, repo_root)
                return True

            # Run review
            async with concurrency.throttle(review_agent):
                review_result = await process_wp_review(
                    wp_id, state, config, feature_dir, repo_root, review_agent, console
                )

            # Handle review outcome
            if review_result.is_approved:
                # Transition lane FIRST (atomic)
                await transition_wp_lane(wp, "complete_review", repo_root)

                # THEN mark review approved - WP is done!
                wp.status = WPStatus.COMPLETED
                state.wps_completed += 1
                logger.info(f"{wp_id} COMPLETED - review approved")
                save_state(state, repo_root)
                return True

            elif review_result.is_rejected:
                # Review rejected - go back to implementation
                wp.status = WPStatus.REWORK
                wp.review_feedback = review_result.feedback
                wp.implementation_retries += 1
                wp.review_retries += 1

                # Clear review timestamps for next cycle
                wp.review_started = None
                wp.review_completed = None

                logger.info(
                    f"{wp_id} REWORK - review rejected (cycle {wp.implementation_retries}/{max_review_cycles})"
                )
                if review_result.feedback:
                    logger.info(f"{wp_id} feedback: {review_result.feedback[:200]}...")

                save_state(state, repo_root)
                # Loop continues - will go back to implementation
                continue

            else:
                # Review error (not rejection) - try fallback agent or fail
                logger.warning(f"{wp_id} review error: {review_result.feedback}")
                next_agent = apply_fallback(wp_id, "review", review_agent, config, state)

                if next_agent:
                    # Retry review with different agent
                    wp.review_started = None
                    wp.review_completed = None
                    save_state(state, repo_root)

                    async with concurrency.throttle(next_agent):
                        review_result = await process_wp_review(
                            wp_id, state, config, feature_dir, repo_root, next_agent, console
                        )

                    # Re-check outcome after fallback
                    if review_result.is_approved:
                        # Transition lane FIRST (atomic)
                        await transition_wp_lane(wp, "complete_review", repo_root)

                        # THEN mark as completed
                        wp.status = WPStatus.COMPLETED
                        state.wps_completed += 1
                        save_state(state, repo_root)
                        return True
                    elif review_result.is_rejected:
                        wp.status = WPStatus.REWORK
                        wp.review_feedback = review_result.feedback
                        wp.implementation_retries += 1
                        wp.review_retries += 1
                        wp.review_started = None
                        wp.review_completed = None
                        save_state(state, repo_root)
                        continue

                # No fallback or fallback also errored - escalate
                await escalate_to_human(wp_id, "review", state, repo_root, console)
                return False

        # ===== REVIEW STATUS (already in review, resuming) =====
        if wp.status == WPStatus.REVIEW:
            # We're resuming a WP that was in review
            # This shouldn't normally happen as review is synchronous
            # Treat as needing implementation
            wp.status = WPStatus.REWORK
            wp.review_feedback = "Review interrupted - restarting"
            save_state(state, repo_root)
            continue

        # Unknown status - shouldn't happen
        logger.error(f"{wp_id} in unexpected status: {wp.status}")
        wp.status = WPStatus.FAILED
        wp.last_error = f"Unexpected status: {wp.status}"
        state.wps_failed += 1
        save_state(state, repo_root)
        return False

    # Should not reach here, but handle gracefully
    return wp.status == WPStatus.COMPLETED


# =============================================================================
# Main Orchestration Loop (T043)
# =============================================================================


async def run_orchestration_loop(
    state: OrchestrationRun,
    config: OrchestratorConfig,
    feature_dir: Path,
    repo_root: Path,
    console: Console | None = None,
    live_display: bool = True,
    override_impl_agent: str | None = None,
    override_review_agent: str | None = None,
) -> None:
    """Main orchestration loop connecting all components.

    Coordinates scheduler, executor, and monitor to process WPs in parallel.

    Args:
        state: Orchestration state.
        config: Orchestrator config.
        feature_dir: Feature directory path.
        repo_root: Repository root.
        console: Rich console for output.
        live_display: Whether to show live progress display.
        override_impl_agent: CLI override for implementation agent.
        override_review_agent: CLI override for review agent.
    """
    if console is None:
        console = Console()

    # Build graph and validate
    graph = build_wp_graph(feature_dir)

    # Initialize concurrency manager
    concurrency = ConcurrencyManager(config)

    # Initialize WP states
    for wp_id in graph:
        if wp_id not in state.work_packages:
            state.work_packages[wp_id] = WPExecution(wp_id=wp_id)

    state.wps_total = len(graph)
    state.status = OrchestrationStatus.RUNNING
    save_state(state, repo_root)

    # Set up shutdown handler
    shutdown_requested = False
    original_sigint = signal.getsignal(signal.SIGINT)
    original_sigterm = signal.getsignal(signal.SIGTERM)

    def signal_handler(sig, frame):
        nonlocal shutdown_requested
        if shutdown_requested:
            # Second signal - force exit
            console.print("\n[red]Force shutdown...[/red]")
            raise SystemExit(1)

        console.print("\n[yellow]Shutdown requested, finishing current tasks...[/yellow]")
        shutdown_requested = True
        state.status = OrchestrationStatus.PAUSED
        save_state(state, repo_root)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Track running tasks
    running_tasks: dict[str, asyncio.Task] = {}

    try:
        # Run with or without live display
        if live_display:
            with Live(create_live_display(state), refresh_per_second=1, console=console) as live:
                await _orchestration_main_loop(
                    state, config, graph, feature_dir, repo_root,
                    concurrency, console, running_tasks,
                    lambda: shutdown_requested,
                    lambda: live.update(create_live_display(state)),
                    override_impl_agent=override_impl_agent,
                    override_review_agent=override_review_agent,
                )
        else:
            await _orchestration_main_loop(
                state, config, graph, feature_dir, repo_root,
                concurrency, console, running_tasks,
                lambda: shutdown_requested,
                lambda: None,  # No display update
                override_impl_agent=override_impl_agent,
                override_review_agent=override_review_agent,
            )

    finally:
        # Restore signal handlers
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)

        # Cancel any remaining tasks
        for task in running_tasks.values():
            if not task.done():
                task.cancel()

        # Finalize state
        if not shutdown_requested:
            if state.wps_failed > 0:
                state.status = OrchestrationStatus.COMPLETED
            else:
                all_done = all(
                    wp.status in [WPStatus.COMPLETED, WPStatus.FAILED]
                    for wp in state.work_packages.values()
                )
                if all_done:
                    state.status = OrchestrationStatus.COMPLETED
                else:
                    state.status = OrchestrationStatus.FAILED

            state.completed_at = datetime.now(timezone.utc)
            save_state(state, repo_root)

        # Print summary
        print_summary(state, console)


async def _orchestration_main_loop(
    state: OrchestrationRun,
    config: OrchestratorConfig,
    graph: dict[str, list[str]],
    feature_dir: Path,
    repo_root: Path,
    concurrency: ConcurrencyManager,
    console: Console,
    running_tasks: dict[str, asyncio.Task],
    is_shutdown: Callable[[], bool],
    update_display: Callable[[], None],
    override_impl_agent: str | None = None,
    override_review_agent: str | None = None,
) -> None:
    """Inner orchestration loop.

    Args:
        state: Orchestration state.
        config: Orchestrator config.
        graph: Dependency graph.
        feature_dir: Feature directory.
        repo_root: Repository root.
        concurrency: Concurrency manager.
        console: Rich console.
        running_tasks: Dict tracking running asyncio tasks.
        is_shutdown: Callback to check if shutdown requested.
        update_display: Callback to update live display.
        override_impl_agent: CLI override for implementation agent.
        override_review_agent: CLI override for review agent.
    """
    while not is_shutdown():
        # Update display
        update_display()

        # Check completion
        all_done = all(
            wp.status in [WPStatus.COMPLETED, WPStatus.FAILED]
            for wp in state.work_packages.values()
        )

        if all_done:
            logger.info("All work packages complete")
            break

        # Check for paused state (human intervention)
        if state.status == OrchestrationStatus.PAUSED:
            logger.info("Orchestration paused")
            break

        # Get ready WPs
        ready = get_ready_wps(graph, state)

        # Start tasks for ready WPs (up to available slots)
        for wp_id in ready:
            if wp_id in running_tasks:
                continue  # Already running

            if concurrency.get_available_slots() <= 0:
                break  # At global limit

            # Create task
            task = asyncio.create_task(
                process_wp(
                    wp_id, state, config, feature_dir, repo_root,
                    concurrency, console,
                    override_impl_agent=override_impl_agent,
                    override_review_agent=override_review_agent,
                )
            )
            running_tasks[wp_id] = task
            logger.info(f"Started task for {wp_id}")

            # Update peak parallelism
            active_count = sum(1 for t in running_tasks.values() if not t.done())
            if active_count > state.parallel_peak:
                state.parallel_peak = active_count

        # Clean up completed tasks
        completed_wp_ids = [
            wp_id for wp_id, task in running_tasks.items()
            if task.done()
        ]
        for wp_id in completed_wp_ids:
            task = running_tasks.pop(wp_id)
            try:
                task.result()  # Raises if task failed
            except Exception as e:
                logger.error(f"Task for {wp_id} raised exception: {e}")

        # Check if nothing can progress
        if not ready and not running_tasks:
            # Deadlock or all blocked on failed WPs
            remaining = [
                wp_id for wp_id, wp in state.work_packages.items()
                if wp.status not in [WPStatus.COMPLETED, WPStatus.FAILED]
            ]
            if remaining:
                logger.warning(f"No progress possible. Remaining: {remaining}")
                for wp_id in remaining:
                    state.work_packages[wp_id].status = WPStatus.FAILED
                    state.work_packages[wp_id].last_error = "Blocked by failed dependencies"
                    state.wps_failed += 1
                save_state(state, repo_root)
            break

        # Wait a bit before next iteration
        await asyncio.sleep(2)


__all__ = [
    # Exceptions
    "OrchestrationError",
    "CircularDependencyError",
    "NoAgentsError",
    "ValidationError",
    # Validation (T046)
    "validate_feature",
    "validate_agents",
    # Progress display (T044)
    "create_status_table",
    "create_progress_panel",
    "create_live_display",
    # Summary report (T045)
    "print_summary",
    # WP processing
    "process_wp",
    "process_wp_implementation",
    "process_wp_review",
    # Main loop (T043)
    "run_orchestration_loop",
]
