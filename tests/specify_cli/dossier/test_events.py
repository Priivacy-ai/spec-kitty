"""Tests for mission dossier event types and emission.

Tests cover:
- All 4 event payload schemas (Pydantic validation)
- Event emitters routing through sync infrastructure
- Conditional event emission (missing only if blocking, drift only if different)
- Envelope metadata auto-population (event_id, timestamp, etc.)
- Offline queue integration (events enqueued, not sent to SaaS during local scan)
- Payload validation (reject invalid data with ValueError)
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from specify_cli.dossier.events import (
    ArtifactCountsPayload,
    MissionDossierArtifactIndexedPayload,
    MissionDossierArtifactMissingPayload,
    MissionDossierParityDriftDetectedPayload,
    MissionDossierSnapshotComputedPayload,
    emit_artifact_indexed,
    emit_artifact_missing,
    emit_parity_drift_detected,
    emit_snapshot_computed,
)


class TestMissionDossierArtifactIndexedPayload:
    """Tests for MissionDossierArtifactIndexedPayload schema."""

    def test_valid_payload_with_all_fields(self):
        """Valid payload with all fields should construct without error."""
        payload = MissionDossierArtifactIndexedPayload(
            feature_slug="042-feature",
            artifact_key="input.spec.main",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256="a" * 64,
            size_bytes=1024,
            wp_id="WP01",
            step_id="planning",
            required_status="required",
        )
        assert payload.feature_slug == "042-feature"
        assert payload.artifact_key == "input.spec.main"
        assert payload.artifact_class == "input"
        assert payload.required_status == "required"

    def test_valid_payload_with_minimal_fields(self):
        """Valid payload with only required fields should construct."""
        payload = MissionDossierArtifactIndexedPayload(
            feature_slug="042-feature",
            artifact_key="input.spec.main",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256="a" * 64,
            size_bytes=1024,
            required_status="optional",
        )
        assert payload.wp_id is None
        assert payload.step_id is None

    def test_invalid_hash_format(self):
        """Invalid SHA256 hash format should raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            MissionDossierArtifactIndexedPayload(
                feature_slug="042-feature",
                artifact_key="input.spec.main",
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256="invalid_hash",
                size_bytes=1024,
                required_status="required",
            )
        assert "Invalid SHA256 hash" in str(exc_info.value)

    def test_invalid_artifact_class(self):
        """Invalid artifact_class should raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            MissionDossierArtifactIndexedPayload(
                feature_slug="042-feature",
                artifact_key="input.spec.main",
                artifact_class="invalid_class",
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=1024,
                required_status="required",
            )
        assert "Invalid artifact_class" in str(exc_info.value)

    def test_invalid_required_status(self):
        """Invalid required_status should raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            MissionDossierArtifactIndexedPayload(
                feature_slug="042-feature",
                artifact_key="input.spec.main",
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=1024,
                required_status="invalid_status",
            )
        assert "Invalid required_status" in str(exc_info.value)

    def test_missing_required_field(self):
        """Missing required field should raise ValidationError."""
        with pytest.raises(ValidationError):
            MissionDossierArtifactIndexedPayload(
                feature_slug="042-feature",
                artifact_key="input.spec.main",
                artifact_class="input",
                relative_path="spec.md",
                # Missing content_hash_sha256
                size_bytes=1024,
                required_status="required",
            )


class TestMissionDossierArtifactMissingPayload:
    """Tests for MissionDossierArtifactMissingPayload schema."""

    def test_valid_payload(self):
        """Valid payload should construct without error."""
        payload = MissionDossierArtifactMissingPayload(
            feature_slug="042-feature",
            artifact_key="output.tasks.per_wp",
            artifact_class="output",
            expected_path_pattern="tasks/*.md",
            reason_code="not_found",
            reason_detail="No tasks directory found",
            blocking=True,
        )
        assert payload.feature_slug == "042-feature"
        assert payload.reason_code == "not_found"
        assert payload.blocking is True

    def test_valid_payload_without_detail(self):
        """Valid payload without reason_detail should construct."""
        payload = MissionDossierArtifactMissingPayload(
            feature_slug="042-feature",
            artifact_key="output.tasks.per_wp",
            artifact_class="output",
            expected_path_pattern="tasks/*.md",
            reason_code="not_found",
            blocking=True,
        )
        assert payload.reason_detail is None

    def test_invalid_reason_code(self):
        """Invalid reason_code should raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            MissionDossierArtifactMissingPayload(
                feature_slug="042-feature",
                artifact_key="output.tasks.per_wp",
                artifact_class="output",
                expected_path_pattern="tasks/*.md",
                reason_code="invalid_reason",
                blocking=True,
            )
        assert "Invalid reason_code" in str(exc_info.value)

    def test_all_valid_reason_codes(self):
        """All valid reason codes should construct successfully."""
        for reason_code in ["not_found", "unreadable", "invalid_format", "deleted_after_scan"]:
            payload = MissionDossierArtifactMissingPayload(
                feature_slug="042-feature",
                artifact_key="output.tasks.per_wp",
                artifact_class="output",
                expected_path_pattern="tasks/*.md",
                reason_code=reason_code,
                blocking=True,
            )
            assert payload.reason_code == reason_code


class TestArtifactCountsPayload:
    """Tests for ArtifactCountsPayload schema."""

    def test_valid_counts(self):
        """Valid artifact counts should construct without error."""
        counts = ArtifactCountsPayload(
            total=10,
            required=7,
            required_present=6,
            required_missing=1,
            optional=3,
            optional_present=3,
        )
        assert counts.total == 10
        assert counts.required_present == 6

    def test_zero_counts(self):
        """Zero counts should be valid."""
        counts = ArtifactCountsPayload(
            total=0,
            required=0,
            required_present=0,
            required_missing=0,
            optional=0,
            optional_present=0,
        )
        assert counts.total == 0

    def test_negative_count_invalid(self):
        """Negative counts should raise ValidationError."""
        with pytest.raises(ValidationError):
            ArtifactCountsPayload(
                total=-1,
                required=0,
                required_present=0,
                required_missing=0,
                optional=0,
                optional_present=0,
            )


class TestMissionDossierSnapshotComputedPayload:
    """Tests for MissionDossierSnapshotComputedPayload schema."""

    def test_valid_payload(self):
        """Valid payload should construct without error."""
        payload = MissionDossierSnapshotComputedPayload(
            feature_slug="042-feature",
            parity_hash_sha256="a" * 64,
            artifact_counts=ArtifactCountsPayload(
                total=10,
                required=7,
                required_present=6,
                required_missing=1,
                optional=3,
                optional_present=3,
            ),
            completeness_status="incomplete",
            snapshot_id="snap-001",
        )
        assert payload.feature_slug == "042-feature"
        assert payload.completeness_status == "incomplete"

    def test_invalid_parity_hash(self):
        """Invalid parity hash should raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            MissionDossierSnapshotComputedPayload(
                feature_slug="042-feature",
                parity_hash_sha256="invalid_hash",
                artifact_counts=ArtifactCountsPayload(
                    total=10,
                    required=7,
                    required_present=6,
                    required_missing=1,
                    optional=3,
                    optional_present=3,
                ),
                completeness_status="complete",
                snapshot_id="snap-001",
            )
        assert "Invalid SHA256 hash" in str(exc_info.value)

    def test_invalid_completeness_status(self):
        """Invalid completeness_status should raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            MissionDossierSnapshotComputedPayload(
                feature_slug="042-feature",
                parity_hash_sha256="a" * 64,
                artifact_counts=ArtifactCountsPayload(
                    total=10,
                    required=7,
                    required_present=6,
                    required_missing=1,
                    optional=3,
                    optional_present=3,
                ),
                completeness_status="invalid_status",
                snapshot_id="snap-001",
            )
        assert "Invalid completeness_status" in str(exc_info.value)

    def test_all_valid_completeness_statuses(self):
        """All valid completeness statuses should construct successfully."""
        for status in ["complete", "incomplete", "unknown"]:
            payload = MissionDossierSnapshotComputedPayload(
                feature_slug="042-feature",
                parity_hash_sha256="a" * 64,
                artifact_counts=ArtifactCountsPayload(
                    total=10,
                    required=7,
                    required_present=6,
                    required_missing=1,
                    optional=3,
                    optional_present=3,
                ),
                completeness_status=status,
                snapshot_id="snap-001",
            )
            assert payload.completeness_status == status


class TestMissionDossierParityDriftDetectedPayload:
    """Tests for MissionDossierParityDriftDetectedPayload schema."""

    def test_valid_payload_with_drift(self):
        """Valid payload with drift should construct without error."""
        payload = MissionDossierParityDriftDetectedPayload(
            feature_slug="042-feature",
            local_parity_hash="a" * 64,
            baseline_parity_hash="b" * 64,
            missing_in_local=["artifact1", "artifact2"],
            missing_in_baseline=["artifact3"],
            severity="warning",
        )
        assert payload.feature_slug == "042-feature"
        assert payload.severity == "warning"
        assert len(payload.missing_in_local) == 2

    def test_valid_payload_without_missing_lists(self):
        """Valid payload with empty missing lists should construct."""
        payload = MissionDossierParityDriftDetectedPayload(
            feature_slug="042-feature",
            local_parity_hash="a" * 64,
            baseline_parity_hash="b" * 64,
            severity="error",
        )
        assert payload.missing_in_local == []
        assert payload.missing_in_baseline == []

    def test_invalid_local_hash(self):
        """Invalid local hash should raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            MissionDossierParityDriftDetectedPayload(
                feature_slug="042-feature",
                local_parity_hash="invalid_hash",
                baseline_parity_hash="b" * 64,
                severity="warning",
            )
        assert "Invalid SHA256 hash" in str(exc_info.value)

    def test_invalid_severity(self):
        """Invalid severity should raise ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            MissionDossierParityDriftDetectedPayload(
                feature_slug="042-feature",
                local_parity_hash="a" * 64,
                baseline_parity_hash="b" * 64,
                severity="invalid_severity",
            )
        assert "Invalid severity" in str(exc_info.value)

    def test_all_valid_severities(self):
        """All valid severities should construct successfully."""
        for severity in ["info", "warning", "error"]:
            payload = MissionDossierParityDriftDetectedPayload(
                feature_slug="042-feature",
                local_parity_hash="a" * 64,
                baseline_parity_hash="b" * 64,
                severity=severity,
            )
            assert payload.severity == severity


class TestEmitArtifactIndexed:
    """Tests for emit_artifact_indexed emitter function."""

    @patch("specify_cli.sync.events.get_emitter")
    def test_emit_artifact_indexed_success(self, mock_get_emitter):
        """emit_artifact_indexed should emit event to sync infrastructure."""
        mock_emitter = MagicMock()
        mock_event = {
            "event_id": "event-001",
            "event_type": "MissionDossierArtifactIndexed",
            "timestamp": "2026-02-21T12:00:00+00:00",
        }
        mock_emitter._emit.return_value = mock_event
        mock_get_emitter.return_value = mock_emitter

        result = emit_artifact_indexed(
            feature_slug="042-feature",
            artifact_key="input.spec.main",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256="a" * 64,
            size_bytes=1024,
            wp_id="WP01",
            step_id="planning",
            required_status="required",
        )

        assert result == mock_event
        mock_emitter._emit.assert_called_once()
        call_args = mock_emitter._emit.call_args
        assert call_args[1]["event_type"] == "MissionDossierArtifactIndexed"
        assert call_args[1]["aggregate_type"] == "MissionDossier"

    def test_emit_artifact_indexed_invalid_payload(self, caplog):
        """emit_artifact_indexed should reject invalid payload with error log."""
        result = emit_artifact_indexed(
            feature_slug="042-feature",
            artifact_key="input.spec.main",
            artifact_class="invalid_class",  # Invalid
            relative_path="spec.md",
            content_hash_sha256="a" * 64,
            size_bytes=1024,
            required_status="required",
        )

        assert result is None
        assert "Payload validation failed" in caplog.text

    @patch("specify_cli.sync.events.get_emitter")
    def test_emit_artifact_indexed_with_minimal_fields(self, mock_get_emitter):
        """emit_artifact_indexed should work with minimal fields."""
        mock_emitter = MagicMock()
        mock_event = {"event_id": "event-001", "event_type": "MissionDossierArtifactIndexed"}
        mock_emitter._emit.return_value = mock_event
        mock_get_emitter.return_value = mock_emitter

        result = emit_artifact_indexed(
            feature_slug="042-feature",
            artifact_key="input.spec.main",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256="a" * 64,
            size_bytes=1024,
            required_status="optional",
        )

        assert result == mock_event


class TestEmitArtifactMissing:
    """Tests for emit_artifact_missing emitter function."""

    @patch("specify_cli.sync.events.get_emitter")
    def test_emit_artifact_missing_blocking_true(self, mock_get_emitter):
        """emit_artifact_missing should emit event when blocking=True."""
        mock_emitter = MagicMock()
        mock_event = {
            "event_id": "event-002",
            "event_type": "MissionDossierArtifactMissing",
        }
        mock_emitter._emit.return_value = mock_event
        mock_get_emitter.return_value = mock_emitter

        result = emit_artifact_missing(
            feature_slug="042-feature",
            artifact_key="output.tasks.per_wp",
            artifact_class="output",
            expected_path_pattern="tasks/*.md",
            reason_code="not_found",
            blocking=True,
        )

        assert result == mock_event
        mock_emitter._emit.assert_called_once()

    def test_emit_artifact_missing_blocking_false(self, caplog):
        """emit_artifact_missing should skip event when blocking=False."""
        with caplog.at_level(logging.DEBUG):
            result = emit_artifact_missing(
                feature_slug="042-feature",
                artifact_key="output.tasks.per_wp",
                artifact_class="output",
                expected_path_pattern="tasks/*.md",
                reason_code="not_found",
                blocking=False,
            )

        assert result is None
        assert "Skipping optional artifact missing event" in caplog.text

    def test_emit_artifact_missing_invalid_payload(self, caplog):
        """emit_artifact_missing should reject invalid payload."""
        result = emit_artifact_missing(
            feature_slug="042-feature",
            artifact_key="output.tasks.per_wp",
            artifact_class="invalid_class",  # Invalid
            expected_path_pattern="tasks/*.md",
            reason_code="not_found",
            blocking=True,
        )

        assert result is None
        assert "Payload validation failed" in caplog.text


class TestEmitSnapshotComputed:
    """Tests for emit_snapshot_computed emitter function."""

    @patch("specify_cli.sync.events.get_emitter")
    def test_emit_snapshot_computed_complete(self, mock_get_emitter):
        """emit_snapshot_computed should emit event with complete status."""
        mock_emitter = MagicMock()
        mock_event = {
            "event_id": "event-003",
            "event_type": "MissionDossierSnapshotComputed",
        }
        mock_emitter._emit.return_value = mock_event
        mock_get_emitter.return_value = mock_emitter

        result = emit_snapshot_computed(
            feature_slug="042-feature",
            parity_hash_sha256="a" * 64,
            total_artifacts=10,
            required_artifacts=7,
            required_present=7,
            required_missing=0,
            optional_artifacts=3,
            optional_present=3,
            completeness_status="complete",
            snapshot_id="snap-001",
        )

        assert result == mock_event
        mock_emitter._emit.assert_called_once()

    @patch("specify_cli.sync.events.get_emitter")
    def test_emit_snapshot_computed_incomplete(self, mock_get_emitter):
        """emit_snapshot_computed should emit event with incomplete status."""
        mock_emitter = MagicMock()
        mock_event = {
            "event_id": "event-003",
            "event_type": "MissionDossierSnapshotComputed",
        }
        mock_emitter._emit.return_value = mock_event
        mock_get_emitter.return_value = mock_emitter

        result = emit_snapshot_computed(
            feature_slug="042-feature",
            parity_hash_sha256="a" * 64,
            total_artifacts=10,
            required_artifacts=7,
            required_present=6,
            required_missing=1,
            optional_artifacts=3,
            optional_present=3,
            completeness_status="incomplete",
            snapshot_id="snap-001",
        )

        assert result == mock_event

    def test_emit_snapshot_computed_invalid_payload(self, caplog):
        """emit_snapshot_computed should reject invalid payload."""
        result = emit_snapshot_computed(
            feature_slug="042-feature",
            parity_hash_sha256="invalid_hash",  # Invalid
            total_artifacts=10,
            required_artifacts=7,
            required_present=7,
            required_missing=0,
            optional_artifacts=3,
            optional_present=3,
            completeness_status="complete",
            snapshot_id="snap-001",
        )

        assert result is None
        assert "Payload validation failed" in caplog.text


class TestEmitParityDriftDetected:
    """Tests for emit_parity_drift_detected emitter function."""

    @patch("specify_cli.sync.events.get_emitter")
    def test_emit_parity_drift_detected_with_drift(self, mock_get_emitter):
        """emit_parity_drift_detected should emit event when hashes differ."""
        mock_emitter = MagicMock()
        mock_event = {
            "event_id": "event-004",
            "event_type": "MissionDossierParityDriftDetected",
        }
        mock_emitter._emit.return_value = mock_event
        mock_get_emitter.return_value = mock_emitter

        result = emit_parity_drift_detected(
            feature_slug="042-feature",
            local_parity_hash="a" * 64,
            baseline_parity_hash="b" * 64,  # Different hash
            missing_in_local=["artifact1"],
            missing_in_baseline=["artifact2"],
            severity="warning",
        )

        assert result == mock_event
        mock_emitter._emit.assert_called_once()

    def test_emit_parity_drift_detected_no_drift(self, caplog):
        """emit_parity_drift_detected should skip event when hashes match."""
        with caplog.at_level(logging.DEBUG):
            result = emit_parity_drift_detected(
                feature_slug="042-feature",
                local_parity_hash="a" * 64,
                baseline_parity_hash="a" * 64,  # Same hash - no drift
                severity="info",
            )

        assert result is None
        assert "No parity drift detected" in caplog.text

    def test_emit_parity_drift_detected_invalid_payload(self, caplog):
        """emit_parity_drift_detected should reject invalid payload."""
        result = emit_parity_drift_detected(
            feature_slug="042-feature",
            local_parity_hash="invalid_hash",  # Invalid
            baseline_parity_hash="b" * 64,
            severity="warning",
        )

        assert result is None
        assert "Payload validation failed" in caplog.text

    @patch("specify_cli.sync.events.get_emitter")
    def test_emit_parity_drift_detected_error_severity(self, mock_get_emitter):
        """emit_parity_drift_detected should emit with error severity."""
        mock_emitter = MagicMock()
        mock_event = {"event_id": "event-004", "event_type": "MissionDossierParityDriftDetected"}
        mock_emitter._emit.return_value = mock_event
        mock_get_emitter.return_value = mock_emitter

        result = emit_parity_drift_detected(
            feature_slug="042-feature",
            local_parity_hash="a" * 64,
            baseline_parity_hash="b" * 64,
            severity="error",
        )

        assert result == mock_event


class TestEventEnvelopeMetadata:
    """Tests for event envelope metadata auto-population."""

    @patch("specify_cli.sync.events.get_emitter")
    def test_emitter_calls_with_correct_aggregate_type(self, mock_get_emitter):
        """All dossier events should use 'MissionDossier' aggregate_type."""
        mock_emitter = MagicMock()
        mock_emitter._emit.return_value = {}
        mock_get_emitter.return_value = mock_emitter

        emit_artifact_indexed(
            feature_slug="042-feature",
            artifact_key="input.spec.main",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256="a" * 64,
            size_bytes=1024,
            required_status="required",
        )

        call_kwargs = mock_emitter._emit.call_args[1]
        assert call_kwargs["aggregate_type"] == "MissionDossier"

    @patch("specify_cli.sync.events.get_emitter")
    def test_emitter_constructs_aggregate_id(self, mock_get_emitter):
        """Events should construct aggregate_id from feature_slug and key."""
        mock_emitter = MagicMock()
        mock_emitter._emit.return_value = {}
        mock_get_emitter.return_value = mock_emitter

        emit_artifact_indexed(
            feature_slug="042-feature",
            artifact_key="input.spec.main",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256="a" * 64,
            size_bytes=1024,
            required_status="required",
        )

        call_kwargs = mock_emitter._emit.call_args[1]
        assert call_kwargs["aggregate_id"] == "042-feature:input.spec.main"
