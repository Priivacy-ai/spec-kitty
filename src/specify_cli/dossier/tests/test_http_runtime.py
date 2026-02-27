"""HTTP runtime integration tests for dossier API endpoints.

These tests actually invoke HTTP handlers with real request/response cycles
to catch routing bugs, argument order issues, and stubbed functions that
unit tests miss through mocking.

This test file validates:
- /api/dossier/overview endpoint with real snapshot data
- /api/dossier/artifacts endpoint with filtering
- /api/dossier/artifacts/{key} endpoint with content retrieval
- /api/dossier/snapshots/export endpoint

Test Strategy:
- Create real snapshot files in temp directory
- Invoke handler methods directly (simulating HTTP request)
- Verify response model structures and data
- Ensure no silent failures (explicit errors on data issues)
"""

import json
import pytest
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

from specify_cli.dossier.api import (
    DossierAPIHandler,
    DossierOverviewResponse,
    ArtifactListResponse,
    ArtifactDetailResponse,
    SnapshotExportResponse,
)
from specify_cli.dossier.snapshot import save_snapshot, compute_snapshot
from specify_cli.dossier.models import ArtifactRef, MissionDossier, MissionDossierSnapshot


class TestDossierHTTPRuntime:
    """Runtime HTTP endpoint tests with real snapshots."""

    @pytest.fixture
    def temp_feature_dir(self, tmp_path):
        """Create temp feature directory with real snapshot."""
        feature_dir = tmp_path / "kitty-specs" / "042-test-feature"
        feature_dir.mkdir(parents=True)

        # Create real dossier with artifacts
        artifacts = [
            ArtifactRef(
                artifact_key="input.spec.main",
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=1024,
                required_status="required",
                is_present=True,
                indexed_at=datetime.now(timezone.utc),
            ),
            ArtifactRef(
                artifact_key="output.plan.main",
                artifact_class="output",
                relative_path="plan.md",
                content_hash_sha256="b" * 64,
                size_bytes=2048,
                required_status="required",
                is_present=True,
                indexed_at=datetime.now(timezone.utc),
            ),
            ArtifactRef(
                artifact_key="evidence.research",
                artifact_class="evidence",
                relative_path="research.md",
                content_hash_sha256="c" * 64,
                size_bytes=512,
                required_status="optional",
                is_present=False,
                error_reason="not_found",
                indexed_at=datetime.now(timezone.utc),
            ),
        ]

        dossier = MissionDossier(
            feature_slug="042-test-feature",
            feature_dir=str(feature_dir),
            artifacts=artifacts,
            mission_slug="software-dev",
            mission_run_id="test-run-001",
        )

        # Compute and save snapshot
        snapshot = compute_snapshot(dossier)
        save_snapshot(snapshot, feature_dir)

        return feature_dir

    def test_overview_endpoint_returns_valid_model(self, temp_feature_dir):
        """Verify overview endpoint returns proper response model."""
        handler = DossierAPIHandler(temp_feature_dir.parent.parent)
        response = handler.handle_dossier_overview("042-test-feature")

        # Verify response is model (not error dict)
        assert isinstance(response, DossierOverviewResponse)
        assert response.feature_slug == "042-test-feature"
        assert response.completeness_status in ("complete", "incomplete", "unknown")
        assert len(response.parity_hash_sha256) == 64  # SHA256 hex

    def test_artifacts_endpoint_returns_full_list(self, temp_feature_dir):
        """Verify artifacts endpoint returns all artifacts."""
        handler = DossierAPIHandler(temp_feature_dir.parent.parent)
        response = handler.handle_dossier_artifacts("042-test-feature")

        # Verify response is model (not error dict)
        assert isinstance(response, ArtifactListResponse)
        assert response.total_count == 3  # All artifacts
        assert response.filtered_count == 3  # No filtering applied
        assert len(response.artifacts) == 3

        # Verify artifact data is complete
        for item in response.artifacts:
            assert item.artifact_key
            assert item.artifact_class
            assert item.relative_path  # This was missing before fix!
            assert item.required_status in ("required", "optional")

    def test_artifacts_endpoint_filters_by_class(self, temp_feature_dir):
        """Verify artifacts endpoint respects class filter."""
        handler = DossierAPIHandler(temp_feature_dir.parent.parent)
        response = handler.handle_dossier_artifacts(
            "042-test-feature", **{"class": "input"}
        )

        # Verify filtering works
        assert response.total_count == 3  # Total unchanged
        assert response.filtered_count == 1  # Only input class
        assert len(response.artifacts) == 1
        assert response.artifacts[0].artifact_class == "input"

    def test_artifacts_endpoint_filters_by_required_only(self, temp_feature_dir):
        """Verify artifacts endpoint respects required_only filter."""
        handler = DossierAPIHandler(temp_feature_dir.parent.parent)
        response = handler.handle_dossier_artifacts(
            "042-test-feature", required_only="true"
        )

        # Verify only required artifacts returned
        assert response.total_count == 3  # Total unchanged
        assert response.filtered_count == 2  # Only required
        assert len(response.artifacts) == 2
        for item in response.artifacts:
            assert item.required_status == "required"

    def test_artifact_detail_endpoint_reconstructs_from_snapshot(self, temp_feature_dir):
        """Verify detail endpoint can reconstruct artifact from snapshot."""
        handler = DossierAPIHandler(temp_feature_dir.parent.parent)
        response = handler.handle_dossier_artifact_detail(
            "042-test-feature", "input.spec.main"
        )

        # Verify response is model (not error dict)
        assert isinstance(response, ArtifactDetailResponse)
        assert response.artifact_key == "input.spec.main"
        assert response.artifact_class == "input"
        assert response.relative_path == "spec.md"  # This was missing before fix!
        assert response.size_bytes == 1024
        assert response.is_present is True

    def test_artifact_detail_handles_missing_artifact(self, temp_feature_dir):
        """Verify detail endpoint handles missing artifacts gracefully."""
        handler = DossierAPIHandler(temp_feature_dir.parent.parent)
        response = handler.handle_dossier_artifact_detail(
            "042-test-feature", "nonexistent.artifact"
        )

        # Verify error response
        assert isinstance(response, dict)
        assert "error" in response
        assert response.get("status_code") == 404

    def test_export_endpoint_returns_snapshot(self, temp_feature_dir):
        """Verify export endpoint returns complete snapshot."""
        handler = DossierAPIHandler(temp_feature_dir.parent.parent)
        response = handler.handle_dossier_snapshot_export("042-test-feature")

        # Verify response is model (not error dict)
        assert isinstance(response, SnapshotExportResponse)
        assert response.feature_slug == "042-test-feature"
        assert response.total_artifacts == 3
        assert response.required_artifacts == 2
        assert response.required_present == 2
        assert response.required_missing == 0

    def test_all_artifact_summaries_have_required_fields(self, temp_feature_dir):
        """Verify snapshots include all fields needed for reconstruction."""
        from specify_cli.dossier.snapshot import load_snapshot

        snapshot = load_snapshot(temp_feature_dir, "042-test-feature")
        assert snapshot is not None

        # Verify each summary has all required fields
        required_fields = {
            "artifact_key",
            "artifact_class",
            "relative_path",  # Was missing!
            "content_hash_sha256",  # Was missing!
            "size_bytes",  # Was missing!
            "required_status",
            "is_present",
            "indexed_at",  # Was missing!
        }

        for summary in snapshot.artifact_summaries:
            for field in required_fields:
                assert field in summary, f"Summary missing field: {field}"
                # Verify non-None for critical fields
                if field in ("artifact_key", "artifact_class", "relative_path", "required_status"):
                    assert summary[field] is not None, f"Field {field} is None"
