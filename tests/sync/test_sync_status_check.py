"""Tests for sync status --check using real auth tokens."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from specify_cli.auth.errors import AuthenticationError, NetworkError
from specify_cli.cli.commands.sync import _check_server_connection
from specify_cli.sync.feature_flags import SAAS_SYNC_ENV_VAR

pytestmark = pytest.mark.fast


SERVER_URL = "https://spec-kitty-dev.fly.dev"


@pytest.fixture(autouse=True)
def _enable_saas_flag(monkeypatch):
    """Enable the SaaS sync feature flag for every test in this module."""
    monkeypatch.setenv(SAAS_SYNC_ENV_VAR, "1")
    yield


def _fake_token_manager(
    *,
    authenticated: bool = True,
    access_token: str | None = "valid-access-token",
    token_error: Exception | None = None,
) -> MagicMock:
    """Build a MagicMock TokenManager that quacks the way ``_check_server_connection`` expects."""

    tm = MagicMock()
    tm.is_authenticated = authenticated

    async def _get_access_token() -> str | None:
        if token_error is not None:
            raise token_error
        if access_token is None:
            raise AuthenticationError("expired")
        return access_token

    tm.get_access_token = _get_access_token
    return tm


def _mock_response(status_code=200, text=""):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.text = text
    return mock_response


def _mock_response_for_probe(
    *,
    get_status=200,
    get_text="",
    get_side_effect=None,
    post_status=200,
    post_text="",
    post_side_effect=None,
):
    """Create a request_with_fallback_sync side effect for health/batch probes."""

    def _request(method: str, url: str, **kwargs):
        if method == "GET":
            if get_side_effect is not None:
                raise get_side_effect
            return _mock_response(get_status, get_text)
        if method == "POST":
            if post_side_effect is not None:
                raise post_side_effect
            return _mock_response(post_status, post_text)
        raise AssertionError(f"Unexpected method {method}")

    return MagicMock(side_effect=_request)


def test_check_server_connection_reports_disabled_when_flag_off(monkeypatch):
    """Flag-off mode should skip connectivity probing entirely."""
    monkeypatch.delenv(SAAS_SYNC_ENV_VAR, raising=False)

    status, note = _check_server_connection(SERVER_URL)

    assert "Disabled" in status
    assert "not enabled" in note.lower()


class TestCheckServerConnectionNoCredentials:
    """Test behavior when there is no authenticated session."""

    def test_no_authenticated_session(self):
        """When the token manager reports unauthenticated, return 'Not authenticated' message."""
        fake_tm = _fake_token_manager(authenticated=False)
        with patch("specify_cli.auth.get_token_manager", return_value=fake_tm):
            status, note = _check_server_connection(SERVER_URL)

        assert "Not authenticated" in status
        assert "spec-kitty auth login" in note


class TestCheckServerConnectionExpiredToken:
    """Test behavior when access token is expired."""

    def test_expired_token_refresh_fails(self):
        """When refresh fails (AuthenticationError), return 'Session expired'."""
        fake_tm = _fake_token_manager(access_token=None)
        with patch("specify_cli.auth.get_token_manager", return_value=fake_tm):
            status, note = _check_server_connection(SERVER_URL)

        assert "Session expired" in status
        assert "spec-kitty auth login" in note

    @patch("specify_cli.auth.http.request_with_fallback_sync")
    def test_expired_token_refresh_succeeds(self, mock_request):
        """When access token is refreshed successfully, probe with the new token."""
        mock_request.side_effect = _mock_response_for_probe(get_status=200)
        fake_tm = _fake_token_manager(access_token="refreshed-access-token")

        with patch("specify_cli.auth.get_token_manager", return_value=fake_tm):
            status, note = _check_server_connection(SERVER_URL)

        assert "Connected" in status
        assert "authentication valid" in note


class TestCheckServerConnectionTokenProbeErrors:
    """Test behavior when token probe fails for non-auth reasons."""

    def test_unexpected_token_probe_error(self):
        """Unexpected token probe errors should not be reported as session expiry."""
        fake_tm = _fake_token_manager(
            token_error=RuntimeError("credentials file lock timeout")
        )

        with patch("specify_cli.auth.get_token_manager", return_value=fake_tm):
            status, note = _check_server_connection(SERVER_URL)

        assert "Error" in status
        assert "Authentication probe failed" in note
        assert "Session expired" not in status


class TestCheckServerConnectionValidToken:
    """Test behavior when a valid access token is available."""

    @patch("specify_cli.auth.http.request_with_fallback_sync")
    def test_server_returns_200(self, mock_request):
        """When server returns 200, report connected and auth valid."""
        mock_request.side_effect = _mock_response_for_probe(get_status=200)
        fake_tm = _fake_token_manager(access_token="valid-access-token")

        with patch("specify_cli.auth.get_token_manager", return_value=fake_tm):
            status, note = _check_server_connection(SERVER_URL)

        assert "Connected" in status
        assert "authentication valid" in note

        # Verify it used real token, not a hardcoded test token
        call_args = mock_request.call_args
        auth_header = call_args.kwargs.get("headers", {}).get("Authorization", "")
        assert auth_header == "Bearer valid-access-token"

    @patch("specify_cli.auth.http.request_with_fallback_sync")
    def test_server_returns_401(self, mock_request):
        """When server returns 401, report authentication failed."""
        mock_request.side_effect = _mock_response_for_probe(get_status=401)
        fake_tm = _fake_token_manager(access_token="stale-token")

        with patch("specify_cli.auth.get_token_manager", return_value=fake_tm):
            status, note = _check_server_connection(SERVER_URL)

        assert "Authentication failed" in status
        assert "spec-kitty auth login" in note

    @patch("specify_cli.auth.http.request_with_fallback_sync")
    def test_server_returns_403(self, mock_request):
        """When server returns 403, report permission denied."""
        mock_request.side_effect = _mock_response_for_probe(get_status=403)
        fake_tm = _fake_token_manager(access_token="valid-token")

        with patch("specify_cli.auth.get_token_manager", return_value=fake_tm):
            status, note = _check_server_connection(SERVER_URL)

        assert "Permission denied" in status
        assert "team membership" in note

    @patch("specify_cli.auth.http.request_with_fallback_sync")
    def test_server_returns_unexpected_status(self, mock_request):
        """When server returns an unexpected status code, report it."""
        mock_request.side_effect = _mock_response_for_probe(get_status=500)
        fake_tm = _fake_token_manager(access_token="valid-token")

        with patch("specify_cli.auth.get_token_manager", return_value=fake_tm):
            status, note = _check_server_connection(SERVER_URL)

        assert "Unexpected" in status
        assert "500" in note


class TestCheckServerConnectionUnreachable:
    """Test behavior when server is unreachable."""

    @patch("specify_cli.auth.http.request_with_fallback_sync")
    def test_connection_timeout(self, mock_request):
        """When server times out, report unreachable."""
        mock_request.side_effect = _mock_response_for_probe(
            get_side_effect=NetworkError("Connection timed out")
        )
        fake_tm = _fake_token_manager(access_token="valid-token")

        with patch("specify_cli.auth.get_token_manager", return_value=fake_tm):
            status, note = _check_server_connection(SERVER_URL)

        assert "Unreachable" in status
        assert "queued for later sync" in note

    @patch("specify_cli.auth.http.request_with_fallback_sync")
    def test_connection_refused(self, mock_request):
        """When connection is refused, report unreachable."""
        mock_request.side_effect = _mock_response_for_probe(
            get_side_effect=NetworkError("Connection refused")
        )
        fake_tm = _fake_token_manager(access_token="valid-token")

        with patch("specify_cli.auth.get_token_manager", return_value=fake_tm):
            status, note = _check_server_connection(SERVER_URL)

        assert "Unreachable" in status
        assert "Connection refused" in note


class TestCheckServerConnectionNoHardcodedTokens:
    """Regression tests: ensure no hardcoded test tokens remain."""

    @patch("specify_cli.auth.http.request_with_fallback_sync")
    def test_no_test_token_in_request(self, mock_request):
        """Verify that the probe never sends a hardcoded 'test-token'."""
        mock_request.side_effect = _mock_response_for_probe(get_status=200)
        fake_tm = _fake_token_manager(access_token="real-user-jwt-token")

        with patch("specify_cli.auth.get_token_manager", return_value=fake_tm):
            _check_server_connection(SERVER_URL)

        call_args = mock_request.call_args
        auth_header = call_args.kwargs.get("headers", {}).get("Authorization", "")
        assert "test-token" not in auth_header
        assert "real-user-jwt-token" in auth_header

    @patch("specify_cli.auth.http.request_with_fallback_sync")
    def test_probes_health_endpoint_not_websocket(self, mock_request):
        """Verify probe hits the HTTP health endpoint, not a WebSocket URL."""
        mock_request.side_effect = _mock_response_for_probe(get_status=200)
        fake_tm = _fake_token_manager(access_token="valid-token")

        with patch("specify_cli.auth.get_token_manager", return_value=fake_tm):
            _check_server_connection(SERVER_URL)

        call_args = mock_request.call_args
        probe_url = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("url", "")
        assert "api/v1/sync/health" in probe_url
        assert "wss://" not in probe_url
        assert "ws://" not in probe_url

    @patch("specify_cli.auth.http.request_with_fallback_sync")
    def test_falls_back_to_legacy_batch_probe_when_health_endpoint_missing(self, mock_request):
        """404 health probes should fall back to the legacy batch probe."""
        mock_request.side_effect = _mock_response_for_probe(
            get_status=404,
            post_status=400,
            post_text='{"error":"No events provided"}',
        )
        fake_tm = _fake_token_manager(access_token="valid-token")

        with patch("specify_cli.auth.get_token_manager", return_value=fake_tm):
            status, note = _check_server_connection(SERVER_URL)

        assert "Connected" in status
        assert "legacy batch probe" in note
        assert mock_request.call_count == 2
