"""E2E test for ``spec-kitty auth status`` via CliRunner.

Covers FR-015 (status output fields) end-to-end through the real Typer app.

Test isolation: imports :class:`CliRunner` and drives ``auth status`` with
a :class:`FakeSecureStorage` pre-populated with a known session.
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.auth.session import StoredSession, Team
from specify_cli.cli.commands.auth import app

from .conftest import FakeSecureStorage


runner = CliRunner()


def _authenticated_session() -> StoredSession:
    """Build a StoredSession with deterministic, human-readable fields."""
    now = datetime.now(UTC)
    return StoredSession(
        user_id="u_alice",
        email="alice@example.com",
        name="Alice Developer",
        teams=[
            Team(id="tm_acme", name="Acme Corp", role="admin"),
            Team(id="tm_beta", name="Beta Labs", role="member"),
        ],
        default_team_id="tm_acme",
        access_token="at_status_fixture",
        refresh_token="rt_status_fixture",
        session_id="sess_status_fixture",
        issued_at=now - timedelta(minutes=30),
        access_token_expires_at=now + timedelta(minutes=30),
        refresh_token_expires_at=now + timedelta(days=89),
        scope="offline_access",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )


class TestStatusE2E:
    """End-to-end status through the real Typer app."""

    def test_status_authenticated_displays_expected_fields(
        self,
        fake_storage: FakeSecureStorage,
    ) -> None:
        """FR-015: status displays user/team/expiry/backend/session fields."""
        fake_storage._session = _authenticated_session()

        with patch(
            "specify_cli.auth.secure_storage.SecureStorage.from_environment",
            return_value=fake_storage,
        ):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0, result.stdout
        assert "Authenticated" in result.stdout
        # Identity block.
        assert "alice@example.com" in result.stdout
        assert "Alice Developer" in result.stdout
        assert "u_alice" in result.stdout
        # Teams block.
        assert "Acme Corp" in result.stdout
        assert "Beta Labs" in result.stdout
        # Storage backend label (FR-015).
        assert "Encrypted session file" in result.stdout
        # Session id surfaced (FR-015).
        assert "sess_status_fixture" in result.stdout
        # Auth method label surfaced.
        assert "Browser" in result.stdout

        # SECURITY: raw tokens must NEVER appear in status output.
        assert "at_status_fixture" not in result.stdout
        assert "rt_status_fixture" not in result.stdout

    def test_status_not_authenticated_still_exits_zero(
        self,
        fake_storage: FakeSecureStorage,
    ) -> None:
        """FR-015: ``auth status`` exits 0 even when not authenticated."""
        fake_storage._session = None

        with patch(
            "specify_cli.auth.secure_storage.SecureStorage.from_environment",
            return_value=fake_storage,
        ):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0, result.stdout
        assert "Not authenticated" in result.stdout
        assert "spec-kitty auth login" in result.stdout

    def test_status_refresh_expired_prompts_re_login(
        self,
        fake_storage: FakeSecureStorage,
    ) -> None:
        """A session whose refresh token has expired prompts re-login."""
        now = datetime.now(UTC)
        session = _authenticated_session()
        # Force refresh expiry into the past.
        session.refresh_token_expires_at = now - timedelta(minutes=1)
        fake_storage._session = session

        with patch(
            "specify_cli.auth.secure_storage.SecureStorage.from_environment",
            return_value=fake_storage,
        ):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0, result.stdout
        assert "Session expired" in result.stdout

    def test_status_device_code_method_label(
        self,
        fake_storage: FakeSecureStorage,
    ) -> None:
        """Device-flow sessions surface the ``Headless`` auth-method label."""
        session = _authenticated_session()
        session.auth_method = "device_code"
        fake_storage._session = session

        with patch(
            "specify_cli.auth.secure_storage.SecureStorage.from_environment",
            return_value=fake_storage,
        ):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0, result.stdout
        assert "Headless" in result.stdout

    def test_status_marks_default_team(
        self,
        fake_storage: FakeSecureStorage,
    ) -> None:
        """The default team must be marked visually in the teams list."""
        fake_storage._session = _authenticated_session()

        with patch(
            "specify_cli.auth.secure_storage.SecureStorage.from_environment",
            return_value=fake_storage,
        ):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0, result.stdout
        # Acme Corp is the default team and should be marked as such.
        # The marker may be Rich-stylized ``(default)`` or similar.
        assert "default" in result.stdout.lower()
