"""Dossier sync pipeline orchestration.

Wires indexer → event emission → body upload preparation
as a single pipeline invoked during feature-aware sync.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from specify_cli.dossier.models import MissionDossier
    from specify_cli.sync.project_identity import ProjectIdentity

    from .body_queue import OfflineBodyUploadQueue
    from .namespace import NamespaceRef, UploadOutcome

logger = logging.getLogger(__name__)


@dataclass
class DossierSyncResult:
    """Result of a full dossier sync pipeline run."""

    dossier: MissionDossier | None
    events_emitted: int
    body_outcomes: list[UploadOutcome]
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.dossier is not None and not self.errors


def sync_feature_dossier(
    feature_dir: Path,
    namespace_ref: NamespaceRef,
    body_queue: OfflineBodyUploadQueue,
    mission_type: str = "software-dev",
    step_id: str | None = None,
    *,
    repo_root: Path | None = None,
    project_identity: ProjectIdentity | None = None,
) -> DossierSyncResult:
    """Run full dossier sync: index → emit events → prepare body uploads.

    This is the ONLY entrypoint for body upload preparation.
    BackgroundSyncService only drains already-enqueued work.
    """
    from specify_cli.dossier.drift_detector import detect_drift
    from specify_cli.dossier.events import (
        emit_artifact_indexed,
        emit_parity_drift_detected,
        emit_snapshot_computed,
    )
    from specify_cli.dossier.indexer import Indexer
    from specify_cli.dossier.manifest import ManifestRegistry
    from specify_cli.dossier.snapshot import compute_snapshot, save_snapshot

    from .body_upload import log_upload_outcomes, prepare_body_uploads
    from .namespace import UploadStatus

    errors: list[str] = []

    # Step 1: Index
    try:
        indexer = Indexer(ManifestRegistry())
        dossier = indexer.index_feature(feature_dir, mission_type, step_id)
    except Exception as e:
        logger.error("Indexer failed for %s: %s", feature_dir, e)
        return DossierSyncResult(
            dossier=None, events_emitted=0, body_outcomes=[], errors=[str(e)],
        )

    # Step 2: Emit dossier events for present and missing artifacts
    events_emitted = 0
    ns_dict = namespace_ref.to_dict()
    for artifact in dossier.artifacts:
        if artifact.is_present:
            try:
                result = emit_artifact_indexed(
                    feature_slug=namespace_ref.feature_slug,
                    artifact_key=artifact.artifact_key,
                    artifact_class=artifact.artifact_class,
                    relative_path=artifact.relative_path,
                    content_hash_sha256=artifact.content_hash_sha256,
                    size_bytes=artifact.size_bytes,
                    step_id=step_id,
                    required_status=artifact.required_status,
                    namespace=ns_dict,
                )
                if result is not None:
                    events_emitted += 1
            except Exception as e:
                logger.warning(
                    "Event emission failed for %s: %s", artifact.relative_path, e,
                )
        else:
            # Emit missing event for non-present required artifacts
            try:
                from specify_cli.dossier.events import emit_artifact_missing

                result = emit_artifact_missing(
                    feature_slug=namespace_ref.feature_slug,
                    artifact_key=artifact.artifact_key,
                    artifact_class=artifact.artifact_class,
                    expected_path_pattern=artifact.relative_path,
                    reason_code=artifact.error_reason or "not_found",
                    blocking=artifact.required_status == "required",
                    namespace=ns_dict,
                )
                if result is not None:
                    events_emitted += 1
            except Exception as e:
                logger.warning(
                    "Missing event emission failed for %s: %s",
                    artifact.relative_path, e,
                )

    # Step 3: Compute + emit snapshot (always) and drift (if baseline exists)
    snapshot = None
    try:
        snapshot = compute_snapshot(dossier)
        save_snapshot(snapshot, feature_dir)
        dossier.latest_snapshot = snapshot.model_dump(mode="json")

        result = emit_snapshot_computed(
            feature_slug=namespace_ref.feature_slug,
            parity_hash_sha256=snapshot.parity_hash_sha256,
            total_artifacts=snapshot.total_artifacts,
            required_artifacts=snapshot.required_artifacts,
            required_present=snapshot.required_present,
            required_missing=snapshot.required_missing,
            optional_artifacts=snapshot.optional_artifacts,
            optional_present=snapshot.optional_present,
            completeness_status=snapshot.completeness_status,
            snapshot_id=snapshot.snapshot_id,
            namespace=ns_dict,
        )
        if result is not None:
            events_emitted += 1
    except Exception as e:
        logger.warning("Snapshot computation/emission failed for %s: %s", feature_dir, e)

    if snapshot is not None and repo_root is not None and project_identity is not None:
        try:
            has_drift, drift_info = detect_drift(
                feature_slug=namespace_ref.feature_slug,
                current_snapshot=snapshot,
                repo_root=repo_root,
                project_identity=project_identity,
                target_branch=namespace_ref.target_branch,
                mission_key=namespace_ref.mission_key,
                manifest_version=namespace_ref.manifest_version,
            )
            if has_drift and drift_info is not None:
                result = emit_parity_drift_detected(
                    feature_slug=namespace_ref.feature_slug,
                    local_parity_hash=drift_info["local_parity_hash"],
                    baseline_parity_hash=drift_info["baseline_parity_hash"],
                    missing_in_local=drift_info["missing_in_local"],
                    missing_in_baseline=drift_info["missing_in_baseline"],
                    severity=drift_info["severity"],
                    namespace=ns_dict,
                )
                if result is not None:
                    events_emitted += 1
        except Exception as e:
            logger.warning("Parity drift detection/emission failed for %s: %s", feature_dir, e)

    # Step 4: Prepare body uploads
    body_outcomes: list[UploadOutcome] = []
    try:
        body_outcomes = prepare_body_uploads(
            artifacts=dossier.artifacts,
            namespace_ref=namespace_ref,
            body_queue=body_queue,
            feature_dir=feature_dir,
        )
    except Exception as e:
        logger.error(
            "Body upload preparation failed for %s: %s", feature_dir, e,
        )
        errors.append(f"body_upload_preparation_failed: {e}")

    # Per-artifact result logging (FR-012)
    if body_outcomes:
        log_upload_outcomes(body_outcomes, namespace_ref.feature_slug, logger)

    # Summary logging
    queued = sum(1 for o in body_outcomes if o.status == UploadStatus.QUEUED)
    skipped = sum(1 for o in body_outcomes if o.status == UploadStatus.SKIPPED)
    logger.info(
        "Dossier sync for %s: %d events emitted, %d bodies queued, %d skipped",
        namespace_ref.feature_slug, events_emitted, queued, skipped,
    )

    return DossierSyncResult(
        dossier=dossier,
        events_emitted=events_emitted,
        body_outcomes=body_outcomes,
        errors=errors,
    )


def trigger_feature_dossier_sync_if_enabled(
    feature_dir: Path,
    feature_slug: str,
    repo_root: Path,
    mission_type: str = "software-dev",
    step_id: str | None = None,
) -> DossierSyncResult | None:
    """Fire-and-forget dossier sync triggered after feature artifact mutations.

    Never raises. Logs failures. Returns None if sync is disabled or fails.
    """
    try:
        from .feature_flags import is_saas_sync_enabled

        if not is_saas_sync_enabled():
            return None

        from specify_cli.core.paths import get_feature_target_branch
        from specify_cli.mission import get_feature_mission_key
        from specify_cli.sync.namespace import NamespaceRef, resolve_manifest_version
        from specify_cli.sync.project_identity import ensure_identity
        from specify_cli.sync.runtime import get_runtime

        # Resolve namespace components
        identity = ensure_identity(repo_root)
        if identity.project_uuid is None:
            logger.warning("No project UUID; skipping dossier sync")
            return None

        target_branch = get_feature_target_branch(repo_root, feature_slug)
        resolved_mission = get_feature_mission_key(feature_dir) or mission_type
        manifest_version = resolve_manifest_version(resolved_mission)

        namespace_ref = NamespaceRef.from_context(
            identity=identity,
            feature_slug=feature_slug,
            target_branch=target_branch,
            mission_key=resolved_mission,
            manifest_version=manifest_version,
        )

        # Get body queue from runtime
        runtime = get_runtime()
        if runtime.body_queue is None:
            logger.debug("Body queue not initialised; skipping dossier sync")
            return None

        return sync_feature_dossier(
            feature_dir=feature_dir,
            namespace_ref=namespace_ref,
            body_queue=runtime.body_queue,
            mission_type=resolved_mission,
            step_id=step_id,
            repo_root=repo_root,
            project_identity=identity,
        )
    except Exception as e:
        logger.warning("Dossier sync failed for %s: %s", feature_slug, e)
        return None
