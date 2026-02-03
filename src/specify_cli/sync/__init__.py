"""
Sync module for spec-kitty CLI.

Provides real-time synchronization with spec-kitty-saas server via:
- WebSocket client for event streaming
- Offline queue for resilience
- JWT authentication
"""

from .client import WebSocketClient
from .config import SyncConfig
from .queue import OfflineQueue

__all__ = ['WebSocketClient', 'SyncConfig', 'OfflineQueue']
