"""Unit + CliRunner tests for ``spec-kitty auth status`` (feature 080, WP07).

Covers:

- ``format_duration`` across all five branches (expired, <1 minute,
  minutes, hours, days) including singular/plural handling.
- ``format_storage_backend`` for the supported backend plus the
  unknown-fallthrough branch.
- ``format_auth_method`` across both known methods plus the unknown
  fallthrough branch.
- ``_print_token_expiry`` with a concrete ``refresh_token_expires_at``
  AND with ``None`` (the defensive legacy-session fallback — per C-012
  the amendment landed 2026-04-09 so new sessions never hit this branch,
  but the CLI must not crash on replayed pre-amendment sessions).
- CliRunner E2E:
    * authenticated path with multi-team session and default marker
    * unauthenticated path
    * refresh-expired path (the early-return branch in ``status_impl``)

Every CliRunner test mocks ``SecureStorage.from_environment`` so we never
touch the real auth store — matches the pattern established by
``tests/auth/test_device_code_flow.py`` and ``tests/cli/commands/test_auth_login.py``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from io import StringIO
from unittest.mock import Mock, patch

import pytest
from rich.console import Console
from typer.testing import CliRunner

from specify_cli.auth import reset_token_manager
from specify_cli.auth.session import StoredSession, Team
from specify_cli.cli.commands._auth_status import (
    _print_token_expiry,
    format_auth_method,
    format_duration,
    format_storage_backend,
)
from specify_cli.cli.commands.auth import app


runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    """Reset the process-wide TokenManager between tests.

    Also provides ``SPEC_KITTY_SAAS_URL`` so any auth config code paths
    that probe it don't blow up.
    """
    monkeypatch.setenv("SPEC_KITTY_SAAS_URL", "https://saas.test")
    reset_token_manager()
    yield
    reset_token_manager()


def _make_session(
    *,
    email: str = "alice@example.com",
    name: str = "Alice Developer",
    access_remaining_seconds: int = 3600,
    refresh_remaining_days: int | None = 89,
    storage_backend: str = "file",
    auth_method: str = "authorization_code",
    teams: list[Team] | None = None,
    default_team_id: str = "tm_acme",
) -> StoredSession:
    """Build a StoredSession with controllable remaining-time offsets.

    ``refresh_remaining_days=None`` produces a legacy session (the
    ``refresh_token_expires_at`` defensive branch).

    Implementation note: we add a 30-second pad on top of each positive
    offset so that the few microseconds that elapse between building the
    session and materializing the status output don't push the integer
    division below the next boundary (e.g. 89 days - 0.001s -> 88 days).
    """
    now = datetime.now(UTC)
    if teams is None:
        teams = [
            Team(id="tm_acme", name="Acme Corp", role="admin"),
            Team(id="tm_widgets", name="Widgets Inc", role="member"),
        ]
    refresh_exp: datetime | None
    if refresh_remaining_days is None:
        refresh_exp = None
    elif refresh_remaining_days < 0:
        # Negative offsets intentionally land in the past (expired branch).
        refresh_exp = now + timedelta(days=refresh_remaining_days)
    else:
        refresh_exp = now + timedelta(days=refresh_remaining_days, seconds=30)
    access_exp = (
        now + timedelta(seconds=access_remaining_seconds + 30)
        if access_remaining_seconds >= 0
        else now + timedelta(seconds=access_remaining_seconds)
    )
    return StoredSession(
        user_id="u_alice",
        email=email,
        name=name,
        teams=teams,
        default_team_id=default_team_id,
        access_token="at_xyz_ignore",
        refresh_token="rt_xyz_ignore",
        session_id="sess_01HR6CABCDEF",
        issued_at=now,
        access_token_expires_at=access_exp,
        refresh_token_expires_at=refresh_exp,
        scope="offline_access",
        storage_backend=storage_backend,  # type: ignore[arg-type]
        last_used_at=now,
        auth_method=auth_method,  # type: ignore[arg-type]
    )


def _mock_storage_returning(session: StoredSession | None, *, backend: str = "file"):
    """Build a Mock SecureStorage returning ``session`` on ``read()``."""
    mock_storage = Mock()
    mock_storage.read.return_value = session
    mock_storage.write = Mock(return_value=None)
    mock_storage.delete = Mock(return_value=None)
    mock_storage.backend_name = backend
    return mock_storage


# ---------------------------------------------------------------------------
# format_duration — all five branches
# ---------------------------------------------------------------------------


class TestFormatDuration:
    """Exhaustive coverage of the format_duration branch table."""

    def test_expired_branch(self):
        assert "expired" in format_duration(-100)

    def test_expired_branch_zero(self):
        assert "expired" in format_duration(0)

    def test_less_than_one_minute(self):
        # 45 seconds -> "< 1 minute" (we deliberately don't render "45 seconds"
        # in the status layout because sub-minute precision is noise).
        assert format_duration(45) == "< 1 minute"

    def test_less_than_one_minute_just_below(self):
        assert format_duration(59) == "< 1 minute"

    def test_minute_singular(self):
        assert format_duration(60) == "1 minute"

    def test_minutes_plural(self):
        assert format_duration(120) == "2 minutes"

    def test_minutes_plural_42(self):
        assert format_duration(42 * 60) == "42 minutes"

    def test_hour_singular(self):
        assert format_duration(3600) == "1 hour"

    def test_hours_plural(self):
        assert format_duration(7200) == "2 hours"

    def test_day_singular(self):
        assert format_duration(86400) == "1 day"

    def test_days_plural(self):
        assert format_duration(86400 * 87) == "87 days"

    def test_days_plural_large(self):
        assert format_duration(86400 * 365) == "365 days"


# ---------------------------------------------------------------------------
# format_storage_backend
# ---------------------------------------------------------------------------


class TestFormatStorageBackend:
    """The supported backend plus unknown fallthrough."""

    def test_file_label(self):
        assert format_storage_backend("file") == "Encrypted session file"

    def test_unknown_fallthrough(self):
        assert "Unknown" in format_storage_backend("unknown-backend")
        assert "unknown-backend" in format_storage_backend("unknown-backend")


# ---------------------------------------------------------------------------
# format_auth_method
# ---------------------------------------------------------------------------


class TestFormatAuthMethod:
    """Both known methods plus unknown fallthrough."""

    def test_authorization_code_label(self):
        label = format_auth_method("authorization_code")
        assert "Browser" in label
        assert "PKCE" in label

    def test_device_code_label(self):
        label = format_auth_method("device_code")
        assert "Headless" in label
        assert "Device" in label

    def test_unknown_fallthrough(self):
        assert "Unknown" in format_auth_method("xyz")


# ---------------------------------------------------------------------------
# _print_token_expiry — both branches (datetime + None defensive fallback)
# ---------------------------------------------------------------------------


def _capture_print_token_expiry(session: StoredSession) -> str:
    """Run ``_print_token_expiry`` against a local Console and return output."""
    buf = StringIO()
    test_console = Console(file=buf, force_terminal=False, width=120)
    with patch("specify_cli.cli.commands._auth_status.console", test_console):
        _print_token_expiry(session)
    return buf.getvalue()


class TestPrintTokenExpiry:
    """The defensive None branch exists only to handle pre-amendment sessions."""

    def test_refresh_datetime_branch_shows_duration(self):
        session = _make_session(
            access_remaining_seconds=3600,
            refresh_remaining_days=89,
        )
        out = _capture_print_token_expiry(session)
        assert "Access token:" in out
        assert "Refresh token:" in out
        assert "89 days" in out
        # Must NOT mention the legacy-session fallback when the datetime is present.
        assert "legacy session" not in out
        assert "server-managed" not in out

    def test_refresh_none_branch_shows_legacy_fallback(self):
        session = _make_session(
            access_remaining_seconds=3600,
            refresh_remaining_days=None,  # pre-amendment / replayed session
        )
        out = _capture_print_token_expiry(session)
        assert "Access token:" in out
        assert "Refresh token:" in out
        # Defensive fallback copy per the C-012 amendment contract.
        assert "server-managed" in out
        assert "legacy session" in out
        assert "re-login" in out

    def test_access_token_expired_rendered_as_expired(self):
        session = _make_session(
            access_remaining_seconds=-100,
            refresh_remaining_days=89,
        )
        out = _capture_print_token_expiry(session)
        assert "expired" in out


# ---------------------------------------------------------------------------
# CliRunner E2E — drives `auth status` through the live Typer app
# ---------------------------------------------------------------------------


class TestAuthStatusCommand:
    """Exercise the full dispatch path: ``runner.invoke(app, ['status'])``."""

    def test_not_authenticated_path(self):
        """No session -> friendly unauthenticated message, exit code 0."""
        mock_storage = _mock_storage_returning(None, backend="file")
        with patch(
            "specify_cli.auth.secure_storage.SecureStorage.from_environment",
            return_value=mock_storage,
        ):
            reset_token_manager()
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0, result.stdout
        assert "Not authenticated" in result.stdout
        assert "spec-kitty auth login" in result.stdout

    def test_authenticated_path_happy(self):
        """Authenticated session prints identity, teams, expiry, backend."""
        session = _make_session(
            access_remaining_seconds=3600,
            refresh_remaining_days=89,
            storage_backend="file",
            auth_method="authorization_code",
        )
        mock_storage = _mock_storage_returning(session, backend="file")
        with patch(
            "specify_cli.auth.secure_storage.SecureStorage.from_environment",
            return_value=mock_storage,
        ):
            reset_token_manager()
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0, result.stdout
        # Banner
        assert "Authenticated" in result.stdout
        # Identity
        assert "alice@example.com" in result.stdout
        assert "Alice Developer" in result.stdout
        assert "u_alice" in result.stdout
        # Teams with default marker
        assert "Acme Corp" in result.stdout
        assert "Widgets Inc" in result.stdout
        assert "default" in result.stdout  # default-team marker
        # Expiry — access ~1 hour, refresh 89 days
        assert "1 hour" in result.stdout
        assert "89 days" in result.stdout
        # Storage backend (human label, not raw literal)
        assert "Encrypted session file" in result.stdout
        # Session id
        assert "sess_01HR6CABCDEF" in result.stdout
        # Auth method human label
        assert "Browser" in result.stdout
        assert "PKCE" in result.stdout
        # Secrets must NOT leak.
        assert "at_xyz_ignore" not in result.stdout
        assert "rt_xyz_ignore" not in result.stdout

    def test_authenticated_path_minutes_branch(self):
        """Access token with 600s remaining must render minutes, not hours."""
        session = _make_session(
            access_remaining_seconds=600,  # 10 minutes
            refresh_remaining_days=89,
            storage_backend="file",
        )
        mock_storage = _mock_storage_returning(session, backend="file")
        with patch(
            "specify_cli.auth.secure_storage.SecureStorage.from_environment",
            return_value=mock_storage,
        ):
            reset_token_manager()
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0, result.stdout
        assert "10 minutes" in result.stdout
        assert "89 days" in result.stdout
        assert "Encrypted session file" in result.stdout

    def test_refresh_token_expired_early_return(self):
        """A session with an expired refresh token takes the early-return branch."""
        session = _make_session(
            access_remaining_seconds=-100,
            refresh_remaining_days=-1,  # refresh already expired
        )
        mock_storage = _mock_storage_returning(session, backend="file")
        with patch(
            "specify_cli.auth.secure_storage.SecureStorage.from_environment",
            return_value=mock_storage,
        ):
            reset_token_manager()
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0, result.stdout
        assert "Session expired" in result.stdout
        assert "spec-kitty auth login" in result.stdout

    def test_authenticated_path_device_code_auth_method(self):
        """Device-code sessions render the Headless label."""
        session = _make_session(
            auth_method="device_code",
            storage_backend="file",
        )
        mock_storage = _mock_storage_returning(session, backend="file")
        with patch(
            "specify_cli.auth.secure_storage.SecureStorage.from_environment",
            return_value=mock_storage,
        ):
            reset_token_manager()
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0, result.stdout
        assert "Headless" in result.stdout
        assert "Device" in result.stdout
        assert "Encrypted session file" in result.stdout

    def test_authenticated_path_empty_teams(self):
        """A session with no teams should print ``(none)`` instead of crashing."""
        session = _make_session(teams=[], default_team_id="")
        mock_storage = _mock_storage_returning(session, backend="file")
        with patch(
            "specify_cli.auth.secure_storage.SecureStorage.from_environment",
            return_value=mock_storage,
        ):
            reset_token_manager()
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0, result.stdout
        assert "(none)" in result.stdout

    def test_authenticated_path_legacy_refresh_none_branch(self):
        """Replayed pre-amendment session hits the defensive None branch."""
        session = _make_session(refresh_remaining_days=None)
        mock_storage = _mock_storage_returning(session, backend="file")
        with patch(
            "specify_cli.auth.secure_storage.SecureStorage.from_environment",
            return_value=mock_storage,
        ):
            reset_token_manager()
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0, result.stdout
        assert "server-managed" in result.stdout
        assert "legacy session" in result.stdout
