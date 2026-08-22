"""Canonical writer for generated command/skill files (FR-001/002, #3651).

Generated command files are written by
:mod:`specify_cli.runtime.agent_commands` and by a fixed set of ``upgrade``
migrations that correct stale command content on disk (see
``tests/upgrade/test_generated_writer.py`` for the enumerated in-scope
list), and are then made read-only (``chmod & ~0o222``) so a project team
member editing the file by hand notices immediately that it is managed, not
authored.

Every subsequent *re-write* of that same file — by the generation layer
itself on a later run, or by an ``upgrade`` migration correcting stale
content — must restore the write bit before writing and (by default) strip
it again afterwards. Doing this inline at every call site is exactly the
duplicated pattern that caused #3651: a call site that forgot the
restore-before-write half raised ``PermissionError`` (``Errno 13``) the
moment it tried to overwrite its own previously-generated read-only file.

This module owns that lifecycle for those consumers, so it cannot be
forgotten again at their call sites.

Not every generated-file writer in the codebase routes through here.
:mod:`specify_cli.runtime.agent_skills` and :mod:`specify_cli.skills.installer`
manage their own read-only regime independently: both delete and recreate
their whole target tree on every run rather than overwriting an existing
read-only file in place, so the restore-before-write hazard this module
guards against does not apply to them. That is a deliberate, separate
design, not a gap in this module's coverage.

Only stdlib is used here: :mod:`specify_cli.upgrade` depends on
:mod:`specify_cli.runtime`, never the reverse, so a runtime-layer module must
not import anything from ``upgrade/``.
"""

from __future__ import annotations

import os
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

    The write itself is atomic with respect to *path*'s prior content: the
    new content is written to a temporary sibling file in the same
    directory (so it lives on the same filesystem) and then moved into
    place with :func:`os.replace`, which is an atomic rename on every
    platform this project supports. A failure while writing the temporary
    file (disk full, interrupted process, etc.) therefore never truncates
    or corrupts a pre-existing *path* — the original content is left
    exactly as it was.

    If *path* already exists (and may be read-only from a previous write),
    its write bit is restored first so the replace below cannot fail with
    ``PermissionError`` merely because the target was previously marked
    read-only; a directory containing a read-only file does not itself need
    to be writable for :func:`os.replace` to succeed, but the destination
    file's own read-only bit on some platforms can still surface as a
    permission error, so the restore is kept for parity with the previous
    behavior and to avoid a mode mismatch between the temp file and the
    final file. The read-only strip below runs in a ``finally`` block, so
    when ``read_only`` is ``True`` the file is guaranteed to end read-only
    even if something goes wrong after the replace — there is no window in
    which an interrupted run leaves a previously-managed file writable.

    A genuine write failure (disk full, missing parent directory, path is a
    directory, etc.) is not caught here and propagates to the caller — only
    the read-only-target case is handled. On failure, any temporary file
    created during the attempt is cleaned up and *path* is left untouched.

    Symlinks are refused: if *path* is a symlink, this function raises
    ``ValueError`` rather than silently writing through the link to
    whatever it resolves to (or replacing the link itself). Every current
    target of this writer is a regular file in a managed tree; a symlink at
    that location indicates something unexpected happened to the tree, and
    guessing at intent (follow vs. replace-the-link) is worse than failing
    loudly.

    Args:
        path: Destination file. May or may not exist; if it exists it may
            be read-only. Must not be a symlink.
        content: Text to write.
        read_only: When ``True`` (default), the file is left read-only after
            writing. When ``False``, it is left writable.
        encoding: Text encoding used for the write.

    Raises:
        ValueError: If *path* is a symlink.
    """
    if path.is_symlink():
        raise ValueError(
            f"write_generated_file refuses to write through a symlink: {path} "
            "(the managed generated-file tree is expected to contain only "
            "regular files; replace or remove the symlink before writing)"
        )

    existing_mode: int | None = None
    if path.exists():
        existing_mode = path.stat().st_mode
        if existing_mode & _WRITE_BITS == 0:
            path.chmod(existing_mode | _WRITE_BITS)

    tmp_path = path.with_name(f".{path.name}.tmp{os.getpid()}")
    try:
        tmp_path.write_text(content, encoding=encoding)
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    finally:
        if read_only and path.exists():
            written_mode = path.stat().st_mode
            path.chmod(written_mode & ~_WRITE_BITS)
