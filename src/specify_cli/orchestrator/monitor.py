"""Monitor for tracking execution completion and handling failures.

This module handles:
    - Exit code detection and classification (T032)
    - JSON output parsing from agents (T033)
    - Retry logic with configurable limits (T034)
    - Fallback strategy execution (T035)
    - Lane status updates via existing commands (T036)
    - Human escalation when all agents fail (T037)

Implemented in WP07.
"""

from __future__ import annotations

import asyncio
import json
import logging
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from rich.console import Console
from rich.panel import Panel

from specify_cli.orchestrator.agents.base import InvocationResult
from specify_cli.orchestrator.config import (
    AgentConfig,
    FallbackStrategy,
    OrchestrationStatus,
    OrchestratorConfig,
    WPStatus,
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
# Constants
# =============================================================================


# Timeout exit code (same as Unix `timeout` command)
TIMEOUT_EXIT_CODE = 124

# Delay between retries (seconds)
RETRY_DELAY_SECONDS = 5

# Maximum error message length to store
MAX_ERROR_LENGTH = 500


# =============================================================================
# Failure Types (T032)
# =============================================================================


class FailureType(str, Enum):
    """Classification of execution failures."""

    TIMEOUT = "timeout"
    AUTH_ERROR = "auth_error"
    RATE_LIMIT = "rate_limit"
    GENERAL_ERROR = "general_error"
    NETWORK_ERROR = "network_error"


# =============================================================================
# Exit Code Detection (T032)
# =============================================================================


def is_success(result: InvocationResult) -> bool:
    """Determine if invocation was successful.

    Args:
        result: The invocation result to check.

    Returns:
        True if the invocation succeeded (exit code 0 and success flag).
    """
    return result.exit_code == 0 and result.success


def classify_failure(result: InvocationResult, agent_id: str) -> FailureType:
    """Classify the type of failure for appropriate handling.

    Uses exit codes and stderr content to determine failure type,
    which influences retry and fallback behavior.

    Args:
        result: The failed invocation result.
        agent_id: The agent that produced the result.

    Returns:
        FailureType indicating the nature of the failure.
    """
    stderr_lower = result.stderr.lower()

    # Timeout detection (exit code 124 is Unix timeout standard)
    if result.exit_code == TIMEOUT_EXIT_CODE:
        return FailureType.TIMEOUT

    # Gemini-specific error codes
    if agent_id == "gemini":
        if result.exit_code == 41:  # Gemini auth error
            return FailureType.AUTH_ERROR
        if result.exit_code == 42:  # Gemini rate limit
            return FailureType.RATE_LIMIT

    # Claude-specific error patterns
    if agent_id == "claude-code":
        if "api key" in stderr_lower or "unauthorized" in stderr_lower:
            return FailureType.AUTH_ERROR
        if "rate limit" in stderr_lower or "429" in stderr_lower:
            return FailureType.RATE_LIMIT

    # Codex-specific patterns
    if agent_id == "codex":
        if "openai api key" in stderr_lower:
            return FailureType.AUTH_ERROR
        if "rate_limit_exceeded" in stderr_lower:
            return FailureType.RATE_LIMIT

    # Generic pattern matching for stderr content
    if "authentication" in stderr_lower:
        return FailureType.AUTH_ERROR
    if "api key" in stderr_lower or "api_key" in stderr_lower:
        return FailureType.AUTH_ERROR
    if "unauthorized" in stderr_lower or "401" in stderr_lower:
        return FailureType.AUTH_ERROR

    if "rate limit" in stderr_lower or "rate_limit" in stderr_lower:
        return FailureType.RATE_LIMIT
    if "too many requests" in stderr_lower or "429" in stderr_lower:
        return FailureType.RATE_LIMIT

    if "network" in stderr_lower or "connection" in stderr_lower:
        return FailureType.NETWORK_ERROR
    if "timeout" in stderr_lower or "timed out" in stderr_lower:
        return FailureType.NETWORK_ERROR

    return FailureType.GENERAL_ERROR


def should_retry(failure_type: FailureType) -> bool:
    """Determine if a failure type should be retried.

    Some failures like auth errors won't be fixed by retrying.

    Args:
        failure_type: The classified failure type.

    Returns:
        True if retrying the same agent might succeed.
    """
    # Don't retry auth errors - they need user intervention
    if failure_type == FailureType.AUTH_ERROR:
        return False

    # All other failures might be transient
    return True


# =============================================================================
# JSON Output Parsing (T033)
# =============================================================================


def parse_json_output(stdout: str) -> dict | None:
    """Parse JSON output from agent, handling JSONL format.

    Agents may output JSON in different formats:
    - Single JSON object
    - JSONL (one JSON per line, final line is result)
    - Embedded JSON in other output

    Args:
        stdout: Raw stdout from the agent.

    Returns:
        Parsed JSON dict or None if parsing fails.
    """
    if not stdout.strip():
        return None

    # Try parsing entire output as single JSON
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        pass

    # Try parsing last non-empty lines as JSON (JSONL format)
    lines = stdout.strip().split("\n")
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue

        # Only attempt parsing lines that look like JSON
        if line.startswith("{") or line.startswith("["):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue

    return None


def extract_result_data(json_data: dict | None) -> dict[str, Any]:
    """Extract useful fields from parsed JSON.

    Normalizes different agent output formats into a standard structure.

    Args:
        json_data: Parsed JSON from agent output.

    Returns:
        Dict with normalized fields (files_modified, commits_made, etc.)
    """
    if not json_data:
        return {}

    result: dict[str, Any] = {}

    # Extract files modified - different agents use different keys
    for key in ["files", "files_modified", "modified_files", "changedFiles"]:
        if key in json_data and isinstance(json_data[key], list):
            result["files_modified"] = [str(f) for f in json_data[key]]
            break

    # Extract commits - different agents use different keys
    for key in ["commits", "commits_made", "commitShas", "commit_hashes"]:
        if key in json_data and isinstance(json_data[key], list):
            result["commits_made"] = [str(c) for c in json_data[key]]
            break

    # Extract errors
    if "errors" in json_data:
        errors = json_data["errors"]
        if isinstance(errors, list):
            result["errors"] = [str(e) for e in errors]
        elif errors:
            result["errors"] = [str(errors)]
    elif "error" in json_data and json_data["error"]:
        result["errors"] = [str(json_data["error"])]

    # Extract warnings
    if "warnings" in json_data:
        warnings = json_data["warnings"]
        if isinstance(warnings, list):
            result["warnings"] = [str(w) for w in warnings]
        elif warnings:
            result["warnings"] = [str(warnings)]
    elif "warning" in json_data and json_data["warning"]:
        result["warnings"] = [str(json_data["warning"])]

    return result


def analyze_output(result: InvocationResult) -> dict[str, Any]:
    """Analyze agent output and extract structured data.

    Combines exit code analysis with JSON parsing for comprehensive result.

    Args:
        result: The invocation result to analyze.

    Returns:
        Dict with analysis results including any extracted structured data.
    """
    analysis: dict[str, Any] = {
        "success": is_success(result),
        "exit_code": result.exit_code,
        "duration_seconds": result.duration_seconds,
    }

    # Try to parse JSON from stdout
    json_data = parse_json_output(result.stdout)
    if json_data:
        analysis["json_data"] = json_data
        analysis.update(extract_result_data(json_data))

    # Use data already extracted by invoker if no JSON found
    if "files_modified" not in analysis and result.files_modified:
        analysis["files_modified"] = result.files_modified
    if "commits_made" not in analysis and result.commits_made:
        analysis["commits_made"] = result.commits_made
    if "errors" not in analysis and result.errors:
        analysis["errors"] = result.errors
    if "warnings" not in analysis and result.warnings:
        analysis["warnings"] = result.warnings

    return analysis


# =============================================================================
# Retry Logic (T034)
# =============================================================================


async def execute_with_retry(
    executor_fn: Callable[[], Awaitable[InvocationResult]],
    wp_execution: WPExecution,
    config: OrchestratorConfig,
    role: str,
    agent_id: str,
) -> InvocationResult:
    """Execute with retry logic.

    Retries failed invocations up to the configured limit, with a delay
    between attempts. Updates the WP execution state with retry count.

    Args:
        executor_fn: Async function to execute (returns InvocationResult).
        wp_execution: WP execution state to update.
        config: Orchestrator config for retry limits.
        role: "implementation" or "review".
        agent_id: The agent being used (for failure classification).

    Returns:
        Final InvocationResult (success or last failure).
    """
    max_retries = config.max_retries
    attempt = 0

    # Get current retry count for this role
    if role == "implementation":
        retries = wp_execution.implementation_retries
    else:
        retries = wp_execution.review_retries

    while attempt <= max_retries:
        result = await executor_fn()

        if is_success(result):
            logger.info(
                f"WP {wp_execution.wp_id} {role} succeeded on attempt {attempt + 1}"
            )
            return result

        # Classify the failure
        failure_type = classify_failure(result, agent_id)
        logger.warning(
            f"WP {wp_execution.wp_id} {role} failed: {failure_type.value}"
        )

        # Store the error (truncated)
        error_msg = result.stderr[:MAX_ERROR_LENGTH] if result.stderr else ""
        if not error_msg and result.errors:
            error_msg = "; ".join(result.errors)[:MAX_ERROR_LENGTH]
        wp_execution.last_error = error_msg

        # Check if this failure type should be retried
        if not should_retry(failure_type):
            logger.warning(
                f"WP {wp_execution.wp_id} {role} failure type {failure_type.value} "
                "is not retryable"
            )
            break

        attempt += 1
        retries += 1

        # Update retry count in state
        if role == "implementation":
            wp_execution.implementation_retries = retries
        else:
            wp_execution.review_retries = retries

        if attempt <= max_retries:
            logger.info(
                f"WP {wp_execution.wp_id} {role} retrying "
                f"(attempt {attempt + 1}/{max_retries + 1})..."
            )
            await asyncio.sleep(RETRY_DELAY_SECONDS)

    return result


# =============================================================================
# Fallback Strategy Execution (T035)
# =============================================================================


def apply_fallback(
    wp_id: str,
    role: str,
    failed_agent: str,
    config: OrchestratorConfig,
    state: OrchestrationRun,
) -> str | None:
    """Apply fallback strategy and return next agent to try.

    Implements the configured fallback strategy to select the next
    agent after a failure. Updates the WP execution state with
    tried agents.

    Args:
        wp_id: Work package ID.
        role: "implementation" or "review".
        failed_agent: The agent that just failed.
        config: Orchestrator config with fallback strategy.
        state: Orchestration run state.

    Returns:
        Next agent ID to try, or None if no fallback available.
    """
    strategy = config.fallback_strategy
    wp_execution = state.work_packages[wp_id]

    logger.info(
        f"Applying fallback strategy '{strategy.value}' for {wp_id} {role}"
    )

    if strategy == FallbackStrategy.FAIL:
        # No fallback - fail immediately
        logger.info("Fallback strategy is FAIL, no fallback attempt")
        return None

    if strategy == FallbackStrategy.SAME_AGENT:
        # In single-agent mode or same_agent strategy, just fail after retries
        logger.info("Fallback strategy is SAME_AGENT, no fallback to other agents")
        return None

    if strategy == FallbackStrategy.NEXT_IN_LIST:
        # Track the failed agent
        if failed_agent not in wp_execution.fallback_agents_tried:
            wp_execution.fallback_agents_tried.append(failed_agent)

        # Get candidates from defaults list for this role
        candidates = config.defaults.get(role, [])

        for agent_id in candidates:
            # Skip agents we've already tried
            if agent_id in wp_execution.fallback_agents_tried:
                continue

            # Check if agent is enabled
            agent_config = config.agents.get(agent_id)
            if agent_config is None:
                continue
            if not agent_config.enabled:
                continue

            # Check if agent supports this role
            if role not in agent_config.roles:
                continue

            logger.info(f"Fallback: next agent for {wp_id} {role} is {agent_id}")
            return agent_id

        # All candidates exhausted
        logger.warning(
            f"Fallback: all agents exhausted for {wp_id} {role}. "
            f"Tried: {wp_execution.fallback_agents_tried}"
        )
        return None

    # Unknown strategy (shouldn't happen)
    logger.error(f"Unknown fallback strategy: {strategy}")
    return None


def get_available_fallback_agents(
    wp_id: str,
    role: str,
    config: OrchestratorConfig,
    state: OrchestrationRun,
) -> list[str]:
    """Get list of agents that haven't been tried yet for fallback.

    Args:
        wp_id: Work package ID.
        role: "implementation" or "review".
        config: Orchestrator config.
        state: Orchestration run state.

    Returns:
        List of agent IDs that are available for fallback.
    """
    wp_execution = state.work_packages[wp_id]
    tried = set(wp_execution.fallback_agents_tried)
    candidates = config.defaults.get(role, [])

    available = []
    for agent_id in candidates:
        if agent_id in tried:
            continue
        agent_config = config.agents.get(agent_id)
        if agent_config and agent_config.enabled and role in agent_config.roles:
            available.append(agent_id)

    return available


# =============================================================================
# Lane Status Updates (T036)
# =============================================================================


async def update_wp_lane(
    wp_id: str,
    lane: str,
    note: str,
    repo_root: Path,
) -> bool:
    """Update WP lane status using spec-kitty command.

    Calls the existing CLI command to update the lane, ensuring
    proper integration with the rest of the spec-kitty workflow.

    Args:
        wp_id: Work package ID.
        lane: Target lane (doing, for_review, done).
        note: Status note for the history.
        repo_root: Repository root for command execution.

    Returns:
        True if the command succeeded.
    """
    cmd = [
        "spec-kitty",
        "agent",
        "tasks",
        "move-task",
        wp_id,
        "--to",
        lane,
        "--note",
        note,
    ]

    logger.info(f"Updating {wp_id} lane to '{lane}'")
    logger.debug(f"Command: {' '.join(cmd)}")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=repo_root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            logger.info(f"Successfully updated {wp_id} to '{lane}'")
            return True
        else:
            stderr_text = stderr.decode("utf-8", errors="replace")
            logger.error(f"Failed to update {wp_id} lane: {stderr_text}")
            return False

    except FileNotFoundError:
        logger.error("spec-kitty command not found. Is spec-kitty-cli installed?")
        return False
    except Exception as e:
        logger.error(f"Unexpected error updating lane: {e}")
        return False


async def mark_subtask_done(
    subtask_id: str,
    repo_root: Path,
) -> bool:
    """Mark a subtask as done using spec-kitty command.

    Args:
        subtask_id: Subtask ID (e.g., "T001").
        repo_root: Repository root for command execution.

    Returns:
        True if the command succeeded.
    """
    cmd = [
        "spec-kitty",
        "agent",
        "tasks",
        "mark-status",
        subtask_id,
        "--status",
        "done",
    ]

    logger.info(f"Marking subtask {subtask_id} as done")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=repo_root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()
        return process.returncode == 0
    except Exception as e:
        logger.error(f"Failed to mark subtask done: {e}")
        return False


# Lane transition helpers
LANE_TRANSITIONS = {
    # (from_status, event) -> (to_status, to_lane)
    # Starting implementation
    (WPStatus.PENDING, "start_implementation"): (WPStatus.IMPLEMENTATION, "doing"),
    (WPStatus.READY, "start_implementation"): (WPStatus.IMPLEMENTATION, "doing"),
    # Idempotent: already implementing, stay in implementation
    (WPStatus.IMPLEMENTATION, "start_implementation"): (WPStatus.IMPLEMENTATION, "doing"),
    # Completing implementation
    (WPStatus.IMPLEMENTATION, "complete_implementation"): (
        WPStatus.REVIEW,
        "for_review",
    ),
    # Idempotent: already in review, stay in review
    (WPStatus.REVIEW, "complete_implementation"): (WPStatus.REVIEW, "for_review"),
    # Completing review
    (WPStatus.REVIEW, "complete_review"): (WPStatus.COMPLETED, "done"),
    # Rework: going back to implementation
    (WPStatus.REWORK, "start_implementation"): (WPStatus.IMPLEMENTATION, "doing"),
}


async def transition_wp_lane(
    wp_execution: WPExecution,
    event: str,
    repo_root: Path,
) -> bool:
    """Transition WP to the next lane based on event.

    Args:
        wp_execution: The WP execution state.
        event: The event triggering the transition.
        repo_root: Repository root for command execution.

    Returns:
        True if transition succeeded.
    """
    current_status = wp_execution.status
    key = (current_status, event)

    if key not in LANE_TRANSITIONS:
        logger.warning(
            f"No transition defined for {wp_execution.wp_id} "
            f"from {current_status.value} on event '{event}'"
        )
        return False

    new_status, new_lane = LANE_TRANSITIONS[key]
    note = f"Automated: {event.replace('_', ' ')}"

    success = await update_wp_lane(
        wp_execution.wp_id,
        new_lane,
        note,
        repo_root,
    )

    if success:
        wp_execution.status = new_status
        logger.info(
            f"{wp_execution.wp_id}: {current_status.value} -> {new_status.value}"
        )

    return success


# =============================================================================
# Human Escalation (T037)
# =============================================================================


async def escalate_to_human(
    wp_id: str,
    role: str,
    state: OrchestrationRun,
    repo_root: Path,
    console: Console | None = None,
) -> None:
    """Pause orchestration and alert user when all agents fail.

    Sets orchestration status to PAUSED and prints clear instructions
    for the user on how to proceed.

    Args:
        wp_id: The WP that failed.
        role: The role that failed ("implementation" or "review").
        state: Orchestration run state to update.
        repo_root: Repository root for state persistence.
        console: Rich console for output (creates one if not provided).
    """
    if console is None:
        console = Console()

    wp_execution = state.work_packages[wp_id]

    # Update state
    state.status = OrchestrationStatus.PAUSED
    wp_execution.status = WPStatus.FAILED
    state.wps_failed += 1

    # Save state for resume capability
    save_state(state, repo_root)

    # Get log file path if available
    log_file_info = ""
    if wp_execution.log_file:
        log_file_info = f"\nLog file: {wp_execution.log_file}"

    # Get tried agents info
    tried_agents = wp_execution.fallback_agents_tried
    tried_info = f"Agents tried: {', '.join(tried_agents)}" if tried_agents else ""

    # Format the error message
    last_error = wp_execution.last_error or "No error message captured"
    if len(last_error) > 300:
        last_error = last_error[:300] + "..."

    # Print alert panel
    console.print()
    console.print(
        Panel(
            f"[bold red]Orchestration Paused[/bold red]\n\n"
            f"Work package [bold]{wp_id}[/bold] failed during {role}.\n"
            f"All agents exhausted after retries and fallbacks.\n"
            f"{tried_info}\n\n"
            f"[bold]Last error:[/bold]\n{last_error}\n"
            f"{log_file_info}\n\n"
            f"[bold]Options:[/bold]\n"
            f"1. Fix the issue and resume:\n"
            f"   [cyan]spec-kitty orchestrate --resume[/cyan]\n\n"
            f"2. Skip this WP and continue:\n"
            f"   [cyan]spec-kitty orchestrate --skip {wp_id}[/cyan]\n\n"
            f"3. Abort the orchestration:\n"
            f"   [cyan]spec-kitty orchestrate --abort[/cyan]",
            title="Human Intervention Required",
            border_style="red",
        )
    )
    console.print()

    logger.info(f"Orchestration paused: {wp_id} failed during {role}")


def get_escalation_summary(state: OrchestrationRun) -> dict[str, Any]:
    """Get a summary of escalation state for programmatic access.

    Args:
        state: Orchestration run state.

    Returns:
        Dict with escalation details.
    """
    failed_wps = [
        wp_id
        for wp_id, wp in state.work_packages.items()
        if wp.status == WPStatus.FAILED
    ]

    return {
        "is_paused": state.status == OrchestrationStatus.PAUSED,
        "failed_wps": failed_wps,
        "total_wps": state.wps_total,
        "completed_wps": state.wps_completed,
        "failed_count": state.wps_failed,
        "details": {
            wp_id: {
                "last_error": state.work_packages[wp_id].last_error,
                "agents_tried": state.work_packages[wp_id].fallback_agents_tried,
                "log_file": str(state.work_packages[wp_id].log_file)
                if state.work_packages[wp_id].log_file
                else None,
            }
            for wp_id in failed_wps
        },
    }


# =============================================================================
# Combined Monitor Functions
# =============================================================================


async def handle_wp_failure(
    wp_id: str,
    role: str,
    failed_agent: str,
    result: InvocationResult,
    config: OrchestratorConfig,
    state: OrchestrationRun,
    repo_root: Path,
    execute_phase_fn: Callable[
        [str, str, str], Awaitable[InvocationResult]
    ] | None = None,
    console: Console | None = None,
) -> InvocationResult | None:
    """Handle a WP phase failure with fallback and escalation.

    Coordinates the fallback strategy and escalation flow after
    a WP phase fails.

    Args:
        wp_id: Work package ID.
        role: "implementation" or "review".
        failed_agent: The agent that failed.
        result: The failed invocation result.
        config: Orchestrator config.
        state: Orchestration run state.
        repo_root: Repository root.
        execute_phase_fn: Optional function to execute with a new agent.
            Signature: (wp_id, role, agent_id) -> InvocationResult
        console: Rich console for output.

    Returns:
        InvocationResult from successful retry/fallback, or None if
        escalated to human.
    """
    failure_type = classify_failure(result, failed_agent)
    logger.info(f"Handling failure for {wp_id} {role}: {failure_type.value}")

    # Try fallback if available
    next_agent = apply_fallback(wp_id, role, failed_agent, config, state)

    if next_agent and execute_phase_fn:
        logger.info(f"Attempting fallback with {next_agent} for {wp_id} {role}")
        return await execute_phase_fn(wp_id, role, next_agent)

    # No fallback available - escalate to human
    await escalate_to_human(wp_id, role, state, repo_root, console)
    return None


def update_wp_progress(
    wp_execution: WPExecution,
    result: InvocationResult,
    role: str,
) -> None:
    """Update WP execution state based on result.

    Args:
        wp_execution: WP execution state to update.
        result: The invocation result.
        role: "implementation" or "review".
    """
    if role == "implementation":
        wp_execution.implementation_exit_code = result.exit_code
    else:
        wp_execution.review_exit_code = result.exit_code

    # Analyze output and update any extracted data
    analysis = analyze_output(result)

    if not is_success(result):
        error_msg = result.stderr[:MAX_ERROR_LENGTH] if result.stderr else ""
        if not error_msg and analysis.get("errors"):
            error_msg = "; ".join(analysis["errors"])[:MAX_ERROR_LENGTH]
        wp_execution.last_error = error_msg


__all__ = [
    # Constants
    "TIMEOUT_EXIT_CODE",
    "RETRY_DELAY_SECONDS",
    "MAX_ERROR_LENGTH",
    # Enums
    "FailureType",
    # Exit code detection (T032)
    "is_success",
    "classify_failure",
    "should_retry",
    # JSON parsing (T033)
    "parse_json_output",
    "extract_result_data",
    "analyze_output",
    # Retry logic (T034)
    "execute_with_retry",
    # Fallback strategy (T035)
    "apply_fallback",
    "get_available_fallback_agents",
    # Lane updates (T036)
    "update_wp_lane",
    "mark_subtask_done",
    "transition_wp_lane",
    "LANE_TRANSITIONS",
    # Human escalation (T037)
    "escalate_to_human",
    "get_escalation_summary",
    # Combined functions
    "handle_wp_failure",
    "update_wp_progress",
]
