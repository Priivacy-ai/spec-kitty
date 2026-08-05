"""Offline queue durability: enqueue while offline, and the size limit.

Originally the end-to-end offline *replay* suite, whose replay half was driven by
the queue-backed drain. #3167 retired that drain and the 11 nodes that drove it;
the surviving 4 are pure `OfflineQueue` behaviour, which stays live and is now
replayed by the delivery dispatcher rather than by `batch_sync`. Per-node
disposition:
`kitty-specs/chain-b-consent-bypass-3167-01KZ63HK/contracts/deletion-manifest.md`.

Still covered here:
1. Queue events while offline (FIFO ordering, complex nested payloads)
2. Queue size limits (oldest-row eviction, and accepting again after a drain)
"""

import pytest
from pathlib import Path
import tempfile

pytestmark = pytest.mark.fast

from specify_cli.sync.queue import OfflineQueue


@pytest.fixture
def temp_queue():
    """Create a queue with a temporary database"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_queue.db"
        queue = OfflineQueue(db_path)
        yield queue


def create_test_event(index: int, node_id: str = "test-node") -> dict:
    """Create a test event with all required fields"""
    return {
        "event_id": f"evt-{index:06d}",
        "event_type": "WPStatusChanged",
        "aggregate_id": f"WP{index % 100:02d}",
        "aggregate_type": "WorkPackage",
        "lamport_clock": index,
        "node_id": node_id,
        "causation_id": f"evt-{index - 1:06d}" if index > 0 else None,
        "payload": {"wp_id": f"WP{index % 100:02d}", "from_lane": "planned", "to_lane": "in_progress", "index": index},
    }


class TestQueueEventsOffline:
    """Test T129: Queue 100 events offline"""

    def test_queue_100_events_offline(self, temp_queue):
        """Queue 100 events while offline and verify queue state"""
        # Queue 100 events
        for i in range(100):
            event = create_test_event(i)
            result = temp_queue.queue_event(event)
            assert result is True, f"Failed to queue event {i}"

        # Verify queue size
        assert temp_queue.size() == 100

        # Verify FIFO ordering preserved
        events = temp_queue.drain_queue(limit=100)
        assert len(events) == 100
        for i, event in enumerate(events):
            assert event["event_id"] == f"evt-{i:06d}"
            assert event["payload"]["index"] == i

    def test_queue_events_with_complex_payloads(self, temp_queue):
        """Queue events with complex nested payloads"""
        for i in range(50):
            event = {
                "event_id": f"complex-{i}",
                "event_type": "ComplexEvent",
                "aggregate_id": "WP01",
                "lamport_clock": i,
                "node_id": "test",
                "payload": {
                    "nested": {"deep": {"value": i, "list": [1, 2, 3], "string": f"data-{i}"}},
                    "tags": ["tag1", "tag2", "tag3"],
                    "metadata": {"key": "value"},
                },
            }
            temp_queue.queue_event(event)

        assert temp_queue.size() == 50

        # Verify complex payload preserved
        events = temp_queue.drain_queue()
        assert events[25]["payload"]["nested"]["deep"]["value"] == 25


class TestQueueSizeLimit:
    """Test T133: Queue size limit warning"""

    def test_queue_size_limit_enforced(self, tmp_path: Path):
        """Queue should evict the oldest event at MAX_QUEUE_SIZE."""
        max_queue_size = 8
        queue = OfflineQueue(tmp_path / "queue_size_limit.db", max_queue_size=max_queue_size)

        # Fill queue to limit
        for i in range(max_queue_size):
            result = queue.queue_event({"event_id": f"evt-{i}", "event_type": "Test", "payload": {}})
            assert result is True

        assert queue.size() == max_queue_size

        # 10,001st event should succeed and evict the oldest row
        result = queue.queue_event({"event_id": "evt-overflow", "event_type": "Test", "payload": {}})
        assert result is True
        assert queue.size() == max_queue_size
        events = queue.drain_queue(limit=1)
        assert events[0]["event_id"] == "evt-1"

    def test_queue_accepts_after_sync(self, tmp_path: Path):
        """Queue accepts new events after sync makes room"""
        max_queue_size = 32
        drain_count = 10
        queue = OfflineQueue(tmp_path / "queue_accepts_after_sync.db", max_queue_size=max_queue_size)

        # Fill to limit
        for i in range(max_queue_size):
            queue.queue_event({"event_id": f"evt-{i}", "event_type": "Test", "payload": {}})

        # Drain some events (simulating sync)
        events = queue.drain_queue(limit=drain_count)
        queue.mark_synced([e["event_id"] for e in events])

        assert queue.size() == max_queue_size - drain_count

        # Should accept new events now
        result = queue.queue_event({"event_id": "evt-new", "event_type": "Test", "payload": {}})
        assert result is True
