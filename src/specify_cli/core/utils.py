"""Shared utility helpers used across Spec Kitty modules."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def format_path(path: Path, relative_to: Path | None = None) -> str:
    """Return a string path, optionally relative to another directory."""
    target = path
    if relative_to is not None:
        try:
            target = path.relative_to(relative_to)
        except ValueError:
            target = path
    return str(target)


def ensure_directory(path: Path) -> Path:
    """Create a directory (and parents) if it does not exist and return the Path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_remove(path: Path) -> bool:
    """Remove a file or directory tree if it exists, returning True when something was removed."""
    if not path.exists():
        return False
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()
    return True


def get_platform() -> str:
    """Return the current platform identifier (linux/darwin/win32)."""
    return sys.platform


__all__ = ["format_path", "ensure_directory", "safe_remove", "get_platform"]
