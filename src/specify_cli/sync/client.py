"""WebSocket client for real-time sync"""
import asyncio
import json
from typing import Optional, Callable
import websockets
from websockets import ConnectionClosed


class ConnectionStatus:
    """Connection status constants"""
    CONNECTED = "Connected"
    RECONNECTING = "Reconnecting"
    OFFLINE = "Offline"
    BATCH_MODE = "Offline - Batch Mode"


class WebSocketClient:
    """
    WebSocket client for spec-kitty sync protocol.

    Handles:
    - Connection management
    - Authentication
    - Event sending/receiving
    - Heartbeat (pong responses)
    """

    def __init__(self, server_url: str, token: str):
        """
        Initialize WebSocket client.

        Args:
            server_url: Server URL (e.g., wss://spec-kitty-dev.fly.dev)
            token: Ephemeral WebSocket token
        """
        self.server_url = server_url
        self.token = token
        self.ws: Optional[websockets.ClientConnection] = None
        self.connected = False
        self.status = ConnectionStatus.OFFLINE
        self.message_handler: Optional[Callable] = None

    async def connect(self):
        """Establish WebSocket connection with authentication"""
        uri = f"{self.server_url}/ws/v1/events/"
        headers = {"Authorization": f"Bearer {self.token}"}

        try:
            self.ws = await websockets.connect(
                uri,
                additional_headers=headers,
                ping_interval=None,  # We handle heartbeat manually
                ping_timeout=None
            )
            self.connected = True
            self.status = ConnectionStatus.CONNECTED

            # Receive initial snapshot
            await self._receive_snapshot()

            # Start message listener
            asyncio.create_task(self._listen())

            print("✅ Connected to sync server")

        except websockets.InvalidStatus as e:
            if e.response.status_code == 401:
                print("❌ Authentication failed: Invalid token")
            else:
                print(f"❌ Connection failed: HTTP {e.response.status_code}")
            self.status = ConnectionStatus.OFFLINE
            raise
        except Exception as e:
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            print(f"❌ Connection failed: {e}")
            raise

    async def disconnect(self):
        """Close WebSocket connection"""
        if self.ws:
            await self.ws.close()
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            print("Disconnected from sync server")

    async def send_event(self, event: dict):
        """
        Send event to server.

        Args:
            event: Event dict with type, event_id, lamport_clock, etc.
        """
        if not self.connected or not self.ws:
            raise ConnectionError("Not connected to server")

        try:
            await self.ws.send(json.dumps(event))
        except ConnectionClosed:
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            raise ConnectionError("Connection closed")

    async def _listen(self):
        """Listen for messages from server"""
        try:
            async for message in self.ws:
                data = json.loads(message)
                await self._handle_message(data)
        except ConnectionClosed:
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            print("Connection closed by server")

    async def _handle_message(self, data: dict):
        """Handle incoming message"""
        msg_type = data.get('type')

        if msg_type == 'snapshot':
            await self._handle_snapshot(data)
        elif msg_type == 'event':
            await self._handle_event(data)
        elif msg_type == 'ping':
            await self._handle_ping(data)
        else:
            # Unknown message type
            pass

    async def _receive_snapshot(self):
        """Receive and process initial snapshot"""
        message = await self.ws.recv()
        data = json.loads(message)

        if data.get('type') == 'snapshot':
            print(f"📦 Received snapshot: {len(data.get('work_packages', []))} work packages")
        else:
            print(f"⚠️  Expected snapshot, got {data.get('type')}")

    async def _handle_snapshot(self, data: dict):
        """Process snapshot"""
        # Store snapshot data locally if needed
        pass

    async def _handle_event(self, data: dict):
        """Process event broadcast"""
        if self.message_handler:
            await self.message_handler(data)

    async def _handle_ping(self, data: dict):
        """Respond to server ping"""
        pong = {
            'type': 'pong',
            'timestamp': data.get('timestamp')
        }
        await self.ws.send(json.dumps(pong))

    def set_message_handler(self, handler: Callable):
        """Set handler for incoming events"""
        self.message_handler = handler

    def get_status(self) -> str:
        """Get current connection status"""
        return self.status
