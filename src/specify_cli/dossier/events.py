"""Mission dossier event types and emission.

This module defines the 4 canonical dossier event schemas and integration
with the sync infrastructure (EventEmitter + OfflineQueue) for SaaS backend
integration.

Event Types:
1. MissionDossierArtifactIndexed - Emitted once per artifact indexed
2. MissionDossierArtifactMissing - Emitted if required artifact missing
3. MissionDossierSnapshotComputed - Emitted after all artifacts indexed
4. MissionDossierParityDriftDetected - Emitted if parity hash differs from baseline

See: kitty-specs/042-local-mission-dossier-authority-parity-export/data-model.md
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# ── Event Payload Schemas ─────────────────────────────────────────────


class MissionDossierArtifactIndexedPayload(BaseModel):
    """Emitted when artifact successfully indexed.

    This event represents a single artifact that was successfully discovered,
    read, hashed, and registered in the dossier.
    """

    feature_slug: str = Field(..., min_length=1, description="Feature identifier")
    artifact_key: str = Field(..., min_length=1, description="Stable unique key for artifact")
    artifact_class: str = Field(..., description="Classification (input|workflow|output|evidence|policy|runtime|other)")
    relative_path: str = Field(..., min_length=1, description="Path relative to feature directory")
    content_hash_sha256: str = Field(..., description="SHA256 hash of artifact bytes")
    size_bytes: int = Field(..., ge=0, description="File size in bytes")
    wp_id: Optional[str] = Field(None, description="Work package ID if linked")
    step_id: Optional[str] = Field(None, description="Mission step if step-specific")
    required_status: str = Field(..., description="'required' or 'optional'")

    @field_validator("content_hash_sha256")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        """Validate SHA256 hex format."""
        if not re.match(r"^[a-f0-9]{64}$", v):
            raise ValueError(f"Invalid SHA256 hash: {v}")
        return v

    @field_validator("artifact_class")
    @classmethod
    def validate_artifact_class(cls, v: str) -> str:
        """Validate artifact classification."""
        valid_classes = {"input", "workflow", "output", "evidence", "policy", "runtime", "other"}
        if v not in valid_classes:
            raise ValueError(f"Invalid artifact_class: {v}")
        return v

    @field_validator("required_status")
    @classmethod
    def validate_required_status(cls, v: str) -> str:
        """Validate required status enum."""
        if v not in {"required", "optional"}:
            raise ValueError(f"Invalid required_status: {v}")
        return v


class MissionDossierArtifactMissingPayload(BaseModel):
    """Emitted when required artifact missing or unreadable.

    This event represents a required artifact that was expected (per manifest)
    but could not be found or read during the scan.
    """

    feature_slug: str = Field(..., min_length=1, description="Feature identifier")
    artifact_key: str = Field(..., min_length=1, description="Stable unique key for artifact")
    artifact_class: str = Field(..., description="Classification (input|workflow|output|evidence|policy|runtime|other)")
    expected_path_pattern: str = Field(..., description="Expected path pattern or glob")
    reason_code: str = Field(..., description="Reason code for absence")
    reason_detail: Optional[str] = Field(None, description="Additional detail about reason")
    blocking: bool = Field(..., description="True if blocks completeness")

    @field_validator("artifact_class")
    @classmethod
    def validate_artifact_class(cls, v: str) -> str:
        """Validate artifact classification."""
        valid_classes = {"input", "workflow", "output", "evidence", "policy", "runtime", "other"}
        if v not in valid_classes:
            raise ValueError(f"Invalid artifact_class: {v}")
        return v

    @field_validator("reason_code")
    @classmethod
    def validate_reason_code(cls, v: str) -> str:
        """Validate reason code enum."""
        valid_codes = {"not_found", "unreadable", "invalid_format", "deleted_after_scan"}
        if v not in valid_codes:
            raise ValueError(f"Invalid reason_code: {v}")
        return v


class ArtifactCountsPayload(BaseModel):
    """Artifact counts breakdown for snapshot computed event."""

    total: int = Field(..., ge=0, description="Total artifacts")
    required: int = Field(..., ge=0, description="Required artifacts in manifest")
    required_present: int = Field(..., ge=0, description="Required artifacts found")
    required_missing: int = Field(..., ge=0, description="Required artifacts missing")
    optional: int = Field(..., ge=0, description="Optional artifacts in manifest")
    optional_present: int = Field(..., ge=0, description="Optional artifacts found")


class MissionDossierSnapshotComputedPayload(BaseModel):
    """Emitted after snapshot computed.

    This event represents the completion of a scan and computation of the
    dossier snapshot, including artifact counts and completeness status.
    """

    feature_slug: str = Field(..., min_length=1, description="Feature identifier")
    parity_hash_sha256: str = Field(..., description="Deterministic hash of entire snapshot")
    artifact_counts: ArtifactCountsPayload = Field(..., description="Artifact count breakdown")
    completeness_status: str = Field(..., description="'complete' | 'incomplete' | 'unknown'")
    snapshot_id: str = Field(..., min_length=1, description="Unique snapshot identifier")

    @field_validator("parity_hash_sha256")
    @classmethod
    def validate_parity_hash(cls, v: str) -> str:
        """Validate SHA256 hex format."""
        if not re.match(r"^[a-f0-9]{64}$", v):
            raise ValueError(f"Invalid SHA256 hash: {v}")
        return v

    @field_validator("completeness_status")
    @classmethod
    def validate_completeness_status(cls, v: str) -> str:
        """Validate completeness status enum."""
        if v not in {"complete", "incomplete", "unknown"}:
            raise ValueError(f"Invalid completeness_status: {v}")
        return v


class MissionDossierParityDriftDetectedPayload(BaseModel):
    """Emitted when local snapshot differs from baseline.

    This event represents detection of a difference between the local snapshot
    and the accepted baseline snapshot, indicating potential drift or
    unauthorized changes.
    """

    feature_slug: str = Field(..., min_length=1, description="Feature identifier")
    local_parity_hash: str = Field(..., description="Local snapshot parity hash")
    baseline_parity_hash: str = Field(..., description="Baseline snapshot parity hash")
    missing_in_local: list[str] = Field(default_factory=list, description="Artifact keys missing in local")
    missing_in_baseline: list[str] = Field(default_factory=list, description="Artifact keys missing in baseline")
    severity: str = Field(..., description="'info' | 'warning' | 'error'")

    @field_validator("local_parity_hash", "baseline_parity_hash")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        """Validate SHA256 hex format."""
        if not re.match(r"^[a-f0-9]{64}$", v):
            raise ValueError(f"Invalid SHA256 hash: {v}")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """Validate severity enum."""
        if v not in {"info", "warning", "error"}:
            raise ValueError(f"Invalid severity: {v}")
        return v


# ── Event Emitter Helpers ─────────────────────────────────────────────


def emit_artifact_indexed(
    feature_slug: str,
    artifact_key: str,
    artifact_class: str,
    relative_path: str,
    content_hash_sha256: str,
    size_bytes: int,
    wp_id: Optional[str] = None,
    step_id: Optional[str] = None,
    required_status: str = "optional",
) -> dict[str, Any] | None:
    """Emit MissionDossierArtifactIndexed event.

    Args:
        feature_slug: Feature identifier
        artifact_key: Stable unique key for artifact
        artifact_class: Classification of artifact
        relative_path: Path relative to feature directory
        content_hash_sha256: SHA256 hash of artifact content
        size_bytes: File size in bytes
        wp_id: Work package ID if linked (optional)
        step_id: Mission step if step-specific (optional)
        required_status: 'required' or 'optional' from manifest

    Returns:
        Event dict on success (enqueued to OfflineQueue), None on failure
    """
    try:
        # Validate payload using Pydantic
        payload = MissionDossierArtifactIndexedPayload(
            feature_slug=feature_slug,
            artifact_key=artifact_key,
            artifact_class=artifact_class,
            relative_path=relative_path,
            content_hash_sha256=content_hash_sha256,
            size_bytes=size_bytes,
            wp_id=wp_id,
            step_id=step_id,
            required_status=required_status,
        )

        # Route via sync emitter API
        from specify_cli.sync.events import get_emitter

        emitter = get_emitter()
        event = emitter._emit(
            event_type="MissionDossierArtifactIndexed",
            aggregate_id=f"{feature_slug}:{artifact_key}",
            aggregate_type="MissionDossier",
            payload=payload.model_dump(),
        )
        return event

    except ValueError as e:
        logger.error(f"Payload validation failed for artifact_indexed: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to emit artifact_indexed event: {e}")
        return None


def emit_artifact_missing(
    feature_slug: str,
    artifact_key: str,
    artifact_class: str,
    expected_path_pattern: str,
    reason_code: str,
    reason_detail: Optional[str] = None,
    blocking: bool = True,
) -> dict[str, Any] | None:
    """Emit MissionDossierArtifactMissing event (only if required/blocking).

    Args:
        feature_slug: Feature identifier
        artifact_key: Stable unique key for artifact
        artifact_class: Classification of artifact
        expected_path_pattern: Expected path pattern or glob
        reason_code: Reason code ('not_found', 'unreadable', 'invalid_format', 'deleted_after_scan')
        reason_detail: Additional detail about reason (optional)
        blocking: True if blocks completeness

    Returns:
        Event dict on success (enqueued to OfflineQueue), None on failure or non-blocking
    """
    # Only emit if blocking/required
    if not blocking:
        logger.debug(f"Skipping optional artifact missing event for {artifact_key}")
        return None

    try:
        # Validate payload using Pydantic
        payload = MissionDossierArtifactMissingPayload(
            feature_slug=feature_slug,
            artifact_key=artifact_key,
            artifact_class=artifact_class,
            expected_path_pattern=expected_path_pattern,
            reason_code=reason_code,
            reason_detail=reason_detail,
            blocking=blocking,
        )

        # Route via sync emitter API
        from specify_cli.sync.events import get_emitter

        emitter = get_emitter()
        event = emitter._emit(
            event_type="MissionDossierArtifactMissing",
            aggregate_id=f"{feature_slug}:{artifact_key}",
            aggregate_type="MissionDossier",
            payload=payload.model_dump(),
        )
        return event

    except ValueError as e:
        logger.error(f"Payload validation failed for artifact_missing: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to emit artifact_missing event: {e}")
        return None


def emit_snapshot_computed(
    feature_slug: str,
    parity_hash_sha256: str,
    total_artifacts: int,
    required_artifacts: int,
    required_present: int,
    required_missing: int,
    optional_artifacts: int,
    optional_present: int,
    completeness_status: str,
    snapshot_id: str,
) -> dict[str, Any] | None:
    """Emit MissionDossierSnapshotComputed event (always).

    Args:
        feature_slug: Feature identifier
        parity_hash_sha256: Deterministic hash of entire snapshot
        total_artifacts: Total artifacts scanned
        required_artifacts: Required artifacts in manifest
        required_present: Required artifacts found
        required_missing: Required artifacts missing
        optional_artifacts: Optional artifacts in manifest
        optional_present: Optional artifacts found
        completeness_status: 'complete', 'incomplete', or 'unknown'
        snapshot_id: Unique snapshot identifier

    Returns:
        Event dict on success (enqueued to OfflineQueue), None on failure
    """
    try:
        # Validate payload using Pydantic
        payload = MissionDossierSnapshotComputedPayload(
            feature_slug=feature_slug,
            parity_hash_sha256=parity_hash_sha256,
            artifact_counts=ArtifactCountsPayload(
                total=total_artifacts,
                required=required_artifacts,
                required_present=required_present,
                required_missing=required_missing,
                optional=optional_artifacts,
                optional_present=optional_present,
            ),
            completeness_status=completeness_status,
            snapshot_id=snapshot_id,
        )

        # Route via sync emitter API
        from specify_cli.sync.events import get_emitter

        emitter = get_emitter()
        event = emitter._emit(
            event_type="MissionDossierSnapshotComputed",
            aggregate_id=f"{feature_slug}:{snapshot_id}",
            aggregate_type="MissionDossier",
            payload=payload.model_dump(),
        )
        return event

    except ValueError as e:
        logger.error(f"Payload validation failed for snapshot_computed: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to emit snapshot_computed event: {e}")
        return None


def emit_parity_drift_detected(
    feature_slug: str,
    local_parity_hash: str,
    baseline_parity_hash: str,
    missing_in_local: Optional[list[str]] = None,
    missing_in_baseline: Optional[list[str]] = None,
    severity: str = "warning",
) -> dict[str, Any] | None:
    """Emit MissionDossierParityDriftDetected event (only if drift detected).

    Args:
        feature_slug: Feature identifier
        local_parity_hash: Local snapshot parity hash
        baseline_parity_hash: Baseline snapshot parity hash
        missing_in_local: Artifact keys missing in local (optional)
        missing_in_baseline: Artifact keys missing in baseline (optional)
        severity: 'info', 'warning', or 'error'

    Returns:
        Event dict on success (enqueued to OfflineQueue), None if no drift or on failure
    """
    # Only emit if hashes differ (drift detected)
    if local_parity_hash == baseline_parity_hash:
        logger.debug(f"No parity drift detected for {feature_slug}")
        return None

    try:
        # Validate payload using Pydantic
        payload = MissionDossierParityDriftDetectedPayload(
            feature_slug=feature_slug,
            local_parity_hash=local_parity_hash,
            baseline_parity_hash=baseline_parity_hash,
            missing_in_local=missing_in_local or [],
            missing_in_baseline=missing_in_baseline or [],
            severity=severity,
        )

        # Route via sync emitter API
        from specify_cli.sync.events import get_emitter

        emitter = get_emitter()
        event = emitter._emit(
            event_type="MissionDossierParityDriftDetected",
            aggregate_id=f"{feature_slug}:drift",
            aggregate_type="MissionDossier",
            payload=payload.model_dump(),
        )
        return event

    except ValueError as e:
        logger.error(f"Payload validation failed for parity_drift_detected: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to emit parity_drift_detected event: {e}")
        return None
