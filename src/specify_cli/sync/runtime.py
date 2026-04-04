"""SyncRuntime: Lazy singleton managing WebSocket and background sync.

Provides a single entry point for background sync lifecycle management.
The runtime starts on first get_runtime() call (lazy initialization) and
stops cleanly on process exit via atexit handler.

Usage:
    from specify_cli.sync.runtime import get_runtime

    # Runtime auto-starts on first access
    runtime = get_runtime()

    # Attach emitter for WebSocket wiring
    runtime.attach_emitter(emitter)

    # Explicit shutdown (also happens via atexit)
    runtime.stop()
"""

from __future__ import annotations

import atexit
import asyncio
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from specify_cli.core.paths import locate_project_root

from .feature_flags import is_saas_sync_enabled, saas_sync_disabled_message

if TYPE_CHECKING:
    from .background import BackgroundSyncService
    from .body_queue import OfflineBodyUploadQueue
    from .client import WebSocketClient
    from .emitter import EventEmitter

logger = logging.getLogger(__name__)


def _safe_queue_size(queue_obj: object) -> int:
    """Best-effort queue size lookup that tolerates mocked test doubles."""
    try:
        raw = queue_obj.size()
    except Exception:
        return 0

    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _auto_start_enabled() -> bool:
    """Check if sync auto-start is enabled via config.

    Reads .kittify/config.yaml for sync.auto_start setting.
    Defaults to True if config is missing or invalid.
    """
    project_root = locate_project_root(Path.cwd()) or Path.cwd()
    config_path = project_root / ".kittify" / "config.yaml"
    if not config_path.exists():
        return True

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        if config is None:
            return True
        sync_config = config.get("sync", {})
        if sync_config is None:
            return True
        auto_start = sync_config.get("auto_start", True)
        # Handle explicit False only
        return auto_start is not False
    except Exception as e:
        logger.debug(f"Could not read sync config: {e}")
        return True


@dataclass
class SyncRuntime:
    """Background sync runtime managing WebSocket and queue.

    The runtime coordinates:
    - BackgroundSyncService: Periodic queue flush
    - WebSocketClient: Real-time event streaming (if authenticated)
    - EventEmitter wiring: Connects WS client to emitter when available

    Thread-safe and idempotent: start() can be called multiple times.
    """

    background_service: BackgroundSyncService | None = field(default=None, repr=False)
    ws_client: WebSocketClient | None = field(default=None, repr=False)
    emitter: EventEmitter | None = field(default=None, repr=False)
    body_queue: OfflineBodyUploadQueue | None = field(default=None, repr=False)
    _async_loop: asyncio.AbstractEventLoop | None = field(default=None, repr=False)
    _async_loop_thread: threading.Thread | None = field(default=None, repr=False)
    started: bool = False

    def start(self) -> None:
        """Start background services (idempotent).

        - Starts BackgroundSyncService for queue processing
        - Connects WebSocket if authenticated
        - Safe to call multiple times
        """
        if self.started:
            return

        if not is_saas_sync_enabled():
            logger.info("%s SyncRuntime not started.", saas_sync_disabled_message())
            return

        # Check config for opt-out (project-level)
        if not _auto_start_enabled():
            logger.info("Sync auto-start disabled via config")
            return

        # Start background service (use existing singleton)
        from .background import get_sync_service
        self.background_service = get_sync_service()

        # Create body queue sharing same DB as event queue (C-001)
        from .body_queue import OfflineBodyUploadQueue
        self.body_queue = OfflineBodyUploadQueue(
            db_path=self.background_service.queue.db_path,
        )
        self.background_service._body_queue = self.body_queue
        if _safe_queue_size(self.background_service.queue) > 0 or _safe_queue_size(self.body_queue) > 0:
            self.background_service.wake()

        self._ensure_async_loop()

        # Connect WebSocket if authenticated
        self._connect_websocket_if_authenticated()

        self.started = True
        logger.debug("SyncRuntime started")

    def _connect_websocket_if_authenticated(self) -> None:
        """Attempt WebSocket connection if user is authenticated."""
        from .auth import AuthClient
        from .config import SyncConfig

        auth = AuthClient()
        config = SyncConfig()

        if auth.is_authenticated():
            try:
                from .client import WebSocketClient
                self.ws_client = WebSocketClient(
                    server_url=config.get_server_url(),
                    auth_client=auth,
                )
                self._ensure_async_loop()
                if self._async_loop is None:
                    logger.info("Async loop unavailable; events will be queued for batch sync")
                    return
                future = asyncio.run_coroutine_threadsafe(self.ws_client.connect(), self._async_loop)
                future.add_done_callback(self._log_async_future_error)

                # Wire WebSocket to emitter if already attached
                if self.emitter is not None:
                    self.emitter.ws_client = self.ws_client
                logger.debug("WebSocket connect scheduled")
            except Exception as e:
                logger.warning(f"WebSocket connection failed: {e}")
                logger.info("Events will be queued for batch sync")
        else:
            logger.info("Not authenticated; events queued locally")
            logger.info("Run 'spec-kitty auth login' to enable real-time sync")

    def _ensure_async_loop(self) -> None:
        """Create a dedicated asyncio loop for daemon-owned WebSocket transport."""
        if self._async_loop is not None and self._async_loop_thread is not None and self._async_loop_thread.is_alive():
            return

        loop = asyncio.new_event_loop()

        def _run_loop() -> None:
            asyncio.set_event_loop(loop)
            loop.run_forever()

        thread = threading.Thread(
            target=_run_loop,
            name="spec-kitty-sync-async-loop",
            daemon=True,
        )
        thread.start()
        self._async_loop = loop
        self._async_loop_thread = thread

    def _log_async_future_error(self, future: object) -> None:
        """Log exceptions from asyncio.run_coroutine_threadsafe futures."""
        try:
            future.result()
        except Exception as exc:
            logger.debug("Async sync task failed: %s", exc)

    def get_websocket_status(self) -> str:
        """Expose current WebSocket connection status."""
        if self.ws_client is None:
            return "Offline"
        return self.ws_client.get_status()

    def publish_event(self, event: dict[str, object]) -> bool:
        """Best-effort real-time event publish via the daemon-owned WebSocket."""
        if not self.started:
            self.start()

        if self.ws_client is None or self._async_loop is None:
            self._connect_websocket_if_authenticated()
            return False

        if not self.ws_client.connected:
            self._connect_websocket_if_authenticated()
            return False

        try:
            future = asyncio.run_coroutine_threadsafe(self.ws_client.send_event(event), self._async_loop)
            future.result(timeout=2.0)
            return True
        except Exception as exc:
            logger.debug("WebSocket publish failed: %s", exc)
            return False

    def attach_emitter(self, emitter: EventEmitter) -> None:
        """Attach emitter so WS client can be injected.

        Called by get_emitter() after creating the EventEmitter instance.
        If WebSocket is already connected, wires it to the emitter.
        """
        self.emitter = emitter
        if self.ws_client is not None:
            self.emitter.ws_client = self.ws_client

    def stop(self) -> None:
        """Stop background services gracefully.

        Disconnects WebSocket and stops background sync service.
        Safe to call multiple times or if not started.
        """
        if not self.started:
            return

        if self.ws_client:
            try:
                if self._async_loop is not None:
                    future = asyncio.run_coroutine_threadsafe(self.ws_client.disconnect(), self._async_loop)
                    future.result(timeout=5.0)
            except Exception:
                pass
            self.ws_client = None

        if self.background_service:
            self.background_service.stop()
            self.background_service = None

        if self._async_loop is not None:
            try:
                self._async_loop.call_soon_threadsafe(self._async_loop.stop)
            except Exception:
                pass
        if self._async_loop_thread is not None and self._async_loop_thread.is_alive():
            self._async_loop_thread.join(timeout=5.0)
        if self._async_loop is not None:
            try:
                self._async_loop.close()
            except Exception:
                pass
        self._async_loop = None
        self._async_loop_thread = None
        self.body_queue = None
        self.started = False
        logger.debug("SyncRuntime stopped")


# ── Singleton accessor ────────────────────────────────────────────

_runtime: SyncRuntime | None = None
_runtime_lock = threading.Lock()


def get_runtime() -> SyncRuntime:
    """Get or create the singleton SyncRuntime instance.

    Thread-safe via double-checked locking pattern.
    Runtime starts on first access (lazy initialization).
    """
    global _runtime
    if _runtime is None:
        with _runtime_lock:
            if _runtime is None:
                _runtime = SyncRuntime()
                _runtime.start()
    return _runtime


def reset_runtime() -> None:
    """Reset the singleton (for testing only)."""
    global _runtime
    with _runtime_lock:
        if _runtime is not None:
            _runtime.stop()
        _runtime = None


def _shutdown_runtime() -> None:
    """atexit handler for graceful shutdown."""
    global _runtime
    if _runtime is not None:
        _runtime.stop()


atexit.register(_shutdown_runtime)
