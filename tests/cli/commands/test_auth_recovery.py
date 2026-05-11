"""Unit tests for ``specify_cli.cli.commands._auth_recovery`` (Mission 7, #829)."""

from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console

from specify_cli.cli.commands import _auth_recovery as recovery
from specify_cli.cli.commands._auth_recovery import (
    EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE,
    RecoveryOutcome,
    detect_logged_out_with_connected_teamspace,
    handle_unauthenticated_with_teamspace,
    is_interactive,
    offer_login_recovery,
)


pytestmark = pytest.mark.fast


def _make_console() -> tuple[Console, io.StringIO]:
    buf = io.StringIO()
    return Console(file=buf, force_terminal=False, width=120), buf


# ---------------------------------------------------------------------------
# detect_logged_out_with_connected_teamspace
# ---------------------------------------------------------------------------


class TestDetector:
    """Read-only detector covering all five resolution branches."""

    def test_valid_session_returns_none(self, monkeypatch):
        tm = MagicMock()
        tm.is_authenticated = True
        monkeypatch.setattr(
            "specify_cli.auth.get_token_manager",
            lambda: tm,
        )
        assert detect_logged_out_with_connected_teamspace() is None

    def test_routing_repo_slug_wins(self, monkeypatch):
        tm = MagicMock()
        tm.is_authenticated = False
        monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: tm)
        routing = SimpleNamespace(repo_slug="acme-eng", project_slug="acme")
        monkeypatch.setattr(
            "specify_cli.sync.routing.resolve_checkout_sync_routing",
            lambda: routing,
        )
        assert detect_logged_out_with_connected_teamspace() == "acme-eng"

    def test_routing_falls_back_to_project_slug(self, monkeypatch):
        tm = MagicMock()
        tm.is_authenticated = False
        monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: tm)
        routing = SimpleNamespace(repo_slug=None, project_slug="acme")
        monkeypatch.setattr(
            "specify_cli.sync.routing.resolve_checkout_sync_routing",
            lambda: routing,
        )
        assert detect_logged_out_with_connected_teamspace() == "acme"

    def test_falls_back_to_stored_private_team_name(self, monkeypatch):
        team = SimpleNamespace(name="Engineering", is_private_teamspace=True)
        session = SimpleNamespace(teams=[team])
        tm = MagicMock()
        tm.is_authenticated = False
        tm.get_current_session.return_value = session
        monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: tm)
        monkeypatch.setattr(
            "specify_cli.sync.routing.resolve_checkout_sync_routing",
            lambda: None,
        )
        assert detect_logged_out_with_connected_teamspace() == "Engineering"

    def test_nothing_known_returns_none(self, monkeypatch):
        tm = MagicMock()
        tm.is_authenticated = False
        tm.get_current_session.return_value = None
        monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: tm)
        monkeypatch.setattr(
            "specify_cli.sync.routing.resolve_checkout_sync_routing",
            lambda: None,
        )
        assert detect_logged_out_with_connected_teamspace() is None

    def test_routing_slug_whitespace_only_is_ignored(self, monkeypatch):
        tm = MagicMock()
        tm.is_authenticated = False
        tm.get_current_session.return_value = None
        monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: tm)
        routing = SimpleNamespace(repo_slug="   ", project_slug="")
        monkeypatch.setattr(
            "specify_cli.sync.routing.resolve_checkout_sync_routing",
            lambda: routing,
        )
        assert detect_logged_out_with_connected_teamspace() is None


# ---------------------------------------------------------------------------
# is_interactive
# ---------------------------------------------------------------------------


class TestIsInteractive:
    def test_tty_no_env_is_true(self, monkeypatch):
        monkeypatch.delenv("SPEC_KITTY_NON_INTERACTIVE", raising=False)
        monkeypatch.delenv("SPEC_KITTY_FORCE_INTERACTIVE", raising=False)
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        assert is_interactive() is True

    def test_non_interactive_env_disables(self, monkeypatch):
        monkeypatch.delenv("SPEC_KITTY_FORCE_INTERACTIVE", raising=False)
        monkeypatch.setenv("SPEC_KITTY_NON_INTERACTIVE", "1")
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        assert is_interactive() is False

    def test_no_tty_returns_false(self, monkeypatch):
        monkeypatch.delenv("SPEC_KITTY_NON_INTERACTIVE", raising=False)
        monkeypatch.delenv("SPEC_KITTY_FORCE_INTERACTIVE", raising=False)
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        assert is_interactive() is False

    def test_force_interactive_env_overrides(self, monkeypatch):
        monkeypatch.setenv("SPEC_KITTY_FORCE_INTERACTIVE", "1")
        monkeypatch.setenv("SPEC_KITTY_NON_INTERACTIVE", "1")
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        assert is_interactive() is True


# ---------------------------------------------------------------------------
# offer_login_recovery
# ---------------------------------------------------------------------------


class TestOfferLoginRecovery:
    def test_choice_l_invokes_login_and_returns_logged_in(self, monkeypatch):
        console, _ = _make_console()
        monkeypatch.setattr(recovery, "_read_one_keystroke", lambda: "l")
        mock_login = AsyncMock()
        with patch(
            "specify_cli.cli.commands._auth_login.login_impl",
            mock_login,
        ):
            result = offer_login_recovery(
                teamspace="acme-eng",
                command_name="sync now",
                console=console,
            )
        assert result is RecoveryOutcome.LOGGED_IN
        mock_login.assert_awaited_once()

    def test_choice_s_returns_skipped_without_login(self, monkeypatch):
        console, _ = _make_console()
        monkeypatch.setattr(recovery, "_read_one_keystroke", lambda: "s")
        mock_login = AsyncMock()
        with patch(
            "specify_cli.cli.commands._auth_login.login_impl",
            mock_login,
        ):
            result = offer_login_recovery(
                teamspace="acme-eng",
                command_name="sync now",
                console=console,
            )
        assert result is RecoveryOutcome.SKIPPED
        mock_login.assert_not_called()

    def test_choice_q_returns_quit(self, monkeypatch):
        console, _ = _make_console()
        monkeypatch.setattr(recovery, "_read_one_keystroke", lambda: "q")
        result = offer_login_recovery(
            teamspace="acme-eng",
            command_name="sync now",
            console=console,
        )
        assert result is RecoveryOutcome.QUIT

    def test_unknown_input_is_treated_as_skip(self, monkeypatch):
        console, _ = _make_console()
        monkeypatch.setattr(recovery, "_read_one_keystroke", lambda: "x")
        result = offer_login_recovery(
            teamspace="acme-eng",
            command_name="sync now",
            console=console,
        )
        assert result is RecoveryOutcome.SKIPPED

    def test_login_failure_is_caught_and_skipped(self, monkeypatch):
        from specify_cli.auth.errors import AuthenticationError

        console, buf = _make_console()
        monkeypatch.setattr(recovery, "_read_one_keystroke", lambda: "l")
        mock_login = AsyncMock(side_effect=AuthenticationError("nope"))
        with patch(
            "specify_cli.cli.commands._auth_login.login_impl",
            mock_login,
        ):
            result = offer_login_recovery(
                teamspace="acme-eng",
                command_name="sync now",
                console=console,
            )
        assert result is RecoveryOutcome.SKIPPED
        assert "Login failed" in buf.getvalue()
        assert "nope" in buf.getvalue()


# ---------------------------------------------------------------------------
# handle_unauthenticated_with_teamspace
# ---------------------------------------------------------------------------


class TestFacade:
    def test_no_teamspace_returns_no_teamspace(self, monkeypatch, capsys):
        console, _ = _make_console()
        monkeypatch.setattr(
            recovery,
            "detect_logged_out_with_connected_teamspace",
            lambda: None,
        )
        result = handle_unauthenticated_with_teamspace(
            command_name="sync now",
            console=console,
        )
        assert result is RecoveryOutcome.NO_TEAMSPACE
        # stderr untouched: no canonical line.
        captured = capsys.readouterr()
        assert "logged_out_on_connected_teamspace" not in captured.err

    def test_non_interactive_emits_structured_line(self, monkeypatch, capsys):
        console, _ = _make_console()
        monkeypatch.setattr(
            recovery,
            "detect_logged_out_with_connected_teamspace",
            lambda: "acme-eng",
        )
        monkeypatch.setattr(recovery, "is_interactive", lambda: False)
        result = handle_unauthenticated_with_teamspace(
            command_name="sync now",
            console=console,
        )
        assert result is RecoveryOutcome.EXIT_4
        captured = capsys.readouterr()
        assert (
            "spec-kitty: logged_out_on_connected_teamspace "
            "teamspace=acme-eng command=sync now "
            "action=run-spec-kitty-auth-login"
        ) in captured.err

    def test_interactive_calls_prompt_and_propagates(self, monkeypatch):
        console, _ = _make_console()
        monkeypatch.setattr(
            recovery,
            "detect_logged_out_with_connected_teamspace",
            lambda: "acme-eng",
        )
        monkeypatch.setattr(recovery, "is_interactive", lambda: True)
        prompt = MagicMock(return_value=RecoveryOutcome.LOGGED_IN)
        monkeypatch.setattr(recovery, "offer_login_recovery", prompt)
        result = handle_unauthenticated_with_teamspace(
            command_name="sync doctor",
            console=console,
        )
        assert result is RecoveryOutcome.LOGGED_IN
        prompt.assert_called_once_with(
            teamspace="acme-eng",
            command_name="sync doctor",
            console=console,
        )


def test_exit_code_constant_is_four():
    """FR-005: the exit code is exactly 4 and exported."""
    assert EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE == 4
