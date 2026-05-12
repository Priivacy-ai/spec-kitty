"""Cached row-count invariants for OfflineQueue (Mission 6 / issue #352).

These tests lock in the contract that ``OfflineQueue._row_count`` (the
in-process cap-check cache) stays coherent with the on-disk row count across
every mutation path, so ``queue_event()`` and ``append()`` can avoid the
per-event ``SELECT COUNT(*) FROM queue`` table scan.

The intent here is *not* to re-test the queue behavior covered in
``test_offline_queue.py`` — those still pass. This file focuses on the
counter invariants themselves.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.fast

from specify_cli.sync.queue import (
    DEFAULT_STRICT_CAP_SIZE,
    OfflineQueue,
    OfflineQueueFull,
)


@pytest.fixture
def temp_queue() -> Iterator[OfflineQueue]:
    """Create a queue with a temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "counter_queue.db"
        yield OfflineQueue(db_path)


@dataclass
class _FakeBatchResult:
    """Minimal stand-in for BatchEventResult used by ``process_batch_results``."""

    status: str
    event_id: str


def _evt(eid: str, etype: str = "Test", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"event_id": eid, "event_type": etype, "payload": payload or {}}


def _dossier_evt(
    eid: str, project_uuid: str, mission_slug: str, artifact_key: str
) -> dict[str, Any]:
    """Build a coalesceable event matching ``MissionDossierArtifactIndexed``."""
    return {
        "event_id": eid,
        "event_type": "MissionDossierArtifactIndexed",
        "project_uuid": project_uuid,
        "payload": {
            "project_uuid": project_uuid,
            "mission_slug": mission_slug,
            "artifact_key": artifact_key,
        },
    }


class TestRowCountCache:
    def test_counter_initializes_lazily(self, temp_queue: OfflineQueue) -> None:
        # Fresh queue: cache is uninitialized.
        assert temp_queue._row_count is None
        # First size() call loads from disk.
        assert temp_queue.size() == 0
        assert temp_queue._row_count == 0

    def test_counter_increments_on_insert(self, temp_queue: OfflineQueue) -> None:
        for i in range(5):
            assert temp_queue.queue_event(_evt(f"evt-{i}")) is True
        assert temp_queue._row_count == 5
        assert temp_queue._size_from_disk() == 5

    def test_counter_unchanged_on_coalesce(self, temp_queue: OfflineQueue) -> None:
        # Two events with the same coalesce key collapse into one row.
        a = _dossier_evt("a-1", "proj-1", "miss-1", "spec.md")
        b = _dossier_evt("b-1", "proj-1", "miss-1", "spec.md")
        assert temp_queue.queue_event(a) is True
        assert temp_queue._row_count == 1
        assert temp_queue.queue_event(b) is True
        # Coalesce path returned True without growing the queue.
        assert temp_queue._row_count == 1
        assert temp_queue._size_from_disk() == 1

    def test_counter_unchanged_on_duplicate_event_id(self, temp_queue: OfflineQueue) -> None:
        # INSERT OR IGNORE + conditional UPDATE preserves the row count when
        # the same event_id is inserted twice (matches the legacy
        # ``INSERT OR REPLACE`` semantics).
        assert temp_queue.queue_event(_evt("evt-1", payload={"v": 1})) is True
        assert temp_queue._row_count == 1
        assert temp_queue.queue_event(_evt("evt-1", payload={"v": 2})) is True
        assert temp_queue._row_count == 1
        # Disk also reports 1 row, with the latest payload.
        assert temp_queue._size_from_disk() == 1
        events = temp_queue.drain_queue(limit=10)
        assert len(events) == 1
        assert events[0]["payload"]["v"] == 2

    def test_counter_after_eviction_equals_cap(self, tmp_path: Path) -> None:
        cap = 8
        q = OfflineQueue(tmp_path / "cap.db", max_queue_size=cap)
        for i in range(cap):
            assert q.queue_event(_evt(f"e-{i}")) is True
        assert q._row_count == cap
        # One more triggers FIFO eviction; size stays at cap.
        assert q.queue_event(_evt("overflow")) is True
        assert q._row_count == cap
        assert q._size_from_disk() == cap

    def test_strict_append_raises_full(self, tmp_path: Path) -> None:
        cap = 4
        q = OfflineQueue(tmp_path / "strict.db", max_queue_size=1000)
        for i in range(cap):
            q.append(_evt(f"s-{i}"), cap=cap)
        assert q._row_count == cap
        with pytest.raises(OfflineQueueFull):
            q.append(_evt("over"), cap=cap)
        # The failed append must not mutate the counter.
        assert q._row_count == cap

    def test_strict_append_default_cap_constant(self, tmp_path: Path) -> None:
        # Belt-and-braces: ensure the documented default strict cap is still
        # the one referenced by ``append()``. This catches accidental drift
        # of the cap constant during refactors.
        q = OfflineQueue(tmp_path / "strict_default.db", max_queue_size=1_000_000)
        q.append(_evt("only-one"))
        assert q._row_count == 1
        # The constant is exported for callers.
        assert DEFAULT_STRICT_CAP_SIZE >= 1

    def test_counter_after_mark_synced(self, temp_queue: OfflineQueue) -> None:
        for i in range(5):
            temp_queue.queue_event(_evt(f"m-{i}"))
        assert temp_queue._row_count == 5
        temp_queue.mark_synced(["m-1", "m-3"])
        assert temp_queue._row_count == 3
        assert temp_queue._size_from_disk() == 3

    def test_counter_unchanged_when_mark_synced_misses(
        self, temp_queue: OfflineQueue
    ) -> None:
        # Marking unknown IDs as synced must not double-decrement.
        for i in range(3):
            temp_queue.queue_event(_evt(f"k-{i}"))
        temp_queue.mark_synced(["does-not-exist"])
        assert temp_queue._row_count == 3
        assert temp_queue._size_from_disk() == 3

    def test_counter_after_clear(self, temp_queue: OfflineQueue) -> None:
        for i in range(7):
            temp_queue.queue_event(_evt(f"c-{i}"))
        assert temp_queue._row_count == 7
        temp_queue.clear()
        assert temp_queue._row_count == 0
        assert temp_queue._size_from_disk() == 0

    def test_counter_after_remove_project_events(
        self, temp_queue: OfflineQueue
    ) -> None:
        # Two projects, two events each.
        for i in range(2):
            temp_queue.queue_event(
                {
                    "event_id": f"a-{i}",
                    "event_type": "BuildRegistered",
                    "project_uuid": "proj-a",
                    "payload": {"project_uuid": "proj-a"},
                }
            )
            temp_queue.queue_event(
                {
                    "event_id": f"b-{i}",
                    "event_type": "BuildRegistered",
                    "project_uuid": "proj-b",
                    "payload": {"project_uuid": "proj-b"},
                }
            )
        assert temp_queue._row_count == 4
        removed = temp_queue.remove_project_events("proj-a")
        assert removed == 2
        assert temp_queue._row_count == 2
        assert temp_queue._size_from_disk() == 2

    def test_counter_after_process_batch_results(
        self, temp_queue: OfflineQueue
    ) -> None:
        for i in range(6):
            temp_queue.queue_event(_evt(f"b-{i}"))
        assert temp_queue._row_count == 6

        results = [
            _FakeBatchResult(status="success", event_id="b-0"),
            _FakeBatchResult(status="duplicate", event_id="b-1"),
            _FakeBatchResult(status="failed_permanent", event_id="b-2"),
            _FakeBatchResult(status="rejected", event_id="b-3"),
            _FakeBatchResult(status="rejected", event_id="b-4"),
            # Unknown status -> ignored by process_batch_results.
            _FakeBatchResult(status="failed_transient", event_id="b-5"),
        ]
        temp_queue.process_batch_results(results)
        # 3 rows deleted (success/duplicate/failed_permanent), 2 rejected
        # rows bump retry_count but stay in queue, failed_transient is a
        # no-op.
        assert temp_queue._row_count == 3
        assert temp_queue._size_from_disk() == 3

    def test_counter_after_drain_to_file(
        self, temp_queue: OfflineQueue, tmp_path: Path
    ) -> None:
        for i in range(4):
            temp_queue.queue_event(_evt(f"d-{i}"))
        assert temp_queue._row_count == 4
        out = tmp_path / "overflow.jsonl"
        count = temp_queue.drain_to_file(out)
        assert count == 4
        # drain_to_file calls clear(); counter must zero.
        assert temp_queue._row_count == 0
        assert temp_queue._size_from_disk() == 0
        assert out.exists()

    def test_counter_loads_from_existing_db(
        self, persistent_db_path: Path
    ) -> None:
        # Populate the DB with one instance, then open a new one — the
        # second instance MUST see the correct size on first read.
        q1 = OfflineQueue(persistent_db_path)
        for i in range(3):
            q1.queue_event(_evt(f"l-{i}"))
        assert q1._row_count == 3
        del q1
        q2 = OfflineQueue(persistent_db_path)
        # Cache is None until first read.
        assert q2._row_count is None
        assert q2.size() == 3
        assert q2._row_count == 3

    def test_size_reflects_external_mutations(
        self, persistent_db_path: Path
    ) -> None:
        # Two ``OfflineQueue`` instances pointing at the same DB. ``size()``
        # MUST re-read from disk so external mutations are visible.
        q1 = OfflineQueue(persistent_db_path)
        q2 = OfflineQueue(persistent_db_path)
        q1.queue_event(_evt("x-1"))
        q1.queue_event(_evt("x-2"))
        # q2 has not been touched yet — its cache is uninitialized.
        # size() refreshes from disk and observes the two rows.
        assert q2.size() == 2
        # q1 removes one event.
        q1.mark_synced(["x-1"])
        # q2 must observe the new count on next size() call.
        assert q2.size() == 1

    def test_invariant_size_equals_disk_after_mixed_operations(
        self, temp_queue: OfflineQueue
    ) -> None:
        # Interleave inserts, coalesces, deletes, clear; after each step
        # the cached counter must agree with disk.
        def assert_invariant() -> None:
            assert temp_queue.size() == temp_queue._size_from_disk()

        for i in range(4):
            temp_queue.queue_event(_evt(f"x-{i}"))
            assert_invariant()

        # Coalesce-eligible insert.
        a = _dossier_evt("d-1", "proj", "miss", "spec.md")
        b = _dossier_evt("d-2", "proj", "miss", "spec.md")
        temp_queue.queue_event(a)
        assert_invariant()
        temp_queue.queue_event(b)
        assert_invariant()

        # Duplicate event_id.
        temp_queue.queue_event(_evt("x-0", payload={"v": "new"}))
        assert_invariant()

        # Selective sync.
        temp_queue.mark_synced(["x-1", "x-2"])
        assert_invariant()

        # Clear.
        temp_queue.clear()
        assert_invariant()


@pytest.fixture
def persistent_db_path() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "counter_persistent.db"


class TestMultiInstanceCapEnforcement:
    """PR #1029 review fix: the cached row count is a per-instance value, but
    two ``OfflineQueue`` instances can target the same SQLite file. When a
    sibling instance inserts behind our back, the cache underestimates the
    persisted depth — the cap-check on the hot path must reconcile against
    disk before deciding to evict or refuse, otherwise the persisted queue
    can grow past ``max_queue_size``.

    Reviewer's repro: two instances, ``max_queue_size=2``, drove the queue
    to a persisted depth of 3. After the fix the persisted depth stays
    bounded by the cap.
    """

    def test_queue_event_cap_holds_across_two_instances(
        self, persistent_db_path: Path
    ) -> None:
        cap = 2
        q1 = OfflineQueue(persistent_db_path, max_queue_size=cap)
        q2 = OfflineQueue(persistent_db_path, max_queue_size=cap)

        # q1 fills to cap-1; q2's cache is still uninitialized.
        assert q1.queue_event(_evt("a-1")) is True
        assert q1._row_count == 1
        assert q2._row_count is None

        # q2 inserts one event. Its cache lazy-loads and sees 1, so the
        # naive cached path would happily accept a second insert without
        # reconciling — that is the bug.
        assert q2.queue_event(_evt("b-1")) is True
        # Persisted depth must equal the cap; the cache reconciles when
        # ``current_size + 1 > cap``.
        assert q1._size_from_disk() == cap

        # Force one more insert through each instance; persisted depth
        # must still be bounded by the cap (FIFO eviction kicks in).
        assert q1.queue_event(_evt("a-2")) is True
        assert q1._size_from_disk() == cap
        assert q2.queue_event(_evt("b-2")) is True
        assert q2._size_from_disk() == cap

    def test_queue_event_cap_holds_when_sibling_fills_to_cap_minus_one(
        self, persistent_db_path: Path
    ) -> None:
        # Exact scenario from the reviewer: persisted queue size grew to 3
        # under ``max_queue_size=2`` because the cached counter on the
        # second instance pointed at the same DB never reconciled.
        cap = 2
        q1 = OfflineQueue(persistent_db_path, max_queue_size=cap)
        q2 = OfflineQueue(persistent_db_path, max_queue_size=cap)

        # Fill to cap-1 via q1.
        assert q1.queue_event(_evt("a-1")) is True

        # q2 inserts one event. Without the fix, q2's lazy-load saw 0 and
        # the cap check would have happily accepted three rows. With the
        # fix, q2's cap check reconciles against disk when the projected
        # post-insert depth would breach the cap.
        assert q2.queue_event(_evt("b-1")) is True

        # Another insert via q2 must trigger eviction, not unbounded growth.
        assert q2.queue_event(_evt("b-2")) is True

        # The reviewer's symptom: persisted depth > cap. The fix bounds it.
        assert q1._size_from_disk() <= cap
        assert q2._size_from_disk() <= cap

    def test_strict_append_cap_holds_across_two_instances(
        self, persistent_db_path: Path
    ) -> None:
        # Same multi-instance hazard for the strict-cap append surface:
        # the second instance must reconcile when about to cross the cap,
        # so it raises ``OfflineQueueFull`` instead of silently exceeding.
        cap = 2
        q1 = OfflineQueue(persistent_db_path, max_queue_size=10_000)
        q2 = OfflineQueue(persistent_db_path, max_queue_size=10_000)

        q1.append(_evt("a-1"), cap=cap)
        q1.append(_evt("a-2"), cap=cap)
        # q1's cache reports cap; q2's cache is uninitialized.
        assert q1._row_count == cap
        assert q2._row_count is None

        # q2 must observe the persisted depth and raise.
        with pytest.raises(OfflineQueueFull):
            q2.append(_evt("b-1"), cap=cap)

        # Persisted depth still at cap, not above.
        assert q2._size_from_disk() == cap


class TestNoCountScansOnHotPath:
    """White-box guarantee: ``queue_event`` and ``append`` never *execute*
    ``SELECT COUNT(*) FROM queue`` on the steady-state non-coalesced path.

    We assert this by patching ``sqlite3.connect`` and intercepting every
    SQL string executed through the resulting connection, then driving the
    hot path with a steady-state insert (cache primed, no eviction, no
    coalescing). The legacy implementation issued one count scan per call,
    so any regression that re-introduces it surfaces here.
    """

    def _record_executes(
        self,
        temp_queue: OfflineQueue,
        monkeypatch: pytest.MonkeyPatch,
    ) -> list[str]:
        import sqlite3 as _sqlite

        recorded: list[str] = []
        real_connect = _sqlite.connect

        class _RecordingConnection:
            """Thin proxy around a real sqlite3 connection that records every
            SQL string executed through ``.execute(...)``."""

            def __init__(self, conn: _sqlite.Connection) -> None:
                self._conn = conn

            def execute(self, sql: str, *e_args: Any, **e_kwargs: Any) -> Any:
                recorded.append(sql)
                return self._conn.execute(sql, *e_args, **e_kwargs)

            def commit(self) -> None:
                self._conn.commit()

            def close(self) -> None:
                self._conn.close()

            def rollback(self) -> None:
                self._conn.rollback()

            def __getattr__(self, name: str) -> Any:  # pragma: no cover - passthrough
                return getattr(self._conn, name)

        def patched_connect(*args: Any, **kwargs: Any) -> _RecordingConnection:
            return _RecordingConnection(real_connect(*args, **kwargs))

        monkeypatch.setattr("specify_cli.sync.queue.sqlite3.connect", patched_connect)
        return recorded

    def test_queue_event_steady_state_has_no_count_scan(
        self, temp_queue: OfflineQueue, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Prime the cache so ``_ensure_row_count`` is a no-op disk read.
        temp_queue.queue_event(_evt("warm"))
        recorded = self._record_executes(temp_queue, monkeypatch)
        # One steady-state insert.
        assert temp_queue.queue_event(_evt("hot")) is True
        # No ``SELECT COUNT(*) FROM queue`` should appear.
        for sql in recorded:
            assert "SELECT COUNT(*) FROM queue" not in sql, sql

    def test_append_steady_state_has_no_count_scan(
        self, temp_queue: OfflineQueue, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Prime the cache via a normal queue_event.
        temp_queue.queue_event(_evt("warm"))
        recorded = self._record_executes(temp_queue, monkeypatch)
        temp_queue.append(_evt("strict-hot"))
        for sql in recorded:
            assert "SELECT COUNT(*) FROM queue" not in sql, sql
