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
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from .background import BackgroundSyncService
    from .client import WebSocketClient
    from .emitter import EventEmitter

logger = logging.getLogger(__name__)


def _auto_start_enabled() -> bool:
    """Check if sync auto-start is enabled via config.

    Reads .kittify/config.yaml for sync.auto_start setting.
    Defaults to True if config is missing or invalid.
    """
    config_path = Path.cwd() / ".kittify" / "config.yaml"
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
    started: bool = False

    def start(self) -> None:
        """Start background services (idempotent).

        - Starts BackgroundSyncService for queue processing
        - Connects WebSocket if authenticated
        - Safe to call multiple times
        """
        if self.started:
            return

        # Check config for opt-out (project-level)
        if not _auto_start_enabled():
            logger.info("Sync auto-start disabled via config")
            return

        # Start background service (use existing singleton)
        from .background import get_sync_service
        self.background_service = get_sync_service()

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
                import asyncio
                try:
                    asyncio.get_running_loop()
                    # Running event loop available: connect non-blocking.
                    asyncio.ensure_future(self.ws_client.connect())
                except RuntimeError:
                    # Synchronous CLI context: skip auto WebSocket connect.
                    # Creating a temporary event loop here spawns a background
                    # listener task that outlives the loop and triggers noisy
                    # "Task was destroyed but it is pending!" warnings.
                    logger.debug(
                        "No running event loop; skipping auto WebSocket connect "
                        "in sync context"
                    )
                    logger.info("Events will be queued for batch sync")
                    return

                # Wire WebSocket to emitter if already attached
                if self.emitter is not None:
                    self.emitter.ws_client = self.ws_client
                logger.debug("WebSocket connected")
            except Exception as e:
                logger.warning(f"WebSocket connection failed: {e}")
                logger.info("Events will be queued for batch sync")
        else:
            logger.info("Not authenticated; events queued locally")
            logger.info("Run 'spec-kitty auth login' to enable real-time sync")

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
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    asyncio.ensure_future(self.ws_client.disconnect())
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    try:
                        loop.run_until_complete(self.ws_client.disconnect())
                    finally:
                        loop.close()
            except Exception:
                pass
            self.ws_client = None

        if self.background_service:
            self.background_service.stop()
            self.background_service = None

        self.started = False
        logger.debug("SyncRuntime stopped")


# ── Singleton accessor ────────────────────────────────────────────

_runtime: SyncRuntime | None = None


def get_runtime() -> SyncRuntime:
    """Get or create the singleton SyncRuntime instance.

    Thread-safe via module-level singleton pattern.
    Runtime starts on first access (lazy initialization).
    """
    global _runtime
    if _runtime is None:
        _runtime = SyncRuntime()
        _runtime.start()
    return _runtime


def reset_runtime() -> None:
    """Reset the singleton (for testing only)."""
    global _runtime
    if _runtime is not None:
        _runtime.stop()
    _runtime = None


def _shutdown_runtime() -> None:
    """atexit handler for graceful shutdown."""
    global _runtime
    if _runtime is not None:
        _runtime.stop()


atexit.register(_shutdown_runtime)
