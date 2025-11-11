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
) -> tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            check=check_return,
            capture_output=capture,
            text=True,
            shell=shell,
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


__all__ = [
    "get_current_branch",
    "init_git_repo",
    "is_git_repo",
    "run_command",
]
