"""Body upload preparation and filtering for artifact body sync.

Transforms ArtifactRef list from the indexer into queued body upload tasks.
Filters by supported surfaces (FR-004), formats (FR-005), size limits,
and binary detection (FR-006). Re-hash guard detects TOCTOU file changes.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from .body_queue import BodyEnqueueResult
from .namespace import UploadOutcome, UploadStatus, is_supported_format

if TYPE_CHECKING:
    from specify_cli.dossier.models import ArtifactRef

    from .body_queue import OfflineBodyUploadQueue
    from .namespace import NamespaceRef

logger = logging.getLogger(__name__)

MAX_INLINE_SIZE_BYTES = 512 * 1024  # 512 KiB

# FR-004: Supported feature-scoped surfaces
_TOP_LEVEL_ARTIFACTS: frozenset[str] = frozenset({
    "spec.md", "plan.md", "tasks.md", "research.md",
    "quickstart.md", "data-model.md",
})

_DIRECTORY_PREFIXES: tuple[str, ...] = (
    "research/", "contracts/", "checklists/",
)

_WP_PATTERN = re.compile(r"^tasks/WP\d+.*\.md$")


def _is_supported_surface(relative_path: str) -> bool:
    """Check if artifact path matches FR-004 supported surfaces."""
    if relative_path in _TOP_LEVEL_ARTIFACTS:
        return True
    if any(relative_path.startswith(prefix) for prefix in _DIRECTORY_PREFIXES):
        return True
    return bool(_WP_PATTERN.match(relative_path))


def _check_format(relative_path: str) -> UploadOutcome | None:
    """Return UploadOutcome(skipped) if format unsupported, else None."""
    if not is_supported_format(relative_path):
        ext = Path(relative_path).suffix or "(no extension)"
        return UploadOutcome(
            artifact_path=relative_path,
            status=UploadStatus.SKIPPED,
            reason=f"unsupported_format: {ext}",
        )
    return None


def _check_size_limit(relative_path: str, size_bytes: int) -> UploadOutcome | None:
    """Return UploadOutcome(skipped) if oversized, else None."""
    if size_bytes > MAX_INLINE_SIZE_BYTES:
        return UploadOutcome(
            artifact_path=relative_path,
            status=UploadStatus.SKIPPED,
            reason=f"oversized: {size_bytes} bytes > {MAX_INLINE_SIZE_BYTES} limit",
        )
    return None


def _read_and_rehash(
    feature_dir: Path,
    relative_path: str,
    expected_hash: str,
) -> tuple[str, str] | UploadOutcome:
    """Read file content and verify hash matches indexer scan.

    Reads raw bytes for hashing (matching dossier/hasher.py convention),
    then decodes as UTF-8 for content body.

    Returns (content_text, actual_hash) on success, or UploadOutcome on failure.
    """
    file_path = feature_dir / relative_path
    try:
        raw_bytes = file_path.read_bytes()
    except FileNotFoundError:
        return UploadOutcome(
            artifact_path=relative_path,
            status=UploadStatus.SKIPPED,
            reason="deleted_after_scan",
        )
    except OSError as e:
        return UploadOutcome(
            artifact_path=relative_path,
            status=UploadStatus.SKIPPED,
            reason=f"read_error: {e}",
        )

    # Hash raw bytes to match dossier/hasher.py hash_file() convention
    actual_hash = hashlib.sha256(raw_bytes).hexdigest()
    if actual_hash != expected_hash:
        return UploadOutcome(
            artifact_path=relative_path,
            status=UploadStatus.SKIPPED,
            reason="content_hash_mismatch",
            content_hash=actual_hash,
        )

    # Decode as UTF-8 — catches binary files that got past format filtering
    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return UploadOutcome(
            artifact_path=relative_path,
            status=UploadStatus.SKIPPED,
            reason="not_valid_utf8",
        )

    return content, actual_hash


def prepare_body_uploads(
    artifacts: list[ArtifactRef],
    namespace_ref: NamespaceRef,
    body_queue: OfflineBodyUploadQueue,
    feature_dir: Path,
) -> list[UploadOutcome]:
    """Filter artifacts, read content, enqueue body uploads.

    Returns a list of UploadOutcome for every artifact processed
    (including skipped ones for diagnostics per FR-012).
    """
    outcomes: list[UploadOutcome] = []

    for artifact in artifacts:
        # Skip non-present artifacts
        if not artifact.is_present:
            outcomes.append(UploadOutcome(
                artifact_path=artifact.relative_path,
                status=UploadStatus.SKIPPED,
                reason=f"not_present: {artifact.error_reason or 'unknown'}",
            ))
            continue

        # Filter 1: Supported surface (FR-004)
        if not _is_supported_surface(artifact.relative_path):
            outcomes.append(UploadOutcome(
                artifact_path=artifact.relative_path,
                status=UploadStatus.SKIPPED,
                reason="unsupported_surface",
            ))
            continue

        # Filter 2: Supported format (FR-005/FR-006)
        format_skip = _check_format(artifact.relative_path)
        if format_skip is not None:
            outcomes.append(format_skip)
            continue

        # Filter 3: Size limit
        size_skip = _check_size_limit(artifact.relative_path, artifact.size_bytes)
        if size_skip is not None:
            outcomes.append(size_skip)
            continue

        # Read content + re-hash guard
        result = _read_and_rehash(
            feature_dir, artifact.relative_path, artifact.content_hash_sha256,
        )
        if isinstance(result, UploadOutcome):
            outcomes.append(result)
            continue

        content, actual_hash = result

        # Enqueue
        enqueue_result = body_queue.enqueue(
            namespace=namespace_ref,
            artifact_path=artifact.relative_path,
            content_hash=actual_hash,
            content_body=content,
            size_bytes=len(content.encode("utf-8")),
        )

        if enqueue_result == BodyEnqueueResult.ENQUEUED:
            status = UploadStatus.QUEUED
            reason = "enqueued"
        elif enqueue_result == BodyEnqueueResult.ALREADY_EXISTS:
            status = UploadStatus.ALREADY_EXISTS
            reason = "already_in_queue"
        else:
            status = UploadStatus.FAILED
            reason = "queue_full"

        outcomes.append(UploadOutcome(
            artifact_path=artifact.relative_path,
            status=status,
            reason=reason,
            content_hash=actual_hash,
        ))

    return outcomes


def log_upload_outcomes(
    outcomes: list[UploadOutcome],
    feature_slug: str,
    log: logging.Logger | None = None,
) -> None:
    """Log per-artifact upload outcomes with summary.

    INFO level: aggregate counts by status (always visible).
    DEBUG level: per-artifact detail (visible with -v or --debug).
    """
    if log is None:
        log = logger

    by_status: dict[str, int] = {}
    for outcome in outcomes:
        by_status[outcome.status.value] = by_status.get(outcome.status.value, 0) + 1

    log.info(
        "Body upload results for %s: %s",
        feature_slug,
        ", ".join(f"{k}={v}" for k, v in sorted(by_status.items())),
    )

    for outcome in outcomes:
        log.debug("  %s", outcome)
