"""SaaS Tracker HTTP client with auth, retry, polling, and error handling.

All SaaS-backed tracker operations flow through ``SaaSTrackerClient``.
Endpoint paths match the PRI-12 frozen contract exactly.
"""

from __future__ import annotations

import secrets
import time
import uuid
from typing import Any

import httpx

from specify_cli.sync.auth import AuthClient, CredentialStore
from specify_cli.sync.config import SyncConfig


class SaaSTrackerClientError(RuntimeError):
    """Raised when a SaaS tracker API call fails."""


def _poll_jitter_multiplier() -> float:
    """Return a cryptographically strong jitter multiplier in [0.8, 1.2]."""
    return 0.8 + (secrets.randbelow(4001) / 10000.0)


# ---------------------------------------------------------------------------
# Error-envelope helpers
# ---------------------------------------------------------------------------

def _parse_error_envelope(response: httpx.Response) -> dict[str, Any]:
    """Extract PRI-12 error envelope fields from a non-2xx response.

    Returns a dict with keys: code, category, message, retryable,
    user_action_required, source, retry_after_seconds.
    Missing keys default to ``None`` (or ``False`` for booleans).
    """
    try:
        body: dict[str, Any] = response.json()
    except Exception:
        return {
            "code": None,
            "category": None,
            "message": f"HTTP {response.status_code}",
            "retryable": False,
            "user_action_required": None,
            "source": None,
            "retry_after_seconds": None,
        }

    return {
        "code": body.get("code"),
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
    credential_store:
        Provides Bearer tokens and team slug.  Falls back to a default
        ``CredentialStore()`` when *None*.
    sync_config:
        Provides the server base URL.  Falls back to a default
        ``SyncConfig()`` when *None*.
    timeout:
        Per-request HTTP timeout in seconds (default 30).
    """

    def __init__(
        self,
        credential_store: CredentialStore | None = None,
        sync_config: SyncConfig | None = None,
        *,
        timeout: float = 30.0,
    ) -> None:
        self._credential_store = credential_store or CredentialStore()  # type: ignore[no-untyped-call]
        self._sync_config = sync_config or SyncConfig()  # type: ignore[no-untyped-call]
        self._base_url: str = self._sync_config.get_server_url()
        self._timeout = timeout

    _STATUS_PATH = "/api/v1/tracker/status/"
    _MAPPINGS_PATH = "/api/v1/tracker/mappings/"
    _PULL_PATH = "/api/v1/tracker/pull/"
    _PUSH_PATH = "/api/v1/tracker/push/"
    _RUN_PATH = "/api/v1/tracker/run/"
    _OPERATIONS_PATH = "/api/v1/tracker/operations/{operation_id}/"

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
        """Issue a single HTTP request with auth + team-slug headers."""
        access_token = self._credential_store.get_access_token()
        if access_token is None:
            raise SaaSTrackerClientError(
                "No valid access token. Run `spec-kitty auth login` to authenticate."
            )

        team_slug = self._credential_store.get_team_slug()
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
                auth_client = AuthClient()  # type: ignore[no-untyped-call]
                auth_client.credential_store = self._credential_store
                auth_client.config = self._sync_config
                auth_client.refresh_tokens()
            except Exception as exc:
                raise SaaSTrackerClientError(
                    "Session expired. Run `spec-kitty auth login` to re-authenticate."
                ) from exc

            response = self._request(
                method, path, json=json, headers=headers, params=params
            )
            if response.status_code == 401:
                raise SaaSTrackerClientError(
                    "Session expired. Run `spec-kitty auth login` to re-authenticate."
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
                    envelope.get("message") or "Rate limited by SaaS API."
                )

        # --- Other non-2xx ---
        if response.status_code >= 400:
            envelope = _parse_error_envelope(response)
            msg = envelope.get("message") or f"HTTP {response.status_code}"
            # user_action_required is a boolean per PRI-12 ErrorEnvelope.
            # When True, suffix the message with generic guidance.
            if envelope.get("user_action_required"):
                msg += " (action required — check the Spec Kitty dashboard)"
            raise SaaSTrackerClientError(msg)

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
            jittered_delay = delay * _poll_jitter_multiplier()
            time.sleep(jittered_delay)
            delay = min(delay * 2, cap)

    # ----- synchronous endpoints -----

    def pull(
        self,
        provider: str,
        project_slug: str,
        *,
        limit: int = 100,
        cursor: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST /api/v1/tracker/pull -- pull items from external tracker."""
        payload: dict[str, Any] = {
            "provider": provider,
            "project_slug": project_slug,
            "limit": limit,
        }
        if cursor is not None:
            payload["cursor"] = cursor
        if filters is not None:
            payload["filters"] = filters

        response = self._request_with_retry("POST", self._PULL_PATH, json=payload)
        result: dict[str, Any] = response.json()
        return result

    def status(self, provider: str, project_slug: str) -> dict[str, Any]:
        """GET /api/v1/tracker/status -- connection/sync status."""
        response = self._request_with_retry(
            "GET",
            self._STATUS_PATH,
            params={"provider": provider, "project_slug": project_slug},
        )
        result: dict[str, Any] = response.json()
        return result

    def mappings(self, provider: str, project_slug: str) -> dict[str, Any]:
        """GET /api/v1/tracker/mappings -- field mappings."""
        response = self._request_with_retry(
            "GET",
            self._MAPPINGS_PATH,
            params={"provider": provider, "project_slug": project_slug},
        )
        result: dict[str, Any] = response.json()
        return result

    # ----- async-capable endpoints -----

    def push(
        self,
        provider: str,
        project_slug: str,
        items: list[dict[str, Any]],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """POST /api/v1/tracker/push -- push items to external tracker.

        May return 200 (sync) or 202 (async -> poll).
        """
        key = idempotency_key or str(uuid.uuid4())
        payload: dict[str, Any] = {
            "provider": provider,
            "project_slug": project_slug,
            "items": items,
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
        project_slug: str,
        *,
        pull_first: bool = True,
        limit: int = 100,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """POST /api/v1/tracker/run -- full sync cycle.

        May return 200 (sync) or 202 (async -> poll).
        """
        key = idempotency_key or str(uuid.uuid4())
        payload: dict[str, Any] = {
            "provider": provider,
            "project_slug": project_slug,
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
