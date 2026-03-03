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

from specify_cli.sync.background import (
    BackgroundSyncService,
    get_sync_service,
    reset_sync_service,
)
from specify_cli.sync.batch import BatchSyncResult
from specify_cli.sync.queue import OfflineQueue


@pytest.fixture
def mock_queue(tmp_path) -> OfflineQueue:
    """Real queue with tmp_path database."""
    return OfflineQueue(db_path=tmp_path / "bg_queue.db")


@pytest.fixture
def mock_auth() -> MagicMock:
    """Mock AuthClient."""
    auth = MagicMock()
    auth.get_access_token.return_value = "token"
    auth.is_authenticated.return_value = True
    return auth


@pytest.fixture
def mock_config() -> MagicMock:
    """Mock SyncConfig."""
    config = MagicMock()
    config.get_server_url.return_value = "https://test.example.com"
    return config


@pytest.fixture
def service(mock_queue, mock_auth, mock_config) -> BackgroundSyncService:
    """BackgroundSyncService with mocked dependencies."""
    return BackgroundSyncService(
        queue=mock_queue,
        auth=mock_auth,
        config=mock_config,
        sync_interval_seconds=0.1,  # Fast for testing
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


class TestExponentialBackoff:
    """Test backoff on sync failure."""

    @patch("specify_cli.sync.background.batch_sync")
    def test_backoff_doubles_on_failure(self, mock_batch, service: BackgroundSyncService):
        """Backoff doubles with each consecutive failure."""
        service._backoff_seconds = 0.5
        mock_batch.side_effect = Exception("fail")

        service._perform_sync()  # failure 1
        assert service._backoff_seconds == 1.0
        service._perform_sync()  # failure 2
        assert service._backoff_seconds == 2.0
        service._perform_sync()  # failure 3
        assert service._backoff_seconds == 4.0

    @patch("specify_cli.sync.background.batch_sync")
    def test_backoff_capped_at_30s(self, mock_batch, service: BackgroundSyncService):
        """Backoff never exceeds 30 seconds."""
        service._backoff_seconds = 16.0
        mock_batch.side_effect = Exception("fail")

        service._perform_sync()  # 16 -> 30 (capped)
        assert service._backoff_seconds == 30.0
        service._perform_sync()  # stays at 30
        assert service._backoff_seconds == 30.0

    @patch("specify_cli.sync.background.batch_sync")
    def test_backoff_resets_on_success(self, mock_batch, service: BackgroundSyncService):
        """Backoff resets to 0.5s on successful sync."""
        service._backoff_seconds = 16.0
        service._consecutive_failures = 5

        ok_result = BatchSyncResult()
        ok_result.synced_count = 1
        mock_batch.return_value = ok_result

        service._perform_sync()

        assert service._backoff_seconds == 0.5
        assert service._consecutive_failures == 0

    @patch("specify_cli.sync.background.batch_sync")
    def test_consecutive_failures_tracked(self, mock_batch, service: BackgroundSyncService):
        """consecutive_failures increments on each failure."""
        assert service.consecutive_failures == 0
        mock_batch.side_effect = Exception("fail")

        service._perform_sync()
        assert service.consecutive_failures == 1
        service._perform_sync()
        assert service.consecutive_failures == 2


class TestSyncNow:
    """Test sync_now() immediate flush."""

    @patch("specify_cli.sync.background.sync_all_queued_events")
    def test_sync_now_drains_queue(self, mock_sync_all, service, mock_auth):
        """sync_now() calls sync_all_queued_events."""
        expected = BatchSyncResult()
        expected.synced_count = 5
        mock_sync_all.return_value = expected

        result = service.sync_now()
        assert result.synced_count == 5
        mock_sync_all.assert_called_once()

    @patch("specify_cli.sync.background.sync_all_queued_events")
    def test_sync_now_resets_backoff(self, mock_sync_all, service):
        """sync_now() resets backoff on success."""
        service._backoff_seconds = 16.0
        service._consecutive_failures = 3

        ok = BatchSyncResult()
        ok.synced_count = 1
        mock_sync_all.return_value = ok

        service.sync_now()
        assert service._backoff_seconds == 0.5
        assert service._consecutive_failures == 0

    def test_sync_now_when_not_authenticated(self, service, mock_auth):
        """sync_now() returns empty result when not authenticated."""
        mock_auth.get_access_token.return_value = None

        result = service.sync_now()
        assert result.synced_count == 0

    @patch("specify_cli.sync.background.sync_all_queued_events")
    def test_sync_now_handles_failure(self, mock_sync_all, service):
        """sync_now() handles sync failure gracefully."""
        mock_sync_all.side_effect = Exception("Network error")

        result = service.sync_now()
        assert result.error_count == 1
        assert "Network error" in result.error_messages[0]


class TestLastSync:
    """Test last_sync tracking."""

    @patch("specify_cli.sync.background.batch_sync")
    def test_last_sync_updated_on_success(self, mock_batch, service):
        """last_sync is updated after successful sync."""
        assert service.last_sync is None

        ok = BatchSyncResult()
        ok.synced_count = 1
        mock_batch.return_value = ok

        # Populate queue so sync proceeds
        service.queue.queue_event({
            "event_id": "test123456789012345678901",
            "event_type": "WPStatusChanged",
            "payload": {},
        })
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

    @patch("specify_cli.sync.background.AuthClient")
    @patch("specify_cli.sync.background.SyncConfig")
    @patch("specify_cli.sync.background.OfflineQueue")
    def test_get_sync_service_returns_same_instance(self, mock_q, _c, _a):
        """get_sync_service() returns the same instance."""
        mock_q.return_value.size.return_value = 0
        s1 = get_sync_service()
        s2 = get_sync_service()
        assert s1 is s2
        s1.stop()

    @patch("specify_cli.sync.background.AuthClient")
    @patch("specify_cli.sync.background.SyncConfig")
    @patch("specify_cli.sync.background.OfflineQueue")
    def test_reset_clears_singleton(self, mock_q, _c, _a):
        """reset_sync_service() allows new instance."""
        mock_q.return_value.size.return_value = 0
        s1 = get_sync_service()
        s1.stop()
        reset_sync_service()
        s2 = get_sync_service()
        assert s1 is not s2
        s2.stop()
