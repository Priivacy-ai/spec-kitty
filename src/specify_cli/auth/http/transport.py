"""OAuth-aware async HTTP client.

`OAuthHttpClient` wraps `httpx.AsyncClient` and:
  1. Injects `Authorization: Bearer <access_token>` on every request using the
     process-wide `TokenManager` (fetched via `get_token_manager()`).
  2. On a 401 response, forces a refresh via `TokenManager.refresh_if_needed()`
     (single-flight) and retries the request exactly once. The server's 401 is
     authoritative even when the local expiry timer says the token is still
     valid, so we mark the current session's access token as expired before
     calling refresh.
  3. On the retry, if the response is still 401, raises
     `NotAuthenticatedError` so callers can surface a clean login prompt.
  4. Translates `httpx.TransportError` (DNS, connection, timeout) into
     `NetworkError` to match the auth error hierarchy.

The client never reads or writes tokens directly — all token access goes
through `TokenManager.get_access_token()`. This keeps the refresh/retry policy
centralized and ensures other code paths (WebSocket pre-connect, sync batch,
tracker) share the same single-flight refresh behavior.
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from typing import Any

import httpx

from specify_cli.auth import get_token_manager
from specify_cli.auth.errors import (
    NetworkError,
    NotAuthenticatedError,
    TokenRefreshError,
)

# Default timeout for all HTTP operations (per WP08 spec).
DEFAULT_TIMEOUT_SECONDS = 30.0


class OAuthHttpClient:
    """Async HTTP client that injects OAuth bearer tokens and retries once on 401.

    Usage:
        async with OAuthHttpClient() as client:
            response = await client.get("https://api.example.com/v1/teams")
            response.raise_for_status()
            data = response.json()

    All HTTP methods (`get`, `post`, `put`, `patch`, `delete`, `request`) accept
    the same kwargs as `httpx.AsyncClient.request()`. If the caller supplies an
    explicit `Authorization` header in `headers`, it is overwritten with the
    bearer token produced by `TokenManager.get_access_token()`.
    """

    def __init__(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the client.

        Args:
            timeout: Per-request timeout in seconds (default 30s).
            client: Optional pre-constructed `httpx.AsyncClient`. When provided,
                the caller owns its lifecycle (we will not close it). When not
                provided, we create and own an internal client.
        """
        self._timeout = timeout
        self._external_client = client is not None
        self._client: httpx.AsyncClient = client or httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self) -> OAuthHttpClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying httpx client (only if we own it)."""
        if not self._external_client:
            await self._client.aclose()

    async def request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Perform an HTTP request with bearer injection + 401 retry-once.

        Raises:
            NotAuthenticatedError: If no session is available or the refresh
                fails to produce a usable token.
            TokenRefreshError: If refresh explicitly fails (propagated).
            NetworkError: If the underlying transport raises
                `httpx.TransportError` (DNS, connection, timeout, etc.).
        """
        tm = get_token_manager()

        # First attempt: inject the current access token (auto-refresh if near expiry).
        try:
            access_token = await tm.get_access_token()
        except (NotAuthenticatedError, TokenRefreshError):
            # Propagate auth errors unchanged — callers differentiate these.
            raise

        response = await self._send(method, url, access_token, kwargs)

        # If the server rejected our token, try a forced refresh + retry-once.
        if response.status_code == 401:
            # Close the stale response body before retrying (httpx best practice).
            await response.aclose()

            # The server's 401 is authoritative: the token is invalid even if
            # our local expiry timer says it's still good. Mark the current
            # access token as expired so `refresh_if_needed()` will actually
            # refresh rather than short-circuit as a no-op.
            self._force_access_token_expired(tm)

            # Force a refresh. If the server invalidated our session mid-flight,
            # `refresh_if_needed()` will raise RefreshTokenExpiredError /
            # SessionInvalidError (both subclasses of TokenRefreshError).
            await tm.refresh_if_needed()

            # Re-fetch the (now-refreshed) access token.
            access_token = await tm.get_access_token()

            response = await self._send(method, url, access_token, kwargs)

            if response.status_code == 401:
                # Still unauthorized after a fresh token — the session is dead.
                await response.aclose()
                raise NotAuthenticatedError(
                    "Authentication failed after token refresh. Please log in again.",
                )

        return response

    @staticmethod
    def _force_access_token_expired(tm: Any) -> None:
        """Mark the current session's access token as expired.

        This is the minimal-surface-area way to force the single-flight
        `refresh_if_needed()` path to actually refresh after a server-side 401.
        If there is no current session we leave the TokenManager untouched —
        the subsequent ``refresh_if_needed()`` will raise
        ``NotAuthenticatedError`` naturally.
        """
        session = tm.get_current_session()
        if session is None:
            return
        # Bump expiry well into the past so any buffer window still classifies
        # as expired.
        session.access_token_expires_at = datetime.now(UTC) - timedelta(seconds=60)

    async def _send(
        self,
        method: str,
        url: str,
        access_token: str,
        kwargs: dict[str, Any],
    ) -> httpx.Response:
        """Inject the bearer header and delegate to httpx, translating network errors."""
        # Merge Authorization into caller-supplied headers (without mutating the caller's dict).
        caller_headers = kwargs.get("headers") or {}
        headers = dict(caller_headers)
        headers["Authorization"] = f"Bearer {access_token}"
        send_kwargs = dict(kwargs)
        send_kwargs["headers"] = headers

        try:
            return await self._client.request(method, url, **send_kwargs)
        except httpx.TransportError as exc:
            raise NetworkError(f"HTTP transport error: {exc}") from exc

    # --- Convenience methods (match httpx.AsyncClient surface) ---

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
