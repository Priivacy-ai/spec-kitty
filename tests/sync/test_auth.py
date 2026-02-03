"""Unit tests for AuthClient."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import httpx
import pytest

from specify_cli.sync.auth import AuthClient, AuthenticationError


@pytest.fixture
def auth_client(tmp_path):
    """Create AuthClient with temp credential store and test server URL."""
    client = AuthClient()
    cred_dir = tmp_path / ".spec-kitty"
    cred_dir.mkdir()
    client.credential_store.credentials_path = cred_dir / "credentials"
    client.credential_store.lock_path = client.credential_store.credentials_path.with_suffix(".lock")
    client.config.get_server_url = lambda: "https://test.example.com"
    return client


class TestObtainTokens:
    """Tests for AuthClient.obtain_tokens()."""

    def test_obtain_tokens_success(self, auth_client):
        """obtain_tokens() should store tokens on success."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access": "new_access_token",
            "refresh": "new_refresh_token",
        }

        with patch.object(auth_client, "_get_http_client") as mock_client:
            mock_client.return_value.post.return_value = mock_response

            result = auth_client.obtain_tokens("user@example.com", "password")

            assert result is True
            assert auth_client.credential_store.get_access_token() == "new_access_token"

    def test_obtain_tokens_invalid_credentials(self, auth_client):
        """obtain_tokens() should raise on 401."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Invalid credentials"}

        with patch.object(auth_client, "_get_http_client") as mock_client:
            mock_client.return_value.post.return_value = mock_response

            with pytest.raises(AuthenticationError) as exc_info:
                auth_client.obtain_tokens("user@example.com", "wrong")

            assert "Invalid username or password" in str(exc_info.value)

    def test_obtain_tokens_network_error(self, auth_client):
        """obtain_tokens() should raise on network error."""
        with patch.object(auth_client, "_get_http_client") as mock_client:
            mock_client.return_value.post.side_effect = httpx.RequestError("Connection failed")

            with pytest.raises(AuthenticationError) as exc_info:
                auth_client.obtain_tokens("user@example.com", "password")

            assert "Cannot reach server" in str(exc_info.value)

    def test_rejects_non_https_server_url(self, auth_client):
        """Non-HTTPS server URLs should be rejected."""
        auth_client.config.get_server_url = lambda: "http://insecure.example.com"

        with pytest.raises(AuthenticationError) as exc_info:
            _ = auth_client.server_url

        assert "https://" in str(exc_info.value)


class TestRefreshTokens:
    """Tests for AuthClient.refresh_tokens()."""

    def test_refresh_tokens_success(self, auth_client):
        """refresh_tokens() should update stored tokens."""
        auth_client.credential_store.save(
            access_token="old_access",
            refresh_token="old_refresh",
            access_expires_at=datetime.utcnow() - timedelta(minutes=1),
            refresh_expires_at=datetime.utcnow() + timedelta(days=7),
            username="user@example.com",
            server_url="https://test.example.com",
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access": "new_access_token",
            "refresh": "new_refresh_token",
        }

        with patch.object(auth_client, "_get_http_client") as mock_client:
            mock_client.return_value.post.return_value = mock_response

            result = auth_client.refresh_tokens()

            assert result is True
            data = auth_client.credential_store.load()
            assert data["tokens"]["access"] == "new_access_token"
            assert data["tokens"]["refresh"] == "new_refresh_token"

    def test_refresh_tokens_no_refresh_token(self, auth_client):
        """refresh_tokens() should raise when no refresh token stored."""
        with pytest.raises(AuthenticationError) as exc_info:
            auth_client.refresh_tokens()

        assert "No valid refresh token" in str(exc_info.value)

    def test_refresh_tokens_does_not_leak_token(self, auth_client):
        """refresh_tokens() errors should not include token values."""
        sensitive_token = "SECRET_REFRESH_TOKEN"
        auth_client.credential_store.save(
            access_token="old_access",
            refresh_token=sensitive_token,
            access_expires_at=datetime.utcnow() - timedelta(minutes=1),
            refresh_expires_at=datetime.utcnow() + timedelta(days=7),
            username="user@example.com",
            server_url="https://test.example.com",
        )

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Token invalid"}

        with patch.object(auth_client, "_get_http_client") as mock_client:
            mock_client.return_value.post.return_value = mock_response

            with pytest.raises(AuthenticationError) as exc_info:
                auth_client.refresh_tokens()

        assert sensitive_token not in str(exc_info.value)


class TestGetAccessToken:
    """Tests for AuthClient.get_access_token()."""

    def test_get_access_token_returns_valid(self, auth_client):
        """get_access_token() should return valid token directly."""
        auth_client.credential_store.save(
            access_token="valid_access",
            refresh_token="test",
            access_expires_at=datetime.utcnow() + timedelta(minutes=15),
            refresh_expires_at=datetime.utcnow() + timedelta(days=7),
            username="user@example.com",
            server_url="https://test.example.com",
        )

        token = auth_client.get_access_token()
        assert token == "valid_access"

    def test_get_access_token_refreshes_expired(self, auth_client):
        """get_access_token() should refresh expired access token."""
        auth_client.credential_store.save(
            access_token="expired_access",
            refresh_token="valid_refresh",
            access_expires_at=datetime.utcnow() - timedelta(minutes=1),
            refresh_expires_at=datetime.utcnow() + timedelta(days=7),
            username="user@example.com",
            server_url="https://test.example.com",
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access": "refreshed_access",
            "refresh": "new_refresh",
        }

        with patch.object(auth_client, "_get_http_client") as mock_client:
            mock_client.return_value.post.return_value = mock_response

            token = auth_client.get_access_token()

            assert token == "refreshed_access"


class TestIsAuthenticated:
    """Tests for AuthClient.is_authenticated()."""

    def test_is_authenticated_true(self, auth_client):
        """is_authenticated() should return True when tokens valid."""
        auth_client.credential_store.save(
            access_token="test",
            refresh_token="test",
            access_expires_at=datetime.utcnow() + timedelta(minutes=15),
            refresh_expires_at=datetime.utcnow() + timedelta(days=7),
            username="user@example.com",
            server_url="https://test.example.com",
        )

        assert auth_client.is_authenticated() is True

    def test_is_authenticated_false(self, auth_client):
        """is_authenticated() should return False when no tokens."""
        assert auth_client.is_authenticated() is False


class TestClearCredentials:
    """Tests for AuthClient.clear_credentials()."""

    def test_clear_credentials(self, auth_client):
        """clear_credentials() should remove stored credentials."""
        auth_client.credential_store.save(
            access_token="test",
            refresh_token="test",
            access_expires_at=datetime.utcnow() + timedelta(minutes=15),
            refresh_expires_at=datetime.utcnow() + timedelta(days=7),
            username="user@example.com",
            server_url="https://test.example.com",
        )

        auth_client.clear_credentials()

        assert auth_client.is_authenticated() is False
