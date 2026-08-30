"""CliRunner tests for ``spec-kitty auth login`` (feature 080, WP04 T027).

These tests exercise the real Typer ``app`` exported by
``specify_cli.cli.commands.auth`` via :class:`typer.testing.CliRunner`.
Internal flow orchestration is mocked at the
``specify_cli.cli.commands._auth_login`` seam so we test the command-to-
implementation wiring without starting a loopback server or touching the
real auth store.

Key behaviors under test (per WP04 acceptance criteria):

- ``--help`` does not mention ``password`` or ``username``.
- Browser flow is dispatched by default.
- ``--headless`` dispatches to the device flow branch.
- Missing ``SPEC_KITTY_SAAS_URL`` surfaces a clear configuration error.
- ``--force`` triggers re-authentication even when already logged in.
- Already-authenticated users without ``--force`` see a friendly message.
"""

from __future__ import annotations

from kernel.clock import timedelta, now_utc
import re
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.auth import reset_token_manager
from specify_cli.auth.errors import (
    AuthenticationError,
    BrowserLaunchError,
    CallbackValidationError,
)
from specify_cli.auth.session import StoredSession, Team
from specify_cli.cli.commands.auth import app


pytestmark = [pytest.mark.integration]

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


def _make_session(
    email: str = "alice@example.com",
    team_name: str = "Team One",
    is_private_teamspace: bool = False,
) -> StoredSession:
    now = now_utc()
    return StoredSession(
        user_id="user-1",
        email=email,
        name="Alice",
        teams=[
            Team(
                id="t1",
                name=team_name,
                role="owner",
                is_private_teamspace=is_private_teamspace,
            )
        ],
        default_team_id="t1",
        access_token="access-xyz",
        refresh_token="refresh-xyz",
        session_id="sess-1",
        issued_at=now,
        access_token_expires_at=now + timedelta(hours=1),
        refresh_token_expires_at=now + timedelta(days=30),
        scope="offline_access",
        storage_backend="file",
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
        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
        assert "--headless" in plain
        assert "--force" in plain

    def test_help_describes_browser_flow(self):
        result = runner.invoke(app, ["login", "--help"])
        assert result.exit_code == 0
        assert "browser" in result.stdout.lower() or "oauth" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Dispatch (browser vs headless)
# ---------------------------------------------------------------------------


class TestAuthLoginDispatch:
    def test_login_no_longer_calls_teamspace_mission_state_gate(self):
        """Phase 6 (issue #1288): identity acquisition is decoupled from
        TeamSpace mission-state readiness. The gate symbol must not be
        imported into the auth-login module and the command must not
        consult it. Sync / tracker / connect commands continue to gate
        themselves — that's their job, not auth's."""
        import specify_cli.cli.commands._auth_login as auth_login_module

        # The gate symbol must not be importable from the auth-login
        # module: even an indirect re-export would re-create the wrong
        # coupling.
        assert not hasattr(auth_login_module, "enforce_teamspace_mission_state_ready")

    def test_login_proceeds_even_if_teamspace_mission_state_is_blocked(self):
        """Belt-and-suspenders for the structural guarantee above: even
        if the gate were called somehow, blocking it must not block
        identity acquisition. Patches the gate to raise, then verifies
        the login impl never invokes it."""
        async def _noop_browser_flow(*_args, **_kwargs):
            return None

        with patch(
            "specify_cli.cli.commands._teamspace_mission_state_gate.enforce_teamspace_mission_state_ready",
            side_effect=AssertionError("auth login must not invoke the TeamSpace gate"),
        ), patch(
            "specify_cli.cli.commands._auth_login._run_browser_flow",
            new=AsyncMock(side_effect=_noop_browser_flow),
        ):
            result = runner.invoke(app, ["login"])

        assert result.exit_code == 0, result.stdout

    def test_default_dispatches_to_browser_flow(self):
        async def _noop(*args, **kwargs):
            return None

        with patch(
            "specify_cli.cli.commands._auth_login.get_token_manager"
        ) as mock_factory, patch(
            "specify_cli.cli.commands._auth_login._run_browser_flow",
            new=AsyncMock(side_effect=_noop),
        ) as mock_browser, patch(
            "specify_cli.cli.commands._auth_login._run_device_flow",
            new=AsyncMock(side_effect=_noop),
        ) as mock_device:
            mock_factory.return_value.is_authenticated = False
            result = runner.invoke(app, ["login"])

        assert result.exit_code == 0, result.stdout
        assert mock_browser.called
        assert not mock_device.called

    def test_headless_dispatches_to_device_flow(self):
        async def _noop(*args, **kwargs):
            return None

        with patch(
            "specify_cli.cli.commands._auth_login.get_token_manager"
        ) as mock_factory, patch(
            "specify_cli.cli.commands._auth_login._run_browser_flow",
            new=AsyncMock(side_effect=_noop),
        ) as mock_browser, patch(
            "specify_cli.cli.commands._auth_login._run_device_flow",
            new=AsyncMock(side_effect=_noop),
        ) as mock_device:
            mock_factory.return_value.is_authenticated = False
            result = runner.invoke(app, ["login", "--headless"])

        assert result.exit_code == 0, result.stdout
        assert mock_device.called
        assert not mock_browser.called


# ---------------------------------------------------------------------------
# Configuration errors
# ---------------------------------------------------------------------------


class TestAuthLoginConfigErrors:

    def test_missing_env_and_config_exits_nonzero(self, monkeypatch):
        # #3406 FR-005: with NEITHER SPEC_KITTY_SAAS_URL nor a configured
        # `[sync].server_url`, login refuses rather than silently targeting the
        # descriptive dev default. The remedy names both ways to set a server.
        monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
        result = runner.invoke(app, ["login"])

        assert result.exit_code != 0
        assert "No hosted server is configured" in result.stdout
        assert "SPEC_KITTY_SAAS_URL" in result.stdout
        # #182: unescaped, Rich markup parses "[sync]" as a style tag and
        # silently drops it from the remedy.
        assert "[sync].server_url" in result.stdout

    def test_missing_env_uses_configured_sync_server_url(self, monkeypatch, tmp_path):
        # #3406 FR-005: the actual bug. When the env var is unset but the user
        # already set a server via `[sync].server_url` in the runtime root's
        # config.toml (the former `spec-kitty sync server <url>` writer died
        # with the sync transport, issue #5), login must use that configured
        # server_url (the same target sync used) instead of erroring.
        runtime_root = tmp_path / "runtime-root"
        runtime_root.mkdir(parents=True)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime_root))
        monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
        (runtime_root / "config.toml").write_text(
            '[sync]\nserver_url = "https://configured.example"\n', encoding="utf-8"
        )

        async def _noop(*_args, **_kwargs):
            return None

        with patch(
            "specify_cli.cli.commands._auth_login.get_token_manager"
        ) as mock_factory, patch(
            "specify_cli.cli.commands._auth_login._run_browser_flow",
            new=AsyncMock(side_effect=_noop),
        ) as mock_browser:
            mock_factory.return_value.is_authenticated = False
            result = runner.invoke(app, ["login"])

        assert result.exit_code == 0, result.stdout
        assert mock_browser.called
        # Login resolved the configured server_url and handed it to the flow.
        assert mock_browser.call_args.args[1] == "https://configured.example"

    def test_blank_configured_server_url_still_refuses(self, monkeypatch, tmp_path):
        # #182 squad MAJOR: `server_url = ""` names no endpoint, so login must
        # refuse exactly as it does when `[sync].server_url` is absent — not
        # treat the blank string as a configured (but empty) endpoint.
        runtime_root = tmp_path / "runtime-root"
        runtime_root.mkdir(parents=True)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime_root))
        monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
        (runtime_root / "config.toml").write_text(
            '[sync]\nserver_url = ""\n', encoding="utf-8"
        )

        result = runner.invoke(app, ["login"])

        assert result.exit_code != 0
        assert "No hosted server is configured" in result.stdout


class TestAuthLoginSaasLineRendering:
    def test_saas_line_renders_server_url_containing_bracket_markup(
        self, monkeypatch, tmp_path
    ):
        """#202: ``_run_browser_flow`` interpolated the configured
        ``server_url`` into a Rich ``[dim]`` line unescaped, so a value
        containing a closing-tag-like substring (``https://x.test[/]``) raised
        ``rich.markup.MarkupError`` out of ``console.print`` and crashed login
        before the OAuth flow could start. The URL must render verbatim."""
        bracketed = "https://x.test[/]"
        runtime_root = tmp_path / "runtime-root"
        runtime_root.mkdir(parents=True)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime_root))
        monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
        (runtime_root / "config.toml").write_text(
            f'[sync]\nserver_url = "{bracketed}"\n', encoding="utf-8"
        )

        async def _noop_login(*_args, **_kwargs):
            return _make_session()

        with patch(
            "specify_cli.cli.commands._auth_login.get_token_manager"
        ) as mock_factory, patch(
            "specify_cli.auth.flows.authorization_code.AuthorizationCodeFlow"
        ) as mock_flow_cls:
            mock_factory.return_value.is_authenticated = False
            mock_flow_cls.return_value.login = AsyncMock(side_effect=_noop_login)
            result = runner.invoke(app, ["login"])

        assert result.exit_code == 0, result.stdout
        # Rendered verbatim — no MarkupError, no swallowed markup tags.
        assert f"SaaS: {bracketed}" in result.stdout


class TestAuthLoginErrorMessageEscaping:
    """#526: exception text printed on login error paths can carry a raw,
    server-controlled body (e.g. a non-200 token-exchange response). Unescaped,
    a value containing a closing-tag-like substring raises
    ``rich.errors.MarkupError`` out of ``console.print`` instead of a clean
    non-zero exit with a readable diagnostic."""

    @pytest.mark.parametrize(
        ("headless", "flow_class", "error_type", "expected_prefix"),
        [
            (
                False,
                "specify_cli.auth.flows.authorization_code.AuthorizationCodeFlow",
                CallbackValidationError,
                "Callback validation failed",
            ),
            (
                False,
                "specify_cli.auth.flows.authorization_code.AuthorizationCodeFlow",
                BrowserLaunchError,
                "Could not launch browser",
            ),
            (
                False,
                "specify_cli.auth.flows.authorization_code.AuthorizationCodeFlow",
                AuthenticationError,
                "Authentication failed",
            ),
            (
                True,
                "specify_cli.auth.flows.device_code.DeviceCodeFlow",
                AuthenticationError,
                "Device flow failed",
            ),
        ],
        ids=("callback-validation", "browser-launch", "browser-auth", "device-auth"),
    )
    def test_markup_like_exception_text_does_not_crash(
        self,
        monkeypatch,
        tmp_path,
        headless,
        flow_class,
        error_type,
        expected_prefix,
    ):
        runtime_root = tmp_path / "runtime-root"
        runtime_root.mkdir(parents=True)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(runtime_root))
        monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test")

        hostile_body = "Token exchange failed: HTTP 400 - bad [/] token"

        async def _raise_auth_error(*_args, **_kwargs):
            raise error_type(hostile_body)

        with patch(
            "specify_cli.cli.commands._auth_login.get_token_manager"
        ) as mock_factory, patch(flow_class) as mock_flow_cls:
            mock_factory.return_value.is_authenticated = False
            mock_flow_cls.return_value.login = AsyncMock(
                side_effect=_raise_auth_error
            )
            args = ["login", "--headless"] if headless else ["login"]
            result = runner.invoke(app, args)

        # A clean non-zero exit, not an unhandled MarkupError traceback.
        assert result.exit_code == 1, result.stdout
        assert "MarkupError" not in result.stdout
        assert expected_prefix in result.stdout
        assert hostile_body in result.stdout


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

    def test_renders_bracket_markup_in_existing_session_email(self):
        existing = _make_session(email="alice[/]@example.com")

        with patch(
            "specify_cli.cli.commands._auth_login.get_token_manager"
        ) as mock_factory:
            mock_tm = mock_factory.return_value
            mock_tm.is_authenticated = True
            mock_tm.get_current_session.return_value = existing

            result = runner.invoke(app, ["login"])

        assert result.exit_code == 0, result.stdout
        assert "Already logged in as alice[/]@example.com" in result.stdout
        assert "MarkupError" not in result.stdout

    def test_renders_bracket_markup_in_success_email(self):
        session = _make_session(email="alice[/]@example.com")

        async def _login(*_args, **_kwargs):
            return session

        with patch(
            "specify_cli.cli.commands._auth_login.get_token_manager"
        ) as mock_factory, patch(
            "specify_cli.auth.flows.authorization_code.AuthorizationCodeFlow"
        ) as mock_flow_cls:
            mock_factory.return_value.is_authenticated = False
            mock_flow_cls.return_value.login = AsyncMock(side_effect=_login)
            result = runner.invoke(app, ["login"])

        assert result.exit_code == 0, result.stdout
        assert "Authenticated as alice[/]@example.com" in result.stdout
        assert "MarkupError" not in result.stdout

    def test_renders_bracket_markup_in_private_team_name_with_suffix(self):
        session = _make_session(
            team_name="A[/]C", is_private_teamspace=True
        )

        async def _login(*_args, **_kwargs):
            return session

        with patch(
            "specify_cli.cli.commands._auth_login.get_token_manager"
        ) as mock_factory, patch(
            "specify_cli.auth.flows.authorization_code.AuthorizationCodeFlow"
        ) as mock_flow_cls:
            mock_factory.return_value.is_authenticated = False
            mock_flow_cls.return_value.login = AsyncMock(side_effect=_login)
            result = runner.invoke(app, ["login"])

        assert result.exit_code == 0, result.stdout
        assert "Default team: A[/]C [Private Teamspace]" in result.stdout
        assert "MarkupError" not in result.stdout

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
