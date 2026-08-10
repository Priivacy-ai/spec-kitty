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
    from specify_cli.dossier.snapshot import MissionDossierSnapshot
    from specify_cli.identity.project import ProjectIdentity

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


def _emit_artifact_events(
    dossier: MissionDossier,
    namespace_ref: NamespaceRef,
    step_id: str | None,
    ns_dict: dict[str, object],
) -> int:
    """Emit indexed/missing events for every artifact in the dossier.

    Each artifact's emission is independently isolated (its own try/except)
    so one artifact's failure never blocks the rest — mirrors the original
    inline loop's per-artifact isolation. Returns the count of events
    successfully emitted (a non-``None`` result).
    """
    from specify_cli.dossier.events import emit_artifact_indexed, emit_artifact_missing

    events_emitted = 0
    for artifact in dossier.artifacts:
        if artifact.is_present:
            try:
                result = emit_artifact_indexed(
                    mission_slug=namespace_ref.mission_slug,
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
                result = emit_artifact_missing(
                    mission_slug=namespace_ref.mission_slug,
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
    return events_emitted


def _emit_snapshot(
    dossier: MissionDossier,
    feature_dir: Path,
    namespace_ref: NamespaceRef,
    ns_dict: dict[str, object],
) -> tuple[MissionDossierSnapshot | None, int]:
    """Compute, persist, and emit the dossier snapshot.

    Retains its own try/except so a snapshot failure never aborts the other
    pipeline steps. Returns ``(snapshot, events_emitted)`` — ``snapshot`` is
    ``None`` and ``events_emitted`` is ``0`` on failure.
    """
    from specify_cli.dossier.events import emit_snapshot_computed
    from specify_cli.dossier.snapshot import compute_snapshot, save_snapshot

    snapshot: MissionDossierSnapshot | None = None
    events_emitted = 0
    try:
        snapshot = compute_snapshot(dossier)
        save_snapshot(snapshot, feature_dir)
        dossier.latest_snapshot = snapshot.model_dump(mode="json")

        result = emit_snapshot_computed(
            mission_slug=namespace_ref.mission_slug,
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
    return snapshot, events_emitted


def _emit_drift(
    snapshot: MissionDossierSnapshot,
    feature_dir: Path,
    namespace_ref: NamespaceRef,
    ns_dict: dict[str, object],
    repo_root: Path,
    project_identity: ProjectIdentity,
) -> int:
    """Detect and emit parity drift against the baseline snapshot.

    Retains its own try/except so a drift-detection failure never aborts the
    other pipeline steps. Returns the count of events emitted (0 or 1).
    """
    from specify_cli.dossier.drift_detector import detect_drift
    from specify_cli.dossier.events import emit_parity_drift_detected

    events_emitted = 0
    try:
        has_drift, drift_info = detect_drift(
            mission_slug=namespace_ref.mission_slug,
            current_snapshot=snapshot,
            repo_root=repo_root,
            project_identity=project_identity,
            target_branch=namespace_ref.target_branch,
            mission_type=namespace_ref.mission_type,
            manifest_version=namespace_ref.manifest_version,
        )
        if has_drift and drift_info is not None:
            result = emit_parity_drift_detected(
                mission_slug=namespace_ref.mission_slug,
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
    return events_emitted


def _prepare_bodies(
    dossier: MissionDossier,
    namespace_ref: NamespaceRef,
    body_queue: OfflineBodyUploadQueue,
    feature_dir: Path,
) -> tuple[list[UploadOutcome], list[str]]:
    """Prepare body uploads for the dossier's artifacts.

    Retains its own try/except so a body-upload-preparation failure never
    aborts the events already emitted. Returns ``(body_outcomes, errors)``.
    """
    from .body_upload import prepare_body_uploads

    body_outcomes: list[UploadOutcome] = []
    errors: list[str] = []
    try:
        body_outcomes = prepare_body_uploads(
            artifacts=dossier.artifacts,
            namespace_ref=namespace_ref,
            body_queue=body_queue,
            feature_dir=feature_dir,
        )
    except Exception as e:
        logger.exception("Body upload preparation failed for %s", feature_dir)
        errors.append(f"body_upload_preparation_failed: {e}")
    return body_outcomes, errors


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
    from specify_cli.dossier.indexer import Indexer
    from specify_cli.dossier.manifest import ManifestRegistry

    from .body_upload import log_upload_outcomes
    from .lint_report_staging import stage_charter_lint_report
    from .namespace import UploadStatus

    # Step 0: Stage the repo-global charter-lint decay report into this
    # mission's dossier BEFORE indexing, but only when the report was produced
    # for this mission (issue #2481, unblocks saas #392). Best-effort no-op.
    if stage_charter_lint_report(feature_dir, namespace_ref.mission_slug):
        logger.info(
            "Staged charter-lint decay report into dossier for %s",
            namespace_ref.mission_slug,
        )

    # Step 1: Index
    try:
        indexer = Indexer(ManifestRegistry())
        dossier = indexer.index_feature(feature_dir, mission_type, step_id)
    except Exception as e:
        logger.exception("Indexer failed for %s", feature_dir)
        return DossierSyncResult(
            dossier=None, events_emitted=0, body_outcomes=[], errors=[str(e)],
        )

    ns_dict = namespace_ref.to_dict()
    events_emitted = 0

    # Step 2: Emit dossier events for present and missing artifacts
    events_emitted += _emit_artifact_events(dossier, namespace_ref, step_id, ns_dict)

    # Step 3: Compute + emit snapshot (always) and drift (if baseline exists)
    snapshot, snapshot_events = _emit_snapshot(dossier, feature_dir, namespace_ref, ns_dict)
    events_emitted += snapshot_events

    if snapshot is not None and repo_root is not None and project_identity is not None:
        events_emitted += _emit_drift(
            snapshot, feature_dir, namespace_ref, ns_dict, repo_root, project_identity,
        )

    # Step 4: Prepare body uploads
    body_outcomes, errors = _prepare_bodies(dossier, namespace_ref, body_queue, feature_dir)

    # Per-artifact result logging (FR-012)
    if body_outcomes:
        log_upload_outcomes(body_outcomes, namespace_ref.mission_slug, logger)

    # Summary logging
    queued = sum(1 for o in body_outcomes if o.status == UploadStatus.QUEUED)
    skipped = sum(1 for o in body_outcomes if o.status == UploadStatus.SKIPPED)
    logger.info(
        "Dossier sync for %s: %d events emitted, %d bodies queued, %d skipped",
        namespace_ref.mission_slug, events_emitted, queued, skipped,
    )

    return DossierSyncResult(
        dossier=dossier,
        events_emitted=events_emitted,
        body_outcomes=body_outcomes,
        errors=errors,
    )


def trigger_feature_dossier_sync_if_enabled(
    feature_dir: Path,
    mission_slug: str,
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
        from specify_cli.mission import get_mission_type
        from specify_cli.sync.namespace import NamespaceRef, resolve_manifest_version
        from specify_cli.identity.project import resolve_identity
        from specify_cli.sync.body_queue import OfflineBodyUploadQueue

        # Background dossier sync: resolve identity WITHOUT persisting (#2263,
        # FR-001/FR-003) — a fire-and-forget read path must not dirty config.yaml.
        identity = resolve_identity(repo_root)
        if identity.project_uuid is None:
            logger.warning("No project UUID; skipping dossier sync")
            return None

        # #3030 FR-031 (E5): ``is_saas_sync_enabled()`` above is machine-global
        # *arming*, and arming is never a grant — it is the 2026-07-27 incident's own
        # mechanism, exported once and ridden by five projects that had never opted in.
        # Until now nothing between it and ``prepare_body_uploads`` asked the project.
        # Asked here as well as at the enqueue because this gate stands in front of
        # more than the bodies: everything below it emits dossier events carrying the
        # mission slug, computes and saves a snapshot, and runs drift detection. Both
        # gates now read the one consent chain, so this is defence in depth rather than
        # the two-chains divergence C-003 forbids (the same shape as
        # ``emit_local_commit`` + ``flush_pending_local_commits``).
        from .body_upload import project_consents_to_hosted_sync

        if not project_consents_to_hosted_sync(
            str(identity.project_uuid), repo_root=repo_root
        ):
            logger.debug(
                "Dossier sync skipped for %s: project %s has not consented to hosted sync",
                mission_slug,
                identity.project_uuid,
            )
            return None

        target_branch = get_feature_target_branch(repo_root, mission_slug)
        resolved_mission = get_mission_type(feature_dir) or mission_type
        manifest_version = resolve_manifest_version(resolved_mission)

        namespace_ref = NamespaceRef.from_context(
            identity=identity,
            mission_slug=mission_slug,
            target_branch=target_branch,
            mission_type=resolved_mission,
            manifest_version=manifest_version,
        )

        # Create body queue directly — writes to the same scoped SQLite DB
        # the daemon drains.  Avoids starting a full SyncRuntime (threads,
        # WebSocket, atexit handlers) inside a short-lived CLI process.
        body_queue = OfflineBodyUploadQueue()

        return sync_feature_dossier(
            feature_dir=feature_dir,
            namespace_ref=namespace_ref,
            body_queue=body_queue,
            mission_type=resolved_mission,
            step_id=step_id,
            repo_root=repo_root,
            project_identity=identity,
        )
    except Exception as e:
        logger.warning("Dossier sync failed for %s: %s", mission_slug, e)
        return None
