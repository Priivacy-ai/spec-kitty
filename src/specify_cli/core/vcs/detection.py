"""
VCS Detection Module
====================

This module provides tool detection and the get_vcs() factory function.
It detects whether git is available and returns the appropriate implementation.
"""

from __future__ import annotations

from specify_cli.core.constants import KITTY_SPECS_DIR
import contextlib
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from specify_cli.mission_metadata import load_meta

from .exceptions import (
    VCSBackendMismatchError,
    VCSNotFoundError,
)
from .types import VCSBackend

if TYPE_CHECKING:
    from .protocol import VCSProtocol


# =============================================================================
# Tool Detection Functions
# =============================================================================


@lru_cache(maxsize=1)
def is_git_available() -> bool:
    """
    Check if git is installed and working.

    Returns:
        True if git is installed and responds to --version, False otherwise.
    """
    if shutil.which("git") is None:
        return False
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


@lru_cache(maxsize=1)
def get_git_version() -> str | None:
    """
    Get installed git version, or None if not installed.

    Returns:
        Version string (e.g., "2.43.0") or None if git is not available.
    """
    if not is_git_available():
        return None
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            timeout=5,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            return None
        # git version format: "git version 2.43.0" or "git version 2.43.0.windows.1"
        output = result.stdout.strip()
        match = re.search(r"git version\s+(\d+\.\d+\.\d+)", output)
        if match:
            return match.group(1)
        # Fallback: return everything after "git version "
        if "git version " in output:
            return output.split("git version ")[1].strip()
        return "unknown"
    except (subprocess.TimeoutExpired, OSError):
        return None


def detect_available_backends() -> list[VCSBackend]:
    """
    Detect which VCS tools are installed and available.

    Returns:
        List of available backends.
    """
    backends = []
    if is_git_available():
        backends.append(VCSBackend.GIT)
    return backends


# =============================================================================
# Factory Function
# =============================================================================


def _get_locked_vcs_from_feature(path: Path) -> VCSBackend | None:
    """
    Read VCS from feature meta.json if path is inside that feature.

    Args:
        path: A path that might be within a feature directory.

    Returns:
        The locked VCSBackend if path is inside a feature with locked VCS, None otherwise.

    Note:
        Only returns a locked VCS if `path` is actually inside the feature directory
        (either in kitty-specs/###-feature/ or in a worktree for that feature).
        Does NOT return VCS for unrelated features.
    """
    current = path.resolve()

    # Strategy 1: Check if path is directly inside kitty-specs/###-feature/
    # e.g., /repo/kitty-specs/015-feature/tasks/WP01.md
    for parent in [current, *current.parents]:
        if parent.parent and parent.parent.name == KITTY_SPECS_DIR:
            # parent is a feature directory like kitty-specs/015-feature/
            meta = load_meta(parent, on_malformed="none")
            if meta is not None and "vcs" in meta:
                with contextlib.suppress(ValueError):
                    return VCSBackend(meta["vcs"])
            # Path is in a feature dir but no valid meta.json
            return None

    # Strategy 2: Check if we're in a worktree for a feature
    # e.g., .worktrees/015-feature-name-lane-a/src/file.py
    if ".worktrees" in str(current):
        # Find the worktree root (direct child of .worktrees/)
        worktree_root = None
        for parent in [current, *current.parents]:
            if parent.parent and parent.parent.name == ".worktrees":
                worktree_root = parent
                break

        if worktree_root:
            # Resolve the mission slug from the worktree dir name via the
            # canonical dual-era grammar. The dir name is the body of the lane
            # branch (``kitty/mission-<name>``), so it carries either legacy
            # ``NNN-slug-lane-x`` or mid8-era ``<slug>-<mid8>-lane-x``. The old
            # ``re.match(r"(\d{3})-", ...)`` returned None for EVERY mid8
            # mission — silent signal loss (#1860 class).
            from specify_cli.lanes.branch_naming import parse_mission_slug_from_branch

            worktree_name = worktree_root.name
            parsed = parse_mission_slug_from_branch(f"kitty/mission-{worktree_name}")
            if parsed is not None:
                # Match the kitty-specs feature dir for the resolved slug.
                # Legacy worktrees embed the full ``NNN-slug`` (dir name matches
                # exactly); mid8 worktrees carry the human-slug (the dir name is
                # the slug, optionally still NNN-prefixed in kitty-specs).
                main_repo = worktree_root.parent.parent
                mission_specs = main_repo / KITTY_SPECS_DIR
                if mission_specs.is_dir():
                    slug = parsed.slug
                    for feature_dir in mission_specs.iterdir():
                        if not feature_dir.is_dir():
                            continue
                        name = feature_dir.name
                        if name == slug or name.endswith(f"-{slug}") or name == f"{slug}":
                            meta = load_meta(feature_dir, on_malformed="none")
                            if meta is not None and "vcs" in meta:
                                with contextlib.suppress(ValueError):
                                    return VCSBackend(meta["vcs"])
                            # Found feature dir but no valid meta.json
                            return None

    # Path is not inside any feature
    return None


def _instantiate_backend(backend: VCSBackend) -> VCSProtocol:
    """
    Instantiate the appropriate VCS implementation.

    Args:
        backend: The backend to instantiate.

    Returns:
        A VCSProtocol implementation.

    Raises:
        VCSNotFoundError: If the requested backend is not available.
    """
    if backend == VCSBackend.GIT:
        if not is_git_available():
            raise VCSNotFoundError("git is not available. Please install git.")
        # Lazy import to avoid circular imports
        from .git import GitVCS

        return GitVCS()
    else:
        raise VCSNotFoundError(f"Unknown VCS backend: {backend}")


def get_vcs(
    path: Path,
    backend: VCSBackend | None = None,
) -> VCSProtocol:
    """
    Factory function to get appropriate VCS implementation.

    Args:
        path: Path within a repository or feature directory.
        backend: Explicit backend choice (None = auto-detect).

    Returns:
        VCSProtocol implementation (GitVCS).

    Raises:
        VCSNotFoundError: Git is not available.
        VCSBackendMismatchError: Requested backend doesn't match feature's locked VCS.

    Detection order:
        1. If backend specified, use that
        2. If path is in a feature, read meta.json for locked VCS
        3. If git available, use git
        4. Raise VCSNotFoundError
    """
    # 1. If explicit backend specified, use that
    if backend is not None:
        # Check if there's a locked VCS that conflicts
        locked = _get_locked_vcs_from_feature(path)
        if locked is not None and locked != backend:
            raise VCSBackendMismatchError(
                f"Requested backend '{backend.value}' doesn't match feature's "
                f"locked VCS '{locked.value}'. "
                f"Features must use the same VCS throughout their lifecycle."
            )
        return _instantiate_backend(backend)

    # 2. Check for locked VCS in feature meta.json
    locked = _get_locked_vcs_from_feature(path)
    if locked is not None:
        return _instantiate_backend(locked)

    # 3. Auto-detect based on availability
    if is_git_available():
        # Lazy import to avoid circular imports
        from .git import GitVCS

        return GitVCS()

    # 4. git not available
    raise VCSNotFoundError(
        "git is not available. "
        "Please install git: https://git-scm.com/downloads"
    )


# =============================================================================
# Cache Management (for testing)
# =============================================================================


def _clear_detection_cache() -> None:
    """
    Clear the detection cache. For testing purposes only.

    This clears the cached results of is_git_available and get_git_version.
    """
    is_git_available.cache_clear()
    get_git_version.cache_clear()
