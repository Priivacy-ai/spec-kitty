"""Authentication utilities for sync module."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
import toml
from filelock import FileLock, Timeout

from specify_cli.sync.config import SyncConfig

SPEC_KITTY_DIR = Path.home() / ".spec-kitty"
CREDENTIALS_PATH = SPEC_KITTY_DIR / "credentials"
LOCK_PATH = CREDENTIALS_PATH.with_suffix(".lock")


class CredentialStore:
    """Manages secure storage of authentication tokens in TOML format."""

    def __init__(self):
        self.credentials_path = CREDENTIALS_PATH
        self.lock_path = LOCK_PATH

    def _ensure_directory(self):
        """Create ~/.spec-kitty/ directory if it doesn't exist."""
        SPEC_KITTY_DIR.mkdir(mode=0o700, exist_ok=True)

    def _acquire_lock(self) -> FileLock:
        """Create a file lock with a timeout."""
        return FileLock(self.lock_path, timeout=10)

    def load(self) -> Optional[dict]:
        """Load credentials from TOML file. Returns None if not exists or invalid."""
        if not self.credentials_path.exists():
            return None

        try:
            with self._acquire_lock():
                with open(self.credentials_path, "r") as handle:
                    return toml.load(handle)
        except (toml.TomlDecodeError, OSError, Timeout):
            return None

    def save(
        self,
        access_token: str,
        refresh_token: str,
        access_expires_at: datetime,
        refresh_expires_at: datetime,
        username: str,
        server_url: str,
    ):
        """Save credentials to TOML file with 600 permissions."""
        self._ensure_directory()

        data = {
            "tokens": {
                "access": access_token,
                "refresh": refresh_token,
                "access_expires_at": access_expires_at.isoformat(),
                "refresh_expires_at": refresh_expires_at.isoformat(),
            },
            "user": {
                "username": username,
            },
            "server": {
                "url": server_url,
            },
        }

        try:
            with self._acquire_lock():
                with open(self.credentials_path, "w") as handle:
                    toml.dump(data, handle)
                if os.name != "nt":
                    os.chmod(self.credentials_path, 0o600)
        except Timeout as exc:
            raise RuntimeError(
                "Cannot acquire lock on credentials file. Another process may be using it."
            ) from exc

    def clear(self):
        """Delete the credentials file."""
        try:
            with self._acquire_lock():
                if self.credentials_path.exists():
                    self.credentials_path.unlink()
        except Timeout as exc:
            raise RuntimeError(
                "Cannot acquire lock on credentials file. Another process may be using it."
            ) from exc

    def exists(self) -> bool:
        """Check if credentials file exists."""
        return self.credentials_path.exists()

    def _parse_expiry(self, value: str) -> Optional[datetime]:
        try:
            if isinstance(value, str) and value.endswith("Z"):
                value = value[:-1] + "+00:00"
            return datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return None

    def get_access_token(self) -> Optional[str]:
        """Get access token if valid (not expired). Returns None if expired or missing."""
        data = self.load()
        if not data or "tokens" not in data:
            return None

        tokens = data["tokens"]
        if "access" not in tokens or "access_expires_at" not in tokens:
            return None

        expires_at = self._parse_expiry(tokens["access_expires_at"])
        if not expires_at or datetime.utcnow() >= expires_at:
            return None

        return tokens["access"]

    def get_refresh_token(self) -> Optional[str]:
        """Get refresh token if valid (not expired). Returns None if expired or missing."""
        data = self.load()
        if not data or "tokens" not in data:
            return None

        tokens = data["tokens"]
        if "refresh" not in tokens or "refresh_expires_at" not in tokens:
            return None

        expires_at = self._parse_expiry(tokens["refresh_expires_at"])
        if not expires_at or datetime.utcnow() >= expires_at:
            return None

        return tokens["refresh"]

    def is_access_token_valid(self) -> bool:
        """Check if access token exists and is not expired."""
        return self.get_access_token() is not None

    def is_refresh_token_valid(self) -> bool:
        """Check if refresh token exists and is not expired."""
        return self.get_refresh_token() is not None

    def get_username(self) -> Optional[str]:
        """Get stored username."""
        data = self.load()
        if not data or "user" not in data:
            return None
        return data["user"].get("username")

    def get_server_url(self) -> Optional[str]:
        """Get stored server URL."""
        data = self.load()
        if not data or "server" not in data:
            return None
        return data["server"].get("url")

    def get_token_expiry_info(self) -> dict:
        """Get token expiry information for status display."""
        data = self.load()
        if not data or "tokens" not in data:
            return {"access_expires_at": None, "refresh_expires_at": None}

        tokens = data["tokens"]
        return {
            "access_expires_at": tokens.get("access_expires_at"),
            "refresh_expires_at": tokens.get("refresh_expires_at"),
        }


class AuthenticationError(Exception):
    """Raised when authentication fails."""


class AuthClient:
    """Handles authentication operations with the SaaS API."""

    def __init__(self):
        self.credential_store = CredentialStore()
        self.config = SyncConfig()
        self._http_client: Optional[httpx.Client] = None

    def _validate_server_url(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise AuthenticationError(
                "Authentication requires an HTTPS server URL. Please update sync server URL to use https://"
            )
        return url

    @property
    def server_url(self) -> str:
        """Get server URL from config."""
        return self._validate_server_url(self.config.get_server_url())

    def _get_http_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=10.0)
        return self._http_client

    def close(self):
        """Close HTTP client."""
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def obtain_tokens(self, username: str, password: str) -> bool:
        """
        Authenticate with username/password and store tokens.

        Args:
            username: User's email or username
            password: User's password

        Returns:
            True if authentication succeeded

        Raises:
            AuthenticationError: If credentials are invalid
            httpx.RequestError: If network error occurs
        """
        client = self._get_http_client()
        url = f"{self.server_url}/api/v1/token/"

        try:
            response = client.post(url, json={"username": username, "password": password})
        except httpx.RequestError as exc:
            raise AuthenticationError(f"Cannot reach server: {exc}") from exc

        if response.status_code == 401:
            raise AuthenticationError("Invalid username or password")
        if response.status_code != 200:
            raise AuthenticationError(f"Server error: {response.status_code}")

        try:
            data = response.json()
        except ValueError as exc:
            raise AuthenticationError("Invalid server response") from exc

        try:
            access_token = data["access"]
            refresh_token = data["refresh"]
        except KeyError as exc:
            raise AuthenticationError("Invalid server response") from exc

        # Use server-provided expiry if available, else use defaults
        # Server may return access_lifetime (seconds) or expires_in
        access_lifetime = data.get("access_lifetime") or data.get("expires_in") or 900  # 15 min default
        refresh_lifetime = data.get("refresh_lifetime") or data.get("refresh_expires_in") or 604800  # 7 days default
        access_expires_at = datetime.utcnow() + timedelta(seconds=access_lifetime)
        refresh_expires_at = datetime.utcnow() + timedelta(seconds=refresh_lifetime)

        self.credential_store.save(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_at=access_expires_at,
            refresh_expires_at=refresh_expires_at,
            username=username,
            server_url=self.server_url,
        )

        return True

    def refresh_tokens(self) -> bool:
        """
        Refresh access token using stored refresh token.

        Returns:
            True if refresh succeeded

        Raises:
            AuthenticationError: If refresh token is invalid/expired
            httpx.RequestError: If network error occurs
        """
        refresh_token = self.credential_store.get_refresh_token()
        if not refresh_token:
            raise AuthenticationError("No valid refresh token. Please log in again.")

        client = self._get_http_client()
        url = f"{self.server_url}/api/v1/token/refresh/"

        try:
            response = client.post(url, json={"refresh": refresh_token})
        except httpx.RequestError as exc:
            raise AuthenticationError(f"Cannot reach server: {exc}") from exc

        if response.status_code == 401:
            self.clear_credentials()
            raise AuthenticationError("Session expired. Please log in again.")
        if response.status_code != 200:
            raise AuthenticationError(f"Server error: {response.status_code}")

        try:
            data = response.json()
        except ValueError as exc:
            raise AuthenticationError("Invalid server response") from exc

        try:
            new_access_token = data["access"]
            new_refresh_token = data["refresh"]
        except KeyError as exc:
            raise AuthenticationError("Invalid server response") from exc

        username = self.credential_store.get_username() or "unknown"
        server_url = self.credential_store.get_server_url() or self.server_url
        server_url = self._validate_server_url(server_url)

        # Use server-provided expiry if available, else use defaults
        access_lifetime = data.get("access_lifetime") or data.get("expires_in") or 900  # 15 min default
        refresh_lifetime = data.get("refresh_lifetime") or data.get("refresh_expires_in") or 604800  # 7 days default
        access_expires_at = datetime.utcnow() + timedelta(seconds=access_lifetime)
        refresh_expires_at = datetime.utcnow() + timedelta(seconds=refresh_lifetime)

        self.credential_store.save(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            access_expires_at=access_expires_at,
            refresh_expires_at=refresh_expires_at,
            username=username,
            server_url=server_url,
        )

        return True

    def obtain_ws_token(self) -> str:
        """
        Obtain ephemeral WebSocket token.

        Returns:
            WebSocket token string

        Raises:
            AuthenticationError: If not authenticated or token exchange fails
        """
        access_token = self.get_access_token()
        if not access_token:
            raise AuthenticationError("Not authenticated. Please log in first.")

        client = self._get_http_client()
        url = f"{self.server_url}/api/v1/ws-token/"

        try:
            response = client.post(url, headers={"Authorization": f"Bearer {access_token}"})
        except httpx.RequestError as exc:
            raise AuthenticationError(f"Cannot reach server: {exc}") from exc

        if response.status_code == 401:
            self.refresh_tokens()
            access_token = self.credential_store.get_access_token()
            if not access_token:
                self.clear_credentials()
                raise AuthenticationError("Session expired. Please log in again.")
            response = client.post(
                url, headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code == 401:
                self.clear_credentials()
                raise AuthenticationError("Session expired. Please log in again.")

        if response.status_code != 200:
            raise AuthenticationError(f"Server error: {response.status_code}")

        try:
            data = response.json()
        except ValueError as exc:
            raise AuthenticationError("Invalid server response") from exc

        try:
            return data["ws_token"]
        except KeyError as exc:
            raise AuthenticationError("Invalid server response") from exc

    def get_access_token(self) -> Optional[str]:
        """
        Get valid access token, refreshing silently if expired.

        Returns:
            Access token string, or None if not authenticated

        Note:
            This method performs silent refresh if the access token is expired
            but the refresh token is valid. No user interaction required.
        """
        access_token = self.credential_store.get_access_token()
        if access_token:
            return access_token

        if self.credential_store.is_refresh_token_valid():
            try:
                self.refresh_tokens()
                return self.credential_store.get_access_token()
            except AuthenticationError:
                return None

        return None

    def is_authenticated(self) -> bool:
        """Check if user is authenticated (has valid access or refresh token)."""
        return (
            self.credential_store.is_access_token_valid()
            or self.credential_store.is_refresh_token_valid()
        )

    def clear_credentials(self):
        """Clear all stored credentials."""
        self.credential_store.clear()
