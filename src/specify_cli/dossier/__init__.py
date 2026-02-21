"""Mission dossier system for artifact indexing, classification, and parity detection."""

from .models import ArtifactRef, MissionDossier
from .hasher import hash_file, hash_file_with_validation, Hasher
from .manifest import (
    ArtifactClassEnum,
    ExpectedArtifactSpec,
    ExpectedArtifactManifest,
    ManifestRegistry,
)
from .events import (
    MissionDossierArtifactIndexedPayload,
    MissionDossierArtifactMissingPayload,
    ArtifactCountsPayload,
    MissionDossierSnapshotComputedPayload,
    MissionDossierParityDriftDetectedPayload,
    emit_artifact_indexed,
    emit_artifact_missing,
    emit_snapshot_computed,
    emit_parity_drift_detected,
)

__all__ = [
    "ArtifactRef",
    "MissionDossier",
    "hash_file",
    "hash_file_with_validation",
    "Hasher",
    "ArtifactClassEnum",
    "ExpectedArtifactSpec",
    "ExpectedArtifactManifest",
    "ManifestRegistry",
    "MissionDossierArtifactIndexedPayload",
    "MissionDossierArtifactMissingPayload",
    "ArtifactCountsPayload",
    "MissionDossierSnapshotComputedPayload",
    "MissionDossierParityDriftDetectedPayload",
    "emit_artifact_indexed",
    "emit_artifact_missing",
    "emit_snapshot_computed",
    "emit_parity_drift_detected",
]
