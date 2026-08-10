"""HTTP transport for artifact body push to SaaS push-content endpoint.

Sends individual body upload tasks to POST /api/dossier/push-content/
and classifies responses into UploadOutcome with retryable semantics.

Authentication:
    This module does not manage tokens. Callers (``sync/background.py``)
    are responsible for fetching a fresh OAuth access token from
    ``specify_cli.auth.get_token_manager()`` before invoking ``push_content``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import requests

from specify_cli.auth.http import request_with_stdlib_fallback_sync
from specify_cli.sync._team import CATEGORY_MISSING_PRIVATE_TEAM
from .namespace import UploadOutcome, UploadStatus

if TYPE_CHECKING:
    from specify_cli.delivery.interfaces import DeliveryTarget

    from .body_queue import BodyUploadTask

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 30


def push_content(
    task: BodyUploadTask,
    auth_token: str,
    server_url: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
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
    from specify_cli.core.contract_gate import validate_outbound_payload

    url = f"{server_url.rstrip('/')}/api/dossier/push-content/"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }
    payload = _build_request_body(task)
    validate_outbound_payload(payload, "body_sync")

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=timeout,
        )
    except requests.ConnectionError as e:
        fallback = request_with_stdlib_fallback_sync(
            "POST",
            url,
            timeout=timeout,
            json=payload,
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
            json=payload,
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


def push_content_with_transport_gate(
    task: BodyUploadTask,
    auth_token: str,
    target: DeliveryTarget,
    server_url: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> UploadOutcome:
    """POST one body only after WP06's durable per-project final gate opens."""
    from specify_cli.delivery.consent_gate import (
        ProjectTransportDisclosure,
        ProjectTransportRefusal,
        default_transport_deadline,
        execute_project_transport_disclosure,
        stable_transport_id,
    )
    from specify_cli.sync.transport_attempts import DeliveryOutcome

    native_identity = "body-upload:" + stable_transport_id(
        task.project_uuid,
        target.target_id,
        task.artifact_path,
        task.content_hash,
    )
    disclosure = ProjectTransportDisclosure(
        project_uuid=task.project_uuid,
        target_identity=target.target_identity,
        account_identity=target.account_identity,
        private_teamspace_id=target.private_teamspace_id,
        target_project_uuid=target.project_uuid.storage_token,
        target_generation=target.configuration_generation,
        admission_generation=str(target.admission_generation),
        binding_audience=str(target.binding_audience),
        write_kind="body_upload",
        native_identity=native_identity,
        payload_hash=f"{task.hash_algorithm}:{task.content_hash}",
        payload_reference=f"body:{task.artifact_path}:{task.content_hash}",
        attempt_id="body-upload:"
        + stable_transport_id(
            "attempt",
            task.project_uuid,
            target.target_id,
            task.artifact_path,
            task.content_hash,
        ),
        deadline_at=default_transport_deadline(),
    )

    def _classify(value: object) -> tuple[str, str | None]:
        if not isinstance(value, UploadOutcome):
            return DeliveryOutcome.UNKNOWN.value, None
        if value.status is UploadStatus.UPLOADED:
            return DeliveryOutcome.DELIVERED.value, None
        if value.status is UploadStatus.ALREADY_EXISTS:
            return DeliveryOutcome.DUPLICATE.value, None
        if value.status is UploadStatus.FAILED and not value.retryable:
            return DeliveryOutcome.REFUSED.value, value.reason or "body_upload_refused"
        return DeliveryOutcome.UNKNOWN.value, None

    gated = execute_project_transport_disclosure(
        disclosure,
        send=lambda: push_content(task, auth_token, server_url, timeout=timeout),
        classify=_classify,
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


def _build_request_body(task: BodyUploadTask) -> dict[str, Any]:
    """Build JSON request body from task.

    Includes 5 namespace fields (FR-002) + 4 artifact fields (FR-003).
    """
    return {
        "project_uuid": task.project_uuid,
        "mission_slug": task.mission_slug,
        "target_branch": task.target_branch,
        "mission_type": task.mission_type,
        "manifest_version": task.manifest_version,
        "artifact_path": task.artifact_path,
        "content_hash": task.content_hash,
        "hash_algorithm": task.hash_algorithm,
        "content_body": task.content_body,
    }


def _safe_json(response: Any) -> dict[str, Any]:
    """Parse response JSON safely, returning empty dict on failure."""
    try:
        return response.json()  # type: ignore[no-any-return]
    except ValueError:
        return {}


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


def _classify_response(
    task: BodyUploadTask,
    response: Any,
) -> UploadOutcome:
    """Map HTTP response to UploadOutcome with retryable semantics."""
    status = response.status_code

    if status == 201:
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.UPLOADED,
            reason="stored",
            content_hash=task.content_hash,
        )

    if status == 200:
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.ALREADY_EXISTS,
            reason="already_exists",
            content_hash=task.content_hash,
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
        reason = CATEGORY_MISSING_PRIVATE_TEAM if _body_mentions_missing_private_team(body) else "unauthorized"
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
