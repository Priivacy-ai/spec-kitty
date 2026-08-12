"""Body upload preparation and filtering for artifact body sync.

Transforms ArtifactRef list from the indexer into queued body upload tasks.
Filters by supported surfaces (FR-004), formats (FR-005), size limits,
and binary detection (FR-006). Re-hash guard detects TOCTOU file changes.
"""

from __future__ import annotations

import hashlib
import logging
from kernel._safe_re import re
from pathlib import Path
from typing import TYPE_CHECKING

from specify_cli.core.paths import locate_project_root

from .body_queue import BodyEnqueueResult
from .namespace import UploadOutcome, UploadStatus, is_supported_format

if TYPE_CHECKING:
    from specify_cli.dossier.models import ArtifactRef

    from .body_queue import OfflineBodyUploadQueue
    from .layout_generation import LayoutGenerationAuthority
    from .namespace import NamespaceRef
    from .project_context import ProjectSyncContext
    from .project_store import ProjectUnitOfWork

logger = logging.getLogger(__name__)

MAX_INLINE_SIZE_BYTES = 512 * 1024  # 512 KiB

# FR-004: Supported feature-scoped surfaces
_TOP_LEVEL_ARTIFACTS: frozenset[str] = frozenset(
    {
        "spec.md",
        "plan.md",
        "tasks.md",
        "analysis-report.md",
        "research.md",
        "quickstart.md",
        "data-model.md",
        "lint-report.json",
    }
)

_DIRECTORY_PREFIXES: tuple[str, ...] = (
    "research/",
    "contracts/",
    "checklists/",
)

_WP_PATTERN = re.compile(r"^tasks/WP\d+.*\.md$")


def project_consents_to_hosted_sync(
    project_uuid: str | None,
    *,
    feature_dir: Path | None = None,
    repo_root: Path | None = None,
) -> bool:
    """Does *project_uuid* consent to hosted sync? (#3030 FR-031)

    The one consent question for the dossier path — the enqueue gate below and the
    pipeline gate in :mod:`~specify_cli.sync.dossier_pipeline` both ask it here, so the
    path cannot grow two answers again.

    **This replaces ``is_sync_enabled_for_checkout(repo_root)``, and both halves of
    that call were wrong.**

    *Which project is asking* now comes from the data's **own** ``project_uuid`` — the
    one on the ``NamespaceRef`` the bodies are being staged under, which is the same
    value ``background._consenting_body_project_uuids`` re-reads off the queued row
    before the actual POST (E10). Deriving it from the checkout instead is the bug
    class: a checkout answers "where am I standing", never "may this project's
    documents leave", and the two differ in exactly the monorepo/worktree/``cd``
    situations the 2026-07-27 incident occurred in.

    *Whether it consents* now comes from ``consent.consented_project_uuids`` rather
    than ``routing.effective_sync_enabled``. The routing chain also honours the
    repo-slug-keyed ``[sync.repo_defaults]`` record, which FR-019 condemns because it
    is keyed on a mutable git remote — a fresh clone or a re-``git init`` inherits a
    decision nobody made about it. One path holding two gates that walked two
    different chains is the C-003 divergence; both now walk the declared one.

    **Fails closed, and the fail-open branch is gone.** The old gate read
    ``repo_root is not None and not is_sync_enabled_for_checkout(repo_root)``, so an
    unresolvable project root skipped the gate altogether — undetermined read as
    consent, FR-003's rule verbatim. Here an unusable uuid and a raising chain both
    deny. Note this is *not* "deny whenever the checkout is unresolvable": the uuid
    still carries a determinable answer through the machine-global index, so an
    unresolvable checkout costs the project-local *level*, not the decision.

    *feature_dir* / *repo_root* are only **offered** as checkouts for the project-local
    level. A root that declares a different uuid is ignored by the resolver, so
    offering one can never widen the answer.
    """
    uuid = str(project_uuid or "").strip()
    if not uuid:
        return False

    offered: list[Path] = []
    if repo_root is not None:
        offered.append(Path(repo_root))
    elif feature_dir is not None:
        located = locate_project_root(feature_dir)
        if located is not None:
            offered.append(located)

    try:
        from .consent import consented_project_uuids  # noqa: PLC0415

        granted = uuid in consented_project_uuids([uuid], checkout_roots=offered or None)
    except Exception:  # noqa: BLE001 - unanswerable is not granted
        logger.warning(
            "Could not resolve hosted-sync consent for project %s; withholding its artifact bodies",
            uuid,
            exc_info=True,
        )
        return False

    if not granted:
        logger.debug(
            "Artifact bodies withheld: project %s has not consented to hosted sync",
            uuid,
        )
    return granted


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
    actual_hash = hashlib.sha256(raw_bytes).hexdigest()  # noqa: TID251 - production raw SHA-256 owner
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


def _validate_explicit_body_capture_authority(
    namespace_ref: NamespaceRef,
    body_queue: OfflineBodyUploadQueue,
    project_context: ProjectSyncContext | None,
    project_unit: ProjectUnitOfWork | None,
    project_layout: LayoutGenerationAuthority | None,
) -> bool:
    """Validate the optional exact same-UoW capture tuple before artifact I/O."""
    explicit_authority = project_context is not None or project_unit is not None or project_layout is not None
    if not explicit_authority:
        return False
    if project_context is None or project_unit is None or project_layout is None:
        raise ValueError("body capture requires context, active unit, and layout authority")
    from .project_context import validate_project_sync_context_authority

    validate_project_sync_context_authority(project_context)
    if project_unit.store_identity is not project_context.store_identity:
        raise ValueError("body project unit does not match the explicit context")
    if body_queue.store_identity is not project_context.store_identity:
        raise ValueError("body queue does not match the explicit project context")
    if body_queue.unit_of_work_identity != project_unit.connection_identity:
        raise ValueError("body queue does not use the supplied active unit")
    if namespace_ref.project_uuid != project_context.project_uuid.storage_token:
        raise ValueError("body namespace belongs to another project")
    # This read proves the caller did not retain a stale unit after its owning
    # transaction closed. The permit check binds the supplied layout authority
    # to the same canonical project and runtime root before artifact reads or
    # durable writes. UUID equality alone is insufficient: a same-UUID authority
    # rooted under another SPEC_KITTY_HOME must not redirect this transaction.
    project_unit.execute("SELECT 1")
    expected_projects_root = project_context.store_identity.database_path.parents[2]
    if (
        project_layout.record_path != expected_projects_root / ".layout-generation.json"
        or project_layout.lock_path != expected_projects_root / ".layout-generation.lock"
        or project_layout.marker_path != expected_projects_root / ".layout-generation.initialized"
    ):
        raise ValueError("body layout authority belongs to another runtime root")
    if project_layout.issue_write_permit().project_uuid != project_context.project_uuid:
        raise ValueError("body layout authority belongs to another project")
    return True


def _enqueue_artifact(
    artifact: ArtifactRef,
    namespace_ref: NamespaceRef,
    body_queue: OfflineBodyUploadQueue,
    content: str,
    actual_hash: str,
) -> UploadOutcome:
    """Enqueue already-read, already-hashed artifact content."""
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

    return UploadOutcome(
        artifact_path=artifact.relative_path,
        status=status,
        reason=reason,
        content_hash=actual_hash,
    )


def _process_artifact(
    artifact: ArtifactRef,
    namespace_ref: NamespaceRef,
    body_queue: OfflineBodyUploadQueue,
    feature_dir: Path,
) -> UploadOutcome:
    """Filter, read, and enqueue a single artifact; return its outcome.

    Each filter stage returns early with the SKIPPED outcome that the
    original inline loop produced via ``continue`` — same guard order,
    same reasons, same terminal enqueue call.
    """
    # Skip non-present artifacts
    if not artifact.is_present:
        return UploadOutcome(
            artifact_path=artifact.relative_path,
            status=UploadStatus.SKIPPED,
            reason=f"not_present: {artifact.error_reason or 'unknown'}",
        )

    # Filter 1: Supported surface (FR-004)
    if not _is_supported_surface(artifact.relative_path):
        return UploadOutcome(
            artifact_path=artifact.relative_path,
            status=UploadStatus.SKIPPED,
            reason="unsupported_surface",
        )

    # Filter 2: Supported format (FR-005/FR-006)
    format_skip = _check_format(artifact.relative_path)
    if format_skip is not None:
        return format_skip

    # Filter 3: Size limit
    size_skip = _check_size_limit(artifact.relative_path, artifact.size_bytes)
    if size_skip is not None:
        return size_skip

    # Read content + re-hash guard
    result = _read_and_rehash(
        feature_dir,
        artifact.relative_path,
        artifact.content_hash_sha256,
    )
    if isinstance(result, UploadOutcome):
        return result

    content, actual_hash = result
    if content == "":
        return UploadOutcome(
            artifact_path=artifact.relative_path,
            status=UploadStatus.SKIPPED,
            reason="empty_content",
            content_hash=actual_hash,
        )

    return _enqueue_artifact(artifact, namespace_ref, body_queue, content, actual_hash)


def prepare_body_uploads(
    artifacts: list[ArtifactRef],
    namespace_ref: NamespaceRef,
    body_queue: OfflineBodyUploadQueue,
    feature_dir: Path,
    *,
    project_context: ProjectSyncContext | None = None,
    project_unit: ProjectUnitOfWork | None = None,
    project_layout: LayoutGenerationAuthority | None = None,
) -> list[UploadOutcome]:
    """Filter artifacts, read content, enqueue body uploads.

    Returns a list of UploadOutcome for every artifact processed
    (including skipped ones for diagnostics per FR-012).
    """
    explicit_authority = _validate_explicit_body_capture_authority(
        namespace_ref,
        body_queue,
        project_context,
        project_unit,
        project_layout,
    )
    # Legacy callers have no store-minted local-capture authority. Preserve their
    # fail-closed consent lookup; the explicit path above already carries the exact
    # verified store decision and must not reopen that store while its UoW is live.
    if not explicit_authority and not project_consents_to_hosted_sync(namespace_ref.project_uuid, feature_dir=feature_dir):
        return [
            UploadOutcome(
                artifact_path=artifact.relative_path,
                status=UploadStatus.SKIPPED,
                reason="project_not_consented",
            )
            for artifact in artifacts
        ]

    return [
        _process_artifact(artifact, namespace_ref, body_queue, feature_dir)
        for artifact in artifacts
    ]


def log_upload_outcomes(
    outcomes: list[UploadOutcome],
    mission_slug: str,
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
        mission_slug,
        ", ".join(f"{k}={v}" for k, v in sorted(by_status.items())),
    )

    for outcome in outcomes:
        log.debug("  %s", outcome)
