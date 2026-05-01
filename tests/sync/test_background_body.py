"""Tests for background sync body queue drain integration."""

from __future__ import annotations

import pytest
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from specify_cli.sync.body_queue import BodyUploadTask, OfflineBodyUploadQueue
from specify_cli.sync.namespace import UploadOutcome, UploadStatus

pytestmark = pytest.mark.fast


@pytest.fixture(autouse=True)
def _patch_bg_token_fetch(monkeypatch):
    """Autouse: patch the background-sync token-fetch bridge so tests stay hermetic.

    Individual tests can override by directly monkeypatching the module
    attribute (e.g., ``_make_service(..., auth_token=None, monkeypatch=monkeypatch)``).
    """
    import specify_cli.sync.background as bg_mod

    monkeypatch.setattr(
        bg_mod,
        "_fetch_access_token_sync",
        MagicMock(return_value="token"),
    )
    yield


def _make_task(
    row_id: int = 1,
    artifact_path: str = "spec.md",
    content_hash: str = "abc123",
    retry_count: int = 0,
    next_attempt_at: float = 0.0,
) -> BodyUploadTask:
    return BodyUploadTask(
        row_id=row_id,
        project_uuid="proj-uuid",
        mission_slug="047-feat",
        target_branch="main",
        mission_type="software-dev",
        manifest_version="1",
        artifact_path=artifact_path,
        content_hash=content_hash,
        hash_algorithm="sha256",
        content_body="# Spec\n",
        size_bytes=8,
        retry_count=retry_count,
        next_attempt_at=next_attempt_at,
        created_at=time.time(),
        last_error=None,
    )


def _enqueue_task(
    queue: OfflineBodyUploadQueue,
    artifact_path: str = "spec.md",
    content: str = "# Spec\n",
) -> None:
    """Enqueue a task into the body queue for testing."""
    from specify_cli.sync.namespace import NamespaceRef

    ns = NamespaceRef(
        project_uuid="proj-uuid",
        mission_slug="047-feat",
        target_branch="main",
        mission_type="software-dev",
        manifest_version="1",
    )
    import hashlib

    content_hash = hashlib.sha256(content.encode()).hexdigest()
    queue.enqueue(
        namespace=ns,
        artifact_path=artifact_path,
        content_hash=content_hash,
        content_body=content,
        size_bytes=len(content.encode()),
    )


def _make_service(
    tmp_path: Path,
    auth_token: str | None = "test-token",
) -> MagicMock:
    """Create a BackgroundSyncService with mocked dependencies and real body queue.

    The ``_patch_bg_token_fetch`` autouse fixture seeds ``_fetch_access_token_sync``
    with a ``MagicMock(return_value="token")``. If a test asks for a different
    auth_token, we override that mock's return value on the currently-live
    module attribute.
    """
    from specify_cli.sync.background import BackgroundSyncService
    from specify_cli.sync.queue import OfflineQueue
    import specify_cli.sync.background as bg_mod

    db_path = tmp_path / "queue.db"
    event_queue = OfflineQueue(db_path=db_path)
    body_queue = OfflineBodyUploadQueue(db_path=db_path)

    if auth_token != "test-token":
        # Override the autouse-patched mock return value.
        bg_mod._fetch_access_token_sync.return_value = auth_token

    mock_config = MagicMock()
    mock_config.get_server_url.return_value = "https://test.example.com"

    service = BackgroundSyncService(
        queue=event_queue,
        config=mock_config,
    )
    service._body_queue = body_queue
    return service


# --- Drain ordering ---


class TestDrainOrdering:
    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_events_drain_before_bodies(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Verify event queue drains before body queue in _sync_once()."""
        from specify_cli.sync.batch import BatchSyncResult

        mock_batch.return_value = BatchSyncResult()

        service = _make_service(tmp_path)
        _enqueue_task(service._body_queue, "spec.md", "# Spec\n")

        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.UPLOADED,
            reason="stored",
            content_hash="abc",
        )

        call_order: list[str] = []

        def track_batch(*args, **kwargs):
            call_order.append("event_drain")
            return BatchSyncResult()

        def track_push(*args, **kwargs):
            call_order.append("body_drain")
            return UploadOutcome(
                artifact_path="spec.md",
                status=UploadStatus.UPLOADED,
                reason="stored",
                content_hash="abc",
            )

        mock_batch.side_effect = track_batch
        mock_push.side_effect = track_push

        service._sync_once()

        assert call_order == ["event_drain", "body_drain"]


# --- Body outcome handling ---


class TestBodyOutcomeHandling:
    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_successful_upload_removes_task(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        from specify_cli.sync.batch import BatchSyncResult

        mock_batch.return_value = BatchSyncResult()
        service = _make_service(tmp_path)
        _enqueue_task(service._body_queue, "spec.md")

        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.UPLOADED,
            reason="stored",
            content_hash="abc",
        )

        service._sync_once()

        stats = service._body_queue.get_stats()
        assert stats.total_count == 0

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_already_exists_removes_task(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        from specify_cli.sync.batch import BatchSyncResult

        mock_batch.return_value = BatchSyncResult()
        service = _make_service(tmp_path)
        _enqueue_task(service._body_queue, "spec.md")

        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.ALREADY_EXISTS,
            reason="already_exists",
            content_hash="abc",
        )

        service._sync_once()

        stats = service._body_queue.get_stats()
        assert stats.total_count == 0

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_retryable_failure_keeps_task_with_backoff(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        from specify_cli.sync.batch import BatchSyncResult

        mock_batch.return_value = BatchSyncResult()
        service = _make_service(tmp_path)
        _enqueue_task(service._body_queue, "spec.md")

        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.FAILED,
            reason="connection_error",
            content_hash="abc",
            retryable=True,
        )

        service._sync_once()

        stats = service._body_queue.get_stats()
        assert stats.total_count == 1
        assert stats.max_retry_count == 1

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_permanent_failure_removes_task(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        from specify_cli.sync.batch import BatchSyncResult
        import logging

        mock_batch.return_value = BatchSyncResult()
        service = _make_service(tmp_path)
        _enqueue_task(service._body_queue, "spec.md")

        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.FAILED,
            reason="bad_request: invalid payload",
            content_hash="abc",
            retryable=False,
        )

        with caplog.at_level(logging.WARNING):
            service._sync_once()

        stats = service._body_queue.get_stats()
        assert stats.total_count == 0
        failures = service._body_queue.get_recent_failures()
        assert len(failures) == 1
        assert failures[0].artifact_path == "spec.md"
        assert failures[0].failure_reason == "bad_request: invalid payload"
        assert "Body upload permanent failure" not in caplog.text


# --- Edge cases ---


class TestEdgeCases:
    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_no_auth_token_skips_body_drain(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        from specify_cli.sync.batch import BatchSyncResult

        mock_batch.return_value = BatchSyncResult()
        service = _make_service(tmp_path, auth_token=None)
        _enqueue_task(service._body_queue, "spec.md")

        service._sync_once()

        mock_push.assert_not_called()
        stats = service._body_queue.get_stats()
        assert stats.total_count == 1  # Task still queued

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_empty_queue_no_push_calls(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        from specify_cli.sync.batch import BatchSyncResult

        mock_batch.return_value = BatchSyncResult()
        service = _make_service(tmp_path)

        service._sync_once()

        mock_push.assert_not_called()

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_backoff_respected_tasks_not_drained(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Task with next_attempt_at in the future should not be drained."""
        import sqlite3

        from specify_cli.sync.batch import BatchSyncResult

        mock_batch.return_value = BatchSyncResult()
        service = _make_service(tmp_path)
        _enqueue_task(service._body_queue, "spec.md")

        # Push next_attempt_at far into the future
        conn = sqlite3.connect(service._body_queue.db_path)
        try:
            conn.execute(
                "UPDATE body_upload_queue SET next_attempt_at = ?",
                (time.time() + 9999,),
            )
            conn.commit()
        finally:
            conn.close()

        service._sync_once()

        mock_push.assert_not_called()
        stats = service._body_queue.get_stats()
        assert stats.total_count == 1  # Still queued, not drained

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_event_sync_exception_skips_body_drain(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        service = _make_service(tmp_path)
        _enqueue_task(service._body_queue, "spec.md")
        mock_batch.side_effect = RuntimeError("server unavailable")

        service._sync_once()

        mock_push.assert_not_called()
        stats = service._body_queue.get_stats()
        assert stats.total_count == 1

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_stale_tasks_removed(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Tasks exceeding max retry count should be removed."""
        import sqlite3

        from specify_cli.sync.batch import BatchSyncResult

        mock_batch.return_value = BatchSyncResult()
        service = _make_service(tmp_path)
        _enqueue_task(service._body_queue, "spec.md")

        # Set retry_count to 21 (exceeds max of 20)
        conn = sqlite3.connect(service._body_queue.db_path)
        try:
            conn.execute("UPDATE body_upload_queue SET retry_count = 21")
            conn.commit()
        finally:
            conn.close()

        service._sync_once()

        stats = service._body_queue.get_stats()
        assert stats.total_count == 0  # Removed as stale

    def test_no_body_queue_skips_drain(self, tmp_path: Path) -> None:
        """When _body_queue is None, drain is skipped gracefully."""
        from specify_cli.sync.background import BackgroundSyncService
        from specify_cli.sync.queue import OfflineQueue

        db_path = tmp_path / "queue.db"
        service = BackgroundSyncService(
            queue=OfflineQueue(db_path=db_path),
            config=MagicMock(),
        )
        # _body_queue is None by default — this should not raise
        with (
            patch(
                "specify_cli.sync.background.is_saas_sync_enabled",
                return_value=True,
            ),
            patch("specify_cli.sync.background.batch_sync") as mock_batch,
        ):
            from specify_cli.sync.batch import BatchSyncResult

            mock_batch.return_value = BatchSyncResult()
            service._sync_once()  # No error


# --- Body queue size() ---


class TestBodyQueueSize:
    def test_size_returns_zero_for_empty_queue(self, tmp_path: Path) -> None:
        queue = OfflineBodyUploadQueue(db_path=tmp_path / "queue.db")
        assert queue.size() == 0

    def test_size_returns_correct_count(self, tmp_path: Path) -> None:
        queue = OfflineBodyUploadQueue(db_path=tmp_path / "queue.db")
        _enqueue_task(queue, "spec.md", "# Spec\n")
        _enqueue_task(queue, "plan.md", "# Plan\n")
        assert queue.size() == 2


# --- Timer triggers with body queue ---


class TestTimerBodyQueue:
    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_timer_triggers_when_only_body_queue_has_tasks(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Timer should trigger sync when event queue is empty but body queue has work."""
        from specify_cli.sync.batch import BatchSyncResult

        mock_batch.return_value = BatchSyncResult()
        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.UPLOADED,
            reason="stored",
            content_hash="abc",
        )

        service = _make_service(tmp_path)
        # Event queue is empty, body queue has a task
        _enqueue_task(service._body_queue, "spec.md", "# Spec\n")
        assert service.queue.size() == 0
        assert service._body_queue.size() == 1

        service._running = True
        service._on_timer()

        # Should have called batch_sync (via _perform_sync)
        mock_batch.assert_called_once()

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    def test_timer_skips_when_both_queues_empty(
        self,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Timer should skip sync when both queues are empty."""
        service = _make_service(tmp_path)
        assert service.queue.size() == 0
        assert service._body_queue.size() == 0

        service._running = True
        with patch.object(service, "_perform_sync") as mock_perform:
            service._on_timer()
            mock_perform.assert_not_called()


# --- sync_now() drains body queue ---


class TestSyncNowBody:
    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.sync_all_queued_events")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_sync_now_drains_body_queue(
        self,
        mock_push: MagicMock,
        mock_sync_all: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        from specify_cli.sync.batch import BatchSyncResult

        mock_sync_all.return_value = BatchSyncResult()
        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.UPLOADED,
            reason="stored",
            content_hash="abc",
        )

        service = _make_service(tmp_path)
        _enqueue_task(service._body_queue, "spec.md", "# Spec\n")

        service.sync_now()

        mock_push.assert_called_once()
        assert service._body_queue.size() == 0


# --- stop() best-effort includes body queue ---


class TestStopBody:
    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.background.batch_sync")
    @patch("specify_cli.sync.body_transport.push_content")
    def test_stop_best_effort_includes_body_queue(
        self,
        mock_push: MagicMock,
        mock_batch: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        from specify_cli.sync.batch import BatchSyncResult

        mock_batch.return_value = BatchSyncResult()
        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.UPLOADED,
            reason="stored",
            content_hash="abc",
        )

        service = _make_service(tmp_path)
        _enqueue_task(service._body_queue, "spec.md", "# Spec\n")
        service._running = True

        service.stop()

        # Body queue should have been attempted
        mock_batch.assert_called()


# --- Runtime lifecycle ---


class TestRuntimeLifecycle:
    @patch("specify_cli.sync.runtime.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.runtime._auto_start_enabled", return_value=True)
    @patch("specify_cli.sync.background.get_sync_service")
    def test_start_creates_body_queue(
        self,
        mock_get_service: MagicMock,
        mock_auto_start: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        from specify_cli.sync.queue import OfflineQueue
        from specify_cli.sync.runtime import SyncRuntime

        db_path = tmp_path / "queue.db"
        mock_service = MagicMock()
        mock_service.queue = OfflineQueue(db_path=db_path)
        mock_get_service.return_value = mock_service

        runtime = SyncRuntime()
        runtime.start()

        assert runtime.body_queue is not None
        assert runtime.body_queue.db_path == db_path
        assert mock_service._body_queue is runtime.body_queue

    @patch("specify_cli.sync.runtime.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.runtime._auto_start_enabled", return_value=True)
    @patch("specify_cli.sync.background.get_sync_service")
    def test_stop_clears_body_queue(
        self,
        mock_get_service: MagicMock,
        mock_auto_start: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        from specify_cli.sync.queue import OfflineQueue
        from specify_cli.sync.runtime import SyncRuntime

        db_path = tmp_path / "queue.db"
        mock_service = MagicMock()
        mock_service.queue = OfflineQueue(db_path=db_path)
        mock_get_service.return_value = mock_service

        runtime = SyncRuntime()
        runtime.start()
        assert runtime.body_queue is not None

        runtime.stop()
        assert runtime.body_queue is None

    @patch("specify_cli.sync.runtime.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.runtime._auto_start_enabled", return_value=True)
    @patch("specify_cli.sync.background.get_sync_service")
    def test_shared_db_path(
        self,
        mock_get_service: MagicMock,
        mock_auto_start: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Body queue and event queue must share the same DB file."""
        from specify_cli.sync.queue import OfflineQueue
        from specify_cli.sync.runtime import SyncRuntime

        db_path = tmp_path / "queue.db"
        mock_service = MagicMock()
        mock_service.queue = OfflineQueue(db_path=db_path)
        mock_get_service.return_value = mock_service

        runtime = SyncRuntime()
        runtime.start()

        assert runtime.body_queue is not None
        assert runtime.body_queue.db_path == mock_service.queue.db_path
