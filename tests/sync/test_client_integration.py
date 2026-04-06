"""Integration tests for WebSocket client"""

import json
import pytest
from unittest.mock import AsyncMock
from uuid import UUID

from specify_cli.sync.client import WebSocketClient, ConnectionStatus
from specify_cli.sync.project_identity import ProjectIdentity

pytestmark = pytest.mark.fast


@pytest.mark.asyncio
async def test_heartbeat_pong_includes_build_id():
    """Test that pong response to server ping includes build_id from project identity."""
    identity = ProjectIdentity(
        project_uuid=UUID("12345678-1234-5678-1234-567812345678"),
        project_slug="test-project",
        node_id="abcdef123456",
        build_id="bid-9999",
    )
    client = WebSocketClient(
        server_url="ws://localhost:8000",
        token="test-token",
        project_identity=identity,
    )

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
    """Test that pong response omits build_id when no project identity is set."""
    client = WebSocketClient(
        server_url="ws://localhost:8000",
        token="test-token",
    )

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
    """
    Test connecting to development server.

    Note: This test requires the spec-kitty-saas server running at localhost:8000
    with a valid authentication token. It will be skipped if the server is not available.
    """
    # Skip if server not available
    pytest.skip("Integration test requires running server - use for manual testing")

    # This would be used for manual testing with a real server
    client = WebSocketClient(
        server_url="ws://localhost:8000",
        token="test-token",  # Would need real token from server
    )

    await client.connect()
    assert client.connected
    assert client.get_status() == ConnectionStatus.CONNECTED

    await client.disconnect()
    assert not client.connected
    assert client.get_status() == ConnectionStatus.OFFLINE


@pytest.mark.asyncio
async def test_client_initialization():
    """Test WebSocket client can be initialized"""
    client = WebSocketClient(server_url="ws://localhost:8000", token="test-token")

    assert client.server_url == "ws://localhost:8000"
    assert client._direct_token == "test-token"
    assert not client.connected
    assert client.get_status() == ConnectionStatus.OFFLINE


@pytest.mark.asyncio
async def test_send_event_when_not_connected():
    """Test sending event when not connected raises error"""
    client = WebSocketClient(server_url="ws://localhost:8000", token="test-token")

    with pytest.raises(ConnectionError, match="Not connected to server"):
        await client.send_event({"type": "test"})
