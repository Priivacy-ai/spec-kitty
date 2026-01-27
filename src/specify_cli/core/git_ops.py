"""Git and subprocess helpers for the Spec Kitty CLI."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Sequence

from rich.console import Console

ConsoleType = Console | None


def _resolve_console(console: ConsoleType) -> Console:
    """Return the provided console or lazily create one."""
    return console if console is not None else Console()


def run_command(
    cmd: Sequence[str] | str,
    *,
    check_return: bool = True,
    capture: bool = False,
    shell: bool = False,
    console: ConsoleType = None,
    cwd: Path | str | None = None,
) -> tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr).

    Args:
        cmd: Command to run
        check_return: If True, raise on non-zero exit
        capture: If True, capture stdout/stderr
        shell: If True, run through shell
        console: Rich console for output
        cwd: Working directory for command execution

    Returns:
        Tuple of (returncode, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            check=check_return,
            capture_output=capture,
            text=True,
            shell=shell,
            cwd=str(cwd) if cwd else None,
        )
        stdout = (result.stdout or "").strip() if capture else ""
        stderr = (result.stderr or "").strip() if capture else ""
        return result.returncode, stdout, stderr
    except subprocess.CalledProcessError as exc:
        if check_return:
            resolved_console = _resolve_console(console)
            resolved_console.print(f"[red]Error running command:[/red] {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
            resolved_console.print(f"[red]Exit code:[/red] {exc.returncode}")
            if exc.stderr:
                resolved_console.print(f"[red]Error output:[/red] {exc.stderr.strip()}")
        raise


def is_git_repo(path: Path | None = None) -> bool:
    """Return True when the provided path lives inside a git repository."""
    target = (path or Path.cwd()).resolve()
    if not target.is_dir():
        return False
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            check=True,
            capture_output=True,
            cwd=target,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def init_git_repo(project_path: Path, quiet: bool = False, console: ConsoleType = None) -> bool:
    """Initialize a git repository with an initial commit."""
    resolved_console = _resolve_console(console)
    original_cwd = Path.cwd()
    try:
        os.chdir(project_path)
        if not quiet:
            resolved_console.print("[cyan]Initializing git repository...[/cyan]")
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit from Specify template"],
            check=True,
            capture_output=True,
        )
        if not quiet:
            resolved_console.print("[green]✓[/green] Git repository initialized")
        return True
    except subprocess.CalledProcessError as exc:
        if not quiet:
            resolved_console.print(f"[red]Error initializing git repository:[/red] {exc}")
        return False
    finally:
        os.chdir(original_cwd)


def get_current_branch(path: Path | None = None) -> str | None:
    """Return the current git branch name for the provided repository path."""
    repo_path = (path or Path.cwd()).resolve()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            cwd=repo_path,
        )
        branch = result.stdout.strip()
        return branch or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def has_remote(repo_path: Path, remote_name: str = "origin") -> bool:
    """Check if repository has a configured remote.

    Args:
        repo_path: Repository root path
        remote_name: Remote name to check (default: "origin")

    Returns:
        True if remote exists, False otherwise
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", remote_name],
            capture_output=True,
            text=True,
            cwd=repo_path,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def has_tracking_branch(repo_path: Path) -> bool:
    """Check if current branch has upstream tracking configured.

    Args:
        repo_path: Repository root path

    Returns:
        True if current branch tracks a remote branch, False otherwise
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            capture_output=True,
            text=True,
            cwd=repo_path,
            check=False,
        )
        # Returns 0 with output like "origin/main" if tracking exists
        # Returns 128 with error if no tracking configured
        return result.returncode == 0 and result.stdout.strip() != ""
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def exclude_from_git_index(repo_path: Path, patterns: list[str]) -> None:
    """Add patterns to .git/info/exclude to prevent git tracking.

    This is a local-only exclusion (never committed, unlike .gitignore).
    Useful for build artifacts, worktrees, and other local-only files.

    Args:
        repo_path: Repository root path
        patterns: List of patterns to exclude (e.g., [".worktrees/"])
    """
    exclude_file = repo_path / ".git" / "info" / "exclude"
    if not exclude_file.exists():
        return

    # Read existing exclusions
    try:
        existing = set(exclude_file.read_text().splitlines())
    except OSError:
        existing = set()

    # Add new patterns
    new_patterns = [p for p in patterns if p not in existing]
    if new_patterns:
        try:
            with exclude_file.open("a") as f:
                marker = "# Added by spec-kitty (local exclusions)"
                if marker not in existing:
                    f.write(f"\n{marker}\n")
                for pattern in new_patterns:
                    f.write(f"{pattern}\n")
        except OSError:
            pass  # Non-critical, continue silently


__all__ = [
    "exclude_from_git_index",
    "get_current_branch",
    "has_remote",
    "has_tracking_branch",
    "init_git_repo",
    "is_git_repo",
    "run_command",
]
