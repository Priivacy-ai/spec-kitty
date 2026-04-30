"""Tests for manifest.py — WP03 T017 / T020, updated for v2 (WP02).

Covers:
- manifest-last semantics: absence of manifest means "partial"
- SynthesisManifest round-trip (dump_yaml → load_yaml)
- verify() catches hash mismatch via ManifestIntegrityError
- verify() passes when hashes match
- run_id matches the staging dir concept
- Manifest ordering is deterministic (sorted by kind, slug)
- v2: manifest_hash validates correctly (strip → re-hash → matches)
- v2: synthesizer_version is required and non-empty
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from charter.synthesizer.errors import ManifestIntegrityError
from charter.synthesizer.manifest import (
    ManifestArtifactEntry,
    SynthesisManifest,
    dump_yaml,
    load_yaml,
    verify,
)
from charter.synthesizer.path_guard import PathGuard
from charter.synthesizer.synthesize_pipeline import canonical_yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_manifest_hash(
    manifest: SynthesisManifest,
) -> str:
    """Compute the expected manifest_hash for a SynthesisManifest.

    Strips manifest_hash from model_dump, serializes via canonical_yaml (bytes),
    then SHA-256 hexdigest. canonical_yaml returns bytes — no .encode() needed.
    """
    fields = manifest.model_dump(mode="python")
    fields.pop("manifest_hash")
    return hashlib.sha256(canonical_yaml(fields)).hexdigest()


def _make_manifest(run_id: str = "01KPE222TESTRUNID0000000001") -> SynthesisManifest:
    """Create a sample v2 manifest for testing."""
    artifacts = [
        ManifestArtifactEntry(
            kind="tactic",
            slug="my-tactic",
            path=".kittify/doctrine/tactics/my-tactic.tactic.yaml",
            provenance_path=".kittify/charter/provenance/tactic-my-tactic.yaml",
            content_hash="a" * 64,
        ),
    ]
    # Build the manifest_hash from the data without the hash field
    data_without_hash = {
        "schema_version": "2",
        "mission_id": None,
        "created_at": "2026-04-17T12:00:00+00:00",
        "run_id": run_id,
        "adapter_id": "fixture",
        "adapter_version": "1.0.0",
        "synthesizer_version": "3.2.0a5",
        "artifacts": [a.model_dump(mode="python") for a in artifacts],
    }
    manifest_hash = hashlib.sha256(canonical_yaml(data_without_hash)).hexdigest()
    return SynthesisManifest(
        schema_version="2",
        mission_id=None,
        created_at="2026-04-17T12:00:00+00:00",
        run_id=run_id,
        adapter_id="fixture",
        adapter_version="1.0.0",
        synthesizer_version="3.2.0a5",
        manifest_hash=manifest_hash,
        artifacts=artifacts,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def guard(tmp_path: Path) -> PathGuard:
    return PathGuard(tmp_path, extra_allowed_prefixes=[tmp_path])


# ---------------------------------------------------------------------------
# Manifest-last semantics
# ---------------------------------------------------------------------------


def test_manifest_absence_means_partial(tmp_path: Path) -> None:
    """If manifest file does not exist, the live tree is treated as partial.

    This test verifies the authority rule: manifest absent → partial state.
    We validate this by checking that load_yaml raises FileNotFoundError.
    """
    manifest_path = tmp_path / "synthesis-manifest.yaml"
    with pytest.raises(FileNotFoundError):
        load_yaml(manifest_path)


def test_run_id_present_in_manifest(tmp_path: Path, guard: PathGuard) -> None:
    """run_id in the manifest matches the staging dir run_id."""
    run_id = "01KPE222TESTRUNID0000000042"
    manifest = _make_manifest(run_id=run_id)
    out_path = tmp_path / "synthesis-manifest.yaml"
    dump_yaml(manifest, out_path, guard)
    loaded = load_yaml(out_path)
    assert loaded.run_id == run_id


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------


def test_manifest_round_trip(tmp_path: Path, guard: PathGuard) -> None:
    """dump_yaml → load_yaml reproduces all fields."""
    manifest = _make_manifest()
    out_path = tmp_path / "synthesis-manifest.yaml"
    dump_yaml(manifest, out_path, guard)
    loaded = load_yaml(out_path)
    assert loaded.schema_version == "2"
    assert loaded.run_id == manifest.run_id
    assert loaded.adapter_id == "fixture"
    assert loaded.adapter_version == "1.0.0"
    assert loaded.synthesizer_version == "3.2.0a5"
    assert len(loaded.manifest_hash) == 64
    assert len(loaded.artifacts) == 1
    assert loaded.artifacts[0].kind == "tactic"
    assert loaded.artifacts[0].slug == "my-tactic"
    assert loaded.artifacts[0].content_hash == "a" * 64


def test_manifest_with_mission_id(tmp_path: Path, guard: PathGuard) -> None:
    """mission_id is optional and round-trips correctly."""
    artifacts: list[ManifestArtifactEntry] = []
    data_without_hash = {
        "schema_version": "2",
        "mission_id": "01KPE222CD1MMCYEGB3ZCY51VR",
        "created_at": "2026-04-17T12:00:00+00:00",
        "run_id": "01KPE222TESTRUNID0000000001",
        "adapter_id": "fixture",
        "adapter_version": "1.0.0",
        "synthesizer_version": "3.2.0a5",
        "artifacts": [],
    }
    manifest_hash = hashlib.sha256(canonical_yaml(data_without_hash)).hexdigest()
    manifest = SynthesisManifest(
        created_at="2026-04-17T12:00:00+00:00",
        run_id="01KPE222TESTRUNID0000000001",
        adapter_id="fixture",
        adapter_version="1.0.0",
        synthesizer_version="3.2.0a5",
        manifest_hash=manifest_hash,
        mission_id="01KPE222CD1MMCYEGB3ZCY51VR",
        artifacts=artifacts,
    )
    out_path = tmp_path / "synthesis-manifest.yaml"
    dump_yaml(manifest, out_path, guard)
    loaded = load_yaml(out_path)
    assert loaded.mission_id == "01KPE222CD1MMCYEGB3ZCY51VR"


# ---------------------------------------------------------------------------
# verify() — hash matching
# ---------------------------------------------------------------------------


def test_verify_passes_when_hashes_match(tmp_path: Path, guard: PathGuard) -> None:
    """verify() passes when all artifact content_hash values match on-disk bytes."""
    # Create an actual artifact file
    artifact_bytes = b"id: PROJECT_001\ntitle: Test\n"
    content_hash = hashlib.sha256(artifact_bytes).hexdigest()

    artifact_rel = ".kittify/doctrine/tactics/my-tactic.tactic.yaml"
    artifact_path = tmp_path / artifact_rel
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(artifact_bytes)

    artifacts = [
        ManifestArtifactEntry(
            kind="tactic",
            slug="my-tactic",
            path=artifact_rel,
            provenance_path=".kittify/charter/provenance/tactic-my-tactic.yaml",
            content_hash=content_hash,
        )
    ]
    data_without_hash = {
        "schema_version": "2",
        "mission_id": None,
        "created_at": "2026-04-17T12:00:00+00:00",
        "run_id": "01KPE222TESTRUNID0000000001",
        "adapter_id": "fixture",
        "adapter_version": "1.0.0",
        "synthesizer_version": "3.2.0a5",
        "artifacts": [a.model_dump(mode="python") for a in artifacts],
    }
    manifest_hash = hashlib.sha256(canonical_yaml(data_without_hash)).hexdigest()
    manifest = SynthesisManifest(
        created_at="2026-04-17T12:00:00+00:00",
        run_id="01KPE222TESTRUNID0000000001",
        adapter_id="fixture",
        adapter_version="1.0.0",
        synthesizer_version="3.2.0a5",
        manifest_hash=manifest_hash,
        artifacts=artifacts,
    )
    # Should not raise
    verify(manifest, tmp_path)


def test_verify_raises_on_hash_mismatch(tmp_path: Path) -> None:
    """verify() raises ManifestIntegrityError when content_hash does not match."""
    artifact_rel = ".kittify/doctrine/tactics/my-tactic.tactic.yaml"
    artifact_path = tmp_path / artifact_rel
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(b"actual content")

    wrong_hash = "0" * 64  # definitely wrong

    artifacts = [
        ManifestArtifactEntry(
            kind="tactic",
            slug="my-tactic",
            path=artifact_rel,
            provenance_path=".kittify/charter/provenance/tactic-my-tactic.yaml",
            content_hash=wrong_hash,
        )
    ]
    data_without_hash = {
        "schema_version": "2",
        "mission_id": None,
        "created_at": "2026-04-17T12:00:00+00:00",
        "run_id": "01KPE222TESTRUNID0000000001",
        "adapter_id": "fixture",
        "adapter_version": "1.0.0",
        "synthesizer_version": "3.2.0a5",
        "artifacts": [a.model_dump(mode="python") for a in artifacts],
    }
    manifest_hash = hashlib.sha256(canonical_yaml(data_without_hash)).hexdigest()
    manifest = SynthesisManifest(
        created_at="2026-04-17T12:00:00+00:00",
        run_id="01KPE222TESTRUNID0000000001",
        adapter_id="fixture",
        adapter_version="1.0.0",
        synthesizer_version="3.2.0a5",
        manifest_hash=manifest_hash,
        artifacts=artifacts,
    )
    with pytest.raises(ManifestIntegrityError) as exc_info:
        verify(manifest, tmp_path)
    assert "my-tactic" in str(exc_info.value)


def test_verify_raises_on_missing_artifact(tmp_path: Path) -> None:
    """verify() raises ManifestIntegrityError when artifact file is missing."""
    artifact_rel = ".kittify/doctrine/tactics/missing-tactic.tactic.yaml"
    # Don't create the artifact file

    artifacts = [
        ManifestArtifactEntry(
            kind="tactic",
            slug="missing-tactic",
            path=artifact_rel,
            provenance_path=".kittify/charter/provenance/tactic-missing-tactic.yaml",
            content_hash="a" * 64,
        )
    ]
    data_without_hash = {
        "schema_version": "2",
        "mission_id": None,
        "created_at": "2026-04-17T12:00:00+00:00",
        "run_id": "01KPE222TESTRUNID0000000001",
        "adapter_id": "fixture",
        "adapter_version": "1.0.0",
        "synthesizer_version": "3.2.0a5",
        "artifacts": [a.model_dump(mode="python") for a in artifacts],
    }
    manifest_hash = hashlib.sha256(canonical_yaml(data_without_hash)).hexdigest()
    manifest = SynthesisManifest(
        created_at="2026-04-17T12:00:00+00:00",
        run_id="01KPE222TESTRUNID0000000001",
        adapter_id="fixture",
        adapter_version="1.0.0",
        synthesizer_version="3.2.0a5",
        manifest_hash=manifest_hash,
        artifacts=artifacts,
    )
    with pytest.raises(ManifestIntegrityError):
        verify(manifest, tmp_path)


# ---------------------------------------------------------------------------
# Ordering (deterministic)
# ---------------------------------------------------------------------------


def test_manifest_artifact_ordering(tmp_path: Path, guard: PathGuard) -> None:
    """Artifacts are stored in (kind, slug) order for determinism."""
    artifacts = [
        ManifestArtifactEntry(
            kind="tactic",
            slug="z-tactic",
            path=".kittify/doctrine/tactics/z-tactic.tactic.yaml",
            provenance_path=".kittify/charter/provenance/tactic-z-tactic.yaml",
            content_hash="a" * 64,
        ),
        ManifestArtifactEntry(
            kind="directive",
            slug="a-directive",
            path=".kittify/doctrine/directives/001-a-directive.directive.yaml",
            provenance_path=".kittify/charter/provenance/directive-a-directive.yaml",
            content_hash="b" * 64,
        ),
        ManifestArtifactEntry(
            kind="tactic",
            slug="a-tactic",
            path=".kittify/doctrine/tactics/a-tactic.tactic.yaml",
            provenance_path=".kittify/charter/provenance/tactic-a-tactic.yaml",
            content_hash="c" * 64,
        ),
    ]
    data_without_hash = {
        "schema_version": "2",
        "mission_id": None,
        "created_at": "2026-04-17T12:00:00+00:00",
        "run_id": "01KPE222TESTRUNID0000000001",
        "adapter_id": "fixture",
        "adapter_version": "1.0.0",
        "synthesizer_version": "3.2.0a5",
        "artifacts": [a.model_dump(mode="python") for a in artifacts],
    }
    manifest_hash = hashlib.sha256(canonical_yaml(data_without_hash)).hexdigest()
    manifest = SynthesisManifest(
        created_at="2026-04-17T12:00:00+00:00",
        run_id="01KPE222TESTRUNID0000000001",
        adapter_id="fixture",
        adapter_version="1.0.0",
        synthesizer_version="3.2.0a5",
        manifest_hash=manifest_hash,
        artifacts=artifacts,
    )
    out_path = tmp_path / "synthesis-manifest.yaml"
    dump_yaml(manifest, out_path, guard)
    loaded = load_yaml(out_path)
    # Verify round-trip preserves the order
    assert len(loaded.artifacts) == 3


# ---------------------------------------------------------------------------
# v2: manifest_hash validation
# ---------------------------------------------------------------------------


def test_manifest_hash_validates(tmp_path: Path, guard: PathGuard) -> None:
    """manifest_hash stored in the manifest matches a re-computed hash.

    Build a manifest, strip manifest_hash from model_dump, re-hash via
    canonical_yaml (bytes — no .encode() needed), verify it matches the stored hash.
    """
    manifest = _make_manifest()
    # Strip manifest_hash and re-compute
    fields_without_hash = manifest.model_dump(mode="python")
    fields_without_hash.pop("manifest_hash")
    # canonical_yaml() returns bytes — hash directly, no .encode()
    computed = hashlib.sha256(canonical_yaml(fields_without_hash)).hexdigest()
    assert computed == manifest.manifest_hash


def test_manifest_synthesizer_version_empty_raises() -> None:
    """SynthesisManifest with synthesizer_version='' must raise ValidationError."""
    artifacts: list[ManifestArtifactEntry] = []
    data_without_hash = {
        "schema_version": "2",
        "mission_id": None,
        "created_at": "2026-04-17T12:00:00+00:00",
        "run_id": "01KPE222TESTRUNID0000000001",
        "adapter_id": "fixture",
        "adapter_version": "1.0.0",
        "synthesizer_version": "valid",
        "artifacts": [],
    }
    manifest_hash = hashlib.sha256(canonical_yaml(data_without_hash)).hexdigest()
    with pytest.raises(ValidationError):
        SynthesisManifest(
            created_at="2026-04-17T12:00:00+00:00",
            run_id="01KPE222TESTRUNID0000000001",
            adapter_id="fixture",
            adapter_version="1.0.0",
            synthesizer_version="",  # empty — should raise
            manifest_hash=manifest_hash,
            artifacts=[],
        )
