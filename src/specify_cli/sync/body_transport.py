"""HTTP transport for artifact body push to SaaS push-content endpoint.

Sends individual body upload tasks to POST /api/dossier/push-content/
and classifies responses into UploadOutcome with retryable semantics.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import requests

from .namespace import UploadOutcome, UploadStatus

if TYPE_CHECKING:
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

    Returns UploadOutcome classifying the server response.
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
            url, json=payload, headers=headers, timeout=timeout,
        )
    except requests.ConnectionError as e:
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.FAILED,
            reason=f"connection_error: {e}",
            content_hash=task.content_hash,
            retryable=True,
        )
    except requests.Timeout as e:
        return UploadOutcome(
            artifact_path=task.artifact_path,
            status=UploadStatus.FAILED,
            reason=f"timeout: {e}",
            content_hash=task.content_hash,
            retryable=True,
        )

    return _classify_response(task, response)


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


def _safe_json(response: requests.Response) -> dict[str, Any]:
    """Parse response JSON safely, returning empty dict on failure."""
    try:
        return response.json()  # type: ignore[no-any-return]
    except (ValueError, requests.JSONDecodeError):
        return {}


def _classify_response(
    task: BodyUploadTask, response: requests.Response,
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
            reason=f"bad_request: {body.get('detail', 'unknown')}",
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
    task: BodyUploadTask, response: requests.Response,
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
