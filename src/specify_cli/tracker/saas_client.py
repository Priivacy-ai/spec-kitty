"""SaaS Tracker HTTP client with auth, retry, polling, and error handling.

All SaaS-backed tracker operations flow through ``SaaSTrackerClient``.
Endpoint paths match the PRI-12 frozen contract exactly.

Authentication (WP08 rewiring):
    Tokens and team context are read from the process-wide ``TokenManager``
    via ``specify_cli.auth.get_token_manager()``. Because the public surface
    is synchronous (``httpx.Client``) but ``TokenManager`` is async, a small
    sync bridge (``_fetch_access_token_sync`` + ``_force_refresh_sync``)
    runs token operations on a short-lived event loop.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
import secrets
import time
import uuid
from datetime import datetime, timedelta, UTC
from typing import Any, cast

import httpx

from specify_cli.auth import get_token_manager
from specify_cli.auth.errors import (
    AuthenticationError,
    NotAuthenticatedError,
)
from specify_cli.sync.config import SyncConfig
from specify_cli.core.contract_gate import validate_outbound_payload

_SESSION_EXPIRED_MESSAGE = (
    "Session expired. Run `spec-kitty auth login` to re-authenticate."
)


class SaaSTrackerClientError(RuntimeError):
    """Raised when a SaaS tracker API call fails.

    Attributes carry structured PRI-12 error envelope data for
    programmatic inspection (e.g., stale-binding detection).
    Backward compatible: ``SaaSTrackerClientError("msg")`` still works,
    and ``str(e)`` returns the message.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
        user_action_required: bool = False,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.user_action_required = user_action_required


def _poll_jitter_multiplier() -> float:
    """Return a cryptographically strong jitter multiplier in [0.8, 1.2]."""
    return 0.8 + (secrets.randbelow(4001) / 10000.0)


def _run_in_fresh_loop(coro: Any) -> Any:
    """Run ``coro`` on a fresh asyncio loop and return its result.

    Assumes the caller is not running inside an event loop itself. The
    SaaSTrackerClient is a synchronous transport so this assumption holds
    for the CLI code paths that use it.
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
    """Return a valid access token from TokenManager, or ``None`` if unauth."""
    tm = get_token_manager()
    if not tm.is_authenticated:
        return None
    try:
        return cast("str | None", _run_in_fresh_loop(tm.get_access_token()))
    except AuthenticationError:
        return None


def _force_refresh_sync() -> bool:
    """Force a token refresh via TokenManager (sync bridge).

    Marks the current session's access token as expired so the single-flight
    ``refresh_if_needed()`` actually runs. Returns ``True`` on success,
    raises ``AuthenticationError`` if refresh fails.
    """
    tm = get_token_manager()
    session = tm.get_current_session()
    if session is None:
        raise NotAuthenticatedError("No session to refresh")
    # Bump expiry so refresh_if_needed treats the token as stale.
    session.access_token_expires_at = datetime.now(UTC) - timedelta(seconds=60)
    _run_in_fresh_loop(tm.refresh_if_needed())
    return True


def _current_team_slug_sync() -> str | None:
    """Return the current team slug (team id) from TokenManager session, or None."""
    tm = get_token_manager()
    session = tm.get_current_session()
    if session is None or not session.teams:
        return None
    for team in session.teams:
        if team.id == session.default_team_id:
            return team.id
    return session.teams[0].id


# ---------------------------------------------------------------------------
# Error-envelope helpers
# ---------------------------------------------------------------------------

def _parse_error_envelope(response: httpx.Response) -> dict[str, Any]:
    """Extract PRI-12 error envelope fields from a non-2xx response.

    Returns a dict with keys: error_code, category, message, retryable,
    user_action_required, source, retry_after_seconds.
    Missing keys default to ``None`` (or ``False`` for booleans).
    """
    try:
        body: dict[str, Any] = response.json()
    except Exception:
        return {
            "error_code": None,
            "category": None,
            "message": f"HTTP {response.status_code}",
            "retryable": False,
            "user_action_required": None,
            "source": None,
            "retry_after_seconds": None,
        }

    return {
        "error_code": body.get("error_code"),
        "category": body.get("category"),
        "message": body.get("message", f"HTTP {response.status_code}"),
        "retryable": body.get("retryable", False),
        "user_action_required": body.get("user_action_required"),
        "source": body.get("source"),
        "retry_after_seconds": body.get("retry_after_seconds"),
    }


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class SaaSTrackerClient:
    """Low-level synchronous HTTP transport for the SaaS tracker API.

    Parameters
    ----------
    sync_config:
        Provides the server base URL.  Falls back to a default
        ``SyncConfig()`` when *None*.
    timeout:
        Per-request HTTP timeout in seconds (default 30).

    Notes
    -----
    Tokens and team slug are sourced from the process-wide TokenManager
    (see module docstring). Callers no longer pass a credential store.
    """

    def __init__(
        self,
        sync_config: SyncConfig | None = None,
        *,
        timeout: float = 30.0,
    ) -> None:
        self._sync_config = sync_config or SyncConfig()
        self._base_url: str = self._sync_config.get_server_url()
        self._timeout = timeout

    _STATUS_PATH = "/api/v1/tracker/status/"
    _MAPPINGS_PATH = "/api/v1/tracker/mappings/"
    _PULL_PATH = "/api/v1/tracker/pull/"
    _PUSH_PATH = "/api/v1/tracker/push/"
    _RUN_PATH = "/api/v1/tracker/run/"
    _OPERATIONS_PATH = "/api/v1/tracker/operations/{operation_id}/"
    _SEARCH_ISSUES_PATH = "/api/v1/tracker/issue-search/"
    _LIST_TICKETS_PATH = "/api/v1/tracker/list-tickets/"
    _BIND_ORIGIN_PATH = "/api/v1/tracker/mission-origin/bind/"
    _RESOURCES_PATH = "/api/v1/tracker/resources/"
    _BIND_RESOLVE_PATH = "/api/v1/tracker/bind-resolve/"
    _BIND_CONFIRM_PATH = "/api/v1/tracker/bind-confirm/"
    _BIND_VALIDATE_PATH = "/api/v1/tracker/bind-validate/"

    # ----- routing helpers -----

    def _routing_params(
        self,
        provider: str,
        project_slug: str | None,
        binding_ref: str | None,
    ) -> dict[str, str]:
        """Build the routing-key dict for an API call.

        When *binding_ref* is provided it takes precedence over
        *project_slug*.  If neither is supplied a
        ``SaaSTrackerClientError`` with ``error_code="missing_routing_key"``
        is raised.
        """
        params: dict[str, str] = {"provider": provider}
        if binding_ref:
            params["binding_ref"] = binding_ref
        elif project_slug:
            params["project_slug"] = project_slug
        else:
            raise SaaSTrackerClientError(
                "Either project_slug or binding_ref must be provided.",
                error_code="missing_routing_key",
                status_code=None,
            )
        return params

    # ----- low-level request helpers -----

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Issue a single HTTP request with auth + team-slug headers.

        Tokens and team slug come from the process-wide ``TokenManager``
        via the sync bridge helpers at the top of this module. No direct
        filesystem or credential-store access.
        """
        access_token = _fetch_access_token_sync()
        if access_token is None:
            raise SaaSTrackerClientError(
                "No valid access token. Run `spec-kitty auth login` to authenticate."
            )

        team_slug = _current_team_slug_sync()
        if not team_slug:
            raise SaaSTrackerClientError(
                "No team context available. Run `spec-kitty auth login` to authenticate."
            )

        merged_headers: dict[str, str] = {
            "Authorization": f"Bearer {access_token}",
            "X-Team-Slug": team_slug,
        }
        if headers:
            merged_headers.update(headers)

        url = f"{self._base_url}{path}"

        try:
            with httpx.Client(timeout=self._timeout) as client:
                return client.request(
                    method,
                    url,
                    json=json,
                    headers=merged_headers,
                    params=params,
                )
        except httpx.ConnectError as exc:
            raise SaaSTrackerClientError(
                f"Cannot connect to Spec Kitty SaaS at {url}. "
                "Check your network connection."
            ) from exc
        except httpx.TimeoutException as exc:
            raise SaaSTrackerClientError(
                f"Cannot connect to Spec Kitty SaaS at {url}. "
                "Check your network connection."
            ) from exc

    def _request_with_retry(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Issue a request with 401-refresh and 429-rate-limit retry logic."""
        response = self._request(
            method, path, json=json, headers=headers, params=params
        )

        # --- 401: one refresh + retry ---
        if response.status_code == 401:
            try:
                # Force a refresh via TokenManager (sync bridge). The single-flight
                # lock inside TokenManager guarantees at most one concurrent refresh
                # across threads / callers.
                _force_refresh_sync()
            except AuthenticationError as exc:
                raise SaaSTrackerClientError(
                    _SESSION_EXPIRED_MESSAGE,
                    error_code="session_expired",
                    status_code=401,
                    user_action_required=True,
                ) from exc
            except Exception as exc:
                raise SaaSTrackerClientError(
                    _SESSION_EXPIRED_MESSAGE,
                    error_code="session_expired",
                    status_code=401,
                    user_action_required=True,
                ) from exc

            response = self._request(
                method, path, json=json, headers=headers, params=params
            )
            if response.status_code == 401:
                raise SaaSTrackerClientError(
                    _SESSION_EXPIRED_MESSAGE,
                    error_code="session_expired",
                    status_code=401,
                    user_action_required=True,
                )

        # --- 429: respect retry_after_seconds ---
        if response.status_code == 429:
            envelope = _parse_error_envelope(response)
            wait_seconds = envelope.get("retry_after_seconds")
            if wait_seconds is None or not isinstance(wait_seconds, (int, float)):
                wait_seconds = 5
            time.sleep(float(wait_seconds))

            response = self._request(
                method, path, json=json, headers=headers, params=params
            )
            if response.status_code == 429:
                envelope = _parse_error_envelope(response)
                raise SaaSTrackerClientError(
                    envelope.get("message") or "Rate limited by SaaS API.",
                    error_code="rate_limited",
                    status_code=429,
                )

        # --- Other non-2xx ---
        if response.status_code >= 400:
            envelope = _parse_error_envelope(response)
            msg = envelope.get("message") or f"HTTP {response.status_code}"
            # user_action_required is a boolean per PRI-12 ErrorEnvelope.
            # When True, suffix the message with generic guidance.
            if envelope.get("user_action_required"):
                msg += " (action required — check the Spec Kitty dashboard)"
            raise SaaSTrackerClientError(
                msg,
                error_code=envelope.get("error_code"),
                status_code=response.status_code,
                details=envelope,
                user_action_required=bool(envelope.get("user_action_required")),
            )

        return response

    # ----- polling -----

    def _poll_operation(self, operation_id: str) -> dict[str, Any]:
        """Poll an async operation until terminal state.

        Uses exponential backoff: 1s, 2s, 4s, ... capped at 30s.
        Total timeout: 300 seconds (5 minutes).
        """
        delay = 1.0
        cap = 30.0
        total_timeout = 300.0
        start = time.monotonic()

        while True:
            elapsed = time.monotonic() - start
            if elapsed >= total_timeout:
                raise SaaSTrackerClientError(
                    f"Operation {operation_id} timed out after 5 minutes"
                )

            response = self._request_with_retry(
                "GET",
                self._OPERATIONS_PATH.format(operation_id=operation_id),
            )

            body: dict[str, Any] = response.json()
            status = body.get("status")

            if status == "completed":
                result_val = body.get("result", body)
                return dict(result_val) if isinstance(result_val, dict) else body

            if status == "failed":
                error_data = body.get("error")
                if isinstance(error_data, dict):
                    # error_data is an ErrorEnvelope per PRI-12.
                    # user_action_required is boolean, not a string.
                    error_msg = error_data.get("message") or "Operation failed"
                    if error_data.get("user_action_required"):
                        error_msg += " (action required — check the Spec Kitty dashboard)"
                else:
                    error_msg = str(error_data) if error_data else "Operation failed"
                raise SaaSTrackerClientError(error_msg)

            # pending / running -- sleep with jitter then retry
            jitter_basis_points = secrets.randbelow(4000)
            jitter_factor = 0.8 + (jitter_basis_points / 10000)
            jittered_delay = delay * jitter_factor
            time.sleep(jittered_delay)
            delay = min(delay * 2, cap)

    # ----- synchronous endpoints -----

    def pull(
        self,
        provider: str,
        project_slug: str | None = None,
        *,
        binding_ref: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST /api/v1/tracker/pull -- pull items from external tracker."""
        payload: dict[str, Any] = {
            **self._routing_params(provider, project_slug, binding_ref),
            "limit": limit,
        }
        if cursor is not None:
            payload["cursor"] = cursor
        if filters is not None:
            payload["filters"] = filters

        response = self._request_with_retry("POST", self._PULL_PATH, json=payload)
        result: dict[str, Any] = response.json()
        return result

    def status(
        self,
        provider: str,
        project_slug: str | None = None,
        *,
        binding_ref: str | None = None,
        installation_wide: bool = False,
    ) -> dict[str, Any]:
        """GET /api/v1/tracker/status -- connection/sync status.

        When *installation_wide* is True, sends only ``provider`` as a query
        param (no project_slug or binding_ref). The SaaS host returns
        installation-level status for that provider.
        """
        if installation_wide:
            params: dict[str, str] = {"provider": provider}
        else:
            params = self._routing_params(provider, project_slug, binding_ref)
        response = self._request_with_retry(
            "GET",
            self._STATUS_PATH,
            params=params,
        )
        result: dict[str, Any] = response.json()
        return result

    def mappings(
        self,
        provider: str,
        project_slug: str | None = None,
        *,
        binding_ref: str | None = None,
    ) -> dict[str, Any]:
        """GET /api/v1/tracker/mappings -- field mappings."""
        params = (
            self._routing_params(provider, project_slug, binding_ref)
            if binding_ref or project_slug
            else {"provider": provider}
        )
        response = self._request_with_retry(
            "GET",
            self._MAPPINGS_PATH,
            params=params,
        )
        result: dict[str, Any] = response.json()
        return result

    def search_issues(
        self,
        provider: str,
        project_slug: str | None = None,
        *,
        binding_ref: str | None = None,
        query_text: str | None = None,
        query_key: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """POST search endpoint — find candidate issues for origin binding.

        Returns a dict with 'candidates' list and routing context
        ('resource_type', 'resource_id').

        query_key takes precedence over query_text when both provided.
        """
        payload: dict[str, Any] = {"provider": provider, "limit": limit}
        if binding_ref:
            payload["binding_ref"] = binding_ref
        elif project_slug:
            payload["project_slug"] = project_slug
        if query_key is not None:
            payload["query_key"] = query_key
        if query_text is not None:
            payload["query_text"] = query_text

        response = self._request_with_retry("POST", self._SEARCH_ISSUES_PATH, json=payload)
        result: dict[str, Any] = response.json()
        return result

    def list_tickets(
        self,
        provider: str,
        project_slug: str | None = None,
        *,
        binding_ref: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """POST browse endpoint — list visible tickets in the mapped resource."""
        payload: dict[str, Any] = {"provider": provider, "limit": limit}
        if binding_ref:
            payload["binding_ref"] = binding_ref
        elif project_slug:
            payload["project_slug"] = project_slug

        response = self._request_with_retry("POST", self._LIST_TICKETS_PATH, json=payload)
        result: dict[str, Any] = response.json()
        return result

    def bind_mission_origin(
        self,
        provider: str,
        project_slug: str | None = None,
        *,
        binding_ref: str | None = None,
        mission_id: str,
        mission_slug: str | None = None,
        external_issue_id: str,
        external_issue_key: str,
        external_issue_url: str,
        title: str,
        external_status: str = "",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """POST bind endpoint — create MissionOriginLink on SaaS.

        This is the authoritative write for the control-plane record.
        Same-origin re-bind returns success (no-op). Different-origin
        returns 409.
        """
        key = idempotency_key or str(uuid.uuid4())
        payload: dict[str, Any] = {
            "provider": provider,
            "mission_id": mission_id,
            "external_issue_id": external_issue_id,
            "external_issue_key": external_issue_key,
            "external_issue_url": external_issue_url,
            "external_title": title,
            "external_status": external_status,
        }
        if mission_slug:
            payload["mission_slug"] = mission_slug
        if binding_ref:
            payload["binding_ref"] = binding_ref
        elif project_slug:
            payload["project_slug"] = project_slug
        else:
            raise SaaSTrackerClientError(
                "Either project_slug or binding_ref must be provided.",
                error_code="invalid_routing",
                status_code=400,
            )
        response = self._request_with_retry(
            "POST",
            self._BIND_ORIGIN_PATH,
            json=payload,
            headers={"Idempotency-Key": key},
        )
        result: dict[str, Any] = response.json()
        return result

    # ----- discovery and binding endpoints -----

    def resources(self, provider: str) -> dict[str, Any]:
        """GET /api/v1/tracker/resources/ -- enumerate bindable resources."""
        response = self._request_with_retry(
            "GET",
            self._RESOURCES_PATH,
            params={"provider": provider},
        )
        result: dict[str, Any] = response.json()
        return result

    def bind_resolve(
        self,
        provider: str,
        project_identity: dict[str, Any],
    ) -> dict[str, Any]:
        """POST /api/v1/tracker/bind-resolve/ -- resolve identity to bind candidates."""
        validate_outbound_payload(project_identity, "tracker_bind")
        payload: dict[str, Any] = {
            "provider": provider,
            "project_identity": project_identity,
        }
        response = self._request_with_retry(
            "POST",
            self._BIND_RESOLVE_PATH,
            json=payload,
        )
        result: dict[str, Any] = response.json()
        return result

    def bind_confirm(
        self,
        provider: str,
        candidate_token: str,
        project_identity: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """POST /api/v1/tracker/bind-confirm/ -- confirm bind selection."""
        validate_outbound_payload(project_identity, "tracker_bind")
        key = idempotency_key or str(uuid.uuid4())
        payload: dict[str, Any] = {
            "provider": provider,
            "candidate_token": candidate_token,
            "project_identity": project_identity,
        }
        response = self._request_with_retry(
            "POST",
            self._BIND_CONFIRM_PATH,
            json=payload,
            headers={"Idempotency-Key": key},
        )
        result: dict[str, Any] = response.json()
        return result

    def bind_validate(
        self,
        provider: str,
        binding_ref: str,
        project_identity: dict[str, Any],
    ) -> dict[str, Any]:
        """POST /api/v1/tracker/bind-validate/ -- validate binding ref."""
        validate_outbound_payload(project_identity, "tracker_bind")
        payload: dict[str, Any] = {
            "provider": provider,
            "binding_ref": binding_ref,
            "project_identity": project_identity,
        }
        response = self._request_with_retry(
            "POST",
            self._BIND_VALIDATE_PATH,
            json=payload,
        )
        result: dict[str, Any] = response.json()
        return result

    # ----- async-capable endpoints -----

    def push(
        self,
        provider: str,
        project_slug: str | None = None,
        items: list[dict[str, Any]] | None = None,
        *,
        binding_ref: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """POST /api/v1/tracker/push -- push items to external tracker.

        May return 200 (sync) or 202 (async -> poll).
        """
        key = idempotency_key or str(uuid.uuid4())
        payload: dict[str, Any] = {
            **self._routing_params(provider, project_slug, binding_ref),
            "items": items or [],
        }
        response = self._request_with_retry(
            "POST",
            self._PUSH_PATH,
            json=payload,
            headers={"Idempotency-Key": key},
        )

        if response.status_code == 202:
            body: dict[str, Any] = response.json()
            operation_id = body["operation_id"]
            return self._poll_operation(str(operation_id))

        result: dict[str, Any] = response.json()
        return result

    def run(
        self,
        provider: str,
        project_slug: str | None = None,
        *,
        binding_ref: str | None = None,
        pull_first: bool = True,
        limit: int = 100,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """POST /api/v1/tracker/run -- full sync cycle.

        May return 200 (sync) or 202 (async -> poll).
        """
        key = idempotency_key or str(uuid.uuid4())
        payload: dict[str, Any] = {
            **self._routing_params(provider, project_slug, binding_ref),
            "pull_first": pull_first,
            "limit": limit,
        }
        response = self._request_with_retry(
            "POST",
            self._RUN_PATH,
            json=payload,
            headers={"Idempotency-Key": key},
        )

        if response.status_code == 202:
            body: dict[str, Any] = response.json()
            operation_id = body["operation_id"]
            return self._poll_operation(str(operation_id))

        result: dict[str, Any] = response.json()
        return result
