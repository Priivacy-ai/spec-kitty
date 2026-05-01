"""Integration test: ``OfflineQueueFull`` + drain helper (FR-027, T035).

Verifies that:

* ``OfflineQueue.append()`` raises :class:`OfflineQueueFull` rather than
  silently dropping events when the queue is at capacity.
* :meth:`OfflineQueue.drain_to_file` writes a JSONL stream and clears
  the queue.
* The drained file is replayable: a fresh :class:`OfflineQueue`
  re-imports every drained event with the strict-cap append surface.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.sync.queue import (
    DEFAULT_STRICT_CAP_SIZE,  # noqa: F401 - smoke import for the surface
    OfflineQueue,
    OfflineQueueFull,
)


CAP = 5  # tight cap keeps the test fast and deterministic


def _event(idx: int) -> dict[str, object]:
    return {
        "event_id": f"evt-{idx:04d}",
        "event_type": "TestEvent",
        "payload": {"i": idx},
    }


@pytest.fixture
def queue(tmp_path: Path) -> OfflineQueue:
    """A scratch :class:`OfflineQueue` rooted in *tmp_path*."""
    db_path = tmp_path / "queue.db"
    return OfflineQueue(db_path=db_path)


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

    def test_drain_to_file_writes_jsonl_and_clears(
        self,
        queue: OfflineQueue,
        tmp_path: Path,
    ) -> None:
        for i in range(CAP):
            queue.append(_event(i), cap=CAP)
        overflow = tmp_path / "sync" / "overflow.jsonl"

        drained = queue.drain_to_file(overflow)
        assert drained == CAP
        assert queue.size() == 0
        assert overflow.exists()

        lines = overflow.read_text(encoding="utf-8").splitlines()
        assert len(lines) == CAP
        ids = [json.loads(line)["event_id"] for line in lines]
        # Order is FIFO.
        assert ids == [f"evt-{i:04d}" for i in range(CAP)]

    def test_drained_file_is_replayable(
        self,
        queue: OfflineQueue,
        tmp_path: Path,
    ) -> None:
        """Round-trip: drain -> re-import -> queue has every event."""
        for i in range(CAP):
            queue.append(_event(i), cap=CAP)
        overflow = tmp_path / "sync" / "overflow.jsonl"
        drained = queue.drain_to_file(overflow)
        assert drained == CAP

        # Fresh queue: re-import the drained events using the
        # strict-cap append surface.
        replay_db = tmp_path / "replay.db"
        replay_queue = OfflineQueue(db_path=replay_db)
        with open(overflow, "r", encoding="utf-8") as fh:
            for line in fh:
                replay_queue.append(json.loads(line), cap=CAP)
        assert replay_queue.size() == CAP
        events = replay_queue.drain_queue(limit=CAP * 2)
        assert {e["event_id"] for e in events} == {
            f"evt-{i:04d}" for i in range(CAP)
        }

    def test_zero_events_dropped_under_load(
        self,
        queue: OfflineQueue,
        tmp_path: Path,
    ) -> None:
        """Burst of (CAP * 3) appends → exactly 0 events lost.

        The CLI handler pattern is:

            try:
                queue.append(event, cap=CAP)
            except OfflineQueueFull:
                queue.drain_to_file(overflow_path)
                queue.append(event, cap=CAP)  # retry once

        We replay that pattern here and assert all events end up either
        in the queue or in the overflow file.
        """
        overflow = tmp_path / "sync" / "overflow.jsonl"
        total = CAP * 3
        attempts = 0
        for i in range(total):
            attempts += 1
            try:
                queue.append(_event(i), cap=CAP)
            except OfflineQueueFull:
                # Drain then re-append once.
                # Use a per-overflow-cycle distinct file to preserve
                # evidence across multiple drains.
                cycle_path = tmp_path / "sync" / f"overflow-{attempts:04d}.jsonl"
                queue.drain_to_file(cycle_path)
                queue.append(_event(i), cap=CAP)

        # Sum events retained in queue + every overflow file.
        retained = queue.size()
        overflow_total = 0
        for path in (tmp_path / "sync").glob("overflow-*.jsonl"):
            overflow_total += sum(1 for _ in path.read_text().splitlines() if _.strip())

        assert retained + overflow_total == total, (
            f"Expected {total} events accounted for, "
            f"got retained={retained} + overflow={overflow_total}"
        )
