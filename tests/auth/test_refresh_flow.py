"""Tests for :class:`TokenRefreshFlow` (feature 080, WP04 T027).

Unit tests for the refresh grant flow with mocked httpx. These tests
verify the four primary paths called out by WP04's acceptance criteria:

1. Happy path: ``200`` with rotated tokens returns an updated session.
2. ``400 invalid_grant`` raises :class:`RefreshTokenExpiredError`.
3. ``400 session_invalid`` raises :class:`SessionInvalidError`.
4. Transport-level failures raise :class:`NetworkError`.

Plus the refresh-TTL amendment behavior per C-012: the absolute
``refresh_token_expires_at`` is preferred, with a fallback to the
relative ``refresh_token_expires_in`` form.
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from specify_cli.auth.errors import (
    NetworkError,
    RefreshTokenExpiredError,
    SessionInvalidError,
    TokenRefreshError,
)
from specify_cli.auth.flows.refresh import TokenRefreshFlow
from specify_cli.auth.session import StoredSession, Team


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _saas_url(monkeypatch):
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test")
    yield


def _make_session(
    *,
    refresh_token: str = "refresh-v1",
    refresh_token_expires_at: datetime | None = None,
) -> StoredSession:
    now = datetime.now(UTC)
    return StoredSession(
        user_id="user-1",
        email="a@b.com",
        name="A B",
        teams=[Team(id="t1", name="T1", role="owner")],
        default_team_id="t1",
        access_token="access-v1",
        refresh_token=refresh_token,
        session_id="sess",
        issued_at=now,
        access_token_expires_at=now - timedelta(seconds=1),  # expired
        refresh_token_expires_at=refresh_token_expires_at,
        scope="offline_access",
        storage_backend="keychain",
        last_used_at=now,
        auth_method="authorization_code",
    )


def _mock_httpx_response(status_code: int, json_body: dict | None = None, text: str = ""):
    r = Mock(spec=httpx.Response)
    r.status_code = status_code
    r.text = text or (str(json_body) if json_body else "")
    r.json = Mock(return_value=json_body or {})
    return r


def _refresh_body(
    *,
    access_token: str = "access-v2",
    refresh_token: str | None = "refresh-v2",
    expires_in: int = 3600,
    refresh_token_expires_at: str | None = "2099-01-01T00:00:00+00:00",
    refresh_token_expires_in: int | None = None,
    scope: str = "offline_access",
) -> dict:
    body: dict = {
        "access_token": access_token,
        "expires_in": expires_in,
        "scope": scope,
    }
    if refresh_token is not None:
        body["refresh_token"] = refresh_token
    if refresh_token_expires_at is not None:
        body["refresh_token_expires_at"] = refresh_token_expires_at
    if refresh_token_expires_in is not None:
        body["refresh_token_expires_in"] = refresh_token_expires_in
    return body


# ---------------------------------------------------------------------------
# Happy path + updated session
# ---------------------------------------------------------------------------


class TestRefreshHappyPath:

    @pytest.mark.asyncio
    async def test_refresh_returns_updated_session(self):
        flow = TokenRefreshFlow()
        session = _make_session()
        body = _refresh_body()

        with patch("specify_cli.auth.flows.refresh.PublicHttpClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = _mock_httpx_response(200, body)

            updated = await flow.refresh(session)

        assert updated.access_token == "access-v2"
        assert updated.refresh_token == "refresh-v2"
        assert updated.session_id == "sess"  # preserved
        assert updated.user_id == "user-1"  # preserved
        assert updated.email == "a@b.com"  # preserved
        assert updated.default_team_id == "t1"  # preserved
        assert updated.refresh_token_expires_at == datetime(2099, 1, 1, tzinfo=UTC)

    @pytest.mark.asyncio
    async def test_refresh_keeps_old_refresh_token_when_not_rotated(self):
        flow = TokenRefreshFlow()
        session = _make_session(refresh_token="refresh-v1")
        body = _refresh_body(refresh_token=None)

        with patch("specify_cli.auth.flows.refresh.PublicHttpClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = _mock_httpx_response(200, body)

            updated = await flow.refresh(session)

        assert updated.refresh_token == "refresh-v1"
        assert updated.access_token == "access-v2"

    @pytest.mark.asyncio
    async def test_refresh_posts_to_correct_endpoint(self):
        flow = TokenRefreshFlow()
        session = _make_session()
        body = _refresh_body()

        with patch("specify_cli.auth.flows.refresh.PublicHttpClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = _mock_httpx_response(200, body)

            await flow.refresh(session)

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://saas.test/oauth/token"
        posted_data = call_args[1]["data"]
        assert posted_data["grant_type"] == "refresh_token"
        assert posted_data["refresh_token"] == "refresh-v1"
        assert posted_data["client_id"] == "cli_native"


# ---------------------------------------------------------------------------
# Refresh-TTL amendment behavior (C-012 / 2026-04-09)
# ---------------------------------------------------------------------------


class TestRefreshTTLAmendment:

    @pytest.mark.asyncio
    async def test_absolute_expires_at_is_preferred(self):
        """When both absolute and relative forms are present, absolute wins."""
        flow = TokenRefreshFlow()
        session = _make_session()
        body = _refresh_body(
            refresh_token_expires_at="2099-06-01T00:00:00+00:00",
            refresh_token_expires_in=86400,
        )

        with patch("specify_cli.auth.flows.refresh.PublicHttpClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = _mock_httpx_response(200, body)

            updated = await flow.refresh(session)

        assert updated.refresh_token_expires_at == datetime(2099, 6, 1, tzinfo=UTC)

    @pytest.mark.asyncio
    async def test_falls_back_to_expires_in(self):
        """When only the relative form is present, compute expires_at from it."""
        flow = TokenRefreshFlow()
        session = _make_session()
        body = _refresh_body(
            refresh_token_expires_at=None,
            refresh_token_expires_in=3600,
        )

        before = datetime.now(UTC)
        with patch("specify_cli.auth.flows.refresh.PublicHttpClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = _mock_httpx_response(200, body)

            updated = await flow.refresh(session)
        after = datetime.now(UTC)

        assert updated.refresh_token_expires_at is not None
        delta = updated.refresh_token_expires_at - before
        assert timedelta(seconds=3595) <= delta <= timedelta(seconds=3605)
        assert updated.refresh_token_expires_at <= after + timedelta(seconds=3600)

    @pytest.mark.asyncio
    async def test_z_suffix_accepted(self):
        flow = TokenRefreshFlow()
        session = _make_session()
        body = _refresh_body(refresh_token_expires_at="2099-01-01T00:00:00Z")

        with patch("specify_cli.auth.flows.refresh.PublicHttpClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = _mock_httpx_response(200, body)

            updated = await flow.refresh(session)

        assert updated.refresh_token_expires_at == datetime(2099, 1, 1, tzinfo=UTC)

    @pytest.mark.asyncio
    async def test_preserves_prior_expiry_when_response_omits_both_forms(self):
        """Non-compliant server: last-resort fallback preserves prior expiry."""
        flow = TokenRefreshFlow()
        prior = datetime(2099, 1, 1, tzinfo=UTC)
        session = _make_session(refresh_token_expires_at=prior)
        body = _refresh_body(
            refresh_token_expires_at=None,
            refresh_token_expires_in=None,
        )

        with patch("specify_cli.auth.flows.refresh.PublicHttpClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = _mock_httpx_response(200, body)

            updated = await flow.refresh(session)

        assert updated.refresh_token_expires_at == prior


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestRefreshErrors:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [400, 401])
    async def test_invalid_grant_raises_expired(self, status_code):
        flow = TokenRefreshFlow()
        session = _make_session()

        with patch("specify_cli.auth.flows.refresh.PublicHttpClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = _mock_httpx_response(
                status_code, {"error": "invalid_grant"}
            )

            with pytest.raises(RefreshTokenExpiredError):
                await flow.refresh(session)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [400, 401])
    async def test_session_invalid_raises_session_invalid(self, status_code):
        flow = TokenRefreshFlow()
        session = _make_session()

        with patch("specify_cli.auth.flows.refresh.PublicHttpClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = _mock_httpx_response(
                status_code, {"error": "session_invalid"}
            )

            with pytest.raises(SessionInvalidError):
                await flow.refresh(session)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [400, 401])
    async def test_unknown_error_raises_token_refresh_error(self, status_code):
        flow = TokenRefreshFlow()
        session = _make_session()

        with patch("specify_cli.auth.flows.refresh.PublicHttpClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = _mock_httpx_response(
                status_code, {"error": "mystery"}, text="mystery error"
            )

            with pytest.raises(TokenRefreshError):
                await flow.refresh(session)

    @pytest.mark.asyncio
    async def test_500_raises_token_refresh_error(self):
        flow = TokenRefreshFlow()
        session = _make_session()

        with patch("specify_cli.auth.flows.refresh.PublicHttpClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = _mock_httpx_response(
                500, {}, text="internal"
            )

            with pytest.raises(TokenRefreshError, match="HTTP 500"):
                await flow.refresh(session)

    @pytest.mark.asyncio
    async def test_network_error_raises_network_error(self):
        flow = TokenRefreshFlow()
        session = _make_session()

        with patch("specify_cli.auth.flows.refresh.PublicHttpClient") as mock_cls:
            mock_client = AsyncMock()
            mock_cls.return_value.__aenter__.return_value = mock_client
            # PublicHttpClient wraps httpx.RequestError as NetworkError internally;
            # the flow now catches NetworkError from the client directly.
            mock_client.post.side_effect = NetworkError("DNS failed")

            with pytest.raises(NetworkError, match="Network error during refresh"):
                await flow.refresh(session)
