"""SaaS HTTP client for the Widen Mode feature.

Provides a thin, mockable wrapper around ``httpx`` for all SaaS calls made
by the widen flow and prereq checker.  Dependency-inject a custom
``httpx.Client`` via the ``_http`` parameter for unit tests.

All public methods:
- Raise ``SaasClientError`` (or a subclass) on any failure — raw ``httpx``
  exceptions are never propagated to callers.
- Map HTTP status codes to typed exception subclasses.
- Accept per-call timeout overrides where documented.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

import httpx

from specify_cli.saas_client.auth import AuthContext, load_auth_context
from specify_cli.saas_client.endpoints import DiscussionData, DiscussionMessage, WidenResponse
from specify_cli.saas_client.errors import (
    SaasAuthError,
    SaasClientError,
    SaasNotFoundError,
    SaasTimeoutError,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Timeout constants (seconds)
_TIMEOUT_DEFAULT = 5.0
_TIMEOUT_PREREQ_PROBE = 0.5
_TIMEOUT_DISCUSSION = 10.0


def _map_http_error(resp: httpx.Response, context: str) -> SaasClientError:
    """Convert a non-2xx ``httpx.Response`` into a typed ``SaasClientError``."""
    status = resp.status_code
    try:
        body = resp.text[:200]
    except Exception:
        body = ""
    msg = f"{context}: HTTP {status}" + (f" — {body}" if body else "")
    if status in (401, 403):
        return SaasAuthError(msg, status_code=status)
    if status == 404:
        return SaasNotFoundError(msg, status_code=status)
    return SaasClientError(msg, status_code=status)


class SaasClient:
    """Thin HTTP client for spec-kitty SaaS endpoints.

    Args:
        base_url: Root URL of the SaaS API, e.g. ``https://api.spec-kitty.io``.
        token: Bearer token for authentication.
        timeout: Default request timeout in seconds.  Individual methods may
            override this for their specific use-case.
        _http: Optional pre-constructed ``httpx.Client``.  Pass a mock client
            in tests to intercept HTTP calls without network access.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        timeout: float = _TIMEOUT_DEFAULT,
        _http: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout
        self._http = _http or httpx.Client(
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Public auth helpers
    # ------------------------------------------------------------------

    @property
    def has_token(self) -> bool:
        """Return ``True`` when a non-empty bearer token is configured.

        Use this instead of accessing ``_token`` directly so callers are
        insulated from the private attribute name.
        """
        return bool(self._token)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls, repo_root: object = None) -> SaasClient:
        """Construct from environment variables or ``.kittify/saas-auth.json``.

        Args:
            repo_root: Optional :class:`~pathlib.Path` to the repo root, passed
                through to :func:`~specify_cli.saas_client.auth.load_auth_context`.

        Returns:
            A fully initialised :class:`SaasClient`.

        Raises:
            SaasAuthError: If authentication credentials cannot be resolved.
        """
        from pathlib import Path

        root: Path | None = Path(str(repo_root)) if repo_root is not None else None
        ctx: AuthContext = load_auth_context(repo_root=root)
        return cls(base_url=ctx.saas_url, token=ctx.token)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(
        self,
        path: str,
        *,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Issue a GET request, mapping exceptions to ``SaasClientError``."""
        url = f"{self._base_url}{path}"
        effective_timeout = timeout if timeout is not None else self._timeout
        try:
            resp = self._http.get(url, timeout=effective_timeout)
        except httpx.TimeoutException as exc:
            raise SaasTimeoutError(f"GET {url} timed out after {effective_timeout}s") from exc
        except httpx.RequestError as exc:
            raise SaasClientError(f"GET {url} failed: {exc}") from exc
        if not resp.is_success:
            raise _map_http_error(resp, f"GET {url}")
        return resp

    def _post(
        self,
        path: str,
        *,
        json: object,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Issue a POST request with a JSON body, mapping exceptions to ``SaasClientError``."""
        url = f"{self._base_url}{path}"
        effective_timeout = timeout if timeout is not None else self._timeout
        try:
            resp = self._http.post(url, json=json, timeout=effective_timeout)
        except httpx.TimeoutException as exc:
            raise SaasTimeoutError(f"POST {url} timed out after {effective_timeout}s") from exc
        except httpx.RequestError as exc:
            raise SaasClientError(f"POST {url} failed: {exc}") from exc
        if not resp.is_success:
            raise _map_http_error(resp, f"POST {url}")
        return resp

    # ------------------------------------------------------------------
    # Public endpoint methods
    # ------------------------------------------------------------------

    def get_audience_default(self, mission_id: str) -> list[str]:
        """Fetch the default audience for a mission.

        ``GET /api/v1/missions/{id}/audience-default``

        Returns a list of member display names, e.g.
        ``["Alice Johnson", "Bob Smith"]``.

        Args:
            mission_id: ULID or slug identifying the mission.

        Returns:
            List of audience member display names.

        Raises:
            SaasClientError: On any HTTP or network failure.
            SaasNotFoundError: If the mission does not exist (HTTP 404).
            SaasAuthError: On auth failure (HTTP 401/403).
            SaasTimeoutError: If the request exceeds the default timeout.
        """
        path = f"/api/v1/missions/{mission_id}/audience-default"
        resp = self._get(path)
        data = resp.json()
        # Accept either {"members": [...]} or a bare list
        if isinstance(data, list):
            return [str(m) for m in data]
        members = data.get("members", [])
        return [str(m) for m in members]

    def post_widen(self, decision_id: str, invited: list[str]) -> WidenResponse:
        """Widen a decision point by inviting external participants.

        ``POST /api/v1/decision-points/{id}/widen``

        Args:
            decision_id: ULID of the decision point to widen.
            invited: List of display names (or IDs) to invite.

        Returns:
            :class:`~specify_cli.saas_client.endpoints.WidenResponse` with
            ``decision_id``, ``widened_at``, ``slack_thread_url``, and
            ``invited_count``.

        Raises:
            SaasClientError: On any HTTP or network failure.
            SaasAuthError: On auth failure (HTTP 401/403).
            SaasTimeoutError: If the request exceeds the default timeout.
        """
        path = f"/api/v1/decision-points/{decision_id}/widen"
        resp = self._post(path, json={"invited": invited})
        data: dict[str, Any] = resp.json()
        return WidenResponse(
            decision_id=str(data.get("decision_id", decision_id)),
            widened_at=str(data.get("widened_at", "")),
            slack_thread_url=data.get("slack_thread_url") or None,
            invited_count=data.get("invited_count") or None,
        )

    def get_team_integrations(self, team_slug: str) -> list[str]:
        """Fetch the list of active integrations for a team.

        ``GET /api/v1/teams/{slug}/integrations``

        Used by the prereq checker (500ms timeout — it is a fast probe).

        Args:
            team_slug: The team's URL slug.

        Returns:
            List of integration names, e.g. ``["slack", "github"]``.

        Raises:
            SaasClientError: On any HTTP or network failure.
            SaasTimeoutError: If the request exceeds the 500ms probe timeout.
        """
        path = f"/api/v1/teams/{team_slug}/integrations"
        resp = self._get(path, timeout=_TIMEOUT_PREREQ_PROBE)
        data = resp.json()
        if isinstance(data, list):
            return [str(i) for i in data]
        integrations = data.get("integrations", [])
        return [str(i) for i in integrations]

    def health_probe(self) -> bool:
        """Check whether the SaaS API is reachable.

        ``GET /api/v1/health``

        Uses a short 500ms timeout.  Returns ``False`` on any error — this
        method never raises.

        Returns:
            ``True`` if the API responds with HTTP 200, ``False`` otherwise.
        """
        try:
            self._get("/api/v1/health", timeout=_TIMEOUT_PREREQ_PROBE)
            return True
        except SaasClientError:
            return False

    def fetch_discussion(self, decision_id: str) -> DiscussionData:
        """Fetch the discussion thread for a widened decision point.

        ``GET /api/v1/decision-points/{id}/discussion``

        Uses a longer 10-second timeout (per NFR-002) because discussion
        payloads may be large.

        Args:
            decision_id: ULID of the widened decision point.

        Returns:
            :class:`~specify_cli.saas_client.endpoints.DiscussionData`.

        Raises:
            SaasClientError: On any HTTP or network failure.
            SaasNotFoundError: If the decision point does not exist (HTTP 404).
            SaasAuthError: On auth failure (HTTP 401/403).
            SaasTimeoutError: If the request exceeds the 10-second timeout.
        """
        path = f"/api/v1/decision-points/{decision_id}/discussion"
        resp = self._get(path, timeout=_TIMEOUT_DISCUSSION)
        data: dict[str, Any] = resp.json()

        raw_messages = data.get("messages", []) or []
        messages = cast(
            list[DiscussionMessage],
            [
                {
                    "author": str(m.get("author", "")),
                    "text": str(m.get("text", "")),
                    "timestamp": m.get("timestamp") or None,
                }
                for m in raw_messages
                if isinstance(m, dict)
            ],
        )

        raw_participants = data.get("participants", []) or []
        participants = [str(p) for p in raw_participants]

        return DiscussionData(
            decision_id=str(data.get("decision_id", decision_id)),
            participants=participants,
            messages=messages,
            thread_url=data.get("thread_url") or None,
            message_count=int(data.get("message_count", len(messages))),
        )
