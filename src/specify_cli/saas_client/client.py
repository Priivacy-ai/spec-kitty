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

import hashlib
import json as json_module
import logging
import secrets
from kernel.clock import UTC, datetime, now_utc, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlencode, urlsplit, urlunsplit

import httpx

from specify_cli.saas_client.auth import AuthContext, load_auth_context
from specify_cli.egress import project_egress_refusal
from specify_cli.saas_client.endpoints import AdmissionAnswer, AudienceMember, DiscussionData, DiscussionMessage, WidenResponse
from specify_cli.saas_client.errors import (
    SaasAuthError,
    SaasClientError,
    SaasConsentError,
    SaasNotFoundError,
    SaasTimeoutError,
)
from specify_cli.auth import get_token_manager
from specify_cli.auth.session import require_private_team_id
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
    mark_delivery_result_unknown,
    mark_transport_started,
    record_logical_operation_result,
    restart_delivery_attempt,
)
from specify_cli.sync.transport_lease import TransportLeaseContext, acquire_project_transport_lease

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

#: This transport's own identifier-set fragment, rendered into the shared refusal
#: template in ``specify_cli/egress.py``. It is an **argument**, not a second
#: presentation of the policy (FR-008/SC-015) — each transport passes its own
#: because the two sets are asymmetric: this client carries ``decision_id`` and
#: no ``project_slug`` or issue titles, and naming a kind it cannot transmit
#: would overstate the exposure to an operator (US2-AS2).
#:
#: Scope (ruling PB-3): the identifiers **of the project whose consent was
#: refused**. ``team_slug`` is the *destination* and ``invited_user_ids`` are
#: recipient ids; neither belongs here, and appending the destination team's name
#: to make the message "more complete" would add an identifier to an
#: operator-facing message rather than remove one.
SAAS_EGRESS_IDENTIFIER_KINDS = "mission and decision identifiers"

# Timeout constants (seconds)
_TIMEOUT_DEFAULT = 5.0
_TIMEOUT_PREREQ_PROBE = 0.5
_TIMEOUT_DISCUSSION = 10.0


def _normalize_origin(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme.lower() not in {"http", "https"} or parts.hostname is None:
        raise ValueError("SaaS URL must contain an http(s) origin")
    host = parts.hostname.encode("idna").decode("ascii").lower()
    default_port = 443 if parts.scheme.lower() == "https" else 80
    netloc = host if parts.port in {None, default_port} else f"{host}:{parts.port}"
    return urlunsplit((parts.scheme.lower(), netloc, "", "", ""))


def _authenticated_authority_for_token(token: str) -> tuple[str, str, str] | None:
    """Resolve exact account, Private and Collaborative Teamspaces from auth."""
    session = get_token_manager().get_current_session()
    if session is None or not secrets.compare_digest(session.access_token, token):
        return None
    private_teamspace_id = require_private_team_id(session)
    if private_teamspace_id is None:
        return None
    collaborative_ids = {team.id.strip() for team in session.teams if not team.is_private_teamspace and isinstance(team.id, str) and team.id.strip()}
    if len(collaborative_ids) != 1:
        return None
    return session.user_id, private_teamspace_id, collaborative_ids.pop()


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
        base_url: Root URL of the SaaS API (from ``SPEC_KITTY_SAAS_URL`` /
            auth context; D-5 — no hardcoded domain).
        token: Bearer token for authentication.
        timeout: Default request timeout in seconds.  Individual methods may
            override this for their specific use-case.
        _http: Optional pre-constructed ``httpx.Client``.  Pass a mock client
            in tests to intercept HTTP calls without network access.
        project_root: The checkout that **owns the data this client will send**
            (#3030 FR-030) — the repository holding the mission or decision
            record, not the process's current working directory.  Every request
            is refused unless that project has consented to hosted sync.
            ``None`` **denies**: a transport that has not been told whose data it
            carries cannot resolve consent, and inability to determine consent is
            never consent.  The refusing default is deliberate so that a future
            construction site which forgets to pass it fails loudly rather than
            leaking silently.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        team_slug: str | None = None,
        timeout: float = _TIMEOUT_DEFAULT,
        _http: httpx.Client | None = None,
        project_root: Path | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._team_slug = team_slug
        self._timeout = timeout
        self._project_root = Path(project_root) if project_root is not None else None
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
                through to :func:`~specify_cli.saas_client.auth.load_auth_context`
                **and** carried on the client as the project whose consent gates
                every send (#3030 FR-030).  Omitting it yields a client that
                refuses every request, because there is then no project whose
                consent could be resolved.

        Returns:
            A fully initialised :class:`SaasClient`.

        Raises:
            SaasAuthError: If authentication credentials cannot be resolved.
        """
        root: Path | None = Path(str(repo_root)) if repo_root is not None else None
        ctx: AuthContext = load_auth_context(repo_root=root)
        return cls(
            base_url=ctx.saas_url,
            token=ctx.token,
            team_slug=ctx.team_slug,
            project_root=root,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refuse_unless_project_consents(self) -> None:
        """Raise :class:`SaasConsentError` unless the owning project consents.

        Called from both :meth:`_get` and :meth:`_post` — the package's only two
        sinks — **before the URL is even used**, because four of this client's
        five endpoints put ``mission_id`` (documented "ULID or slug", and a slug
        is a client engagement name) in the *request path*. A gate that inspected
        only the JSON body would miss every one of them.
        """
        refusal = project_egress_refusal(self._project_root, SAAS_EGRESS_IDENTIFIER_KINDS)
        if refusal is not None:
            raise SaasConsentError(refusal)

    def _get(
        self,
        path: str,
        *,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Issue a GET request, mapping exceptions to ``SaasClientError``."""
        return self._execute_logical_request("GET", path, timeout=timeout)

    def _post(
        self,
        path: str,
        *,
        json: object,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Issue a POST request with a JSON body, mapping exceptions to ``SaasClientError``."""
        return self._execute_logical_request("POST", path, json=json, timeout=timeout)

    def _execute_logical_request(
        self,
        method: str,
        path: str,
        *,
        json: object | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Run one hosted invocation through durable allocation and WP06 state."""
        self._refuse_unless_project_consents()
        authority = _authenticated_authority_for_token(self._token)
        if authority is None:
            raise SaasConsentError("target_authority_mismatch: token-matched account, Private Teamspace, and one Collaborative Teamspace are required")
        account_identity, private_teamspace_id, collaborative_teamspace_id = authority
        url = f"{self._base_url}{path}"
        effective_timeout = timeout if timeout is not None else self._timeout
        disclosed = json_module.dumps(
            {"method": method, "url": url, "json": json},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        repeatability = LogicalOperationRepeatability.REPEATABLE_READ if method == "GET" else LogicalOperationRepeatability.IDEMPOTENT_WRITE
        payload_hash = hashlib.sha256(disclosed.encode("utf-8")).hexdigest()  # noqa: TID251
        semantic_key = f"{method}:{url}"
        if repeatability is LogicalOperationRepeatability.IDEMPOTENT_WRITE:
            semantic_key = f"{semantic_key}:payload:{payload_hash}"
        request = LogicalOperationRequest(
            write_kind=f"generic_saas_{method.lower()}",
            semantic_key=semantic_key,
            # Native transport body checksum, not charter/doctrine content.
            payload_hash=payload_hash,
            payload_reference=disclosed,
            repeatability=repeatability,
            reconciliation_policy="native_identity_retry",
            deadline_at=(now_utc() + timedelta(seconds=min(max(effective_timeout * 4, 5.0), 300.0))).isoformat(),
            recover_with_persisted_deadline=True,
            collaborative_teamspace_id=collaborative_teamspace_id,
        )
        try:
            store = self._project_transport_store(
                account_identity=account_identity,
                private_teamspace_id=private_teamspace_id,
            )
            decision = allocate_logical_delivery_operation(store, request)
            if decision.disposition is LogicalOperationDisposition.TERMINAL_PRIOR:
                if decision.outcome in {DeliveryOutcome.DELIVERED, DeliveryOutcome.DUPLICATE}:
                    if decision.terminal_response_reference is None:
                        raise SaasClientError("Hosted operation terminal response requires operator recovery")
                    return httpx.Response(
                        200,
                        content=decision.terminal_response_reference.encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                        request=httpx.Request(method, url),
                    )
                if decision.terminal_refusal_category == "project_not_admitted":
                    raise SaasConsentError(self._generic_refusal_message(decision.terminal_refusal_reference))
                raise SaasClientError(f"Hosted operation is terminal: {decision.diagnostic}")
            if not decision.may_resend:
                raise SaasClientError(f"Hosted operation requires recovery: {decision.diagnostic}")
            resp, outcome, category = self._send_generic_operation(
                store,
                decision,
                method=method,
                url=url,
                json=json,
                effective_timeout=effective_timeout,
                repeatability=repeatability,
                authority=authority,
            )
        except SaasClientError:
            raise
        except ProjectStoreError as exc:
            raise SaasClientError(f"Hosted operation requires recovery: {exc}") from exc
        except ValueError as exc:
            raise SaasClientError(f"Hosted operation request is invalid: {exc}") from exc
        if not resp.is_success:
            if category == "project_not_admitted":
                raise SaasConsentError(self._generic_refusal_message(self._generic_refusal_reference(resp)))
            raise _map_http_error(resp, f"{method} {url}")
        return resp

    def _send_generic_operation(
        self,
        store: ProjectSyncStore,
        decision: LogicalOperationDecision,
        *,
        method: str,
        url: str,
        json: object | None,
        effective_timeout: float,
        repeatability: LogicalOperationRepeatability,
        authority: tuple[str, str, str],
    ) -> tuple[httpx.Response, DeliveryOutcome, str | None]:
        """Start, send, and persist one operation under one continuous lease."""
        deadline = self._decision_deadline(decision.deadline_at)
        lease_timeout = min(5.0, max(0.0, self._remaining_seconds(deadline)))
        with acquire_project_transport_lease(store, lock_timeout_seconds=lease_timeout) as lease:
            with lease.unit_of_work() as (unit, context):
                if decision.state is DeliveryAttemptState.RETRYABLE_NO_EFFECT:
                    restart_delivery_attempt(unit, context, decision.attempt_id)
                else:
                    mark_transport_started(unit, context, decision.attempt_id)
            request_timeout = min(effective_timeout, self._remaining_seconds(deadline))
            if request_timeout <= 0:
                with lease.unit_of_work() as (unit, context):
                    record_logical_operation_result(
                        unit,
                        context,
                        result_id=f"{decision.attempt_id}:result",
                        attempt_id=decision.attempt_id,
                        outcome=DeliveryOutcome.RETRYABLE_NO_EFFECT,
                    )
                raise SaasTimeoutError(f"{method} {url} exceeded its persisted deadline before I/O")
            try:
                if _authenticated_authority_for_token(self._token) != authority:
                    raise SaasConsentError("target_authority_mismatch: authenticated authority changed before transport")
                if method == "GET":
                    response = self._http.get(url, timeout=request_timeout)
                else:
                    response = self._http.post(
                        url,
                        json=json,
                        headers={"Idempotency-Key": decision.native_identity or decision.attempt_id},
                        timeout=request_timeout,
                    )
            except httpx.TimeoutException as exc:
                self._record_generic_transport_exception(lease, decision.attempt_id, exc)
                raise SaasTimeoutError(f"{method} {url} timed out after {request_timeout}s") from exc
            except httpx.RequestError as exc:
                self._record_generic_transport_exception(lease, decision.attempt_id, exc)
                raise SaasClientError(f"{method} {url} failed: {exc}") from exc

            outcome, category = self._classify_generic_response(
                response,
                native_identity=decision.native_identity or decision.attempt_id,
                is_write=repeatability is LogicalOperationRepeatability.IDEMPOTENT_WRITE,
            )
            response_reference = self._response_reference(response) if outcome in {DeliveryOutcome.DELIVERED, DeliveryOutcome.DUPLICATE} else None
            refusal_reference = self._generic_refusal_reference(response) if outcome is DeliveryOutcome.REFUSED and category == "project_not_admitted" else None
            with lease.unit_of_work() as (unit, context):
                record_logical_operation_result(
                    unit,
                    context,
                    result_id=f"{decision.attempt_id}:result",
                    attempt_id=decision.attempt_id,
                    outcome=outcome,
                    terminal_refusal_category=category,
                    response_reference=response_reference,
                    refusal_reference=refusal_reference,
                )
        return response, outcome, category

    def _project_transport_store(
        self,
        *,
        account_identity: str,
        private_teamspace_id: str,
    ) -> ProjectSyncStore:
        if self._project_root is None:
            raise SaasConsentError("project_not_admitted: no owning project was supplied")
        identity = resolve_identity(self._project_root)
        if identity.project_uuid is None:
            raise SaasConsentError("project_not_admitted: owning project has no canonical UUID")
        store = ProjectSyncStore(str(identity.project_uuid))
        try:
            context = store.create_context()
        except ProjectStoreError as exc:
            raise SaasConsentError(f"project_not_admitted: project transport store is unavailable ({exc})") from exc
        target = context.target_audience
        if (
            context.consent_generation is None
            or context.epoch_id is None
            or target is None
            or context.admission_generation is None
            or context.binding_audience is None
        ):
            raise SaasConsentError("project_not_admitted: exact hosted target authority is unavailable")
        if (
            target.target_identity != _normalize_origin(self._base_url)
            or target.account_identity != account_identity
            or target.private_teamspace_id != private_teamspace_id
        ):
            raise SaasConsentError("target_authority_mismatch: admitted target does not match the SaaS client")
        return store

    @staticmethod
    def _response_body(response: httpx.Response) -> dict[str, object] | None:
        try:
            body = response.json()
        except Exception:
            return None
        return body if isinstance(body, dict) else None

    @staticmethod
    def _response_reference(response: httpx.Response) -> str:
        return json_module.dumps(
            response.json(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def _generic_refusal_reference(cls, response: httpx.Response) -> str:
        body = cls._response_body(response) or {}
        envelope = {
            key: body[key]
            for key in (
                "error_category",
                "idempotency_key",
                "message",
                "retryable",
                "status",
            )
            if key in body
        }
        return json_module.dumps(
            {"http_status": response.status_code, "envelope": envelope},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    @staticmethod
    def _generic_refusal_message(reference: str | None) -> str:
        if reference is None:
            return "project_not_admitted: hosted target refused this project"
        try:
            value = json_module.loads(reference)
            envelope = value["envelope"]
            message = envelope.get("message")
        except (KeyError, TypeError, json_module.JSONDecodeError):
            return "project_not_admitted: hosted target refused this project"
        return str(message) if isinstance(message, str) and message else "project_not_admitted: hosted target refused this project"

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
        return (deadline - now_utc()).total_seconds()

    @classmethod
    def _classify_generic_response(
        cls,
        response: httpx.Response,
        *,
        native_identity: str,
        is_write: bool,
    ) -> tuple[DeliveryOutcome, str | None]:
        if response.is_success:
            if is_write and cls._is_exact_idempotency_replay(
                response,
                native_identity=native_identity,
            ):
                return DeliveryOutcome.DUPLICATE, None
            return DeliveryOutcome.DELIVERED, None
        body = cls._response_body(response)
        category = body.get("error_category") if body is not None else None
        correlated = body is not None and body.get("idempotency_key") == native_identity
        if (
            body is not None
            and is_write
            and category == "project_not_admitted"
            and correlated
            and body.get("status") == "rejected"
            and body.get("retryable") is False
        ):
            return DeliveryOutcome.REFUSED, "project_not_admitted"
        if response.status_code in {401, 429}:
            return DeliveryOutcome.RETRYABLE_NO_EFFECT, None
        if response.status_code >= 500 and correlated and body is not None and body.get("effect_certainty") == "no_effect":
            return DeliveryOutcome.RETRYABLE_NO_EFFECT, None
        return DeliveryOutcome.UNKNOWN, None

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
    def _record_generic_transport_exception(
        lease: TransportLeaseContext,
        attempt_id: str,
        error: httpx.RequestError,
    ) -> None:
        with lease.unit_of_work() as (unit, context):
            if isinstance(error, (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)):
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
                    reason="request outcome is unknown after transport failure",
                )

    def _resolve_team_slug(self, team_slug: str | None = None) -> str:
        authority = _authenticated_authority_for_token(self._token)
        if authority is None:
            raise SaasAuthError("Exactly one token-matched Collaborative Teamspace is required")
        slug = authority[2]
        if team_slug is not None and team_slug.strip() != slug:
            raise SaasConsentError("target_authority_mismatch: collaborative team path substitution refused")
        if self._team_slug is not None and self._team_slug.strip() != slug:
            raise SaasConsentError("target_authority_mismatch: collaborative team path substitution refused")
        return slug

    def _team_path(self, team_slug: str | None, path: str) -> str:
        self._refuse_unless_project_consents()
        return f"/a/{self._resolve_team_slug(team_slug)}/collaboration{path}"

    # ------------------------------------------------------------------
    # Public endpoint methods
    # ------------------------------------------------------------------

    def get_audience_default(self, mission_id: str, *, team_slug: str | None = None) -> list[AudienceMember]:
        """Fetch the default audience for a mission.

        ``GET /a/{team_slug}/collaboration/missions/{id}/audience-default``

        Returns Teamspace member dicts containing at least ``user_id`` and
        ``display_name``. Legacy bare-string responses are tolerated for older
        test stubs by returning display-name-only member dicts.

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
        path = self._team_path(team_slug, f"/missions/{mission_id}/audience-default")
        resp = self._get(path)
        data = resp.json()
        # Accept either {"members": [...]} or a bare list
        members = data if isinstance(data, list) else data.get("members", [])
        normalized: list[AudienceMember] = []
        for member in members:
            if isinstance(member, dict):
                normalized.append(cast(AudienceMember, dict(member)))
            else:
                normalized.append({"display_name": str(member)})
        return normalized

    def post_widen(
        self,
        decision_id: str,
        invited: list[int],
        *,
        team_slug: str | None = None,
    ) -> WidenResponse:
        """Widen a decision point by inviting external participants.

        ``POST /a/{team_slug}/collaboration/decision-points/{id}/widen``

        Args:
            decision_id: ULID of the decision point to widen.
            invited: List of Teamspace user IDs to invite.

        Returns:
            :class:`~specify_cli.saas_client.endpoints.WidenResponse` with
            ``decision_id``, ``widened_at``, ``slack_thread_url``, and
            ``invited_count``.

        Raises:
            SaasClientError: On any HTTP or network failure.
            SaasAuthError: On auth failure (HTTP 401/403).
            SaasTimeoutError: If the request exceeds the default timeout.
        """
        path = self._team_path(team_slug, f"/decision-points/{decision_id}/widen")
        resp = self._post(path, json={"invited_user_ids": invited})
        data: dict[str, Any] = resp.json()
        return WidenResponse(
            decision_id=str(data.get("decision_id", decision_id)),
            widened_at=str(data.get("widened_at", "")),
            slack_thread_url=data.get("slack_thread_url") or None,
            invited_count=data.get("invited_count") or None,
        )

    def get_team_integrations(self, team_slug: str) -> list[str]:
        """Fetch the list of active integrations for a team.

        ``GET /a/{team_slug}/collaboration/integrations/``

        Used by the prereq checker (500ms timeout — it is a fast probe).

        Args:
            team_slug: The team's URL slug.

        Returns:
            List of integration names, e.g. ``["slack", "github"]``.

        Raises:
            SaasClientError: On any HTTP or network failure.
            SaasTimeoutError: If the request exceeds the 500ms probe timeout.
        """
        path = self._team_path(team_slug, "/integrations/")
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

    def fetch_discussion(self, decision_id: str, *, team_slug: str | None = None) -> DiscussionData:
        """Fetch the discussion thread for a widened decision point.

        ``GET /a/{team_slug}/collaboration/decision-points/{id}/discussion/``

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
        path = self._team_path(team_slug, f"/decision-points/{decision_id}/discussion/")
        resp = self._get(path, timeout=_TIMEOUT_DISCUSSION)
        data: dict[str, Any] = resp.json()

        raw_messages = data.get("messages", []) or []
        messages: list[DiscussionMessage] = [
            {
                "author": str(m.get("author") or m.get("author_display_name") or ""),
                "text": str(m.get("text", "")),
                "timestamp": m.get("timestamp") or m.get("ts") or None,
            }
            for m in raw_messages
            if isinstance(m, dict)
        ]

        raw_participants = data.get("participants", []) or []
        participants = [
            str(p.get("display_name") or p.get("teamspace_user_id") or p.get("slack_user_id")) if isinstance(p, dict) else str(p) for p in raw_participants
        ]

        return DiscussionData(
            decision_id=str(data.get("decision_id", decision_id)),
            participants=participants,
            messages=messages,
            thread_url=data.get("thread_url") or None,
            message_count=int(data.get("message_count", len(messages))),
        )

    def check_repo_admission(self, repo_slug: str, host: str | None = None) -> AdmissionAnswer:
        """Check which team (if any) ``repo_slug`` is admitted into.

        ``GET /api/v1/sync/repo-admission/?repo_slug=<>&host=<>``
        (TEAM-ADMIT-M2-07/08, ADR-TEAM-REPO-ADMISSION-2026-08-24 §4.2/§4.3).

        This is a plain lookup, not team-scoped like the collaboration
        endpoints above: the whole point of the call is to *discover* which
        team (if any) admits the repo, so unlike ``_team_path()`` callers
        there is no team slug to require up front.

        ``host`` is optional but recommended — ``repo_slug`` alone cannot
        distinguish the same ``owner/repo`` slug hosted on two different git
        providers (e.g. github.com vs. a self-hosted GitLab); the server uses
        it to disambiguate by provider when given.

        Args:
            repo_slug: ``owner/repo``-style slug, e.g. from
                :func:`specify_cli.sync.git_metadata.parse_repo_slug`.
            host: Bare git remote hostname, e.g. from
                :func:`specify_cli.sync.git_metadata.parse_remote_host`.

        Returns:
            :class:`~specify_cli.saas_client.endpoints.AdmissionAnswer`.
            Both response shapes are HTTP 200 — check ``admitted`` to tell
            them apart; a not-admitted answer is a normal return value, not
            an exception.

        Raises:
            SaasClientError: On any HTTP or network failure — distinguishable
                from a genuine ``admitted: False`` answer, which is returned
                rather than raised.
            SaasAuthError: On auth failure (HTTP 401/403).
            SaasTimeoutError: If the request exceeds the default timeout.
        """
        params = {"repo_slug": repo_slug}
        if host is not None:
            params["host"] = host
        path = f"/api/v1/sync/repo-admission/?{urlencode(params)}"
        resp = self._get(path)
        data: dict[str, Any] = resp.json()
        return cast(
            AdmissionAnswer,
            {
                "admitted": bool(data.get("admitted", False)),
                "team": data.get("team"),
                "provider": data.get("provider"),
                "repo_slug": str(data.get("repo_slug", repo_slug)),
                "checked_at": data.get("checked_at"),
                "reason": data.get("reason"),
            },
        )
