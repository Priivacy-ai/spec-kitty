"""Tests for UpgradeAttemptStore and default_history_db_path (WP02 T012).

Covers all query-interface contracts from contracts/history-store-query.md.
Uses SPEC_KITTY_HISTORY_DB_PATH for test isolation (no ~/.cache writes).
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from specify_cli.compat._detect.install_method import InstallMethod
from specify_cli.compat.history import (
    UpgradeAttemptOutcome,
    UpgradeAttemptRecord,
    UpgradeAttemptStore,
    default_history_db_path,
)

pytestmark = [pytest.mark.fast]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ULID_COUNTER = 0


def _make_ulid() -> str:
    """Generate a deterministic fake ULID (26 chars) for tests."""
    global _ULID_COUNTER
    _ULID_COUNTER += 1
    return f"01HTEST{str(_ULID_COUNTER).zfill(19)}"


def _make_record(
    *,
    attempt_id: str | None = None,
    install_method: InstallMethod = InstallMethod.UV_TOOL,
    outcome: UpgradeAttemptOutcome = UpgradeAttemptOutcome.SUCCESS,
    target_version: str | None = "3.2.0",
    timestamp: datetime | None = None,
    intent: str = "upgrade",
    exit_code: int | None = 0,
) -> UpgradeAttemptRecord:
    if attempt_id is None:
        attempt_id = _make_ulid()
    if timestamp is None:
        timestamp = datetime.now(tz=UTC)
    return UpgradeAttemptRecord(
        attempt_id=attempt_id,
        timestamp=timestamp,
        install_method=install_method,
        intent=intent,
        outcome=outcome,
        exit_code=exit_code,
        target_version=target_version,
    )


def _make_store(tmp_path: Path) -> UpgradeAttemptStore:
    """Create a store backed by a temp-path db."""
    db = tmp_path / "test-history.db"
    return UpgradeAttemptStore(db_path=db)


# ---------------------------------------------------------------------------
# default_history_db_path
# ---------------------------------------------------------------------------


class TestDefaultHistoryDbPath:
    def test_returns_path_instance(self) -> None:
        path = default_history_db_path()
        assert isinstance(path, Path)
        assert path.name == "upgrade-history.db"

    def test_env_var_override(self, tmp_path: Path, monkeypatch: Any) -> None:
        custom = str(tmp_path / "custom.db")
        monkeypatch.setenv("SPEC_KITTY_HISTORY_DB_PATH", custom)
        assert default_history_db_path() == Path(custom)

    def test_empty_env_var_falls_back_to_platformdirs(self, monkeypatch: Any) -> None:
        monkeypatch.delenv("SPEC_KITTY_HISTORY_DB_PATH", raising=False)
        path = default_history_db_path()
        assert path.name == "upgrade-history.db"


# ---------------------------------------------------------------------------
# UpgradeAttemptStore: append + last_success_timestamp
# ---------------------------------------------------------------------------


class TestAppendAndRead:
    def test_append_and_read_back(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        ts = datetime(2026, 6, 26, 12, 0, 0, tzinfo=UTC)
        record = _make_record(
            attempt_id="01HAPPENDSUCCESS0000000001",
            install_method=InstallMethod.UV_TOOL,
            outcome=UpgradeAttemptOutcome.SUCCESS,
            target_version="3.2.0",
            timestamp=ts,
        )
        store.append(record)
        result = store.last_success_timestamp(InstallMethod.UV_TOOL)
        assert result is not None
        assert result.year == 2026
        assert result.month == 6
        assert result.day == 26

    def test_last_success_returns_none_when_no_records(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        assert store.last_success_timestamp(InstallMethod.PIPX) is None

    def test_last_success_returns_none_for_different_install_method(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        store.append(_make_record(install_method=InstallMethod.UV_TOOL))
        assert store.last_success_timestamp(InstallMethod.PIPX) is None

    def test_last_success_returns_most_recent(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        ts_old = datetime(2026, 1, 1, tzinfo=UTC)
        ts_new = datetime(2026, 6, 26, tzinfo=UTC)
        store.append(_make_record(attempt_id="01HOLDRECORD000000000001", timestamp=ts_old))
        store.append(_make_record(attempt_id="01HNEWRECORD000000000001", timestamp=ts_new))
        result = store.last_success_timestamp(InstallMethod.UV_TOOL)
        assert result is not None
        assert result.year == 2026
        assert result.month == 6


# ---------------------------------------------------------------------------
# UpgradeAttemptStore: is_idempotent
# ---------------------------------------------------------------------------


class TestIsIdempotent:
    def test_false_before_any_record(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        record = _make_record(target_version="3.2.0")
        assert store.is_idempotent(record) is False

    def test_true_after_success_record(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        record = _make_record(
            attempt_id="01HIDEMPOTENT00000000001",
            target_version="3.2.0",
            outcome=UpgradeAttemptOutcome.SUCCESS,
        )
        store.append(record)
        assert store.is_idempotent(record) is True

    def test_false_after_failure_record(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        record = _make_record(
            attempt_id="01HFAILRECORD00000000001",
            target_version="3.2.0",
            outcome=UpgradeAttemptOutcome.FAILURE,
        )
        store.append(record)
        assert store.is_idempotent(record) is False

    def test_false_when_target_version_is_none(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        record = _make_record(target_version=None)
        # Even if we somehow had a prior success, cannot deduplicate unknown version.
        assert store.is_idempotent(record) is False

    def test_false_for_different_install_method(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        store.append(_make_record(
            attempt_id="01HUVTOOLSUCCESS00000001",
            install_method=InstallMethod.UV_TOOL,
            target_version="3.2.0",
        ))
        pipx_record = _make_record(
            install_method=InstallMethod.PIPX,
            target_version="3.2.0",
        )
        assert store.is_idempotent(pipx_record) is False

    def test_false_for_different_version(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        store.append(_make_record(
            attempt_id="01HVERSION320000000001",
            target_version="3.2.0",
        ))
        newer = _make_record(target_version="3.3.0")
        assert store.is_idempotent(newer) is False


# ---------------------------------------------------------------------------
# UpgradeAttemptStore: consecutive_failure_count
# ---------------------------------------------------------------------------


class TestConsecutiveFailureCount:
    def test_zero_with_no_records(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        assert store.consecutive_failure_count(InstallMethod.UV_TOOL) == 0

    def test_zero_with_only_successes(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        for i in range(3):
            store.append(_make_record(
                attempt_id=f"01HSUCC{str(i).zfill(20)}",
                outcome=UpgradeAttemptOutcome.SUCCESS,
            ))
        assert store.consecutive_failure_count(InstallMethod.UV_TOOL) == 0

    def test_three_consecutive_failures(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        for i in range(3):
            store.append(_make_record(
                attempt_id=f"01HFAIL{str(i).zfill(20)}",
                outcome=UpgradeAttemptOutcome.FAILURE,
                exit_code=1,
            ))
        assert store.consecutive_failure_count(InstallMethod.UV_TOOL) == 3

    def test_stops_counting_at_success(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        # Timestamps are relative to *now* so the rows always fall inside the
        # 300s recency window of consecutive_failure_count() — otherwise the
        # test silently starts returning 0 once wall-clock advances past any
        # fixed seed date (the window is now - window_seconds).
        now = datetime.now(UTC)
        # Insert: success (oldest), then 2 more-recent failures.
        store.append(_make_record(
            attempt_id="01HSUCC0000000000000001",
            outcome=UpgradeAttemptOutcome.SUCCESS,
            timestamp=now - timedelta(seconds=60),
        ))
        for i in range(2):
            store.append(_make_record(
                attempt_id=f"01HFAILAFTER{str(i).zfill(14)}",
                outcome=UpgradeAttemptOutcome.FAILURE,
                exit_code=1,
                timestamp=now - timedelta(seconds=40 - i * 10),
            ))
        assert store.consecutive_failure_count(InstallMethod.UV_TOOL) == 2

    def test_zero_for_different_install_method(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        store.append(_make_record(
            attempt_id="01HPIPXFAIL0000000001",
            install_method=InstallMethod.PIPX,
            outcome=UpgradeAttemptOutcome.FAILURE,
        ))
        # UV_TOOL method has no records.
        assert store.consecutive_failure_count(InstallMethod.UV_TOOL) == 0


# ---------------------------------------------------------------------------
# UpgradeAttemptStore: duplicate attempt_id (INSERT OR IGNORE)
# ---------------------------------------------------------------------------


class TestInsertOrIgnore:
    def test_duplicate_attempt_id_is_silent_noop(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        record = _make_record(attempt_id="01HDUPLICATERECORD000001")
        store.append(record)
        # Second insert with same attempt_id must not raise and must not double-count.
        store.append(record)
        # Only one success for this method.
        result = store.last_success_timestamp(InstallMethod.UV_TOOL)
        assert result is not None
        # consecutive_failure_count should still be 0 (no failures).
        assert store.consecutive_failure_count(InstallMethod.UV_TOOL) == 0


# ---------------------------------------------------------------------------
# UpgradeAttemptStore: retention trim
# ---------------------------------------------------------------------------


class TestRetentionTrim:
    def test_retention_trim_keeps_at_most_200(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        # Insert 205 records for UV_TOOL.
        for i in range(205):
            store.append(_make_record(
                attempt_id=f"01HRETENTION{str(i).zfill(15)}",
                timestamp=datetime(2026, 1, 1, 0, 0, i % 60, tzinfo=UTC),
            ))
        # Query: direct sqlite count to verify trim.
        import sqlite3

        conn = sqlite3.connect(str(tmp_path / "test-history.db"))
        (count,) = conn.execute(
            "SELECT COUNT(*) FROM upgrade_attempts WHERE install_method = ?",
            ("uv-tool",),
        ).fetchone()
        conn.close()
        assert count <= 200

    def test_retention_trim_does_not_affect_other_install_methods(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        # Insert 205 UV_TOOL records.
        for i in range(205):
            store.append(_make_record(
                attempt_id=f"01HUVASYMM{str(i).zfill(16)}",
                install_method=InstallMethod.UV_TOOL,
            ))
        # Insert 5 PIPX records.
        for j in range(5):
            store.append(_make_record(
                attempt_id=f"01HPIPXASYMM{str(j).zfill(14)}",
                install_method=InstallMethod.PIPX,
            ))
        import sqlite3

        conn = sqlite3.connect(str(tmp_path / "test-history.db"))
        (pipx_count,) = conn.execute(
            "SELECT COUNT(*) FROM upgrade_attempts WHERE install_method = ?",
            ("pipx",),
        ).fetchone()
        conn.close()
        assert pipx_count == 5


# ---------------------------------------------------------------------------
# UpgradeAttemptStore: SPEC_KITTY_HISTORY_DB_PATH env override
# ---------------------------------------------------------------------------


class TestEnvVarOverride:
    def test_store_uses_env_var_path(self, tmp_path: Path, monkeypatch: Any) -> None:
        custom_db = tmp_path / "env-override" / "history.db"
        monkeypatch.setenv("SPEC_KITTY_HISTORY_DB_PATH", str(custom_db))
        # A store created with db_path=None should use the env var path.
        store = UpgradeAttemptStore()
        store.append(_make_record(attempt_id="01HENVOVERRIDE000000001"))
        assert custom_db.exists()

    def test_store_with_explicit_path_ignores_env_var(self, tmp_path: Path, monkeypatch: Any) -> None:
        custom_db = tmp_path / "env-override" / "history.db"
        monkeypatch.setenv("SPEC_KITTY_HISTORY_DB_PATH", str(custom_db))
        explicit_db = tmp_path / "explicit.db"
        store = UpgradeAttemptStore(db_path=explicit_db)
        store.append(_make_record(attempt_id="01HEXPLICITDB00000001"))
        assert explicit_db.exists()
        # env-var path should NOT have been created.
        assert not custom_db.exists()


# ---------------------------------------------------------------------------
# UpgradeAttemptStore: fail-safe append on corrupt / unwritable path
# ---------------------------------------------------------------------------


class TestFailSafeAppend:
    def test_unwritable_dir_does_not_raise(self, tmp_path: Path) -> None:
        # Point the store at a path where parent is a file (not a dir).
        bad_parent = tmp_path / "some-file.txt"
        bad_parent.write_text("not a dir", encoding="utf-8")
        bad_db = bad_parent / "history.db"
        store = UpgradeAttemptStore(db_path=bad_db)
        # append() must swallow the OS error silently.
        store.append(_make_record(attempt_id="01HBADPATH000000000001"))
        # No exception raised — pass.


# ---------------------------------------------------------------------------
# UpgradeAttemptStore: concurrent writes (WAL mode)
# ---------------------------------------------------------------------------


class TestConcurrentWrites:
    def test_concurrent_appends_do_not_corrupt(self, tmp_path: Path) -> None:
        store = _make_store(tmp_path)
        errors: list[Exception] = []
        barrier = threading.Barrier(2)

        def _worker(worker_id: int) -> None:
            barrier.wait()
            try:
                for i in range(10):
                    store.append(_make_record(
                        attempt_id=f"01HCONC{str(worker_id).zfill(1)}{str(i).zfill(19)}",
                    ))
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        t1 = threading.Thread(target=_worker, args=(1,))
        t2 = threading.Thread(target=_worker, args=(2,))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert not errors, f"Concurrent writes raised: {errors}"

        # Verify we can still read without error.
        result = store.last_success_timestamp(InstallMethod.UV_TOOL)
        assert result is not None  # At least some records were written.

    def test_read_write_concurrent_no_corruption(self, tmp_path: Path) -> None:
        """Read and write simultaneously; both should succeed (WAL mode)."""
        store = _make_store(tmp_path)
        # Pre-populate.
        for i in range(5):
            store.append(_make_record(attempt_id=f"01HPREPOP{str(i).zfill(17)}"))

        results: list[Any] = []
        barrier = threading.Barrier(2)

        def _reader() -> None:
            barrier.wait()
            for _ in range(10):
                ts = store.last_success_timestamp(InstallMethod.UV_TOOL)
                results.append(ts)

        def _writer() -> None:
            barrier.wait()
            for i in range(10):
                store.append(_make_record(attempt_id=f"01HCONCWRITE{str(i).zfill(14)}"))

        t1 = threading.Thread(target=_reader)
        t2 = threading.Thread(target=_writer)
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)
        # No exceptions; results list has entries (even if some are None).
        assert len(results) == 10


# ---------------------------------------------------------------------------
# UpgradeAttemptStore: no fd leak on error path (regression for fix(1358))
# ---------------------------------------------------------------------------


class TestNoFdLeakOnErrorPath:
    """Regression test for fix(1358): connection closed on all error paths.

    Monkeypatches _connect() to return a mock connection whose execute()
    raises sqlite3.OperationalError (simulating a corrupt / locked DB).
    Asserts that close() is called exactly once on every code path, proving
    the fd-leak is gone regardless of the exception route taken.
    Fail-open/fail-safe contracts are also verified (no change to return values).
    """

    @staticmethod
    def _make_erroring_conn() -> MagicMock:
        """Return a mock connection that raises on execute() and does not suppress exceptions."""
        conn = MagicMock()
        conn.execute.side_effect = sqlite3.OperationalError("simulated DB error")
        # Ensure the transaction context-manager (__enter__/__exit__) never suppresses.
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        return conn

    def test_append_closes_conn_on_execute_error(self, tmp_path: Path, monkeypatch: Any) -> None:
        store = _make_store(tmp_path)
        mock_conn = self._make_erroring_conn()
        monkeypatch.setattr(store, "_connect", lambda: mock_conn)
        store.append(_make_record())  # fail-safe: must not raise
        mock_conn.close.assert_called_once()

    def test_is_idempotent_closes_conn_on_execute_error(self, tmp_path: Path, monkeypatch: Any) -> None:
        store = _make_store(tmp_path)
        mock_conn = self._make_erroring_conn()
        monkeypatch.setattr(store, "_connect", lambda: mock_conn)
        result = store.is_idempotent(_make_record(target_version="3.2.0"))
        assert result is False  # fail-open contract preserved
        mock_conn.close.assert_called_once()

    def test_consecutive_failure_count_closes_conn_on_execute_error(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        store = _make_store(tmp_path)
        mock_conn = self._make_erroring_conn()
        monkeypatch.setattr(store, "_connect", lambda: mock_conn)
        result = store.consecutive_failure_count(InstallMethod.UV_TOOL)
        assert result == 0  # fail-open contract preserved
        mock_conn.close.assert_called_once()

    def test_last_success_timestamp_closes_conn_on_execute_error(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        store = _make_store(tmp_path)
        mock_conn = self._make_erroring_conn()
        monkeypatch.setattr(store, "_connect", lambda: mock_conn)
        result = store.last_success_timestamp(InstallMethod.UV_TOOL)
        assert result is None  # fail-open contract preserved
        mock_conn.close.assert_called_once()

    def test_connect_closes_conn_when_schema_init_raises(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """A failure during PRAGMA/CREATE must close the fd before propagating.

        Otherwise the just-opened connection leaks (the caller's
        contextlib.closing only engages once _connect returns).
        """
        store = _make_store(tmp_path)
        mock_conn = self._make_erroring_conn()
        monkeypatch.setattr(sqlite3, "connect", lambda *a, **k: mock_conn)
        with pytest.raises(sqlite3.OperationalError):
            store._connect()  # noqa: SLF001
        mock_conn.close.assert_called_once()
