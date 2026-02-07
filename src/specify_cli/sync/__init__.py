"""
Sync module for spec-kitty CLI.

Provides real-time synchronization with spec-kitty-saas server via:
- WebSocket client for event streaming
- Offline queue for resilience
- JWT authentication
- Batch sync for offline queue replay
- Event emission with Lamport clock ordering

Heavy dependencies (requests, websockets) are lazily imported via __getattr__
so that lightweight imports like ``from specify_cli.sync.events import ...``
do not pull in optional packages.
"""

from .clock import LamportClock, generate_node_id
from .events import (
    get_emitter,
    reset_emitter,
    emit_wp_status_changed,
    emit_wp_created,
    emit_wp_assigned,
    emit_feature_created,
    emit_feature_completed,
    emit_history_added,
    emit_error_logged,
    emit_dependency_resolved,
)
from .queue import OfflineQueue

# Lazy-loaded names (require 'requests' or 'websockets' at runtime)
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "AuthClient": (".auth", "AuthClient"),
    "AuthenticationError": (".auth", "AuthenticationError"),
    "CredentialStore": (".auth", "CredentialStore"),
    "BatchSyncResult": (".batch", "BatchSyncResult"),
    "batch_sync": (".batch", "batch_sync"),
    "sync_all_queued_events": (".batch", "sync_all_queued_events"),
    "WebSocketClient": (".client", "WebSocketClient"),
    "SyncConfig": (".config", "SyncConfig"),
    "BackgroundSyncService": (".background", "BackgroundSyncService"),
    "get_sync_service": (".background", "get_sync_service"),
    "reset_sync_service": (".background", "reset_sync_service"),
    "SyncRuntime": (".runtime", "SyncRuntime"),
    "get_runtime": (".runtime", "get_runtime"),
    "reset_runtime": (".runtime", "reset_runtime"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr = _LAZY_IMPORTS[name]
        import importlib

        mod = importlib.import_module(module_path, __name__)
        return getattr(mod, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AuthClient",
    "AuthenticationError",
    "CredentialStore",
    "WebSocketClient",
    "SyncConfig",
    "OfflineQueue",
    "batch_sync",
    "sync_all_queued_events",
    "BatchSyncResult",
    "LamportClock",
    "generate_node_id",
    "get_emitter",
    "reset_emitter",
    "emit_wp_status_changed",
    "emit_wp_created",
    "emit_wp_assigned",
    "emit_feature_created",
    "emit_feature_completed",
    "emit_history_added",
    "emit_error_logged",
    "emit_dependency_resolved",
    "BackgroundSyncService",
    "get_sync_service",
    "reset_sync_service",
    "SyncRuntime",
    "get_runtime",
    "reset_runtime",
]
