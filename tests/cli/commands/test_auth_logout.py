"""Unit + CliRunner tests for ``spec-kitty auth logout`` (feature 080, WP06).

Covers the four acceptance paths from WP06:

- **Not logged in**: prints a friendly notice, exits 0.
- **Happy path (server 200)**: calls the server, clears local session.
- **Server failure (FR-014)**: server call fails (network error), local
  session is STILL cleared.
- **``--force``**: skips the server call entirely, clears local session.

Every test drives the real Typer ``app`` from
``specify_cli.cli.commands.auth`` via :class:`typer.testing.CliRunner`
(T063 audit requirement) and mocks ``SecureStorage.from_environment`` so
no real auth store is touched. HTTP is mocked at the ``httpx.AsyncClient``
seam because the logout command uses :mod:`httpx` directly rather than
the (not-yet-landed) ``OAuthHttpClient`` transport from WP08.
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest
from typer.testing import CliRunner

from specify_cli.auth import reset_token_manager
from specify_cli.auth.session import StoredSession, Team
from specify_cli.cli.commands.auth import app


runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    """Reset the process-wide TokenManager between tests.

    Also sets ``SPEC_KITTY_SAAS_URL`` so ``get_saas_base_url`` succeeds
    without touching real config. Tests that verify the missing-config
    path delete the env var explicitly.
    """
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test")
    reset_token_manager()
    yield
    reset_token_manager()


def _make_session(
    *,
    access_remaining_seconds: int = 3600,
    refresh_remaining_days: int = 89,
) -> StoredSession:
    """Build a concrete StoredSession for logout tests.

    We use stable dummy token values (``at_xyz``/``rt_xyz``) because the
    test suite asserts they do NOT appear in stdout, i.e. the logout
    command must not leak tokens into its user-facing output.
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
        refresh_token_expires_at=now + timedelta(days=refresh_remaining_days),
        scope="offline_access",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )


def _mock_storage(session: StoredSession | None):
    """Build a Mock SecureStorage that returns ``session`` on ``read()``.

    ``delete`` is a ``MagicMock`` so tests can assert call counts to
    verify FR-014 (local credentials ARE cleared even on server failure).
    """
    storage = Mock()
    storage.read.return_value = session
    storage.write = Mock(return_value=None)
    storage.delete = MagicMock()
    storage.backend_name = "file"
    return storage


def _make_async_client_mock(post_side_effect):
    """Build a mock for ``httpx.AsyncClient`` whose ``post`` is awaitable.

    ``post_side_effect`` is either:

    - an object to return from ``await client.post(...)``, or
    - an Exception instance/class to raise from ``await client.post(...)``.

    The async-context-manager protocol is satisfied via ``AsyncMock`` so
    ``async with httpx.AsyncClient(...) as client:`` works as written.
    """
    async_client = MagicMock()
    async_client.__aenter__ = AsyncMock(return_value=async_client)
    async_client.__aexit__ = AsyncMock(return_value=None)

    if isinstance(post_side_effect, BaseException) or (
        isinstance(post_side_effect, type)
        and issubclass(post_side_effect, BaseException)
    ):
        async_client.post = AsyncMock(side_effect=post_side_effect)
    else:
        async_client.post = AsyncMock(return_value=post_side_effect)

    return async_client


# ---------------------------------------------------------------------------
# CliRunner E2E — drive ``auth logout`` through the live Typer app
# ---------------------------------------------------------------------------


class TestAuthLogoutCommand:
    """Exercise the full dispatch path: ``runner.invoke(app, ['logout'])``."""

    def test_not_logged_in(self):
        """No session -> friendly ``Not logged in`` notice, exit 0."""
        storage = _mock_storage(None)
        with patch(
            "specify_cli.auth.secure_storage.SecureStorage.from_environment",
            return_value=storage,
        ):
            reset_token_manager()
            result = runner.invoke(app, ["logout"])

        assert result.exit_code == 0, result.stdout
        assert "Not logged in" in result.stdout
        # No server call should have happened -> no local delete either,
        # because there was no session to clear in the first place.
        storage.delete.assert_not_called()

    def test_logout_success_server_200(self):
        """Happy path: server returns 200, local cleanup runs."""
        storage = _mock_storage(_make_session())

        response = MagicMock()
        response.status_code = 200
        async_client = _make_async_client_mock(response)

        with (
            patch(
                "specify_cli.auth.secure_storage.SecureStorage.from_environment",
                return_value=storage,
            ),
            patch(
                "specify_cli.cli.commands._auth_logout.httpx.AsyncClient",
                return_value=async_client,
            ),
        ):
            reset_token_manager()
            result = runner.invoke(app, ["logout"])

        assert result.exit_code == 0, result.stdout
        assert "Logged out" in result.stdout
        # Server was called.
        async_client.post.assert_awaited_once()
        called_url = async_client.post.call_args.args[0]
        assert called_url == "https://saas.test/api/v1/logout"
        # Verify bearer token header — kwargs-based assertion.
        headers = async_client.post.call_args.kwargs["headers"]
        assert headers == {"Authorization": "Bearer at_xyz"}
        # Verify NO body was sent (bearer-only endpoint contract).
        assert "json" not in async_client.post.call_args.kwargs
        assert "data" not in async_client.post.call_args.kwargs
        assert "content" not in async_client.post.call_args.kwargs
        # Local cleanup happened.
        storage.delete.assert_called_once()
        # Tokens must NOT leak into stdout.
        assert "at_xyz" not in result.stdout
        assert "rt_xyz" not in result.stdout

    def test_logout_server_failure_still_clears_local(self):
        """FR-014: network error MUST NOT block local credential deletion."""
        storage = _mock_storage(_make_session())

        async_client = _make_async_client_mock(httpx.RequestError("network down"))

        with (
            patch(
                "specify_cli.auth.secure_storage.SecureStorage.from_environment",
                return_value=storage,
            ),
            patch(
                "specify_cli.cli.commands._auth_logout.httpx.AsyncClient",
                return_value=async_client,
            ),
        ):
            reset_token_manager()
            result = runner.invoke(app, ["logout"])

        assert result.exit_code == 0, result.stdout
        # Warning printed.
        assert "Server logout failed" in result.stdout
        # Local cleanup still happened — THIS is the FR-014 assertion.
        assert "Logged out" in result.stdout
        storage.delete.assert_called_once()

    def test_logout_server_500_still_clears_local(self):
        """Server-side 5xx is downgraded to warning; local cleanup still runs."""
        storage = _mock_storage(_make_session())

        response = MagicMock()
        response.status_code = 500
        async_client = _make_async_client_mock(response)

        with (
            patch(
                "specify_cli.auth.secure_storage.SecureStorage.from_environment",
                return_value=storage,
            ),
            patch(
                "specify_cli.cli.commands._auth_logout.httpx.AsyncClient",
                return_value=async_client,
            ),
        ):
            reset_token_manager()
            result = runner.invoke(app, ["logout"])

        assert result.exit_code == 0, result.stdout
        assert "HTTP 500" in result.stdout
        assert "Logged out" in result.stdout
        storage.delete.assert_called_once()

    def test_logout_server_401_treated_as_already_invalid(self):
        """401 means the session was already invalid server-side — still clean locally."""
        storage = _mock_storage(_make_session())

        response = MagicMock()
        response.status_code = 401
        async_client = _make_async_client_mock(response)

        with (
            patch(
                "specify_cli.auth.secure_storage.SecureStorage.from_environment",
                return_value=storage,
            ),
            patch(
                "specify_cli.cli.commands._auth_logout.httpx.AsyncClient",
                return_value=async_client,
            ),
        ):
            reset_token_manager()
            result = runner.invoke(app, ["logout"])

        assert result.exit_code == 0, result.stdout
        # Friendly warning — session was already invalid.
        assert "already invalid" in result.stdout
        assert "Logged out" in result.stdout
        storage.delete.assert_called_once()

    def test_logout_force_skips_server(self):
        """``--force`` must skip the HTTP call and only delete locally."""
        storage = _mock_storage(_make_session())

        # Even though we patch AsyncClient, we expect it to NOT be called.
        response = MagicMock()
        response.status_code = 200
        async_client = _make_async_client_mock(response)

        with (
            patch(
                "specify_cli.auth.secure_storage.SecureStorage.from_environment",
                return_value=storage,
            ),
            patch(
                "specify_cli.cli.commands._auth_logout.httpx.AsyncClient",
                return_value=async_client,
            ),
        ):
            reset_token_manager()
            result = runner.invoke(app, ["logout", "--force"])

        assert result.exit_code == 0, result.stdout
        # Server was NOT called.
        async_client.post.assert_not_called()
        # Force-skip banner printed.
        assert "Skipping server revocation" in result.stdout
        # Local cleanup still ran.
        assert "Logged out" in result.stdout
        storage.delete.assert_called_once()

    def test_logout_missing_saas_url_proceeds_local_only(self, monkeypatch):
        """Missing ``SPEC_KITTY_SAAS_URL`` must NOT block local cleanup."""
        monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
        storage = _mock_storage(_make_session())

        # Patch AsyncClient to a mock that would explode if called — we
        # expect the config error to short-circuit before any HTTP attempt.
        async_client = _make_async_client_mock(
            httpx.RequestError("should not be called"),
        )

        with (
            patch(
                "specify_cli.auth.secure_storage.SecureStorage.from_environment",
                return_value=storage,
            ),
            patch(
                "specify_cli.cli.commands._auth_logout.httpx.AsyncClient",
                return_value=async_client,
            ),
        ):
            reset_token_manager()
            result = runner.invoke(app, ["logout"])

        assert result.exit_code == 0, result.stdout
        # Warning about config error.
        assert "config error" in result.stdout.lower()
        # Server was NOT called (config error short-circuited).
        async_client.post.assert_not_called()
        # Local cleanup still ran.
        assert "Logged out" in result.stdout
        storage.delete.assert_called_once()

    def test_logout_generic_exception_still_clears_local(self):
        """Unexpected exception during server call must not block local cleanup."""
        storage = _mock_storage(_make_session())

        async_client = _make_async_client_mock(RuntimeError("boom"))

        with (
            patch(
                "specify_cli.auth.secure_storage.SecureStorage.from_environment",
                return_value=storage,
            ),
            patch(
                "specify_cli.cli.commands._auth_logout.httpx.AsyncClient",
                return_value=async_client,
            ),
        ):
            reset_token_manager()
            result = runner.invoke(app, ["logout"])

        assert result.exit_code == 0, result.stdout
        assert "Server logout failed" in result.stdout
        assert "Logged out" in result.stdout
        storage.delete.assert_called_once()


# ---------------------------------------------------------------------------
# Direct import check — the dispatch shell in auth.py uses this exact path
# ---------------------------------------------------------------------------


def test_logout_impl_is_importable():
    """The dispatch shell does ``from ... import logout_impl`` — must work."""
    from specify_cli.cli.commands._auth_logout import logout_impl

    assert callable(logout_impl)
