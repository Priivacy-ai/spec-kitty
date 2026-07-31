"""The T007 legacy-queue guard must not fail open (#3030 H8).

``_count_legacy_event_rows`` decides whether the daemon may start. Its safe
default is therefore **permission**, which makes it exactly the shape that already
burned this mission once (a guard whose own ``except Exception`` hid its arity
bug and reported "clean"). Two anchors are needed:

* A **real** legacy ``queue.db`` with known rows, so the count is measured against
  an actual object shape. A renamed field or a changed arity then fails loudly
  instead of silently degrading to the ``0`` default — which reads as "clean".
* "Could not determine" must be distinguishable from "genuinely zero", and must
  not be granted permission (FR-003's rule applied to this gate).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.fast

from specify_cli.sync.background import (
    BackgroundSyncService,
    LegacyQueueNotConvergedError,
    LegacyQueueUndeterminedError,
    _count_legacy_event_rows,
)

_LEGACY_QUEUE_DDL = """
CREATE TABLE IF NOT EXISTS queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    data TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    retry_count INTEGER DEFAULT 0,
    coalesce_key TEXT
)
"""


def _seed_legacy_queue(home: Path, rows: int) -> Path:
    """Write a real legacy ``~/.spec-kitty/queue.db`` holding *rows* event rows."""
    home.mkdir(parents=True, exist_ok=True)
    db = home / "queue.db"
    conn = sqlite3.connect(db)
    try:
        conn.execute(_LEGACY_QUEUE_DDL)
        for index in range(rows):
            conn.execute(
                "INSERT INTO queue (event_id, event_type, data, timestamp) "
                "VALUES (?, ?, ?, ?)",
                (f"legacy-{index}", "WPStatusChanged", "{}", 1750000000),
            )
        conn.commit()
    finally:
        conn.close()
    return db


class TestCounterIsAnchoredToARealQueue:
    """Measured against a real DB, so a shape change cannot read as "clean"."""

    def test_counts_the_rows_a_real_legacy_queue_actually_holds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        home = tmp_path / "spec-kitty-home"
        _seed_legacy_queue(home, rows=7)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(home))

        assert _count_legacy_event_rows() == 7, (
            "the guard must report the real row count, not a default"
        )

    def test_no_legacy_db_is_a_genuine_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        home = tmp_path / "empty-home"
        home.mkdir()
        monkeypatch.setenv("SPEC_KITTY_HOME", str(home))

        assert _count_legacy_event_rows() == 0

    def test_a_renamed_count_field_fails_loudly_instead_of_reporting_clean(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The exact regression the ``getattr(counts, "event_rows", 0)`` default hid.

        If the counts object ever loses/renames ``event_rows``, the guard used to
        report ``0`` — permission — for a queue that may hold thousands of
        undeliverable rows. It must raise instead.
        """
        home = tmp_path / "spec-kitty-home"
        _seed_legacy_queue(home, rows=3)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(home))

        class _RenamedCounts:
            queue_event_rows = 3  # the field used to be called event_rows

        with (
            patch(
                "specify_cli.sync.queue.detect_legacy_rows_for_scope",
                return_value=_RenamedCounts(),
            ),
            pytest.raises(AttributeError),
        ):
            _count_legacy_event_rows()

    def test_a_changed_arity_fails_loudly_instead_of_reporting_clean(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        home = tmp_path / "spec-kitty-home"
        _seed_legacy_queue(home, rows=3)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(home))

        def _new_signature(scope, *, include_bodies):  # noqa: ANN001, ANN202
            raise AssertionError("unreachable: called with the old arity")

        with (
            patch(
                "specify_cli.sync.queue.detect_legacy_rows_for_scope",
                _new_signature,
            ),
            pytest.raises(TypeError),
        ):
            _count_legacy_event_rows()


class TestUndeterminedIsNotPermission:
    """An unreadable legacy DB is "unknown", and unknown is not "clean"."""

    def test_unreadable_legacy_db_reports_undetermined_not_zero(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        home = tmp_path / "spec-kitty-home"
        _seed_legacy_queue(home, rows=2)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(home))

        with patch(
            "specify_cli.sync.queue.detect_legacy_rows_for_scope",
            side_effect=sqlite3.DatabaseError("file is not a database"),
        ):
            assert _count_legacy_event_rows() is None, (
                "a corrupt/unreadable legacy DB must be reported as undetermined, "
                "which is a different answer from 'zero rows'"
            )

    def test_undetermined_refuses_to_start_the_daemon(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = BackgroundSyncService(queue=_FakeQueue(), config=None)
        monkeypatch.setattr(
            "specify_cli.sync.background._count_legacy_event_rows", lambda: None
        )

        with pytest.raises(LegacyQueueUndeterminedError) as excinfo:
            service._assert_legacy_queue_converged()

        message = str(excinfo.value)
        assert "queue.db" in message, "the message must name the file to act on"
        assert isinstance(excinfo.value, LegacyQueueNotConvergedError), (
            "callers already handling the converged error must keep working"
        )

    def test_genuine_zero_starts_normally(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = BackgroundSyncService(queue=_FakeQueue(), config=None)
        monkeypatch.setattr(
            "specify_cli.sync.background._count_legacy_event_rows", lambda: 0
        )

        service._assert_legacy_queue_converged()  # must not raise

    def test_stranded_rows_still_refuse(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        service = BackgroundSyncService(queue=_FakeQueue(), config=None)
        monkeypatch.setattr(
            "specify_cli.sync.background._count_legacy_event_rows", lambda: 12
        )

        with pytest.raises(LegacyQueueNotConvergedError) as excinfo:
            service._assert_legacy_queue_converged()
        assert "12" in str(excinfo.value)
        assert "sync migrate" in str(excinfo.value)


class _FakeQueue:
    """Minimal stand-in; these tests never touch the queue itself."""

    def size(self) -> int:
        return 0


class TestARefusedStartLeavesNoDeadSingleton:
    """The guard raises from ``start()``, which the singletons call unguarded.

    ``get_sync_service`` assigned ``_service`` and ``get_runtime`` assigned
    ``_runtime`` **before** ``start()`` ran. When the guard fired, the module was
    left holding a constructed-but-never-started singleton (and, for the service,
    no ``atexit`` stop hook): every later call handed back the dead object and
    silently never retried, so sync stayed dead for the life of the process even
    after the operator ran ``sync migrate``.
    """

    def test_get_sync_service_does_not_cache_a_service_that_failed_to_start(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import specify_cli.sync.background as bg

        monkeypatch.setattr(bg, "_service", None)
        monkeypatch.setattr(bg, "is_saas_sync_enabled", lambda: True)
        monkeypatch.setattr(bg, "_count_legacy_event_rows", lambda: 5)
        monkeypatch.setattr(bg, "OfflineQueue", _FakeQueue)
        monkeypatch.setattr(bg, "SyncConfig", lambda: None)

        with pytest.raises(LegacyQueueNotConvergedError):
            bg.get_sync_service()

        assert bg._service is None, (
            "a service that refused to start must not be cached; the next call "
            "has to retry once the operator has migrated"
        )

        # After the remedy, the very next call must actually start.
        monkeypatch.setattr(bg, "_count_legacy_event_rows", lambda: 0)
        service = bg.get_sync_service()
        try:
            assert service.is_running is True
        finally:
            service.stop()
            bg._service = None

    def test_get_runtime_does_not_cache_a_runtime_that_failed_to_start(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import specify_cli.sync.runtime as rt

        monkeypatch.setattr(rt, "_runtime", None)
        monkeypatch.setattr(rt, "is_saas_sync_enabled", lambda: True)
        monkeypatch.setattr(rt, "_auto_start_enabled", lambda: True)
        monkeypatch.setattr(
            rt.SyncRuntime,
            "start",
            lambda self: (_ for _ in ()).throw(LegacyQueueNotConvergedError("nope")),
        )

        with pytest.raises(LegacyQueueNotConvergedError):
            rt.get_runtime()

        assert rt._runtime is None, (
            "an unstarted runtime must not be cached, or every later call gets a "
            "dead runtime that never retries start()"
        )
