"""Text-file helpers that refuse to follow a final symlink component."""

from __future__ import annotations

import errno
import os
from pathlib import Path

__all__ = ["NoFollowPathError", "open_no_follow", "read_text_no_follow", "write_text_no_follow"]


class NoFollowPathError(RuntimeError):
    """Raised when a requested path is a symlink and must not be followed."""


def open_no_follow(path: Path, flags: int, mode: int = 0o666) -> int:
    """Open *path* without following a final symlink component.

    On platforms exposing :data:`os.O_NOFOLLOW`, the kernel enforces this on
    the open syscall, closing the check-then-use window. Other platforms get a
    best-effort pre-open symlink check.

    Args:
        path: File path to open.
        flags: Flags accepted by :func:`os.open`.
        mode: Creation mode used when *flags* includes ``os.O_CREAT``.

    Returns:
        An owned file descriptor; callers must close it.

    Raises:
        NoFollowPathError: If *path* is a final-component symlink.
        OSError: If the operating system cannot open the path for another
            reason.
    """
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    if no_follow == 0 and path.is_symlink():
        raise NoFollowPathError(f"{path} is a symlink; refusing to open it")
    try:
        return os.open(path, flags | no_follow, mode)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise NoFollowPathError(f"{path} is a symlink; refusing to open it") from exc
        raise


def read_text_no_follow(path: Path, encoding: str = "utf-8", errors: str | None = None) -> str:
    """Read text from a regular file without following a symlink."""
    fd = open_no_follow(path, os.O_RDONLY)
    with os.fdopen(fd, "r", encoding=encoding, errors=errors) as handle:
        return handle.read()


def write_text_no_follow(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write *content* to a regular file without following a symlink."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = open_no_follow(path, flags)
    with os.fdopen(fd, "w", encoding=encoding) as handle:
        handle.write(content)
