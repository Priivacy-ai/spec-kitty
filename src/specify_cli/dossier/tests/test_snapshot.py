"""Tests for snapshot computation and parity hash (WP05).

Test coverage:
- T023: Deterministic snapshot computation
- T024: Order-independent parity hash algorithm
- T025: Snapshot persistence (save/load)
- T026: Snapshot reproducibility validation
- T027: Snapshot equality comparison
"""

import json
import random
from datetime import datetime, timezone
from pathlib import Path

import pytest

from specify_cli.dossier.models import ArtifactRef, MissionDossier, MissionDossierSnapshot
from specify_cli.dossier.snapshot import (
    compute_snapshot,
    compute_parity_hash_from_dossier,
    get_parity_hash_components,
    save_snapshot,
    load_snapshot,
    get_latest_snapshot,
)


class TestComputeSnapshotDeterministic:
    """T023: Deterministic snapshot computation"""

    def test_snapshot_computes_without_errors(self):
        """Snapshot should compute without errors for valid dossier."""
        dossier = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="test-run-001",
            feature_slug="042-local-mission-dossier",
            feature_dir="/test/feature",
            artifacts=[
                ArtifactRef(
                    artifact_key="spec.main",
                    artifact_class="input",
                    relative_path="spec.md",
                    content_hash_sha256="a" * 64,
                    size_bytes=1000,
                    required_status="required",
                    is_present=True,
                ),
            ],
            manifest={"test": "manifest"},
        )

        snapshot = compute_snapshot(dossier)

        assert snapshot is not None
        assert snapshot.feature_slug == "042-local-mission-dossier"
        assert snapshot.total_artifacts == 1

    def test_artifact_counts_accurate(self):
        """Artifact counts should be accurate."""
        artifacts = []
        # Create 10 required, 8 present
        for i in range(10):
            artifacts.append(
                ArtifactRef(
                    artifact_key=f"required-{i}",
                    artifact_class="input",
                    relative_path=f"required-{i}.md",
                    content_hash_sha256=hex(i)[2:].zfill(64),
                    size_bytes=1000 + i,
                    required_status="required",
                    is_present=i < 8,  # First 8 present, last 2 missing
                )
            )

        # Create 5 optional, 3 present
        for i in range(5):
            artifacts.append(
                ArtifactRef(
                    artifact_key=f"optional-{i}",
                    artifact_class="output",
                    relative_path=f"optional-{i}.md",
                    content_hash_sha256=hex(10 + i)[2:].zfill(64),
                    size_bytes=2000 + i,
                    required_status="optional",
                    is_present=i < 3,  # First 3 present, last 2 missing
                )
            )

        dossier = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="test-run-002",
            feature_slug="042-local-mission-dossier",
            feature_dir="/test/feature",
            artifacts=artifacts,
            manifest={"test": "manifest"},
        )

        snapshot = compute_snapshot(dossier)

        assert snapshot.total_artifacts == 15
        assert snapshot.required_artifacts == 10
        assert snapshot.required_present == 8
        assert snapshot.required_missing == 2
        assert snapshot.optional_artifacts == 5
        assert snapshot.optional_present == 3

    def test_completeness_status_complete(self):
        """Completeness status should be 'complete' when all required present."""
        artifacts = [
            ArtifactRef(
                artifact_key="required-1",
                artifact_class="input",
                relative_path="required-1.md",
                content_hash_sha256="a" * 64,
                size_bytes=1000,
                required_status="required",
                is_present=True,
            ),
            ArtifactRef(
                artifact_key="required-2",
                artifact_class="input",
                relative_path="required-2.md",
                content_hash_sha256="b" * 64,
                size_bytes=2000,
                required_status="required",
                is_present=True,
            ),
        ]

        dossier = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="test-run-003",
            feature_slug="042-local-mission-dossier",
            feature_dir="/test/feature",
            artifacts=artifacts,
            manifest={"test": "manifest"},
        )

        snapshot = compute_snapshot(dossier)
        assert snapshot.completeness_status == "complete"

    def test_completeness_status_incomplete(self):
        """Completeness status should be 'incomplete' when required missing."""
        artifacts = [
            ArtifactRef(
                artifact_key="required-1",
                artifact_class="input",
                relative_path="required-1.md",
                content_hash_sha256="a" * 64,
                size_bytes=1000,
                required_status="required",
                is_present=True,
            ),
            ArtifactRef(
                artifact_key="required-2",
                artifact_class="input",
                relative_path="required-2.md",
                content_hash_sha256="b" * 64,
                size_bytes=2000,
                required_status="required",
                is_present=False,
                error_reason="not_found",
            ),
        ]

        dossier = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="test-run-004",
            feature_slug="042-local-mission-dossier",
            feature_dir="/test/feature",
            artifacts=artifacts,
            manifest={"test": "manifest"},
        )

        snapshot = compute_snapshot(dossier)
        assert snapshot.completeness_status == "incomplete"

    def test_completeness_status_unknown_no_manifest(self):
        """Completeness status should be 'unknown' when no manifest."""
        artifacts = [
            ArtifactRef(
                artifact_key="artifact-1",
                artifact_class="input",
                relative_path="artifact-1.md",
                content_hash_sha256="a" * 64,
                size_bytes=1000,
                required_status="required",
                is_present=True,
            ),
        ]

        dossier = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="test-run-005",
            feature_slug="042-local-mission-dossier",
            feature_dir="/test/feature",
            artifacts=artifacts,
            manifest=None,
        )

        snapshot = compute_snapshot(dossier)
        assert snapshot.completeness_status == "unknown"

    def test_artifact_summaries_complete(self):
        """Artifact summaries should include all required fields."""
        artifacts = [
            ArtifactRef(
                artifact_key="spec.main",
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=1000,
                wp_id="WP01",
                step_id="planning",
                required_status="required",
                is_present=True,
                error_reason=None,
            ),
        ]

        dossier = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="test-run-006",
            feature_slug="042-local-mission-dossier",
            feature_dir="/test/feature",
            artifacts=artifacts,
            manifest={"test": "manifest"},
        )

        snapshot = compute_snapshot(dossier)

        assert len(snapshot.artifact_summaries) == 1
        summary = snapshot.artifact_summaries[0]
        assert summary["artifact_key"] == "spec.main"
        assert summary["artifact_class"] == "input"
        assert summary["wp_id"] == "WP01"
        assert summary["step_id"] == "planning"
        assert summary["is_present"] is True
        assert summary["error_reason"] is None

    def test_artifacts_sorted_by_key(self):
        """Artifacts should be sorted by artifact_key in summaries."""
        artifacts = [
            ArtifactRef(
                artifact_key="z-artifact",
                artifact_class="input",
                relative_path="z.md",
                content_hash_sha256="a" * 64,
                size_bytes=1000,
                required_status="optional",
                is_present=True,
            ),
            ArtifactRef(
                artifact_key="a-artifact",
                artifact_class="input",
                relative_path="a.md",
                content_hash_sha256="b" * 64,
                size_bytes=1000,
                required_status="optional",
                is_present=True,
            ),
            ArtifactRef(
                artifact_key="m-artifact",
                artifact_class="input",
                relative_path="m.md",
                content_hash_sha256="c" * 64,
                size_bytes=1000,
                required_status="optional",
                is_present=True,
            ),
        ]

        dossier = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="test-run-007",
            feature_slug="042-local-mission-dossier",
            feature_dir="/test/feature",
            artifacts=artifacts,
            manifest={"test": "manifest"},
        )

        snapshot = compute_snapshot(dossier)

        keys = [s["artifact_key"] for s in snapshot.artifact_summaries]
        assert keys == ["a-artifact", "m-artifact", "z-artifact"]


class TestParityHashAlgorithm:
    """T024: Order-independent parity hash algorithm"""

    def test_parity_hash_deterministic_single_artifact(self):
        """Parity hash should be deterministic for single artifact."""
        artifacts = [
            ArtifactRef(
                artifact_key="spec.main",
                artifact_class="input",
                relative_path="spec.md",
                content_hash_sha256="a" * 64,
                size_bytes=1000,
                required_status="required",
                is_present=True,
            ),
        ]

        dossier = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="test-run-008",
            feature_slug="042-local-mission-dossier",
            feature_dir="/test/feature",
            artifacts=artifacts,
            manifest={"test": "manifest"},
        )

        hash1 = compute_parity_hash_from_dossier(dossier)
        hash2 = compute_parity_hash_from_dossier(dossier)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 is 64 hex characters

    def test_parity_hash_order_independence(self):
        """Same artifacts in different order should produce same parity hash."""
        # Create 30 artifacts
        artifacts = [
            ArtifactRef(
                artifact_key=f"artifact-{i:02d}",
                artifact_class="input",
                relative_path=f"artifact-{i:02d}.md",
                content_hash_sha256=hex(i)[2:].zfill(64),
                size_bytes=1000 + i,
                required_status="optional",
                is_present=True,
            )
            for i in range(30)
        ]

        # Compute hash with original order
        dossier1 = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="test-run-009",
            feature_slug="042-local-mission-dossier",
            feature_dir="/test/feature",
            artifacts=artifacts,
            manifest={"test": "manifest"},
        )
        hash1 = compute_parity_hash_from_dossier(dossier1)

        # Compute hash with shuffled order
        shuffled_artifacts = artifacts.copy()
        random.shuffle(shuffled_artifacts)

        dossier2 = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="test-run-009b",
            feature_slug="042-local-mission-dossier",
            feature_dir="/test/feature",
            artifacts=shuffled_artifacts,
            manifest={"test": "manifest"},
        )
        hash2 = compute_parity_hash_from_dossier(dossier2)

        assert hash1 == hash2

    def test_parity_hash_different_artifacts_different_hash(self):
        """Different artifacts should produce different parity hash."""
        artifacts1 = [
            ArtifactRef(
                artifact_key="artifact-1",
                artifact_class="input",
                relative_path="artifact-1.md",
                content_hash_sha256="a" * 64,
                size_bytes=1000,
                required_status="optional",
                is_present=True,
            ),
        ]

        dossier1 = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="test-run-010",
            feature_slug="042-local-mission-dossier",
            feature_dir="/test/feature",
            artifacts=artifacts1,
            manifest={"test": "manifest"},
        )
        hash1 = compute_parity_hash_from_dossier(dossier1)

        artifacts2 = [
            ArtifactRef(
                artifact_key="artifact-2",
                artifact_class="input",
                relative_path="artifact-2.md",
                content_hash_sha256="b" * 64,
                size_bytes=1000,
                required_status="optional",
                is_present=True,
            ),
        ]

        dossier2 = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="test-run-011",
            feature_slug="042-local-mission-dossier",
            feature_dir="/test/feature",
            artifacts=artifacts2,
            manifest={"test": "manifest"},
        )
        hash2 = compute_parity_hash_from_dossier(dossier2)

        assert hash1 != hash2

    def test_missing_artifacts_excluded_from_parity(self):
        """Missing artifacts should be excluded from parity hash."""
        artifacts = [
            ArtifactRef(
                artifact_key="present-1",
                artifact_class="input",
                relative_path="present-1.md",
                content_hash_sha256="a" * 64,
                size_bytes=1000,
                required_status="optional",
                is_present=True,
            ),
            ArtifactRef(
                artifact_key="missing-1",
                artifact_class="input",
                relative_path="missing-1.md",
                content_hash_sha256="b" * 64,
                size_bytes=1000,
                required_status="optional",
                is_present=False,
                error_reason="not_found",
            ),
        ]

        dossier_with_missing = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="test-run-012",
            feature_slug="042-local-mission-dossier",
            feature_dir="/test/feature",
            artifacts=artifacts,
            manifest={"test": "manifest"},
        )

        # Dossier with only present artifact
        artifacts_present_only = [artifacts[0]]
        dossier_present_only = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="test-run-013",
            feature_slug="042-local-mission-dossier",
            feature_dir="/test/feature",
            artifacts=artifacts_present_only,
            manifest={"test": "manifest"},
        )

        hash_with_missing = compute_parity_hash_from_dossier(dossier_with_missing)
        hash_present_only = compute_parity_hash_from_dossier(dossier_present_only)

        assert hash_with_missing == hash_present_only

    def test_duplicate_hashes_included(self):
        """Duplicate artifact hashes should be included (not deduplicated)."""
        # Two artifacts with identical content hash
        artifacts = [
            ArtifactRef(
                artifact_key="artifact-1",
                artifact_class="input",
                relative_path="artifact-1.md",
                content_hash_sha256="a" * 64,
                size_bytes=1000,
                required_status="optional",
                is_present=True,
            ),
            ArtifactRef(
                artifact_key="artifact-2",
                artifact_class="input",
                relative_path="artifact-2.md",
                content_hash_sha256="a" * 64,  # Same hash
                size_bytes=1000,
                required_status="optional",
                is_present=True,
            ),
        ]

        dossier = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="test-run-014",
            feature_slug="042-local-mission-dossier",
            feature_dir="/test/feature",
            artifacts=artifacts,
            manifest={"test": "manifest"},
        )

        components = get_parity_hash_components(dossier)
        assert len(components) == 2  # Both hashes included, not deduplicated
        assert components[0] == "a" * 64
        assert components[1] == "a" * 64


class TestSnapshotPersistence:
    """T025: Snapshot persistence (save/load)"""

    def test_snapshot_saves_to_correct_path(self, tmp_path):
        """Snapshot should save to correct file path."""
        snapshot = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="a" * 64,
            completeness_status="complete",
        )

        save_snapshot(snapshot, tmp_path)

        expected_file = (
            tmp_path
            / ".kittify"
            / "dossiers"
            / "042-local-mission-dossier"
            / "snapshot-latest.json"
        )
        assert expected_file.exists()

    def test_snapshot_loads_from_json(self, tmp_path):
        """Snapshot should load from JSON without errors."""
        snapshot = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="a" * 64,
            completeness_status="complete",
            total_artifacts=5,
            required_artifacts=3,
        )

        save_snapshot(snapshot, tmp_path)

        loaded = load_snapshot(tmp_path, "042-local-mission-dossier")

        assert loaded is not None
        assert loaded.feature_slug == "042-local-mission-dossier"
        assert loaded.parity_hash_sha256 == "a" * 64
        assert loaded.completeness_status == "complete"
        assert loaded.total_artifacts == 5

    def test_snapshot_roundtrip_preserves_all_fields(self, tmp_path):
        """Round-trip (save, load) should preserve all fields."""
        snapshot = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="a" * 64,
            completeness_status="incomplete",
            total_artifacts=10,
            required_artifacts=7,
            required_present=5,
            required_missing=2,
            optional_artifacts=3,
            optional_present=2,
            parity_hash_components=["b" * 64, "c" * 64],
            artifact_summaries=[
                {"artifact_key": "test", "artifact_class": "input", "is_present": True}
            ],
        )

        save_snapshot(snapshot, tmp_path)
        loaded = load_snapshot(tmp_path, "042-local-mission-dossier")

        assert loaded.total_artifacts == snapshot.total_artifacts
        assert loaded.required_artifacts == snapshot.required_artifacts
        assert loaded.required_present == snapshot.required_present
        assert loaded.required_missing == snapshot.required_missing
        assert loaded.optional_artifacts == snapshot.optional_artifacts
        assert loaded.optional_present == snapshot.optional_present
        assert loaded.parity_hash_components == snapshot.parity_hash_components
        assert loaded.artifact_summaries == snapshot.artifact_summaries

    def test_load_missing_file_returns_none(self, tmp_path):
        """Loading non-existent snapshot should return None."""
        loaded = load_snapshot(tmp_path, "nonexistent-feature")
        assert loaded is None

    def test_get_latest_snapshot_convenience_alias(self, tmp_path):
        """get_latest_snapshot should work as convenience alias."""
        snapshot = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="a" * 64,
            completeness_status="complete",
        )

        save_snapshot(snapshot, tmp_path)

        loaded = get_latest_snapshot(tmp_path, "042-local-mission-dossier")

        assert loaded is not None
        assert loaded.parity_hash_sha256 == "a" * 64


class TestSnapshotReproducibility:
    """T026: Snapshot reproducibility validation"""

    def test_snapshot_reproducibility_multiple_runs(self):
        """Same content, multiple runs should produce identical snapshot."""
        artifacts = [
            ArtifactRef(
                artifact_key=f"artifact-{i}",
                artifact_class="input",
                relative_path=f"artifact-{i}.md",
                content_hash_sha256=hex(i)[2:].zfill(64),
                size_bytes=1000 + i,
                required_status="required" if i < 20 else "optional",
                is_present=i < 25,
            )
            for i in range(30)
        ]

        # Snapshot 1
        dossier1 = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="test-run-015",
            feature_slug="042-local-mission-dossier",
            feature_dir="/test/feature",
            artifacts=artifacts,
            manifest={"test": "manifest"},
        )
        snapshot1 = compute_snapshot(dossier1)

        # Snapshot 2 (same content)
        dossier2 = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="test-run-016",
            feature_slug="042-local-mission-dossier",
            feature_dir="/test/feature",
            artifacts=artifacts,
            manifest={"test": "manifest"},
        )
        snapshot2 = compute_snapshot(dossier2)

        # Hashes should be identical
        assert snapshot1.parity_hash_sha256 == snapshot2.parity_hash_sha256
        assert snapshot1.completeness_status == snapshot2.completeness_status
        assert snapshot1.total_artifacts == snapshot2.total_artifacts
        assert snapshot1.required_present == snapshot2.required_present

    def test_snapshot_reproducibility_order_independence(self):
        """Different artifact ordering should produce identical snapshot."""
        artifacts = [
            ArtifactRef(
                artifact_key=f"artifact-{i}",
                artifact_class="input",
                relative_path=f"artifact-{i}.md",
                content_hash_sha256=hex(i)[2:].zfill(64),
                size_bytes=1000 + i,
                required_status="optional",
                is_present=True,
            )
            for i in range(30)
        ]

        # Snapshot 1: original order
        dossier1 = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="test-run-017",
            feature_slug="042-local-mission-dossier",
            feature_dir="/test/feature",
            artifacts=artifacts,
            manifest={"test": "manifest"},
        )
        snapshot1 = compute_snapshot(dossier1)

        # Snapshot 2: shuffled order
        shuffled = artifacts.copy()
        random.shuffle(shuffled)
        dossier2 = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="test-run-018",
            feature_slug="042-local-mission-dossier",
            feature_dir="/test/feature",
            artifacts=shuffled,
            manifest={"test": "manifest"},
        )
        snapshot2 = compute_snapshot(dossier2)

        assert snapshot1.parity_hash_sha256 == snapshot2.parity_hash_sha256


class TestSnapshotEquality:
    """T027: Snapshot equality comparison"""

    def test_same_parity_hash_equal_snapshots(self):
        """Snapshots with same parity hash should be equal."""
        snapshot1 = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="a" * 64,
            completeness_status="complete",
        )

        snapshot2 = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="a" * 64,
            completeness_status="complete",
        )

        assert snapshot1 == snapshot2

    def test_different_parity_hash_unequal_snapshots(self):
        """Snapshots with different parity hash should be unequal."""
        snapshot1 = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="a" * 64,
            completeness_status="complete",
        )

        snapshot2 = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="b" * 64,
            completeness_status="complete",
        )

        assert snapshot1 != snapshot2

    def test_snapshot_equality_ignores_timestamp(self):
        """Equality should ignore timestamp differences."""
        now = datetime.now(timezone.utc)
        snapshot1 = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="a" * 64,
            completeness_status="complete",
            computed_at=now,
        )

        # Different timestamp
        snapshot2 = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="a" * 64,
            completeness_status="complete",
            computed_at=datetime(2020, 1, 1),
        )

        assert snapshot1 == snapshot2

    def test_snapshot_equality_ignores_id(self):
        """Equality should ignore snapshot_id differences."""
        snapshot1 = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            snapshot_id="id-1",
            parity_hash_sha256="a" * 64,
            completeness_status="complete",
        )

        snapshot2 = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            snapshot_id="id-2",
            parity_hash_sha256="a" * 64,
            completeness_status="complete",
        )

        assert snapshot1 == snapshot2

    def test_snapshot_equality_requires_same_completeness_status(self):
        """Equality requires same completeness status."""
        snapshot1 = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="a" * 64,
            completeness_status="complete",
        )

        snapshot2 = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="a" * 64,
            completeness_status="incomplete",
        )

        assert snapshot1 != snapshot2

    def test_snapshot_has_parity_diff(self):
        """has_parity_diff should detect parity differences."""
        snapshot1 = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="a" * 64,
            completeness_status="complete",
        )

        snapshot2 = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="b" * 64,
            completeness_status="complete",
        )

        assert snapshot1.has_parity_diff(snapshot2)

    def test_snapshot_equality_with_non_snapshot_returns_false(self):
        """Equality with non-snapshot object should return False."""
        snapshot = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="a" * 64,
            completeness_status="complete",
        )

        assert snapshot != "not a snapshot"
        assert snapshot != 123
        assert snapshot != None

    def test_snapshot_hash_for_set_usage(self):
        """Snapshot should be hashable for set/dict usage."""
        snapshot1 = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="a" * 64,
            completeness_status="complete",
        )

        snapshot2 = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="b" * 64,
            completeness_status="complete",
        )

        snapshot_set = {snapshot1, snapshot2}
        assert len(snapshot_set) == 2
        assert snapshot1 in snapshot_set


class TestLargeSnapshot:
    """Test with 30+ artifacts"""

    def test_snapshot_computes_for_30_plus_artifacts(self):
        """Snapshot should compute without errors for 30+ artifacts."""
        artifacts = [
            ArtifactRef(
                artifact_key=f"artifact-{i:03d}",
                artifact_class="input" if i % 3 == 0 else "output",
                relative_path=f"artifact-{i:03d}.md",
                content_hash_sha256=hex(i)[2:].zfill(64),
                size_bytes=1000 + i,
                wp_id=f"WP{(i % 10) + 1:02d}",
                step_id="planning" if i % 2 == 0 else "implementation",
                required_status="required" if i < 20 else "optional",
                is_present=i < 28,
                error_reason="not_found" if i >= 28 else None,
            )
            for i in range(35)
        ]

        dossier = MissionDossier(
            mission_slug="software-dev",
            mission_run_id="test-run-019",
            feature_slug="042-local-mission-dossier",
            feature_dir="/test/feature",
            artifacts=artifacts,
            manifest={"test": "manifest"},
        )

        snapshot = compute_snapshot(dossier)

        assert snapshot.total_artifacts == 35
        assert snapshot.required_artifacts == 20
        assert snapshot.required_present == 20
        assert snapshot.required_missing == 0
        assert snapshot.optional_artifacts == 15
        assert snapshot.optional_present == 8
        assert snapshot.completeness_status == "complete"
        assert len(snapshot.parity_hash_sha256) == 64
        assert len(snapshot.artifact_summaries) == 35
