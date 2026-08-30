"""Project-owned row-count and cap invariants for ``OfflineQueue``.

The retired queue cached a count beside a free-standing SQLite path.  The
canonical outbox deliberately owns neither: every count is read inside the
project store's outer unit of work.  These historical node names remain stable
while their assertions exercise the replacement invariants.
"""

from __future__ import annotations

import inspect
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from specify_cli.sync.project_store import ProjectSyncStore, ProjectUnitOfWork
from specify_cli.sync.queue import DEFAULT_STRICT_CAP_SIZE, OfflineQueue, OfflineQueueFull

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT = "aaaaaaaa-0000-0000-0000-000000000001"


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectSyncStore:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    value = ProjectSyncStore(PROJECT)
    authority = value.layout_generation()
    authority.begin_cutover("offline-queue-counter-tests")
    authority.publish_project_only("offline-queue-counter-tests", verify_exact=lambda: True)
    return value


@pytest.fixture
def unit(store: ProjectSyncStore) -> Iterator[ProjectUnitOfWork]:
    with store.unit_of_work() as value:
        yield value


@pytest.fixture
def temp_queue(unit: ProjectUnitOfWork, store: ProjectSyncStore) -> OfflineQueue:
    return OfflineQueue(unit, store.layout_generation())


@dataclass
class _FakeBatchResult:
    status: str
    event_id: str


def _evt(eid: str, etype: str = "Test", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "event_id": eid,
        "event_type": etype,
        "project_uuid": PROJECT,
        "payload": payload or {},
    }


def _dossier_evt(eid: str, mission_slug: str, artifact_key: str) -> dict[str, Any]:
    return {
        "event_id": eid,
        "event_type": "MissionDossierArtifactIndexed",
        "project_uuid": PROJECT,
        "payload": {
            "namespace": {"project_uuid": PROJECT, "mission_slug": mission_slug},
            "artifact_id": {"path": artifact_key},
        },
    }


def _persisted_pending(unit: ProjectUnitOfWork) -> int:
    row = unit.execute(
        "SELECT COUNT(*) FROM outbox_tasks WHERE project_uuid = ? AND task_kind = 'event' AND state NOT IN ('synced', 'terminal_failed')",
        (PROJECT,),
    ).fetchone()
    assert row is not None
    return int(row[0])


class TestRowCountCache:
    def test_counter_initializes_lazily(self, temp_queue: OfflineQueue) -> None:
        assert not hasattr(temp_queue, "_row_count")
        assert temp_queue.size() == 0

    def test_counter_increments_on_insert(self, temp_queue: OfflineQueue, unit: ProjectUnitOfWork) -> None:
        for index in range(5):
            assert temp_queue.queue_event(_evt(f"evt-{index}")) is True
        assert temp_queue.size() == _persisted_pending(unit) == 5

    def test_counter_unchanged_on_coalesce(self, temp_queue: OfflineQueue, unit: ProjectUnitOfWork) -> None:
        assert temp_queue.queue_event(_dossier_evt("a-1", "miss-1", "spec.md")) is True
        assert temp_queue.queue_event(_dossier_evt("b-1", "miss-1", "spec.md")) is True
        assert temp_queue.size() == _persisted_pending(unit) == 2

    def test_counter_unchanged_on_duplicate_event_id(self, temp_queue: OfflineQueue, unit: ProjectUnitOfWork) -> None:
        assert temp_queue.queue_event(_evt("evt-1", payload={"v": 1})) is True
        assert temp_queue.queue_event(_evt("evt-1", payload={"v": 2})) is True
        assert temp_queue.size() == _persisted_pending(unit) == 1
        assert temp_queue.drain_queue()[0].event["payload"] == {"v": 1}

    def test_counter_after_eviction_equals_cap(self, unit: ProjectUnitOfWork, store: ProjectSyncStore) -> None:
        queue = OfflineQueue(unit, store.layout_generation(), max_queue_size=8)
        for index in range(8):
            assert queue.queue_event(_evt(f"e-{index}")) is True
        assert queue.queue_event(_evt("overflow")) is False
        assert queue.size() == _persisted_pending(unit) == 8

    def test_strict_append_raises_full(self, unit: ProjectUnitOfWork, store: ProjectSyncStore) -> None:
        queue = OfflineQueue(unit, store.layout_generation(), max_queue_size=1000)
        for index in range(4):
            queue.append(_evt(f"s-{index}"), cap=4)
        with pytest.raises(OfflineQueueFull):
            queue.append(_evt("over"), cap=4)
        assert queue.size() == 4

    def test_strict_append_default_cap_constant(self, unit: ProjectUnitOfWork, store: ProjectSyncStore) -> None:
        queue = OfflineQueue(unit, store.layout_generation(), max_queue_size=1_000_000)
        queue.append(_evt("only-one"))
        assert queue.size() == 1
        assert DEFAULT_STRICT_CAP_SIZE >= 1

    def test_counter_after_mark_synced(self, temp_queue: OfflineQueue, unit: ProjectUnitOfWork) -> None:
        for index in range(5):
            temp_queue.queue_event(_evt(f"m-{index}"))
        temp_queue.mark_synced(["m-1", "m-3"])
        assert temp_queue.size() == _persisted_pending(unit) == 3

    def test_counter_unchanged_when_mark_synced_misses(self, temp_queue: OfflineQueue, unit: ProjectUnitOfWork) -> None:
        for index in range(3):
            temp_queue.queue_event(_evt(f"k-{index}"))
        temp_queue.mark_synced(["does-not-exist"])
        assert temp_queue.size() == _persisted_pending(unit) == 3

    def test_counter_after_clear(self, temp_queue: OfflineQueue, unit: ProjectUnitOfWork) -> None:
        for index in range(7):
            temp_queue.queue_event(_evt(f"c-{index}"))
        temp_queue.clear()
        assert temp_queue.size() == _persisted_pending(unit) == 0

    def test_counter_after_process_batch_results(self, temp_queue: OfflineQueue, unit: ProjectUnitOfWork) -> None:
        for index in range(7):
            temp_queue.queue_event(_evt(f"b-{index}"))
        temp_queue.process_batch_results(
            [
                _FakeBatchResult("success", "b-0"),
                _FakeBatchResult("duplicate", "b-1"),
                _FakeBatchResult("failed_permanent", "b-2"),
                _FakeBatchResult("rejected", "b-3"),
                _FakeBatchResult("rejected", "b-4"),
                _FakeBatchResult("failed_transient", "b-5"),
                _FakeBatchResult("pending", "b-6"),
            ]
        )
        assert temp_queue.size() == _persisted_pending(unit) == 4
        assert temp_queue.get_queue_stats().total_retried == 2

    def test_counter_after_drain_to_file(self, temp_queue: OfflineQueue, unit: ProjectUnitOfWork) -> None:
        for index in range(4):
            temp_queue.queue_event(_evt(f"d-{index}"))
        assert not hasattr(temp_queue, "drain_to_file")
        assert temp_queue.size() == _persisted_pending(unit) == 4

    def test_counter_loads_from_existing_db(self, store: ProjectSyncStore) -> None:
        with store.unit_of_work() as first:
            queue = OfflineQueue(first, store.layout_generation())
            for index in range(3):
                queue.queue_event(_evt(f"l-{index}"))
        with store.unit_of_work() as second:
            assert OfflineQueue(second, store.layout_generation()).size() == 3

    def test_size_reflects_external_mutations(self, unit: ProjectUnitOfWork, store: ProjectSyncStore) -> None:
        first = OfflineQueue(unit, store.layout_generation())
        second = OfflineQueue(unit, store.layout_generation())
        first.queue_event(_evt("x-1"))
        first.queue_event(_evt("x-2"))
        assert second.size() == 2
        first.mark_synced(["x-1"])
        assert second.size() == 1

    def test_invariant_size_equals_disk_after_mixed_operations(self, temp_queue: OfflineQueue, unit: ProjectUnitOfWork) -> None:
        def assert_invariant() -> None:
            assert temp_queue.size() == _persisted_pending(unit)

        for index in range(4):
            temp_queue.queue_event(_evt(f"x-{index}"))
            assert_invariant()
        temp_queue.queue_event(_dossier_evt("d-1", "miss", "spec.md"))
        temp_queue.queue_event(_dossier_evt("d-2", "miss", "spec.md"))
        assert_invariant()
        temp_queue.queue_event(_evt("x-0", payload={"v": "new"}))
        temp_queue.mark_synced(["x-1", "x-2"])
        assert_invariant()
        temp_queue.clear()
        assert_invariant()


class TestMultiInstanceCapEnforcement:
    def test_queue_event_cap_holds_across_two_instances(self, unit: ProjectUnitOfWork, store: ProjectSyncStore) -> None:
        first = OfflineQueue(unit, store.layout_generation(), max_queue_size=2)
        second = OfflineQueue(unit, store.layout_generation(), max_queue_size=2)
        assert first.queue_event(_evt("a-1")) is True
        assert second.queue_event(_evt("b-1")) is True
        assert first.queue_event(_evt("a-2")) is False
        assert second.queue_event(_evt("b-2")) is False
        assert first.size() == second.size() == 2

    def test_queue_event_cap_holds_when_sibling_fills_to_cap_minus_one(self, unit: ProjectUnitOfWork, store: ProjectSyncStore) -> None:
        first = OfflineQueue(unit, store.layout_generation(), max_queue_size=2)
        second = OfflineQueue(unit, store.layout_generation(), max_queue_size=2)
        assert first.queue_event(_evt("a-1")) is True
        assert second.queue_event(_evt("b-1")) is True
        assert second.queue_event(_evt("b-2")) is False
        assert first.size() == second.size() == 2

    def test_strict_append_cap_holds_across_two_instances(self, unit: ProjectUnitOfWork, store: ProjectSyncStore) -> None:
        first = OfflineQueue(unit, store.layout_generation(), max_queue_size=10_000)
        second = OfflineQueue(unit, store.layout_generation(), max_queue_size=10_000)
        first.append(_evt("a-1"), cap=2)
        first.append(_evt("a-2"), cap=2)
        with pytest.raises(OfflineQueueFull):
            second.append(_evt("b-1"), cap=2)
        assert second.size() == 2


class TestNoCountScansOnHotPath:
    def test_queue_event_steady_state_has_no_count_scan(self) -> None:
        source = inspect.getsource(OfflineQueue.queue_event)
        assert "FROM queue" not in source
        assert "outbox_tasks" in source

    def test_append_steady_state_has_no_count_scan(self) -> None:
        source = inspect.getsource(OfflineQueue.append)
        assert "FROM queue" not in source
        assert "self.size()" in source
