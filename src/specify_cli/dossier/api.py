"""Dossier REST API endpoints for dashboard access.

This module provides REST endpoints for accessing mission dossier data:
- GET /api/dossier/overview - High-level summary (completeness, counts, parity hash)
- GET /api/dossier/artifacts - List artifacts with filtering and stable ordering
- GET /api/dossier/artifacts/{artifact_key} - Detail view with full content (if <5MB)
- GET /api/dossier/snapshots/export - Snapshot JSON for SaaS import

Implements adapter pattern for future FastAPI migration (T033).

See: kitty-specs/042-local-mission-dossier-authority-parity-export/tasks/WP06-api-endpoints.md
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .models import ArtifactRef, MissionDossier, MissionDossierSnapshot
from .snapshot import load_snapshot

__all__ = [
    "DossierOverviewResponse",
    "ArtifactListItem",
    "ArtifactListResponse",
    "ArtifactDetailResponse",
    "SnapshotExportResponse",
    "DossierHandlerAdapter",
    "DossierAPIHandler",
]


# ============================================================================
# Response Models
# ============================================================================


class DossierOverviewResponse(BaseModel):
    """High-level dossier summary (completeness, counts, hashes)."""

    feature_slug: str = Field(
        ..., description="Feature identifier (e.g., '042-local-mission-dossier')"
    )
    completeness_status: str = Field(
        ..., description="'complete' | 'incomplete' | 'unknown'"
    )
    parity_hash_sha256: str = Field(
        ..., description="SHA256 hash of sorted artifact hashes"
    )
    artifact_counts: Dict[str, int] = Field(
        ...,
        description="Artifact counts: {total, required, required_present, required_missing, optional, optional_present}",
    )
    missing_required_count: int = Field(
        ..., description="Number of required artifacts that are missing"
    )
    last_scanned_at: Optional[datetime] = Field(
        None, description="When the dossier was last scanned"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ArtifactListItem(BaseModel):
    """Summary of a single artifact in list view."""

    artifact_key: str = Field(
        ..., description="Stable, unique key for this artifact"
    )
    artifact_class: str = Field(
        ..., description="Classification: input|workflow|output|evidence|policy|runtime|other"
    )
    relative_path: str = Field(
        ..., description="Relative path from feature directory"
    )
    size_bytes: int = Field(..., description="File size in bytes")
    wp_id: Optional[str] = Field(
        None, description="Work package ID if linked (e.g., 'WP01')"
    )
    step_id: Optional[str] = Field(
        None, description="Mission step (e.g., 'planning')"
    )
    required_status: str = Field(
        ..., description="'required' | 'optional' (from manifest)"
    )
    is_present: bool = Field(..., description="True if file currently exists")
    error_reason: Optional[str] = Field(
        None, description="Error reason if not present"
    )


class ArtifactListResponse(BaseModel):
    """List of artifacts with filtering metadata."""

    total_count: int = Field(..., description="Total number of artifacts")
    filtered_count: int = Field(..., description="Number of artifacts after filtering")
    artifacts: List[ArtifactListItem] = Field(..., description="Filtered artifact list")
    filters_applied: Dict[str, Any] = Field(
        ..., description="Filters applied: {class, wp_id, step_id, required_only}"
    )


class ArtifactDetailResponse(BaseModel):
    """Detailed view of a single artifact with full content."""

    artifact_key: str = Field(..., description="Stable, unique key")
    artifact_class: str = Field(..., description="Classification")
    relative_path: str = Field(..., description="Relative path from feature directory")
    content_hash_sha256: Optional[str] = Field(
        None, description="SHA256 hash of content"
    )
    size_bytes: int = Field(..., description="File size in bytes")
    wp_id: Optional[str] = Field(None, description="Work package ID if linked")
    step_id: Optional[str] = Field(None, description="Mission step")
    required_status: str = Field(
        ..., description="'required' | 'optional' (from manifest)"
    )
    is_present: bool = Field(..., description="True if file exists")
    error_reason: Optional[str] = Field(None, description="Error reason if not present")
    content: Optional[str] = Field(
        None, description="Full text content (if <5MB and readable)"
    )
    content_truncated: bool = Field(
        ..., description="True if content was truncated"
    )
    truncation_notice: Optional[str] = Field(
        None, description="Explanation if content truncated or unreadable"
    )
    media_type_hint: str = Field(
        ..., description="'markdown' | 'json' | 'yaml' | 'text'"
    )
    indexed_at: datetime = Field(..., description="When artifact was indexed")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SnapshotExportResponse(BaseModel):
    """Snapshot JSON for SaaS import."""

    feature_slug: str = Field(..., description="Feature identifier")
    snapshot_id: str = Field(..., description="Unique snapshot ID (UUID)")
    total_artifacts: int = Field(..., description="Total number of artifacts")
    required_artifacts: int = Field(..., description="Count of required artifacts")
    required_present: int = Field(..., description="Count of present required artifacts")
    required_missing: int = Field(..., description="Count of missing required artifacts")
    optional_artifacts: int = Field(..., description="Count of optional artifacts")
    optional_present: int = Field(..., description="Count of present optional artifacts")
    completeness_status: str = Field(..., description="'complete'|'incomplete'|'unknown'")
    parity_hash_sha256: str = Field(..., description="SHA256 parity hash")
    artifact_summaries: List[Dict[str, Any]] = Field(
        ..., description="Artifact metadata summaries"
    )
    computed_at: str = Field(..., description="ISO timestamp when snapshot was computed")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============================================================================
# Adapter Protocol (for future FastAPI migration)
# ============================================================================


class DossierHandlerAdapter:
    """Interface/protocol for dossier handlers (HTTP-framework agnostic).

    Enables future FastAPI migration: FastAPI routes will wrap these methods.

    All methods return pydantic models (serializable to JSON).
    Error handling: Return error_response or raise (framework-dependent).
    """

    def handle_dossier_overview(
        self, feature_slug: str
    ) -> DossierOverviewResponse | Dict[str, Any]:
        """GET /api/dossier/overview?feature={feature_slug}

        Returns:
            DossierOverviewResponse or error dict
        """
        raise NotImplementedError

    def handle_dossier_artifacts(
        self, feature_slug: str, **filters
    ) -> ArtifactListResponse | Dict[str, Any]:
        """GET /api/dossier/artifacts?feature={feature_slug}&class=...&wp_id=...&step_id=...&required_only=...

        Returns:
            ArtifactListResponse or error dict
        """
        raise NotImplementedError

    def handle_dossier_artifact_detail(
        self, feature_slug: str, artifact_key: str
    ) -> ArtifactDetailResponse | Dict[str, Any]:
        """GET /api/dossier/artifacts/{artifact_key}

        Returns:
            ArtifactDetailResponse or error dict
        """
        raise NotImplementedError

    def handle_dossier_snapshot_export(
        self, feature_slug: str
    ) -> SnapshotExportResponse | Dict[str, Any]:
        """GET /api/dossier/snapshots/export?feature={feature_slug}

        Returns:
            SnapshotExportResponse or error dict (SaaS import-compatible)
        """
        raise NotImplementedError


# ============================================================================
# Handler Implementation
# ============================================================================


def error_response(message: str, status_code: int) -> Dict[str, Any]:
    """Create a standardized error response.

    Args:
        message: Error description
        status_code: HTTP status code

    Returns:
        Error dict with status_code and message
    """
    return {"error": message, "status_code": status_code}


def infer_media_type(file_path: str) -> str:
    """Infer media type from file extension.

    Args:
        file_path: File path (relative or absolute)

    Returns:
        Media type hint: 'markdown' | 'json' | 'yaml' | 'text'
    """
    ext = Path(file_path).suffix.lower()
    if ext in [".md"]:
        return "markdown"
    if ext in [".json"]:
        return "json"
    if ext in [".yaml", ".yml"]:
        return "yaml"
    return "text"


class DossierAPIHandler(DossierHandlerAdapter):
    """Implement dossier API endpoints.

    Integrates with existing dashboard HTTPServer handler pattern.
    All methods are pure functions: no HTTP context, only return models.
    """

    def __init__(self, repo_root: Path):
        """Initialize handler with repo root.

        Args:
            repo_root: Root of the spec-kitty repository
        """
        self.repo_root = Path(repo_root)

    def handle_dossier_overview(
        self, feature_slug: str
    ) -> DossierOverviewResponse | Dict[str, Any]:
        """Return high-level dossier summary.

        Args:
            feature_slug: Feature identifier

        Returns:
            DossierOverviewResponse or error dict
        """
        try:
            # Load snapshot
            feature_dir = (
                self.repo_root / "kitty-specs" / feature_slug
            )
            snapshot = load_snapshot(feature_slug, feature_dir)

            if not snapshot:
                return error_response(f"Dossier not found for {feature_slug}", 404)

            return DossierOverviewResponse(
                feature_slug=feature_slug,
                completeness_status=snapshot.completeness_status,
                parity_hash_sha256=snapshot.parity_hash_sha256,
                artifact_counts={
                    "total": snapshot.total_artifacts,
                    "required": snapshot.required_artifacts,
                    "required_present": snapshot.required_present,
                    "required_missing": snapshot.required_missing,
                    "optional": snapshot.optional_artifacts,
                    "optional_present": snapshot.optional_present,
                },
                missing_required_count=snapshot.required_missing,
                last_scanned_at=snapshot.computed_at,
            )
        except Exception as exc:
            return error_response(f"Error loading overview: {str(exc)}", 500)

    def handle_dossier_artifacts(
        self, feature_slug: str, **filters
    ) -> ArtifactListResponse | Dict[str, Any]:
        """List all artifacts with filtering and stable ordering.

        Filters:
        - class: One of {input, workflow, output, evidence, policy, runtime}
        - wp_id: Exact match (e.g., "WP01")
        - step_id: Exact match (e.g., "plan")
        - required_only: Boolean (true/false)

        Args:
            feature_slug: Feature identifier
            **filters: Optional filtering parameters

        Returns:
            ArtifactListResponse or error dict
        """
        try:
            # Load dossier (not implemented yet - placeholder)
            # For now, return empty list with full filters applied
            dossier = self._load_dossier(feature_slug)

            if not dossier:
                return error_response(f"Dossier not found for {feature_slug}", 404)

            # Apply filters
            filtered_artifacts = dossier.artifacts

            # Filter by class
            if "class" in filters:
                filtered_artifacts = [
                    a
                    for a in filtered_artifacts
                    if a.artifact_class == filters["class"]
                ]

            # Filter by wp_id
            if "wp_id" in filters:
                filtered_artifacts = [
                    a for a in filtered_artifacts if a.wp_id == filters["wp_id"]
                ]

            # Filter by step_id
            if "step_id" in filters:
                filtered_artifacts = [
                    a for a in filtered_artifacts if a.step_id == filters["step_id"]
                ]

            # Filter by required_only
            if filters.get("required_only") == "true":
                filtered_artifacts = [
                    a
                    for a in filtered_artifacts
                    if a.required_status == "required"
                ]

            # Sort by artifact_key (stable ordering)
            filtered_artifacts = sorted(
                filtered_artifacts, key=lambda a: a.artifact_key
            )

            # Build response
            return ArtifactListResponse(
                total_count=len(dossier.artifacts),
                filtered_count=len(filtered_artifacts),
                artifacts=[
                    ArtifactListItem(
                        artifact_key=a.artifact_key,
                        artifact_class=a.artifact_class,
                        relative_path=a.relative_path,
                        size_bytes=a.size_bytes,
                        wp_id=a.wp_id,
                        step_id=a.step_id,
                        required_status=a.required_status,
                        is_present=a.is_present,
                        error_reason=a.error_reason,
                    )
                    for a in filtered_artifacts
                ],
                filters_applied=filters,
            )
        except Exception as exc:
            return error_response(f"Error listing artifacts: {str(exc)}", 500)

    def handle_dossier_artifact_detail(
        self, feature_slug: str, artifact_key: str
    ) -> ArtifactDetailResponse | Dict[str, Any]:
        """Return artifact detail with full-text content (or truncation notice).

        Args:
            feature_slug: Feature identifier
            artifact_key: Artifact key (e.g., 'input.spec.main')

        Returns:
            ArtifactDetailResponse or error dict
        """
        try:
            dossier = self._load_dossier(feature_slug)

            if not dossier:
                return error_response(f"Dossier not found for {feature_slug}", 404)

            # Find artifact
            artifact = None
            for a in dossier.artifacts:
                if a.artifact_key == artifact_key:
                    artifact = a
                    break

            if not artifact:
                return error_response(f"Artifact {artifact_key} not found", 404)

            # Load full content if present and <5MB (5242880 bytes)
            content = None
            content_truncated = False
            truncation_notice = None

            if artifact.is_present:
                file_path = Path(dossier.feature_dir) / artifact.relative_path
                if artifact.size_bytes < 5242880:  # 5MB threshold
                    try:
                        content = file_path.read_text(encoding="utf-8")
                    except Exception as exc:
                        truncation_notice = f"Could not read: {str(exc)}"
                else:
                    content_truncated = True
                    truncation_notice = f"File {artifact.size_bytes / 1024 / 1024:.1f}MB, content not included"

            # Media type hint
            media_type_hint = infer_media_type(artifact.relative_path)

            return ArtifactDetailResponse(
                artifact_key=artifact.artifact_key,
                artifact_class=artifact.artifact_class,
                relative_path=artifact.relative_path,
                content_hash_sha256=artifact.content_hash_sha256,
                size_bytes=artifact.size_bytes,
                wp_id=artifact.wp_id,
                step_id=artifact.step_id,
                required_status=artifact.required_status,
                is_present=artifact.is_present,
                error_reason=artifact.error_reason,
                content=content,
                content_truncated=content_truncated,
                truncation_notice=truncation_notice,
                media_type_hint=media_type_hint,
                indexed_at=artifact.indexed_at,
            )
        except Exception as exc:
            return error_response(f"Error loading artifact detail: {str(exc)}", 500)

    def handle_dossier_snapshot_export(
        self, feature_slug: str
    ) -> SnapshotExportResponse | Dict[str, Any]:
        """Export snapshot JSON for SaaS import.

        Args:
            feature_slug: Feature identifier

        Returns:
            SnapshotExportResponse or error dict (SaaS import-compatible)
        """
        try:
            feature_dir = (
                self.repo_root / "kitty-specs" / feature_slug
            )
            snapshot = load_snapshot(feature_slug, feature_dir)

            if not snapshot:
                return error_response(f"Snapshot not found for {feature_slug}", 404)

            return SnapshotExportResponse(
                feature_slug=snapshot.feature_slug,
                snapshot_id=snapshot.snapshot_id,
                total_artifacts=snapshot.total_artifacts,
                required_artifacts=snapshot.required_artifacts,
                required_present=snapshot.required_present,
                required_missing=snapshot.required_missing,
                optional_artifacts=snapshot.optional_artifacts,
                optional_present=snapshot.optional_present,
                completeness_status=snapshot.completeness_status,
                parity_hash_sha256=snapshot.parity_hash_sha256,
                artifact_summaries=snapshot.artifact_summaries,
                computed_at=snapshot.computed_at.isoformat(),
            )
        except Exception as exc:
            return error_response(f"Error exporting snapshot: {str(exc)}", 500)

    def _load_dossier(self, feature_slug: str) -> Optional[MissionDossier]:
        """Load dossier for a feature (placeholder).

        This is a placeholder - actual implementation will load from
        dossier storage (.kittify/dossiers/{feature_slug}/dossier.json).

        Args:
            feature_slug: Feature identifier

        Returns:
            MissionDossier or None if not found
        """
        # TODO: Implement actual dossier loading from storage
        # For now, return None to indicate not found
        return None
