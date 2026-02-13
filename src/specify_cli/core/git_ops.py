"""Git and subprocess helpers for the Spec Kitty CLI."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from rich.console import Console

ConsoleType = Console | None


@dataclass
class BranchResolution:
    """Result of branch resolution for feature operations.

    Attributes:
        target: Target branch from meta.json
        current: User's current branch
        should_notify: True if current != target (informational notification needed)
        action: "proceed" (branches match) or "stay_on_current" (respect user's branch)
    """

    target: str
    current: str
    should_notify: bool
    action: str


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
            encoding="utf-8",
            errors="replace",
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
    """Return the current git branch name for the provided repository path.

    Tries ``git branch --show-current`` first (Git 2.22+, correctly handles
    unborn branches).  Falls back to ``git rev-parse --abbrev-ref HEAD`` for
    older Git versions.  Returns ``None`` for detached HEAD or when not
    inside a git repository.
    """
    repo_path = (path or Path.cwd()).resolve()

    # Primary: git branch --show-current (Git 2.22+)
    # Handles unborn branches correctly and returns empty string for detached HEAD.
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=repo_path,
        )
        branch = result.stdout.strip()
        return branch or None
    except subprocess.CalledProcessError:
        pass
    except FileNotFoundError:
        return None

    # Fallback: git rev-parse --abbrev-ref HEAD (Git < 2.22)
    # Returns "HEAD" for detached HEAD; fails on unborn branches.
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=repo_path,
        )
        branch = result.stdout.strip()
        if branch == "HEAD":
            return None  # Detached HEAD
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
            encoding="utf-8",
            errors="replace",
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
            encoding="utf-8",
            errors="replace",
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


def resolve_primary_branch(repo_root: Path) -> str:
    """Detect the primary branch name for the repository.

    Tries multiple methods in order:
    1. origin/HEAD symbolic ref (most reliable for cloned repos)
    2. Check which common branch exists (main, master, develop)
    3. Fallback to "main"

    Args:
        repo_root: Repository root path

    Returns:
        Primary branch name (e.g., "main", "master", "develop")
    """
    # Method 1: Get from origin's HEAD
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            ref = result.stdout.strip()
            if ref:
                branch = ref.split("/")[-1]
                if branch:
                    return branch
    except subprocess.TimeoutExpired:
        pass

    # Method 2: Check which common branch exists
    for branch in ["main", "master", "develop"]:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--verify", branch],
                cwd=repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                return branch
        except subprocess.TimeoutExpired:
            continue

    # Method 3: Fallback
    return "main"


def resolve_target_branch(
    feature_slug: str,
    repo_path: Path,
    current_branch: str | None = None,
    respect_current: bool = True,
) -> BranchResolution:
    """Resolve target branch for feature operations without auto-checkout.

    This function unifies branch resolution logic across all CLI commands.
    It respects the user's current branch and never performs auto-checkout
    to main/master without explicit permission.

    Args:
        feature_slug: Feature identifier (e.g., "038-v0-15-0-quality-bugfix-release")
        repo_path: Repository root path
        current_branch: User's current branch (auto-detected if None)
        respect_current: If True, stay on current branch (default behavior)

    Returns:
        BranchResolution with:
        - target: Target branch from meta.json (or "main" fallback)
        - current: User's current branch
        - should_notify: True if current != target (show informational message)
        - action: "proceed" if branches match, "stay_on_current" otherwise

    Example:
        >>> resolution = resolve_target_branch("038-bugfix", repo_root, "develop")
        >>> if resolution.should_notify:
        ...     console.print(f"Note: On '{resolution.current}', target is '{resolution.target}'")
        >>> # Proceed on current branch (no checkout)
    """
    # Auto-detect current branch if not provided
    if current_branch is None:
        current_branch = get_current_branch(repo_path)
        if current_branch is None:
            raise RuntimeError("Could not determine current branch")

    # Read target branch from meta.json
    meta_file = repo_path / "kitty-specs" / feature_slug / "meta.json"
    fallback = resolve_primary_branch(repo_path)
    target = fallback
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            target = meta.get("target_branch", fallback)
        except (json.JSONDecodeError, OSError):
            # Fallback to detected primary branch if meta.json is invalid
            target = fallback

    # Check if branches match
    if current_branch == target:
        return BranchResolution(
            target=target,
            current=current_branch,
            should_notify=False,
            action="proceed",
        )

    # Branches differ
    if respect_current:
        # Stay on current branch, notify user
        return BranchResolution(
            target=target,
            current=current_branch,
            should_notify=True,
            action="stay_on_current",
        )
    else:
        # Legacy behavior: auto-checkout allowed (not recommended)
        return BranchResolution(
            target=target,
            current=current_branch,
            should_notify=True,
            action="checkout_target",
        )


__all__ = [
    "BranchResolution",
    "exclude_from_git_index",
    "get_current_branch",
    "has_remote",
    "has_tracking_branch",
    "init_git_repo",
    "is_git_repo",
    "resolve_primary_branch",
    "resolve_target_branch",
    "run_command",
]
