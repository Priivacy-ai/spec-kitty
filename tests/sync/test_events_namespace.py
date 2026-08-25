"""Tests for namespace gating in dossier event emission.

Delivery was removed with the sync transport, so the observable contract is
the gate: a valid call validates and drops (returns ``None``), and a missing
namespace refuses before validation instead of producing an envelope no
consumer ever asked for.
"""

from __future__ import annotations

import pytest

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
    def test_accepts_namespace_and_drops(self) -> None:
        result = emit_artifact_indexed(
            mission_slug="047-feat",
            artifact_key="input.spec",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256=VALID_HASH,
            size_bytes=100,
            namespace=_make_namespace_dict(),
        )
        assert result is None

    def test_refuses_to_emit_without_namespace(self) -> None:
        # spec-kitty-events >= 5.0.0 required ``namespace``; the emitter still
        # refuses rather than produce an envelope with no namespace.
        result = emit_artifact_indexed(
            mission_slug="047-feat",
            artifact_key="input.spec",
            artifact_class="input",
            relative_path="spec.md",
            content_hash_sha256=VALID_HASH,
            size_bytes=100,
        )
        assert result is None


class TestArtifactMissingNamespace:
    def test_accepts_namespace_and_drops(self) -> None:
        result = emit_artifact_missing(
            mission_slug="047-feat",
            artifact_key="input.spec",
            artifact_class="input",
            expected_path_pattern="spec.md",
            reason_code="not_found",
            blocking=True,
            namespace=_make_namespace_dict(),
        )
        assert result is None

    def test_refuses_to_emit_without_namespace(self) -> None:
        result = emit_artifact_missing(
            mission_slug="047-feat",
            artifact_key="input.spec",
            artifact_class="input",
            expected_path_pattern="spec.md",
            reason_code="not_found",
            blocking=True,
        )
        assert result is None


class TestSnapshotComputedNamespace:
    def test_accepts_namespace_and_drops(self) -> None:
        result = emit_snapshot_computed(
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
            namespace=_make_namespace_dict(),
        )
        assert result is None


class TestParityDriftNamespace:
    def test_accepts_namespace_and_drops(self) -> None:
        result = emit_parity_drift_detected(
            mission_slug="047-feat",
            local_parity_hash=VALID_HASH,
            baseline_parity_hash="b" * 64,
            namespace=_make_namespace_dict(),
        )
        assert result is None
