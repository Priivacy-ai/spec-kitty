"""Enhanced path resolution for spec-kitty CLI with worktree detection."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple


def locate_project_root(start: Path | None = None) -> Optional[Path]:
    """
    Locate the spec-kitty project root directory using three-tier resolution strategy.

    Resolution order:
    1. SPECIFY_REPO_ROOT environment variable (highest priority)
    2. Git repository root via `git rev-parse --show-toplevel`
    3. Walk up directory tree looking for .kittify/ marker

    Args:
        start: Starting directory for search (defaults to current working directory)

    Returns:
        Path to project root, or None if not found

    Examples:
        >>> # From main repo
        >>> root = locate_project_root()
        >>> assert (root / ".kittify").exists()

        >>> # From worktree
        >>> root = locate_project_root(Path(".worktrees/my-feature"))
        >>> assert (root / ".kittify").exists()
    """
    # Tier 1: Check environment variable (allows override for CI/CD)
    if env_root := os.getenv("SPECIFY_REPO_ROOT"):
        env_path = Path(env_root).resolve()
        if env_path.exists() and (env_path / ".kittify").is_dir():
            return env_path
        # Invalid env var - fall through to other methods

    # Tier 2: Try git repository root
    current = (start or Path.cwd()).resolve()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=current,
            timeout=5,
            check=False
        )
        if result.returncode == 0:
            git_root = Path(result.stdout.strip()).resolve()
            if (git_root / ".kittify").is_dir():
                return git_root
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # Git not available or timed out - fall through to marker search
        pass

    # Tier 3: Walk up directory tree looking for .kittify/ marker
    for candidate in [current, *current.parents]:
        # Handle broken symlinks gracefully
        kittify_path = candidate / ".kittify"
        if kittify_path.is_symlink() and not kittify_path.exists():
            # Broken symlink - skip this candidate
            continue
        if kittify_path.is_dir():
            return candidate

    return None


def is_worktree_context(path: Path) -> bool:
    """
    Detect if the given path is within a git worktree directory.

    Checks if '.worktrees' appears in the path hierarchy, indicating
    execution from within a feature worktree.

    Args:
        path: Path to check (typically current working directory)

    Returns:
        True if path is within .worktrees/ directory, False otherwise

    Examples:
        >>> is_worktree_context(Path("/repo/.worktrees/feature-001"))
        True
        >>> is_worktree_context(Path("/repo/kitty-specs"))
        False
    """
    return ".worktrees" in path.parts


def resolve_with_context(start: Path | None = None) -> Tuple[Optional[Path], bool]:
    """
    Resolve project root and detect worktree context in one call.

    Args:
        start: Starting directory for search (defaults to current working directory)

    Returns:
        Tuple of (project_root, is_worktree)
        - project_root: Path to repo root or None if not found
        - is_worktree: True if executing from within .worktrees/

    Examples:
        >>> # From main repo
        >>> root, in_worktree = resolve_with_context()
        >>> assert in_worktree is False

        >>> # From worktree
        >>> root, in_worktree = resolve_with_context(Path(".worktrees/my-feature"))
        >>> assert in_worktree is True
    """
    current = (start or Path.cwd()).resolve()
    root = locate_project_root(current)
    in_worktree = is_worktree_context(current)
    return root, in_worktree


def check_broken_symlink(path: Path) -> bool:
    """
    Check if a path is a broken symlink (symlink pointing to non-existent target).

    This helper is useful for graceful error handling when dealing with
    worktree symlinks that may become invalid.

    Args:
        path: Path to check

    Returns:
        True if path is a broken symlink, False otherwise

    Note:
        A broken symlink returns True for is_symlink() but False for exists().
        Always check is_symlink() before exists() to detect this condition.
    """
    return path.is_symlink() and not path.exists()


__all__ = [
    "locate_project_root",
    "is_worktree_context",
    "resolve_with_context",
    "check_broken_symlink",
]
