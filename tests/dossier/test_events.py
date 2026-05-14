"""Tests for mission dossier event types and emission (namespaced envelope).

These tests pin the wire shape produced by the four dossier event emitters
against the canonical ``spec_kitty_events>=5.0.0`` server schemas. The
legacy flat envelope (``mission_slug, artifact_key, content_hash_sha256, …``)
was rejected by the deployed SaaS with ``Additional properties are not
allowed``; the migration is tracked under
Priivacy-ai/spec-kitty#1047 and the launch evidence lives in
Priivacy-ai/spec-kitty-end-to-end-testing#37.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import jsonschema
import pytest
from pydantic import ValidationError
from spec_kitty_events.schemas import load_schema

from specify_cli.dossier.events import (
    ArtifactIdentity,
    ContentHashRef,
    LocalNamespaceTuple,
    MissionDossierArtifactIndexedPayload,
    MissionDossierArtifactMissingPayload,
    MissionDossierParityDriftDetectedPayload,
    MissionDossierSnapshotComputedPayload,
    emit_artifact_indexed,
    emit_artifact_missing,
    emit_parity_drift_detected,
    emit_snapshot_computed,
)

pytestmark = pytest.mark.fast


# ── Schema helpers ─────────────────────────────────────────────────────


def _server_schema(name: str) -> dict[str, Any]:
    return load_schema(name)


def _assert_valid(payload: dict[str, Any], schema_name: str) -> None:
    jsonschema.validate(payload, _server_schema(schema_name))


@pytest.fixture
def namespace() -> LocalNamespaceTuple:
    return LocalNamespaceTuple(
        project_uuid="11111111-2222-3333-4444-555555555555",
        mission_slug="042-feature",
        target_branch="main",
        mission_type="software-dev",
        manifest_version="1.0.0",
    )


@pytest.fixture
def captured_emissions(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    captured: list[dict[str, Any]] = []

    def _fake(event_type: str, aggregate_id: str, aggregate_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        captured.append(
            {
                "event_type": event_type,
                "aggregate_id": aggregate_id,
                "aggregate_type": aggregate_type,
                "payload": payload,
            }
        )
        return {"ok": True, "event_id": f"fake-{len(captured)}"}

    monkeypatch.setattr("specify_cli.dossier.events.fire_dossier_event", _fake)
    return captured


# ── Sub-object models ──────────────────────────────────────────────────


class TestLocalNamespaceTuple:
    def test_valid(self) -> None:
        LocalNamespaceTuple(
            project_uuid="p", mission_slug="m", target_branch="main",
            mission_type="software-dev", manifest_version="1.0.0",
        )

    def test_rejects_extra(self) -> None:
        with pytest.raises(ValidationError):
            LocalNamespaceTuple(  # type: ignore[call-arg]
                project_uuid="p", mission_slug="m", target_branch="main",
                mission_type="software-dev", manifest_version="1.0.0",
                bogus="x",
            )

    def test_step_id_optional(self) -> None:
        ns = LocalNamespaceTuple(
            project_uuid="p", mission_slug="m", target_branch="main",
            mission_type="software-dev", manifest_version="1.0.0",
            step_id="planning",
        )
        assert ns.step_id == "planning"


class TestArtifactIdentity:
    def test_valid(self) -> None:
        ArtifactIdentity(mission_type="software-dev", path="spec.md", artifact_class="input")

    def test_rejects_unknown_class(self) -> None:
        with pytest.raises(ValidationError):
            ArtifactIdentity(mission_type="software-dev", path="spec.md", artifact_class="bogus")

    def test_rejects_other_class(self) -> None:
        # The new server schema dropped the legacy ``other`` enum value.
        with pytest.raises(ValidationError):
            ArtifactIdentity(mission_type="software-dev", path="spec.md", artifact_class="other")


class TestContentHashRef:
    def test_valid(self) -> None:
        ContentHashRef(algorithm="sha256", hash="a" * 64, size_bytes=10)

    def test_lowercases_hash(self) -> None:
        ref = ContentHashRef(algorithm="sha256", hash="A" * 64)
        assert ref.hash == "a" * 64

    def test_rejects_unknown_algorithm(self) -> None:
        with pytest.raises(ValidationError):
            ContentHashRef(algorithm="crc32", hash="abc")


# ── End-to-end emitter behavior + schema parity ────────────────────────


class TestEmitArtifactIndexed:
    def test_emits_namespaced_envelope(
        self, captured_emissions: list[dict[str, Any]], namespace: LocalNamespaceTuple
    ) -> None:
        result = emit_artifact_indexed(
            mission_slug="042-feature",
            artifact_key="input.spec.main",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256="a" * 64,
            size_bytes=1024,
            wp_id="WP01",
            step_id="planning",
            required_status="required",
            namespace=namespace,
        )
        assert result is not None
        assert len(captured_emissions) == 1
        evt = captured_emissions[0]
        assert evt["event_type"] == "MissionDossierArtifactIndexed"
        assert evt["aggregate_type"] == "MissionDossier"
        assert evt["aggregate_id"] == "042-feature:spec.md"

        payload = evt["payload"]
        assert set(payload.keys()).issubset(
            {"namespace", "artifact_id", "content_ref", "indexed_at",
             "provenance", "step_id", "context_diagnostics", "supersedes"}
        )
        assert payload["namespace"]["mission_slug"] == "042-feature"
        assert payload["namespace"]["mission_type"] == "software-dev"
        assert payload["artifact_id"] == {
            "mission_type": "software-dev",
            "path": "spec.md",
            "artifact_class": "input",
            "wp_id": "WP01",
        }
        assert payload["content_ref"] == {
            "algorithm": "sha256",
            "hash": "a" * 64,
            "size_bytes": 1024,
        }
        assert payload["step_id"] == "planning"
        assert payload["context_diagnostics"]["artifact_key"] == "input.spec.main"
        assert payload["context_diagnostics"]["required_status"] == "required"

        _assert_valid(payload, "mission_dossier_artifact_indexed_payload")

    def test_legacy_other_class_maps_to_runtime(
        self, captured_emissions: list[dict[str, Any]], namespace: LocalNamespaceTuple
    ) -> None:
        emit_artifact_indexed(
            mission_slug="042-feature",
            artifact_key="legacy.other",
            artifact_class="other",
            relative_path="legacy.md",
            content_hash_sha256="a" * 64,
            size_bytes=1,
            namespace=namespace,
        )
        payload = captured_emissions[0]["payload"]
        assert payload["artifact_id"]["artifact_class"] == "runtime"
        _assert_valid(payload, "mission_dossier_artifact_indexed_payload")

    def test_accepts_dict_namespace(
        self, captured_emissions: list[dict[str, Any]], namespace: LocalNamespaceTuple
    ) -> None:
        ns_dict = namespace.model_dump(exclude_none=True)
        emit_artifact_indexed(
            mission_slug="042-feature",
            artifact_key="input.spec.main",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256="a" * 64,
            size_bytes=1,
            namespace=ns_dict,
        )
        assert captured_emissions
        _assert_valid(captured_emissions[0]["payload"], "mission_dossier_artifact_indexed_payload")

    def test_missing_namespace_refuses_to_emit(
        self, captured_emissions: list[dict[str, Any]], caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.ERROR, logger="specify_cli.dossier.events")
        result = emit_artifact_indexed(
            mission_slug="042-feature",
            artifact_key="input.spec.main",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256="a" * 64,
            size_bytes=1,
            namespace=None,
        )
        assert result is None
        assert not captured_emissions
        assert any(
            "MissionDossierArtifactIndexed" in record.message
            for record in caplog.records
        )

    def test_invalid_artifact_class_returns_none(
        self, captured_emissions: list[dict[str, Any]], namespace: LocalNamespaceTuple
    ) -> None:
        result = emit_artifact_indexed(
            mission_slug="042-feature",
            artifact_key="x",
            artifact_class="bogus",
            relative_path="x.md",
            content_hash_sha256="a" * 64,
            size_bytes=1,
            namespace=namespace,
        )
        assert result is None
        assert not captured_emissions


class TestEmitArtifactMissing:
    def test_blocking_emits_namespaced_envelope(
        self, captured_emissions: list[dict[str, Any]], namespace: LocalNamespaceTuple
    ) -> None:
        emit_artifact_missing(
            mission_slug="042-feature",
            artifact_key="output.dossier.indexed",
            artifact_class="output",
            expected_path_pattern="dossier.json",
            reason_code="not_found",
            reason_detail="never produced by the indexer",
            blocking=True,
            namespace=namespace,
            manifest_step="indexing",
        )
        assert captured_emissions
        payload = captured_emissions[0]["payload"]
        _assert_valid(payload, "mission_dossier_artifact_missing_payload")
        assert payload["expected_identity"]["path"] == "dossier.json"
        assert payload["manifest_step"] == "indexing"
        assert payload["context_diagnostics"]["reason_code"] == "not_found"
        assert payload["context_diagnostics"]["reason_detail"] == "never produced by the indexer"

    def test_non_blocking_skips(
        self, captured_emissions: list[dict[str, Any]], namespace: LocalNamespaceTuple
    ) -> None:
        result = emit_artifact_missing(
            mission_slug="042-feature",
            artifact_key="optional.body",
            artifact_class="output",
            expected_path_pattern="body.md",
            reason_code="not_found",
            blocking=False,
            namespace=namespace,
        )
        assert result is None
        assert not captured_emissions


class TestEmitSnapshotComputed:
    def test_emits_namespaced_envelope(
        self, captured_emissions: list[dict[str, Any]], namespace: LocalNamespaceTuple
    ) -> None:
        emit_snapshot_computed(
            mission_slug="042-feature",
            parity_hash_sha256="b" * 64,
            total_artifacts=10,
            required_artifacts=5,
            required_present=5,
            required_missing=0,
            optional_artifacts=5,
            optional_present=4,
            completeness_status="complete",
            snapshot_id="snap-01",
            namespace=namespace,
        )
        assert captured_emissions
        payload = captured_emissions[0]["payload"]
        _assert_valid(payload, "mission_dossier_snapshot_computed_payload")
        assert payload["snapshot_hash"] == "b" * 64
        assert payload["artifact_count"] == 10
        assert payload["anomaly_count"] == 0
        assert payload["context_diagnostics"]["snapshot_id"] == "snap-01"
        assert payload["context_diagnostics"]["completeness_status"] == "complete"


class TestEmitParityDriftDetected:
    def test_emits_when_hashes_differ(
        self, captured_emissions: list[dict[str, Any]], namespace: LocalNamespaceTuple
    ) -> None:
        emit_parity_drift_detected(
            mission_slug="042-feature",
            local_parity_hash="c" * 64,
            baseline_parity_hash="d" * 64,
            missing_in_local=["foo.md"],
            missing_in_baseline=["bar.md"],
            severity="warning",
            namespace=namespace,
        )
        assert captured_emissions
        payload = captured_emissions[0]["payload"]
        _assert_valid(payload, "mission_dossier_parity_drift_detected_payload")
        assert payload["actual_hash"] == "c" * 64
        assert payload["expected_hash"] == "d" * 64
        assert payload["drift_kind"] == "anomaly_introduced"
        paths = {item["path"] for item in payload["artifact_ids_changed"]}
        assert paths == {"foo.md", "bar.md"}
        assert payload["context_diagnostics"]["severity"] == "warning"

    def test_identical_hashes_skip(
        self, captured_emissions: list[dict[str, Any]], namespace: LocalNamespaceTuple
    ) -> None:
        result = emit_parity_drift_detected(
            mission_slug="042-feature",
            local_parity_hash="c" * 64,
            baseline_parity_hash="c" * 64,
            severity="warning",
            namespace=namespace,
        )
        assert result is None
        assert not captured_emissions


# ── Wire-payload Pydantic models reject extras (parity with server) ────


class TestWirePayloadModelsRejectExtras:
    @pytest.mark.parametrize(
        "model_cls",
        [
            MissionDossierArtifactIndexedPayload,
            MissionDossierArtifactMissingPayload,
            MissionDossierSnapshotComputedPayload,
            MissionDossierParityDriftDetectedPayload,
        ],
    )
    def test_extras_rejected(self, model_cls: type) -> None:
        with pytest.raises(ValidationError):
            model_cls(bogus="x")  # type: ignore[call-arg]


class TestPayloadJsonRoundTrip:
    def test_indexed_payload_is_json_serializable(
        self, captured_emissions: list[dict[str, Any]], namespace: LocalNamespaceTuple
    ) -> None:
        emit_artifact_indexed(
            mission_slug="042-feature",
            artifact_key="input.spec.main",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256="a" * 64,
            size_bytes=1,
            namespace=namespace,
        )
        payload = captured_emissions[0]["payload"]
        json.dumps(payload)
