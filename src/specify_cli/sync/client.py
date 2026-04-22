"""WebSocket client for real-time sync with exponential backoff reconnection.

As of WP08 (browser-mediated OAuth), this client fetches its ephemeral
WebSocket token via ``specify_cli.auth.websocket.provision_ws_token`` (which
uses the process-wide ``TokenManager``). All tokens and server URLs flow
through the ``auth`` package; this module does not read legacy credential
state directly.
"""

import asyncio
import json
import random
from contextlib import suppress
from collections.abc import Callable
from typing import Any

import websockets
from websockets import ConnectionClosed

from specify_cli.auth import get_token_manager
from specify_cli.auth.errors import (
    AuthenticationError,
    NotAuthenticatedError,
    TokenRefreshError,
)
from specify_cli.auth.session import get_private_team_id
from specify_cli.auth.websocket import provision_ws_token
from specify_cli.core.contract_gate import validate_outbound_payload
from specify_cli.sync.feature_flags import (
    is_saas_sync_enabled,
    saas_sync_disabled_message,
)
from specify_cli.sync.project_identity import ProjectIdentity


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
    - Connection management via ``provision_ws_token`` (pre-connect token provisioning)
    - Event sending/receiving
    - Heartbeat (pong responses)
    - Automatic reconnection with exponential backoff

    The client no longer stores or refreshes tokens itself — every connect
    attempt calls ``provision_ws_token()`` which delegates to the shared
    ``TokenManager`` (single-flight refresh, consistent 401 semantics).
    """

    # Reconnection configuration
    MAX_RECONNECT_ATTEMPTS = 10
    BASE_DELAY_SECONDS = 0.5  # 500ms
    MAX_DELAY_SECONDS = 30.0
    JITTER_RANGE = 1.0  # +/- 1 second

    def __init__(
        self,
        project_identity: ProjectIdentity | None = None,
    ):
        """
        Initialize WebSocket client.

        Args:
            project_identity: ProjectIdentity for build_id in heartbeats.

        Notes:
            Server URL and authentication are resolved on every ``connect()``
            call via ``provision_ws_token``. There is no direct token argument.
        """
        self._project_identity = project_identity
        self.ws: websockets.ClientConnection | None = None
        self.connected = False
        self.status = ConnectionStatus.OFFLINE
        self.message_handler: Callable | None = None
        self.reconnect_attempts = 0
        self._listen_task: asyncio.Task | None = None

    def _current_team_id(self) -> str:
        """Resolve the team id to use for ws-token provisioning.

        Private Teamspace wins when present; otherwise fall back to the session default.
        """
        tm = get_token_manager()
        session = tm.get_current_session()
        if session is None:
            raise NotAuthenticatedError(
                "WebSocket connect requires an authenticated session. "
                "Run `spec-kitty auth login`."
            )
        if not session.default_team_id:
            if not session.teams:
                raise NotAuthenticatedError(
                    "No teams associated with the current session."
                )
            private_team_id = get_private_team_id(session.teams)
            if private_team_id:
                return private_team_id
            return session.teams[0].id
        private_team_id = get_private_team_id(session.teams)
        if private_team_id:
            return private_team_id
        return session.default_team_id

    async def connect(self):
        """Establish WebSocket connection with authentication.

        Flow:
        1. Gate on the SaaS-sync feature flag.
        2. Fetch a fresh ws_token + ws_url via ``provision_ws_token`` (which
           single-flight-refreshes the access token if needed).
        3. Open the WS upgrade at ``ws_url?token=<ws_token>``.
        4. Receive the initial snapshot and start the listener task.
        """
        if not is_saas_sync_enabled():
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            raise AuthenticationError(saas_sync_disabled_message())

        try:
            team_id = self._current_team_id()
            ws_bundle = await provision_ws_token(team_id)
        except NotAuthenticatedError:
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            print("❌ Not authenticated. Run `spec-kitty auth login`.")
            raise
        except TokenRefreshError as exc:
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            print(f"❌ Token refresh failed: {exc}")
            raise
        except Exception as exc:
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            print(f"❌ Connection failed: {exc}")
            raise

        ws_url = ws_bundle.get("ws_url")
        ws_token = ws_bundle.get("ws_token")
        if not ws_url or not ws_token:
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            raise AuthenticationError(
                "WebSocket provisioning returned an incomplete bundle."
            )

        # Normalize ws_url scheme (provisioning returns https/http; WS needs wss/ws).
        if ws_url.startswith("https://"):
            ws_url = "wss://" + ws_url[len("https://") :]
        elif ws_url.startswith("http://"):
            ws_url = "ws://" + ws_url[len("http://") :]

        # Token-in-query-string, matching the SaaS contract for ephemeral ws tokens.
        separator = "&" if "?" in ws_url else "?"
        uri = f"{ws_url}{separator}token={ws_token}"

        try:
            self.ws = await websockets.connect(
                uri,
                ping_interval=None,  # We handle heartbeat manually
                ping_timeout=None,
            )
            self.connected = True
            self.status = ConnectionStatus.CONNECTED

            # Receive initial snapshot
            await self._receive_snapshot()

            # Start message listener
            self._listen_task = asyncio.create_task(self._listen())

            print("✅ Connected to sync server")
            return

        except websockets.InvalidStatus as e:
            if e.response.status_code == 401:
                print("❌ WebSocket rejected token. Please re-authenticate.")
            else:
                print(f"❌ Connection failed: HTTP {e.response.status_code}")
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            raise
        except Exception as e:
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            print(f"❌ Connection failed: {e}")
            raise

    async def disconnect(self):
        """Close WebSocket connection"""
        if self._listen_task:
            self._listen_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._listen_task
            self._listen_task = None

        if self.ws:
            await self.ws.close()
            self.ws = None
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
            delay = min(self.BASE_DELAY_SECONDS * (2**self.reconnect_attempts), self.MAX_DELAY_SECONDS)
            # Add jitter to prevent thundering herd
            jitter = random.uniform(-self.JITTER_RANGE, self.JITTER_RANGE)  # noqa: S311
            delay = max(0, delay + jitter)

            attempt_num = self.reconnect_attempts + 1
            print(f"🔄 Reconnecting... ({attempt_num}/{self.MAX_RECONNECT_ATTEMPTS})")

            await asyncio.sleep(delay)

            try:
                await self.connect()
                # Success - reset attempt counter
                self.reconnect_attempts = 0
                return True
            except (NotAuthenticatedError, TokenRefreshError):
                self.status = ConnectionStatus.BATCH_MODE
                print("⚠️  Authentication failed. Please run 'spec-kitty auth login'")
                return False
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
        return min(self.BASE_DELAY_SECONDS * (2**attempt), self.MAX_DELAY_SECONDS)

    async def send_event(self, event: dict):
        """
        Send event to server.

        Args:
            event: Event dict with type, event_id, lamport_clock, etc.
        """
        if not self.connected or not self.ws:
            raise ConnectionError("Not connected to server")

        # Contract gate: validate envelope before WebSocket send
        validate_outbound_payload(event, "envelope")

        try:
            await self.ws.send(json.dumps(event))
        except ConnectionClosed:
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            raise ConnectionError("Connection closed") from None

    async def _listen(self):
        """Listen for messages from server"""
        try:
            async for message in self.ws:
                data = json.loads(message)
                await self._handle_message(data)
        except asyncio.CancelledError:
            # Expected during explicit disconnect/shutdown.
            raise
        except ConnectionClosed:
            self.connected = False
            self.status = ConnectionStatus.OFFLINE
            print("Connection closed by server")
        finally:
            self._listen_task = None

    async def _handle_message(self, data: dict):
        """Handle incoming message"""
        msg_type = data.get("type")

        if msg_type == "snapshot":
            await self._handle_snapshot(data)
        elif msg_type == "event":
            await self._handle_event(data)
        elif msg_type == "ping":
            await self._handle_ping(data)
        else:
            # Unknown message type
            pass

    async def _receive_snapshot(self):
        """Receive and process initial snapshot"""
        message = await self.ws.recv()
        data = json.loads(message)

        if data.get("type") == "snapshot":
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
        """Respond to server ping with build_id for identity correlation."""
        pong: dict[str, Any] = {"type": "pong", "timestamp": data.get("timestamp")}
        if self._project_identity is not None and self._project_identity.build_id:
            pong["build_id"] = self._project_identity.build_id
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
