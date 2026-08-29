"""Integration test: ``OfflineQueueFull`` (FR-027, T035).

Verifies that:

* ``OfflineQueue.append()`` raises :class:`OfflineQueueFull` rather than
  silently dropping events when the queue is at capacity.
* A burst of appends past capacity loses zero events when the caller drains
  and acknowledges (``drain_queue`` + ``remove_events``) to free capacity and
  retries, using the per-project-store queue API.

Historical note: this module used to also cover ``OfflineQueue.drain_to_file``
(a JSONL-file spillover written by the caller on overflow) and its replay
round-trip. That method was retired when the queue moved off a
file/db-per-project backing onto the shared per-project SQLite store (see
``tests/sync/test_offline_queue_counter.py::test_counter_after_drain_to_file``,
which asserts ``not hasattr(queue, "drain_to_file")``). There is no file-based
equivalent to port those two tests to — the durable store itself is now the
only backing, so "drain to a JSONL file" has no successor operation — so they
were retired rather than migrated.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from specify_cli.sync.project_store import ProjectSyncStore, ProjectUnitOfWork
from specify_cli.sync.queue import (
    DEFAULT_STRICT_CAP_SIZE,  # noqa: F401 - smoke import for the surface
    OfflineQueue,
    OfflineQueueFull,
)


from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

CAP = 5  # tight cap keeps the test fast and deterministic
PROJECT = "aaaaaaaa-0000-0000-0000-00000000ff10"


def _event(idx: int) -> dict[str, object]:
    return {
        "event_id": f"evt-{idx:04d}",
        "event_type": "TestEvent",
        "project_uuid": PROJECT,
        "payload": {"i": idx},
    }


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectSyncStore:
    """A scratch per-project store rooted in *tmp_path*."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    value = ProjectSyncStore(PROJECT)
    authority = value.layout_generation()
    authority.begin_cutover("offline-queue-overflow-test")
    authority.publish_project_only("offline-queue-overflow-test", verify_exact=lambda: True)
    return value


@pytest.fixture
def unit(store: ProjectSyncStore) -> Iterator[ProjectUnitOfWork]:
    with store.unit_of_work() as value:
        yield value


@pytest.fixture
def queue(unit: ProjectUnitOfWork, store: ProjectSyncStore) -> OfflineQueue:
    """A scratch :class:`OfflineQueue` bound to the *store*/*unit* fixtures."""
    return OfflineQueue(unit, store.layout_generation())


class TestOfflineQueueOverflow:
    """FR-027: full queue must not silently drop events."""

    def test_append_raises_at_cap(self, queue: OfflineQueue) -> None:
        for i in range(CAP):
            queue.append(_event(i), cap=CAP)
        assert queue.size() == CAP

        with pytest.raises(OfflineQueueFull) as exc_info:
            queue.append(_event(CAP), cap=CAP)
        # Structured error: cap and current depth are exposed.
        assert exc_info.value.cap == CAP
        assert exc_info.value.current == CAP

    def test_zero_events_dropped_under_load(self, queue: OfflineQueue) -> None:
        """Burst of (CAP * 3) appends → exactly 0 events lost.

        The CLI handler pattern (post-per-project-store migration) is:

            try:
                queue.append(event, cap=CAP)
            except OfflineQueueFull:
                # Free capacity by acknowledging the oldest pending batch,
                # then retry once.
                oldest = queue.drain_queue(limit=CAP)
                queue.remove_events([task.event_id for task in oldest])
                queue.append(event, cap=CAP)

        This replaces the old file-spillover pattern (``drain_to_file`` was
        retired — see the module docstring) with the store-native
        drain-then-acknowledge pair. We replay that pattern here and assert
        every event ends up either still pending in the queue or
        acknowledged (removed) — never lost.
        """
        total = CAP * 3
        acknowledged_ids: set[str] = set()
        for i in range(total):
            try:
                queue.append(_event(i), cap=CAP)
            except OfflineQueueFull:
                oldest = queue.drain_queue(limit=CAP)
                ids = [task.event_id for task in oldest]
                queue.remove_events(ids)
                acknowledged_ids.update(ids)
                queue.append(_event(i), cap=CAP)

        retained_ids = {task.event_id for task in queue.drain_queue(limit=total * 2)}
        expected_ids = {f"evt-{i:04d}" for i in range(total)}

        assert acknowledged_ids & retained_ids == set(), (
            "an event must not be both acknowledged and still pending"
        )
        assert acknowledged_ids | retained_ids == expected_ids, (
            f"Expected all {total} events accounted for, "
            f"got retained={len(retained_ids)} + acknowledged={len(acknowledged_ids)}"
        )
