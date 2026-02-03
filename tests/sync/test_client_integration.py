"""Integration tests for WebSocket client"""
import pytest
import asyncio
from specify_cli.sync.client import WebSocketClient, ConnectionStatus


@pytest.mark.anyio
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
        token="test-token"  # Would need real token from server
    )

    await client.connect()
    assert client.connected
    assert client.get_status() == ConnectionStatus.CONNECTED

    await client.disconnect()
    assert not client.connected
    assert client.get_status() == ConnectionStatus.OFFLINE


@pytest.mark.anyio
async def test_client_initialization():
    """Test WebSocket client can be initialized"""
    client = WebSocketClient(
        server_url="ws://localhost:8000",
        token="test-token"
    )

    assert client.server_url == "ws://localhost:8000"
    assert client.token == "test-token"
    assert not client.connected
    assert client.get_status() == ConnectionStatus.OFFLINE


@pytest.mark.anyio
async def test_send_event_when_not_connected():
    """Test sending event when not connected raises error"""
    client = WebSocketClient(
        server_url="ws://localhost:8000",
        token="test-token"
    )

    with pytest.raises(ConnectionError, match="Not connected to server"):
        await client.send_event({"type": "test"})
