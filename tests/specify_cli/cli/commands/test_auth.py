"""Integration tests for auth CLI commands."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from specify_cli import app as cli_app
from specify_cli.sync.feature_flags import SAAS_SYNC_ENV_VAR
from specify_cli.sync.queue import (
    OfflineQueue,
    build_queue_scope,
    pending_events_for_scope,
    scope_db_path,
    write_active_scope,
)


@pytest.fixture
def runner():
    """Create CLI runner."""
    return CliRunner()


@pytest.fixture
def temp_credentials(tmp_path, monkeypatch):
    """Set up temporary credentials directory."""
    monkeypatch.setenv("HOME", str(tmp_path))
    cred_dir = tmp_path / ".spec-kitty"
    cred_dir.mkdir()

    import specify_cli.sync.auth as auth_module

    monkeypatch.setattr(auth_module, "SPEC_KITTY_DIR", cred_dir)
    monkeypatch.setattr(auth_module, "CREDENTIALS_PATH", cred_dir / "credentials")
    monkeypatch.setattr(auth_module, "LOCK_PATH", cred_dir / "credentials.lock")

    return cred_dir


class TestAuthLogin:
    """Tests for 'spec-kitty auth login' command."""

    def test_login_blocked_when_saas_feature_disabled(self, runner, temp_credentials, monkeypatch):
        """Login should fail fast when SaaS feature flag is disabled."""
        monkeypatch.delenv(SAAS_SYNC_ENV_VAR, raising=False)
        result = runner.invoke(
            cli_app,
            ["auth", "login"],
            input="test@example.com\ntestpassword\n",
        )

        assert result.exit_code == 1
        assert "SaaS sync is disabled by feature flag" in result.stdout

    def test_login_success(self, runner, temp_credentials):
        """Login should succeed with valid credentials."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access": "test_access",
            "refresh": "test_refresh",
        }

        with patch("specify_cli.sync.auth.httpx.Client") as mock_client_class:
            mock_client_class.return_value.post.return_value = mock_response

            result = runner.invoke(
                cli_app,
                ["auth", "login"],
                input="test@example.com\ntestpassword\n",
            )

        assert result.exit_code == 0
        assert "Login successful" in result.stdout

    def test_login_invalid_credentials(self, runner, temp_credentials):
        """Login should fail with invalid credentials."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Invalid credentials"}

        with patch("specify_cli.sync.auth.httpx.Client") as mock_client_class:
            mock_client_class.return_value.post.return_value = mock_response

            result = runner.invoke(
                cli_app,
                ["auth", "login"],
                input="test@example.com\nwrongpassword\n",
            )

        assert result.exit_code == 1
        assert "Invalid username or password" in result.stdout

    def test_login_already_authenticated(self, runner, temp_credentials):
        """Login should warn if already authenticated."""
        cred_path = temp_credentials / "credentials"
        cred_path.write_text(
            """
[tokens]
access = "existing"
refresh = "existing"
access_expires_at = "2099-01-01T00:00:00"
refresh_expires_at = "2099-01-01T00:00:00"

[user]
username = "existing@example.com"

[server]
url = "https://test.example.com"
""".strip()
        )

        result = runner.invoke(
            cli_app,
            ["auth", "login", "--username", "ignored@example.com", "--password", "ignored"],
        )

        assert result.exit_code == 0
        assert "Already authenticated" in result.stdout

    def test_login_blocks_account_switch_when_previous_scope_has_pending_events(
        self, runner, temp_credentials
    ):
        """Login should block account switch unless --force when previous queue has pending events."""
        previous_scope = build_queue_scope(
            "https://test.example.com", "old@example.com", "old-team"
        )
        write_active_scope(previous_scope)
        old_queue = OfflineQueue(scope_db_path(previous_scope))
        old_queue.queue_event(
            {
                "event_id": "evt-old-001",
                "event_type": "WPStatusChanged",
                "payload": {"wp_id": "WP01", "from_lane": "planned", "to_lane": "claimed"},
            }
        )
        assert pending_events_for_scope(previous_scope) == 1

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access": "new_access",
            "refresh": "new_refresh",
            "team_slug": "new-team",
        }

        with patch("specify_cli.sync.auth.SyncConfig.get_server_url", return_value="https://test.example.com"):
            with patch("specify_cli.sync.auth.httpx.Client") as mock_client_class:
                mock_client_class.return_value.post.return_value = mock_response
                result = runner.invoke(
                    cli_app,
                    ["auth", "login", "--username", "new@example.com", "--password", "testpassword"],
                )

        assert result.exit_code == 1
        assert "Account switch blocked" in result.stdout
        assert not (temp_credentials / "credentials").exists()
        assert pending_events_for_scope(previous_scope) == 1

    def test_login_allows_account_switch_with_force_even_when_previous_scope_has_pending_events(
        self, runner, temp_credentials
    ):
        """--force allows switching accounts while preserving old scoped queue."""
        previous_scope = build_queue_scope(
            "https://test.example.com", "old@example.com", "old-team"
        )
        write_active_scope(previous_scope)
        old_queue = OfflineQueue(scope_db_path(previous_scope))
        old_queue.queue_event(
            {
                "event_id": "evt-old-002",
                "event_type": "WPStatusChanged",
                "payload": {"wp_id": "WP02", "from_lane": "planned", "to_lane": "claimed"},
            }
        )
        assert pending_events_for_scope(previous_scope) == 1

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access": "new_access",
            "refresh": "new_refresh",
            "team_slug": "new-team",
        }

        with patch("specify_cli.sync.auth.SyncConfig.get_server_url", return_value="https://test.example.com"):
            with patch("specify_cli.sync.auth.httpx.Client") as mock_client_class:
                mock_client_class.return_value.post.return_value = mock_response
                result = runner.invoke(
                    cli_app,
                    [
                        "auth",
                        "login",
                        "--force",
                        "--username",
                        "new@example.com",
                        "--password",
                        "testpassword",
                    ],
                )

        assert result.exit_code == 0
        assert "Login successful" in result.stdout
        assert "Switching accounts with 1 pending event" in result.stdout
        assert (temp_credentials / "credentials").exists()
        assert pending_events_for_scope(previous_scope) == 1


class TestAuthLogout:
    """Tests for 'spec-kitty auth logout' command."""

    def test_logout_success(self, runner, temp_credentials):
        """Logout should clear credentials."""
        cred_path = temp_credentials / "credentials"
        cred_path.write_text(
            """
[tokens]
access = "test"
refresh = "test"
access_expires_at = "2099-01-01T00:00:00"
refresh_expires_at = "2099-01-01T00:00:00"

[user]
username = "test@example.com"

[server]
url = "https://test.example.com"
""".strip()
        )

        result = runner.invoke(cli_app, ["auth", "logout"])

        assert result.exit_code == 0
        assert "Logged out" in result.stdout
        assert not cred_path.exists()

    def test_logout_not_authenticated(self, runner, temp_credentials):
        """Logout should handle not being authenticated."""
        result = runner.invoke(cli_app, ["auth", "logout"])

        assert result.exit_code == 0
        assert "No active session" in result.stdout


class TestAuthStatus:
    """Tests for 'spec-kitty auth status' command."""

    def test_status_authenticated(self, runner, temp_credentials):
        """Status should show info when authenticated."""
        cred_path = temp_credentials / "credentials"
        cred_path.write_text(
            """
[tokens]
access = "test"
refresh = "test"
access_expires_at = "2099-01-01T00:00:00"
refresh_expires_at = "2099-01-01T00:00:00"

[user]
username = "test@example.com"

[server]
url = "https://test.example.com"
""".strip()
        )

        result = runner.invoke(cli_app, ["auth", "status"])

        assert result.exit_code == 0
        assert "Authenticated" in result.stdout
        assert "test@example.com" in result.stdout

    def test_status_not_authenticated(self, runner, temp_credentials):
        """Status should show not authenticated."""
        result = runner.invoke(cli_app, ["auth", "status"])

        assert result.exit_code == 0
        assert "Not authenticated" in result.stdout
