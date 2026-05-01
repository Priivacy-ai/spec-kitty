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
import contextlib
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from specify_cli.core.paths import locate_project_root
from specify_cli.diagnostics import invocation_succeeded

from .feature_flags import is_saas_sync_enabled, saas_sync_disabled_message
from .routing import is_sync_enabled_for_checkout

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

    Local checkout overrides win. If none is present, the remembered
    repository default from ``~/.spec-kitty/config.toml`` is used.
    """
    project_root = locate_project_root(Path.cwd())
    if project_root is None:
        return True

    project_setting = _read_project_auto_start(project_root)
    if project_setting is not None:
        return project_setting

    try:
        return is_sync_enabled_for_checkout(project_root)
    except Exception as e:
        logger.debug(f"Could not resolve sync routing config: {e}")
        return True


def _read_project_auto_start(project_root: Path) -> bool | None:
    """Read the legacy project-local ``sync.auto_start`` flag when present."""
    config_path = project_root / ".kittify" / "config.yaml"
    if not config_path.exists():
        return None

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.debug("Could not read project sync config from %s: %s", config_path, exc)
        return None

    if not isinstance(raw, dict):
        return None

    sync_section = raw.get("sync")
    if not isinstance(sync_section, dict):
        return None

    auto_start = sync_section.get("auto_start")
    return auto_start if isinstance(auto_start, bool) else None


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
    _build_registered: bool = False
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
        from specify_cli.auth import get_token_manager

        tm = get_token_manager()

        if tm.is_authenticated:
            try:
                from .client import WebSocketClient

                project_identity = self._attached_project_identity()
                # Server URL comes from SPEC_KITTY_SAAS_URL via WebSocketClient internals;
                # runtime does not hardcode host/scheme (see decision D-5).
                self.ws_client = WebSocketClient(project_identity=project_identity)
                self._ensure_async_loop()
                if self._async_loop is None:
                    logger.info("Async loop unavailable; events will be queued for batch sync")
                    return
                future = asyncio.run_coroutine_threadsafe(self.ws_client.connect(), self._async_loop)
                future.add_done_callback(self._log_async_future_error)

                # Wire WebSocket to emitter if already attached
                if self.emitter is not None:
                    self.emitter.ws_client = self.ws_client
                    if project_identity is not None:
                        self.ws_client._project_identity = project_identity
                logger.debug("WebSocket connect scheduled")
            except Exception as e:
                logger.warning(f"WebSocket connection failed: {e}")
                logger.info("Events will be queued for batch sync")
        else:
            logger.info("Not authenticated; events queued locally")
            logger.info("Run 'spec-kitty auth login' to enable real-time sync")

    def _attached_project_identity(self) -> object | None:
        """Return the attached emitter's project identity when it is usable."""
        if self.emitter is None:
            return None

        try:
            identity = self.emitter._get_identity()
        except Exception as exc:
            logger.debug("Could not resolve project identity from emitter: %s", exc)
            return None

        build_id = getattr(identity, "build_id", None)
        if not isinstance(build_id, str) or not build_id:
            return None
        return identity

    def _attached_repo_slug(self) -> str | None:
        """Return the repo slug from the attached emitter, if available."""
        if self.emitter is None:
            return None
        try:
            git_meta = self.emitter._get_git_metadata()
        except Exception as exc:
            logger.debug("Could not resolve git metadata from emitter: %s", exc)
            return None
        repo_slug = getattr(git_meta, "repo_slug", None)
        return repo_slug if isinstance(repo_slug, str) and repo_slug else None

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
        identity = self._attached_project_identity()
        if self.ws_client is not None:
            self.emitter.ws_client = self.ws_client
            if identity is not None:
                self.ws_client._project_identity = identity

        if not self._build_registered and identity is not None and getattr(identity, "is_complete", False) is True and self._attached_repo_slug() is not None:
            event = emitter.emit_build_registered()
            if event is not None:
                self._build_registered = True
                if self.background_service is not None:
                    self.background_service.wake()

    def stop(self) -> None:
        """Stop background services gracefully.

        Disconnects WebSocket and stops background sync service.
        Safe to call multiple times or if not started.

        FR-008: When ``invocation_succeeded()`` returns True, any warnings
        emitted by the inner shutdown path (background sync, websocket
        teardown) should be downgraded so they don't paint red over a
        clean stdout JSON payload (#735). The ``BackgroundSyncService.stop``
        path consults the same flag.
        """
        if not self.started:
            return

        succeeded = invocation_succeeded()

        if self.ws_client:
            try:
                if self._async_loop is not None:
                    future = asyncio.run_coroutine_threadsafe(self.ws_client.disconnect(), self._async_loop)
                    future.result(timeout=5.0)
            except Exception as exc:
                if succeeded:
                    logger.debug(
                        "WebSocket disconnect failed during post-success shutdown: %s",
                        exc,
                    )
                else:
                    logger.debug("WebSocket disconnect failed during shutdown: %s", exc)
            self.ws_client = None

        if self.background_service:
            self.background_service.stop()
            self.background_service = None

        if self._async_loop is not None:
            with contextlib.suppress(Exception):
                self._async_loop.call_soon_threadsafe(self._async_loop.stop)
        if self._async_loop_thread is not None and self._async_loop_thread.is_alive():
            self._async_loop_thread.join(timeout=5.0)
        if self._async_loop is not None:
            with contextlib.suppress(Exception):
                self._async_loop.close()
        self._async_loop = None
        self._async_loop_thread = None
        self.body_queue = None
        self._build_registered = False
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
