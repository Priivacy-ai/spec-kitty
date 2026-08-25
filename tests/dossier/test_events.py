"""Tests for mission dossier event types and emission (namespaced envelope).

The CLI→SaaS sync transport was deleted, so the four dossier emitters no
longer deliver anywhere: they still coerce namespaces, gate on blocking /
hash-equality / artifact-class validity, run the canonical payload validators,
and then drop the envelope locally (:func:`specify_cli.dossier.events.
_undelivered`). These tests pin that contract plus the wire-payload Pydantic
models themselves (the ``MissionDossier*`` payload schemas remain canonical
sub-object definitions shared with ``spec_kitty_events``).
"""

from __future__ import annotations

import logging

import pytest
from pydantic import ValidationError

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


@pytest.fixture
def namespace() -> LocalNamespaceTuple:
    return LocalNamespaceTuple(
        project_uuid="11111111-2222-3333-4444-555555555555",
        mission_slug="042-feature",
        target_branch="main",
        mission_type="software-dev",
        manifest_version="1.0.0",
    )


# ── Sub-object models ──────────────────────────────────────────────────


class TestLocalNamespaceTuple:
    def test_valid(self) -> None:
        LocalNamespaceTuple(
            project_uuid="p",
            mission_slug="m",
            target_branch="main",
            mission_type="software-dev",
            manifest_version="1.0.0",
        )

    def test_rejects_extra(self) -> None:
        with pytest.raises(ValidationError):
            LocalNamespaceTuple(  # type: ignore[call-arg]
                project_uuid="p",
                mission_slug="m",
                target_branch="main",
                mission_type="software-dev",
                manifest_version="1.0.0",
                bogus="x",
            )

    def test_step_id_optional(self) -> None:
        ns = LocalNamespaceTuple(
            project_uuid="p",
            mission_slug="m",
            target_branch="main",
            mission_type="software-dev",
            manifest_version="1.0.0",
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
        # The former server schema dropped the legacy ``other`` enum value.
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


# ── Emitter gating + drop semantics ───────────────────────────────────


class TestEmitDropSemantics:
    """Valid envelopes validate and are dropped locally (no transport)."""

    def test_artifact_indexed_drops_after_validation(
        self, namespace: LocalNamespaceTuple, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.ERROR, logger="specify_cli.dossier.events")
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
        assert result is None
        assert not [r for r in caplog.records if "Payload validation failed" in r.message]

    def test_blocking_missing_drops_after_validation(
        self, namespace: LocalNamespaceTuple, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.ERROR, logger="specify_cli.dossier.events")
        result = emit_artifact_missing(
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
        assert result is None
        assert not [r for r in caplog.records if "Payload validation failed" in r.message]

    def test_snapshot_computed_accepts_legacy_positional_order(
        self, namespace: LocalNamespaceTuple, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Legacy positional order still passes validation (no failure logged)."""
        caplog.set_level(logging.ERROR, logger="specify_cli.dossier.events")
        result = emit_snapshot_computed(
            "042-feature",
            "b" * 64,
            10,
            6,
            4,
            2,
            4,
            3,
            "incomplete",
            "snap-positional",
            namespace,
        )
        assert result is None
        assert not [r for r in caplog.records if "Payload validation failed" in r.message]

    def test_parity_drift_drops_after_validation(
        self, namespace: LocalNamespaceTuple, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.ERROR, logger="specify_cli.dossier.events")
        result = emit_parity_drift_detected(
            mission_slug="042-feature",
            local_parity_hash="c" * 64,
            baseline_parity_hash="d" * 64,
            missing_in_local=["foo.md"],
            missing_in_baseline=["bar.md"],
            severity="warning",
            namespace=namespace,
        )
        assert result is None
        assert not [r for r in caplog.records if "Payload validation failed" in r.message]


class TestEmitGatingStillApplies:
    """Refusal gates fire before the drop, exactly as when delivery existed."""

    def test_missing_namespace_refuses_to_emit(self, caplog: pytest.LogCaptureFixture) -> None:
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
        assert any("MissionDossierArtifactIndexed" in record.message for record in caplog.records)

    def test_invalid_artifact_class_returns_none(self, namespace: LocalNamespaceTuple) -> None:
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

    def test_non_blocking_skips(self, namespace: LocalNamespaceTuple) -> None:
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

    def test_identical_hashes_skip(self, namespace: LocalNamespaceTuple) -> None:
        result = emit_parity_drift_detected(
            mission_slug="042-feature",
            local_parity_hash="c" * 64,
            baseline_parity_hash="c" * 64,
            severity="warning",
            namespace=namespace,
        )
        assert result is None


# ── Wire-payload Pydantic models reject extras (canonical sub-objects) ─


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
