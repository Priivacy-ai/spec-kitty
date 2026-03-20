"""Tests for issue #306: offline queue resilience improvements.

Covers:
- Event coalescing for high-volume types (MissionDossierArtifactIndexed, etc.)
- Configurable queue cap via max_queue_size parameter
- Improved queue-full messaging
- QueueStats includes max_queue_size
- Migration of coalesce_key column on legacy databases
"""

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast

from specify_cli.sync.queue import (
    COALESCEABLE_EVENT_TYPES,
    DEFAULT_MAX_QUEUE_SIZE,
    OfflineQueue,
    QueueStats,
    _coalesce_key,
)


@pytest.fixture
def temp_queue(tmp_path: Path) -> OfflineQueue:
    """Queue with default settings."""
    db_path = tmp_path / "test_queue.db"
    return OfflineQueue(db_path=db_path)


@pytest.fixture
def small_queue(tmp_path: Path) -> OfflineQueue:
    """Queue with a small max size for testing overflow."""
    db_path = tmp_path / "small_queue.db"
    return OfflineQueue(db_path=db_path, max_queue_size=5)


# ---------------------------------------------------------------------------
# A. Event coalescing
# ---------------------------------------------------------------------------


class TestCoalesceKey:
    """Unit tests for the _coalesce_key() helper."""

    def test_non_coalesceable_returns_none(self):
        event = {"event_type": "WPStatusChanged", "payload": {"wp_id": "WP01"}}
        assert _coalesce_key(event) is None

    def test_artifact_indexed_key(self):
        event = {
            "event_type": "MissionDossierArtifactIndexed",
            "payload": {"feature_slug": "010-my-feature", "artifact_key": "manifest.json"},
        }
        key = _coalesce_key(event)
        assert key == "MissionDossierArtifactIndexed|010-my-feature|manifest.json"

    def test_snapshot_computed_key(self):
        event = {
            "event_type": "MissionDossierSnapshotComputed",
            "payload": {"feature_slug": "010-my-feature", "snapshot_id": "snap-001"},
        }
        key = _coalesce_key(event)
        assert key == "MissionDossierSnapshotComputed|010-my-feature"

    def test_missing_payload_fields_produce_empty_parts(self):
        event = {"event_type": "MissionDossierArtifactIndexed", "payload": {}}
        key = _coalesce_key(event)
        assert key == "MissionDossierArtifactIndexed||"


class TestEventCoalescing:
    """Integration tests: coalescing prevents duplicate queue rows."""

    def test_coalescing_updates_existing_row(self, temp_queue: OfflineQueue):
        """Second event with same coalesce key replaces first, keeping queue size at 1."""
        event1 = {
            "event_id": "evt-001",
            "event_type": "MissionDossierArtifactIndexed",
            "payload": {
                "feature_slug": "010-feat",
                "artifact_key": "readme.md",
                "content_hash_sha256": "aaa",
            },
        }
        event2 = {
            "event_id": "evt-002",
            "event_type": "MissionDossierArtifactIndexed",
            "payload": {
                "feature_slug": "010-feat",
                "artifact_key": "readme.md",
                "content_hash_sha256": "bbb",
            },
        }

        assert temp_queue.queue_event(event1) is True
        assert temp_queue.size() == 1

        assert temp_queue.queue_event(event2) is True
        assert temp_queue.size() == 1  # coalesced, not 2

        events = temp_queue.drain_queue()
        assert len(events) == 1
        assert events[0]["event_id"] == "evt-002"
        assert events[0]["payload"]["content_hash_sha256"] == "bbb"

    def test_different_artifact_keys_not_coalesced(self, temp_queue: OfflineQueue):
        event1 = {
            "event_id": "evt-001",
            "event_type": "MissionDossierArtifactIndexed",
            "payload": {"feature_slug": "010-feat", "artifact_key": "a.md"},
        }
        event2 = {
            "event_id": "evt-002",
            "event_type": "MissionDossierArtifactIndexed",
            "payload": {"feature_slug": "010-feat", "artifact_key": "b.md"},
        }

        temp_queue.queue_event(event1)
        temp_queue.queue_event(event2)
        assert temp_queue.size() == 2

    def test_non_coalesceable_events_never_coalesced(self, temp_queue: OfflineQueue):
        """WPStatusChanged events should never coalesce."""
        for i in range(5):
            temp_queue.queue_event({
                "event_id": f"evt-{i}",
                "event_type": "WPStatusChanged",
                "payload": {"wp_id": "WP01"},
            })
        assert temp_queue.size() == 5

    def test_coalescing_works_even_when_queue_full(self, small_queue: OfflineQueue):
        """Coalescing updates in-place before the size check, so it succeeds even at capacity."""
        # Fill with 4 non-coalesceable + 1 coalesceable
        for i in range(4):
            small_queue.queue_event({
                "event_id": f"nc-{i}",
                "event_type": "WPStatusChanged",
                "payload": {},
            })
        small_queue.queue_event({
            "event_id": "coal-1",
            "event_type": "MissionDossierArtifactIndexed",
            "payload": {"feature_slug": "f", "artifact_key": "k"},
        })
        assert small_queue.size() == 5  # at capacity

        # This should coalesce in-place (update the existing coalesceable row)
        result = small_queue.queue_event({
            "event_id": "coal-2",
            "event_type": "MissionDossierArtifactIndexed",
            "payload": {"feature_slug": "f", "artifact_key": "k"},
        })
        assert result is True
        assert small_queue.size() == 5  # still at capacity, not 6

    def test_snapshot_computed_coalesces(self, temp_queue: OfflineQueue):
        """MissionDossierSnapshotComputed should keep only the latest snapshot per feature."""
        for i in range(10):
            temp_queue.queue_event({
                "event_id": f"snap-{i}",
                "event_type": "MissionDossierSnapshotComputed",
                "payload": {"feature_slug": "010-feat", "snapshot_id": f"snap-{i}"},
            })
        assert temp_queue.size() == 1
        events = temp_queue.drain_queue()
        assert events[0]["event_id"] == "snap-9"
        assert events[0]["payload"]["snapshot_id"] == "snap-9"


# ---------------------------------------------------------------------------
# B. Configurable queue cap
# ---------------------------------------------------------------------------


class TestConfigurableQueueCap:
    """Test that max_queue_size is configurable."""

    def test_default_max_queue_size(self, temp_queue: OfflineQueue):
        assert temp_queue._max_queue_size == DEFAULT_MAX_QUEUE_SIZE

    def test_custom_max_queue_size(self, small_queue: OfflineQueue):
        assert small_queue._max_queue_size == 5

    def test_queue_evicts_oldest_at_custom_cap(self, small_queue: OfflineQueue):
        for i in range(5):
            assert small_queue.queue_event({
                "event_id": f"evt-{i}",
                "event_type": "WPStatusChanged",
                "payload": {},
            }) is True

        # 6th event should succeed, evicting the oldest
        result = small_queue.queue_event({
            "event_id": "overflow",
            "event_type": "WPStatusChanged",
            "payload": {},
        })
        assert result is True
        assert small_queue.size() == 5  # still at cap, oldest evicted

        # Verify the oldest event (evt-0) was evicted and newest is present
        events = small_queue.drain_queue()
        event_ids = [e["event_id"] for e in events]
        assert "evt-0" not in event_ids
        assert "overflow" in event_ids

    def test_queue_stats_includes_max_size(self, small_queue: OfflineQueue):
        small_queue.queue_event({"event_id": "e1", "event_type": "Test", "payload": {}})
        stats = small_queue.get_queue_stats()
        assert stats.max_queue_size == 5

    def test_class_attr_still_default(self):
        """OfflineQueue.MAX_QUEUE_SIZE class attr preserved for back-compat."""
        assert OfflineQueue.MAX_QUEUE_SIZE == DEFAULT_MAX_QUEUE_SIZE


# ---------------------------------------------------------------------------
# C. Better queue-full messaging
# ---------------------------------------------------------------------------


class TestQueueFullMessaging:
    """The queue-full warning should include actionable remediation advice."""

    def test_full_queue_message_includes_remediation(self, small_queue: OfflineQueue, capsys):
        # Fill the queue
        for i in range(5):
            small_queue.queue_event({"event_id": f"e-{i}", "event_type": "T", "payload": {}})

        # Trigger the eviction path
        small_queue.queue_event({"event_id": "overflow", "event_type": "T", "payload": {}})

        captured = capsys.readouterr()
        assert "Evicted" in captured.err
        assert "spec-kitty sync status --check" in captured.err
        assert "spec-kitty sync now" in captured.err


# ---------------------------------------------------------------------------
# D. QueueStats defaults
# ---------------------------------------------------------------------------


class TestQueueStatsDefaults:
    def test_default_max_queue_size_in_stats(self):
        stats = QueueStats()
        assert stats.max_queue_size == DEFAULT_MAX_QUEUE_SIZE

    def test_empty_queue_stats_max_size(self, temp_queue: OfflineQueue):
        stats = temp_queue.get_queue_stats()
        # Empty queue returns default QueueStats but that's a fresh dataclass
        # so max_queue_size is the DEFAULT (not the instance value when empty)
        # This is acceptable: when queue is empty the stats still report the default.
        assert stats.max_queue_size == DEFAULT_MAX_QUEUE_SIZE


# ---------------------------------------------------------------------------
# Migration: coalesce_key column
# ---------------------------------------------------------------------------


class TestCoalesceKeyMigration:
    """Ensure the migration adds coalesce_key to legacy databases."""

    def test_migration_adds_column_to_legacy_db(self, tmp_path: Path):
        """Create a database WITHOUT coalesce_key, then open with OfflineQueue."""
        db_path = tmp_path / "legacy.db"
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                event_type TEXT NOT NULL,
                data TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                retry_count INTEGER DEFAULT 0
            )
        """)
        conn.execute(
            "INSERT INTO queue (event_id, event_type, data, timestamp) VALUES (?, ?, ?, ?)",
            ("legacy-1", "WPStatusChanged", json.dumps({"event_id": "legacy-1"}), 1000),
        )
        conn.commit()
        conn.close()

        # Now open with OfflineQueue -- migration should add coalesce_key
        queue = OfflineQueue(db_path=db_path)
        assert queue.size() == 1

        # Verify the column exists by inserting with coalesce_key
        queue.queue_event({
            "event_id": "new-1",
            "event_type": "MissionDossierArtifactIndexed",
            "payload": {"feature_slug": "f", "artifact_key": "k"},
        })
        assert queue.size() == 2
