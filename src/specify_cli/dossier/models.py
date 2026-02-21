"""Mission dossier data models for artifact indexing and parity detection.

This module defines core data structures for the mission dossier system,
including ArtifactRef (individual artifact metadata) and MissionDossier
(collection of indexed artifacts).

See: kitty-specs/042-local-mission-dossier-authority-parity-export/data-model.md
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class ArtifactRef(BaseModel):
    """Single artifact indexed in a dossier.

    Immutable reference to a mission artifact with deterministic content hash
    and comprehensive metadata for completeness tracking and parity detection.

    Attributes:
        artifact_key: Stable, unique key for this artifact (e.g., 'input.spec.main')
        artifact_class: Classification (input|workflow|output|evidence|policy|runtime|other)
        relative_path: Relative path from feature directory (e.g., 'spec.md', 'tasks/WP01.md')
        content_hash_sha256: SHA256 hash of artifact bytes (deterministic)
        size_bytes: File size in bytes
        wp_id: Work package ID if linked (e.g., 'WP01', None if not WP-specific)
        step_id: Mission step (e.g., 'planning', None if not step-specific)
        required_status: 'required' | 'optional' (from manifest)
        provenance: Source info {source_kind, actor_id, captured_at}
        is_present: True if file currently exists and readable
        error_reason: If not present: 'not_found'|'unreadable'|'invalid_format'|'deleted_after_scan'
        indexed_at: When this artifact was indexed (UTC)

    Uniqueness Constraint:
        (feature_slug, artifact_key) is unique per dossier
    """

    # Identity
    artifact_key: str = Field(
        ...,
        min_length=1,
        description="Stable, unique key for this artifact (e.g., 'input.spec.main', 'output.tasks.per_wp')",
    )
    artifact_class: str = Field(
        ...,
        description="Classification: input | workflow | output | evidence | policy | runtime | other",
    )

    # Location & Content
    relative_path: str = Field(
        ...,
        min_length=1,
        description="Relative path from feature directory (e.g., 'spec.md', 'tasks/WP01.md')",
    )
    content_hash_sha256: str = Field(
        ...,
        description="SHA256 hash of artifact bytes (deterministic)",
    )
    size_bytes: int = Field(
        ...,
        ge=0,
        description="File size in bytes",
    )

    # Metadata
    wp_id: Optional[str] = Field(
        None,
        description="Work package ID if linked (e.g., 'WP01', None if not WP-specific)",
    )
    step_id: Optional[str] = Field(
        None,
        description="Mission step (e.g., 'planning', 'implementation', None if not step-specific)",
    )
    required_status: str = Field(
        default="optional",
        description="'required' | 'optional' (from manifest)",
    )

    # Provenance
    provenance: Optional[dict] = Field(
        default=None,
        description="Source info: {source_kind: 'git'|'runtime'|'generated'|'manual', actor_id, captured_at}",
    )

    # State
    is_present: bool = Field(
        default=True,
        description="True if file currently exists and readable",
    )
    error_reason: Optional[str] = Field(
        None,
        description="If not present: 'not_found' | 'unreadable' | 'invalid_format' | 'deleted_after_scan'",
    )

    # Timestamps
    indexed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this artifact was indexed",
    )

    @validator("artifact_key")
    def validate_artifact_key(cls, v):
        """Validate artifact_key format (alphanumeric + dots/underscores)."""
        if not v:
            raise ValueError("artifact_key cannot be empty")
        # Allow alphanumeric, dots, underscores, hyphens
        import re
        if not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise ValueError(
                f"artifact_key must contain only alphanumeric characters, dots, underscores, and hyphens; got '{v}'"
            )
        return v

    @validator("artifact_class")
    def validate_artifact_class(cls, v):
        """Validate artifact_class is one of the allowed types."""
        allowed_classes = {
            "input",
            "workflow",
            "output",
            "evidence",
            "policy",
            "runtime",
            "other",
        }
        if v not in allowed_classes:
            raise ValueError(
                f"artifact_class must be one of {allowed_classes}; got '{v}'"
            )
        return v

    @validator("required_status")
    def validate_required_status(cls, v):
        """Validate required_status is 'required' or 'optional'."""
        allowed_values = {"required", "optional"}
        if v not in allowed_values:
            raise ValueError(
                f"required_status must be one of {allowed_values}; got '{v}'"
            )
        return v

    @validator("content_hash_sha256")
    def validate_content_hash_sha256(cls, v):
        """Validate content_hash_sha256 is a 64-character hex string (SHA256)."""
        if v is not None and v != "":
            if len(v) != 64:
                raise ValueError(
                    f"content_hash_sha256 must be 64 hex characters (SHA256); got {len(v)} characters"
                )
            try:
                int(v, 16)
            except ValueError:
                raise ValueError(
                    f"content_hash_sha256 must be valid hexadecimal; got '{v}'"
                )
        return v

    class Config:
        """Pydantic configuration for JSON serialization."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class MissionDossier(BaseModel):
    """Complete artifact inventory for a mission/feature.

    Collection of indexed artifacts with metadata, manifest information,
    and completeness tracking.

    Attributes:
        mission_slug: Mission type (e.g., 'software-dev')
        mission_run_id: UUID or feature run identifier
        feature_slug: Feature identifier (e.g., '042-local-mission-dossier')
        feature_dir: Absolute path to feature directory
        artifacts: All indexed artifacts
        manifest: Loaded manifest for this mission type (None if not found)
        latest_snapshot: Most recent snapshot (after all artifacts indexed)
        dossier_created_at: When dossier was created
        dossier_updated_at: When dossier was last updated
    """

    # Identity
    mission_slug: str = Field(
        ...,
        description="e.g., 'software-dev'",
    )
    mission_run_id: str = Field(
        ...,
        description="UUID or feature run identifier",
    )
    feature_slug: str = Field(
        ...,
        description="e.g., '042-local-mission-dossier'",
    )
    feature_dir: str = Field(
        ...,
        description="Absolute path to feature directory",
    )

    # Artifacts
    artifacts: List[ArtifactRef] = Field(
        default_factory=list,
        description="All indexed artifacts",
    )

    # Completeness (manifest from WP02)
    manifest: Optional[dict] = Field(
        None,
        description="Loaded manifest for this mission type (None if not found)",
    )

    # Snapshot (from WP05)
    latest_snapshot: Optional[dict] = Field(
        None,
        description="Most recent snapshot (after all artifacts indexed)",
    )

    # Timestamps
    dossier_created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When dossier was created",
    )
    dossier_updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When dossier was last updated",
    )

    def get_required_artifacts(self, step_id: Optional[str] = None) -> List[ArtifactRef]:
        """Return required artifacts for step (or all required if step_id=None).

        Args:
            step_id: Optional mission step to filter by

        Returns:
            List of artifacts with required_status='required'
        """
        required = [a for a in self.artifacts if a.required_status == "required"]
        if step_id:
            required = [a for a in required if a.step_id == step_id]
        return required

    def get_missing_required_artifacts(
        self, step_id: Optional[str] = None
    ) -> List[ArtifactRef]:
        """Return required artifacts that are not present.

        Args:
            step_id: Optional mission step to filter by

        Returns:
            List of required artifacts where is_present=False
        """
        required = self.get_required_artifacts(step_id)
        return [a for a in required if not a.is_present]

    @property
    def completeness_status(self) -> str:
        """Completeness status: 'complete', 'incomplete', or 'unknown'.

        Returns:
            'complete' if all required artifacts present
            'incomplete' if any required artifact missing
            'unknown' if no manifest available
        """
        if not self.manifest:
            return "unknown"  # No manifest, can't judge completeness
        missing = self.get_missing_required_artifacts()
        return "complete" if not missing else "incomplete"

    class Config:
        """Pydantic configuration for JSON serialization."""

        json_encoders = {datetime: lambda v: v.isoformat()}
