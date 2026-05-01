"""Tests for ``specify_cli.core.file_lock`` — covering the 7 cases in
``contracts/refresh-lock.md`` §"Test contract".

The suite uses ``asyncio`` (pytest-asyncio with ``asyncio_mode = auto``) and
relies on a temporary lock path per test so cases are isolated from each
other and from any production lock file under ``~/.spec-kitty``.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from specify_cli.core import file_lock as fl
from specify_cli.core.file_lock import (
    LockAcquireTimeout,
    LockRecord,
    MachineFileLock,
    force_release,
    read_lock_record,
)


@pytest.fixture()
def lock_path(tmp_path: Path) -> Path:
    return tmp_path / "subdir" / "refresh.lock"


def _write_record(path: Path, *, age_s: float = 0.0, pid: int | None = None) -> None:
    """Write a synthetic lock record to ``path`` with ``age_s`` seconds in the past."""
    started = datetime.now(UTC) - timedelta(seconds=age_s)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "pid": pid if pid is not None else os.getpid(),
        "started_at": started.isoformat(),
        "host": "test-host",
        "version": "test",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True))


# ---------------------------------------------------------------------------
# 1. test_acquire_and_release
# ---------------------------------------------------------------------------


async def test_acquire_and_release(lock_path: Path) -> None:
    async with MachineFileLock(lock_path, acquire_timeout_s=2.0) as record:
        assert isinstance(record, LockRecord)
        assert record.pid == os.getpid()
        assert record.schema_version == 1
        on_disk = read_lock_record(lock_path)
        assert on_disk is not None
        assert on_disk.pid == os.getpid()

    # After the context exits the lock file is removed and the record gone.
    assert read_lock_record(lock_path) is None


# ---------------------------------------------------------------------------
# 2. test_concurrent_acquire_serialized
# ---------------------------------------------------------------------------


async def test_concurrent_acquire_serialized(lock_path: Path) -> None:
    sequence: list[str] = []

    async def hold(label: str, dwell_s: float) -> None:
        async with MachineFileLock(lock_path, acquire_timeout_s=5.0):
            sequence.append(f"enter-{label}")
            await asyncio.sleep(dwell_s)
            sequence.append(f"exit-{label}")

    a = asyncio.create_task(hold("a", 0.2))
    # Give task A time to win the race.
    await asyncio.sleep(0.05)
    b = asyncio.create_task(hold("b", 0.05))
    await asyncio.gather(a, b)

    # Critical sections never overlap.
    assert sequence == ["enter-a", "exit-a", "enter-b", "exit-b"]


# ---------------------------------------------------------------------------
# 3. test_acquire_timeout_raises
# ---------------------------------------------------------------------------


async def test_acquire_timeout_raises(lock_path: Path) -> None:
    holder = MachineFileLock(lock_path, acquire_timeout_s=2.0)
    await holder.__aenter__()
    try:
        contender = MachineFileLock(lock_path, acquire_timeout_s=0.3)
        with pytest.raises(LockAcquireTimeout) as info:
            await contender.__aenter__()
        assert str(lock_path) in info.value.path
    finally:
        await holder.__aexit__(None, None, None)


# ---------------------------------------------------------------------------
# 4. test_stale_lock_adopted
# ---------------------------------------------------------------------------


async def test_stale_lock_adopted(lock_path: Path) -> None:
    # Pre-seed a 120-second-old record from a different PID.
    _write_record(lock_path, age_s=120.0, pid=999_999)
    assert read_lock_record(lock_path) is not None

    async with MachineFileLock(lock_path, acquire_timeout_s=1.0, stale_after_s=60.0) as record:
        # The new acquirer adopted the lock and rewrote the record.
        assert record.pid == os.getpid()
        on_disk = read_lock_record(lock_path)
        assert on_disk is not None
        assert on_disk.pid == os.getpid()


# ---------------------------------------------------------------------------
# 5. test_force_release_only_when_stuck
# ---------------------------------------------------------------------------


def test_force_release_missing_returns_false(lock_path: Path) -> None:
    assert force_release(lock_path, only_if_age_s=60.0) is False


def test_force_release_only_when_stuck(lock_path: Path) -> None:
    _write_record(lock_path, age_s=5.0)
    assert force_release(lock_path, only_if_age_s=60.0) is False
    assert lock_path.exists()  # fresh — must not be removed

    _write_record(lock_path, age_s=120.0)
    assert force_release(lock_path, only_if_age_s=60.0) is True
    assert not lock_path.exists()


# ---------------------------------------------------------------------------
# 6. test_atomic_content_write — patch atomic_write to fail mid-write
# ---------------------------------------------------------------------------


async def test_atomic_content_write_failure_leaves_no_partial(lock_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _exploding_write(fd: int, payload: bytes) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(fl, "_atomic_write_under_lock", _exploding_write)

    with pytest.raises(OSError, match="disk full"):
        async with MachineFileLock(lock_path, acquire_timeout_s=1.0):
            pytest.fail("body should not run when content write fails")  # pragma: no cover

    # Reader sees no record because the OS lock was released and content never
    # made it to disk.
    assert read_lock_record(lock_path) is None

    # And the lock is now reclaimable by a subsequent acquirer.
    monkeypatch.undo()
    async with MachineFileLock(lock_path, acquire_timeout_s=1.0) as record:
        assert record.pid == os.getpid()


# ---------------------------------------------------------------------------
# 7. test_platform_dispatch
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only path uses fcntl")
def test_platform_dispatch_posix() -> None:
    import fcntl  # noqa: F401  - presence assertion

    assert hasattr(fcntl, "flock")
    assert hasattr(fcntl, "LOCK_EX")
    assert hasattr(fcntl, "LOCK_NB")
    assert hasattr(fcntl, "LOCK_UN")


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only path uses msvcrt")
def test_platform_dispatch_windows(tmp_path: Path) -> None:  # pragma: no cover - exercised on win32 CI only
    import msvcrt  # type: ignore[import-not-found]

    assert hasattr(msvcrt, "locking")
    # Smoke-test acquire/release through the public API on Windows runners.
    path = tmp_path / "win.lock"

    async def _smoke() -> None:
        async with MachineFileLock(path, acquire_timeout_s=2.0) as record:
            assert record.pid == os.getpid()

    asyncio.run(_smoke())


# ---------------------------------------------------------------------------
# Additional coverage: read_lock_record corruption + LockRecord helpers
# ---------------------------------------------------------------------------


def test_read_lock_record_rejects_corrupt_json(lock_path: Path) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("not-json{")
    assert read_lock_record(lock_path) is None


def test_read_lock_record_rejects_missing_keys(lock_path: Path) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps({"schema_version": 1, "pid": 1}))
    assert read_lock_record(lock_path) is None


def test_read_lock_record_rejects_bad_started_at(lock_path: Path) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pid": 42,
                "started_at": "not-a-timestamp",
                "host": "h",
                "version": "v",
            }
        )
    )
    assert read_lock_record(lock_path) is None


def test_lock_record_age_and_is_stuck() -> None:
    fresh = LockRecord(
        schema_version=1,
        pid=1,
        started_at=datetime.now(UTC),
        host="h",
        version="v",
    )
    assert fresh.age_s < 5.0
    assert fresh.is_stuck(60.0) is False

    stale = LockRecord(
        schema_version=1,
        pid=1,
        started_at=datetime.now(UTC) - timedelta(seconds=120),
        host="h",
        version="v",
    )
    assert stale.age_s > 60.0
    assert stale.is_stuck(60.0) is True


def test_read_lock_record_non_dict_returns_none(lock_path: Path) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps([1, 2, 3]))
    assert read_lock_record(lock_path) is None


def test_read_lock_record_non_string_fields_returns_none(lock_path: Path) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pid": 1,
                "started_at": datetime.now(UTC).isoformat(),
                "host": 12345,  # wrong type
                "version": "v",
            }
        )
    )
    assert read_lock_record(lock_path) is None


def test_force_release_unlink_failure(lock_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_record(lock_path, age_s=120.0)

    def _boom(self: Path, *args: Any, **kwargs: Any) -> None:
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "unlink", _boom)
    assert force_release(lock_path, only_if_age_s=60.0) is False


def test_is_contention_error_distinguishes_genuine_io() -> None:
    # Non-contention OSError (errno=None) propagates rather than being eaten.
    assert fl._is_contention_error(OSError()) is False
    # ENOSPC is a genuine I/O error, never contention.
    err = OSError()
    err.errno = 28  # ENOSPC
    assert fl._is_contention_error(err) is False
    # EACCES is contention on both POSIX and Windows.
    err.errno = 13  # EACCES
    assert fl._is_contention_error(err) is True


async def test_aexit_is_idempotent_when_no_fd_held(lock_path: Path) -> None:
    # Calling __aexit__ before __aenter__ must be a no-op (defensive guard).
    lock = MachineFileLock(lock_path)
    await lock.__aexit__(None, None, None)


async def test_acquire_propagates_non_contention_oserror(lock_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(fd: int) -> None:
        # Simulate a non-contention OSError (e.g. ENOSPC).
        err = OSError("disk full")
        err.errno = 28  # ENOSPC
        raise err

    monkeypatch.setattr(fl, "_os_lock", _boom)
    with pytest.raises(OSError, match="disk full"):
        async with MachineFileLock(lock_path, acquire_timeout_s=0.5):
            pytest.fail("body should not run")  # pragma: no cover


def test_get_package_version_falls_back_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _missing(_name: str) -> str:
        raise fl.importlib_metadata.PackageNotFoundError("spec-kitty-cli")

    monkeypatch.setattr(fl.importlib_metadata, "version", _missing)
    assert fl._get_package_version() == "unknown"


def test_read_lock_record_handles_oserror(lock_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps({"schema_version": 1, "pid": 1, "started_at": "x", "host": "h", "version": "v"}))

    def _boom(self: Path) -> bytes:
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "read_bytes", _boom)
    assert read_lock_record(lock_path) is None


def test_read_lock_record_accepts_naive_timestamp(lock_path: Path) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    naive = datetime.now(UTC).replace(tzinfo=None)
    lock_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pid": 1,
                "started_at": naive.isoformat(),
                "host": "h",
                "version": "v",
            }
        )
    )
    record = read_lock_record(lock_path)
    assert record is not None
    assert record.started_at.tzinfo is not None  # coerced to UTC
