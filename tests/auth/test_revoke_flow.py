"""Unit tests for :class:`RevokeFlow` (WP02, T007).

Tests cover the four ``RevokeOutcome`` values:
- REVOKED: 200 + {"revoked": true}
- SERVER_FAILURE: 200 unexpected body, 5xx, 429, unexpected exception
- NETWORK_ERROR: httpx.RequestError subclass
- NO_REFRESH_TOKEN: session has no refresh token

All HTTP calls are mocked at the ``httpx.AsyncClient`` seam so no real
network traffic occurs. The test for request shape verifies:
- URL is ``/oauth/revoke``
- Body contains ``token=`` and ``token_type_hint=refresh_token``
- NO ``Authorization`` header is sent
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from specify_cli.auth.flows.revoke import RevokeFlow, RevokeOutcome
from specify_cli.auth.session import StoredSession, Team


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _saas_url(monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test")
    yield


def _make_session(*, refresh_token: str = "rfs.sessionid.secret") -> StoredSession:
    """Build a minimal StoredSession for revoke tests."""
    now = datetime.now(UTC)
    return StoredSession(
        user_id="u_test",
        email="test@example.com",
        name="Test User",
        teams=[Team(id="tm_test", name="Test", role="member")],
        default_team_id="tm_test",
        access_token="at_test",
        refresh_token=refresh_token,
        session_id="sess_test",
        issued_at=now,
        access_token_expires_at=now + timedelta(hours=1),
        refresh_token_expires_at=now + timedelta(days=89),
        scope="offline_access",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )


def _make_response(status_code: int, json_body: dict | None = None) -> MagicMock:
    """Build a mock httpx.Response."""
    response = MagicMock()
    response.status_code = status_code
    if json_body is not None:
        response.json = MagicMock(return_value=json_body)
    else:
        response.json = MagicMock(side_effect=ValueError("no JSON"))
    return response


def _make_async_client(post_return=None, post_side_effect=None) -> MagicMock:
    """Build a mock httpx.AsyncClient context manager."""
    async_client = MagicMock()
    async_client.__aenter__ = AsyncMock(return_value=async_client)
    async_client.__aexit__ = AsyncMock(return_value=None)
    if post_side_effect is not None:
        async_client.post = AsyncMock(side_effect=post_side_effect)
    else:
        async_client.post = AsyncMock(return_value=post_return)
    return async_client


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_revoke_200_revoked_true():
    """200 + {"revoked": true} -> REVOKED."""
    session = _make_session()
    response = _make_response(200, {"revoked": True})
    async_client = _make_async_client(post_return=response)

    with patch(
        "specify_cli.auth.flows.revoke.httpx.AsyncClient",
        return_value=async_client,
    ):
        outcome = await RevokeFlow().revoke(session)

    assert outcome is RevokeOutcome.REVOKED


@pytest.mark.asyncio
async def test_revoke_200_unexpected_body():
    """200 + {"status": "ok"} -> SERVER_FAILURE (body doesn't match contract)."""
    session = _make_session()
    response = _make_response(200, {"status": "ok"})
    async_client = _make_async_client(post_return=response)

    with patch(
        "specify_cli.auth.flows.revoke.httpx.AsyncClient",
        return_value=async_client,
    ):
        outcome = await RevokeFlow().revoke(session)

    assert outcome is RevokeOutcome.SERVER_FAILURE


@pytest.mark.asyncio
async def test_revoke_500():
    """5xx -> SERVER_FAILURE (never REVOKED)."""
    session = _make_session()
    response = _make_response(500)
    async_client = _make_async_client(post_return=response)

    with patch(
        "specify_cli.auth.flows.revoke.httpx.AsyncClient",
        return_value=async_client,
    ):
        outcome = await RevokeFlow().revoke(session)

    assert outcome is RevokeOutcome.SERVER_FAILURE


@pytest.mark.asyncio
async def test_revoke_429():
    """429 throttle -> SERVER_FAILURE."""
    session = _make_session()
    response = _make_response(429)
    async_client = _make_async_client(post_return=response)

    with patch(
        "specify_cli.auth.flows.revoke.httpx.AsyncClient",
        return_value=async_client,
    ):
        outcome = await RevokeFlow().revoke(session)

    assert outcome is RevokeOutcome.SERVER_FAILURE


@pytest.mark.asyncio
async def test_revoke_network_error():
    """httpx.ConnectError -> NETWORK_ERROR."""
    session = _make_session()
    async_client = _make_async_client(post_side_effect=httpx.ConnectError("DNS failure"))

    with patch(
        "specify_cli.auth.flows.revoke.httpx.AsyncClient",
        return_value=async_client,
    ):
        outcome = await RevokeFlow().revoke(session)

    assert outcome is RevokeOutcome.NETWORK_ERROR


@pytest.mark.asyncio
async def test_revoke_no_refresh_token():
    """Empty refresh_token -> NO_REFRESH_TOKEN, no HTTP call made."""
    session = _make_session(refresh_token="")
    async_client = _make_async_client(post_return=_make_response(200, {"revoked": True}))

    with patch(
        "specify_cli.auth.flows.revoke.httpx.AsyncClient",
        return_value=async_client,
    ):
        outcome = await RevokeFlow().revoke(session)

    assert outcome is RevokeOutcome.NO_REFRESH_TOKEN
    # No HTTP call should have been made.
    async_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_revoke_request_shape():
    """Verify URL is /oauth/revoke, body has token= and token_type_hint=refresh_token,
    NO Authorization header."""
    session = _make_session(refresh_token="rfs.sessionid.secret")
    response = _make_response(200, {"revoked": True})
    async_client = _make_async_client(post_return=response)

    with patch(
        "specify_cli.auth.flows.revoke.httpx.AsyncClient",
        return_value=async_client,
    ):
        outcome = await RevokeFlow().revoke(session)

    assert outcome is RevokeOutcome.REVOKED
    async_client.post.assert_awaited_once()

    call_args = async_client.post.call_args
    # URL must be /oauth/revoke
    called_url = call_args.args[0]
    assert called_url == "https://saas.test/oauth/revoke"

    # Body must contain token and token_type_hint
    called_data = call_args.kwargs.get("data", {})
    assert called_data.get("token") == "rfs.sessionid.secret"
    assert called_data.get("token_type_hint") == "refresh_token"

    # NO Authorization header
    called_kwargs = call_args.kwargs
    headers = called_kwargs.get("headers", {})
    assert "Authorization" not in headers
    assert "authorization" not in headers


@pytest.mark.asyncio
async def test_revoke_unexpected_exception_is_server_failure():
    """Non-httpx exception -> SERVER_FAILURE (never raises)."""
    session = _make_session()
    async_client = _make_async_client(post_side_effect=RuntimeError("unexpected boom"))

    with patch(
        "specify_cli.auth.flows.revoke.httpx.AsyncClient",
        return_value=async_client,
    ):
        outcome = await RevokeFlow().revoke(session)

    assert outcome is RevokeOutcome.SERVER_FAILURE
