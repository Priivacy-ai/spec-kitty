"""Context validation for location-aware commands.

This module provides runtime validation to ensure commands are executed
in the correct location (main repository vs worktree). Prevents common
mistakes like running 'implement' from inside a worktree.

Example:
    from specify_cli.core.context_validation import (
        require_main_repo,
        require_worktree,
        get_current_context,
    )

    @require_main_repo
    def implement(wp_id: str):
        # This function can only run from main repo
        pass

    @require_worktree
    def some_workspace_command():
        # This function can only run from inside a worktree
        pass
"""

from __future__ import annotations

import functools
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, TypeVar, cast

import typer
from rich.console import Console

console = Console()


class ExecutionContext(str, Enum):
    """Execution context for a command."""

    MAIN_REPO = "main"  # Command runs in main repository
    WORKTREE = "worktree"  # Command runs inside a worktree
    EITHER = "either"  # Command can run in either location


@dataclass
class CurrentContext:
    """Current execution context information."""

    location: ExecutionContext
    cwd: Path
    repo_root: Path | None
    worktree_name: str | None  # e.g., "010-feature-WP02" if in worktree
    worktree_path: Path | None  # Absolute path to worktree directory


def detect_execution_context(cwd: Path | None = None) -> CurrentContext:
    """Detect current execution context.

    Args:
        cwd: Current working directory (defaults to Path.cwd())

    Returns:
        CurrentContext with location, paths, and worktree info

    Example:
        >>> ctx = detect_execution_context()
        >>> if ctx.location == ExecutionContext.WORKTREE:
        ...     print(f"In worktree: {ctx.worktree_name}")
    """
    if cwd is None:
        cwd = Path.cwd().resolve()
    else:
        cwd = cwd.resolve()

    repo_root: Path | None = None

    # Check if .worktrees is in path
    if ".worktrees" in cwd.parts:
        # Extract worktree information
        for i, part in enumerate(cwd.parts):
            if part == ".worktrees" and i + 1 < len(cwd.parts):
                candidate_root = Path(*cwd.parts[:i])
                if (candidate_root / ".kittify").exists() or (candidate_root / ".git").exists():
                    worktree_name = cwd.parts[i + 1]
                    worktree_path = Path(*cwd.parts[: i + 2])
                    repo_root = candidate_root

                    return CurrentContext(
                        location=ExecutionContext.WORKTREE,
                        cwd=cwd,
                        repo_root=repo_root,
                        worktree_name=worktree_name,
                        worktree_path=worktree_path,
                    )

    # Not in worktree - assume main repo
    # Try to find repo root (directory containing .kittify or .git)
    search_path = cwd
    for _ in range(10):  # Limit depth
        if (search_path / ".kittify").exists() or (search_path / ".git").exists():
            repo_root = search_path
            break
        if search_path.parent == search_path:
            break  # Reached filesystem root
        search_path = search_path.parent

    return CurrentContext(
        location=ExecutionContext.MAIN_REPO,
        cwd=cwd,
        repo_root=repo_root,
        worktree_name=None,
        worktree_path=None,
    )


def get_current_context() -> CurrentContext:
    """Get current execution context.

    Convenience function that detects context from current working directory.

    Returns:
        CurrentContext with location and path information
    """
    return detect_execution_context()


def format_location_error(
    required: ExecutionContext,
    actual: ExecutionContext,
    command_name: str,
    current_ctx: CurrentContext,
) -> str:
    """Format a clear error message for location mismatch.

    Args:
        required: Required execution context
        actual: Actual execution context
        command_name: Name of command being run
        current_ctx: Current context information

    Returns:
        Formatted error message with actionable instructions
    """
    if required == ExecutionContext.MAIN_REPO and actual == ExecutionContext.WORKTREE:
        # Command needs main repo, but in worktree
        if current_ctx.repo_root:
            return (
                f"[bold red]Error:[/bold red] '{command_name}' must run from the main repository\n\n"
                f"[yellow]Current location:[/yellow] Inside worktree [cyan]{current_ctx.worktree_name}[/cyan]\n"
                f"[yellow]Required location:[/yellow] Main repository\n\n"
                f"[bold]Change to main repository:[/bold]\n"
                f"  cd {current_ctx.repo_root}\n\n"
                f"[dim]This command creates/manages worktrees and must run from the main repository.\n"
                f"Running from inside a worktree would create nested worktrees, corrupting git state.[/dim]"
            )
        else:
            return (
                f"[bold red]Error:[/bold red] '{command_name}' must run from the main repository\n\n"
                f"[yellow]Current location:[/yellow] Inside worktree [cyan]{current_ctx.worktree_name}[/cyan]\n"
                f"[yellow]Required location:[/yellow] Main repository\n\n"
                f"[bold]Change to main repository:[/bold]\n"
                f"  cd ../..  # Navigate up from worktree\n\n"
                f"[dim]This command must run from the main repository.[/dim]"
            )

    elif required == ExecutionContext.WORKTREE and actual == ExecutionContext.MAIN_REPO:
        # Command needs worktree, but in main repo
        return (
            f"[bold red]Error:[/bold red] '{command_name}' must run from inside a worktree\n\n"
            f"[yellow]Current location:[/yellow] Main repository\n"
            f"[yellow]Required location:[/yellow] Inside a worktree\n\n"
            f"[bold]Change to a worktree:[/bold]\n"
            f"  cd .worktrees/###-feature-WP##/\n\n"
            f"[dim]This command operates on workspace files and must run from inside a worktree.[/dim]"
        )

    else:
        # Generic error
        return (
            f"[bold red]Error:[/bold red] '{command_name}' cannot run in current location\n\n"
            f"[yellow]Current location:[/yellow] {actual.value}\n"
            f"[yellow]Required location:[/yellow] {required.value}\n"
        )


# Type variable for function decoration
F = TypeVar("F", bound=Callable[..., Any])


def require_main_repo(func: F) -> F:
    """Decorator to require command runs from main repository.

    Prevents commands from running inside worktrees, which could cause
    nested worktrees or other git corruption.

    Example:
        @require_main_repo
        def implement(wp_id: str):
            # Can only run from main repo
            create_worktree(...)

    Args:
        func: Function to decorate

    Returns:
        Decorated function that validates location before executing
    """

    @functools.wraps(func)
    def wrapper(*args: object, **kwargs: object) -> Any:
        ctx = get_current_context()

        if ctx.location == ExecutionContext.WORKTREE:
            error_msg = format_location_error(
                required=ExecutionContext.MAIN_REPO,
                actual=ctx.location,
                command_name=func.__name__,
                current_ctx=ctx,
            )
            console.print(error_msg)
            raise typer.Exit(1)

        return func(*args, **kwargs)

    return cast(F, wrapper)


def require_worktree(func: F) -> F:
    """Decorator to require command runs from inside a worktree.

    Prevents commands from running in main repo when they need workspace context.

    Example:
        @require_worktree
        def workspace_status():
            # Can only run from inside worktree
            show_workspace_info(...)

    Args:
        func: Function to decorate

    Returns:
        Decorated function that validates location before executing
    """

    @functools.wraps(func)
    def wrapper(*args: object, **kwargs: object) -> Any:
        ctx = get_current_context()

        if ctx.location == ExecutionContext.MAIN_REPO:
            error_msg = format_location_error(
                required=ExecutionContext.WORKTREE,
                actual=ctx.location,
                command_name=func.__name__,
                current_ctx=ctx,
            )
            console.print(error_msg)
            raise typer.Exit(1)

        return func(*args, **kwargs)

    return cast(F, wrapper)


def require_either(func: F) -> F:
    """Decorator for commands that can run in either location.

    This is primarily for documentation - the decorator doesn't enforce
    anything, just marks the function as location-agnostic.

    Example:
        @require_either
        def status():
            # Can run from main repo or worktree
            ctx = get_current_context()
            if ctx.location == ExecutionContext.WORKTREE:
                show_worktree_status()
            else:
                show_main_repo_status()

    Args:
        func: Function to decorate

    Returns:
        Original function (no validation added)
    """
    return func


def set_context_env_vars(ctx: CurrentContext) -> None:
    """Set environment variables for current context.

    Makes context information available to subprocesses and scripts.

    Environment variables set:
        SPEC_KITTY_CONTEXT: "main" or "worktree"
        SPEC_KITTY_CWD: Current working directory
        SPEC_KITTY_REPO_ROOT: Repository root (if detected)
        SPEC_KITTY_WORKTREE_NAME: Worktree name (if in worktree)
        SPEC_KITTY_WORKTREE_PATH: Worktree path (if in worktree)

    Args:
        ctx: Current context information

    Example:
        >>> ctx = get_current_context()
        >>> set_context_env_vars(ctx)
        >>> print(os.environ.get("SPEC_KITTY_CONTEXT"))
        "main"
    """
    os.environ["SPEC_KITTY_CONTEXT"] = ctx.location.value
    os.environ["SPEC_KITTY_CWD"] = str(ctx.cwd)

    if ctx.repo_root:
        os.environ["SPEC_KITTY_REPO_ROOT"] = str(ctx.repo_root)
    else:
        os.environ.pop("SPEC_KITTY_REPO_ROOT", None)

    if ctx.worktree_name:
        os.environ["SPEC_KITTY_WORKTREE_NAME"] = ctx.worktree_name
    else:
        os.environ.pop("SPEC_KITTY_WORKTREE_NAME", None)

    if ctx.worktree_path:
        os.environ["SPEC_KITTY_WORKTREE_PATH"] = str(ctx.worktree_path)
    else:
        os.environ.pop("SPEC_KITTY_WORKTREE_PATH", None)


def get_context_env_vars() -> dict[str, str]:
    """Get current context environment variables.

    Returns:
        Dictionary of context environment variables
    """
    env_vars = {}

    for key in [
        "SPEC_KITTY_CONTEXT",
        "SPEC_KITTY_CWD",
        "SPEC_KITTY_REPO_ROOT",
        "SPEC_KITTY_WORKTREE_NAME",
        "SPEC_KITTY_WORKTREE_PATH",
    ]:
        value = os.environ.get(key)
        if value:
            env_vars[key] = value

    return env_vars


__all__ = [
    "ExecutionContext",
    "CurrentContext",
    "detect_execution_context",
    "get_current_context",
    "require_main_repo",
    "require_worktree",
    "require_either",
    "set_context_env_vars",
    "get_context_env_vars",
]
