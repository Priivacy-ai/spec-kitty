"""
Sync module for spec-kitty CLI.

Provides real-time synchronization with spec-kitty-saas server via:
- WebSocket client for event streaming
- Offline queue for resilience
- JWT authentication
- Batch sync for offline queue replay
- Event emission with Lamport clock ordering
"""

from .auth import AuthClient, AuthenticationError, CredentialStore
from .batch import BatchSyncResult, batch_sync, sync_all_queued_events
from .client import WebSocketClient
from .config import SyncConfig
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
from .background import BackgroundSyncService, get_sync_service, reset_sync_service
from .queue import OfflineQueue

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
]
