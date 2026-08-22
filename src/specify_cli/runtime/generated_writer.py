"""Canonical writer for generated command/skill files (FR-001/002, #3651).

Every generated command or skill file on disk is written by the generation
layer (:mod:`specify_cli.runtime.agent_commands`,
:mod:`specify_cli.runtime.agent_skills`, :mod:`specify_cli.skills.installer`)
and then made read-only (``chmod & ~0o222``) so a project team member editing
the file by hand notices immediately that it is managed, not authored.

Every subsequent *re-write* of that same file — by the generation layer
itself on a later run, or by an ``upgrade`` migration correcting stale
content — must restore the write bit before writing and (by default) strip
it again afterwards. Doing this inline at every call site is exactly the
duplicated pattern that caused #3651: a call site that forgot the
restore-before-write half raised ``PermissionError`` (``Errno 13``) the
moment it tried to overwrite its own previously-generated read-only file.

This module owns that lifecycle once, for every consumer, so it cannot be
forgotten again.

Only stdlib is used here: :mod:`specify_cli.upgrade` depends on
:mod:`specify_cli.runtime`, never the reverse, so a runtime-layer module must
not import anything from ``upgrade/``.
"""

from __future__ import annotations

from pathlib import Path

# The write bit for owner/group/other. Stripping it makes a file read-only
# in the same sense the generation layer already uses elsewhere
# (``agent_commands.py``, ``agent_skills.py``, ``skills/installer.py``).
_WRITE_BITS = 0o222


def write_generated_file(
    path: Path,
    content: str,
    *,
    read_only: bool = True,
    encoding: str = "utf-8",
) -> None:
    """Write *content* to *path*, owning the read-only permission lifecycle.

    If *path* already exists (and may be read-only from a previous write),
    its write bit is restored first so the write below cannot fail with
    ``PermissionError`` merely because the target was previously marked
    read-only. After writing, the write bit is stripped again when
    ``read_only`` is ``True`` (the default), leaving the file in the same
    managed, read-only state every generated command/skill file is expected
    to be in.

    A genuine write failure (disk full, missing parent directory, path is a
    directory, etc.) is not caught here and propagates to the caller — only
    the read-only-target case is handled.

    Args:
        path: Destination file. May or may not exist; if it exists it may
            be read-only.
        content: Text to write.
        read_only: When ``True`` (default), the file is left read-only after
            writing. When ``False``, it is left writable.
        encoding: Text encoding used for the write.
    """
    if path.exists():
        current_mode = path.stat().st_mode
        path.chmod(current_mode | _WRITE_BITS)

    path.write_text(content, encoding=encoding)

    if read_only:
        written_mode = path.stat().st_mode
        path.chmod(written_mode & ~_WRITE_BITS)
