"""Unit tests for ArtifactRef model validation and serialization.

Tests cover:
- Field validation (required fields, format validation)
- ArtifactRef serialization to/from JSON
- Error handling for malformed inputs
- Edge cases (empty values, boundary conditions)
"""

import json
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from specify_cli.dossier.models import ArtifactRef, MissionDossier


class TestArtifactRefValidation:
    """Test ArtifactRef field validation."""

    def test_create_valid_artifact_ref(self):
        """Create ArtifactRef with all required fields present."""
        artifact = ArtifactRef(
            artifact_key="input.spec.main",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256="a" * 64,
            size_bytes=1024,
        )
        assert artifact.artifact_key == "input.spec.main"
        assert artifact.artifact_class == "input"
        assert artifact.relative_path == "spec.md"
        assert artifact.content_hash_sha256 == "a" * 64
        assert artifact.size_bytes == 1024
        assert artifact.is_present is True
        assert artifact.error_reason is None

    def test_artifact_key_required(self):
        """artifact_key is required, cannot be None."""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactRef(
                artifact_key=None,
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=1024,
            )
        errors = exc_info.value.errors()
        assert any("artifact_key" in str(e) for e in errors)

    def test_artifact_key_cannot_be_empty(self):
        """artifact_key cannot be empty string."""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactRef(
                artifact_key="",
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=1024,
            )
        errors = exc_info.value.errors()
        assert any("artifact_key" in str(e) for e in errors)

    def test_artifact_key_format_valid(self):
        """artifact_key allows alphanumeric, dots, underscores, hyphens."""
        valid_keys = [
            "simple",
            "with.dots",
            "with_underscores",
            "with-hyphens",
            "complex.name_with-all-chars",
            "123numeric",
        ]
        for key in valid_keys:
            artifact = ArtifactRef(
                artifact_key=key,
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=1024,
            )
            assert artifact.artifact_key == key

    def test_artifact_key_format_invalid(self):
        """artifact_key rejects invalid characters."""
        invalid_keys = [
            "with space",
            "with@symbol",
            "with/slash",
            "with\\backslash",
            "with$dollar",
            "with#hash",
        ]
        for key in invalid_keys:
            with pytest.raises(ValidationError) as exc_info:
                ArtifactRef(
                    artifact_key=key,
                    artifact_class="input",
                    relative_path="spec.md",
                    content_hash_sha256="a" * 64,
                    size_bytes=1024,
                )
            errors = exc_info.value.errors()
            assert any("artifact_key" in str(e) for e in errors)

    def test_artifact_class_required(self):
        """artifact_class is required."""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactRef(
                artifact_key="test",
                artifact_class=None,
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=1024,
            )
        errors = exc_info.value.errors()
        assert any("artifact_class" in str(e) for e in errors)

    def test_artifact_class_valid_values(self):
        """artifact_class accepts all allowed values."""
        valid_classes = [
            "input",
            "workflow",
            "output",
            "evidence",
            "policy",
            "runtime",
            "other",
        ]
        for cls in valid_classes:
            artifact = ArtifactRef(
                artifact_key="test",
                artifact_class=cls,
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=1024,
            )
            assert artifact.artifact_class == cls

    def test_artifact_class_invalid_value(self):
        """artifact_class rejects unknown values."""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactRef(
                artifact_key="test",
                artifact_class="unknown",
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=1024,
            )
        errors = exc_info.value.errors()
        assert any("artifact_class" in str(e) for e in errors)

    def test_relative_path_required(self):
        """relative_path is required."""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactRef(
                artifact_key="test",
                artifact_class="input",
                relative_path=None,
                content_hash_sha256="a" * 64,
                size_bytes=1024,
            )
        errors = exc_info.value.errors()
        assert any("relative_path" in str(e) for e in errors)

    def test_content_hash_sha256_required(self):
        """content_hash_sha256 is required and must be 64 hex chars."""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactRef(
                artifact_key="test",
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256=None,
                size_bytes=1024,
            )
        errors = exc_info.value.errors()
        assert any("content_hash_sha256" in str(e) for e in errors)

    def test_content_hash_sha256_must_be_64_chars(self):
        """content_hash_sha256 must be exactly 64 hex characters."""
        invalid_hashes = [
            "a" * 63,  # Too short
            "a" * 65,  # Too long
            "short",  # Way too short
        ]
        for hash_val in invalid_hashes:
            with pytest.raises(ValidationError) as exc_info:
                ArtifactRef(
                    artifact_key="test",
                    artifact_class="input",
                    relative_path="spec.md",
                    content_hash_sha256=hash_val,
                    size_bytes=1024,
                )
            errors = exc_info.value.errors()
            assert any("content_hash_sha256" in str(e) for e in errors)

    def test_content_hash_sha256_must_be_hex(self):
        """content_hash_sha256 must be valid hexadecimal."""
        invalid_hashes = [
            "g" * 64,  # Invalid hex (g is not hex)
            "z" * 64,  # Invalid hex (z is not hex)
            " " * 64,  # Spaces not hex
        ]
        for hash_val in invalid_hashes:
            with pytest.raises(ValidationError) as exc_info:
                ArtifactRef(
                    artifact_key="test",
                    artifact_class="input",
                    relative_path="spec.md",
                    content_hash_sha256=hash_val,
                    size_bytes=1024,
                )
            errors = exc_info.value.errors()
            assert any("content_hash_sha256" in str(e) for e in errors)

    def test_content_hash_sha256_valid_formats(self):
        """content_hash_sha256 accepts valid 64-char hex strings."""
        valid_hashes = [
            "a" * 64,  # All lowercase a
            "0" * 64,  # All zeros
            "f" * 64,  # All lowercase f
            "abcdef0123456789" * 4,  # Mixed valid hex
        ]
        for hash_val in valid_hashes:
            artifact = ArtifactRef(
                artifact_key="test",
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256=hash_val,
                size_bytes=1024,
            )
            assert artifact.content_hash_sha256 == hash_val

    def test_size_bytes_required(self):
        """size_bytes is required."""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactRef(
                artifact_key="test",
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=None,
            )
        errors = exc_info.value.errors()
        assert any("size_bytes" in str(e) for e in errors)

    def test_size_bytes_must_be_non_negative(self):
        """size_bytes must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactRef(
                artifact_key="test",
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=-1,
            )
        errors = exc_info.value.errors()
        assert any("size_bytes" in str(e) for e in errors)

    def test_size_bytes_valid_values(self):
        """size_bytes accepts zero and positive values."""
        valid_sizes = [0, 1, 1024, 1048576, 999999999999]
        for size in valid_sizes:
            artifact = ArtifactRef(
                artifact_key="test",
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=size,
            )
            assert artifact.size_bytes == size

    def test_required_status_valid_values(self):
        """required_status accepts 'required' and 'optional'."""
        for status in ["required", "optional"]:
            artifact = ArtifactRef(
                artifact_key="test",
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=1024,
                required_status=status,
            )
            assert artifact.required_status == status

    def test_required_status_invalid_value(self):
        """required_status rejects invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactRef(
                artifact_key="test",
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=1024,
                required_status="invalid",
            )
        errors = exc_info.value.errors()
        assert any("required_status" in str(e) for e in errors)

    def test_optional_fields(self):
        """Optional fields (wp_id, step_id, provenance) can be None."""
        artifact = ArtifactRef(
            artifact_key="test",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256="a" * 64,
            size_bytes=1024,
            wp_id=None,
            step_id=None,
            provenance=None,
        )
        assert artifact.wp_id is None
        assert artifact.step_id is None
        assert artifact.provenance is None

    def test_optional_fields_with_values(self):
        """Optional fields can have values."""
        provenance = {
            "source_kind": "git",
            "actor_id": "agent-1",
            "captured_at": "2026-02-21T12:00:00Z",
        }
        artifact = ArtifactRef(
            artifact_key="test",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256="a" * 64,
            size_bytes=1024,
            wp_id="WP01",
            step_id="planning",
            provenance=provenance,
        )
        assert artifact.wp_id == "WP01"
        assert artifact.step_id == "planning"
        assert artifact.provenance == provenance


class TestArtifactRefSerialization:
    """Test ArtifactRef JSON serialization and deserialization."""

    def test_serialize_to_json(self):
        """ArtifactRef serializes to JSON with datetime handling."""
        artifact = ArtifactRef(
            artifact_key="test.key",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256="a" * 64,
            size_bytes=1024,
            wp_id="WP01",
            required_status="required",
        )
        # Use json_compatible approach for testing
        json_data = json.loads(artifact.json())
        assert json_data["artifact_key"] == "test.key"
        assert json_data["artifact_class"] == "input"
        assert json_data["relative_path"] == "spec.md"
        assert json_data["content_hash_sha256"] == "a" * 64
        assert json_data["size_bytes"] == 1024
        assert json_data["wp_id"] == "WP01"
        assert json_data["required_status"] == "required"

    def test_serialize_deserialize_roundtrip(self):
        """Serialize ArtifactRef to JSON and deserialize back to object."""
        original = ArtifactRef(
            artifact_key="test.key",
            artifact_class="output",
            relative_path="output/results.json",
            content_hash_sha256="b" * 64,
            size_bytes=2048,
            wp_id="WP02",
            step_id="implementation",
            required_status="optional",
            is_present=True,
            error_reason=None,
        )
        # Serialize to JSON
        json_str = original.json()

        # Deserialize back
        restored = ArtifactRef.parse_raw(json_str)

        # Verify all fields match
        assert restored.artifact_key == original.artifact_key
        assert restored.artifact_class == original.artifact_class
        assert restored.relative_path == original.relative_path
        assert restored.content_hash_sha256 == original.content_hash_sha256
        assert restored.size_bytes == original.size_bytes
        assert restored.wp_id == original.wp_id
        assert restored.step_id == original.step_id
        assert restored.required_status == original.required_status
        assert restored.is_present == original.is_present
        assert restored.error_reason == original.error_reason

    def test_datetime_serialization(self):
        """Datetime fields serialize to ISO format."""
        now = datetime.now(timezone.utc)
        artifact = ArtifactRef(
            artifact_key="test",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256="a" * 64,
            size_bytes=1024,
            indexed_at=now,
        )
        json_data = json.loads(artifact.json())
        # Should be ISO format
        assert isinstance(json_data["indexed_at"], str)
        assert "T" in json_data["indexed_at"]  # ISO datetime format

    def test_default_values(self):
        """Test default values for optional fields."""
        artifact = ArtifactRef(
            artifact_key="test",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256="a" * 64,
            size_bytes=1024,
        )
        # Defaults
        assert artifact.required_status == "optional"
        assert artifact.is_present is True
        assert artifact.error_reason is None
        assert artifact.wp_id is None
        assert artifact.step_id is None
        assert artifact.provenance is None
        # indexed_at should be automatically set
        assert artifact.indexed_at is not None
        assert isinstance(artifact.indexed_at, datetime)


class TestMissionDossier:
    """Test MissionDossier model."""

    def test_create_empty_dossier(self):
        """Create MissionDossier with minimal fields."""
        dossier = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="run-001",
            feature_slug="042-dossier",
            feature_dir="/path/to/feature",
        )
        assert dossier.mission_slug == "software-dev"
        assert dossier.mission_run_id == "run-001"
        assert dossier.feature_slug == "042-dossier"
        assert dossier.feature_dir == "/path/to/feature"
        assert dossier.artifacts == []

    def test_dossier_with_artifacts(self):
        """Create MissionDossier with multiple artifacts."""
        artifacts = [
            ArtifactRef(
                artifact_key="spec",
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=1024,
            ),
            ArtifactRef(
                artifact_key="tasks",
                artifact_class="output",
                relative_path="tasks.md",
                content_hash_sha256="b" * 64,
                size_bytes=2048,
            ),
        ]
        dossier = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="run-001",
            feature_slug="042-dossier",
            feature_dir="/path/to/feature",
            artifacts=artifacts,
        )
        assert len(dossier.artifacts) == 2
        assert dossier.artifacts[0].artifact_key == "spec"
        assert dossier.artifacts[1].artifact_key == "tasks"

    def test_get_required_artifacts(self):
        """MissionDossier.get_required_artifacts() filters by required_status."""
        artifacts = [
            ArtifactRef(
                artifact_key="required1",
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=1024,
                required_status="required",
            ),
            ArtifactRef(
                artifact_key="optional1",
                artifact_class="output",
                relative_path="notes.md",
                content_hash_sha256="b" * 64,
                size_bytes=512,
                required_status="optional",
            ),
            ArtifactRef(
                artifact_key="required2",
                artifact_class="workflow",
                relative_path="plan.md",
                content_hash_sha256="c" * 64,
                size_bytes=2048,
                required_status="required",
            ),
        ]
        dossier = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="run-001",
            feature_slug="042-dossier",
            feature_dir="/path/to/feature",
            artifacts=artifacts,
        )
        required = dossier.get_required_artifacts()
        assert len(required) == 2
        assert all(a.required_status == "required" for a in required)

    def test_get_missing_required_artifacts(self):
        """MissionDossier.get_missing_required_artifacts() finds missing required files."""
        artifacts = [
            ArtifactRef(
                artifact_key="spec",
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=1024,
                required_status="required",
                is_present=True,
            ),
            ArtifactRef(
                artifact_key="tasks",
                artifact_class="output",
                relative_path="tasks.md",
                content_hash_sha256="b" * 64,
                size_bytes=0,
                required_status="required",
                is_present=False,
                error_reason="not_found",
            ),
        ]
        dossier = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="run-001",
            feature_slug="042-dossier",
            feature_dir="/path/to/feature",
            artifacts=artifacts,
        )
        missing = dossier.get_missing_required_artifacts()
        assert len(missing) == 1
        assert missing[0].artifact_key == "tasks"

    def test_completeness_status_complete(self):
        """MissionDossier.completeness_status == 'complete' when all required present."""
        artifacts = [
            ArtifactRef(
                artifact_key="spec",
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=1024,
                required_status="required",
                is_present=True,
            ),
        ]
        dossier = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="run-001",
            feature_slug="042-dossier",
            feature_dir="/path/to/feature",
            artifacts=artifacts,
            manifest={"required": ["spec"]},  # Has manifest
        )
        assert dossier.completeness_status == "complete"

    def test_completeness_status_incomplete(self):
        """MissionDossier.completeness_status == 'incomplete' when required missing."""
        artifacts = [
            ArtifactRef(
                artifact_key="spec",
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=0,
                required_status="required",
                is_present=False,
                error_reason="not_found",
            ),
        ]
        dossier = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="run-001",
            feature_slug="042-dossier",
            feature_dir="/path/to/feature",
            artifacts=artifacts,
            manifest={"required": ["spec"]},  # Has manifest
        )
        assert dossier.completeness_status == "incomplete"

    def test_completeness_status_unknown(self):
        """MissionDossier.completeness_status == 'unknown' when no manifest."""
        artifacts = [
            ArtifactRef(
                artifact_key="spec",
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=1024,
                required_status="required",
                is_present=True,
            ),
        ]
        dossier = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="run-001",
            feature_slug="042-dossier",
            feature_dir="/path/to/feature",
            artifacts=artifacts,
            manifest=None,  # No manifest
        )
        assert dossier.completeness_status == "unknown"
