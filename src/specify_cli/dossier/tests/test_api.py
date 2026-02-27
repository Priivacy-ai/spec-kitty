"""Tests for dossier REST API endpoints (WP06)."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.dossier.api import (
    ArtifactDetailResponse,
    ArtifactListItem,
    ArtifactListResponse,
    DossierAPIHandler,
    DossierOverviewResponse,
    SnapshotExportResponse,
    error_response,
    infer_media_type,
)
from specify_cli.dossier.models import ArtifactRef, MissionDossier, MissionDossierSnapshot


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def repo_root(tmp_path):
    """Create a temporary repo root."""
    return tmp_path


@pytest.fixture
def handler(repo_root):
    """Create a DossierAPIHandler instance."""
    return DossierAPIHandler(repo_root)


@pytest.fixture
def sample_artifacts():
    """Create sample ArtifactRef objects for testing."""
    return [
        ArtifactRef(
            artifact_key="input.spec.main",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256="a" * 64,
            size_bytes=1024,
            wp_id="WP01",
            step_id="planning",
            required_status="required",
            is_present=True,
            error_reason=None,
            indexed_at=datetime.utcnow(),
        ),
        ArtifactRef(
            artifact_key="output.tasks.per_wp",
            artifact_class="output",
            relative_path="tasks/WP01.md",
            content_hash_sha256="b" * 64,
            size_bytes=2048,
            wp_id="WP01",
            step_id="planning",
            required_status="required",
            is_present=True,
            error_reason=None,
            indexed_at=datetime.utcnow(),
        ),
        ArtifactRef(
            artifact_key="evidence.review.notes",
            artifact_class="evidence",
            relative_path=".kittify/review-notes.txt",
            content_hash_sha256="c" * 64,
            size_bytes=512,
            wp_id=None,
            step_id="review",
            required_status="optional",
            is_present=True,
            error_reason=None,
            indexed_at=datetime.utcnow(),
        ),
        ArtifactRef(
            artifact_key="policy.manifest",
            artifact_class="policy",
            relative_path="manifest.yaml",
            content_hash_sha256="d" * 64,
            size_bytes=256,
            wp_id=None,
            step_id=None,
            required_status="required",
            is_present=False,
            error_reason="not_found",
            indexed_at=datetime.utcnow(),
        ),
    ]


@pytest.fixture
def sample_dossier(sample_artifacts):
    """Create a sample MissionDossier."""
    return MissionDossier(
        mission_slug="software-dev",
        mission_run_id="test-run",
        feature_slug="042-local-mission-dossier",
        feature_dir="/tmp/kitty-specs/042-local-mission-dossier",
        artifacts=sample_artifacts,
        manifest={"required": ["input.spec.main", "output.tasks.per_wp", "policy.manifest"]},
        latest_snapshot=None,
        dossier_created_at=datetime.utcnow(),
        dossier_updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_snapshot():
    """Create a sample MissionDossierSnapshot."""
    return MissionDossierSnapshot(
        feature_slug="042-local-mission-dossier",
        snapshot_id="snap-001",
        total_artifacts=4,
        required_artifacts=3,
        required_present=2,
        required_missing=1,
        optional_artifacts=1,
        optional_present=1,
        completeness_status="incomplete",
        parity_hash_sha256="e" * 64,
        parity_hash_components=["a" * 64, "b" * 64, "c" * 64],
        artifact_summaries=[
            {"artifact_key": "input.spec.main", "artifact_class": "input"},
            {"artifact_key": "output.tasks.per_wp", "artifact_class": "output"},
            {"artifact_key": "evidence.review.notes", "artifact_class": "evidence"},
            {"artifact_key": "policy.manifest", "artifact_class": "policy"},
        ],
        computed_at=datetime.utcnow(),
    )


# ============================================================================
# Test: T028 - GET /api/dossier/overview
# ============================================================================


class TestDossierOverviewEndpoint:
    """Tests for GET /api/dossier/overview (T028)."""

    def test_overview_returns_valid_response(self, handler, sample_snapshot):
        """Test that overview returns DossierOverviewResponse with all fields."""
        with patch(
            "specify_cli.dossier.api.load_snapshot", return_value=sample_snapshot
        ):
            response = handler.handle_dossier_overview("042-local-mission-dossier")

            assert isinstance(response, DossierOverviewResponse)
            assert response.feature_slug == "042-local-mission-dossier"
            assert response.completeness_status == "incomplete"
            assert response.parity_hash_sha256 == "e" * 64
            assert response.missing_required_count == 1

    def test_overview_artifact_counts_correct(self, handler, sample_snapshot):
        """Test that artifact counts are correctly reported."""
        with patch(
            "specify_cli.dossier.api.load_snapshot", return_value=sample_snapshot
        ):
            response = handler.handle_dossier_overview("042-local-mission-dossier")

            assert response.artifact_counts["total"] == 4
            assert response.artifact_counts["required"] == 3
            assert response.artifact_counts["required_present"] == 2
            assert response.artifact_counts["required_missing"] == 1
            assert response.artifact_counts["optional"] == 1
            assert response.artifact_counts["optional_present"] == 1

    def test_overview_returns_404_if_not_found(self, handler):
        """Test that overview returns 404 error if dossier not found."""
        with patch("specify_cli.dossier.api.load_snapshot", return_value=None):
            response = handler.handle_dossier_overview("nonexistent-feature")

            assert isinstance(response, dict)
            assert response["status_code"] == 404
            assert "not found" in response["error"].lower()

    def test_overview_last_scanned_at_present(self, handler, sample_snapshot):
        """Test that last_scanned_at timestamp is included."""
        with patch(
            "specify_cli.dossier.api.load_snapshot", return_value=sample_snapshot
        ):
            response = handler.handle_dossier_overview("042-local-mission-dossier")

            assert response.last_scanned_at is not None
            assert isinstance(response.last_scanned_at, datetime)

    def test_overview_serializable_to_json(self, handler, sample_snapshot):
        """Test that overview response is JSON-serializable."""
        with patch(
            "specify_cli.dossier.api.load_snapshot", return_value=sample_snapshot
        ):
            response = handler.handle_dossier_overview("042-local-mission-dossier")

            # Should be serializable
            json_str = response.json()
            parsed = json.loads(json_str)

            assert parsed["feature_slug"] == "042-local-mission-dossier"
            assert parsed["completeness_status"] == "incomplete"


# ============================================================================
# Test: T029 - GET /api/dossier/artifacts
# ============================================================================


class TestDossierArtifactsEndpoint:
    """Tests for GET /api/dossier/artifacts (T029)."""

    def test_artifacts_returns_all_if_no_filters(self, handler, sample_dossier):
        """Test that all artifacts returned if no filters applied."""
        with patch.object(handler, "_load_dossier", return_value=sample_dossier):
            response = handler.handle_dossier_artifacts(
                "042-local-mission-dossier"
            )

            assert isinstance(response, ArtifactListResponse)
            assert response.total_count == 4
            assert response.filtered_count == 4
            assert len(response.artifacts) == 4

    def test_artifacts_filters_by_class(self, handler, sample_dossier):
        """Test that class filter works."""
        with patch.object(handler, "_load_dossier", return_value=sample_dossier):
            response = handler.handle_dossier_artifacts(
                "042-local-mission-dossier", **{"class": "output"}
            )

            assert response.filtered_count == 1
            assert len(response.artifacts) == 1
            assert response.artifacts[0].artifact_class == "output"

    def test_artifacts_filters_by_wp_id(self, handler, sample_dossier):
        """Test that wp_id filter works."""
        with patch.object(handler, "_load_dossier", return_value=sample_dossier):
            response = handler.handle_dossier_artifacts(
                "042-local-mission-dossier", wp_id="WP01"
            )

            assert response.filtered_count == 2
            for artifact in response.artifacts:
                assert artifact.wp_id == "WP01"

    def test_artifacts_filters_by_step_id(self, handler, sample_dossier):
        """Test that step_id filter works."""
        with patch.object(handler, "_load_dossier", return_value=sample_dossier):
            response = handler.handle_dossier_artifacts(
                "042-local-mission-dossier", step_id="planning"
            )

            assert response.filtered_count == 2
            for artifact in response.artifacts:
                assert artifact.step_id == "planning"

    def test_artifacts_filters_by_required_only(self, handler, sample_dossier):
        """Test that required_only filter works."""
        with patch.object(handler, "_load_dossier", return_value=sample_dossier):
            response = handler.handle_dossier_artifacts(
                "042-local-mission-dossier", required_only="true"
            )

            assert response.filtered_count == 3
            for artifact in response.artifacts:
                assert artifact.required_status == "required"

    def test_artifacts_combines_multiple_filters(self, handler, sample_dossier):
        """Test that multiple filters AND together."""
        with patch.object(handler, "_load_dossier", return_value=sample_dossier):
            response = handler.handle_dossier_artifacts(
                "042-local-mission-dossier",
                wp_id="WP01",
                step_id="planning",
            )

            assert response.filtered_count == 2
            for artifact in response.artifacts:
                assert artifact.wp_id == "WP01"
                assert artifact.step_id == "planning"

    def test_artifacts_stable_ordering(self, handler, sample_dossier):
        """Test that artifacts ordered by artifact_key (stable)."""
        with patch.object(handler, "_load_dossier", return_value=sample_dossier):
            response = handler.handle_dossier_artifacts(
                "042-local-mission-dossier"
            )

            keys = [a.artifact_key for a in response.artifacts]
            assert keys == sorted(keys)  # Lexicographic order

    def test_artifacts_returns_404_if_dossier_not_found(self, handler):
        """Test that 404 returned if dossier not found."""
        with patch.object(handler, "_load_dossier", return_value=None):
            response = handler.handle_dossier_artifacts(
                "nonexistent-feature"
            )

            assert isinstance(response, dict)
            assert response["status_code"] == 404

    def test_artifacts_filters_applied_in_response(self, handler, sample_dossier):
        """Test that filters_applied field populated."""
        with patch.object(handler, "_load_dossier", return_value=sample_dossier):
            response = handler.handle_dossier_artifacts(
                "042-local-mission-dossier",
                **{"class": "input", "wp_id": "WP01"}
            )

            assert "class" in response.filters_applied
            assert response.filters_applied["class"] == "input"
            assert response.filters_applied["wp_id"] == "WP01"


# ============================================================================
# Test: T030 - GET /api/dossier/artifacts/{artifact_key}
# ============================================================================


class TestDossierArtifactDetailEndpoint:
    """Tests for GET /api/dossier/artifacts/{artifact_key} (T030)."""

    def test_detail_returns_artifact_with_small_content(
        self, handler, sample_dossier, tmp_path
    ):
        """Test that detail returns content if <5MB."""
        # Set feature_dir to tmp_path
        sample_dossier.feature_dir = str(tmp_path)

        # Create small file
        artifact_file = tmp_path / "spec.md"
        artifact_file.write_text("# Specification\n\nThis is a test.")

        # Update artifact to point to real file
        sample_dossier.artifacts[0].relative_path = "spec.md"
        sample_dossier.artifacts[0].size_bytes = len(artifact_file.read_bytes())

        with patch.object(handler, "_load_dossier", return_value=sample_dossier):
            response = handler.handle_dossier_artifact_detail(
                "042-local-mission-dossier", "input.spec.main"
            )

            assert isinstance(response, ArtifactDetailResponse)
            assert response.artifact_key == "input.spec.main"
            assert response.content is not None
            assert "# Specification" in response.content
            assert response.content_truncated is False

    def test_detail_truncates_large_files(self, handler, sample_dossier):
        """Test that content not included for >5MB files."""
        sample_dossier.artifacts[0].size_bytes = 10 * 1024 * 1024  # 10MB

        with patch.object(handler, "_load_dossier", return_value=sample_dossier):
            response = handler.handle_dossier_artifact_detail(
                "042-local-mission-dossier", "input.spec.main"
            )

            assert response.content_truncated is True
            assert response.truncation_notice is not None
            assert "MB" in response.truncation_notice

    def test_detail_returns_404_if_artifact_not_found(self, handler, sample_dossier):
        """Test that 404 returned if artifact not found."""
        with patch.object(handler, "_load_dossier", return_value=sample_dossier):
            response = handler.handle_dossier_artifact_detail(
                "042-local-mission-dossier", "nonexistent.artifact"
            )

            assert isinstance(response, dict)
            assert response["status_code"] == 404

    def test_detail_infers_media_type(self, handler, sample_dossier):
        """Test that media_type_hint correctly inferred."""
        with patch.object(handler, "_load_dossier", return_value=sample_dossier):
            response = handler.handle_dossier_artifact_detail(
                "042-local-mission-dossier", "input.spec.main"
            )

            assert response.media_type_hint == "markdown"  # spec.md

    def test_detail_missing_artifact_has_no_content(self, handler, sample_dossier):
        """Test that missing artifacts have no content."""
        with patch.object(handler, "_load_dossier", return_value=sample_dossier):
            response = handler.handle_dossier_artifact_detail(
                "042-local-mission-dossier", "policy.manifest"
            )

            assert response.is_present is False
            assert response.content is None
            assert response.error_reason == "not_found"

    def test_detail_all_fields_present(self, handler, sample_dossier):
        """Test that all required fields present in response."""
        with patch.object(handler, "_load_dossier", return_value=sample_dossier):
            response = handler.handle_dossier_artifact_detail(
                "042-local-mission-dossier", "input.spec.main"
            )

            assert response.artifact_key is not None
            assert response.artifact_class is not None
            assert response.relative_path is not None
            assert response.size_bytes is not None
            assert response.required_status is not None
            assert response.is_present is not None
            assert response.content_truncated is not None
            assert response.media_type_hint is not None
            assert response.indexed_at is not None


# ============================================================================
# Test: T031 - GET /api/dossier/snapshots/export
# ============================================================================


class TestDossierSnapshotExportEndpoint:
    """Tests for GET /api/dossier/snapshots/export (T031)."""

    def test_export_returns_valid_snapshot(self, handler, sample_snapshot):
        """Test that export returns SnapshotExportResponse."""
        with patch(
            "specify_cli.dossier.api.load_snapshot", return_value=sample_snapshot
        ):
            response = handler.handle_dossier_snapshot_export(
                "042-local-mission-dossier"
            )

            assert isinstance(response, SnapshotExportResponse)
            assert response.feature_slug == "042-local-mission-dossier"
            assert response.snapshot_id == "snap-001"

    def test_export_all_fields_present(self, handler, sample_snapshot):
        """Test that all fields present for SaaS import."""
        with patch(
            "specify_cli.dossier.api.load_snapshot", return_value=sample_snapshot
        ):
            response = handler.handle_dossier_snapshot_export(
                "042-local-mission-dossier"
            )

            assert response.feature_slug is not None
            assert response.snapshot_id is not None
            assert response.total_artifacts is not None
            assert response.required_artifacts is not None
            assert response.required_present is not None
            assert response.required_missing is not None
            assert response.optional_artifacts is not None
            assert response.optional_present is not None
            assert response.completeness_status is not None
            assert response.parity_hash_sha256 is not None
            assert response.artifact_summaries is not None
            assert response.computed_at is not None

    def test_export_timestamp_iso_format(self, handler, sample_snapshot):
        """Test that computed_at is ISO format string."""
        with patch(
            "specify_cli.dossier.api.load_snapshot", return_value=sample_snapshot
        ):
            response = handler.handle_dossier_snapshot_export(
                "042-local-mission-dossier"
            )

            # Should be ISO string
            assert isinstance(response.computed_at, str)
            assert "T" in response.computed_at

    def test_export_returns_404_if_not_found(self, handler):
        """Test that 404 returned if snapshot not found."""
        with patch("specify_cli.dossier.api.load_snapshot", return_value=None):
            response = handler.handle_dossier_snapshot_export(
                "nonexistent-feature"
            )

            assert isinstance(response, dict)
            assert response["status_code"] == 404

    def test_export_serializable_to_json(self, handler, sample_snapshot):
        """Test that export response is JSON-serializable."""
        with patch(
            "specify_cli.dossier.api.load_snapshot", return_value=sample_snapshot
        ):
            response = handler.handle_dossier_snapshot_export(
                "042-local-mission-dossier"
            )

            # Should be serializable
            json_str = response.json()
            parsed = json.loads(json_str)

            assert parsed["feature_slug"] == "042-local-mission-dossier"
            assert parsed["snapshot_id"] == "snap-001"
            assert "2026-" in parsed["computed_at"]  # ISO timestamp


# ============================================================================
# Test: Utility Functions
# ============================================================================


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_error_response_format(self):
        """Test error_response creates correct format."""
        result = error_response("Test error", 400)

        assert isinstance(result, dict)
        assert result["error"] == "Test error"
        assert result["status_code"] == 400

    def test_infer_media_type_markdown(self):
        """Test media type inference for markdown."""
        assert infer_media_type("spec.md") == "markdown"
        assert infer_media_type("path/to/file.md") == "markdown"

    def test_infer_media_type_json(self):
        """Test media type inference for JSON."""
        assert infer_media_type("config.json") == "json"
        assert infer_media_type("path/to/data.json") == "json"

    def test_infer_media_type_yaml(self):
        """Test media type inference for YAML."""
        assert infer_media_type("config.yaml") == "yaml"
        assert infer_media_type("config.yml") == "yaml"
        assert infer_media_type("path/to/data.yml") == "yaml"

    def test_infer_media_type_text_default(self):
        """Test media type inference defaults to text."""
        assert infer_media_type("README") == "text"
        assert infer_media_type("file.txt") == "text"
        assert infer_media_type("unknown.xyz") == "text"


# ============================================================================
# Test: Adapter Protocol Compliance
# ============================================================================


class TestAdapterProtocol:
    """Tests for adapter protocol (T033)."""

    def test_handler_implements_adapter_interface(self, handler):
        """Test that DossierAPIHandler implements all adapter methods."""
        assert hasattr(handler, "handle_dossier_overview")
        assert hasattr(handler, "handle_dossier_artifacts")
        assert hasattr(handler, "handle_dossier_artifact_detail")
        assert hasattr(handler, "handle_dossier_snapshot_export")

    def test_all_methods_callable(self, handler):
        """Test that all methods are callable."""
        assert callable(handler.handle_dossier_overview)
        assert callable(handler.handle_dossier_artifacts)
        assert callable(handler.handle_dossier_artifact_detail)
        assert callable(handler.handle_dossier_snapshot_export)

    def test_methods_return_models_or_error_dicts(
        self, handler, sample_snapshot, sample_dossier
    ):
        """Test that all methods return models or error dicts."""
        # Overview
        with patch(
            "specify_cli.dossier.api.load_snapshot", return_value=sample_snapshot
        ):
            result = handler.handle_dossier_overview("042-local-mission-dossier")
            assert isinstance(result, (DossierOverviewResponse, dict))

        # Artifacts
        with patch.object(handler, "_load_dossier", return_value=sample_dossier):
            result = handler.handle_dossier_artifacts("042-local-mission-dossier")
            assert isinstance(result, (ArtifactListResponse, dict))

        # Artifact detail
        with patch.object(handler, "_load_dossier", return_value=sample_dossier):
            result = handler.handle_dossier_artifact_detail(
                "042-local-mission-dossier", "input.spec.main"
            )
            assert isinstance(result, (ArtifactDetailResponse, dict))

        # Snapshot export
        with patch(
            "specify_cli.dossier.api.load_snapshot", return_value=sample_snapshot
        ):
            result = handler.handle_dossier_snapshot_export(
                "042-local-mission-dossier"
            )
            assert isinstance(result, (SnapshotExportResponse, dict))
