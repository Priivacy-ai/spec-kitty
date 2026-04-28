"""Central token gateway for the spec-kitty auth subsystem.

Every WP that needs a bearer token awaits ``get_access_token()`` from the
process-wide :class:`TokenManager` returned by
:func:`specify_cli.auth.get_token_manager`. The manager owns the loaded
:class:`StoredSession`, persists updates via the injected
:class:`SecureStorage`, and serializes refresh attempts with a single-flight
``asyncio.Lock`` so a burst of concurrent callers produces exactly one
network refresh.

Per decision D-9 the client never hardcodes a refresh-token TTL; the
:class:`StoredSession` may carry ``refresh_token_expires_at = None`` and
``refresh_if_needed`` only treats the refresh token as expired when the
session explicitly says so.
"""

from __future__ import annotations

import asyncio
import logging

from .errors import (
    NotAuthenticatedError,
    RefreshTokenExpiredError,
    SessionInvalidError,
)
from .secure_storage import SecureStorage
from .session import StoredSession

log = logging.getLogger(__name__)

# Refresh when the access token is within this window of expiry.
_REFRESH_BUFFER_SECONDS = 5


class TokenManager:
    """Centralized token provisioning with single-flight refresh.

    Not a singleton: construct via the ``get_token_manager()`` factory in
    ``specify_cli.auth``. That factory guarantees process-wide sharing with
    thread-safe lazy initialization.
    """

    def __init__(self, storage: SecureStorage) -> None:
        self._storage = storage
        self._session: StoredSession | None = None
        self._refresh_lock: asyncio.Lock | None = None

    # ---- lock lifecycle --------------------------------------------------

    def _get_lock(self) -> asyncio.Lock:
        """Lazy-create the refresh lock inside the current event loop.

        ``asyncio.Lock`` binds to the running loop on creation, so we defer
        construction until the first ``refresh_if_needed`` call. Creating the
        lock in ``__init__`` would bind it to whatever loop happened to be
        active at import time — which is typically not the CLI's loop.
        """
        if self._refresh_lock is None:
            self._refresh_lock = asyncio.Lock()
        return self._refresh_lock

    # ---- session lifecycle ----------------------------------------------

    def load_from_storage_sync(self) -> None:
        """Synchronous load, called once at process startup by the factory.

        Storage read errors are logged and the session is left unset — the
        user can still ``spec-kitty auth login`` to re-establish a session.
        """
        try:
            self._session = self._storage.read()
        except Exception as exc:  # noqa: BLE001 — never crash on stale credentials
            log.warning("Could not load session from storage: %s", exc)
            self._session = None

    def set_session(self, session: StoredSession) -> None:
        """Persist a new session (called by AuthorizationCodeFlow / DeviceCodeFlow)."""
        self._session = session
        self._storage.write(session)

    def clear_session(self) -> None:
        """Delete the current session (called by logout or on session-invalid)."""
        self._session = None
        try:
            self._storage.delete()
        except Exception as exc:  # noqa: BLE001 — logout must not raise on storage quirks
            log.warning("Could not delete session from storage: %s", exc)

    def get_current_session(self) -> StoredSession | None:
        """Return the in-memory session (for ``auth status`` and diagnostics)."""
        return self._session

    @property
    def is_authenticated(self) -> bool:
        """Return True when a session exists and its refresh token is not known-expired.

        When ``refresh_token_expires_at`` is ``None`` (SaaS amendment not
        landed, per C-012), the CLI cannot decide expiry proactively and
        treats the session as still authenticated — the next refresh attempt
        will reveal any server-side expiry via ``400 invalid_grant``.
        """
        if self._session is None:
            return False
        return not self._session.is_refresh_token_expired()

    # ---- token provisioning ---------------------------------------------

    async def get_access_token(self) -> str:
        """Return a valid access token, refreshing if near expiry.

        Raises:
            NotAuthenticatedError: No session is loaded.
            RefreshTokenExpiredError: Refresh token is known-expired.
            SessionInvalidError: SaaS reported ``session_invalid`` during refresh.
        """
        if self._session is None:
            raise NotAuthenticatedError("No active session. Run `spec-kitty auth login` to authenticate.")
        if self._session.is_access_token_expired(buffer_seconds=_REFRESH_BUFFER_SECONDS):
            await self.refresh_if_needed()
        # After refresh, _session is still non-None (refresh_if_needed raises on failure).
        assert self._session is not None
        return self._session.access_token

    async def refresh_if_needed(self) -> bool:
        """Refresh the access token if it's near expiry. Single-flight.

        Returns:
            True if a refresh was performed, False if another concurrent
            caller already refreshed the token.

        Raises:
            NotAuthenticatedError: The session was cleared before we acquired
                the lock.
            RefreshTokenExpiredError: The refresh token is known-expired.
            SessionInvalidError: SaaS reported ``session_invalid``; the
                session has been cleared and the caller must re-login.
        """
        lock = self._get_lock()
        async with lock:
            # Double-check inside the lock: another task may have refreshed
            # while we were waiting for our turn.
            if self._session is None:
                raise NotAuthenticatedError("No session to refresh")
            if not self._session.is_access_token_expired(buffer_seconds=_REFRESH_BUFFER_SECONDS):
                return False  # already refreshed by a previous caller
            if self._session.is_refresh_token_expired():
                raise RefreshTokenExpiredError("Refresh token expired. Run `spec-kitty auth login` to log in again.")

            # Lazy import to avoid circular dependencies: auth.flows.refresh
            # imports from specify_cli.auth (session/errors/config), and is
            # introduced by WP04. WP01 tests mock TokenRefreshFlow, so the
            # missing module is only a runtime concern once refresh fires.
            from .flows.refresh import TokenRefreshFlow  # type: ignore[import-not-found]

            flow = TokenRefreshFlow()
            try:
                updated = await flow.refresh(self._session)
            except RefreshTokenExpiredError:
                # The server rejected the stored refresh token. Clear the
                # local session so follow-up status/diagnostics do not report
                # stale credentials as still authenticated.
                self.clear_session()
                raise
            except SessionInvalidError:
                # Server-side invalidation: clear local state and propagate.
                self.clear_session()
                raise
            self._session = updated
            self._storage.write(updated)
            return True
