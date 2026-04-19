"""DeviceCodeFlow — RFC 8628 Device Authorization Grant orchestration (WP05).

This is the orchestration class for the headless login path. It ties together
the WP03 primitives (``DeviceFlowState``, ``DeviceFlowPoller``,
``format_user_code``) with the SaaS HTTP calls (``POST /oauth/device``,
``POST /oauth/token``, ``GET /api/v1/me``) to produce a
:class:`StoredSession` ready for ``TokenManager.set_session()``.

Contract with the SaaS (feature 080, contracts/ directory):

- ``POST /oauth/device`` — returns a device code, user code, verification URI,
  expiry, and suggested polling interval per RFC 8628 §3.2.
- ``POST /oauth/token`` with
  ``grant_type=urn:ietf:params:oauth:grant-type:device_code`` — exchanges the
  device code for ``access_token`` + ``refresh_token`` once the user has
  approved. The response now (SaaS amendment landed 2026-04-09) includes both
  ``refresh_token_expires_in`` (int seconds) and ``refresh_token_expires_at``
  (ISO-8601 UTC string).
- ``GET /api/v1/me`` — returns ``user_id``, ``email``, ``name``, ``teams[]``
  plus the same refresh-token expiry fields.

Per C-012 and the 2026-04-09 SaaS refresh-TTL amendment, this flow reads the
refresh-token expiry directly from the server response — it never hardcodes a
TTL and never computes the expiry locally. The ``_resolve_refresh_expiry``
helper mirrors the one in :class:`AuthorizationCodeFlow` exactly.

Per D-5 the SaaS base URL is never hardcoded here; callers must pass it in via
the constructor, typically from
:func:`specify_cli.auth.config.get_saas_base_url`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, UTC
from typing import Any, cast

import httpx

from ..config import get_saas_base_url
from ..device_flow import DeviceFlowPoller, DeviceFlowState, format_user_code
from ..errors import (
    AuthenticationError,
    NetworkError,
)
from ..session import StorageBackend, StoredSession, Team

log = logging.getLogger(__name__)

_DEFAULT_CLIENT_ID = "cli_native"
_DEFAULT_SCOPE = "offline_access"
_HTTP_TIMEOUT_SECONDS = 10.0
_DEVICE_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"


class DeviceCodeFlow:
    """Orchestrates the OAuth Device Authorization Grant (RFC 8628).

    Usage::

        flow = DeviceCodeFlow(saas_base_url="https://saas.example.com")
        session = await flow.login(progress_writer=console.print)
        token_manager.set_session(session)

    The flow is stateless across calls — each ``login()`` call requests a
    fresh device code, drives its own :class:`DeviceFlowPoller` to a terminal
    state, and returns a freshly built :class:`StoredSession`.
    """

    def __init__(
        self,
        saas_base_url: str | None = None,
        client_id: str = _DEFAULT_CLIENT_ID,
        *,
        storage_backend: StorageBackend = "file",
    ) -> None:
        """Build a new flow.

        Args:
            saas_base_url: Base URL of the spec-kitty SaaS (no trailing slash).
                When ``None``, the flow calls
                :func:`specify_cli.auth.config.get_saas_base_url` itself, so
                operators must set ``SPEC_KITTY_SAAS_URL`` in the environment
                (per D-5, no hardcoded URL exists anywhere in the CLI).
                Callers that already have the URL in hand (such as
                ``_auth_login.py``) pass it in directly to avoid two env-var
                reads per login.
            client_id: OAuth client identifier. Defaults to ``"cli_native"``.
            storage_backend: Backend identifier to persist on the resulting
                :class:`StoredSession`. Should match the actual backend that
                ``TokenManager`` will use (passed by ``_auth_login.py``).
        """
        resolved = saas_base_url if saas_base_url is not None else get_saas_base_url()
        self._saas_base_url = resolved.rstrip("/")
        self._client_id = client_id
        self._storage_backend: StorageBackend = storage_backend

    async def login(
        self,
        progress_writer: Callable[[str], None] | None = None,
    ) -> StoredSession:
        """Execute the full device authorization flow end-to-end.

        Args:
            progress_writer: Optional callback for displaying progress messages
                (for example, ``rich.Console.print``). When ``None``, progress
                messages are swallowed.

        Returns:
            A :class:`StoredSession` ready for ``TokenManager.set_session()``.

        Raises:
            DeviceFlowDenied: User denied the authorization request.
            DeviceFlowExpired: Device code expired before approval.
            NetworkError: Network failure during one of the HTTP calls.
            AuthenticationError: Any other authentication failure (bad HTTP
                status, missing response fields, etc.).
        """
        writer = progress_writer if progress_writer is not None else (lambda _msg: None)

        # Step 1: request device code from the SaaS.
        device_state = await self._request_device_code()

        # Step 2: display the user code and verification URI so the operator
        # can open a browser on another device and approve the request.
        writer("")
        writer(
            f"[yellow]Visit:[/yellow] [bold blue]{device_state.verification_uri}[/bold blue]"
        )
        writer(
            f"[yellow]Code:[/yellow]  [bold green]{format_user_code(device_state.user_code)}[/bold green]"
        )
        if device_state.verification_uri_complete:
            writer(f"[dim]Or open: {device_state.verification_uri_complete}[/dim]")
        writer("")
        writer(
            f"[dim]Waiting for authorization (timeout in {device_state.expires_in // 60} minutes)...[/dim]"
        )

        # Step 3: poll the token endpoint until approval, denial, or expiry.
        # The poller uses WP03's primitives and respects the 10-second ceiling
        # per FR-018.
        poller = DeviceFlowPoller(device_state)
        tokens = await poller.poll(self._poll_token_request)

        # Step 4: fetch user info and assemble the StoredSession.
        session = await self._build_session(tokens)
        writer("")
        writer("[green]+ Authorization granted[/green]")
        return session

    # ---- Device code request ---------------------------------------------

    async def _request_device_code(self) -> DeviceFlowState:
        """POST ``/oauth/device`` to initiate the device flow.

        Raises:
            NetworkError: On httpx transport errors (connect, DNS, timeout).
            AuthenticationError: On non-200 responses or malformed JSON (for
                example, missing ``device_code``).
        """
        url = f"{self._saas_base_url}/oauth/device"
        data = {"client_id": self._client_id, "scope": _DEFAULT_SCOPE}

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
            try:
                response = await client.post(url, data=data)
            except httpx.RequestError as exc:
                raise NetworkError(
                    f"Network error requesting device code: {exc}"
                ) from exc

        if response.status_code != 200:
            body = response.text[:500]
            raise AuthenticationError(
                f"Device code request failed: HTTP {response.status_code} - {body}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise AuthenticationError(
                f"Device code response was not JSON: {exc}"
            ) from exc

        try:
            return DeviceFlowState.from_oauth_response(payload)
        except KeyError as exc:
            raise AuthenticationError(
                f"Device code response missing required field: {exc}"
            ) from exc

    # ---- Token polling ---------------------------------------------------

    async def _poll_token_request(self, device_code: str) -> dict[str, Any]:
        """POST ``/oauth/token`` with the device_code grant.

        Returns the parsed JSON body. Both success (200) and pending/error
        (400) responses are JSON bodies; the poller distinguishes them via
        the presence of the ``error`` key.

        Raises:
            NetworkError: On httpx transport errors, so the poller can log
                and retry on the next tick.
            AuthenticationError: On unexpected HTTP status codes (not 200/400).
        """
        url = f"{self._saas_base_url}/oauth/token"
        data = {
            "grant_type": _DEVICE_GRANT_TYPE,
            "device_code": device_code,
            "client_id": self._client_id,
        }

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
            try:
                response = await client.post(url, data=data)
            except httpx.RequestError as exc:
                raise NetworkError(
                    f"Network error polling for token: {exc}"
                ) from exc

        # RFC 8628 §3.5: both success and pending/error responses are JSON.
        # The poller classifies via the ``error`` key.
        if response.status_code in (200, 400):
            try:
                return cast(dict[str, Any], response.json())
            except ValueError as exc:
                raise AuthenticationError(
                    f"Token poll response was not JSON: {exc}"
                ) from exc

        raise AuthenticationError(
            f"Unexpected response from /oauth/token: HTTP {response.status_code}"
        )

    # ---- User info + StoredSession ---------------------------------------

    async def _build_session(self, tokens: dict[str, Any]) -> StoredSession:
        """Fetch user info from ``/api/v1/me`` and assemble a StoredSession.

        Contract (feature 080, contracts/protected-endpoints.md, SaaS amendment
        landed 2026-04-09): identical to
        :meth:`AuthorizationCodeFlow._build_session`, except the resulting
        session is tagged with ``auth_method="device_code"``.

        Per C-012, the CLI reads the refresh-token expiry directly from the
        SaaS response — it NEVER hardcodes a TTL and NEVER computes the
        timestamp locally. See :meth:`_resolve_refresh_expiry` for the exact
        fallback order.
        """
        url = f"{self._saas_base_url}/api/v1/me"
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
            try:
                response = await client.get(url, headers=headers)
            except httpx.RequestError as exc:
                raise NetworkError(
                    f"Network error fetching user info: {exc}"
                ) from exc

        if response.status_code != 200:
            raise AuthenticationError(
                f"User info fetch failed: HTTP {response.status_code}"
            )

        try:
            me = response.json()
        except ValueError as exc:
            raise AuthenticationError(
                f"User info response was not JSON: {exc}"
            ) from exc

        teams = [
            Team(id=t["id"], name=t["name"], role=t["role"])
            for t in me.get("teams", [])
        ]
        if not teams:
            raise AuthenticationError(
                "User has no team memberships. Contact your administrator."
            )
        # Client-picked default (see C-011): the SaaS does not return
        # ``default_team_id``; we pick the first team on first login.
        default_team_id = teams[0].id

        now = datetime.now(UTC)
        try:
            expires_in = int(tokens["expires_in"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AuthenticationError(
                "Token response missing or invalid 'expires_in' field."
            ) from exc

        refresh_token_expires_at = self._resolve_refresh_expiry(tokens, me, now)

        return StoredSession(
            user_id=me["user_id"],
            email=me["email"],  # sourced from /api/v1/me .email per C-011
            name=me.get("name", me["email"]),
            teams=teams,
            default_team_id=default_team_id,
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            session_id=tokens["session_id"],
            issued_at=now,
            access_token_expires_at=now + timedelta(seconds=expires_in),
            refresh_token_expires_at=refresh_token_expires_at,
            scope=tokens.get("scope", _DEFAULT_SCOPE),
            storage_backend=self._storage_backend,
            last_used_at=now,
            auth_method="device_code",
        )

    @staticmethod
    def _resolve_refresh_expiry(
        tokens: dict[str, Any],
        me: dict[str, Any],
        now: datetime,
    ) -> datetime | None:
        """Resolve ``refresh_token_expires_at`` from the SaaS responses.

        Per C-012 and the 2026-04-09 SaaS amendment, the CLI never hardcodes
        a refresh-token TTL. Preference order:

        1. ``refresh_token_expires_at`` from the token response (absolute).
        2. ``refresh_token_expires_at`` from ``/api/v1/me`` (absolute).
        3. ``refresh_token_expires_in`` from the token response (relative).
        4. ``None`` — server-managed, client learns expiry on refresh.
        """
        absolute = tokens.get("refresh_token_expires_at") or me.get(
            "refresh_token_expires_at"
        )
        if absolute is not None:
            return _parse_iso_utc(absolute)

        relative = tokens.get("refresh_token_expires_in")
        if relative is not None:
            try:
                return now + timedelta(seconds=int(relative))
            except (TypeError, ValueError):
                log.warning(
                    "refresh_token_expires_in was not an int: %r", relative
                )
                return None
        return None


def _parse_iso_utc(value: str) -> datetime:
    """Parse an ISO-8601 UTC timestamp, accepting the ``Z`` suffix.

    Mirrors the helper in :mod:`specify_cli.auth.flows.authorization_code`;
    the two are identical and intentionally duplicated so the two flows
    remain independently owned by different WPs.
    """
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)
