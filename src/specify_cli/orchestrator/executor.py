"""Executor for spawning and managing agent processes.

This module handles:
    - Async process spawning with asyncio.create_subprocess_exec
    - Stdin piping for prompts
    - stdout/stderr capture to log files
    - Timeout enforcement with proper cleanup
    - Worktree creation integration
"""

from __future__ import annotations

import asyncio
import logging
import time
from asyncio.subprocess import Process
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from specify_cli.orchestrator.agents.base import AgentInvoker, BaseInvoker, InvocationResult

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================


# Exit code returned when execution times out
TIMEOUT_EXIT_CODE = 124  # Same as Unix `timeout` command

# Grace period for process to terminate before force kill
TERMINATION_GRACE_SECONDS = 5.0

# Default logs directory under .kittify
LOGS_DIRNAME = "logs"


# =============================================================================
# Exceptions
# =============================================================================


class ExecutorError(Exception):
    """Base exception for executor errors."""

    pass


class WorktreeCreationError(ExecutorError):
    """Raised when worktree creation fails."""

    pass


class ProcessSpawnError(ExecutorError):
    """Raised when process spawning fails."""

    pass


class TimeoutError(ExecutorError):
    """Raised when execution times out."""

    pass


# =============================================================================
# Async Process Spawning (T027)
# =============================================================================


async def spawn_agent(
    invoker: AgentInvoker | BaseInvoker,
    prompt: str,
    working_dir: Path,
    role: str,
) -> tuple[Process, list[str]]:
    """Spawn agent process.

    Creates an asyncio subprocess for the agent with stdin, stdout, and
    stderr pipes configured for capture.

    Args:
        invoker: Agent invoker that knows how to build commands
        prompt: The task prompt to send to the agent
        working_dir: Directory where agent should execute
        role: Either "implementation" or "review"

    Returns:
        Tuple of (process, command) for tracking

    Raises:
        ProcessSpawnError: If process creation fails
    """
    # Build command using invoker
    cmd = invoker.build_command(prompt, working_dir, role)
    logger.info(f"Spawning {invoker.agent_id}: {' '.join(cmd[:3])}...")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
        )
        logger.debug(f"Process {process.pid} spawned for {invoker.agent_id}")
        return process, cmd

    except OSError as e:
        raise ProcessSpawnError(
            f"Failed to spawn {invoker.agent_id}: {e}"
        ) from e
    except Exception as e:
        raise ProcessSpawnError(
            f"Unexpected error spawning {invoker.agent_id}: {e}"
        ) from e


# =============================================================================
# Timeout Handling (T030)
# =============================================================================


async def execute_with_timeout(
    process: Process,
    stdin_data: bytes | None,
    timeout_seconds: int,
) -> tuple[bytes, bytes, int]:
    """Wait for process with timeout, kill if exceeded.

    Implements graceful shutdown: SIGTERM first, then SIGKILL if needed.

    Args:
        process: Asyncio subprocess to wait on
        stdin_data: Data to send to stdin (or None)
        timeout_seconds: Maximum execution time

    Returns:
        Tuple of (stdout, stderr, exit_code)
        Exit code is TIMEOUT_EXIT_CODE if timed out
    """
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(input=stdin_data),
            timeout=timeout_seconds,
        )
        return stdout, stderr, process.returncode or 0

    except asyncio.TimeoutError:
        logger.warning(
            f"Process {process.pid} timed out after {timeout_seconds}s"
        )

        # Graceful termination first
        try:
            process.terminate()
            logger.debug(f"Sent SIGTERM to process {process.pid}")

            # Wait for graceful shutdown
            try:
                await asyncio.wait_for(
                    process.wait(),
                    timeout=TERMINATION_GRACE_SECONDS,
                )
                logger.debug(f"Process {process.pid} terminated gracefully")
            except asyncio.TimeoutError:
                # Force kill if terminate didn't work
                logger.warning(
                    f"Process {process.pid} didn't respond to SIGTERM, "
                    "sending SIGKILL"
                )
                process.kill()
                await process.wait()
                logger.debug(f"Process {process.pid} killed")

        except ProcessLookupError:
            # Process already dead
            logger.debug(f"Process {process.pid} already terminated")

        return (
            b"",
            f"Execution timed out after {timeout_seconds} seconds".encode(),
            TIMEOUT_EXIT_CODE,
        )


# =============================================================================
# Stdin Piping (T028)
# =============================================================================


async def execute_agent(
    invoker: AgentInvoker | BaseInvoker,
    prompt_content: str,
    working_dir: Path,
    role: str,
    timeout_seconds: int,
) -> InvocationResult:
    """Execute agent with prompt.

    Spawns the agent process, pipes prompt via stdin if needed,
    waits for completion with timeout, and parses output.

    Args:
        invoker: Agent invoker that knows how to build commands
        prompt_content: The task prompt content
        working_dir: Directory where agent should execute
        role: Either "implementation" or "review"
        timeout_seconds: Maximum execution time

    Returns:
        InvocationResult with parsed output
    """
    # Spawn process
    process, cmd = await spawn_agent(invoker, prompt_content, working_dir, role)

    # Prepare stdin data if agent uses stdin
    if invoker.uses_stdin:
        stdin_data = prompt_content.encode("utf-8")
        logger.debug(f"Piping {len(stdin_data)} bytes to stdin")
    else:
        stdin_data = None
        logger.debug("Agent uses command-line args, no stdin")

    # Execute with timeout
    start_time = time.time()
    stdout, stderr, exit_code = await execute_with_timeout(
        process,
        stdin_data,
        timeout_seconds,
    )
    duration = time.time() - start_time

    # Parse output
    result = invoker.parse_output(
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
        exit_code,
        duration,
    )

    logger.info(
        f"{invoker.agent_id} completed: exit={exit_code}, "
        f"duration={duration:.1f}s, success={result.success}"
    )

    return result


# =============================================================================
# Log File Capture (T029)
# =============================================================================


def get_log_dir(repo_root: Path) -> Path:
    """Get logs directory under .kittify.

    Args:
        repo_root: Repository root path

    Returns:
        Path to logs directory (created if needed)
    """
    logs_dir = repo_root / ".kittify" / LOGS_DIRNAME
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_log_path(
    repo_root: Path,
    wp_id: str,
    role: str,
    timestamp: datetime | None = None,
) -> Path:
    """Get path for agent log file.

    Args:
        repo_root: Repository root path
        wp_id: Work package ID (e.g., "WP01")
        role: Either "implementation" or "review"
        timestamp: Optional timestamp for uniqueness

    Returns:
        Path to log file
    """
    logs_dir = get_log_dir(repo_root)

    # Include timestamp for uniqueness (useful for retries)
    if timestamp:
        ts = timestamp.strftime("%Y%m%d-%H%M%S")
        filename = f"{wp_id}-{role}-{ts}.log"
    else:
        filename = f"{wp_id}-{role}.log"

    return logs_dir / filename


def write_log_file(
    log_path: Path,
    agent_id: str,
    role: str,
    result: InvocationResult,
    command: list[str] | None = None,
) -> None:
    """Write agent execution log to file.

    Args:
        log_path: Path to write log file
        agent_id: Agent identifier
        role: Either "implementation" or "review"
        result: Execution result
        command: Optional command that was executed
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "w") as f:
        # Header
        f.write("=" * 70 + "\n")
        f.write(f"Agent: {agent_id}\n")
        f.write(f"Role: {role}\n")
        f.write(f"Exit code: {result.exit_code}\n")
        f.write(f"Success: {result.success}\n")
        f.write(f"Duration: {result.duration_seconds:.2f}s\n")
        if command:
            f.write(f"Command: {' '.join(command[:5])}...\n")
        f.write("=" * 70 + "\n\n")

        # Extracted data
        if result.files_modified:
            f.write("--- FILES MODIFIED ---\n")
            for file in result.files_modified:
                f.write(f"  {file}\n")
            f.write("\n")

        if result.commits_made:
            f.write("--- COMMITS ---\n")
            for commit in result.commits_made:
                f.write(f"  {commit}\n")
            f.write("\n")

        if result.errors:
            f.write("--- ERRORS ---\n")
            for error in result.errors:
                f.write(f"  {error}\n")
            f.write("\n")

        if result.warnings:
            f.write("--- WARNINGS ---\n")
            for warning in result.warnings:
                f.write(f"  {warning}\n")
            f.write("\n")

        # Raw output
        f.write("--- STDOUT ---\n")
        f.write(result.stdout)
        f.write("\n\n--- STDERR ---\n")
        f.write(result.stderr)

    logger.debug(f"Wrote log file: {log_path}")


async def execute_with_logging(
    invoker: AgentInvoker | BaseInvoker,
    prompt_content: str,
    working_dir: Path,
    role: str,
    timeout_seconds: int,
    log_path: Path,
) -> InvocationResult:
    """Execute agent and save output to log file.

    Combines execution with log file writing.

    Args:
        invoker: Agent invoker
        prompt_content: The task prompt content
        working_dir: Directory where agent should execute
        role: Either "implementation" or "review"
        timeout_seconds: Maximum execution time
        log_path: Path to write log file

    Returns:
        InvocationResult with parsed output
    """
    result = await execute_agent(
        invoker,
        prompt_content,
        working_dir,
        role,
        timeout_seconds,
    )

    # Write log file
    write_log_file(log_path, invoker.agent_id, role, result)

    return result


# =============================================================================
# Worktree Creation (T031)
# =============================================================================


async def create_worktree(
    feature_slug: str,
    wp_id: str,
    base_wp: str | None,
    repo_root: Path,
) -> Path:
    """Create worktree for WP using spec-kitty CLI.

    Args:
        feature_slug: Feature identifier (e.g., "020-feature-name")
        wp_id: Work package ID (e.g., "WP01")
        base_wp: Optional base WP for --base flag
        repo_root: Repository root path

    Returns:
        Path to created worktree

    Raises:
        WorktreeCreationError: If creation fails
    """
    # Build command
    cmd = ["spec-kitty", "implement", wp_id]
    if base_wp:
        cmd.extend(["--base", base_wp])

    logger.info(f"Creating worktree for {wp_id}: {' '.join(cmd)}")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=repo_root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            stderr_text = stderr.decode("utf-8", errors="replace")
            raise WorktreeCreationError(
                f"Failed to create worktree for {wp_id}: {stderr_text}"
            )

    except FileNotFoundError:
        raise WorktreeCreationError(
            "spec-kitty command not found. Is spec-kitty-cli installed?"
        )
    except Exception as e:
        raise WorktreeCreationError(
            f"Unexpected error creating worktree: {e}"
        ) from e

    # Return worktree path
    worktree_path = repo_root / ".worktrees" / f"{feature_slug}-{wp_id}"

    if not worktree_path.exists():
        raise WorktreeCreationError(
            f"Worktree path {worktree_path} does not exist after creation"
        )

    logger.info(f"Created worktree: {worktree_path}")
    return worktree_path


def get_worktree_path(
    feature_slug: str,
    wp_id: str,
    repo_root: Path,
) -> Path:
    """Get expected worktree path for a WP.

    Args:
        feature_slug: Feature identifier
        wp_id: Work package ID
        repo_root: Repository root path

    Returns:
        Expected path to worktree
    """
    return repo_root / ".worktrees" / f"{feature_slug}-{wp_id}"


def worktree_exists(
    feature_slug: str,
    wp_id: str,
    repo_root: Path,
) -> bool:
    """Check if worktree already exists.

    Args:
        feature_slug: Feature identifier
        wp_id: Work package ID
        repo_root: Repository root path

    Returns:
        True if worktree directory exists
    """
    return get_worktree_path(feature_slug, wp_id, repo_root).exists()


# =============================================================================
# Full Execution Pipeline
# =============================================================================


@dataclass
class ExecutionContext:
    """Context for a single WP execution.

    Groups together all parameters needed for execution.
    """

    wp_id: str
    feature_slug: str
    invoker: AgentInvoker | BaseInvoker
    prompt_path: Path
    role: str
    timeout_seconds: int
    repo_root: Path
    working_dir: Path | None = None  # Set after worktree creation


async def execute_wp(
    ctx: ExecutionContext,
    create_worktree_if_missing: bool = True,
    base_wp: str | None = None,
) -> tuple[InvocationResult, Path]:
    """Execute a complete WP implementation or review.

    This is the main entry point for WP execution. It:
    1. Creates worktree if needed
    2. Reads prompt file
    3. Executes agent with logging
    4. Returns result and log path

    Args:
        ctx: Execution context with all parameters
        create_worktree_if_missing: Whether to create worktree if not exists
        base_wp: Base WP for --base flag when creating worktree

    Returns:
        Tuple of (InvocationResult, log_path)

    Raises:
        WorktreeCreationError: If worktree creation fails
        ProcessSpawnError: If agent spawn fails
        FileNotFoundError: If prompt file doesn't exist
    """
    # Get or create worktree
    if ctx.working_dir:
        working_dir = ctx.working_dir
    else:
        worktree_path = get_worktree_path(
            ctx.feature_slug,
            ctx.wp_id,
            ctx.repo_root,
        )

        if not worktree_path.exists():
            if create_worktree_if_missing:
                worktree_path = await create_worktree(
                    ctx.feature_slug,
                    ctx.wp_id,
                    base_wp,
                    ctx.repo_root,
                )
            else:
                raise WorktreeCreationError(
                    f"Worktree {worktree_path} does not exist"
                )

        working_dir = worktree_path

    # Read prompt content
    if not ctx.prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {ctx.prompt_path}")

    prompt_content = ctx.prompt_path.read_text()

    # Get log path
    log_path = get_log_path(
        ctx.repo_root,
        ctx.wp_id,
        ctx.role,
        timestamp=datetime.now(),
    )

    # Execute with logging
    result = await execute_with_logging(
        ctx.invoker,
        prompt_content,
        working_dir,
        ctx.role,
        ctx.timeout_seconds,
        log_path,
    )

    return result, log_path


__all__ = [
    # Constants
    "TIMEOUT_EXIT_CODE",
    "TERMINATION_GRACE_SECONDS",
    "LOGS_DIRNAME",
    # Exceptions
    "ExecutorError",
    "WorktreeCreationError",
    "ProcessSpawnError",
    "TimeoutError",
    # Process spawning (T027)
    "spawn_agent",
    # Stdin piping (T028)
    "execute_agent",
    # Log capture (T029)
    "get_log_dir",
    "get_log_path",
    "write_log_file",
    "execute_with_logging",
    # Timeout handling (T030)
    "execute_with_timeout",
    # Worktree integration (T031)
    "create_worktree",
    "get_worktree_path",
    "worktree_exists",
    # Full pipeline
    "ExecutionContext",
    "execute_wp",
]
