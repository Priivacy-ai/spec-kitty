"""Mission dossier system for artifact indexing, classification, and parity detection."""

from .models import ArtifactRef, MissionDossier, MissionDossierSnapshot
from .hasher import (
    WP_STATIC_PROJECTION_FIELDS,
    compute_dossier_snapshot_hash,
    hash_file,
    hash_file_with_validation,
    hash_wp_static_projection,
    wp_static_projection,
)
from .manifest import (
    ArtifactClassEnum,
    ExpectedArtifactSpec,
    ExpectedArtifactManifest,
    ManifestRegistry,
)
from .events import (
    ArtifactIdentity,
    ContentHashRef,
    LocalNamespaceTuple,
    MissionDossierArtifactIndexedPayload,
    MissionDossierArtifactMissingPayload,
    MissionDossierSnapshotComputedPayload,
    MissionDossierParityDriftDetectedPayload,
    emit_artifact_indexed,
    emit_artifact_missing,
    emit_snapshot_computed,
    emit_parity_drift_detected,
)
from .snapshot import (
    compute_snapshot,
    compute_parity_hash_from_dossier,
    get_parity_hash_components,
    save_snapshot,
    load_snapshot,
    get_latest_snapshot,
)

__all__ = [
    "ArtifactRef",
    "MissionDossier",
    "MissionDossierSnapshot",
    "hash_file",
    "hash_file_with_validation",
    "compute_dossier_snapshot_hash",
    "wp_static_projection",
    "hash_wp_static_projection",
    "WP_STATIC_PROJECTION_FIELDS",
    "ArtifactClassEnum",
    "ExpectedArtifactSpec",
    "ExpectedArtifactManifest",
    "ManifestRegistry",
    "ArtifactIdentity",
    "ContentHashRef",
    "LocalNamespaceTuple",
    "MissionDossierArtifactIndexedPayload",
    "MissionDossierArtifactMissingPayload",
    "MissionDossierSnapshotComputedPayload",
    "MissionDossierParityDriftDetectedPayload",
    "emit_artifact_indexed",
    "emit_artifact_missing",
    "emit_snapshot_computed",
    "emit_parity_drift_detected",
    "compute_snapshot",
    "compute_parity_hash_from_dossier",
    "get_parity_hash_components",
    "save_snapshot",
    "load_snapshot",
    "get_latest_snapshot",
]
