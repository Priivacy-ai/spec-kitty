"""Unit tests for drift detection and baseline management.

Tests cover:
- BaselineKey computation and hashing (deterministic)
- BaselineSnapshot persistence (save/load JSON)
- Baseline acceptance logic (key matching, false positives)
- Drift detection (hash comparison)
- ParityDriftDetected event emission
- Baseline capture logic
- Multi-scenario validation (branch switches, manifest updates, multi-user)
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from uuid import UUID
from unittest.mock import MagicMock, patch

from specify_cli.dossier.drift_detector import (
    BaselineKey,
    BaselineSnapshot,
    compute_baseline_key,
    save_baseline,
    load_baseline,
    accept_baseline,
    detect_drift,
    emit_drift_if_detected,
    capture_baseline,
)
from specify_cli.dossier.models import MissionDossierSnapshot
from specify_cli.sync.project_identity import ProjectIdentity


class TestBaselineKey:
    """Test BaselineKey dataclass and methods."""

    def test_baseline_key_creation(self):
        """Create BaselineKey with all 6 components."""
        key = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        assert key.project_uuid == "550e8400-e29b-41d4-a716-446655440000"
        assert key.node_id == "abcdef123456"
        assert key.feature_slug == "042-local-mission-dossier"
        assert key.target_branch == "2.x"
        assert key.mission_key == "software-dev"
        assert key.manifest_version == "1"

    def test_baseline_key_to_dict(self):
        """to_dict() includes all 6 components."""
        key = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        d = key.to_dict()
        assert d["project_uuid"] == "550e8400-e29b-41d4-a716-446655440000"
        assert d["node_id"] == "abcdef123456"
        assert d["feature_slug"] == "042-local-mission-dossier"
        assert d["target_branch"] == "2.x"
        assert d["mission_key"] == "software-dev"
        assert d["manifest_version"] == "1"

    def test_baseline_key_compute_hash(self):
        """compute_hash() produces 64-char SHA256 hash."""
        key = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        hash_val = key.compute_hash()
        assert isinstance(hash_val, str)
        assert len(hash_val) == 64
        assert all(c in "0123456789abcdef" for c in hash_val)

    def test_baseline_key_hash_deterministic(self):
        """Same inputs → same hash (deterministic)."""
        key1 = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        key2 = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        assert key1.compute_hash() == key2.compute_hash()

    def test_baseline_key_hash_different_inputs(self):
        """Different inputs → different hash."""
        key1 = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        key2 = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440001",  # Different UUID
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        assert key1.compute_hash() != key2.compute_hash()

    def test_baseline_key_equality(self):
        """Equality comparison works correctly."""
        key1 = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        key2 = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        assert key1 == key2

    def test_baseline_key_inequality(self):
        """Inequality comparison works correctly."""
        key1 = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        key2 = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="main",  # Different branch
            mission_key="software-dev",
            manifest_version="1",
        )
        assert key1 != key2


class TestBaselineSnapshot:
    """Test BaselineSnapshot persistence and serialization."""

    def test_baseline_snapshot_creation(self):
        """Create BaselineSnapshot with all fields."""
        key = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        snapshot = BaselineSnapshot(
            baseline_key=key,
            baseline_key_hash=key.compute_hash(),
            parity_hash_sha256="a" * 64,
            captured_at=datetime(2026, 2, 21, 9, 0, 0),
            captured_by="abcdef123456",
        )
        assert snapshot.baseline_key == key
        assert snapshot.parity_hash_sha256 == "a" * 64

    def test_baseline_snapshot_to_dict(self):
        """to_dict() produces valid serialization."""
        key = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        snapshot = BaselineSnapshot(
            baseline_key=key,
            baseline_key_hash=key.compute_hash(),
            parity_hash_sha256="a" * 64,
            captured_at=datetime(2026, 2, 21, 9, 0, 0),
            captured_by="abcdef123456",
        )
        d = snapshot.to_dict()
        assert "baseline_key" in d
        assert "baseline_key_hash" in d
        assert "parity_hash_sha256" in d
        assert "captured_at" in d
        assert "captured_by" in d
        assert d["parity_hash_sha256"] == "a" * 64

    def test_baseline_snapshot_from_dict(self):
        """from_dict() reconstructs snapshot correctly."""
        data = {
            "baseline_key": {
                "project_uuid": "550e8400-e29b-41d4-a716-446655440000",
                "node_id": "abcdef123456",
                "feature_slug": "042-local-mission-dossier",
                "target_branch": "2.x",
                "mission_key": "software-dev",
                "manifest_version": "1",
            },
            "baseline_key_hash": "baseline_hash",
            "parity_hash_sha256": "a" * 64,
            "captured_at": "2026-02-21T09:00:00",
            "captured_by": "abcdef123456",
        }
        snapshot = BaselineSnapshot.from_dict(data)
        assert snapshot.baseline_key.project_uuid == "550e8400-e29b-41d4-a716-446655440000"
        assert snapshot.parity_hash_sha256 == "a" * 64
        assert snapshot.captured_by == "abcdef123456"

    def test_baseline_snapshot_round_trip(self):
        """Round-trip (to_dict, from_dict) preserves all fields."""
        key = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        snapshot1 = BaselineSnapshot(
            baseline_key=key,
            baseline_key_hash=key.compute_hash(),
            parity_hash_sha256="a" * 64,
            captured_at=datetime(2026, 2, 21, 9, 0, 0),
            captured_by="abcdef123456",
        )
        d = snapshot1.to_dict()
        snapshot2 = BaselineSnapshot.from_dict(d)
        assert snapshot2.baseline_key == snapshot1.baseline_key
        assert snapshot2.parity_hash_sha256 == snapshot1.parity_hash_sha256
        assert snapshot2.captured_by == snapshot1.captured_by


class TestBaselinePersistence:
    """Test baseline persistence to JSON file."""

    def test_save_baseline_creates_directory(self, tmp_path):
        """save_baseline() creates .kittify/dossiers/{feature_slug}/ directory."""
        key = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        snapshot = BaselineSnapshot(
            baseline_key=key,
            baseline_key_hash=key.compute_hash(),
            parity_hash_sha256="a" * 64,
            captured_at=datetime(2026, 2, 21, 9, 0, 0),
            captured_by="abcdef123456",
        )
        save_baseline("042-local-mission-dossier", snapshot, tmp_path)
        baseline_file = (
            tmp_path
            / ".kittify"
            / "dossiers"
            / "042-local-mission-dossier"
            / "parity-baseline.json"
        )
        assert baseline_file.exists()

    def test_save_baseline_writes_json(self, tmp_path):
        """save_baseline() writes valid JSON file."""
        key = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        snapshot = BaselineSnapshot(
            baseline_key=key,
            baseline_key_hash=key.compute_hash(),
            parity_hash_sha256="a" * 64,
            captured_at=datetime(2026, 2, 21, 9, 0, 0),
            captured_by="abcdef123456",
        )
        save_baseline("042-local-mission-dossier", snapshot, tmp_path)
        baseline_file = (
            tmp_path
            / ".kittify"
            / "dossiers"
            / "042-local-mission-dossier"
            / "parity-baseline.json"
        )
        with open(baseline_file) as f:
            data = json.load(f)
        assert data["parity_hash_sha256"] == "a" * 64
        assert data["baseline_key"]["feature_slug"] == "042-local-mission-dossier"

    def test_load_baseline_reads_json(self, tmp_path):
        """load_baseline() reads file without errors."""
        key = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        snapshot = BaselineSnapshot(
            baseline_key=key,
            baseline_key_hash=key.compute_hash(),
            parity_hash_sha256="a" * 64,
            captured_at=datetime(2026, 2, 21, 9, 0, 0),
            captured_by="abcdef123456",
        )
        save_baseline("042-local-mission-dossier", snapshot, tmp_path)
        loaded = load_baseline("042-local-mission-dossier", tmp_path)
        assert loaded is not None
        assert loaded.parity_hash_sha256 == "a" * 64
        assert loaded.baseline_key.feature_slug == "042-local-mission-dossier"

    def test_load_baseline_missing_file_returns_none(self, tmp_path):
        """load_baseline() returns None if file not found."""
        loaded = load_baseline("nonexistent-feature", tmp_path)
        assert loaded is None

    def test_save_load_round_trip(self, tmp_path):
        """Round-trip (save, load) preserves all fields."""
        key = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        snapshot1 = BaselineSnapshot(
            baseline_key=key,
            baseline_key_hash=key.compute_hash(),
            parity_hash_sha256="a" * 64,
            captured_at=datetime(2026, 2, 21, 9, 0, 0),
            captured_by="abcdef123456",
        )
        save_baseline("042-local-mission-dossier", snapshot1, tmp_path)
        snapshot2 = load_baseline("042-local-mission-dossier", tmp_path)
        assert snapshot2.baseline_key == snapshot1.baseline_key
        assert snapshot2.parity_hash_sha256 == snapshot1.parity_hash_sha256
        assert snapshot2.captured_by == snapshot1.captured_by


class TestBaselineAcceptance:
    """Test baseline acceptance logic (key matching)."""

    def test_accept_baseline_exact_match(self):
        """Exact match → accepted."""
        key = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        snapshot = BaselineSnapshot(
            baseline_key=key,
            baseline_key_hash=key.compute_hash(),
            parity_hash_sha256="a" * 64,
            captured_at=datetime(2026, 2, 21, 9, 0, 0),
            captured_by="abcdef123456",
        )
        current_key = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        accepted, reason = accept_baseline(snapshot, current_key)
        assert accepted is True
        assert reason is None

    def test_accept_baseline_project_uuid_differs(self):
        """project_uuid differs → rejected."""
        key = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        snapshot = BaselineSnapshot(
            baseline_key=key,
            baseline_key_hash=key.compute_hash(),
            parity_hash_sha256="a" * 64,
            captured_at=datetime(2026, 2, 21, 9, 0, 0),
            captured_by="abcdef123456",
        )
        current_key = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440001",  # Different
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        accepted, reason = accept_baseline(snapshot, current_key)
        assert accepted is False
        assert "project_uuid" in reason

    def test_accept_baseline_target_branch_differs(self):
        """target_branch differs → rejected (prevent false positives)."""
        key = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        snapshot = BaselineSnapshot(
            baseline_key=key,
            baseline_key_hash=key.compute_hash(),
            parity_hash_sha256="a" * 64,
            captured_at=datetime(2026, 2, 21, 9, 0, 0),
            captured_by="abcdef123456",
        )
        current_key = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="main",  # Different branch
            mission_key="software-dev",
            manifest_version="1",
        )
        accepted, reason = accept_baseline(snapshot, current_key)
        assert accepted is False
        assert "target_branch" in reason

    def test_accept_baseline_manifest_version_differs(self):
        """manifest_version differs → rejected."""
        key = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        snapshot = BaselineSnapshot(
            baseline_key=key,
            baseline_key_hash=key.compute_hash(),
            parity_hash_sha256="a" * 64,
            captured_at=datetime(2026, 2, 21, 9, 0, 0),
            captured_by="abcdef123456",
        )
        current_key = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="2",  # Different version
        )
        accepted, reason = accept_baseline(snapshot, current_key)
        assert accepted is False
        assert "manifest_version" in reason

    def test_accept_baseline_node_id_differs(self):
        """node_id differs → rejected (multi-user safe)."""
        key = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="abcdef123456",
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        snapshot = BaselineSnapshot(
            baseline_key=key,
            baseline_key_hash=key.compute_hash(),
            parity_hash_sha256="a" * 64,
            captured_at=datetime(2026, 2, 21, 9, 0, 0),
            captured_by="abcdef123456",
        )
        current_key = BaselineKey(
            project_uuid="550e8400-e29b-41d4-a716-446655440000",
            node_id="different_node",  # Different machine
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        accepted, reason = accept_baseline(snapshot, current_key)
        assert accepted is False
        assert "node_id" in reason


class TestDriftDetection:
    """Test drift detection (hash comparison)."""

    def test_detect_drift_same_hash_no_drift(self, tmp_path):
        """Same hash → no drift."""
        project_identity = ProjectIdentity(
            project_uuid=UUID("550e8400-e29b-41d4-a716-446655440000"),
            project_slug="test-project",
            node_id="abcdef123456",
        )
        key = BaselineKey(
            project_uuid=str(project_identity.project_uuid),
            node_id=project_identity.node_id,
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        baseline = BaselineSnapshot(
            baseline_key=key,
            baseline_key_hash=key.compute_hash(),
            parity_hash_sha256="a" * 64,
            captured_at=datetime.utcnow(),
            captured_by="abcdef123456",
        )
        save_baseline("042-local-mission-dossier", baseline, tmp_path)

        snapshot = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="a" * 64,
        )
        has_drift, drift_info = detect_drift(
            feature_slug="042-local-mission-dossier",
            current_snapshot=snapshot,
            repo_root=tmp_path,
            project_identity=project_identity,
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        assert has_drift is False
        assert drift_info is None

    def test_detect_drift_different_hash_drift_detected(self, tmp_path):
        """Different hash → drift detected."""
        project_identity = ProjectIdentity(
            project_uuid=UUID("550e8400-e29b-41d4-a716-446655440000"),
            project_slug="test-project",
            node_id="abcdef123456",
        )
        key = BaselineKey(
            project_uuid=str(project_identity.project_uuid),
            node_id=project_identity.node_id,
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        baseline = BaselineSnapshot(
            baseline_key=key,
            baseline_key_hash=key.compute_hash(),
            parity_hash_sha256="a" * 64,  # Baseline hash
            captured_at=datetime.utcnow(),
            captured_by="abcdef123456",
        )
        save_baseline("042-local-mission-dossier", baseline, tmp_path)

        snapshot = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="b" * 64,  # Different hash
        )
        has_drift, drift_info = detect_drift(
            feature_slug="042-local-mission-dossier",
            current_snapshot=snapshot,
            repo_root=tmp_path,
            project_identity=project_identity,
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        assert has_drift is True
        assert drift_info is not None
        assert drift_info["local_parity_hash"] == "b" * 64
        assert drift_info["baseline_parity_hash"] == "a" * 64

    def test_detect_drift_no_baseline(self, tmp_path):
        """No baseline → no drift (return False)."""
        project_identity = ProjectIdentity(
            project_uuid=UUID("550e8400-e29b-41d4-a716-446655440000"),
            project_slug="test-project",
            node_id="abcdef123456",
        )
        snapshot = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="a" * 64,
        )
        has_drift, drift_info = detect_drift(
            feature_slug="042-local-mission-dossier",
            current_snapshot=snapshot,
            repo_root=tmp_path,
            project_identity=project_identity,
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        assert has_drift is False
        assert drift_info is None

    def test_detect_drift_baseline_rejected_no_drift(self, tmp_path):
        """Baseline key mismatch → baseline rejected (no drift event)."""
        project_identity = ProjectIdentity(
            project_uuid=UUID("550e8400-e29b-41d4-a716-446655440000"),
            project_slug="test-project",
            node_id="abcdef123456",
        )
        # Create baseline with old branch
        old_key = BaselineKey(
            project_uuid=str(project_identity.project_uuid),
            node_id=project_identity.node_id,
            feature_slug="042-local-mission-dossier",
            target_branch="main",  # Old branch
            mission_key="software-dev",
            manifest_version="1",
        )
        baseline = BaselineSnapshot(
            baseline_key=old_key,
            baseline_key_hash=old_key.compute_hash(),
            parity_hash_sha256="a" * 64,
            captured_at=datetime.utcnow(),
            captured_by="abcdef123456",
        )
        save_baseline("042-local-mission-dossier", baseline, tmp_path)

        # Snapshot with different hash but new branch
        snapshot = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="b" * 64,
        )
        has_drift, drift_info = detect_drift(
            feature_slug="042-local-mission-dossier",
            current_snapshot=snapshot,
            repo_root=tmp_path,
            project_identity=project_identity,
            target_branch="2.x",  # New branch
            mission_key="software-dev",
            manifest_version="1",
        )
        # Should return no drift because baseline is rejected
        assert has_drift is False
        assert drift_info is None


class TestCaptureBaseline:
    """Test baseline capture logic."""

    def test_capture_baseline_creates_snapshot(self, tmp_path):
        """capture_baseline() creates BaselineSnapshot."""
        project_identity = ProjectIdentity(
            project_uuid=UUID("550e8400-e29b-41d4-a716-446655440000"),
            project_slug="test-project",
            node_id="abcdef123456",
        )
        snapshot = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="a" * 64,
        )
        baseline = capture_baseline(
            feature_slug="042-local-mission-dossier",
            current_snapshot=snapshot,
            repo_root=tmp_path,
            project_identity=project_identity,
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        assert baseline is not None
        assert baseline.parity_hash_sha256 == "a" * 64
        assert baseline.captured_by == "abcdef123456"

    def test_capture_baseline_saves_to_file(self, tmp_path):
        """capture_baseline() saves baseline to correct file."""
        project_identity = ProjectIdentity(
            project_uuid=UUID("550e8400-e29b-41d4-a716-446655440000"),
            project_slug="test-project",
            node_id="abcdef123456",
        )
        snapshot = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="a" * 64,
        )
        capture_baseline(
            feature_slug="042-local-mission-dossier",
            current_snapshot=snapshot,
            repo_root=tmp_path,
            project_identity=project_identity,
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        baseline_file = (
            tmp_path
            / ".kittify"
            / "dossiers"
            / "042-local-mission-dossier"
            / "parity-baseline.json"
        )
        assert baseline_file.exists()

    def test_capture_baseline_key_hash_correct(self, tmp_path):
        """capture_baseline() computes baseline_key_hash correctly."""
        project_identity = ProjectIdentity(
            project_uuid=UUID("550e8400-e29b-41d4-a716-446655440000"),
            project_slug="test-project",
            node_id="abcdef123456",
        )
        snapshot = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="a" * 64,
        )
        baseline = capture_baseline(
            feature_slug="042-local-mission-dossier",
            current_snapshot=snapshot,
            repo_root=tmp_path,
            project_identity=project_identity,
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        expected_hash = baseline.baseline_key.compute_hash()
        assert baseline.baseline_key_hash == expected_hash

    def test_capture_baseline_captured_at_recent(self, tmp_path):
        """capture_baseline() sets captured_at to recent timestamp."""
        project_identity = ProjectIdentity(
            project_uuid=UUID("550e8400-e29b-41d4-a716-446655440000"),
            project_slug="test-project",
            node_id="abcdef123456",
        )
        snapshot = MissionDossierSnapshot(
            feature_slug="042-local-mission-dossier",
            parity_hash_sha256="a" * 64,
        )
        before = datetime.utcnow()
        baseline = capture_baseline(
            feature_slug="042-local-mission-dossier",
            current_snapshot=snapshot,
            repo_root=tmp_path,
            project_identity=project_identity,
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
        )
        after = datetime.utcnow()
        assert before <= baseline.captured_at <= after


class TestComputeBaselineKey:
    """Test compute_baseline_key() helper function."""

    def test_compute_baseline_key(self):
        """compute_baseline_key() creates valid BaselineKey."""
        project_identity = ProjectIdentity(
            project_uuid=UUID("550e8400-e29b-41d4-a716-446655440000"),
            project_slug="test-project",
            node_id="abcdef123456",
        )
        key = compute_baseline_key(
            feature_slug="042-local-mission-dossier",
            target_branch="2.x",
            mission_key="software-dev",
            manifest_version="1",
            project_identity=project_identity,
        )
        assert key.project_uuid == str(project_identity.project_uuid)
        assert key.node_id == project_identity.node_id
        assert key.feature_slug == "042-local-mission-dossier"
        assert key.target_branch == "2.x"
        assert key.mission_key == "software-dev"
        assert key.manifest_version == "1"
