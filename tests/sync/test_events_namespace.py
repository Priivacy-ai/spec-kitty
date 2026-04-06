"""Tests for namespace injection in dossier event emission."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from specify_cli.dossier.events import (
    emit_artifact_indexed,
    emit_artifact_missing,
    emit_parity_drift_detected,
    emit_snapshot_computed,
)

pytestmark = pytest.mark.fast

def _make_namespace_dict() -> dict[str, str]:
    return {
        "project_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "mission_slug": "047-feat",
        "target_branch": "main",
        "mission_type": "software-dev",
        "manifest_version": "1",
    }


VALID_HASH = "a" * 64


class TestArtifactIndexedNamespace:
    @patch("specify_cli.sync.events.get_emitter")
    def test_includes_namespace_when_provided(self, mock_get_emitter: MagicMock) -> None:
        mock_emitter = MagicMock()
        mock_emitter._emit.return_value = {"event_type": "test"}
        mock_get_emitter.return_value = mock_emitter

        ns = _make_namespace_dict()
        emit_artifact_indexed(
            mission_slug="047-feat",
            artifact_key="input.spec",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256=VALID_HASH,
            size_bytes=100,
            namespace=ns,
        )

        call_kwargs = mock_emitter._emit.call_args
        payload = call_kwargs.kwargs["payload"]
        assert "namespace" in payload
        assert payload["namespace"] == ns
        assert len(payload["namespace"]) == 5

    @patch("specify_cli.sync.events.get_emitter")
    def test_omits_namespace_when_not_provided(self, mock_get_emitter: MagicMock) -> None:
        mock_emitter = MagicMock()
        mock_emitter._emit.return_value = {"event_type": "test"}
        mock_get_emitter.return_value = mock_emitter

        emit_artifact_indexed(
            mission_slug="047-feat",
            artifact_key="input.spec",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256=VALID_HASH,
            size_bytes=100,
        )

        call_kwargs = mock_emitter._emit.call_args
        payload = call_kwargs.kwargs["payload"]
        assert "namespace" not in payload


class TestArtifactMissingNamespace:
    @patch("specify_cli.sync.events.get_emitter")
    def test_includes_namespace_when_provided(self, mock_get_emitter: MagicMock) -> None:
        mock_emitter = MagicMock()
        mock_emitter._emit.return_value = {"event_type": "test"}
        mock_get_emitter.return_value = mock_emitter

        ns = _make_namespace_dict()
        emit_artifact_missing(
            mission_slug="047-feat",
            artifact_key="input.spec",
            artifact_class="input",
            expected_path_pattern="spec.md",
            reason_code="not_found",
            blocking=True,
            namespace=ns,
        )

        call_kwargs = mock_emitter._emit.call_args
        payload = call_kwargs.kwargs["payload"]
        assert "namespace" in payload
        assert payload["namespace"] == ns

    @patch("specify_cli.sync.events.get_emitter")
    def test_omits_namespace_when_not_provided(self, mock_get_emitter: MagicMock) -> None:
        mock_emitter = MagicMock()
        mock_emitter._emit.return_value = {"event_type": "test"}
        mock_get_emitter.return_value = mock_emitter

        emit_artifact_missing(
            mission_slug="047-feat",
            artifact_key="input.spec",
            artifact_class="input",
            expected_path_pattern="spec.md",
            reason_code="not_found",
            blocking=True,
        )

        call_kwargs = mock_emitter._emit.call_args
        payload = call_kwargs.kwargs["payload"]
        assert "namespace" not in payload


class TestSnapshotComputedNamespace:
    @patch("specify_cli.sync.events.get_emitter")
    def test_includes_namespace_when_provided(self, mock_get_emitter: MagicMock) -> None:
        mock_emitter = MagicMock()
        mock_emitter._emit.return_value = {"event_type": "test"}
        mock_get_emitter.return_value = mock_emitter

        ns = _make_namespace_dict()
        emit_snapshot_computed(
            mission_slug="047-feat",
            parity_hash_sha256=VALID_HASH,
            total_artifacts=5,
            required_artifacts=3,
            required_present=3,
            required_missing=0,
            optional_artifacts=2,
            optional_present=1,
            completeness_status="complete",
            snapshot_id="snap-001",
            namespace=ns,
        )

        call_kwargs = mock_emitter._emit.call_args
        payload = call_kwargs.kwargs["payload"]
        assert "namespace" in payload
        assert payload["namespace"] == ns


class TestParityDriftNamespace:
    @patch("specify_cli.sync.events.get_emitter")
    def test_includes_namespace_when_provided(self, mock_get_emitter: MagicMock) -> None:
        mock_emitter = MagicMock()
        mock_emitter._emit.return_value = {"event_type": "test"}
        mock_get_emitter.return_value = mock_emitter

        ns = _make_namespace_dict()
        emit_parity_drift_detected(
            mission_slug="047-feat",
            local_parity_hash=VALID_HASH,
            baseline_parity_hash="b" * 64,
            namespace=ns,
        )

        call_kwargs = mock_emitter._emit.call_args
        payload = call_kwargs.kwargs["payload"]
        assert "namespace" in payload
        assert payload["namespace"] == ns
