"""WebSocket client for real-time sync with exponential backoff reconnection"""
import asyncio
import json
import random
from typing import Optional, Callable
import websockets
from websockets import ConnectionClosed

from specify_cli.sync.auth import AuthClient, AuthenticationError


class ConnectionStatus:
    """Connection status constants"""
    CONNECTED = "Connected"
    RECONNECTING = "Reconnecting"
    OFFLINE = "Offline"
    BATCH_MODE = "OfflineBatchMode"


class WebSocketClient:
    """
    WebSocket client for spec-kitty sync protocol.

    Handles:
    - Connection management
    - Authentication
    - Event sending/receiving
    - Heartbeat (pong responses)
    - Automatic reconnection with exponential backoff
    """

    # Reconnection configuration
    MAX_RECONNECT_ATTEMPTS = 10
    BASE_DELAY_SECONDS = 0.5  # 500ms
    MAX_DELAY_SECONDS = 30.0
    JITTER_RANGE = 1.0  # +/- 1 second

    def __init__(
        self,
        server_url: str,
        token: Optional[str] = None,
        auth_client: Optional[AuthClient] = None,
    ):
        """
        Initialize WebSocket client.

        Args:
            server_url: Server URL (e.g., wss://spec-kitty-dev.fly.dev)
            token: Direct token (deprecated, for backward compatibility)
            auth_client: AuthClient instance for automatic token management

        Note:
            If auth_client is provided, it will be used to obtain tokens.
            If token is provided directly, it will be used as-is (legacy mode).
            If neither is provided, auth_client will be created automatically.
        """
        self.server_url = server_url
        self._direct_token = token
        self._auth_client = auth_client
        self.ws: Optional[websockets.ClientConnection] = None
        self.connected = False
        self.status = ConnectionStatus.OFFLINE
        self.message_handler: Optional[Callable] = None
        self.reconnect_attempts = 0

    def _get_ws_token(self) -> str:
        """
        Get WebSocket token for authentication.

        Returns:
            WebSocket token string

        Raises:
            AuthenticationError: If not authenticated
        """
        if self._direct_token:
            return self._direct_token

        if self._auth_client is None:
            self._auth_client = AuthClient()

        return self._auth_client.obtain_ws_token()

    async def connect(self):
        """Establish WebSocket connection with authentication"""
        uri = f"{self.server_url}/ws/v1/events/"

        retry_count = 0
        max_retries = 1

        while retry_count <= max_retries:
            try:
                ws_token = self._get_ws_token()
                headers = {"Authorization": f"Bearer {ws_token}"}

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
                return

            except websockets.InvalidStatus as e:
                if e.response.status_code == 401:
                    if retry_count < max_retries and self._auth_client and not self._direct_token:
                        print("🔄 Token expired, refreshing...")
                        retry_count += 1
                        try:
                            self._auth_client.refresh_tokens()
                            continue
                        except AuthenticationError:
                            print("❌ Session expired. Please log in again.")
                            self.status = ConnectionStatus.OFFLINE
                            raise
                    print("❌ Authentication failed: Invalid token")
                else:
                    print(f"❌ Connection failed: HTTP {e.response.status_code}")
                self.status = ConnectionStatus.OFFLINE
                raise
            except AuthenticationError as e:
                self.connected = False
                self.status = ConnectionStatus.OFFLINE
                print(f"❌ Authentication failed: {e}")
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

    async def reconnect(self) -> bool:
        """
        Reconnect with exponential backoff.

        Formula: delay = min(500ms * 2^attempt, 30s) + jitter

        Returns:
            True if reconnected successfully, False if max attempts reached
        """
        self.status = ConnectionStatus.RECONNECTING

        while self.reconnect_attempts < self.MAX_RECONNECT_ATTEMPTS:
            # Calculate exponential backoff delay
            delay = min(
                self.BASE_DELAY_SECONDS * (2 ** self.reconnect_attempts),
                self.MAX_DELAY_SECONDS
            )
            # Add jitter to prevent thundering herd
            jitter = random.uniform(-self.JITTER_RANGE, self.JITTER_RANGE)
            delay = max(0, delay + jitter)

            attempt_num = self.reconnect_attempts + 1
            print(f"🔄 Reconnecting... ({attempt_num}/{self.MAX_RECONNECT_ATTEMPTS})")

            await asyncio.sleep(delay)

            try:
                await self.connect()
                # Success - reset attempt counter
                self.reconnect_attempts = 0
                return True
            except AuthenticationError:
                self.status = ConnectionStatus.BATCH_MODE
                print("⚠️  Authentication failed. Please run 'spec-kitty auth login'")
                return False
            except Exception:
                self.reconnect_attempts += 1

        # Max attempts reached - switch to batch mode
        self.status = ConnectionStatus.BATCH_MODE
        print("⚠️  Max reconnection attempts reached. Switched to batch sync mode.")
        print("    Events will be queued locally and synced when connection is restored.")
        return False

    def reset_reconnect_attempts(self):
        """Reset the reconnection attempt counter"""
        self.reconnect_attempts = 0

    def get_reconnect_delay(self, attempt: int) -> float:
        """
        Calculate reconnect delay for a given attempt number.

        Args:
            attempt: The attempt number (0-indexed)

        Returns:
            Delay in seconds (without jitter)
        """
        return min(
            self.BASE_DELAY_SECONDS * (2 ** attempt),
            self.MAX_DELAY_SECONDS
        )

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

    def is_in_batch_mode(self) -> bool:
        """Check if client is in batch sync mode after max reconnection attempts"""
        return self.status == ConnectionStatus.BATCH_MODE
