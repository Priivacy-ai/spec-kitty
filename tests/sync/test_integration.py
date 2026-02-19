"""Integration tests for full emit → queue → batch sync → server flow (T039).

Covers:
- SC-001/SC-006/SC-007: emit → queue → sync
- Auth token handling
- Lamport clock reconciliation
- Multi-event batch flow
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from unittest.mock import MagicMock, patch


from specify_cli.sync.batch import batch_sync
from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.queue import OfflineQueue
from specify_cli.sync.clock import LamportClock


class TestFullFlow:
    """Test emit → queue → batch sync → server."""

    def test_event_emission_to_queue_to_sync(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """Full flow: emit events, verify in queue, sync to mock server (SC-001, SC-006, SC-007)."""
        # 1. Emit events
        emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        emitter.emit_wp_status_changed("WP02", "planned", "in_progress")

        # 2. Verify in queue
        assert temp_queue.size() == 2

        # 3. Sync to mock server
        with patch("specify_cli.sync.batch.requests.post") as mock_post:
            events = temp_queue.drain_queue()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {"event_id": e["event_id"], "status": "success"}
                    for e in events
                ]
            }
            mock_post.return_value = mock_response

            result = batch_sync(
                queue=temp_queue,
                auth_token="test_token",
                server_url="https://test.spec-kitty.dev",
                show_progress=False,
            )

        # 4. Verify success
        assert result.synced_count == 2
        assert temp_queue.size() == 0  # Queue drained

    def test_batch_payload_contains_correct_events(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """Batch POST payload contains all emitted events with correct structure."""
        emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        emitter.emit_wp_created("WP01", "Test WP", "028-sync")
        emitter.emit_wp_assigned("WP01", "claude", "implementation")

        with patch("specify_cli.sync.batch.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {"event_id": f"id{i}", "status": "success"}
                    for i in range(3)
                ]
            }
            mock_post.return_value = mock_response

            batch_sync(
                queue=temp_queue,
                auth_token="token",
                server_url="https://test.example.com",
                show_progress=False,
            )

            # Decompress and inspect the payload
            call_args = mock_post.call_args
            compressed = call_args.kwargs["data"]
            decompressed = gzip.decompress(compressed)
            payload = json.loads(decompressed)

            assert len(payload["events"]) == 3
            event_types = {e["event_type"] for e in payload["events"]}
            assert event_types == {"WPStatusChanged", "WPCreated", "WPAssigned"}

    def test_lamport_clock_ordering_preserved(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """Lamport clock values are strictly increasing across events."""
        events = []
        for i in range(5):
            ev = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
            assert ev is not None
            events.append(ev)

        clocks = [e["lamport_clock"] for e in events]
        assert clocks == sorted(clocks)
        assert len(set(clocks)) == 5  # All unique


class TestBatchSyncAuthHandling:
    """Test authentication-related sync behavior."""

    def test_401_marks_events_for_retry(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """401 response increments retry count, keeps events in queue."""
        emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        initial_size = temp_queue.size()

        with patch("specify_cli.sync.batch.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_post.return_value = mock_response

            result = batch_sync(
                queue=temp_queue,
                auth_token="expired_token",
                server_url="https://test.example.com",
                show_progress=False,
            )

        assert result.error_count == 1
        assert "Authentication failed" in result.error_messages
        # Events stay in queue for retry
        assert temp_queue.size() == initial_size

    def test_server_error_keeps_events_queued(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """500 response keeps events in queue for retry."""
        emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

        with patch("specify_cli.sync.batch.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_post.return_value = mock_response

            result = batch_sync(
                queue=temp_queue,
                auth_token="token",
                server_url="https://test.example.com",
                show_progress=False,
            )

        assert result.error_count == 1
        assert temp_queue.size() == 1  # Still in queue


class TestLamportClockReconciliation:
    """Test clock reconciliation across different scenarios."""

    def test_clock_receive_updates_from_remote(self, tmp_path: Path):
        """Clock reconciles when remote value is higher."""
        clock = LamportClock(value=5, node_id="local", _storage_path=tmp_path / "c.json")
        new_value = clock.receive(100)
        assert new_value == 101
        assert clock.value == 101

    def test_clock_persists_after_reconciliation(self, tmp_path: Path):
        """Clock state is persisted after receive()."""
        path = tmp_path / "c.json"
        clock = LamportClock(value=5, node_id="local", _storage_path=path)
        clock.receive(100)

        # Reload and verify
        reloaded = LamportClock.load(path)
        assert reloaded.value == 101


class TestMultiEventBatch:
    """Test batch flow with finalize-tasks style multi-event emission (SC-004)."""

    def test_feature_created_plus_wp_batch(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """Simulates finalize-tasks: 1 FeatureCreated + N WPCreated events."""
        causation_id = emitter.generate_causation_id()

        # Emit FeatureCreated
        fc = emitter.emit_feature_created(
            feature_slug="028-cli-event-emission-sync",
            feature_number="028",
            target_branch="main",
            wp_count=3,
            causation_id=causation_id,
        )
        assert fc is not None

        # Emit WPCreated for each WP
        for i in range(1, 4):
            wp = emitter.emit_wp_created(
                wp_id=f"WP{i:02d}",
                title=f"Work Package {i}",
                feature_slug="028-cli-event-emission-sync",
                causation_id=causation_id,
            )
            assert wp is not None

        # All 4 events should be queued
        assert temp_queue.size() == 4

        # All WPCreated events share the same causation_id
        events = temp_queue.drain_queue()
        causation_ids = {e.get("causation_id") for e in events if e.get("causation_id")}
        assert len(causation_ids) == 1
        assert causation_id in causation_ids

    def test_mixed_event_types_in_batch(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """Multiple event types can be batched together."""
        emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        emitter.emit_wp_assigned("WP01", "claude", "implementation")
        emitter.emit_history_added("WP01", "note", "Started work")

        assert temp_queue.size() == 3

        with patch("specify_cli.sync.batch.requests.post") as mock_post:
            events = temp_queue.drain_queue()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "results": [
                    {"event_id": e["event_id"], "status": "success"}
                    for e in events
                ]
            }
            mock_post.return_value = mock_response

            result = batch_sync(
                queue=temp_queue,
                auth_token="token",
                server_url="https://test.example.com",
                show_progress=False,
            )

        assert result.synced_count == 3
        assert temp_queue.size() == 0
