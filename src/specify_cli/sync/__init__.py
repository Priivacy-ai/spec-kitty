"""
Sync module for spec-kitty CLI.

Provides real-time synchronization with spec-kitty-saas server via:
- WebSocket client for event streaming
- Offline queue for resilience
- JWT authentication
- Batch sync for offline queue replay
"""

from .auth import AuthClient, AuthenticationError, CredentialStore
from .batch import BatchSyncResult, batch_sync, sync_all_queued_events
from .client import WebSocketClient
from .config import SyncConfig
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
]
