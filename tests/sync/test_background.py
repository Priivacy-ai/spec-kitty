"""Tests for BackgroundSyncService (T038).

Covers:
- start() / stop() lifecycle
- Exponential backoff with 30s cap
- sync_now() immediate flush
- Timer scheduling
- Thread safety
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.fast

from specify_cli.sync.background import (
    BackgroundSyncService,
    get_sync_service,
    reset_sync_service,
)
from specify_cli.sync.queue import OfflineQueue


@pytest.fixture(autouse=True)
def _isolate_legacy_queue(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep lifecycle tests independent of a worker's earlier queue rows."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime-home"))


@pytest.fixture
def mock_queue(tmp_path) -> OfflineQueue:
    """Real queue with tmp_path database."""
    return OfflineQueue(db_path=tmp_path / "bg_queue.db")


@pytest.fixture
def mock_auth(monkeypatch):
    """Mock token-fetching helper used by BackgroundSyncService.

    Returns a MagicMock whose ``return_value`` is the token string; tests can
    set ``.return_value = None`` to simulate the unauthenticated state.
    """
    fake_fetch = MagicMock(return_value="token")
    monkeypatch.setattr(
        "specify_cli.sync.background._fetch_access_token_sync", fake_fetch
    )
    return fake_fetch


@pytest.fixture
def mock_config() -> MagicMock:
    """Mock SyncConfig."""
    config = MagicMock()
    config.get_server_url.return_value = "https://test.example.com"
    return config


@pytest.fixture
def service(mock_queue, mock_auth, mock_config) -> BackgroundSyncService:
    """BackgroundSyncService with mocked dependencies.

    The ``mock_auth`` fixture already patched the token-fetch bridge, so
    constructing the service is a no-op w.r.t. auth plumbing.
    """
    return BackgroundSyncService(
        queue=mock_queue,
        config=mock_config,
        sync_interval_seconds=0.1,  # Fast for testing
    )


def _failing_drain(service: BackgroundSyncService):
    """Make the daemon's surviving work (the body drain) raise.

    Since #3030 FR-012 removed the queue-backed event drain, the body upload
    queue is the only thing a tick can fail on — so it is the seam that drives
    the backoff contract.
    """
    service._body_queue = MagicMock()
    return patch.object(
        service, "_drain_body_queue", side_effect=Exception("fail")
    )


class TestStartStop:
    """Test start/stop lifecycle."""

    def test_start_sets_running(self, service: BackgroundSyncService):
        """start() sets is_running to True."""
        service.start()
        assert service.is_running is True
        service.stop()

    def test_start_schedules_timer(self, service: BackgroundSyncService):
        """start() schedules the first timer."""
        service.start()
        assert service._timer is not None
        service.stop()

    def test_stop_cancels_timer(self, service: BackgroundSyncService):
        """stop() cancels the running timer."""
        service.start()
        service.stop()
        assert service.is_running is False
        assert service._timer is None

    def test_stop_idempotent(self, service: BackgroundSyncService):
        """stop() is safe to call multiple times."""
        service.start()
        service.stop()
        service.stop()  # Should not raise
        assert service.is_running is False

    def test_start_idempotent(self, service: BackgroundSyncService):
        """start() is safe to call multiple times."""
        service.start()
        service.start()  # Should not raise
        assert service.is_running is True
        service.stop()

    def test_timer_is_daemon(self, service: BackgroundSyncService):
        """Timer thread is a daemon (doesn't block CLI exit)."""
        service.start()
        assert service._timer.daemon is True
        service.stop()

    def test_wake_reschedules_timer(self, service: BackgroundSyncService, monkeypatch):
        """wake() cancels the existing timer and schedules an earlier tick."""
        intervals: list[float] = []

        class FakeTimer:
            def __init__(self, interval, callback):
                del callback
                intervals.append(interval)
                self.daemon = False

            def start(self):
                return None

            def cancel(self):
                intervals.append(-1.0)

            def join(self, timeout=None):
                del timeout
                return None

        monkeypatch.setattr("specify_cli.sync.background.threading.Timer", FakeTimer)

        service.start()
        service.wake(delay_seconds=0.25)

        assert intervals[0] == service.sync_interval_seconds
        assert -1.0 in intervals
        assert intervals[-1] == 0.25
        service.stop()

    def test_wake_does_not_wait_for_busy_sync_lock(
        self,
        service: BackgroundSyncService,
        monkeypatch,
    ):
        """wake() is a best-effort hint and must not block status emission."""
        intervals: list[float] = []

        class FakeTimer:
            def __init__(self, interval, callback):
                del callback
                intervals.append(interval)
                self.daemon = False

            def start(self):
                return None

            def cancel(self):
                intervals.append(-1.0)

            def join(self, timeout=None):
                del timeout
                return None

        monkeypatch.setattr("specify_cli.sync.background.threading.Timer", FakeTimer)

        service.start()
        assert service._lock.acquire(blocking=False) is True
        try:
            service.wake(delay_seconds=0.25)
        finally:
            service._lock.release()

        assert intervals == [service.sync_interval_seconds]
        service.stop()


class TestExponentialBackoff:
    """Test backoff on sync failure."""

    def test_backoff_doubles_on_failure(self, service: BackgroundSyncService):
        """Backoff doubles with each consecutive failure."""
        service._backoff_seconds = 0.5

        with _failing_drain(service):
            service._perform_sync()  # failure 1
            assert service._backoff_seconds == 1.0
            service._perform_sync()  # failure 2
            assert service._backoff_seconds == 2.0
            service._perform_sync()  # failure 3
            assert service._backoff_seconds == 4.0

    def test_backoff_capped_at_30s(self, service: BackgroundSyncService):
        """Backoff never exceeds 30 seconds."""
        service._backoff_seconds = 16.0

        with _failing_drain(service):
            service._perform_sync()  # 16 -> 30 (capped)
            assert service._backoff_seconds == 30.0
            service._perform_sync()  # stays at 30
            assert service._backoff_seconds == 30.0

    def test_backoff_resets_on_success(self, service: BackgroundSyncService):
        """Backoff resets to 0.5s on successful sync."""
        service._backoff_seconds = 16.0
        service._consecutive_failures = 5

        service._perform_sync()

        assert service._backoff_seconds == 0.5
        assert service._consecutive_failures == 0

    def test_consecutive_failures_tracked(self, service: BackgroundSyncService):
        """consecutive_failures increments on each failure."""
        assert service.consecutive_failures == 0

        with _failing_drain(service):
            service._perform_sync()
            assert service.consecutive_failures == 1
            service._perform_sync()
            assert service.consecutive_failures == 2


class TestSyncNow:
    """Test sync_now() immediate flush."""

    def test_sync_now_drains_body_queue(self, service, mock_auth):
        """sync_now() drains body uploads — the surviving daemon drain."""
        service._body_queue = MagicMock()

        with patch.object(service, "_drain_body_queue") as mock_drain:
            service.sync_now()
            mock_drain.assert_called_once()

    def test_sync_now_resets_backoff(self, service):
        """sync_now() resets backoff on success."""
        service._backoff_seconds = 16.0
        service._consecutive_failures = 3

        service.sync_now()
        assert service._backoff_seconds == 0.5
        assert service._consecutive_failures == 0

    def test_sync_now_when_not_authenticated_classifies_queue_without_mutation(
        self,
        service,
        mock_auth,
    ):
        """sync_now() classifies queued events as unauthenticated without draining."""
        service.queue.queue_event(
            {
                "event_id": "evt-unauth-001",
                "event_type": "Test",
                "payload": {},
            }
        )
        service.queue.queue_event(
            {
                "event_id": "evt-unauth-002",
                "event_type": "Test",
                "payload": {},
            }
        )
        mock_auth.return_value = None

        result = service.sync_now()
        assert result.synced_count == 0
        assert result.error_count == 2
        assert result.category_counts == {"unauthenticated": 2}
        assert [r.event_id for r in result.failed_results] == [
            "evt-unauth-001",
            "evt-unauth-002",
        ]
        assert "spec-kitty auth login" in result.error_messages[0]
        assert service.queue.size() == 2
        assert [event["event_id"] for event in service.queue.drain_queue()] == [
            "evt-unauth-001",
            "evt-unauth-002",
        ]

    def test_sync_now_handles_failure(self, service):
        """sync_now() handles sync failure gracefully."""
        with _failing_drain(service):
            result = service.sync_now()

        assert result.error_count == 1
        assert "fail" in result.error_messages[0]


class TestLastSync:
    """Test last_sync tracking."""

    def test_last_sync_updated_on_success(self, service):
        """last_sync is updated after successful sync."""
        assert service.last_sync is None

        # Populate queue so sync proceeds
        service.queue.queue_event(
            {
                "event_id": "test123456789012345678901",
                "event_type": "WPStatusChanged",
                "payload": {},
            }
        )
        service._perform_sync()

        assert service.last_sync is not None


class TestSingletonAccessor:
    """Test get_sync_service / reset_sync_service."""

    def teardown_method(self):
        try:
            reset_sync_service()
        except Exception:
            # Force-clear the singleton if stop() fails with mocked queue
            import specify_cli.sync.background as _bg

            with _bg._service_lock:
                if _bg._service is not None:
                    _bg._service._running = False
                    if _bg._service._timer is not None:
                        _bg._service._timer.cancel()
                _bg._service = None

    @patch("specify_cli.sync.background.SyncConfig")
    @patch("specify_cli.sync.background.OfflineQueue")
    def test_get_sync_service_returns_same_instance(self, mock_q, _c):
        """get_sync_service() returns the same instance."""
        mock_q.return_value.size.return_value = 0
        s1 = get_sync_service()
        s2 = get_sync_service()
        assert s1 is s2
        s1.stop()

    @patch("specify_cli.sync.background.SyncConfig")
    @patch("specify_cli.sync.background.OfflineQueue")
    def test_reset_clears_singleton(self, mock_q, _c):
        """reset_sync_service() allows new instance."""
        mock_q.return_value.size.return_value = 0
        s1 = get_sync_service()
        s1.stop()
        reset_sync_service()
        s2 = get_sync_service()
        assert s1 is not s2
        s2.stop()
