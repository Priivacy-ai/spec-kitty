"""Centralized auth transport for sync, tracker, and websocket clients.

This module is the single owner of authenticated HTTP transports inside
``specify_cli``. ``sync``, ``tracker``, and websocket helpers acquire
their HTTP clients from here so that:

* Token refresh is single-flight (one ``RefreshLock`` shared across
  callers — actually backed by the existing :class:`TokenManager`
  single-flight lock).
* 401 → refresh → retry-once is implemented in exactly one place
  (FR-030).
* Token-refresh failures emit at most one user-facing line per command
  invocation (FR-029, NFR-007).

Public API
----------
- :class:`AuthenticatedClient` — wraps a ``httpx.Client`` (sync) and
  performs bearer injection and 401 retry-once.
- :class:`AsyncAuthenticatedClient` — async analog wrapping
  ``httpx.AsyncClient`` (delegates to :class:`OAuthHttpClient` for the
  refresh-and-retry semantics).
- :class:`AuthRefreshFailed` — structured failure type raised when a
  forced refresh exhausts options.
- :func:`get_client` — process-scoped singleton accessor for the sync
  client.
- :func:`get_async_client` — process-scoped singleton accessor for the
  async client.
- :func:`reset_user_facing_dedup` — test helper that resets the
  per-invocation dedup boolean. Production code never calls this; the
  state lives at module scope so a single CLI command shares one
  dedup window.

Architectural test
------------------
``tests/architectural/test_auth_transport_singleton.py`` enforces that
no module under ``src/specify_cli/sync/``, ``src/specify_cli/tracker/``
(SaaS-adjacent surfaces), ``src/specify_cli/saas_client/``, or the
websocket helpers under ``src/specify_cli/auth/websocket/`` instantiates
``httpx.Client`` / ``httpx.AsyncClient`` directly. This module is the
sole exception.

ADR
---
See ``architecture/2.x/adr/2026-04-26-2-auth-transport-boundary.md``
(DIRECTIVE_003).
"""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
from contextlib import suppress
from datetime import datetime, timedelta, UTC
from typing import Any

import httpx

from specify_cli.auth import get_token_manager
from specify_cli.auth.errors import (
    AuthenticationError,
    NotAuthenticatedError,
    TokenRefreshError,
)
from specify_cli.auth.http import request_with_fallback_sync


logger = logging.getLogger(__name__)
AUTH_RELOGIN_MESSAGE = (
    "Authentication expired. Run `spec-kitty auth login` to re-authenticate."
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class AuthRefreshFailed(AuthenticationError):
    """Raised when a forced token refresh fails inside the centralized client.

    Carries a cause chain via ``__cause__`` and a stable
    ``error_code`` attribute so structured logging / SaaS sync surfaces
    can branch on it without string-matching the message.
    """

    error_code: str = "auth_refresh_failed"

    def __init__(
        self,
        message: str = "Token refresh failed",
        *,
        error_code: str = "auth_refresh_failed",
    ) -> None:
        super().__init__(message)
        self.error_code = error_code


# ---------------------------------------------------------------------------
# Per-invocation dedup state (FR-029, NFR-007)
# ---------------------------------------------------------------------------


_dedup_lock = threading.Lock()
_user_facing_failure_emitted = False


def _emit_user_facing_failure_once(message: str) -> None:
    """Emit *message* to stderr at most once per process invocation.

    Subsequent invocations within the same process accumulate to the
    debug log only. This implements FR-029 / NFR-007: ≤ 1 user-facing
    token-refresh failure line per command invocation.
    """
    global _user_facing_failure_emitted
    with _dedup_lock:
        first = not _user_facing_failure_emitted
        _user_facing_failure_emitted = True
    if first:
        # Single user-facing line.
        print(message, file=sys.stderr)
    else:
        # Subsequent failures land in debug log only.
        logger.debug("Suppressed duplicate token-refresh failure: %s", message)


def reset_user_facing_dedup() -> None:
    """Reset the per-invocation dedup boolean. Intended for tests only."""
    global _user_facing_failure_emitted
    with _dedup_lock:
        _user_facing_failure_emitted = False


def _user_facing_failure_was_emitted() -> bool:
    """Return whether the user-facing failure line was already emitted."""
    with _dedup_lock:
        return _user_facing_failure_emitted


# ---------------------------------------------------------------------------
# Refresh helpers (sync bridge over the async TokenManager)
# ---------------------------------------------------------------------------


def _run_in_fresh_loop(coro: Any) -> Any:
    """Execute *coro* on a temporary asyncio loop and return its result.

    The TokenManager API is async; the centralized sync client lives in
    a synchronous code path. This shim mirrors the pattern used by
    ``specify_cli.tracker.saas_client``.
    """
    new_loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(new_loop)
        return new_loop.run_until_complete(coro)
    finally:
        with suppress(Exception):
            asyncio.set_event_loop(None)
        new_loop.close()


def _fetch_access_token_sync() -> str | None:
    """Return a valid access token from the TokenManager, or ``None``."""
    tm = get_token_manager()
    if not tm.is_authenticated:
        return None
    try:
        return _run_in_fresh_loop(tm.get_access_token())
    except AuthenticationError:
        return None


def _force_refresh_sync() -> None:
    """Force a token refresh, raising :class:`AuthRefreshFailed` on failure.

    Marks the current session's access token as expired so that
    ``refresh_if_needed()`` actually performs work, then awaits the
    refresh on a fresh loop.
    """
    tm = get_token_manager()
    session = tm.get_current_session()
    if session is None:
        raise AuthRefreshFailed(
            "No active session to refresh. Run `spec-kitty auth login`.",
            error_code="not_authenticated",
        )
    session.access_token_expires_at = datetime.now(UTC) - timedelta(seconds=60)
    try:
        _run_in_fresh_loop(tm.refresh_if_needed())
    except TokenRefreshError as exc:
        raise AuthRefreshFailed(
            f"Token refresh failed: {exc}",
            error_code="refresh_token_invalid",
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise AuthRefreshFailed(
            f"Token refresh raised unexpected error: {exc}",
            error_code="refresh_unexpected",
        ) from exc


# ---------------------------------------------------------------------------
# Sync client
# ---------------------------------------------------------------------------


class AuthenticatedClient:
    """Centralized synchronous authenticated HTTP transport (FR-030).

    Wraps an :class:`httpx.Client` with bearer injection and a
    refresh-then-retry-once policy on 401. Every callable that needs a
    bearer token in a synchronous code path goes through here.

    The class is intentionally thin: the heavy lifting (single-flight
    refresh, secure storage, network fallback) lives in
    :class:`specify_cli.auth.token_manager.TokenManager` and the
    stdlib-fallback helper. We add only:

    * the public class boundary that the architectural test pins, and
    * the per-invocation dedup state for failure logging.

    Example::

        from specify_cli.auth.transport import get_client

        client = get_client()
        resp = client.request("POST", url, json=payload)
        resp.raise_for_status()
    """

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._timeout = timeout
        # Note: we keep an injected ``httpx.Client`` only when callers
        # explicitly hand one in (tests use this to mock the transport).
        # The architectural test allows ``httpx.Client(...)`` *only in
        # this module*, so wrapping the constructor here is the
        # invariant boundary.
        self._client = client

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    def request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute an authenticated HTTP request with refresh-then-retry on 401.

        Raises:
            NotAuthenticatedError: No session available.
            AuthRefreshFailed: Forced refresh exhausted recoverable paths.
        """
        access_token = _fetch_access_token_sync()
        if access_token is None:
            raise NotAuthenticatedError(
                "Authentication required. Run `spec-kitty auth login`."
            )

        response = self._send(method, url, access_token, kwargs)

        if response.status_code == 401:
            with suppress(Exception):
                response.close()
            try:
                _force_refresh_sync()
            except AuthRefreshFailed as exc:
                _emit_user_facing_failure_once(
                    AUTH_RELOGIN_MESSAGE
                )
                raise exc

            access_token = _fetch_access_token_sync()
            if access_token is None:
                _emit_user_facing_failure_once(AUTH_RELOGIN_MESSAGE)
                raise AuthRefreshFailed(
                    "Refresh succeeded but no access token is available.",
                    error_code="refresh_no_token",
                )

            response = self._send(method, url, access_token, kwargs)
            if response.status_code == 401:
                _emit_user_facing_failure_once(AUTH_RELOGIN_MESSAGE)
                raise AuthRefreshFailed(
                    "Server still returned 401 after a forced refresh.",
                    error_code="post_refresh_401",
                )

        return response

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("DELETE", url, **kwargs)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _send(
        self,
        method: str,
        url: str,
        access_token: str,
        kwargs: dict[str, Any],
    ) -> httpx.Response:
        """Inject the bearer header and dispatch the request.

        Honors the SaaS stdlib HTTPS fallback when the configured SaaS
        host is unreachable via httpx (mirrors :class:`OAuthHttpClient`).
        """
        caller_headers = kwargs.get("headers") or {}
        headers = dict(caller_headers)
        headers["Authorization"] = f"Bearer {access_token}"
        send_kwargs = dict(kwargs)
        send_kwargs["headers"] = headers
        return request_with_fallback_sync(
            method,
            url,
            timeout=self._timeout,
            client=self._client,
            **send_kwargs,
        )


# ---------------------------------------------------------------------------
# Async client (delegates to OAuthHttpClient for the refresh-then-retry path)
# ---------------------------------------------------------------------------


class AsyncAuthenticatedClient:
    """Async analog of :class:`AuthenticatedClient`.

    Today this class is a thin wrapper around
    :class:`specify_cli.auth.http.OAuthHttpClient` so that async callers
    have a stable import path (``from specify_cli.auth.transport import
    AsyncAuthenticatedClient``) that lives behind the architectural
    boundary. The dedup state is shared with the sync client via the
    module-level ``_user_facing_failure_emitted`` boolean.
    """

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        # Lazy import to avoid a hard cycle at module-load time.
        from specify_cli.auth.http.transport import OAuthHttpClient

        self._inner = OAuthHttpClient(timeout=timeout, client=client)

    async def request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        try:
            return await self._inner.request(method, url, **kwargs)
        except TokenRefreshError as exc:
            _emit_user_facing_failure_once(AUTH_RELOGIN_MESSAGE)
            raise AuthRefreshFailed(str(exc), error_code="refresh_token_invalid") from exc

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("PUT", url, **kwargs)

    async def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("PATCH", url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("DELETE", url, **kwargs)


# ---------------------------------------------------------------------------
# Process-scoped singleton accessors
# ---------------------------------------------------------------------------


_client_lock = threading.Lock()
_sync_client: AuthenticatedClient | None = None
_async_client: AsyncAuthenticatedClient | None = None


def get_client(*, timeout: float = 30.0) -> AuthenticatedClient:
    """Return the process-scoped synchronous :class:`AuthenticatedClient`.

    The first call constructs the client; subsequent calls return the
    same instance. Thread-safe via double-checked locking.
    """
    global _sync_client
    if _sync_client is None:
        with _client_lock:
            if _sync_client is None:
                _sync_client = AuthenticatedClient(timeout=timeout)
    return _sync_client


def get_async_client(*, timeout: float = 30.0) -> AsyncAuthenticatedClient:
    """Return the process-scoped :class:`AsyncAuthenticatedClient`."""
    global _async_client
    if _async_client is None:
        with _client_lock:
            if _async_client is None:
                _async_client = AsyncAuthenticatedClient(timeout=timeout)
    return _async_client


def reset_clients() -> None:
    """Drop process-scoped client singletons. For tests only."""
    global _sync_client, _async_client
    with _client_lock:
        _sync_client = None
        _async_client = None


__all__ = [
    "AuthenticatedClient",
    "AsyncAuthenticatedClient",
    "AuthRefreshFailed",
    "get_client",
    "get_async_client",
    "reset_clients",
    "reset_user_facing_dedup",
]
