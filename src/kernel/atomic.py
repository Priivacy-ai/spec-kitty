"""Atomic file write utility.

Guarantees: file is either complete old content or complete new content,
never partial. Uses write-to-temp-then-rename on the same filesystem.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path


def atomic_write(path: Path, content: str | bytes, *, mkdir: bool = False) -> None:
    """Write *content* atomically to *path*.

    Parameters
    ----------
    path : Path
        Target file path.
    content : str | bytes
        File content. ``str`` is encoded to UTF-8; ``bytes`` is written raw.
    mkdir : bool
        If True, create parent directories before writing.
    """
    if mkdir:
        path.parent.mkdir(parents=True, exist_ok=True)

    raw = content.encode("utf-8") if isinstance(content, str) else content

    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=".atomic-",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
        # fd is now closed by the context manager
        os.replace(tmp_path, str(path))
    except BaseException:
        with contextlib.suppress(OSError):
            os.close(fd)
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
