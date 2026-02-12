"""Tests for sync status --check using real auth tokens.

Validates the _check_server_connection function which replaces
the old hardcoded test-token WebSocket probe with a real
auth-token-based HTTP batch endpoint probe.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from specify_cli.cli.commands.sync import _check_server_connection


SERVER_URL = "https://spec-kitty-dev.fly.dev"


def _mock_httpx_client(status_code=200, side_effect=None):
    """Create a mock httpx.Client context manager returning a given status code."""
    mock_response = MagicMock()
    mock_response.status_code = status_code

    mock_client = MagicMock()
    if side_effect:
        mock_client.post.side_effect = side_effect
    else:
        mock_client.post.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    return mock_client


class TestCheckServerConnectionNoCredentials:
    """Test behavior when no credentials file exists."""

    @patch("specify_cli.sync.auth.CredentialStore.exists", return_value=False)
    def test_no_credentials_file(self, mock_exists):
        """When credentials file doesn't exist, return 'Not authenticated' message."""
        status, note = _check_server_connection(SERVER_URL)

        assert "Not authenticated" in status
        assert "spec-kitty auth login" in note


class TestCheckServerConnectionExpiredToken:
    """Test behavior when access token is expired."""

    @patch("specify_cli.sync.auth.AuthClient.get_access_token", return_value=None)
    @patch("specify_cli.sync.auth.CredentialStore.exists", return_value=True)
    def test_expired_token_refresh_fails(self, mock_exists, mock_get_token):
        """When access token expired and refresh also fails, return 'Session expired'."""
        status, note = _check_server_connection(SERVER_URL)

        assert "Session expired" in status
        assert "spec-kitty auth login" in note

    @patch("httpx.Client")
    @patch("specify_cli.sync.auth.AuthClient.get_access_token", return_value="refreshed-access-token")
    @patch("specify_cli.sync.auth.CredentialStore.exists", return_value=True)
    def test_expired_token_refresh_succeeds(self, mock_exists, mock_get_token, MockClient):
        """When access token expired but refresh succeeds, probe with new token."""
        MockClient.return_value = _mock_httpx_client(status_code=200)

        status, note = _check_server_connection(SERVER_URL)

        assert "Connected" in status
        assert "authentication valid" in note


class TestCheckServerConnectionValidToken:
    """Test behavior when a valid access token is available."""

    @patch("httpx.Client")
    @patch("specify_cli.sync.auth.AuthClient.get_access_token", return_value="valid-access-token")
    @patch("specify_cli.sync.auth.CredentialStore.exists", return_value=True)
    def test_server_returns_200(self, mock_exists, mock_get_token, MockClient):
        """When server returns 200, report connected and auth valid."""
        mock_client = _mock_httpx_client(status_code=200)
        MockClient.return_value = mock_client

        status, note = _check_server_connection(SERVER_URL)

        assert "Connected" in status
        assert "authentication valid" in note

        # Verify it used real token, not a hardcoded test token
        call_args = mock_client.post.call_args
        auth_header = call_args.kwargs.get("headers", {}).get("Authorization", "")
        assert "Bearer valid-access-token" == auth_header

    @patch("httpx.Client")
    @patch("specify_cli.sync.auth.AuthClient.get_access_token", return_value="stale-token")
    @patch("specify_cli.sync.auth.CredentialStore.exists", return_value=True)
    def test_server_returns_401(self, mock_exists, mock_get_token, MockClient):
        """When server returns 401, report authentication failed."""
        MockClient.return_value = _mock_httpx_client(status_code=401)

        status, note = _check_server_connection(SERVER_URL)

        assert "Authentication failed" in status
        assert "spec-kitty auth login" in note

    @patch("httpx.Client")
    @patch("specify_cli.sync.auth.AuthClient.get_access_token", return_value="valid-token")
    @patch("specify_cli.sync.auth.CredentialStore.exists", return_value=True)
    def test_server_returns_403(self, mock_exists, mock_get_token, MockClient):
        """When server returns 403, report permission denied."""
        MockClient.return_value = _mock_httpx_client(status_code=403)

        status, note = _check_server_connection(SERVER_URL)

        assert "Permission denied" in status
        assert "team membership" in note

    @patch("httpx.Client")
    @patch("specify_cli.sync.auth.AuthClient.get_access_token", return_value="valid-token")
    @patch("specify_cli.sync.auth.CredentialStore.exists", return_value=True)
    def test_server_returns_unexpected_status(self, mock_exists, mock_get_token, MockClient):
        """When server returns an unexpected status code, report it."""
        MockClient.return_value = _mock_httpx_client(status_code=500)

        status, note = _check_server_connection(SERVER_URL)

        assert "Unexpected" in status
        assert "500" in note


class TestCheckServerConnectionUnreachable:
    """Test behavior when server is unreachable."""

    @patch("httpx.Client")
    @patch("specify_cli.sync.auth.AuthClient.get_access_token", return_value="valid-token")
    @patch("specify_cli.sync.auth.CredentialStore.exists", return_value=True)
    def test_connection_timeout(self, mock_exists, mock_get_token, MockClient):
        """When server times out, report unreachable."""
        MockClient.return_value = _mock_httpx_client(
            side_effect=httpx.TimeoutException("Connection timed out")
        )

        status, note = _check_server_connection(SERVER_URL)

        assert "Unreachable" in status
        assert "queued for later sync" in note

    @patch("httpx.Client")
    @patch("specify_cli.sync.auth.AuthClient.get_access_token", return_value="valid-token")
    @patch("specify_cli.sync.auth.CredentialStore.exists", return_value=True)
    def test_connection_refused(self, mock_exists, mock_get_token, MockClient):
        """When connection is refused, report unreachable."""
        MockClient.return_value = _mock_httpx_client(
            side_effect=httpx.ConnectError("Connection refused")
        )

        status, note = _check_server_connection(SERVER_URL)

        assert "Unreachable" in status
        assert "Connection refused" in note


class TestCheckServerConnectionNoHardcodedTokens:
    """Regression tests: ensure no hardcoded test tokens remain."""

    @patch("httpx.Client")
    @patch("specify_cli.sync.auth.AuthClient.get_access_token", return_value="real-user-jwt-token")
    @patch("specify_cli.sync.auth.CredentialStore.exists", return_value=True)
    def test_no_test_token_in_request(self, mock_exists, mock_get_token, MockClient):
        """Verify that the probe never sends a hardcoded 'test-token'."""
        mock_client = _mock_httpx_client(status_code=200)
        MockClient.return_value = mock_client

        _check_server_connection(SERVER_URL)

        # Verify the Authorization header uses the real token
        call_args = mock_client.post.call_args
        auth_header = call_args.kwargs.get("headers", {}).get("Authorization", "")
        assert "test-token" not in auth_header
        assert "real-user-jwt-token" in auth_header

    @patch("httpx.Client")
    @patch("specify_cli.sync.auth.AuthClient.get_access_token", return_value="valid-token")
    @patch("specify_cli.sync.auth.CredentialStore.exists", return_value=True)
    def test_probes_batch_endpoint_not_websocket(self, mock_exists, mock_get_token, MockClient):
        """Verify probe hits the HTTP batch endpoint, not a WebSocket URL."""
        mock_client = _mock_httpx_client(status_code=200)
        MockClient.return_value = mock_client

        _check_server_connection(SERVER_URL)

        call_args = mock_client.post.call_args
        probe_url = call_args.args[0] if call_args.args else call_args.kwargs.get("url", "")
        assert "api/v1/events/batch" in probe_url
        assert "wss://" not in probe_url
        assert "ws://" not in probe_url
