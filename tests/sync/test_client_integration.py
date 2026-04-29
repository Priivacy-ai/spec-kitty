"""Integration tests for WebSocket client.

Post-WP08 the WebSocketClient no longer takes ``server_url`` / ``token``
kwargs — connection parameters come exclusively from
``provision_ws_token(team_id)``, which talks to the process-wide
``TokenManager``. These tests exercise the behavioral surface that does
not require a live connection (heartbeat pong, error surfaces).
"""

import json
from datetime import UTC, datetime, timedelta
import pytest
from unittest.mock import AsyncMock
from uuid import UUID

from specify_cli.auth.session import StoredSession, Team
from specify_cli.sync.client import WebSocketClient, ConnectionStatus
from specify_cli.sync.project_identity import ProjectIdentity

pytestmark = pytest.mark.fast


@pytest.mark.asyncio
async def test_heartbeat_pong_includes_build_id():
    """pong response to server ping includes build_id from project identity."""
    identity = ProjectIdentity(
        project_uuid=UUID("12345678-1234-5678-1234-567812345678"),
        project_slug="test-project",
        node_id="abcdef123456",
        build_id="bid-9999",
    )
    client = WebSocketClient(project_identity=identity)

    # Simulate an active connection with a mock websocket
    sent_messages: list[str] = []
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock(side_effect=lambda msg: sent_messages.append(msg))
    client.ws = mock_ws
    client.connected = True

    # Simulate receiving a ping
    await client._handle_ping({"type": "ping", "timestamp": "2026-04-06T00:00:00Z"})

    assert len(sent_messages) == 1
    pong = json.loads(sent_messages[0])
    assert pong["type"] == "pong"
    assert pong["timestamp"] == "2026-04-06T00:00:00Z"
    assert pong["build_id"] == "bid-9999"


@pytest.mark.asyncio
async def test_heartbeat_pong_omits_build_id_when_no_identity():
    """pong response omits build_id when no project identity is set."""
    client = WebSocketClient()

    sent_messages: list[str] = []
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock(side_effect=lambda msg: sent_messages.append(msg))
    client.ws = mock_ws
    client.connected = True

    await client._handle_ping({"type": "ping", "timestamp": "2026-04-06T00:00:00Z"})

    assert len(sent_messages) == 1
    pong = json.loads(sent_messages[0])
    assert pong["type"] == "pong"
    assert "build_id" not in pong


@pytest.mark.asyncio
async def test_connect_to_server():
    """Placeholder for a live-server integration test.

    Kept here as documentation of how WebSocketClient should behave
    end-to-end once a running SaaS server is available to the test
    harness. Always skipped; the client now fetches its ws bundle
    from ``provision_ws_token`` internally.
    """
    pytest.skip("Integration test requires running server - use for manual testing")

    client = WebSocketClient()
    await client.connect()
    assert client.connected
    assert client.get_status() == ConnectionStatus.CONNECTED

    await client.disconnect()
    assert not client.connected
    assert client.get_status() == ConnectionStatus.OFFLINE


@pytest.mark.asyncio
async def test_client_initialization():
    """WebSocket client can be constructed with no arguments."""
    client = WebSocketClient()

    assert not client.connected
    assert client.get_status() == ConnectionStatus.OFFLINE
    assert client.ws is None
    assert client._listen_task is None


def test_websocket_client_prefers_private_team_for_ingress(monkeypatch):
    """WS provisioning should keep targeting Private Teamspace even if default_team_id drifts."""
    now = datetime.now(UTC)

    class _FakeTokenManager:
        def get_current_session(self):
            return StoredSession(
                user_id="user-1",
                email="robert@example.com",
                name="Robert",
                teams=[
                    Team(id="product-team", name="Product Team", role="member"),
                    Team(id="private-team", name="Robert Private Teamspace", role="owner", is_private_teamspace=True),
                ],
                default_team_id="product-team",
                access_token="access",
                refresh_token="refresh",
                session_id="sess-1",
                issued_at=now,
                access_token_expires_at=now + timedelta(hours=1),
                refresh_token_expires_at=now + timedelta(days=30),
                scope="offline_access",
                storage_backend="file",
                last_used_at=now,
                auth_method="authorization_code",
            )

    monkeypatch.setattr("specify_cli.sync.client.get_token_manager", lambda: _FakeTokenManager())

    client = WebSocketClient()
    assert client._current_team_id() == "private-team"


@pytest.mark.asyncio
async def test_send_event_when_not_connected():
    """send_event raises ConnectionError when not connected."""
    client = WebSocketClient()

    with pytest.raises(ConnectionError, match="Not connected to server"):
        await client.send_event({"type": "test"})


def test_normalize_ws_url_converts_https_and_loopback_http():
    """Provisioned HTTPS URLs become WSS; loopback HTTP remains allowed for local dev."""
    assert (
        WebSocketClient._normalize_ws_url("https://spec-kitty-dev.fly.dev/ws")
        == "wss://spec-kitty-dev.fly.dev/ws"
    )
    assert (
        WebSocketClient._normalize_ws_url("http://127.0.0.1:9400/ws")
        == "ws://127.0.0.1:9400/ws"
    )
    assert (
        WebSocketClient._normalize_ws_url("ws://localhost:9400/ws")
        == "ws://localhost:9400/ws"
    )


def test_normalize_ws_url_rejects_insecure_remote_plaintext():
    """Remote plaintext endpoints must not receive the ephemeral WS token."""
    with pytest.raises(Exception, match="Refusing insecure WebSocket provisioning URL"):
        WebSocketClient._normalize_ws_url("http://spec-kitty-dev.fly.dev/ws")
    with pytest.raises(Exception, match="Refusing insecure WebSocket provisioning URL"):
        WebSocketClient._normalize_ws_url("ws://spec-kitty-dev.fly.dev/ws")
