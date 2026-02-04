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
from typing import Optional

from .auth import AuthClient
from .batch import BatchSyncResult, batch_sync
from .config import SyncConfig
from .queue import OfflineQueue

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
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def start(self) -> None:
        """Start the background sync service."""
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
        if self.queue.size() > 0:
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
        """Trigger an immediate sync, bypassing the timer."""
        return self._perform_sync()

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
        if self.queue.size() > 0:
            self._perform_sync()
        self._schedule_next_sync()

    def _perform_sync(self) -> BatchSyncResult:
        """Execute a single batch sync operation.

        On success resets backoff; on failure doubles backoff (capped at 30s).
        """
        access_token = self.auth.get_access_token()
        if access_token is None:
            logger.warning("Not authenticated, skipping sync")
            return BatchSyncResult()

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
            return result
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
            return result


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
                atexit.register(_service.stop)
    return _service


def reset_sync_service() -> None:
    """Reset the singleton (for testing only)."""
    global _service
    with _service_lock:
        if _service is not None:
            _service.stop()
        _service = None
