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
import hashlib
import json as json_module
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit, urlunsplit

import httpx

from specify_cli.auth import get_token_manager
from specify_cli.auth.errors import (
    AuthenticationError,
    NotAuthenticatedError,
)
from specify_cli.auth.session import require_private_team_id
from specify_cli.sync.config import SyncConfig
from specify_cli.core.contract_gate import validate_outbound_payload
from specify_cli.identity.project import resolve_identity
from specify_cli.sync.project_store import ProjectStoreError, ProjectSyncStore
from specify_cli.sync.transport_attempts import (
    DeliveryAttemptState,
    DeliveryOutcome,
    LogicalOperationDecision,
    LogicalOperationDisposition,
    LogicalOperationRepeatability,
    LogicalOperationRequest,
    allocate_logical_delivery_operation,
    attach_remote_operation_id,
    execute_remote_operation_query_under_lease,
    mark_delivery_result_unknown,
    mark_transport_started,
    record_logical_operation_result,
    restart_delivery_attempt,
)
from specify_cli.sync.transport_lease import TransportLeaseContext, acquire_project_transport_lease
from specify_cli.tracker.egress_verdict import (
    EgressDestination,
    TrackerEgressVerdict,
    tracker_egress_verdict,
)

_SESSION_EXPIRED_MESSAGE = "Session expired. Run `spec-kitty auth login` to re-authenticate."
_UNAUTHENTICATED_CATEGORY = "unauthenticated"


def _normalize_origin(url: str) -> str:
    """Return the exact HTTP authority used for target-admission binding."""

    parts = urlsplit(url.strip())
    if parts.scheme.lower() not in {"http", "https"} or parts.hostname is None:
        raise ValueError("SaaS URL must contain an http(s) origin")
    host = parts.hostname.encode("idna").decode("ascii").lower()
    default_port = 443 if parts.scheme.lower() == "https" else 80
    netloc = host if parts.port in {None, default_port} else f"{host}:{parts.port}"
    return urlunsplit((parts.scheme.lower(), netloc, "", "", ""))


#: This transport's own identifier-set fragment, rendered into the shared refusal
#: template in ``specify_cli/egress.py``. It is an **argument**, not a second
#: presentation of the policy (FR-008/SC-015) — each transport passes its own
#: because the two sets are asymmetric: this client carries ``mission_slug`` and
#: verbatim issue titles (both engagement names) and **no** ``decision_id``, so
#: naming a decision id here would tell an operator that something was at stake
#: which this transport cannot transmit (US2-AS2).
#:
#: Scope (ruling PB-3): the identifiers **of the project whose consent was
#: refused** — not the destination team, and not recipient ids.
TRACKER_EGRESS_IDENTIFIER_KINDS = "mission and engagement identifiers"


@dataclass(frozen=True, slots=True)
class _HostedTrackerAuthority:
    account_identity: str
    private_teamspace_id: str
    collaborative_team_slug: str


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


class TrackerEgressRefusedError(SaaSTrackerClientError):
    """Raised when the project owning the data has not consented to hosted sync.

    A subclass of :class:`SaaSTrackerClientError` deliberately: every existing
    caller already handles that type (``tracker/origin.py`` converts it to
    ``OriginBindingError``; ``saas_service.py`` to ``TrackerServiceError``), so a
    refusal degrades along the paths the codebase already has instead of arriving
    as an unhandled exception. ``error_code="project_consent_denied"`` makes it
    distinguishable from a transport or authorization failure — an operator told
    "HTTP 403" would go and check their token, which is not the problem.

    It is an **error**, not a silent no-op: these are interactive commands, and
    someone running ``sync push`` deserves to be told the push refused and why.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(
            f"Refusing to send tracker data to Spec Kitty SaaS: {reason}",
            error_code="project_consent_denied",
            status_code=None,
            details={"category": "project_consent_denied", "reason": reason},
            user_action_required=True,
        )


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


def _hosted_authority_for_token(token: str) -> _HostedTrackerAuthority | None:
    """Derive exact hosted authority solely from the token-matched session."""
    session = get_token_manager().get_current_session()
    if session is None or not secrets.compare_digest(session.access_token, token):
        return None
    private_teamspace_id = require_private_team_id(session)
    if private_teamspace_id is None:
        return None
    collaborative_ids = {team.id.strip() for team in session.teams if not team.is_private_teamspace and isinstance(team.id, str) and team.id.strip()}
    if len(collaborative_ids) != 1:
        return None
    return _HostedTrackerAuthority(
        account_identity=session.user_id,
        private_teamspace_id=private_teamspace_id,
        collaborative_team_slug=collaborative_ids.pop(),
    )


# ---------------------------------------------------------------------------
# Error-envelope helpers
# ---------------------------------------------------------------------------


def _parse_error_envelope(response: httpx.Response) -> dict[str, Any]:
    """Extract PRI-12 error envelope fields from a non-2xx response.

    Returns a dict with keys: error_code, error_category, message, retryable,
    user_action_required, source, retry_after_seconds.
    Missing keys default to ``None`` (or ``False`` for booleans).
    """
    try:
        body: dict[str, Any] = response.json()
    except Exception:
        return {
            "error_code": None,
            "error_category": None,
            "message": f"HTTP {response.status_code}",
            "retryable": False,
            "user_action_required": None,
            "source": None,
            "retry_after_seconds": None,
        }

    return {
        "error_code": body.get("error_code"),
        "error_category": body.get("error_category"),
        "message": body.get("message", f"HTTP {response.status_code}"),
        "retryable": body.get("retryable", False),
        "user_action_required": body.get("user_action_required"),
        "source": body.get("source"),
        "retry_after_seconds": body.get("retry_after_seconds"),
        "idempotency_key": body.get("idempotency_key"),
        "operation_id": body.get("operation_id"),
        "status": body.get("status"),
        "effect_certainty": body.get("effect_certainty"),
    }


def _unauthenticated_error(message: str) -> SaaSTrackerClientError:
    return SaaSTrackerClientError(
        message,
        error_code=_UNAUTHENTICATED_CATEGORY,
        status_code=401,
        details={"category": _UNAUTHENTICATED_CATEGORY},
        user_action_required=True,
    )


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class SaaSTrackerClient:
    """Low-level synchronous HTTP transport for the SaaS tracker API.

    Parameters
    ----------
    sync_config:
        Provides the resolved runtime target URL (``SPEC_KITTY_SAAS_URL``
        precedence folded in via ``resolve_runtime_target()``).  Falls back
        to a default ``SyncConfig()`` when *None*.  The URL is resolved at
        construction time and cached for the object lifetime.
    project_root:
        The checkout that **owns the data this client will send** — the mission's
        own repository, not the process's current working directory (#3030
        FR-029).  Every request is refused unless that project has consented to
        hosted sync.  Defaults to ``None``, which **denies**: a transport
        constructed without being told whose data it carries cannot resolve
        consent, and inability to determine consent is never consent (FR-003 /
        NFR-001).  The default is deliberately the refusing one so that a future
        construction site that forgets to pass it fails loudly rather than
        leaking silently.
    timeout:
        Per-request HTTP timeout in seconds (default 30).

    Notes
    -----
    Tokens and team slug are sourced from the process-wide TokenManager
    (see module docstring). Callers no longer pass a credential store.
    Authentication and team scope are **not** consent: the 2026-07-27 incident
    was carried by a correctly authenticated client with a correct team header.
    """

    def __init__(
        self,
        sync_config: SyncConfig | None = None,
        *,
        project_root: Path | None = None,
        timeout: float = 30.0,
        monotonic_clock: Callable[[], float] | None = None,
        jitter_randbelow: Callable[[int], int] | None = None,
    ) -> None:
        self._sync_config = sync_config or SyncConfig()
        self._project_root = Path(project_root) if project_root is not None else None
        # Canonical runtime target authority (#2146): resolve the URL we will
        # actually hit — folding in SPEC_KITTY_SAAS_URL precedence — instead of
        # the raw config.toml accessor, which returns the hardcoded default and
        # would silently ignore an env override.
        self._base_url = _normalize_origin(self._sync_config.resolve_runtime_target().resolved_server_url)
        self._timeout = timeout
        # Instance-scoped seam (#3187): retry/poll delays call ``self._sleep``
        # rather than the bare ``time.sleep``. ``time.sleep`` is a single
        # process-wide stdlib attribute, so a test that patches it (even via
        # ``specify_cli.tracker.saas_client.time.sleep``) records a call from
        # ANY code in the process during the patch window -- another thread's
        # leaked retry loop, or CPython's own ``subprocess.Popen._wait`` busy
        # loop, not just this client's own retry logic. Binding the callable
        # once per instance means only this object's own two call sites can
        # ever write to it, so a test can patch ``client._sleep`` and see
        # exactly its own calls, nothing else running in the process.
        self._sleep: Callable[[float], None] = time.sleep
        self._monotonic: Callable[[], float] = monotonic_clock or time.monotonic
        self._randbelow: Callable[[int], int] = jitter_randbelow or secrets.randbelow

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
        expected_team_slug: str | None = None,
        expected_account_identity: str | None = None,
        expected_private_teamspace_id: str | None = None,
        timeout_seconds: float | None = None,
    ) -> httpx.Response:
        """Issue a single HTTP request with auth + team-slug headers.

        Tokens and team slug come from the process-wide ``TokenManager``
        via the sync bridge helpers at the top of this module. No direct
        filesystem or credential-store access.

        **The per-project consent gate lives here** (#3030 FR-029), at the one
        chokepoint all ten endpoints and the operation poller pass through, so a
        new endpoint method cannot be added without inheriting it. It runs
        *before* the token is fetched: a refusal must not depend on auth state,
        must not mint a token for a project that may not transmit, and must be
        reported as a consent decision rather than as an authentication failure.

        Transport-migration note (an *unrelated* mission's FR-030 — not #3030's,
        which is the ``saas_client/`` package's gate; the two are adjacent here by
        accident of numbering): this module remains on the legacy
        ``httpx.Client(...)`` instantiation pattern because 130+
        downstream tests (under ``tests/sync/tracker/``) patch
        ``specify_cli.tracker.saas_client.httpx.Client`` directly. The
        architectural test in
        ``tests/architectural/test_auth_transport_singleton.py``
        explicitly allowlists this file with a tracked follow-up — the
        centralized :class:`AuthenticatedClient` exists and is the
        target for the next migration wave (sync, websocket, and
        widen-mode SaaS).
        """
        verdict = self._current_tracker_egress_verdict()
        if verdict.refused:
            raise TrackerEgressRefusedError(verdict.message)

        access_token = _fetch_access_token_sync()
        if access_token is None:
            raise _unauthenticated_error("No valid access token. Run `spec-kitty auth login` to authenticate.")

        authenticated_authority = _hosted_authority_for_token(access_token)
        if authenticated_authority is None:
            raise _unauthenticated_error(
                "Token-matched account, Private Teamspace, and exactly one Collaborative Teamspace are required. Run `spec-kitty auth login` to authenticate."
            )
        if expected_team_slug is not None and authenticated_authority.collaborative_team_slug != expected_team_slug:
            raise SaaSTrackerClientError(
                "Authenticated team changed after durable operation allocation.",
                error_code="target_authority_mismatch",
                details={
                    "error_category": "target_authority_mismatch",
                    "effect_certainty": "no_effect",
                },
                user_action_required=True,
            )
        if (
            expected_account_identity is not None
            and expected_private_teamspace_id is not None
            and (
                authenticated_authority.account_identity != expected_account_identity
                or authenticated_authority.private_teamspace_id != expected_private_teamspace_id
            )
        ):
            raise SaaSTrackerClientError(
                "Authenticated account or Private Teamspace changed after durable allocation.",
                error_code="target_authority_mismatch",
                details={
                    "error_category": "target_authority_mismatch",
                    "effect_certainty": "no_effect",
                },
                user_action_required=True,
            )

        merged_headers: dict[str, str] = {
            "Authorization": f"Bearer {access_token}",
            "X-Team-Slug": authenticated_authority.collaborative_team_slug,
        }
        if headers:
            merged_headers.update(headers)

        url = f"{self._base_url}{path}"

        try:
            with httpx.Client(timeout=timeout_seconds or self._timeout) as client:
                return client.request(
                    method,
                    url,
                    json=json,
                    headers=merged_headers,
                    params=params,
                )
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout) as exc:
            raise SaaSTrackerClientError(
                f"Cannot connect to Spec Kitty SaaS at {url}. Check your network connection.",
                details={"effect_certainty": "no_effect"},
            ) from exc
        except httpx.TimeoutException as exc:
            raise SaaSTrackerClientError(
                f"Cannot connect to Spec Kitty SaaS at {url}. Check your network connection.",
                details={"effect_certainty": "unknown"},
            ) from exc

    def _physical_request_with_retry(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        authority: _HostedTrackerAuthority,
        deadline: datetime,
        monotonic_deadline: float,
        allow_error_response: bool = False,
    ) -> httpx.Response:
        """Issue a request with 401-refresh and 429-rate-limit retry logic."""
        request_timeout = min(
            self._timeout,
            self._remaining_transport_seconds(deadline, monotonic_deadline),
        )
        if request_timeout <= 0:
            raise SaaSTrackerClientError(
                "Hosted tracker operation exceeded its persisted deadline before I/O.",
                error_code="deadline_exceeded",
                details={"effect_certainty": "no_effect"},
                user_action_required=True,
            )
        response = self._request(
            method,
            path,
            json=json,
            headers=headers,
            params=params,
            expected_team_slug=authority.collaborative_team_slug,
            expected_account_identity=authority.account_identity,
            expected_private_teamspace_id=authority.private_teamspace_id,
            timeout_seconds=request_timeout,
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
                    details={"effect_certainty": "no_effect"},
                    user_action_required=True,
                ) from exc
            except Exception as exc:
                raise SaaSTrackerClientError(
                    _SESSION_EXPIRED_MESSAGE,
                    error_code="session_expired",
                    status_code=401,
                    details={"effect_certainty": "no_effect"},
                    user_action_required=True,
                ) from exc

            remaining_after_refresh = self._remaining_transport_seconds(
                deadline,
                monotonic_deadline,
            )
            if remaining_after_refresh <= 0:
                raise SaaSTrackerClientError(
                    "Authentication retry exceeded the persisted operation deadline.",
                    error_code="deadline_exceeded",
                    status_code=401,
                    details={"effect_certainty": "no_effect"},
                    user_action_required=True,
                )
            response = self._request(
                method,
                path,
                json=json,
                headers=headers,
                params=params,
                expected_team_slug=authority.collaborative_team_slug,
                expected_account_identity=authority.account_identity,
                expected_private_teamspace_id=authority.private_teamspace_id,
                timeout_seconds=min(self._timeout, remaining_after_refresh),
            )
            if response.status_code == 401:
                raise SaaSTrackerClientError(
                    _SESSION_EXPIRED_MESSAGE,
                    error_code="session_expired",
                    status_code=401,
                    details={"effect_certainty": "no_effect"},
                    user_action_required=True,
                )

        # --- 429: respect retry_after_seconds ---
        if response.status_code == 429:
            envelope = _parse_error_envelope(response)
            wait_seconds = envelope.get("retry_after_seconds")
            if wait_seconds is None or not isinstance(wait_seconds, (int, float)):
                wait_seconds = 5
            if float(wait_seconds) >= self._remaining_transport_seconds(
                deadline,
                monotonic_deadline,
            ):
                raise SaaSTrackerClientError(
                    "Rate-limit retry would exceed the persisted operation deadline.",
                    error_code="deadline_exceeded",
                    status_code=429,
                    details={"effect_certainty": "no_effect"},
                    user_action_required=True,
                )
            self._sleep(float(wait_seconds))

            remaining_after_sleep = self._remaining_transport_seconds(
                deadline,
                monotonic_deadline,
            )
            if remaining_after_sleep <= 0:
                raise SaaSTrackerClientError(
                    "Rate-limit backoff exhausted the persisted operation deadline.",
                    error_code="deadline_exceeded",
                    status_code=429,
                    details={"effect_certainty": "no_effect"},
                    user_action_required=True,
                )

            response = self._request(
                method,
                path,
                json=json,
                headers=headers,
                params=params,
                expected_team_slug=authority.collaborative_team_slug,
                expected_account_identity=authority.account_identity,
                expected_private_teamspace_id=authority.private_teamspace_id,
                timeout_seconds=min(self._timeout, remaining_after_sleep),
            )
            if response.status_code == 429:
                envelope = _parse_error_envelope(response)
                raise SaaSTrackerClientError(
                    envelope.get("message") or "Rate limited by SaaS API.",
                    error_code="rate_limited",
                    status_code=429,
                    details={**envelope, "effect_certainty": "no_effect"},
                )

        # --- Other non-2xx ---
        if response.status_code >= 400:
            if allow_error_response:
                return response
            envelope = _parse_error_envelope(response)
            msg = envelope.get("message") or f"HTTP {response.status_code}"
            # user_action_required is a boolean per PRI-12 ErrorEnvelope.
            # When True, suffix the message with generic guidance.
            if envelope.get("user_action_required"):
                msg += " (action required — check the Spec Kitty dashboard)"
            raise SaaSTrackerClientError(
                msg,
                error_code=envelope.get("error_category") or envelope.get("error_code"),
                status_code=response.status_code,
                details=envelope,
                user_action_required=bool(envelope.get("user_action_required")),
            )

        return response

    def _request_with_retry(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        poll_async: bool = True,
    ) -> httpx.Response:
        """Run one logical tracker operation across all physical retries."""
        store, authority = self._project_transport_store()
        is_write = path in {
            self._BIND_ORIGIN_PATH,
            self._BIND_CONFIRM_PATH,
            self._PUSH_PATH,
            self._RUN_PATH,
        }
        disclosed_request = httpx.Request(
            method,
            f"{self._base_url}{path}",
            json=json,
            params=params,
        )
        disclosed = b"\n".join((method.encode("ascii"), str(disclosed_request.url).encode("utf-8"), disclosed_request.content))
        caller_key = (headers or {}).get("Idempotency-Key")
        if caller_key is not None and not caller_key.strip():
            raise SaaSTrackerClientError("Idempotency-Key must be non-empty", error_code="invalid_operation_request")
        payload_hash = hashlib.sha256(disclosed).hexdigest()  # noqa: TID251
        semantic_parts = [method, path, str(disclosed_request.url)]
        if is_write:
            semantic_parts.append(f"caller-key:{caller_key}" if caller_key else f"payload:{payload_hash}")
        request = LogicalOperationRequest(
            write_kind=self._tracker_write_kind(path),
            semantic_key="\x1f".join(semantic_parts),
            # Exact native HTTP request checksum, not charter/doctrine content.
            payload_hash=payload_hash,
            payload_reference=json_module.dumps(
                {
                    "method": method,
                    "url": str(disclosed_request.url),
                    "body": disclosed_request.content.decode("utf-8"),
                },
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
            repeatability=(LogicalOperationRepeatability.IDEMPOTENT_WRITE if is_write else LogicalOperationRepeatability.REPEATABLE_READ),
            reconciliation_policy=("native_identity_retry_then_query" if is_write else "native_identity_retry"),
            deadline_at=(datetime.now(UTC) + timedelta(seconds=min(max(self._timeout * 4, 30.0), 300.0))).isoformat(),
            recover_with_persisted_deadline=True,
            requested_native_identity=caller_key,
            collaborative_teamspace_id=authority.collaborative_team_slug,
        )
        try:
            decision = allocate_logical_delivery_operation(store, request)
            if decision.disposition is LogicalOperationDisposition.TERMINAL_PRIOR:
                return self._terminal_prior_response(decision, method=method, path=path)
            self._require_resend_or_query(decision)
            deadline = self._decision_deadline(decision.deadline_at)
            monotonic_deadline = self._monotonic() + max(
                0.0,
                self._remaining_seconds(deadline),
            )
            with acquire_project_transport_lease(
                store,
                lock_timeout_seconds=min(5.0, max(0.0, self._remaining_seconds(deadline))),
            ) as lease:
                if decision.may_query and decision.remote_operation_id:
                    return self._poll_operation_under_lease(
                        lease,
                        decision,
                        authority,
                        method=method,
                        path=path,
                        monotonic_deadline=monotonic_deadline,
                    )
                with lease.unit_of_work() as (unit, context):
                    if decision.state is DeliveryAttemptState.RETRYABLE_NO_EFFECT:
                        restart_delivery_attempt(unit, context, decision.attempt_id)
                    else:
                        mark_transport_started(unit, context, decision.attempt_id)

                physical_headers = dict(headers or {})
                if is_write:
                    physical_headers.setdefault(
                        "Idempotency-Key",
                        decision.native_identity or decision.attempt_id,
                    )
                try:
                    response = self._physical_request_with_retry(
                        method,
                        path,
                        json=json,
                        headers=physical_headers or None,
                        params=params,
                        authority=authority,
                        deadline=deadline,
                        monotonic_deadline=monotonic_deadline,
                    )
                except SaaSTrackerClientError as exc:
                    self._park_tracker_failure_under_lease(
                        lease,
                        decision.attempt_id,
                        exc,
                        native_identity=decision.native_identity or decision.attempt_id,
                    )
                    raise

                if response.status_code == 202 and is_write:
                    try:
                        operation_id = self._required_operation_id(response)
                    except SaaSTrackerClientError:
                        with lease.unit_of_work() as (unit, context):
                            mark_delivery_result_unknown(
                                unit,
                                context,
                                attempt_id=decision.attempt_id,
                                reason="async response omitted durable remote correlation",
                            )
                        raise
                    with lease.unit_of_work() as (unit, context):
                        attach_remote_operation_id(
                            unit,
                            context,
                            attempt_id=decision.attempt_id,
                            remote_operation_id=operation_id,
                        )
                        record_logical_operation_result(
                            unit,
                            context,
                            result_id=f"{decision.attempt_id}:result",
                            attempt_id=decision.attempt_id,
                            outcome=DeliveryOutcome.PENDING,
                        )
                    if not poll_async:
                        return response
                    return self._poll_operation_under_lease(
                        lease,
                        decision,
                        authority,
                        method=method,
                        path=path,
                        remote_operation_id=operation_id,
                        monotonic_deadline=monotonic_deadline,
                    )

                response_reference = self._response_reference(response)
                outcome = (
                    DeliveryOutcome.DUPLICATE
                    if is_write
                    and self._is_exact_idempotency_replay(
                        response,
                        native_identity=decision.native_identity or decision.attempt_id,
                    )
                    else DeliveryOutcome.DELIVERED
                )
                with lease.unit_of_work() as (unit, context):
                    record_logical_operation_result(
                        unit,
                        context,
                        result_id=f"{decision.attempt_id}:result",
                        attempt_id=decision.attempt_id,
                        outcome=outcome,
                        response_reference=response_reference,
                    )
                return response
        except SaaSTrackerClientError:
            raise
        except ProjectStoreError as exc:
            raise SaaSTrackerClientError(
                f"Hosted tracker operation requires recovery: {exc}",
                error_code="recovery_required",
                details={"category": "recovery_required"},
                user_action_required=True,
            ) from exc
        except ValueError as exc:
            raise SaaSTrackerClientError(
                f"Hosted tracker operation request is invalid: {exc}",
                error_code="invalid_operation_request",
            ) from exc

    @staticmethod
    def _require_resend_or_query(decision: LogicalOperationDecision) -> None:
        if decision.may_resend or (decision.may_query and decision.remote_operation_id):
            return
        raise SaaSTrackerClientError(
            f"Hosted tracker operation requires recovery: {decision.diagnostic}",
            error_code="recovery_required",
            details={"attempt_id": decision.attempt_id, "state": str(decision.state)},
            user_action_required=True,
        )

    def _project_transport_store(self) -> tuple[ProjectSyncStore, _HostedTrackerAuthority]:
        verdict = self._current_tracker_egress_verdict()
        if verdict.refused:
            raise TrackerEgressRefusedError(verdict.message)
        if self._project_root is None:
            raise TrackerEgressRefusedError("no owning project was supplied")
        identity = resolve_identity(self._project_root)
        if identity.project_uuid is None:
            raise TrackerEgressRefusedError("owning project has no canonical UUID")
        store = ProjectSyncStore(str(identity.project_uuid))
        try:
            context = store.create_context()
        except ProjectStoreError as exc:
            raise SaaSTrackerClientError(
                f"Project transport store is unavailable: {exc}",
                error_code="project_not_admitted",
                details={"category": "project_not_admitted"},
                user_action_required=True,
            ) from exc
        target = context.target_audience
        access_token = _fetch_access_token_sync()
        if access_token is None:
            raise _unauthenticated_error("No valid access token. Run `spec-kitty auth login` to authenticate.")
        authenticated_authority = _hosted_authority_for_token(access_token)
        if authenticated_authority is None:
            raise _unauthenticated_error(
                "Token-matched account, Private Teamspace, and exactly one Collaborative Teamspace are required. Run `spec-kitty auth login` to authenticate."
            )
        account_identity = authenticated_authority.account_identity
        private_teamspace_id = authenticated_authority.private_teamspace_id
        if (
            context.consent_generation is None
            or context.epoch_id is None
            or target is None
            or context.admission_generation is None
            or context.binding_audience is None
        ):
            raise SaaSTrackerClientError(
                "Exact hosted target authority is unavailable for this project.",
                error_code="project_not_admitted",
                details={"category": "project_not_admitted"},
                user_action_required=True,
            )
        try:
            admitted_origin = _normalize_origin(target.target_identity)
        except ValueError:
            admitted_origin = ""
        if admitted_origin != self._base_url or account_identity != target.account_identity or private_teamspace_id != target.private_teamspace_id:
            raise SaaSTrackerClientError(
                "Current hosted target does not match the admitted project target.",
                error_code="target_authority_mismatch",
                details={"category": "target_authority_mismatch"},
                user_action_required=True,
            )
        return store, authenticated_authority

    def _current_tracker_egress_verdict(self) -> TrackerEgressVerdict:
        """Evaluate Channel 2 without duplicating the policy call-site seam."""

        return tracker_egress_verdict(
            self._project_root,
            destination=EgressDestination.HOSTED_SERVICE,
            identifiers=TRACKER_EGRESS_IDENTIFIER_KINDS,
        )

    def _tracker_write_kind(self, path: str) -> str:
        names = {
            self._STATUS_PATH: "tracker_hosted_status",
            self._MAPPINGS_PATH: "tracker_hosted_mappings",
            self._PULL_PATH: "tracker_hosted_pull",
            self._PUSH_PATH: "tracker_hosted_push",
            self._RUN_PATH: "tracker_hosted_run",
            self._SEARCH_ISSUES_PATH: "tracker_hosted_search",
            self._LIST_TICKETS_PATH: "tracker_hosted_list",
            self._BIND_ORIGIN_PATH: "tracker_hosted_bind_origin",
            self._RESOURCES_PATH: "tracker_hosted_resources",
            self._BIND_RESOLVE_PATH: "tracker_hosted_bind_resolve",
            self._BIND_CONFIRM_PATH: "tracker_hosted_bind_confirm",
            self._BIND_VALIDATE_PATH: "tracker_hosted_bind_validate",
        }
        return names.get(path, "tracker_hosted_operation_query")

    @staticmethod
    def _required_operation_id(response: httpx.Response) -> str:
        try:
            body = response.json()
        except Exception as exc:
            raise SaaSTrackerClientError(
                "Async tracker response did not contain valid JSON.",
                error_code="invalid_async_response",
            ) from exc
        operation_id = body.get("operation_id") if isinstance(body, dict) else None
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise SaaSTrackerClientError(
                "Async tracker response did not contain operation_id.",
                error_code="invalid_async_response",
            )
        return operation_id

    @staticmethod
    def _terminal_prior_response(
        decision: LogicalOperationDecision,
        *,
        method: str,
        path: str,
    ) -> httpx.Response:
        if decision.outcome in {DeliveryOutcome.DELIVERED, DeliveryOutcome.DUPLICATE}:
            if decision.terminal_response_reference is None:
                raise SaaSTrackerClientError(
                    "Hosted tracker terminal response requires operator recovery.",
                    error_code="recovery_required",
                    user_action_required=True,
                )
            return httpx.Response(
                200,
                content=decision.terminal_response_reference.encode("utf-8"),
                headers={"Content-Type": "application/json"},
                request=httpx.Request(method, path),
            )
        category = decision.terminal_refusal_category
        if category == "project_not_admitted" and decision.terminal_refusal_reference:
            raise SaaSTrackerClient._error_from_refusal_reference(decision.terminal_refusal_reference)
        raise SaaSTrackerClientError(
            f"Hosted tracker operation is terminal: {decision.diagnostic}",
            error_code=category or "terminal_operation",
            details={"error_category": category, "attempt_id": decision.attempt_id},
            user_action_required=True,
        )

    @staticmethod
    def _response_reference(response: httpx.Response) -> str:
        return json_module.dumps(
            response.json(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    @staticmethod
    def _is_exact_idempotency_replay(
        response: httpx.Response,
        *,
        native_identity: str,
    ) -> bool:
        """Require replay evidence correlated to the exact native request."""
        headers = getattr(response, "headers", None)
        if not isinstance(headers, (httpx.Headers, dict)):
            return False
        replayed = headers.get("Idempotency-Replayed")
        if not isinstance(replayed, str) or replayed.strip().lower() != "true":
            return False
        try:
            request = response.request
        except (AttributeError, RuntimeError):
            return False
        request_headers = getattr(request, "headers", None)
        return isinstance(request_headers, (httpx.Headers, dict)) and request_headers.get("Idempotency-Key") == native_identity

    @staticmethod
    def _refusal_reference(error: SaaSTrackerClientError) -> str:
        allowed = {
            "effect_certainty",
            "error_category",
            "error_code",
            "idempotency_key",
            "message",
            "operation_id",
            "retryable",
            "retry_after_seconds",
            "source",
            "status",
            "user_action_required",
        }
        details = {key: value for key, value in error.details.items() if key in allowed}
        return json_module.dumps(
            {
                "message": str(error),
                "error_code": error.error_code,
                "status_code": error.status_code,
                "details": details,
                "user_action_required": error.user_action_required,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    @staticmethod
    def _error_from_refusal_reference(reference: str) -> SaaSTrackerClientError:
        try:
            value = json_module.loads(reference)
            if not isinstance(value, dict) or not isinstance(value.get("message"), str):
                raise TypeError
            details = value.get("details")
            if not isinstance(details, dict):
                raise TypeError
            return SaaSTrackerClientError(
                value["message"],
                error_code=value.get("error_code"),
                status_code=value.get("status_code"),
                details=details,
                user_action_required=bool(value.get("user_action_required")),
            )
        except (KeyError, TypeError, json_module.JSONDecodeError) as exc:
            raise SaaSTrackerClientError(
                "Hosted tracker refusal history is corrupt.",
                error_code="recovery_required",
                user_action_required=True,
            ) from exc

    @staticmethod
    def _decision_deadline(value: str | None) -> datetime:
        if value is None:
            raise ValueError("durable operation has no deadline")
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError("durable operation deadline must include a timezone")
        return parsed.astimezone(UTC)

    @staticmethod
    def _remaining_seconds(deadline: datetime) -> float:
        return (deadline - datetime.now(UTC)).total_seconds()

    def _remaining_transport_seconds(
        self,
        deadline: datetime,
        monotonic_deadline: float,
    ) -> float:
        """Return the tighter persisted-wall and injected-monotonic budget."""
        return min(
            self._remaining_seconds(deadline),
            monotonic_deadline - self._monotonic(),
        )

    def _park_tracker_failure_under_lease(
        self,
        lease: TransportLeaseContext,
        attempt_id: str,
        error: SaaSTrackerClientError,
        *,
        native_identity: str,
    ) -> None:
        category = error.details.get("error_category")
        correlated = error.details.get("idempotency_key") == native_identity
        exact_refusal = category == "project_not_admitted" and correlated and error.details.get("status") == "rejected" and error.details.get("retryable") is False
        known_no_effect = error.details.get("effect_certainty") == "no_effect"
        if error.status_code in {401, 429}:
            known_no_effect = True
        if error.status_code is not None and error.status_code >= 500:
            known_no_effect = known_no_effect and correlated
        with lease.unit_of_work() as (unit, context):
            if exact_refusal:
                record_logical_operation_result(
                    unit,
                    context,
                    result_id=f"{attempt_id}:result",
                    attempt_id=attempt_id,
                    outcome=DeliveryOutcome.REFUSED,
                    terminal_refusal_category="project_not_admitted",
                    refusal_reference=self._refusal_reference(error),
                )
            elif known_no_effect:
                record_logical_operation_result(
                    unit,
                    context,
                    result_id=f"{attempt_id}:result",
                    attempt_id=attempt_id,
                    outcome=DeliveryOutcome.RETRYABLE_NO_EFFECT,
                )
            else:
                mark_delivery_result_unknown(
                    unit,
                    context,
                    attempt_id=attempt_id,
                    reason="tracker request ended without a classifiable response",
                )

    # ----- polling -----

    def _poll_operation_under_lease(
        self,
        lease: TransportLeaseContext,
        decision: LogicalOperationDecision,
        authority: _HostedTrackerAuthority,
        *,
        method: str,
        path: str,
        remote_operation_id: str | None = None,
        monotonic_deadline: float,
    ) -> httpx.Response:
        """Poll one durable async operation under the original transport lease."""
        operation_id = remote_operation_id or decision.remote_operation_id
        if operation_id is None:
            raise SaaSTrackerClientError(
                "Async tracker recovery has no durable operation correlation.",
                error_code="recovery_required",
                user_action_required=True,
            )
        deadline = self._decision_deadline(decision.deadline_at)
        delay = 1.0
        while True:

            def _query(remote_id: str) -> httpx.Response:
                return self._physical_request_with_retry(
                    "GET",
                    self._OPERATIONS_PATH.format(operation_id=remote_id),
                    authority=authority,
                    deadline=deadline,
                    monotonic_deadline=monotonic_deadline,
                    allow_error_response=True,
                )

            value = execute_remote_operation_query_under_lease(
                lease,
                attempt_id=decision.attempt_id,
                result_id=f"{decision.attempt_id}:result",
                query=_query,
                classify=lambda response: self._classify_operation_query_response(
                    response,
                    expected_operation_id=operation_id,
                ),
                response_reference=self._operation_terminal_response_reference,
                refusal_reference=lambda response: self._operation_refusal_reference(
                    response,
                    expected_operation_id=operation_id,
                ),
            )
            if not isinstance(value, httpx.Response):
                raise SaaSTrackerClientError("Tracker operation query returned an invalid response")
            outcome, category = self._classify_operation_query_response(
                value,
                expected_operation_id=operation_id,
            )
            if outcome is DeliveryOutcome.DELIVERED:
                reference = self._operation_terminal_response_reference(value)
                assert reference is not None
                return httpx.Response(
                    200,
                    content=reference.encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    request=httpx.Request(method, f"{self._base_url}{path}"),
                )
            if outcome is DeliveryOutcome.REFUSED:
                message, details = self._operation_failure_details(value)
                raise SaaSTrackerClientError(
                    message,
                    error_code=category or "remote_operation_failed",
                    details={**details, "error_category": category, "operation_id": operation_id},
                    user_action_required=True,
                )
            if outcome is DeliveryOutcome.UNKNOWN:
                raise SaaSTrackerClientError(
                    "Hosted tracker query outcome is unknown and requires operator recovery.",
                    error_code="recovery_required",
                    details={"operation_id": operation_id},
                    user_action_required=True,
                )
            remaining = self._remaining_transport_seconds(
                deadline,
                monotonic_deadline,
            )
            jitter_factor = 0.8 + (self._randbelow(4000) / 10000)
            sleep_for = min(delay, 30.0) * jitter_factor
            if sleep_for >= remaining:
                raise SaaSTrackerClientError(
                    "Tracker operation polling exceeded its persisted deadline.",
                    error_code="recovery_required",
                    details={"operation_id": operation_id},
                    user_action_required=True,
                )
            self._sleep(sleep_for)
            delay = min(delay * 2, 30.0)

    @staticmethod
    def _classify_operation_query_response(
        response: object,
        *,
        expected_operation_id: str | None = None,
    ) -> tuple[DeliveryOutcome, str | None]:
        if not isinstance(response, httpx.Response):
            raise SaaSTrackerClientError("Tracker operation query returned an invalid response")
        try:
            body = response.json()
        except Exception:
            return DeliveryOutcome.UNKNOWN, None
        if not isinstance(body, dict):
            return DeliveryOutcome.UNKNOWN, None
        if expected_operation_id is not None and body.get("operation_id") is not None and body.get("operation_id") != expected_operation_id:
            return DeliveryOutcome.UNKNOWN, None
        status = body.get("status")
        if status == "completed":
            return DeliveryOutcome.DELIVERED, None
        if status == "failed":
            error = body.get("error")
            category = error.get("error_category") if isinstance(error, dict) else None
            if (
                category == "project_not_admitted"
                and body.get("operation_id") == expected_operation_id
                and isinstance(error, dict)
                and error.get("retryable") is False
            ):
                return DeliveryOutcome.REFUSED, "project_not_admitted"
            return DeliveryOutcome.REFUSED, "remote_operation_failed"
        if status in {"pending", "running"}:
            return DeliveryOutcome.PENDING, None
        if (
            response.status_code == 400
            and body.get("error_category") == "project_not_admitted"
            and body.get("status") == "rejected"
            and body.get("retryable") is False
            and body.get("operation_id") == expected_operation_id
        ):
            return DeliveryOutcome.REFUSED, "project_not_admitted"
        return DeliveryOutcome.UNKNOWN, None

    @staticmethod
    def _operation_terminal_response_reference(response: object) -> str | None:
        if not isinstance(response, httpx.Response):
            return None
        try:
            body = response.json()
        except Exception:
            return None
        if not isinstance(body, dict) or body.get("status") != "completed":
            return None
        result = body.get("result", body)
        return json_module.dumps(
            result,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def _operation_refusal_reference(
        cls,
        response: object,
        *,
        expected_operation_id: str | None = None,
    ) -> str | None:
        if not isinstance(response, httpx.Response):
            return None
        outcome, category = cls._classify_operation_query_response(
            response,
            expected_operation_id=expected_operation_id,
        )
        if outcome is not DeliveryOutcome.REFUSED or category != "project_not_admitted":
            return None
        message, details = cls._operation_failure_details(response)
        error = SaaSTrackerClientError(
            message,
            error_code="project_not_admitted",
            details={
                **details,
                "error_category": category,
                "operation_id": expected_operation_id,
            },
            user_action_required=True,
        )
        return cls._refusal_reference(error)

    @staticmethod
    def _operation_failure_details(response: httpx.Response) -> tuple[str, dict[str, Any]]:
        try:
            body = response.json()
        except Exception:
            return "Operation failed", {}
        error = body.get("error") if isinstance(body, dict) else None
        if isinstance(error, dict):
            message = str(error.get("message") or "Operation failed")
            if error.get("user_action_required"):
                message += " (action required — check the Spec Kitty dashboard)"
            return message, dict(error)
        if isinstance(error, str) and error:
            return error, {}
        return "Operation failed", {}

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
        params = self._routing_params(provider, project_slug, binding_ref) if binding_ref or project_slug else {"provider": provider}
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
            headers={"Idempotency-Key": idempotency_key} if idempotency_key else None,
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
        payload: dict[str, Any] = {
            "provider": provider,
            "candidate_token": candidate_token,
            "project_identity": project_identity,
        }
        response = self._request_with_retry(
            "POST",
            self._BIND_CONFIRM_PATH,
            json=payload,
            headers={"Idempotency-Key": idempotency_key} if idempotency_key else None,
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
        payload: dict[str, Any] = {
            **self._routing_params(provider, project_slug, binding_ref),
            "items": items or [],
        }
        response = self._request_with_retry(
            "POST",
            self._PUSH_PATH,
            json=payload,
            headers={"Idempotency-Key": idempotency_key} if idempotency_key else None,
        )

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
        payload: dict[str, Any] = {
            **self._routing_params(provider, project_slug, binding_ref),
            "pull_first": pull_first,
            "limit": limit,
        }
        response = self._request_with_retry(
            "POST",
            self._RUN_PATH,
            json=payload,
            headers={"Idempotency-Key": idempotency_key} if idempotency_key else None,
        )

        result: dict[str, Any] = response.json()
        return result
