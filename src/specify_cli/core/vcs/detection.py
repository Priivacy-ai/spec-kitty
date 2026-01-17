"""
VCS Detection Module
====================

This module provides tool detection and the get_vcs() factory function.
It detects which VCS tools (git, jj) are available and returns the
appropriate implementation.

See kitty-specs/015-first-class-jujutsu-vcs-integration/contracts/vcs-protocol.py
for the factory function contract.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

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
def is_jj_available() -> bool:
    """
    Check if jj is installed and working.

    Returns:
        True if jj is installed and responds to --version, False otherwise.
    """
    if shutil.which("jj") is None:
        return False
    try:
        result = subprocess.run(
            ["jj", "--version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


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
def get_jj_version() -> str | None:
    """
    Get installed jj version, or None if not installed.

    Returns:
        Version string (e.g., "0.23.0") or None if jj is not available.
    """
    if not is_jj_available():
        return None
    try:
        result = subprocess.run(
            ["jj", "--version"],
            capture_output=True,
            timeout=5,
            text=True,
        )
        if result.returncode != 0:
            return None
        # jj version format: "jj 0.23.0"
        output = result.stdout.strip()
        match = re.search(r"jj\s+(\d+\.\d+\.\d+)", output)
        if match:
            return match.group(1)
        # Fallback: return everything after "jj "
        if output.startswith("jj "):
            return output[3:].strip()
        return "unknown"
    except (subprocess.TimeoutExpired, OSError):
        return None


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
        List of available backends, in preference order (jj first if available).
    """
    backends = []
    if is_jj_available():
        backends.append(VCSBackend.JUJUTSU)
    if is_git_available():
        backends.append(VCSBackend.GIT)
    return backends


# =============================================================================
# Factory Function
# =============================================================================


def _get_locked_vcs_from_feature(path: Path) -> VCSBackend | None:
    """
    Read VCS from feature meta.json if exists.

    Args:
        path: A path that might be within a feature directory.

    Returns:
        The locked VCSBackend if found, None otherwise.
    """
    # Search for kitty-specs/###-feature/meta.json by walking up
    current = path.resolve()

    # Also check if path itself contains kitty-specs
    for parent in [current, *current.parents]:
        # Check for kitty-specs directory
        kitty_specs = parent / "kitty-specs"
        if kitty_specs.is_dir():
            # Search feature directories in kitty-specs
            for feature_dir in kitty_specs.iterdir():
                if feature_dir.is_dir():
                    meta_path = feature_dir / "meta.json"
                    if meta_path.is_file():
                        try:
                            meta = json.loads(meta_path.read_text())
                            if "vcs" in meta:
                                vcs_value = meta["vcs"]
                                return VCSBackend(vcs_value)
                        except (json.JSONDecodeError, ValueError, OSError):
                            continue
            break

    # Check if we're in a worktree that might have feature info in path
    # e.g., .worktrees/015-feature-WP01/
    if ".worktrees" in str(current):
        # Try to find meta.json in the main repo's kitty-specs
        for parent in current.parents:
            if parent.name == ".worktrees":
                main_repo = parent.parent
                kitty_specs = main_repo / "kitty-specs"
                if kitty_specs.is_dir():
                    # Extract feature number from worktree name
                    worktree_name = current.name
                    # Pattern: ###-feature-name-WP##
                    match = re.match(r"(\d{3})-", worktree_name)
                    if match:
                        feature_num = match.group(1)
                        for feature_dir in kitty_specs.iterdir():
                            if feature_dir.is_dir() and feature_dir.name.startswith(
                                f"{feature_num}-"
                            ):
                                meta_path = feature_dir / "meta.json"
                                if meta_path.is_file():
                                    try:
                                        meta = json.loads(meta_path.read_text())
                                        if "vcs" in meta:
                                            return VCSBackend(meta["vcs"])
                                    except (json.JSONDecodeError, ValueError, OSError):
                                        pass
                break

    return None


def _instantiate_backend(backend: VCSBackend) -> "VCSProtocol":
    """
    Instantiate the appropriate VCS implementation.

    Args:
        backend: The backend to instantiate.

    Returns:
        A VCSProtocol implementation.

    Raises:
        VCSNotFoundError: If the requested backend is not available.
    """
    if backend == VCSBackend.JUJUTSU:
        if not is_jj_available():
            raise VCSNotFoundError(
                "jj is not available. Install jj from https://github.com/martinvonz/jj"
            )
        # Lazy import to avoid circular imports
        from .jujutsu import JujutsuVCS

        return JujutsuVCS()
    elif backend == VCSBackend.GIT:
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
    prefer_jj: bool = True,
) -> "VCSProtocol":
    """
    Factory function to get appropriate VCS implementation.

    Args:
        path: Path within a repository or feature directory.
        backend: Explicit backend choice (None = auto-detect).
        prefer_jj: If auto-detecting, prefer jj over git when both available.

    Returns:
        VCSProtocol implementation (GitVCS or JujutsuVCS).

    Raises:
        VCSNotFoundError: Neither jj nor git available.
        VCSBackendMismatchError: Requested backend doesn't match feature's locked VCS.

    Detection order:
        1. If backend specified, use that
        2. If path is in a feature, read meta.json for locked VCS
        3. If jj available and prefer_jj=True, use jj
        4. If git available, use git
        5. Raise VCSNotFoundError
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
    if prefer_jj and is_jj_available():
        # Lazy import to avoid circular imports
        from .jujutsu import JujutsuVCS

        return JujutsuVCS()

    if is_git_available():
        # Lazy import to avoid circular imports
        from .git import GitVCS

        return GitVCS()

    # 4. Neither available
    raise VCSNotFoundError(
        "Neither jj nor git is available. "
        "Please install at least one of:\n"
        "  - jj (recommended): https://github.com/martinvonz/jj#installation\n"
        "  - git: https://git-scm.com/downloads"
    )


# =============================================================================
# Cache Management (for testing)
# =============================================================================


def _clear_detection_cache() -> None:
    """
    Clear the detection cache. For testing purposes only.

    This clears the cached results of is_jj_available, is_git_available,
    get_jj_version, and get_git_version.
    """
    is_jj_available.cache_clear()
    is_git_available.cache_clear()
    get_jj_version.cache_clear()
    get_git_version.cache_clear()
