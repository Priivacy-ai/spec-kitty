"""Enhanced path resolution for spec-kitty CLI with worktree detection."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple


def locate_project_root(start: Path | None = None) -> Optional[Path]:
    """
    Locate the MAIN spec-kitty project root directory, even from within worktrees.

    This function correctly handles git worktrees by detecting when .git is a
    file (worktree pointer) vs a directory (main repo), and following the
    pointer back to the main repository.

    Resolution order:
    1. SPECIFY_REPO_ROOT environment variable (highest priority)
    2. Walk up directory tree, detecting worktree .git files and following to main repo
    3. Fall back to .kittify/ marker search

    Args:
        start: Starting directory for search (defaults to current working directory)

    Returns:
        Path to MAIN project root (not worktree), or None if not found

    Examples:
        >>> # From main repo
        >>> root = locate_project_root()
        >>> assert (root / ".kittify").exists()

        >>> # From worktree - returns MAIN repo, not worktree
        >>> root = locate_project_root(Path(".worktrees/my-feature"))
        >>> assert ".worktrees" not in str(root)
    """
    # Tier 1: Check environment variable (allows override for CI/CD)
    if env_root := os.getenv("SPECIFY_REPO_ROOT"):
        env_path = Path(env_root).resolve()
        if env_path.exists() and (env_path / ".kittify").is_dir():
            return env_path
        # Invalid env var - fall through to other methods

    # Tier 2: Walk up directory tree, handling worktree .git files
    current = (start or Path.cwd()).resolve()

    for candidate in [current, *current.parents]:
        git_path = candidate / ".git"

        if git_path.is_file():
            # This is a worktree! The .git file contains a pointer to the main repo.
            # Format: "gitdir: /path/to/main/.git/worktrees/worktree-name"
            try:
                content = git_path.read_text().strip()
                if content.startswith("gitdir:"):
                    gitdir = Path(content.split(":", 1)[1].strip())
                    # Navigate: .git/worktrees/name -> .git -> main repo root
                    main_git_dir = gitdir.parent.parent
                    main_repo = main_git_dir.parent
                    if main_repo.exists() and (main_repo / ".kittify").is_dir():
                        return main_repo
            except (OSError, ValueError):
                # If we can't read or parse the .git file, continue searching
                pass

        elif git_path.is_dir():
            # This is the main repo (or a regular git repo)
            if (candidate / ".kittify").is_dir():
                return candidate

        # Also check for .kittify marker (fallback for non-git scenarios)
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


def get_main_repo_root(current_path: Path) -> Path:
    """
    Get the main repository root, even if called from a worktree.

    When in a worktree, .git is a file pointing to the main repo's .git directory.
    This function follows that pointer to find the main repo root.

    Args:
        current_path: Current repo root (may be worktree or main repo)

    Returns:
        Path to the main repository root (resolves worktree pointers)

    Examples:
        >>> # From main repo - returns same path
        >>> get_main_repo_root(Path("/repo"))
        Path('/repo')

        >>> # From worktree - returns main repo
        >>> get_main_repo_root(Path("/repo/.worktrees/feature-001"))
        Path('/repo')
    """
    git_file = current_path / ".git"

    if git_file.is_file():
        try:
            git_content = git_file.read_text().strip()
            if git_content.startswith("gitdir:"):
                gitdir = Path(git_content.split(":", 1)[1].strip())
                # Navigate: .git/worktrees/name -> .git -> main repo root
                main_git_dir = gitdir.parent.parent
                main_repo_root = main_git_dir.parent
                return main_repo_root
        except (OSError, ValueError):
            pass

    return current_path


# DEPRECATED: find_feature_slug() has been removed
# Use detect_feature_slug() from specify_cli.core.feature_detection instead
#
# Migration:
#   from specify_cli.core.feature_detection import detect_feature_slug
#   slug = detect_feature_slug(repo_root)
#
# The new centralized implementation provides:
# - Deterministic behavior (no "highest numbered" guessing)
# - Explicit error messages guiding users to --feature flag
# - Consistent behavior across all commands


__all__ = [
    "locate_project_root",
    "is_worktree_context",
    "resolve_with_context",
    "check_broken_symlink",
    "get_main_repo_root",
    # find_feature_slug has been removed - use detect_feature_slug from core.feature_detection
]
