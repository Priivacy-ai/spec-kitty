"""
Sync module for spec-kitty CLI.

Provides real-time synchronization with spec-kitty-saas server via:
- WebSocket client for event streaming
- Offline queue for resilience
- JWT authentication
- Batch sync for offline queue replay
"""

from .client import WebSocketClient
from .config import SyncConfig
from .queue import OfflineQueue
from .batch import batch_sync, sync_all_queued_events, BatchSyncResult

__all__ = [
    'WebSocketClient',
    'SyncConfig',
    'OfflineQueue',
    'batch_sync',
    'sync_all_queued_events',
    'BatchSyncResult',
]
