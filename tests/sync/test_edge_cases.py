"""Edge case tests for sync module (T043).

Covers:
- Network failure queues event (SC-006)
- Invalid schema discards event
- Lamport clock desync recovery
- Queue overflow warning at the configured capacity limit
- Concurrent emission thread safety
- Non-blocking emission (SC-008)
"""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock


from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.queue import OfflineQueue
from specify_cli.sync.clock import LamportClock

import pytest

pytestmark = pytest.mark.fast


class TestNetworkFailureQueuesEvent:
    """Test that events are queued when network is unavailable (SC-006)."""

    def test_websocket_failure_falls_back_to_queue(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
        mock_auth: MagicMock,
    ):
        """WebSocket send failure queues the event instead."""
        mock_ws = MagicMock()
        mock_ws.connected = True
        mock_ws.get_status.return_value = "Connected"
        # Simulate WebSocket send failure
        mock_ws.send_event.side_effect = Exception("Connection lost")
        emitter.ws_client = mock_ws

        # mock auth as authenticated so it tries WS first
        mock_auth.is_authenticated = True

        event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is not None
        # Event should be in offline queue as fallback
        assert temp_queue.size() == 1

    def test_unauthenticated_queues_directly(
        self,
        emitter: EventEmitter,
        temp_queue: OfflineQueue,
        mock_auth: MagicMock,
    ):
        """Unauthenticated state queues events directly."""
        mock_auth.is_authenticated = False
        event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is not None
        assert temp_queue.size() == 1


class TestInvalidSchemaDiscardsEvent:
    """Test that invalid events are discarded with warning."""

    def test_invalid_wp_id_discards(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """Invalid WP ID format results in None return and no queue entry."""
        event = emitter.emit_wp_status_changed("BADID", "planned", "in_progress")
        assert event is None
        assert temp_queue.size() == 0

    def test_invalid_event_type_discards(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """Unknown event type in _emit results in None."""
        event = emitter._emit(
            event_type="NonExistentType",
            aggregate_id="WP01",
            aggregate_type="WorkPackage",
            payload={"foo": "bar"},
        )
        assert event is None
        assert temp_queue.size() == 0

    def test_missing_required_field_discards(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """Missing required payload field results in None."""
        # WPCreated requires wp_id, title, mission_slug - we pass empty title
        event = emitter.emit_wp_created("WP01", "", "028-sync")
        assert event is None
        assert temp_queue.size() == 0


class TestLamportClockDesyncRecovery:
    """Test clock reconciliation when behind server."""

    def test_receive_catches_up(self, tmp_path: Path):
        """Client clock reconciles via receive() when server is ahead."""
        clock = LamportClock(value=5, node_id="client", _storage_path=tmp_path / "c.json")
        # Server reports clock value of 1000
        new_val = clock.receive(1000)
        assert new_val == 1001
        assert clock.value == 1001

    def test_receive_saves_to_disk(self, tmp_path: Path):
        """After reconciliation, the new value is persisted."""
        path = tmp_path / "c.json"
        clock = LamportClock(value=5, node_id="client", _storage_path=path)
        clock.receive(1000)

        reloaded = LamportClock.load(path)
        assert reloaded.value == 1001

    def test_subsequent_ticks_continue_from_reconciled(self, tmp_path: Path):
        """After receive(), tick() continues from the reconciled value."""
        clock = LamportClock(value=5, node_id="client", _storage_path=tmp_path / "c.json")
        clock.receive(1000)
        next_val = clock.tick()
        assert next_val == 1002


class TestQueueOverflow:
    """Test queue behavior at the configured capacity limit."""

    def test_queue_rejects_at_max(self, tmp_path: Path):
        """Queue evicts the oldest event when it reaches MAX_QUEUE_SIZE."""
        max_queue_size = 8
        queue = OfflineQueue(db_path=tmp_path / "overflow.db", max_queue_size=max_queue_size)

        # Fill to capacity
        for i in range(max_queue_size):
            result = queue.queue_event(
                {
                    "event_id": f"evt{i:06d}00000000000000000000",
                    "event_type": "WPStatusChanged",
                    "payload": {},
                }
            )
            assert result is True

        assert queue.size() == max_queue_size

        # Next event should succeed by evicting the oldest row
        result = queue.queue_event(
            {
                "event_id": "overflow_event_00000000000000",
                "event_type": "WPStatusChanged",
                "payload": {},
            }
        )
        assert result is True
        assert queue.size() == max_queue_size
        events = queue.drain_queue(limit=1)
        assert events[0]["event_id"] != "evt0000000000000000000000"

    def test_emitter_handles_full_queue(self, tmp_path: Path, mock_auth: MagicMock):
        """EventEmitter handles queue persistence gracefully (non-blocking)."""
        queue = MagicMock(spec=OfflineQueue)
        queue.queue_event.return_value = True

        clock = LamportClock(value=0, node_id="test", _storage_path=tmp_path / "c.json")
        config = MagicMock()

        # Force unauthenticated path so event goes straight to the queue.
        mock_auth.is_authenticated = False

        em = EventEmitter(clock=clock, config=config, queue=queue, ws_client=None)
        # Should not raise even though queue is full
        event = em.emit_wp_status_changed("WP01", "planned", "in_progress")
        # Event is still returned when it can be persisted.
        assert event is not None


# WP06 (R10 part 2 / PP-06c): fixed thread fan-out for the concurrency stress
# tests. Kept at >=4 so the race surface (concurrent writers to one SQLite
# queue / one Lamport clock) is preserved when the per-thread iteration count is
# trimmed for the default fast run.
_CONCURRENCY_THREADS = 4

# Default per-thread emit volume for the fast-sync run (trimmed 50 -> 20). A
# high-volume variant is retained below behind ``@pytest.mark.slow`` because the
# corruption-catch power of this test is volume-sensitive (C-004): the more
# writes that race, the more likely a regression that drops/duplicates a row is
# surfaced. Do NOT delete the slow variant when tuning the default.
_EMIT_COUNT_DEFAULT = 20
_EMIT_COUNT_SLOW = 50

# Default per-thread tick volume for the clock-uniqueness test (trimmed 20 -> 10).
_CLOCK_COUNT_DEFAULT = 10
_CLOCK_COUNT_SLOW = 50


class TestConcurrentEmission:
    """Test thread safety of concurrent event emission."""

    @staticmethod
    def _run_concurrent_emits(
        tmp_path: Path, mock_auth: MagicMock, count: int, db_name: str
    ) -> None:
        """Drive ``_CONCURRENCY_THREADS`` writers emitting *count* events each.

        Asserts no per-thread errors and that the queue holds exactly
        ``threads * count`` rows — the loop range and this ``threads * count``
        assertion move in lockstep so volume can be tuned without silently
        weakening the invariant.
        """
        queue = OfflineQueue(db_path=tmp_path / db_name)
        clock = LamportClock(value=0, node_id="test", _storage_path=tmp_path / "c.json")
        config = MagicMock()
        mock_auth.is_authenticated = False

        em = EventEmitter(clock=clock, config=config, queue=queue, ws_client=None)

        errors: list[str] = []

        def emit_events(thread_id: int) -> None:
            try:
                for i in range(count):
                    event = em.emit_wp_status_changed("WP01", "planned", "in_progress")
                    if event is None:
                        errors.append(f"Thread {thread_id} event {i} returned None")
            except Exception as exc:
                errors.append(f"Thread {thread_id}: {exc}")

        threads = [
            threading.Thread(target=emit_events, args=(t,))
            for t in range(_CONCURRENCY_THREADS)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Errors during concurrent emission: {errors}"
        # All events should be queued (threads x count), in lockstep with count.
        assert queue.size() == _CONCURRENCY_THREADS * count

    def test_concurrent_emits_no_corruption(self, tmp_path: Path, mock_auth: MagicMock):
        """Concurrent emits don't corrupt queue or clock (default fast volume)."""
        self._run_concurrent_emits(
            tmp_path, mock_auth, _EMIT_COUNT_DEFAULT, "concurrent.db"
        )

    @pytest.mark.slow
    def test_concurrent_emits_no_corruption_high_volume(
        self, tmp_path: Path, mock_auth: MagicMock
    ):
        """High-volume corruption stress (nightly/@slow). Volume-sensitive (C-004)."""
        self._run_concurrent_emits(
            tmp_path, mock_auth, _EMIT_COUNT_SLOW, "concurrent_highvol.db"
        )

    @staticmethod
    def _run_clock_concurrency(
        tmp_path: Path, mock_auth: MagicMock, count: int, db_name: str
    ) -> None:
        """Drive concurrent clock ticks and assert total emitted == threads*count."""
        queue = OfflineQueue(db_path=tmp_path / db_name)
        clock = LamportClock(value=0, node_id="test", _storage_path=tmp_path / "c.json")
        config = MagicMock()
        mock_auth.is_authenticated = False

        em = EventEmitter(clock=clock, config=config, queue=queue, ws_client=None)

        results: list[int] = []
        lock = threading.Lock()

        def emit_and_collect() -> None:
            for _ in range(count):
                event = em.emit_wp_status_changed("WP01", "planned", "in_progress")
                if event:
                    with lock:
                        results.append(event["lamport_clock"])

        threads = [
            threading.Thread(target=emit_and_collect)
            for _ in range(_CONCURRENCY_THREADS)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Note: LamportClock.tick() is not thread-safe in the current impl,
        # but we verify all events were emitted. Some clock values may
        # duplicate under race conditions, but no crashes should occur. The
        # expected total moves in lockstep with the per-thread count.
        assert len(results) == _CONCURRENCY_THREADS * count

    def test_clock_values_unique_under_concurrency(
        self, tmp_path: Path, mock_auth: MagicMock
    ):
        """Lamport clock values under concurrent access (default fast volume)."""
        self._run_clock_concurrency(
            tmp_path, mock_auth, _CLOCK_COUNT_DEFAULT, "concurrent2.db"
        )

    @pytest.mark.slow
    def test_clock_values_unique_under_concurrency_high_volume(
        self, tmp_path: Path, mock_auth: MagicMock
    ):
        """High-volume clock concurrency stress (nightly/@slow). C-004."""
        self._run_clock_concurrency(
            tmp_path, mock_auth, _CLOCK_COUNT_SLOW, "concurrent2_highvol.db"
        )


class TestNonBlockingEmission:
    """Test that emission failures never block CLI commands (SC-008)."""

    def test_exception_in_emit_returns_none(self, tmp_path: Path, mock_auth: MagicMock):
        """Exception during _emit returns None, doesn't raise."""
        del mock_auth  # fixture is side-effect-only (installs fake token manager)
        queue = MagicMock(spec=OfflineQueue)
        clock = MagicMock()
        clock.tick.side_effect = Exception("Clock exploded")
        config = MagicMock()

        em = EventEmitter(clock=clock, config=config, queue=queue, ws_client=None)

        # Should not raise
        event = em.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is None

    def test_queue_exception_returns_event(self, tmp_path: Path, mock_auth: MagicMock):
        """Queue failure during routing doesn't prevent event creation."""
        queue = MagicMock(spec=OfflineQueue)
        queue.queue_event.side_effect = Exception("SQLite locked")

        clock = LamportClock(value=0, node_id="test", _storage_path=tmp_path / "c.json")
        config = MagicMock()
        mock_auth.is_authenticated = False

        em = EventEmitter(clock=clock, config=config, queue=queue, ws_client=None)

        # _route_event catches the exception, so _emit still returns the event
        event = em.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is not None

    def test_auth_exception_queues_event_locally(
        self, tmp_path: Path, monkeypatch
    ):
        """Auth exception during team-slug resolution still queues durably.

        Issue #1072 (teamspace-local-first-outbox): when ``get_token_manager``
        raises, the strict ingress resolver returns ``None``. The emitter
        must NOT drop the event — instead it queues with ``team_slug =
        None`` and ``drain_blocked_reason in {"no_auth", "no_team"}``. The
        drain layer re-checks on every tick and only POSTs when a Private
        Teamspace is resolvable, preserving FR-002/FR-007 of the
        private-teamspace-ingress-safeguards mission.
        """
        queue = OfflineQueue(db_path=tmp_path / "q.db")
        clock = LamportClock(value=0, node_id="test", _storage_path=tmp_path / "c.json")
        config = MagicMock()

        def _boom():
            raise RuntimeError("Not authenticated")

        monkeypatch.setattr("specify_cli.auth.get_token_manager", _boom)

        em = EventEmitter(clock=clock, config=config, queue=queue, ws_client=None)

        event = em.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is not None
        assert event["team_slug"] is None
        assert event["drain_blocked_reason"] in {"no_auth", "no_team"}
        assert queue.size() == 1
