"""CliRunner tests for ``spec-kitty auth login`` (feature 080, WP04 T027).

These tests exercise the real Typer ``app`` exported by
``specify_cli.cli.commands.auth`` via :class:`typer.testing.CliRunner`.
Internal flow orchestration is mocked at the
``specify_cli.cli.commands._auth_login`` seam so we test the command-to-
implementation wiring without starting a loopback server or touching the
real keychain.

Key behaviors under test (per WP04 acceptance criteria):

- ``--help`` does not mention ``password`` or ``username``.
- Browser flow is dispatched by default.
- ``--headless`` dispatches to the device flow branch.
- Missing ``SPEC_KITTY_SAAS_URL`` surfaces a clear configuration error.
- ``--force`` triggers re-authentication even when already logged in.
- Already-authenticated users without ``--force`` see a friendly message.
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.auth import reset_token_manager
from specify_cli.auth.session import StoredSession, Team
from specify_cli.cli.commands.auth import app


runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_tm(monkeypatch):
    """Reset the process-wide TokenManager between tests.

    Also provides a default ``SPEC_KITTY_SAAS_URL`` so the flow can
    construct the config without erroring. Tests that need to verify the
    missing-config path delete the env var explicitly.
    """
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test")
    reset_token_manager()
    yield
    reset_token_manager()


def _make_session(email: str = "alice@example.com") -> StoredSession:
    now = datetime.now(UTC)
    return StoredSession(
        user_id="user-1",
        email=email,
        name="Alice",
        teams=[Team(id="t1", name="Team One", role="owner")],
        default_team_id="t1",
        access_token="access-xyz",
        refresh_token="refresh-xyz",
        session_id="sess-1",
        issued_at=now,
        access_token_expires_at=now + timedelta(hours=1),
        refresh_token_expires_at=now + timedelta(days=30),
        scope="offline_access",
        storage_backend="keychain",
        last_used_at=now,
        auth_method="authorization_code",
    )


# ---------------------------------------------------------------------------
# Help output
# ---------------------------------------------------------------------------


class TestAuthLoginHelp:
    """Verify the new command's help output does not mention legacy flags."""

    def test_help_does_not_mention_password(self):
        result = runner.invoke(app, ["login", "--help"])
        assert result.exit_code == 0
        stdout_lower = result.stdout.lower()
        assert "password" not in stdout_lower
        assert "username" not in stdout_lower

    def test_help_shows_new_flags(self):
        result = runner.invoke(app, ["login", "--help"])
        assert result.exit_code == 0
        assert "--headless" in result.stdout
        assert "--force" in result.stdout

    def test_help_describes_browser_flow(self):
        result = runner.invoke(app, ["login", "--help"])
        assert result.exit_code == 0
        assert "browser" in result.stdout.lower() or "oauth" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Dispatch (browser vs headless)
# ---------------------------------------------------------------------------


class TestAuthLoginDispatch:

    def test_default_dispatches_to_browser_flow(self):
        async def _noop(*args, **kwargs):
            return None

        with patch(
            "specify_cli.cli.commands._auth_login._run_browser_flow",
            new=AsyncMock(side_effect=_noop),
        ) as mock_browser, patch(
            "specify_cli.cli.commands._auth_login._run_device_flow",
            new=AsyncMock(side_effect=_noop),
        ) as mock_device:
            result = runner.invoke(app, ["login"])

        assert result.exit_code == 0, result.stdout
        assert mock_browser.called
        assert not mock_device.called

    def test_headless_dispatches_to_device_flow(self):
        async def _noop(*args, **kwargs):
            return None

        with patch(
            "specify_cli.cli.commands._auth_login._run_browser_flow",
            new=AsyncMock(side_effect=_noop),
        ) as mock_browser, patch(
            "specify_cli.cli.commands._auth_login._run_device_flow",
            new=AsyncMock(side_effect=_noop),
        ) as mock_device:
            result = runner.invoke(app, ["login", "--headless"])

        assert result.exit_code == 0, result.stdout
        assert mock_device.called
        assert not mock_browser.called


# ---------------------------------------------------------------------------
# Configuration errors
# ---------------------------------------------------------------------------


class TestAuthLoginConfigErrors:

    def test_missing_saas_url_exits_nonzero(self, monkeypatch):
        monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
        result = runner.invoke(app, ["login"])

        assert result.exit_code != 0
        assert "SPEC_KITTY_SAAS_URL" in result.stdout


# ---------------------------------------------------------------------------
# Already-authenticated / --force behavior
# ---------------------------------------------------------------------------


class TestAuthLoginAlreadyAuthenticated:

    def test_shows_friendly_message_when_already_logged_in(self):
        existing = _make_session()

        async def _noop(*args, **kwargs):
            return None

        with patch(
            "specify_cli.cli.commands._auth_login.get_token_manager"
        ) as mock_factory, patch(
            "specify_cli.cli.commands._auth_login._run_browser_flow",
            new=AsyncMock(side_effect=_noop),
        ) as mock_browser:
            mock_tm = mock_factory.return_value
            mock_tm.is_authenticated = True
            mock_tm.get_current_session.return_value = existing

            result = runner.invoke(app, ["login"])

        assert result.exit_code == 0, result.stdout
        assert "Already logged in" in result.stdout
        assert existing.email in result.stdout
        assert not mock_browser.called

    def test_force_reauthenticates_even_when_logged_in(self):
        existing = _make_session()

        async def _noop(*args, **kwargs):
            return None

        with patch(
            "specify_cli.cli.commands._auth_login.get_token_manager"
        ) as mock_factory, patch(
            "specify_cli.cli.commands._auth_login._run_browser_flow",
            new=AsyncMock(side_effect=_noop),
        ) as mock_browser:
            mock_tm = mock_factory.return_value
            mock_tm.is_authenticated = True
            mock_tm.get_current_session.return_value = existing

            result = runner.invoke(app, ["login", "--force"])

        assert result.exit_code == 0, result.stdout
        assert mock_browser.called
        mock_tm.clear_session.assert_called_once()

    def test_fresh_login_proceeds_when_not_authenticated(self):
        async def _noop(*args, **kwargs):
            return None

        with patch(
            "specify_cli.cli.commands._auth_login.get_token_manager"
        ) as mock_factory, patch(
            "specify_cli.cli.commands._auth_login._run_browser_flow",
            new=AsyncMock(side_effect=_noop),
        ) as mock_browser:
            mock_tm = mock_factory.return_value
            mock_tm.is_authenticated = False
            mock_tm.get_current_session.return_value = None

            result = runner.invoke(app, ["login"])

        assert result.exit_code == 0, result.stdout
        assert mock_browser.called


# ---------------------------------------------------------------------------
# Headless without WP05: clear "not yet implemented" error
# ---------------------------------------------------------------------------


class TestAuthLoginHeadlessWithoutWP05:

    def test_headless_without_device_code_module_fails_clearly(self):
        """Until WP05 ships ``auth.flows.device_code``, --headless must error clearly."""
        # Ensure no device_code module is importable — if WP05 ships it
        # in the same lane, this test turns into a no-op once the import
        # succeeds. We explicitly bypass the cache so the ImportError
        # branch is exercised.
        import sys

        dropped = sys.modules.pop("specify_cli.auth.flows.device_code", None)
        try:
            with patch(
                "specify_cli.cli.commands._auth_login.get_token_manager"
            ) as mock_factory:
                mock_tm = mock_factory.return_value
                mock_tm.is_authenticated = False
                mock_tm.get_current_session.return_value = None

                result = runner.invoke(app, ["login", "--headless"])
        finally:
            if dropped is not None:
                sys.modules["specify_cli.auth.flows.device_code"] = dropped

        # If the module already exists in the worktree (WP05 landed), the
        # flow succeeds. Otherwise it must exit non-zero with a clear
        # "not yet implemented" message.
        if dropped is None:
            assert result.exit_code != 0
            assert "not yet implemented" in result.stdout.lower() or "WP05" in result.stdout
