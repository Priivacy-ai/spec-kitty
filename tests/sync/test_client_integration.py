"""Integration tests for WebSocket client.

Post-WP08 the WebSocketClient no longer takes ``server_url`` / ``token``
kwargs — connection parameters come exclusively from
``provision_ws_token(team_id)``, which talks to the process-wide
``TokenManager``. These tests exercise the behavioral surface that does
not require a live connection (heartbeat pong, error surfaces).
"""

import json
import pytest
from unittest.mock import AsyncMock
from uuid import UUID

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


@pytest.mark.asyncio
async def test_send_event_when_not_connected():
    """send_event raises ConnectionError when not connected."""
    client = WebSocketClient()

    with pytest.raises(ConnectionError, match="Not connected to server"):
        await client.send_event({"type": "test"})
