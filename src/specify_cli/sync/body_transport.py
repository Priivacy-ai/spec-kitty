"""HTTP transport for artifact body push to SaaS push-content endpoint.

Sends individual body upload tasks to POST /api/dossier/push-content/
and classifies responses into UploadOutcome with retryable semantics.

Authentication:
    This module does not manage tokens. Callers (``sync/background.py``)
    are responsible for fetching a fresh OAuth access token from
    ``specify_cli.auth.get_token_manager()`` before invoking ``push_content``.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, cast

import requests

from specify_cli.auth.http import request_with_stdlib_fallback_sync
from specify_cli.saas_client.admission import (
    ProjectWriteAdmissionProof,
    attach_admission_proof,
)
from specify_cli.sync._team import CATEGORY_MISSING_PRIVATE_TEAM
from specify_cli.sync.project_identity import CanonicalProjectUUID
from .namespace import UploadOutcome, UploadStatus

if TYPE_CHECKING:
    from specify_cli.delivery.consent_gate import ProjectTransportDisclosure
    from specify_cli.delivery.interfaces import DeliveryTarget
    from specify_cli.sync.transport_attempts import DeliveryAttemptSpec

    from .body_queue import BodyUploadTask

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 30
SYNC_PROTOCOL_VERSION = "2.0"


def push_content(
    task: BodyUploadTask,
    auth_token: str,
    server_url: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    *,
    admission_proof: ProjectWriteAdmissionProof | None = None,
) -> UploadOutcome:
    """POST artifact body to SaaS push-content endpoint.

    Args:
        task: body upload task from ``OfflineBodyUploadQueue``.
        auth_token: OAuth access token from
            ``specify_cli.auth.get_token_manager().get_access_token()``.
        server_url: Server base URL (e.g., from ``get_saas_base_url()``).
        timeout: Per-request timeout in seconds.

    Returns:
        UploadOutcome classifying the server response.
    """
    if admission_proof is None:
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.FAILED,
            reason="admission_proof_required: body egress requires exact target authority",
            content_hash=task.content_hash,
            retryable=True,
        )
    try:
        request_body = _build_request_bytes(task, admission_proof)
    except (TypeError, ValueError) as exc:
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.FAILED,
            reason=f"project_not_admitted: {exc}",
            content_hash=task.content_hash,
            retryable=False,
        )
    return _send_content_request(
        task,
        auth_token,
        server_url,
        request_body=request_body,
        timeout=timeout,
    )


def _send_content_request(
    task: BodyUploadTask,
    auth_token: str,
    server_url: str,
    *,
    request_body: bytes,
    timeout: float,
) -> UploadOutcome:
    """Send the exact request bytes already bound into the durable attempt."""

    url = f"{server_url.rstrip('/')}/api/dossier/push-content/"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
        "X-Spec-Kitty-Sync-Protocol": SYNC_PROTOCOL_VERSION,
    }

    try:
        response = requests.post(
            url,
            data=request_body,
            headers=headers,
            timeout=timeout,
        )
    except requests.ConnectionError as e:
        fallback = request_with_stdlib_fallback_sync(
            "POST",
            url,
            timeout=timeout,
            content=request_body,
            headers=headers,
        )
        if fallback is not None:
            return _classify_response(task, fallback)
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.FAILED,
            reason=f"connection_error: {e}",
            content_hash=task.content_hash,
            retryable=True,
        )
    except requests.Timeout as e:
        fallback = request_with_stdlib_fallback_sync(
            "POST",
            url,
            timeout=timeout,
            content=request_body,
            headers=headers,
        )
        if fallback is not None:
            return _classify_response(task, fallback)
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.FAILED,
            reason=f"timeout: {e}",
            content_hash=task.content_hash,
            retryable=True,
        )

    return _classify_response(task, response)


def _reject_unmatched_target(
    task: BodyUploadTask,
    target: DeliveryTarget,
    target_id: str,
) -> UploadOutcome | None:
    """Return a FAILED outcome when *target* fails identity/admission checks.

    Isolated out of ``push_content_with_transport_gate`` to keep that shell
    under the complexity ceiling; both refusals share the same
    ``project_not_admitted`` outcome shape.
    """
    if target.target_id != target_id:
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.FAILED,
            reason="project_not_admitted: body target_id does not match the admitted audience tuple",
            content_hash=task.content_hash,
            retryable=False,
        )
    if target.admission_generation is None:
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.FAILED,
            reason="project_not_admitted: target carries no admission generation",
            content_hash=task.content_hash,
            retryable=False,
        )
    return None


def push_content_with_transport_gate(
    task: BodyUploadTask,
    auth_token: str,
    target: DeliveryTarget,
    server_url: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    context: object | None = None,
) -> UploadOutcome:
    """POST one body only after WP06's durable per-project final gate opens."""
    from specify_cli.delivery.consent_gate import (
        ProjectTransportDisclosure,
        ProjectTransportRefusal,
        default_transport_deadline,
        execute_project_transport_batch,
        stable_transport_id,
    )
    from specify_cli.delivery.targets import compute_target_id
    from specify_cli.sync.project_store import ProjectSyncStore
    from specify_cli.sync.transport_attempts import DeliveryAttemptSpec, DeliveryOutcome

    resolved_server_url, server_refusal = _resolve_body_server_url(
        task,
        target,
        server_url,
    )
    if server_refusal is not None:
        return server_refusal
    assert resolved_server_url is not None

    if context is None:
        context = ProjectSyncStore(task.project_uuid).create_context()
    epoch_id = getattr(context, "epoch_id", None)
    consent_generation = getattr(context, "consent_generation", None)
    if not isinstance(epoch_id, int) or not isinstance(consent_generation, int):
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.FAILED,
            reason="project_not_admitted: body upload requires a consenting project context",
            content_hash=task.content_hash,
            retryable=False,
        )
    target_id = compute_target_id(
        target_identity=target.target_identity,
        account_identity=target.account_identity,
        private_teamspace_id=target.private_teamspace_id,
        project_uuid=target.project_uuid,
        configuration_generation=target.configuration_generation,
    )
    rejection = _reject_unmatched_target(task, target, target_id)
    if rejection is not None:
        return rejection
    assert target.admission_generation is not None
    try:
        proof = ProjectWriteAdmissionProof(
            project_uuid=task.project_uuid,
            admission_generation=int(target.admission_generation),
            binding_audience=str(target.binding_audience),
        )
        request_body = _build_request_bytes(task, proof)
    except (TypeError, ValueError) as exc:
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.FAILED,
            reason=f"project_not_admitted: {exc}",
            content_hash=task.content_hash,
            retryable=False,
        )
    native_identity = "body-upload:" + stable_transport_id(
        task.project_uuid,
        target_id,
        task.artifact_path,
        task.content_hash,
    )
    disclosure = ProjectTransportDisclosure(
        project_uuid=task.project_uuid,
        epoch_id=epoch_id,
        consent_generation=consent_generation,
        target_identity=target.target_identity,
        account_identity=target.account_identity,
        private_teamspace_id=target.private_teamspace_id,
        target_project_uuid=target.project_uuid.storage_token,
        target_generation=target.configuration_generation,
        admission_generation=str(target.admission_generation),
        binding_audience=str(target.binding_audience),
        write_kind="body_upload",
        native_identity=native_identity,
        payload_hash="sha256:" + hashlib.sha256(request_body).hexdigest(),  # noqa: TID251 - exact disclosed request digest
        payload_reference=json.dumps(
            {
                "artifact_path": task.artifact_path,
                "content_hash": task.content_hash,
                "admission_generation": proof.admission_generation,
                "binding_audience": proof.binding_audience,
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        attempt_id="body-upload:"
        + stable_transport_id(
            "attempt",
            task.project_uuid,
            target_id,
            task.artifact_path,
            task.content_hash,
        ),
        deadline_at=default_transport_deadline(),
        reconciliation_policy="native_identity_retry",
    )
    attempt_spec = DeliveryAttemptSpec(
        attempt_id=disclosure.attempt_id,
        write_kind=disclosure.write_kind,
        native_identity=disclosure.native_identity,
        payload_hash=disclosure.payload_hash,
        payload_reference=disclosure.payload_reference,
        deadline_at=disclosure.deadline_at,
        reconciliation_policy=disclosure.reconciliation_policy,
    )

    prior_outcome, restart_attempt_ids = _project_body_replay(
        task,
        disclosure,
        attempt_spec,
    )
    if prior_outcome is not None:
        return prior_outcome

    def _classify(value: object) -> tuple[str, str | None]:
        if not isinstance(value, UploadOutcome):
            return DeliveryOutcome.UNKNOWN.value, None
        if value.status is UploadStatus.UPLOADED:
            return DeliveryOutcome.DELIVERED.value, None
        if value.status is UploadStatus.ALREADY_EXISTS:
            return DeliveryOutcome.DUPLICATE.value, None
        if value.status is UploadStatus.FAILED and not value.retryable:
            return DeliveryOutcome.REFUSED.value, value.reason or "body_upload_refused"
        if value.status is UploadStatus.FAILED and value.reason in {
            "index_entry_not_found",
            "rate_limited",
            "unauthorized",
        }:
            return DeliveryOutcome.RETRYABLE_NO_EFFECT.value, None
        return DeliveryOutcome.UNKNOWN.value, None

    gated = execute_project_transport_batch(
        [disclosure],
        send=lambda: _send_content_request(
            task,
            auth_token,
            resolved_server_url,
            request_body=request_body,
            timeout=timeout,
        ),
        classify=lambda value: {disclosure.attempt_id: _classify(value)},
        restart_attempt_ids=restart_attempt_ids,
    )
    if isinstance(gated, ProjectTransportRefusal):
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.FAILED,
            reason=f"{gated.category}: {gated.diagnostic}",
            content_hash=task.content_hash,
            retryable=False,
        )
    if not isinstance(gated, UploadOutcome):
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.FAILED,
            reason="body upload returned an uncorrelated result",
            content_hash=task.content_hash,
            retryable=True,
        )
    return gated


def _resolve_body_server_url(
    task: BodyUploadTask,
    target: DeliveryTarget,
    server_url: str,
) -> tuple[str | None, UploadOutcome | None]:
    from specify_cli.delivery.targets import canonicalize_url

    try:
        resolved = canonicalize_url(server_url)
        admitted = canonicalize_url(target.target_identity)
    except ValueError as exc:
        return None, _failed_body_outcome(
            task,
            reason=f"project_not_admitted: invalid body server URL: {exc}",
            retryable=False,
        )
    if resolved != admitted:
        return None, _failed_body_outcome(
            task,
            reason="project_not_admitted: body server URL does not match the admitted target",
            retryable=False,
        )
    return resolved, None


def _project_body_replay(
    task: BodyUploadTask,
    disclosure: ProjectTransportDisclosure,
    attempt_spec: DeliveryAttemptSpec,
) -> tuple[UploadOutcome | None, frozenset[str]]:
    from specify_cli.sync.project_store import ProjectSyncStore
    from specify_cli.sync.transport_attempts import (
        DeliveryAttemptState,
        DeliveryOutcome,
        DeliveryTerminalResultStatus,
        get_delivery_terminal_result_projection,
    )
    from specify_cli.sync.transport_lease import acquire_project_transport_lease

    try:
        store = ProjectSyncStore(task.project_uuid)
        with (
            acquire_project_transport_lease(store) as lease,
            lease.unit_of_work() as (unit, current_context),
        ):
            current_target = current_context.target_audience
            expected_authority = (
                disclosure.project_uuid,
                disclosure.epoch_id,
                disclosure.consent_generation,
                disclosure.target_identity,
                disclosure.account_identity,
                disclosure.private_teamspace_id,
                disclosure.target_project_uuid,
                disclosure.target_generation,
                disclosure.admission_generation,
                disclosure.binding_audience,
            )
            actual_authority = (
                current_context.project_uuid.storage_token,
                current_context.epoch_id,
                current_context.consent_generation,
                current_target.target_identity if current_target is not None else None,
                current_target.account_identity if current_target is not None else None,
                current_target.private_teamspace_id if current_target is not None else None,
                CanonicalProjectUUID.parse(current_target.project_uuid).storage_token if current_target is not None else None,
                current_target.configuration_generation if current_target is not None else None,
                str(current_context.admission_generation),
                current_context.binding_audience,
            )
            if actual_authority != expected_authority:
                return (
                    _failed_body_outcome(
                        task,
                        reason="project_not_admitted: body transport authority changed before replay projection",
                        retryable=False,
                    ),
                    frozenset(),
                )
            projection = get_delivery_terminal_result_projection(
                unit,
                current_context,
                attempt_spec,
            )
    except (TypeError, ValueError, RuntimeError) as exc:
        return (
            _failed_body_outcome(
                task,
                reason=f"delivery_attempt_recovery_required: {exc}",
                retryable=False,
            ),
            frozenset(),
        )

    if projection.status is DeliveryTerminalResultStatus.TERMINAL:
        if projection.outcome is DeliveryOutcome.DELIVERED:
            return (
                UploadOutcome(
                    artifact_path=task.artifact_path,
                    status=UploadStatus.UPLOADED,
                    reason="stored",
                    content_hash=task.content_hash,
                ),
                frozenset(),
            )
        if projection.outcome is DeliveryOutcome.DUPLICATE:
            return (
                UploadOutcome(
                    artifact_path=task.artifact_path,
                    status=UploadStatus.ALREADY_EXISTS,
                    reason="already_exists",
                    content_hash=task.content_hash,
                ),
                frozenset(),
            )
        if projection.outcome is DeliveryOutcome.REFUSED:
            return (
                _failed_body_outcome(
                    task,
                    reason=projection.terminal_refusal_category or "body_upload_refused",
                    retryable=False,
                ),
                frozenset(),
            )
        return (
            _failed_body_outcome(
                task,
                reason="delivery_attempt_recovery_required: body terminal history is not replayable",
                retryable=False,
            ),
            frozenset(),
        )
    if projection.status is DeliveryTerminalResultStatus.NONTERMINAL and projection.state is DeliveryAttemptState.RETRYABLE_NO_EFFECT:
        return None, frozenset({disclosure.attempt_id})
    return None, frozenset()


def _failed_body_outcome(
    task: BodyUploadTask,
    *,
    reason: str,
    retryable: bool,
) -> UploadOutcome:
    return UploadOutcome(
        artifact_path=task.artifact_path,
        status=UploadStatus.FAILED,
        reason=reason,
        content_hash=task.content_hash,
        retryable=retryable,
    )


def _build_request_body(
    task: BodyUploadTask,
    admission_proof: ProjectWriteAdmissionProof,
) -> dict[str, Any]:
    """Build JSON request body from task.

    Includes 5 namespace fields (FR-002) + 4 artifact fields (FR-003).
    """
    if task.project_uuid.strip().lower() != admission_proof.project_uuid:
        raise ValueError("body task and admission proof belong to different projects")
    payload: dict[str, object] = {
        "mission_slug": task.mission_slug,
        "target_branch": task.target_branch,
        "mission_type": task.mission_type,
        "manifest_version": task.manifest_version,
        "artifact_path": task.artifact_path,
        "content_hash": task.content_hash,
        "hash_algorithm": task.hash_algorithm,
        "content_body": task.content_body,
    }
    return dict(attach_admission_proof(payload, admission_proof))


def _build_request_bytes(
    task: BodyUploadTask,
    admission_proof: ProjectWriteAdmissionProof,
) -> bytes:
    """Serialize the exact validated pinned-contract body sent on the wire."""
    from specify_cli.core.contract_gate import validate_outbound_payload

    payload = _build_request_body(task, admission_proof)
    validate_outbound_payload(payload, "body_sync")
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _safe_json(response: Any) -> dict[str, Any]:
    """Parse response JSON safely, returning empty dict on failure."""
    try:
        payload = response.json()
    except ValueError:
        return {}
    if not isinstance(payload, Mapping):
        return {}
    return {str(key): value for key, value in cast(Mapping[object, Any], payload).items()}


def _format_bad_request_reason(body: dict[str, Any]) -> str:
    """Render DRF-style 400 payloads into a useful reason string."""
    detail = body.get("detail")
    if isinstance(detail, str) and detail.strip():
        return detail

    field_errors: list[str] = []
    for field, value in body.items():
        if field == "detail":
            continue
        if isinstance(value, list) and value:
            joined = "; ".join(str(item) for item in value if str(item).strip())
            if joined:
                field_errors.append(f"{field}: {joined}")
        elif isinstance(value, str) and value.strip():
            field_errors.append(f"{field}: {value}")

    if field_errors:
        return " | ".join(field_errors)

    return "unknown"


def _body_mentions_missing_private_team(body: dict[str, Any]) -> bool:
    values = [
        body.get("category"),
        body.get("error_code"),
        body.get("error"),
        body.get("message"),
        body.get("detail"),
    ]
    text = " ".join(str(value) for value in values if value is not None).lower()
    return CATEGORY_MISSING_PRIVATE_TEAM in text or "private teamspace" in text or ("private team" in text and "direct ingress" in text)


def _response_correlates(task: BodyUploadTask, body: dict[str, Any]) -> bool:
    artifact_path = body.get("artifact_path")
    content_hash = body.get("content_hash")
    return isinstance(artifact_path, str) and artifact_path == task.artifact_path and isinstance(content_hash, str) and content_hash == task.content_hash


def _uncorrelated_response(task: BodyUploadTask) -> UploadOutcome:
    return UploadOutcome(
        artifact_path=task.artifact_path,
        status=UploadStatus.FAILED,
        reason="uncorrelated_response: artifact_path/content_hash did not match",
        content_hash=task.content_hash,
        retryable=True,
    )


def _classify_response(
    task: BodyUploadTask,
    response: Any,
) -> UploadOutcome:
    """Map HTTP response to UploadOutcome with retryable semantics."""
    status = response.status_code

    if status == 201:
        body = _safe_json(response)
        if not _response_correlates(task, body) or body.get("status") != "stored":
            return _uncorrelated_response(task)
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.UPLOADED,
            reason="stored",
            content_hash=task.content_hash,
        )

    if status == 200:
        body = _safe_json(response)
        if not _response_correlates(task, body) or body.get("status") != "already_exists":
            return _uncorrelated_response(task)
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.ALREADY_EXISTS,
            reason="already_exists",
            content_hash=task.content_hash,
        )

    if status == 202:
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.FAILED,
            reason="accepted_pending",
            content_hash=task.content_hash,
            retryable=True,
        )

    if status == 400:
        body = _safe_json(response)
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.FAILED,
            reason=f"bad_request: {_format_bad_request_reason(body)}",
            content_hash=task.content_hash,
            retryable=False,
        )

    if status == 401:
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.FAILED,
            reason="unauthorized",
            content_hash=task.content_hash,
            retryable=True,
        )

    if status == 403:
        body = _safe_json(response)
        if not _response_correlates(task, body):
            return _uncorrelated_response(task)
        error_category = _canonical_error_category(body)
        if error_category == "project_not_admitted":
            return UploadOutcome(
                artifact_path=task.artifact_path,
                status=UploadStatus.FAILED,
                reason="project_not_admitted",
                content_hash=task.content_hash,
                retryable=False,
            )
        reason = error_category or (CATEGORY_MISSING_PRIVATE_TEAM if _body_mentions_missing_private_team(body) else "unauthorized")
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.FAILED,
            reason=reason,
            content_hash=task.content_hash,
            retryable=False,
        )

    if status == 404:
        return _dispatch_404(task, response)

    if status == 429:
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.FAILED,
            reason="rate_limited",
            content_hash=task.content_hash,
            retryable=True,
        )

    if 500 <= status < 600:
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.FAILED,
            reason=f"server_error: {status}",
            content_hash=task.content_hash,
            retryable=True,
        )

    return UploadOutcome(
        artifact_path=task.artifact_path,
        status=UploadStatus.FAILED,
        reason=f"unexpected_status: {status}",
        content_hash=task.content_hash,
        retryable=False,
    )


def _canonical_error_category(body: Mapping[str, Any]) -> str | None:
    """Read the canonical SaaS per-item refusal aliases without guessing."""
    for field in ("error_category", "category", "code"):
        raw = body.get(field)
        if isinstance(raw, str) and raw.strip():
            return raw.strip().lower()
    return None


def _dispatch_404(
    task: BodyUploadTask,
    response: requests.Response,
) -> UploadOutcome:
    """Dispatch 404 based on error field in response body.

    Per contract: index_entry_not_found is retryable (FR-008),
    namespace_not_found is non-retryable, bare/unknown 404 is
    retryable (conservative default per contract).
    """
    body = _safe_json(response)
    error_code = body.get("error", "")

    if error_code == "index_entry_not_found":
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.FAILED,
            reason="index_entry_not_found",
            content_hash=task.content_hash,
            retryable=True,
        )

    if error_code == "namespace_not_found":
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.FAILED,
            reason="namespace_not_found",
            content_hash=task.content_hash,
            retryable=False,
        )

    # Unknown or missing error field — retryable per contract
    detail = body.get("detail", "unknown")
    return UploadOutcome(
        artifact_path=task.artifact_path,
        status=UploadStatus.FAILED,
        reason=f"not_found: {detail} (error={error_code or 'missing'})",
        content_hash=task.content_hash,
        retryable=True,
    )
