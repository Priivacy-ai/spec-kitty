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
) -> DossierSyncResult:
    """Run full dossier sync: index → emit events → prepare body uploads.

    This is the ONLY entrypoint for body upload preparation.
    BackgroundSyncService only drains already-enqueued work.
    """
    from specify_cli.dossier.events import emit_artifact_indexed
    from specify_cli.dossier.indexer import Indexer
    from specify_cli.dossier.manifest import ManifestRegistry

    from .body_upload import prepare_body_uploads
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

    # Step 2: Emit dossier events for present artifacts
    events_emitted = 0
    for artifact in dossier.artifacts:
        if not artifact.is_present:
            continue
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
            )
            if result is not None:
                events_emitted += 1
        except Exception as e:
            logger.warning(
                "Event emission failed for %s: %s", artifact.relative_path, e,
            )

    # Step 3: Prepare body uploads
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
