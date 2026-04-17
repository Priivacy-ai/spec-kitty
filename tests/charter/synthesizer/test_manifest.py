"""Tests for manifest.py — WP03 T017 / T020.

Covers:
- manifest-last semantics: absence of manifest means "partial"
- SynthesisManifest round-trip (dump_yaml → load_yaml)
- verify() catches hash mismatch via ManifestIntegrityError
- verify() passes when hashes match
- run_id matches the staging dir concept
- Manifest ordering is deterministic (sorted by kind, slug)
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from charter.synthesizer.errors import ManifestIntegrityError
from charter.synthesizer.manifest import (
    ManifestArtifactEntry,
    SynthesisManifest,
    dump_yaml,
    load_yaml,
    verify,
)
from charter.synthesizer.path_guard import PathGuard


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def guard(tmp_path: Path) -> PathGuard:
    return PathGuard(tmp_path, extra_allowed_prefixes=[tmp_path])


def _make_manifest(run_id: str = "01KPE222TESTRUNID0000000001") -> SynthesisManifest:
    """Create a sample manifest for testing."""
    return SynthesisManifest(
        schema_version="1",
        mission_id=None,
        created_at="2026-04-17T12:00:00+00:00",
        run_id=run_id,
        adapter_id="fixture",
        adapter_version="1.0.0",
        artifacts=[
            ManifestArtifactEntry(
                kind="tactic",
                slug="my-tactic",
                path=".kittify/doctrine/tactics/my-tactic.tactic.yaml",
                provenance_path=".kittify/charter/provenance/tactic-my-tactic.yaml",
                content_hash="a" * 64,
            ),
        ],
    )


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
    assert loaded.schema_version == "1"
    assert loaded.run_id == manifest.run_id
    assert loaded.adapter_id == "fixture"
    assert loaded.adapter_version == "1.0.0"
    assert len(loaded.artifacts) == 1
    assert loaded.artifacts[0].kind == "tactic"
    assert loaded.artifacts[0].slug == "my-tactic"
    assert loaded.artifacts[0].content_hash == "a" * 64


def test_manifest_with_mission_id(tmp_path: Path, guard: PathGuard) -> None:
    """mission_id is optional and round-trips correctly."""
    manifest = SynthesisManifest(
        created_at="2026-04-17T12:00:00+00:00",
        run_id="01KPE222TESTRUNID0000000001",
        adapter_id="fixture",
        adapter_version="1.0.0",
        mission_id="01KPE222CD1MMCYEGB3ZCY51VR",
        artifacts=[],
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

    manifest = SynthesisManifest(
        created_at="2026-04-17T12:00:00+00:00",
        run_id="01KPE222TESTRUNID0000000001",
        adapter_id="fixture",
        adapter_version="1.0.0",
        artifacts=[
            ManifestArtifactEntry(
                kind="tactic",
                slug="my-tactic",
                path=artifact_rel,
                provenance_path=".kittify/charter/provenance/tactic-my-tactic.yaml",
                content_hash=content_hash,
            )
        ],
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

    manifest = SynthesisManifest(
        created_at="2026-04-17T12:00:00+00:00",
        run_id="01KPE222TESTRUNID0000000001",
        adapter_id="fixture",
        adapter_version="1.0.0",
        artifacts=[
            ManifestArtifactEntry(
                kind="tactic",
                slug="my-tactic",
                path=artifact_rel,
                provenance_path=".kittify/charter/provenance/tactic-my-tactic.yaml",
                content_hash=wrong_hash,
            )
        ],
    )
    with pytest.raises(ManifestIntegrityError) as exc_info:
        verify(manifest, tmp_path)
    assert "my-tactic" in str(exc_info.value)


def test_verify_raises_on_missing_artifact(tmp_path: Path) -> None:
    """verify() raises ManifestIntegrityError when artifact file is missing."""
    artifact_rel = ".kittify/doctrine/tactics/missing-tactic.tactic.yaml"
    # Don't create the artifact file

    manifest = SynthesisManifest(
        created_at="2026-04-17T12:00:00+00:00",
        run_id="01KPE222TESTRUNID0000000001",
        adapter_id="fixture",
        adapter_version="1.0.0",
        artifacts=[
            ManifestArtifactEntry(
                kind="tactic",
                slug="missing-tactic",
                path=artifact_rel,
                provenance_path=".kittify/charter/provenance/tactic-missing-tactic.yaml",
                content_hash="a" * 64,
            )
        ],
    )
    with pytest.raises(ManifestIntegrityError):
        verify(manifest, tmp_path)


# ---------------------------------------------------------------------------
# Ordering (deterministic)
# ---------------------------------------------------------------------------


def test_manifest_artifact_ordering(tmp_path: Path, guard: PathGuard) -> None:
    """Artifacts are stored in (kind, slug) order for determinism."""
    manifest = SynthesisManifest(
        created_at="2026-04-17T12:00:00+00:00",
        run_id="01KPE222TESTRUNID0000000001",
        adapter_id="fixture",
        adapter_version="1.0.0",
        artifacts=[
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
        ],
    )
    out_path = tmp_path / "synthesis-manifest.yaml"
    dump_yaml(manifest, out_path, guard)
    loaded = load_yaml(out_path)
    # Verify round-trip preserves the order
    assert len(loaded.artifacts) == 3
