"""Regression tests for timezone-aware dossier timestamps.

These tests keep coverage on datetime default factories and runtime timestamp
paths touched by the datetime.utcnow deprecation remediation.
"""

from __future__ import annotations

from datetime import UTC
from pathlib import Path
from uuid import uuid4

from specify_cli.dossier.drift_detector import capture_baseline
from specify_cli.dossier.indexer import Indexer
from specify_cli.dossier.manifest import ManifestRegistry
from specify_cli.dossier.models import ArtifactRef, MissionDossier, MissionDossierSnapshot
from specify_cli.dossier.snapshot import compute_snapshot
from specify_cli.sync.project_identity import ProjectIdentity

import pytest

pytestmark = pytest.mark.fast


def _sample_artifact() -> ArtifactRef:
    return ArtifactRef(
        artifact_key="input.spec.main",
        artifact_class="input",
        relative_path="spec.md",
        content_hash_sha256="a" * 64,
        size_bytes=12,
        required_status="required",
        is_present=True,
    )


def test_models_default_factories_use_timezone_aware_datetimes() -> None:
    artifact = _sample_artifact()
    dossier = MissionDossier(
        mission_type="software-dev",
        mission_run_id="run-1",
        mission_slug="042-sample",
        feature_dir="/tmp/feature",
        artifacts=[artifact],
        latest_snapshot=None,
        manifest=None,
    )
    snapshot = MissionDossierSnapshot(
        mission_slug="042-sample",
        parity_hash_sha256="b" * 64,
    )

    assert artifact.indexed_at.tzinfo == UTC
    assert dossier.dossier_created_at.tzinfo == UTC
    assert dossier.dossier_updated_at.tzinfo == UTC
    assert snapshot.computed_at.tzinfo == UTC


def test_compute_snapshot_sets_timezone_aware_timestamp() -> None:
    dossier = MissionDossier(
        mission_type="software-dev",
        mission_run_id="run-2",
        mission_slug="042-snapshot",
        feature_dir="/tmp/feature",
        artifacts=[_sample_artifact()],
        latest_snapshot=None,
        manifest={"required_always": []},
    )

    snapshot = compute_snapshot(dossier)
    assert snapshot.computed_at.tzinfo == UTC


def test_indexer_uses_timezone_aware_timestamps_for_updates_and_missing(tmp_path: Path) -> None:
    feature_dir = tmp_path / "042-indexer"
    feature_dir.mkdir()
    (feature_dir / "spec.md").write_text("# spec\n", encoding="utf-8")

    indexer = Indexer(ManifestRegistry())
    dossier = indexer.index_feature(feature_dir, "software-dev")

    assert dossier.dossier_updated_at.tzinfo == UTC

    # Force missing artifact materialization path to ensure ghost artifacts
    # receive timezone-aware indexed_at timestamps.
    dossier.artifacts = []
    missing = indexer._detect_missing_artifacts(dossier, step_id="plan")
    assert missing, "Expected manifest-driven missing artifacts for software-dev"
    assert all(a.indexed_at.tzinfo == UTC for a in missing)


def test_capture_baseline_uses_timezone_aware_timestamp(tmp_path: Path) -> None:
    snapshot = MissionDossierSnapshot(
        mission_slug="042-baseline",
        parity_hash_sha256="c" * 64,
    )
    identity = ProjectIdentity(
        project_uuid=uuid4(),
        project_slug="spec-kitty",
        node_id="abcdef123456",
    )

    baseline = capture_baseline(
        mission_slug="042-baseline",
        current_snapshot=snapshot,
        repo_root=tmp_path,
        project_identity=identity,
        target_branch="main",
        mission_type="software-dev",
        manifest_version="1",
    )

    assert baseline.captured_at.tzinfo == UTC
