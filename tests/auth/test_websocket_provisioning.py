"""Unit tests for the WebSocket pre-connect token provisioner (feature 080, WP09).

The provisioner lives at ``specify_cli.auth.websocket.token_provisioning`` and
the public surface is exported from ``specify_cli.auth.websocket``. These
tests cover:

- Success path (200) returns the parsed dict with all required fields.
- Not-authenticated path raises :class:`NotAuthenticatedError`.
- Pre-connect refresh is triggered when the access token is within the
  300-second NFR-005 buffer.
- 403 ``not_a_team_member`` → user-friendly ``WebSocketProvisioningError``.
- 404 ``team not found`` → user-friendly ``WebSocketProvisioningError``.
- 5xx → ``WebSocketProvisioningError`` with "server error" wording.
- ``httpx.RequestError`` → :class:`NetworkError`.

The ``mock_tm`` fixture patches ``get_token_manager`` in the provisioning
module so we never touch real secure storage or the network.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from specify_cli.auth import reset_token_manager
from specify_cli.auth.errors import NetworkError, NotAuthenticatedError
from specify_cli.auth.session import StoredSession, Team
from specify_cli.auth.websocket import (
    WebSocketProvisioningError,
    WebSocketTokenProvisioner,
    provision_ws_token,
)


def _make_session(access_remaining_seconds: int = 3600) -> StoredSession:
    """Build a StoredSession whose access token expires in N seconds.

    ``refresh_token_expires_at`` is set to ``now + 90 days`` so the session
    is considered authenticated. Per spec 080 decision D-9, production code
    never hardcodes a refresh-token TTL — it may be ``None`` when the server
    does not communicate one. This hardcoded value is acceptable here
    because it is TEST CODE, not a real session being persisted.
    """
    now = datetime.now(UTC)
    return StoredSession(
        user_id="u_alice",
        email="alice@example.com",
        name="Alice",
        teams=[Team(id="tm_acme", name="Acme", role="admin")],
        default_team_id="tm_acme",
        access_token="at_xyz",
        refresh_token="rt_xyz",
        session_id="sess_xyz",
        issued_at=now,
        access_token_expires_at=now + timedelta(seconds=access_remaining_seconds),
        refresh_token_expires_at=now + timedelta(days=90),
        scope="offline_access",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )


class _MockResponse:
    """Tiny stand-in for ``httpx.Response`` — only ``status_code`` + ``json()``."""

    def __init__(self, status_code: int, json_body: dict | None = None) -> None:
        self.status_code = status_code
        self._json = json_body if json_body is not None else {}

    def json(self) -> dict:
        return self._json


@pytest.fixture
def mock_tm(monkeypatch):
    """Patch ``get_token_manager`` inside the provisioning module.

    Yields a fake TokenManager with an authenticated session by default.
    Individual tests can tweak ``is_authenticated`` or
    ``get_current_session.return_value`` to exercise other paths.
    """
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test")
    reset_token_manager()
    fake_tm = MagicMock()
    fake_tm.is_authenticated = True
    fake_tm.get_current_session.return_value = _make_session()
    fake_tm.get_access_token = AsyncMock(return_value="at_xyz")
    fake_tm.refresh_if_needed = AsyncMock(return_value=False)
    with patch(
        "specify_cli.auth.websocket.token_provisioning.get_token_manager",
        return_value=fake_tm,
    ):
        yield fake_tm
    reset_token_manager()


def _install_mock_post(mock_client_cls, post_fn):
    """Wire ``post_fn`` into a patched ``httpx.AsyncClient`` context manager."""
    instance = mock_client_cls.return_value.__aenter__.return_value
    instance.post = post_fn
    return instance


class TestWebSocketTokenProvisioner:
    """End-to-end coverage of the provisioner's observable behaviour."""

    async def test_success(self, mock_tm):
        ws_response = {
            "ws_token": "ws_xyz",
            "ws_url": "wss://saas.test/ws",
            "expires_in": 3600,
            "session_id": "sess_xyz",
        }

        async def mock_post(url, json=None, headers=None):
            # Verify the provisioner passes through all contract fields.
            assert url == "https://saas.test/api/v1/ws-token"
            assert json == {"team_id": "tm_acme"}
            assert headers == {"Authorization": "Bearer at_xyz"}
            return _MockResponse(200, ws_response)

        with patch(
            "specify_cli.auth.websocket.token_provisioning.httpx.AsyncClient"
        ) as mock_client:
            _install_mock_post(mock_client, mock_post)
            result = await provision_ws_token("tm_acme")

        assert result == ws_response

    async def test_not_authenticated(self, mock_tm):
        mock_tm.is_authenticated = False
        with pytest.raises(NotAuthenticatedError):
            await provision_ws_token("tm_acme")

    async def test_pre_connect_refresh_when_near_expiry(self, mock_tm):
        # Session expires in 60s, buffer is 300s → must refresh.
        mock_tm.get_current_session.return_value = _make_session(
            access_remaining_seconds=60
        )
        ws_response = {
            "ws_token": "ws_xyz",
            "ws_url": "wss://saas.test/ws",
            "expires_in": 3600,
            "session_id": "sess_xyz",
        }

        async def mock_post(url, json=None, headers=None):
            return _MockResponse(200, ws_response)

        with patch(
            "specify_cli.auth.websocket.token_provisioning.httpx.AsyncClient"
        ) as mock_client:
            _install_mock_post(mock_client, mock_post)
            await provision_ws_token("tm_acme")

        mock_tm.refresh_if_needed.assert_called_once()

    async def test_no_refresh_when_access_token_is_fresh(self, mock_tm):
        """Inverse of the refresh path: a fresh token must NOT refresh."""
        # 3600s remaining, buffer 300s → well outside the window.
        mock_tm.get_current_session.return_value = _make_session(
            access_remaining_seconds=3600
        )
        ws_response = {
            "ws_token": "ws_xyz",
            "ws_url": "wss://saas.test/ws",
            "expires_in": 3600,
            "session_id": "sess_xyz",
        }

        async def mock_post(url, json=None, headers=None):
            return _MockResponse(200, ws_response)

        with patch(
            "specify_cli.auth.websocket.token_provisioning.httpx.AsyncClient"
        ) as mock_client:
            _install_mock_post(mock_client, mock_post)
            await provision_ws_token("tm_acme")

        mock_tm.refresh_if_needed.assert_not_called()

    async def test_403_not_team_member(self, mock_tm):
        async def mock_post(url, json=None, headers=None):
            return _MockResponse(403, {"error": "not_a_team_member"})

        with patch(
            "specify_cli.auth.websocket.token_provisioning.httpx.AsyncClient"
        ) as mock_client:
            _install_mock_post(mock_client, mock_post)
            with pytest.raises(WebSocketProvisioningError, match="not a member"):
                await provision_ws_token("tm_acme")

    async def test_404_team_not_found(self, mock_tm):
        async def mock_post(url, json=None, headers=None):
            return _MockResponse(404, {})

        with patch(
            "specify_cli.auth.websocket.token_provisioning.httpx.AsyncClient"
        ) as mock_client:
            _install_mock_post(mock_client, mock_post)
            with pytest.raises(WebSocketProvisioningError, match="not found"):
                await provision_ws_token("tm_acme")

    async def test_500_server_error(self, mock_tm):
        async def mock_post(url, json=None, headers=None):
            return _MockResponse(500, {})

        with patch(
            "specify_cli.auth.websocket.token_provisioning.httpx.AsyncClient"
        ) as mock_client:
            _install_mock_post(mock_client, mock_post)
            with pytest.raises(WebSocketProvisioningError, match="server error"):
                await provision_ws_token("tm_acme")

    async def test_network_error(self, mock_tm):
        async def mock_post(url, json=None, headers=None):
            raise httpx.RequestError("connection refused")

        with patch(
            "specify_cli.auth.websocket.token_provisioning.httpx.AsyncClient"
        ) as mock_client:
            _install_mock_post(mock_client, mock_post)
            with pytest.raises(NetworkError):
                await provision_ws_token("tm_acme")


class TestProvisionerErrorTranslation:
    """Branch coverage for the non-happy-path status codes."""

    async def test_401_authentication_required(self, mock_tm):
        async def mock_post(url, json=None, headers=None):
            return _MockResponse(401, {})

        with patch(
            "specify_cli.auth.websocket.token_provisioning.httpx.AsyncClient"
        ) as mock_client:
            _install_mock_post(mock_client, mock_post)
            with pytest.raises(
                WebSocketProvisioningError, match="Authentication required"
            ):
                await provision_ws_token("tm_acme")

    async def test_403_generic_forbidden(self, mock_tm):
        async def mock_post(url, json=None, headers=None):
            return _MockResponse(
                403,
                {"error": "other", "error_description": "quota exceeded"},
            )

        with patch(
            "specify_cli.auth.websocket.token_provisioning.httpx.AsyncClient"
        ) as mock_client:
            _install_mock_post(mock_client, mock_post)
            with pytest.raises(WebSocketProvisioningError, match="quota exceeded"):
                await provision_ws_token("tm_acme")

    async def test_unexpected_status_code(self, mock_tm):
        async def mock_post(url, json=None, headers=None):
            return _MockResponse(418, {})

        with patch(
            "specify_cli.auth.websocket.token_provisioning.httpx.AsyncClient"
        ) as mock_client:
            _install_mock_post(mock_client, mock_post)
            with pytest.raises(WebSocketProvisioningError, match="418"):
                await provision_ws_token("tm_acme")

    async def test_200_missing_required_field(self, mock_tm):
        """If the SaaS drops a required field, fail loudly rather than proceed."""
        async def mock_post(url, json=None, headers=None):
            return _MockResponse(
                200,
                {
                    "ws_token": "ws_xyz",
                    "ws_url": "wss://saas.test/ws",
                    # Missing expires_in and session_id.
                },
            )

        with patch(
            "specify_cli.auth.websocket.token_provisioning.httpx.AsyncClient"
        ) as mock_client:
            _install_mock_post(mock_client, mock_post)
            with pytest.raises(
                WebSocketProvisioningError, match="missing required fields"
            ):
                await provision_ws_token("tm_acme")


class TestProvisionerConstruction:
    """Sanity: the buffer is configurable and defaults to 300s."""

    def test_default_buffer_is_five_minutes(self):
        prov = WebSocketTokenProvisioner()
        assert prov._refresh_buffer == 300

    def test_custom_buffer(self):
        prov = WebSocketTokenProvisioner(refresh_buffer_seconds=42)
        assert prov._refresh_buffer == 42
