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
from pathlib import Path

from .errors import IntakeError, IntakeRootInconsistentError


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


class CrossFilesystemWriteError(IntakeError):
    """Raised when ``target_tmp`` and ``target`` would cross filesystems."""

    code = "INTAKE_CROSS_FS"

    def __init__(self, *, target: Path) -> None:
        super().__init__(
            f"INTAKE_CROSS_FS: refusing to atomic-write across filesystems for {target}; "
            "set intake.allow_cross_fs=True in .kittify/config.yaml to override.",
            target=str(target),
        )


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
                    # Cross-fs fallback: best-effort copy then unlink.
                    target.write_bytes(payload)
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
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
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

    Both writes go through :func:`atomic_write_text` so a kill-9 mid-write
    cannot leave a half-written file.  The function additionally checks
    that ``scanner_root`` and ``writer_root`` agree (FR-012) before any
    I/O happens, so a misconfigured caller fails before touching disk.
    """
    _validate_root_consistency(scanner_root, writer_root)
    atomic_write_text(brief_path, brief_text, allow_cross_fs=allow_cross_fs)
    atomic_write_text(source_path, source_yaml, allow_cross_fs=allow_cross_fs)


__all__ = [
    "CrossFilesystemWriteError",
    "atomic_write_bytes",
    "atomic_write_text",
    "write_brief_atomic",
]
