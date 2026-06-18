"""Shared utility helpers used across Spec Kitty modules."""

from __future__ import annotations

import os
import tempfile
import shutil
import sys
from collections.abc import Sequence
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


def ensure_within_directory(path: Path, root: Path) -> Path:
    """Resolve ``path`` and assert it remains under ``root``."""
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"Refusing to access path outside {resolved_root}: {resolved_path}") from exc
    return resolved_path


def ensure_within_any(
    path: Path, *, roots: Sequence[Path], files: Sequence[Path] = ()
) -> Path:
    """Return ``path.resolve(strict=False)`` if it is under any of ``roots`` OR equals
    an allowed exact file in ``files``; else raise ``ValueError``.

    Multi-root sibling of ``ensure_within_directory``. Uses ``resolve(strict=False)``
    intentionally so that non-existent snapshot/rollback paths (which may not yet
    exist on disk) are accepted when they fall under a trusted root.

    Args:
        path: The candidate path to validate.
        roots: Trusted root directories. A resolved ``path`` is accepted when
            it is relative to any of these roots.
        files: Optional allowlist of exact file paths. A resolved ``path`` is
            accepted when it equals the resolved form of any entry here, even if
            it falls under no root.

    Returns:
        The resolved (strict=False) form of ``path``.

    Raises:
        ValueError: When ``path`` is neither under any root nor equal to any
            allowed file.
    """
    resolved = path.resolve(strict=False)
    resolved_roots = [r.resolve(strict=False) for r in roots]
    resolved_files = [f.resolve(strict=False) for f in files]

    if any(resolved == allowed for allowed in resolved_files):
        return resolved

    if any(_is_relative_to(resolved, root) for root in resolved_roots):
        return resolved

    raise ValueError(
        f"Refusing to access path outside trusted roots: {resolved}"
    )


def _is_relative_to(path: Path, root: Path) -> bool:
    """Return True when ``path`` is relative to ``root`` (Python 3.9+ compatible helper)."""
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def write_text_within_directory(path: Path, content: str, *, root: Path, encoding: str = "utf-8") -> Path:
    """Atomically write text to a file only when the resolved path stays under ``root``."""
    safe_path = ensure_within_directory(path, root)
    safe_path.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(dir=safe_path.parent, prefix=f".{safe_path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as handle:
            handle.write(content)
        Path(temp_path).replace(safe_path)
    except Exception:
        Path(temp_path).unlink(missing_ok=True)
        raise
    return safe_path


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


__all__ = [
    "format_path",
    "ensure_directory",
    "ensure_within_any",
    "ensure_within_directory",
    "write_text_within_directory",
    "safe_remove",
    "get_platform",
]
