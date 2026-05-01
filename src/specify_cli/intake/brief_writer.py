"""Atomic write helpers for mission brief + provenance (WP02 T010).

The contract (FR-010, NFR-004) requires that a killed writer never
strands a half-written brief on disk.  We achieve that with the
classic ``open + fsync + replace`` pattern — the temporary file lives
in the same directory as the target, so ``os.replace`` is atomic
within the filesystem.

Cross-filesystem writes are rejected loudly unless the operator opts
in via ``intake.allow_cross_fs=True`` in ``.kittify/config.yaml``
(see :func:`specify_cli.intake.scanner.load_allow_cross_fs`).
"""

from __future__ import annotations

import os
from contextlib import suppress
from pathlib import Path

from .errors import (
    IntakeError,
    IntakePathEscapeError,
    IntakeRootInconsistentError,
)


def _validate_root_consistency(scanner_root: Path, writer_root: Path) -> None:
    """Raise :class:`IntakeRootInconsistentError` if the two roots disagree.

    The scanner and writer must share the same intake root (FR-012).
    Both paths are resolved before comparison so symlinks and trailing
    slashes do not produce spurious mismatches.
    """
    try:
        s_resolved = Path(scanner_root).resolve(strict=False)
        w_resolved = Path(writer_root).resolve(strict=False)
    except OSError as exc:  # pragma: no cover - resolve(strict=False) rarely fails
        raise IntakeRootInconsistentError(
            scanner_root=Path(scanner_root),
            writer_root=Path(writer_root),
        ) from exc
    if s_resolved != w_resolved:
        raise IntakeRootInconsistentError(
            scanner_root=s_resolved,
            writer_root=w_resolved,
        )


def _validate_target_within_root(root: Path, candidate: Path) -> Path:
    """Return the resolved candidate when it stays inside ``root``."""
    resolved_root = Path(root).resolve(strict=False)
    resolved_candidate = Path(candidate).resolve(strict=False)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise IntakePathEscapeError(
            candidate=resolved_candidate,
            intake_root=resolved_root,
        ) from exc
    return resolved_candidate


class CrossFilesystemWriteError(IntakeError):
    """Raised when ``target_tmp`` and ``target`` would cross filesystems."""

    code = "INTAKE_CROSS_FS"

    def __init__(self, *, target: Path) -> None:
        super().__init__(
            f"INTAKE_CROSS_FS: refusing to atomic-write across filesystems for {target}; "
            "set intake.allow_cross_fs=True in .kittify/config.yaml to override.",
            target=str(target),
        )


def _write_payload_via_parent_dirfd(target: Path, payload: bytes) -> None:
    """Write via the already-resolved parent directory descriptor.

    This keeps the writable directory fixed while addressing only the
    basename relative to that directory, which avoids constructing a
    fresh absolute path at the fallback sink.
    """
    parent_fd = os.open(target.parent, os.O_RDONLY)
    target_fd: int | None = None
    try:
        target_fd = os.open(
            target.name,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o666,
            dir_fd=parent_fd,
        )
        with os.fdopen(target_fd, "wb", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if target_fd is not None:
            os.close(target_fd)
        os.close(parent_fd)


def atomic_write_bytes(
    target: Path,
    payload: bytes,
    *,
    allow_cross_fs: bool = False,
) -> None:
    """Atomically write ``payload`` to ``target`` (open + fsync + replace).

    The temporary file is created in the same directory as ``target``
    so ``os.replace`` is atomic on POSIX filesystems.  ``fsync()`` is
    called before the rename so the data is durable across power loss.

    A unique PID-and-random suffix is used for the temp file so
    concurrent writers never clobber each other's tmp files.

    Args:
        target: Final path to write.
        payload: Bytes to write.
        allow_cross_fs: When ``True``, fall back to a non-atomic write
            if the temp file would cross filesystems (rare; only
            relevant on bind mounts).  Default ``False`` — fail loudly.
    """
    target = Path(target)
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)

    # PID + os.urandom(4) keeps tmp names unique across forks.
    suffix = f".{os.getpid()}.{os.urandom(4).hex()}.tmp"
    tmp = parent / (target.name + suffix)

    try:
        with open(tmp, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())

        # Detect cross-filesystem rename risk: if parent and tmp resolve
        # to different st_dev values from target's expected mount, we
        # still proceed (same parent guarantees same fs in normal cases),
        # but if target already exists on a different fs we surface it.
        if target.exists():
            try:
                target_dev = target.stat().st_dev
                tmp_dev = tmp.stat().st_dev
                if target_dev != tmp_dev:
                    if not allow_cross_fs:
                        raise CrossFilesystemWriteError(target=target)
                    # Cross-fs fallback: best-effort direct write through the
                    # already-resolved parent directory descriptor.
                    _write_payload_via_parent_dirfd(target, payload)
                    tmp.unlink(missing_ok=True)
                    return
            except OSError:
                # If we can't stat, proceed with replace — replace will
                # raise on its own if the operation is illegal.
                pass

        os.replace(tmp, target)
    except BaseException:
        # On *any* failure (incl. KeyboardInterrupt, SystemExit) clean
        # up the tmp file so we never leave partial state behind.
        with suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise


def atomic_write_text(
    target: Path,
    text: str,
    *,
    encoding: str = "utf-8",
    allow_cross_fs: bool = False,
) -> None:
    """Encode ``text`` and call :func:`atomic_write_bytes`."""
    atomic_write_bytes(
        Path(target),
        text.encode(encoding),
        allow_cross_fs=allow_cross_fs,
    )


def write_brief_atomic(
    *,
    scanner_root: Path,
    writer_root: Path,
    brief_path: Path,
    brief_text: str,
    source_path: Path,
    source_yaml: str,
    allow_cross_fs: bool = False,
) -> None:
    """Atomically write the mission brief and its provenance sidecar.

    Each individual write is atomic via ``open + fsync + replace`` (the
    ``atomic_write_text`` helper). True pair-atomicity is impossible on
    POSIX (only single-file rename is atomic), so this helper enforces an
    ordering that minimises the window during which a reader can observe
    inconsistent state:

    1. ``source.yaml`` is renamed FIRST.
    2. ``brief.md``  is renamed SECOND, acting as the "commit marker"
       for the pair.

    A reader that consults ``brief.md`` first will see "no brief" any time
    the brief has not yet been renamed in — including the entire window
    between step 1 and step 2. The companion reader
    (``mission_brief.read_brief_source``) honours this by treating
    ``source-without-brief`` as ``None`` (equivalent to "no brief"). The
    legacy recovery branch in ``write_mission_brief`` then unlinks the
    orphan source on the next write.

    Note that we also tolerate stale ``.tmp`` files left behind by a
    kill between fsync and the first rename — each ``atomic_write_*``
    call uses a unique ``PID.hex`` suffix so concurrent writers and
    crashed predecessors never collide on the same temp filename.
    """
    _validate_root_consistency(scanner_root, writer_root)
    _validate_target_within_root(writer_root, brief_path)
    _validate_target_within_root(writer_root, source_path)
    # Source first so brief.md remains the canonical "commit marker"
    # for the pair. The reader treats source-without-brief as no brief.
    atomic_write_text(source_path, source_yaml, allow_cross_fs=allow_cross_fs)
    atomic_write_text(brief_path, brief_text, allow_cross_fs=allow_cross_fs)


__all__ = [
    "CrossFilesystemWriteError",
    "atomic_write_bytes",
    "atomic_write_text",
    "write_brief_atomic",
]
