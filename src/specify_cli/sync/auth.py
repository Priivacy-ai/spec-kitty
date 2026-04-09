"""Authentication utilities for sync module."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, UTC
from pathlib import Path
from urllib.parse import urlparse

import httpx
import toml
from filelock import FileLock, Timeout

from specify_cli.core.atomic import atomic_write

from specify_cli.sync.config import SyncConfig
from specify_cli.sync.feature_flags import (
    is_saas_sync_enabled,
    saas_sync_disabled_message,
)

SPEC_KITTY_DIR = Path.home() / ".spec-kitty"
CREDENTIALS_PATH = SPEC_KITTY_DIR / "credentials"
LOCK_PATH = CREDENTIALS_PATH.with_suffix(".lock")


class CredentialStore:
    """Manages secure storage of authentication tokens in TOML format."""

    def __init__(self):
        self.credentials_path = CREDENTIALS_PATH
        self.lock_path = LOCK_PATH
        # Cached FileLock instance — reusing the same object is required for reentrancy.
        # filelock.FileLock is reentrant per-thread only when the SAME object is reused.
        # Creating a new FileLock object for the same path does NOT exhibit reentrancy.
        self._file_lock: FileLock | None = None

    def _ensure_directory(self):
        """Create ~/.spec-kitty/ directory if it doesn't exist."""
        SPEC_KITTY_DIR.mkdir(mode=0o700, exist_ok=True)

    def _acquire_lock(self) -> FileLock:
        """Return the shared FileLock instance (timeout=10s).

        Reuses the same FileLock object so that reentrant acquisition by the
        same thread (e.g., inside refresh_tokens()) is a no-op rather than a
        deadlock. See FR-401.
        """
        if self._file_lock is None:
            self._file_lock = FileLock(self.lock_path, timeout=10)
        return self._file_lock

    def load(self) -> dict | None:
        """Load credentials from TOML file. Returns None if not exists or invalid."""
        if not self.credentials_path.exists():
            return None

        try:
            with self._acquire_lock(), open(self.credentials_path) as handle:
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
        team_slug: str | None = None,
    ):
        """Save credentials to TOML file with 600 permissions."""
        self._ensure_directory()

        user_data: dict = {
            "username": username,
        }
        if team_slug is not None:
            user_data["team_slug"] = team_slug

        data = {
            "tokens": {
                "access": access_token,
                "refresh": refresh_token,
                "access_expires_at": access_expires_at.isoformat(),
                "refresh_expires_at": refresh_expires_at.isoformat(),
            },
            "user": user_data,
            "server": {
                "url": server_url,
            },
        }

        try:
            with self._acquire_lock():
                content = toml.dumps(data)
                atomic_write(self.credentials_path, content)
                if os.name != "nt":
                    os.chmod(self.credentials_path, 0o600)
        except Timeout as exc:
            raise RuntimeError("Cannot acquire lock on credentials file. Another process may be using it.") from exc

    def clear(self):
        """Delete the credentials file."""
        try:
            with self._acquire_lock():
                if self.credentials_path.exists():
                    self.credentials_path.unlink()
        except Timeout as exc:
            raise RuntimeError("Cannot acquire lock on credentials file. Another process may be using it.") from exc

    def exists(self) -> bool:
        """Check if credentials file exists."""
        return self.credentials_path.exists()

    def _parse_expiry(self, value: str) -> datetime | None:
        """Parse expiry timestamp, normalizing to timezone-aware UTC datetime."""
        try:
            if isinstance(value, str) and value.endswith("Z"):
                value = value[:-1] + "+00:00"
            parsed = datetime.fromisoformat(value)
            # Normalize to timezone-aware UTC for consistent comparison
            if parsed.tzinfo is not None:  # noqa: SIM108
                parsed = parsed.astimezone(UTC)
            else:
                # Assume naive datetimes are UTC
                parsed = parsed.replace(tzinfo=UTC)
            return parsed
        except (TypeError, ValueError):
            return None

    def get_access_token(self) -> str | None:
        """Get access token if valid (not expired). Returns None if expired or missing."""
        data = self.load()
        if not data or "tokens" not in data:
            return None

        tokens = data["tokens"]
        if "access" not in tokens or "access_expires_at" not in tokens:
            return None

        expires_at = self._parse_expiry(tokens["access_expires_at"])
        if not expires_at or datetime.now(UTC) >= expires_at:
            return None

        return tokens["access"]

    def get_refresh_token(self) -> str | None:
        """Get refresh token if valid (not expired). Returns None if expired or missing."""
        data = self.load()
        if not data or "tokens" not in data:
            return None

        tokens = data["tokens"]
        if "refresh" not in tokens or "refresh_expires_at" not in tokens:
            return None

        expires_at = self._parse_expiry(tokens["refresh_expires_at"])
        if not expires_at or datetime.now(UTC) >= expires_at:
            return None

        return tokens["refresh"]

    def is_access_token_valid(self) -> bool:
        """Check if access token exists and is not expired."""
        return self.get_access_token() is not None

    def is_refresh_token_valid(self) -> bool:
        """Check if refresh token exists and is not expired."""
        return self.get_refresh_token() is not None

    def get_username(self) -> str | None:
        """Get stored username."""
        data = self.load()
        if not data or "user" not in data:
            return None
        return data["user"].get("username")

    def get_server_url(self) -> str | None:
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

    def get_team_slug(self) -> str | None:
        """Get stored team slug. Returns None if not available."""
        data = self.load()
        if not data or "user" not in data:
            return None
        return data["user"].get("team_slug")


class AuthenticationError(Exception):
    """Raised when authentication fails."""


class AuthClient:
    """Handles authentication operations with the SaaS API."""

    def __init__(self):
        self.credential_store = CredentialStore()
        self.config = SyncConfig()
        self._http_client: httpx.Client | None = None

    def _validate_server_url(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise AuthenticationError(
                "Authentication requires an HTTPS server URL. Please update sync server URL to use https://"
            )
        return url

    def _coerce_lifetime(self, value: str | int | None, default: int) -> int:
        """Coerce lifetime value to int, handling string responses from server."""
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _require_saas_sync(self, operation: str) -> None:
        """Raise when SaaS connectivity is disabled by feature flag."""
        if not is_saas_sync_enabled():
            raise AuthenticationError(f"{saas_sync_disabled_message()} Operation: {operation}.")

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
        self._require_saas_sync("auth login")

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
        # Server may return access_lifetime (seconds) or expires_in (possibly as strings)
        access_lifetime = self._coerce_lifetime(
            data.get("access_lifetime") or data.get("expires_in"),
            default=900,  # 15 min
        )
        refresh_lifetime = self._coerce_lifetime(
            data.get("refresh_lifetime") or data.get("refresh_expires_in"),
            default=604800,  # 7 days
        )
        access_expires_at = datetime.now(UTC) + timedelta(seconds=access_lifetime)
        refresh_expires_at = datetime.now(UTC) + timedelta(seconds=refresh_lifetime)

        # Get team_slug from server response if available (post-MVP feature)
        team_slug = data.get("team_slug")

        self.credential_store.save(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_at=access_expires_at,
            refresh_expires_at=refresh_expires_at,
            username=username,
            server_url=self.server_url,
            team_slug=team_slug,
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
        self._require_saas_sync("token refresh")

        # T020: Acquire the lock for the FULL transaction (read → network → persist).
        # Inner load()/save()/clear() calls reacquire the same lock as no-ops
        # (filelock.FileLock is reentrant per thread). See FR-401.
        with self.credential_store._acquire_lock():
            # Inner get_refresh_token() calls load() which reacquires the lock as a no-op.
            refresh_token = self.credential_store.get_refresh_token()
            if not refresh_token:
                raise AuthenticationError("No valid refresh token. Please log in again.")

            # Capture the refresh token at transaction entry for stale-401 detection (T021).
            entry_refresh_token = refresh_token

            client = self._get_http_client()
            url = f"{self.server_url}/api/v1/token/refresh/"

            try:
                # T022: HTTP timeout (8s) must be < FileLock timeout (10s) to prevent
                # deadlock if the server hangs. See FR-401.
                # INVARIANT: HTTP timeout (8s) < FileLock timeout (10s) — prevents deadlock
                response = client.post(url, json={"refresh": refresh_token}, timeout=8.0)
            except httpx.RequestError as exc:
                raise AuthenticationError(f"Cannot reach server: {exc}") from exc

            if response.status_code == 401:
                # T021: Re-read credentials under the same lock (reacquires as no-op).
                # If the refresh token on disk has changed since we entered this transaction,
                # another process already rotated the token successfully — our 401 is stale.
                # Exit cleanly without clearing. See FR-402.
                current_creds = self.credential_store.load()
                if current_creds is not None and current_creds["tokens"].get("refresh") != entry_refresh_token:
                    # Stale 401: another process rotated the token — we can exit safely.
                    return True  # Caller should retry get_access_token() to use the new token.

                # Real 401: the token on disk matches what we started with → server rejected it.
                # Clear credentials under the same lock. See FR-403.
                self.credential_store.clear()  # reacquires lock as no-op
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
            # Preserve existing team_slug or use server-provided value if available
            team_slug = data.get("team_slug") or self.credential_store.get_team_slug()

            # Use server-provided expiry if available, else use defaults
            access_lifetime = self._coerce_lifetime(
                data.get("access_lifetime") or data.get("expires_in"),
                default=900,  # 15 min
            )
            refresh_lifetime = self._coerce_lifetime(
                data.get("refresh_lifetime") or data.get("refresh_expires_in"),
                default=604800,  # 7 days
            )
            access_expires_at = datetime.now(UTC) + timedelta(seconds=access_lifetime)
            refresh_expires_at = datetime.now(UTC) + timedelta(seconds=refresh_lifetime)

            # Inner save() reacquires the lock as a no-op (reentrancy).
            self.credential_store.save(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                access_expires_at=access_expires_at,
                refresh_expires_at=refresh_expires_at,
                username=username,
                server_url=server_url,
                team_slug=team_slug,
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
        self._require_saas_sync("websocket token exchange")

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
            response = client.post(url, headers={"Authorization": f"Bearer {access_token}"})

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

    def get_access_token(self) -> str | None:
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
            if not is_saas_sync_enabled():
                return None
            try:
                self.refresh_tokens()
                return self.credential_store.get_access_token()
            except AuthenticationError:
                return None

        return None

    def is_authenticated(self) -> bool:
        """Check if user is authenticated (has valid access or refresh token)."""
        return self.credential_store.is_access_token_valid() or self.credential_store.is_refresh_token_valid()

    def clear_credentials(self):
        """Clear all stored credentials."""
        self.credential_store.clear()

    def get_team_slug(self) -> str | None:
        """Return stored team slug, or None if not authenticated."""
        if not self.is_authenticated():
            return None
        return self.credential_store.get_team_slug()
