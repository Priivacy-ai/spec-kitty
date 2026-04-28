"""Cross-platform machine-wide advisory file lock helper.

Provides a self-contained async context manager (``MachineFileLock``) that
serialises access to a chosen on-disk path across CLI processes on a single
machine. It wraps the appropriate OS primitive per platform:

- POSIX (macOS, Linux): :func:`fcntl.flock` with ``LOCK_EX | LOCK_NB``.
- Windows: :func:`msvcrt.locking` with ``LK_NBLCK``.

The helper is consumed by:

- WP02 — ``specify_cli.auth.refresh_transaction`` to serialise OAuth refresh.
- WP06 — ``specify_cli.cli.commands._auth_doctor`` to introspect / unstick a
  stale lock.

Beyond the OS-level lock, the helper writes a small JSON record describing
the holder (PID, host, version, ISO-8601 ``started_at``) so diagnostic tools
such as ``auth doctor`` can identify whose process is holding the lock and
whether it appears to be stuck.

This module is intentionally side-effect-free at import time and adds no new
third-party dependencies.
"""

from __future__ import annotations

import asyncio
import contextlib
import errno
import json
import os
import socket
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import metadata as importlib_metadata
from pathlib import Path
from types import TracebackType
from typing import Any

if sys.platform == "win32":  # pragma: no cover - platform-specific
    import msvcrt
else:
    import fcntl  # noqa: F401  (imported lazily under POSIX guard)

__all__ = [
    "STALE_AFTER_S_DEFAULT",
    "LockAcquireTimeout",
    "LockRecord",
    "MachineFileLock",
    "force_release",
    "read_lock_record",
]


STALE_AFTER_S_DEFAULT: float = 60.0
"""Default age threshold (seconds) above which a lock record is considered stale.

Stale locks may be safely adopted by new acquirers and removed via
:func:`force_release`. The default is 6× the NFR-002 hold ceiling (10 s) so
slow but legitimate transactions are never preempted.
"""

_ACQUIRE_TIMEOUT_DEFAULT: float = 10.0
_MAX_HOLD_DEFAULT: float = 10.0
_RETRY_SLEEP_S: float = 0.1
_SCHEMA_VERSION: int = 1


class LockAcquireTimeout(Exception):
    """Raised when a :class:`MachineFileLock` cannot acquire within the bounded wait.

    The lock path that timed out is exposed via :attr:`path` for diagnostics.
    """

    def __init__(self, *, path: str) -> None:
        super().__init__(f"Could not acquire machine lock at {path!r} within bounded wait")
        self.path = path


@dataclass(frozen=True)
class LockRecord:
    """Snapshot of the holder of a machine-wide file lock.

    Fields mirror the JSON record persisted under the lock file:

    - ``schema_version`` — content schema version (currently ``1``).
    - ``pid`` — operating-system process identifier of the holder.
    - ``started_at`` — tz-aware UTC :class:`datetime` when the lock was taken.
    - ``host`` — hostname of the machine that wrote the record.
    - ``version`` — ``spec-kitty-cli`` package version (or ``"unknown"``).
    """

    schema_version: int
    pid: int
    started_at: datetime
    host: str
    version: str

    @property
    def age_s(self) -> float:
        """Return seconds elapsed since :attr:`started_at` (clamped at ``0``)."""
        delta = (datetime.now(UTC) - self.started_at).total_seconds()
        return delta if delta > 0 else 0.0

    def is_stuck(self, threshold_s: float = STALE_AFTER_S_DEFAULT) -> bool:
        """Return ``True`` when :attr:`age_s` exceeds ``threshold_s``."""
        return self.age_s > threshold_s


def _get_package_version() -> str:
    """Return the installed ``spec-kitty-cli`` version, or ``"unknown"``."""
    try:
        return importlib_metadata.version("spec-kitty-cli")
    except importlib_metadata.PackageNotFoundError:
        return "unknown"


def _is_contention_error(exc: OSError) -> bool:
    """Return ``True`` when ``exc`` is a normal non-blocking lock contention.

    Non-contention :class:`OSError` instances (genuine I/O errors such as
    ``ENOSPC``) propagate to the caller — the helper does not silently treat
    them as contention.
    """
    if isinstance(exc, BlockingIOError):
        return True
    if exc.errno is None:
        return False
    if sys.platform == "win32":
        return exc.errno in {errno.EACCES, errno.EDEADLK}
    return exc.errno in {errno.EACCES, errno.EAGAIN}


def _os_lock(fd: int) -> None:
    """Acquire a non-blocking exclusive OS-level lock on ``fd``.

    Raises :class:`OSError` on contention; callers must use
    :func:`_is_contention_error` to distinguish contention from genuine errors.
    """
    if sys.platform == "win32":  # pragma: no cover - platform-specific
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _os_unlock(fd: int) -> None:
    """Release an OS-level lock on ``fd`` previously acquired via :func:`_os_lock`."""
    if sys.platform == "win32":  # pragma: no cover - platform-specific
        # Best-effort: release errors do not invalidate caller invariants.
        with contextlib.suppress(OSError):
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        with contextlib.suppress(OSError):
            fcntl.flock(fd, fcntl.LOCK_UN)


def _atomic_write_under_lock(fd: int, payload: bytes) -> None:
    """Replace the contents of the locked ``fd`` with ``payload`` atomically.

    Atomic for concurrent readers in practice: readers that race the truncate
    window observe an empty file (handled as "no record"); readers that
    arrive after the single ``write`` see the complete record. Sub-PIPE_BUF
    writes to regular files are atomic on POSIX, ruling out partial-record
    observation. We do NOT use ``specify_cli.core.atomic.atomic_write`` here
    because that helper rotates the inode via ``os.replace``, which would
    detach the OS lock from the live file path and break mutual exclusion.
    """
    os.ftruncate(fd, 0)
    os.lseek(fd, 0, os.SEEK_SET)
    written = 0
    while written < len(payload):
        chunk = os.write(fd, payload[written:])
        if chunk <= 0:  # pragma: no cover - defensive
            raise OSError(errno.EIO, "short write while persisting lock record")
        written += chunk
    os.fsync(fd)


def _ensure_dir(path: Path) -> None:
    """Create the parent directory of ``path`` with restrictive perms on POSIX."""
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    if sys.platform != "win32":
        # On filesystems that do not honour POSIX modes we silently accept.
        with contextlib.suppress(OSError):
            os.chmod(parent, 0o700)


def _record_to_json(record: LockRecord) -> str:
    payload: dict[str, Any] = {
        "schema_version": record.schema_version,
        "pid": record.pid,
        "started_at": record.started_at.isoformat(),
        "host": record.host,
        "version": record.version,
    }
    return json.dumps(payload, sort_keys=True)


def _record_from_payload(payload: object) -> LockRecord | None:
    if not isinstance(payload, dict):
        return None
    try:
        schema_version = int(payload["schema_version"])
        pid = int(payload["pid"])
        started_raw = payload["started_at"]
        host = payload["host"]
        version = payload["version"]
    except (KeyError, TypeError, ValueError):
        return None
    if not isinstance(started_raw, str) or not isinstance(host, str) or not isinstance(version, str):
        return None
    try:
        started_at = datetime.fromisoformat(started_raw)
    except ValueError:
        return None
    if started_at.tzinfo is None:
        # Treat naive timestamps as UTC for backwards compatibility.
        started_at = started_at.replace(tzinfo=UTC)
    return LockRecord(
        schema_version=schema_version,
        pid=pid,
        started_at=started_at,
        host=host,
        version=version,
    )


def read_lock_record(path: Path) -> LockRecord | None:
    """Return the lock record at ``path`` without acquiring the OS lock.

    Returns ``None`` when:

    - the file does not exist;
    - the file is empty or contains malformed JSON;
    - the JSON is missing required keys or has wrong types.

    Used by ``auth doctor`` to surface whose process holds the lock without
    interfering with an in-flight transaction.
    """
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError:
        return None
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return _record_from_payload(payload)


def force_release(path: Path, *, only_if_age_s: float = STALE_AFTER_S_DEFAULT) -> bool:
    """Remove the lock file at ``path`` iff the record is older than ``only_if_age_s``.

    Returns ``True`` when the file was removed (it existed and was stuck);
    ``False`` when the file is missing, unreadable, or still considered fresh.

    A fresh lock cannot be ripped out from under a running process — the age
    check is performed before any filesystem mutation.
    """
    record = read_lock_record(path)
    if record is None:
        return False
    if record.age_s <= only_if_age_s:
        return False
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return False
    return True


class MachineFileLock:
    """Async context manager guarding a machine-wide advisory lock.

    Usage::

        async with MachineFileLock(path) as record:
            # protected critical section
            ...

    The acquire path opens ``path`` for write, takes a non-blocking OS-level
    exclusive lock, and writes a :class:`LockRecord` describing the current
    process directly to the locked FD (atomic for readers, see
    :func:`_atomic_write_under_lock`). On exit the OS lock is released
    unconditionally via ``try/finally`` and the file is truncated.

    Bounded-wait semantics: the acquire loop retries every
    ``_RETRY_SLEEP_S`` seconds for at most ``acquire_timeout_s`` seconds. If
    contention persists past the timeout :class:`LockAcquireTimeout` is raised.

    Stale-lock adoption: when the existing record is older than
    ``stale_after_s`` the helper deletes the file and retries the OS lock once
    to reclaim ownership. Concurrent adopters are tolerated — the loop simply
    re-enters bounded wait if the second attempt also contends.

    The protected block is the caller's responsibility; ``max_hold_s`` is
    advisory and callers SHOULD wrap the work in :func:`asyncio.wait_for` to
    enforce the NFR-002 10 s ceiling.
    """

    def __init__(
        self,
        path: Path,
        *,
        max_hold_s: float = _MAX_HOLD_DEFAULT,
        stale_after_s: float = STALE_AFTER_S_DEFAULT,
        acquire_timeout_s: float = _ACQUIRE_TIMEOUT_DEFAULT,
    ) -> None:
        self.path = path
        self.max_hold_s = max_hold_s
        self.stale_after_s = stale_after_s
        self.acquire_timeout_s = acquire_timeout_s
        self._fd: int | None = None
        self._record: LockRecord | None = None

    def _build_record(self) -> LockRecord:
        return LockRecord(
            schema_version=_SCHEMA_VERSION,
            pid=os.getpid(),
            started_at=datetime.now(UTC),
            host=socket.gethostname(),
            version=_get_package_version(),
        )

    def _open_fd(self) -> int:
        flags = os.O_RDWR | os.O_CREAT
        # ``0o600`` keeps the lock file readable only by the owner on POSIX.
        return os.open(str(self.path), flags, 0o600)

    async def __aenter__(self) -> LockRecord:
        _ensure_dir(self.path)
        deadline = asyncio.get_event_loop().time() + self.acquire_timeout_s
        adopted_once = False
        while True:
            fd = self._open_fd()
            try:
                _os_lock(fd)
            except OSError as exc:
                os.close(fd)
                if not _is_contention_error(exc):
                    raise
                # Contention path — consider staleness adoption then sleep.
                existing = read_lock_record(self.path)
                if (
                    not adopted_once
                    and existing is not None
                    and existing.age_s > self.stale_after_s
                ):
                    adopted_once = True
                    # Another process may have already adopted; fall through.
                    with contextlib.suppress(OSError):
                        self.path.unlink(missing_ok=True)
                    # Immediate retry of the OS lock without sleep.
                    continue
                if asyncio.get_event_loop().time() >= deadline:
                    raise LockAcquireTimeout(path=str(self.path)) from None
                await asyncio.sleep(_RETRY_SLEEP_S)
                continue

            # OS lock acquired — write content directly to the locked FD.
            record = self._build_record()
            try:
                _atomic_write_under_lock(fd, _record_to_json(record).encode("utf-8"))
            except BaseException:
                # Roll back the OS lock so we never leave it held without content.
                _os_unlock(fd)
                os.close(fd)
                raise
            self._fd = fd
            self._record = record
            return record

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        fd = self._fd
        if fd is None:
            return
        try:
            # Best-effort content cleanup. We TRUNCATE rather than unlink so
            # the on-disk inode survives and concurrent acquirers serialise
            # against our OS lock until ``flock(LOCK_UN)`` runs below. If we
            # unlinked, a contender's ``os.open(O_CREAT)`` would mint a fresh
            # inode and lock that instead — defeating mutual exclusion.
            with contextlib.suppress(OSError):
                os.ftruncate(fd, 0)
        finally:
            try:
                _os_unlock(fd)
            finally:
                with contextlib.suppress(OSError):
                    os.close(fd)
                self._fd = None
                self._record = None
