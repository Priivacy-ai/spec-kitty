"""Integration tests for WebSocket client.

Post-WP08 the WebSocketClient no longer takes ``server_url`` / ``token``
kwargs — connection parameters come exclusively from
``provision_ws_token(team_id)``, which talks to the process-wide
``TokenManager``. These tests exercise the behavioral surface that does
not require a live connection (heartbeat pong, error surfaces).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
import pytest
from unittest.mock import AsyncMock
from uuid import UUID

import httpx
import respx

from specify_cli.auth.secure_storage import SecureStorage
from specify_cli.auth.session import StoredSession, Team
from specify_cli.auth.token_manager import TokenManager
from specify_cli.sync.client import WebSocketClient, ConnectionStatus
from specify_cli.sync.project_identity import ProjectIdentity

pytestmark = pytest.mark.fast

_SAAS_BASE_URL = "https://saas.example"


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


# ---------------------------------------------------------------------------
# WP05 / T022 — ws-token strict resolver coverage
#
# The strict resolver (``sync/_team.resolve_private_team_id_for_ingress``) is
# called in ``client.connect()`` immediately before ``provision_ws_token``.
# These tests exercise three scenarios:
#
#   - shared-only session that rehydrates to a private team via /api/v1/me
#   - shared-only session whose rehydrate still surfaces no private team
#   - healthy session that already carries a Private Teamspace and skips /me
#
# We patch ``websockets.connect`` so the WS upgrade never opens a real socket;
# the assertions are about the HTTP traffic ``provision_ws_token`` produces
# and the structured warnings the resolver emits on the skip path.
# ---------------------------------------------------------------------------


class _FakeStorage(SecureStorage):  # type: ignore[misc]
    """Minimal in-memory ``SecureStorage`` fake for TokenManager."""

    def __init__(self) -> None:
        self._session: StoredSession | None = None

    def read(self) -> StoredSession | None:
        return self._session

    def write(self, session: StoredSession) -> None:
        self._session = session

    def delete(self) -> None:
        self._session = None

    @property
    def backend_name(self) -> str:
        return "file"


def _build_session(*, teams: list[Team]) -> StoredSession:
    now = datetime.now(UTC)
    return StoredSession(
        user_id="user-1",
        email="u@example.com",
        name="U",
        teams=teams,
        default_team_id=teams[0].id if teams else "",
        access_token="access-v1",
        refresh_token="refresh-v1",
        session_id="sess",
        issued_at=now,
        # Far-future access token so the provisioner does not trigger a
        # pre-connect refresh (5-minute buffer in token_provisioning.py).
        access_token_expires_at=now + timedelta(hours=2),
        refresh_token_expires_at=now + timedelta(days=30),
        scope="openid",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )


@pytest.fixture
def token_manager_with_shared_only_session() -> TokenManager:
    storage = _FakeStorage()
    tm = TokenManager(storage, saas_base_url=_SAAS_BASE_URL)
    tm._session = _build_session(
        teams=[
            Team(
                id="t-shared",
                name="Shared",
                role="member",
                is_private_teamspace=False,
            )
        ]
    )
    return tm


@pytest.fixture
def token_manager_with_private_session() -> TokenManager:
    storage = _FakeStorage()
    tm = TokenManager(storage, saas_base_url=_SAAS_BASE_URL)
    tm._session = _build_session(
        teams=[
            Team(
                id="t-shared",
                name="Shared",
                role="member",
                is_private_teamspace=False,
            ),
            Team(
                id="t-private",
                name="Private",
                role="owner",
                is_private_teamspace=True,
            ),
        ]
    )
    return tm


def _make_fake_ws(snapshot: dict[str, Any]) -> AsyncMock:
    """Produce an AsyncMock that mimics a connected ``websockets`` connection.

    The first ``recv()`` returns the initial snapshot frame as JSON, and any
    further iteration / send is a no-op. This is enough to satisfy
    ``WebSocketClient.connect``'s ``_receive_snapshot`` and the ``_listen``
    task spawn that follows it.
    """
    ws = AsyncMock()
    ws.recv = AsyncMock(return_value=json.dumps(snapshot))

    async def _aiter() -> Any:
        if False:
            yield  # pragma: no cover
        return

    ws.__aiter__ = lambda self: _aiter()
    ws.send = AsyncMock()
    ws.close = AsyncMock()
    return ws


def _patch_singleton(
    monkeypatch: pytest.MonkeyPatch,
    tm: TokenManager,
) -> None:
    """Make every ``get_token_manager()`` call return ``tm``.

    Both the resolver in ``sync/_team.py`` and the inner provisioner reach
    for the singleton via ``specify_cli.auth.get_token_manager``. The
    ``token_provisioning`` module imported the symbol at load time
    (``from .. import get_token_manager``) so we also rebind the module-local
    name to keep the test isolated from the real auth state on disk.
    """
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: tm)
    monkeypatch.setattr(
        "specify_cli.auth.websocket.token_provisioning.get_token_manager",
        lambda: tm,
    )
    monkeypatch.setattr("specify_cli.sync.client.get_token_manager", lambda: tm)


def _enable_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force ``is_saas_sync_enabled()`` on for the duration of the test."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", _SAAS_BASE_URL)


@pytest.mark.asyncio
@respx.mock
async def test_ws_token_rehydrates_when_session_lacks_private(
    token_manager_with_shared_only_session: TokenManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-002 + AC-005: shared-only session triggers /api/v1/me rehydrate;
    on success, /api/v1/ws-token receives the private id."""
    _enable_sync(monkeypatch)
    _patch_singleton(monkeypatch, token_manager_with_shared_only_session)

    me_route = respx.get(f"{_SAAS_BASE_URL}/api/v1/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "email": "u@example.com",
                "teams": [
                    {
                        "id": "t-private",
                        "name": "Private",
                        "role": "owner",
                        "is_private_teamspace": True,
                    },
                    {
                        "id": "t-shared",
                        "name": "Shared",
                        "role": "member",
                        "is_private_teamspace": False,
                    },
                ],
            },
        )
    )
    wstoken_route = respx.post(f"{_SAAS_BASE_URL}/api/v1/ws-token").mock(
        return_value=httpx.Response(
            200,
            json={
                "ws_url": "wss://saas.example/ws",
                "ws_token": "ws-tok",
                "expires_in": 60,
                "session_id": "sess",
            },
        )
    )
    fake_ws = _make_fake_ws(
        {"type": "snapshot", "work_packages": []},
    )

    async def _fake_connect(*args: Any, **kwargs: Any) -> AsyncMock:  # noqa: ARG001
        return fake_ws

    monkeypatch.setattr("specify_cli.sync.client.websockets.connect", _fake_connect)

    client = WebSocketClient()
    await client.connect()

    # Cancel the listener task spawned by connect() so the test exits cleanly.
    if client._listen_task is not None:
        client._listen_task.cancel()

    assert me_route.call_count == 1
    assert wstoken_route.call_count == 1
    body = wstoken_route.calls[0].request.read().decode()
    assert "t-private" in body
    parsed = json.loads(body)
    assert parsed.get("team_id") == "t-private"


@pytest.mark.asyncio
@respx.mock
async def test_ws_token_skipped_when_no_private_team_after_rehydrate(
    token_manager_with_shared_only_session: TokenManager,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC-005: shared-only session, rehydrate returns no private => no ws-token POST."""
    _enable_sync(monkeypatch)
    _patch_singleton(monkeypatch, token_manager_with_shared_only_session)

    respx.get(f"{_SAAS_BASE_URL}/api/v1/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "email": "u@example.com",
                "teams": [
                    {
                        "id": "t-shared",
                        "name": "Shared",
                        "role": "member",
                        "is_private_teamspace": False,
                    }
                ],
            },
        )
    )
    wstoken_route = respx.post(f"{_SAAS_BASE_URL}/api/v1/ws-token").mock(
        return_value=httpx.Response(200, json={})
    )

    client = WebSocketClient()
    with caplog.at_level(logging.WARNING, logger="specify_cli.sync._team"):
        await client.connect()

    assert wstoken_route.call_count == 0
    assert client.connected is False
    assert client.status == ConnectionStatus.OFFLINE

    matching = [
        record
        for record in caplog.records
        if "direct ingress skipped" in record.getMessage()
        and "/api/v1/ws-token" in record.getMessage()
    ]
    assert matching, (
        "expected structured 'direct ingress skipped' warning citing "
        "/api/v1/ws-token endpoint"
    )


@pytest.mark.asyncio
@respx.mock
async def test_ws_token_healthy_session_no_rehydrate(
    token_manager_with_private_session: TokenManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario 1 regression: healthy session => no /api/v1/me call, ws-token goes through."""
    _enable_sync(monkeypatch)
    _patch_singleton(monkeypatch, token_manager_with_private_session)

    me_route = respx.get(f"{_SAAS_BASE_URL}/api/v1/me").mock(
        return_value=httpx.Response(200, json={})
    )
    wstoken_route = respx.post(f"{_SAAS_BASE_URL}/api/v1/ws-token").mock(
        return_value=httpx.Response(
            200,
            json={
                "ws_url": "wss://saas.example/ws",
                "ws_token": "ws-tok",
                "expires_in": 60,
                "session_id": "sess",
            },
        )
    )

    fake_ws = _make_fake_ws({"type": "snapshot", "work_packages": []})

    async def _fake_connect(*args: Any, **kwargs: Any) -> AsyncMock:  # noqa: ARG001
        return fake_ws

    monkeypatch.setattr("specify_cli.sync.client.websockets.connect", _fake_connect)

    client = WebSocketClient()
    await client.connect()

    # Cancel the listener task spawned by connect() so the test exits cleanly.
    if client._listen_task is not None:
        client._listen_task.cancel()

    assert me_route.call_count == 0
    assert wstoken_route.call_count == 1
    body = json.loads(wstoken_route.calls[0].request.read().decode())
    assert body.get("team_id") == "t-private"
