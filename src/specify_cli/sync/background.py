"""Background sync service for periodic queue flush.

Provides a daemon-threaded service that periodically drains the offline
event queue and syncs to the server, with exponential backoff on failures
and graceful shutdown via atexit.
"""

from __future__ import annotations

import atexit
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from .auth import AuthClient
from .batch import BatchSyncResult, batch_sync, sync_all_queued_events
from .config import SyncConfig
from .feature_flags import is_saas_sync_enabled, saas_sync_disabled_message
from .queue import OfflineQueue

if TYPE_CHECKING:
    from .body_queue import BodyUploadTask, OfflineBodyUploadQueue
    from .namespace import UploadOutcome

logger = logging.getLogger(__name__)


@dataclass
class BackgroundSyncService:
    """Manages periodic background sync of the offline event queue."""

    queue: OfflineQueue
    auth: AuthClient
    config: SyncConfig
    sync_interval_seconds: float = 300.0  # 5 minutes default
    _timer: Optional[threading.Timer] = field(default=None, init=False, repr=False)
    _running: bool = field(default=False, init=False, repr=False)
    _backoff_seconds: float = field(default=0.5, init=False, repr=False)
    _last_sync: Optional[datetime] = field(default=None, init=False, repr=False)
    _consecutive_failures: int = field(default=0, init=False, repr=False)
    _body_queue: Optional[OfflineBodyUploadQueue] = field(default=None, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def start(self) -> None:
        """Start the background sync service."""
        if not is_saas_sync_enabled():
            logger.info("%s Background sync service will remain stopped.", saas_sync_disabled_message())
            return

        with self._lock:
            if self._running:
                return
            self._running = True
        self._schedule_next_sync()
        logger.debug("Background sync service started (interval=%ss)", self.sync_interval_seconds)

    def stop(self) -> None:
        """Stop the background sync service gracefully.

        Cancels the pending timer and attempts a best-effort final sync
        if there are queued events.
        """
        with self._lock:
            self._running = False
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

        # Best-effort final sync
        body_queue_has_work = (
            self._body_queue is not None and self._body_queue.size() > 0
        )
        if self.queue.size() > 0 or body_queue_has_work:
            try:
                self._perform_sync()
            except Exception:
                pass
        logger.debug("Background sync service stopped")

    @property
    def last_sync(self) -> Optional[datetime]:
        return self._last_sync

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    @property
    def is_running(self) -> bool:
        return self._running

    def sync_now(self) -> BatchSyncResult:
        """Trigger an immediate sync, draining all queued events.

        Unlike the periodic timer (which syncs a single batch), this
        loops until the queue is empty or all remaining events have
        exceeded their retry limit.
        """
        return self._perform_full_sync()

    # ── Internal ──────────────────────────────────────────────────

    def _schedule_next_sync(self) -> None:
        """Schedule the next sync tick based on interval or backoff."""
        if not self._running:
            return

        if self._consecutive_failures > 0:
            interval = min(self._backoff_seconds, 30.0)
        else:
            interval = self.sync_interval_seconds

        self._timer = threading.Timer(interval, self._on_timer)
        self._timer.daemon = True  # Don't block CLI exit
        self._timer.start()

    def _on_timer(self) -> None:
        """Timer callback: sync if queue is non-empty, then reschedule."""
        if not self._running:
            return
        body_queue_has_work = (
            self._body_queue is not None and self._body_queue.size() > 0
        )
        if self.queue.size() > 0 or body_queue_has_work:
            self._perform_sync()
        self._schedule_next_sync()

    def _perform_sync(self) -> BatchSyncResult:
        """Execute a single batch sync operation (up to 1000 events).

        Thread-safe: acquires _lock so timer callbacks and sync_now()
        cannot overlap.

        On success resets backoff; on failure doubles backoff (capped at 30s).
        """
        with self._lock:
            return self._sync_once()

    def _perform_full_sync(self) -> BatchSyncResult:
        """Drain the entire queue across multiple batches.

        Thread-safe: holds _lock for the full duration so background
        timer ticks are serialised.
        """
        if not is_saas_sync_enabled():
            logger.info("%s Full sync skipped.", saas_sync_disabled_message())
            result = BatchSyncResult()
            result.error_messages.append(saas_sync_disabled_message())
            return result

        with self._lock:
            access_token = self.auth.get_access_token()
            if access_token is None:
                logger.warning("Not authenticated, skipping sync")
                return BatchSyncResult()

            try:
                result = sync_all_queued_events(
                    queue=self.queue,
                    auth_token=access_token,
                    server_url=self.config.get_server_url(),
                    batch_size=1000,
                    show_progress=False,
                )
                # Drain body upload queue after events (FR-007)
                if self._body_queue is not None:
                    self._drain_body_queue()
                self._consecutive_failures = 0
                self._backoff_seconds = 0.5
                self._last_sync = datetime.now(timezone.utc)
                return result
            except Exception as exc:
                self._consecutive_failures += 1
                self._backoff_seconds = min(self._backoff_seconds * 2, 30.0)
                logger.warning(
                    "Full sync failed (attempt %d, next backoff %.1fs): %s",
                    self._consecutive_failures,
                    self._backoff_seconds,
                    exc,
                )
                result = BatchSyncResult()
                result.error_count = 1
                result.error_messages.append(str(exc))
                return result

    def _sync_once(self) -> BatchSyncResult:
        """Internal: single-batch sync (caller must hold _lock).

        Drain ordering: events first, then body uploads (Design Decision #5).
        """
        if not is_saas_sync_enabled():
            logger.info("%s Single-batch sync skipped.", saas_sync_disabled_message())
            result = BatchSyncResult()
            result.error_messages.append(saas_sync_disabled_message())
            return result

        access_token = self.auth.get_access_token()
        if access_token is None:
            logger.warning("Not authenticated, skipping sync")
            return BatchSyncResult()

        event_sync_succeeded = False
        try:
            result = batch_sync(
                queue=self.queue,
                auth_token=access_token,
                server_url=self.config.get_server_url(),
                limit=1000,
                show_progress=False,
            )
            # Success: reset backoff
            self._consecutive_failures = 0
            self._backoff_seconds = 0.5
            self._last_sync = datetime.now(timezone.utc)
            event_sync_succeeded = True
        except Exception as exc:
            self._consecutive_failures += 1
            self._backoff_seconds = min(self._backoff_seconds * 2, 30.0)
            logger.warning(
                "Sync failed (attempt %d, next backoff %.1fs): %s",
                self._consecutive_failures,
                self._backoff_seconds,
                exc,
            )
            result = BatchSyncResult()
            result.error_count = 1
            result.error_messages.append(str(exc))

        # Drain body upload queue after event queue (FR-007, Design Decision #5)
        if event_sync_succeeded and self._body_queue is not None:
            self._drain_body_queue()

        return result

    def _drain_body_queue(self) -> None:
        """Drain body upload queue, processing tasks one at a time.

        Backoff progression (NFR-003):
        retry 0 → 1s, retry 1 → 2s, retry 2 → 4s, retry 3 → 8s,
        retry 4 → 16s, retry 5 → 32s, retry 6 → 64s, retry 7 → 128s,
        retry 8 → 256s, retry 9+ → 300s (5 min cap)
        """
        from .body_transport import push_content

        assert self._body_queue is not None

        # Remove stale tasks that exceeded max retries (prevent unbounded growth)
        removed = self._body_queue.remove_stale(max_retry_count=20)
        if removed > 0:
            logger.info("Removed %d stale body upload tasks", removed)

        access_token = self.auth.get_access_token()
        if access_token is None:
            logger.debug("No auth token available, skipping body queue drain")
            return

        tasks = self._body_queue.drain(limit=50)
        if not tasks:
            return

        server_url = self.config.get_server_url()
        for task in tasks:
            outcome = push_content(task, access_token, server_url)
            self._handle_body_outcome(task, outcome)

    def _handle_body_outcome(
        self, task: BodyUploadTask, outcome: UploadOutcome,
    ) -> None:
        """Update queue based on upload outcome."""
        from .namespace import UploadStatus

        assert self._body_queue is not None

        if outcome.status == UploadStatus.UPLOADED:
            self._body_queue.mark_uploaded(task.row_id)
            logger.debug("Body uploaded: %s", outcome)
        elif outcome.status == UploadStatus.ALREADY_EXISTS:
            self._body_queue.mark_already_exists(task.row_id)
            logger.debug("Body already exists: %s", outcome)
        elif outcome.status == UploadStatus.FAILED and outcome.retryable:
            self._body_queue.mark_failed_retryable(task.row_id, outcome.reason)
            logger.debug("Body upload retryable failure: %s", outcome)
        elif outcome.status == UploadStatus.FAILED and not outcome.retryable:
            self._body_queue.mark_failed_permanent(task.row_id, outcome.reason)
            logger.warning("Body upload permanent failure: %s", outcome)
        else:
            logger.warning("Unexpected body outcome: %s", outcome)


# ── Singleton accessor ────────────────────────────────────────────

_service: Optional[BackgroundSyncService] = None
_service_lock = threading.Lock()


def get_sync_service() -> BackgroundSyncService:
    """Get or create the singleton BackgroundSyncService.

    Registers an atexit handler so the service stops cleanly when the
    process exits.
    """
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = BackgroundSyncService(
                    queue=OfflineQueue(),
                    auth=AuthClient(),
                    config=SyncConfig(),
                )
                if is_saas_sync_enabled():
                    _service.start()
                else:
                    logger.info("%s Service created without auto-start.", saas_sync_disabled_message())
                atexit.register(_service.stop)
    return _service


def reset_sync_service() -> None:
    """Reset the singleton (for testing only)."""
    global _service
    with _service_lock:
        if _service is not None:
            _service.stop()
        _service = None
