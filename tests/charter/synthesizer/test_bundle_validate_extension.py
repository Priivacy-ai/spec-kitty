"""Tests for bundle.py validate_synthesis_state extension — WP03 T019 / T020.

Four main fixtures + regression fixture:

1. Valid post-synthesis bundle → passes (no errors, no warnings).
2. Artifact without provenance → structured error.
3. Provenance sidecar without artifact → structured error.
4. Schema-invalid artifact file → (manifest hash mismatch) structured error.
5. Regression: no synthesis state at all → passes exactly as v1.0.0 (C-012).

Also tests:
- Stale .failed/ staging dirs produce warnings (not errors).
- validate_synthesis_state is additive-only (legacy bundles unaffected).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


from charter.bundle import (
    BundleValidationResult,
    CANONICAL_MANIFEST,
    SCHEMA_VERSION,
    _check_artifacts_have_provenance,
    _find_artifact,
    _kind_and_slug_from_artifact,
    validate_synthesis_state,
)
from charter.synthesizer.synthesize_pipeline import canonical_yaml
from charter.synthesizer.manifest import (
    ManifestArtifactEntry,
    SynthesisManifest,
    dump_yaml as dump_manifest,
)
from charter.synthesizer.path_guard import PathGuard


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_artifact(repo: Path, kind: str, slug: str, filename: str, content: bytes) -> Path:
    """Write a synthesized artifact file to the doctrine tree."""
    subdir = {"directive": "directives", "tactic": "tactics", "styleguide": "styleguides"}[kind]
    path = repo / ".kittify" / "doctrine" / subdir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _write_provenance(repo: Path, kind: str, slug: str, content: str) -> Path:
    """Write a provenance sidecar to the charter provenance tree."""
    path = repo / ".kittify" / "charter" / "provenance" / f"{kind}-{slug}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _tactic_body(slug: str = "my-tactic") -> bytes:
    return canonical_yaml({"id": slug, "title": "My Tactic", "summary": "A tactic."})


def _directive_body(artifact_id: str = "PROJECT_001", slug: str = "my-directive") -> bytes:
    return canonical_yaml(
        {
            "id": artifact_id,
            "title": "My Directive",
            "description": "A directive.",
            "guidance": "Follow this.",
        }
    )


def _make_v2_manifest(
    artifacts: list[ManifestArtifactEntry],
    run_id: str = "01KPE222TESTRUNID0000000001",
    created_at: str = "2026-04-17T12:00:00+00:00",
    adapter_id: str = "fixture",
    adapter_version: str = "1.0.0",
) -> SynthesisManifest:
    """Build a valid v2 SynthesisManifest with computed manifest_hash."""
    data_without_hash: dict[str, Any] = {
        "schema_version": "2",
        "mission_id": None,
        "created_at": created_at,
        "run_id": run_id,
        "adapter_id": adapter_id,
        "adapter_version": adapter_version,
        "synthesizer_version": "3.2.0a5",
        "artifacts": [a.model_dump(mode="python") for a in artifacts],
    }
    manifest_hash = hashlib.sha256(canonical_yaml(data_without_hash)).hexdigest()
    return SynthesisManifest(
        created_at=created_at,
        run_id=run_id,
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        synthesizer_version="3.2.0a5",
        manifest_hash=manifest_hash,
        artifacts=artifacts,
    )


def _prov_yaml(kind: str, slug: str, content_hash: str) -> str:
    return (
        f"schema_version: '2'\n"
        f"artifact_urn: '{kind}:{slug}'\n"
        f"artifact_kind: {kind}\n"
        f"artifact_slug: {slug}\n"
        f"artifact_content_hash: {content_hash}\n"
        f"inputs_hash: {'b' * 64}\n"
        f"adapter_id: fixture\n"
        f"adapter_version: 1.0.0\n"
        f"synthesizer_version: '3.2.0a5'\n"
        f"source_urns:\n"
        f"- directive:DIRECTIVE_003\n"
        f"source_input_ids:\n"
        f"- directive:DIRECTIVE_003\n"
        f"generated_at: '2026-04-17T12:00:00+00:00'\n"
        f"produced_at: '2026-01-01T00:00:00+00:00'\n"
        f"corpus_snapshot_id: '(none)'\n"
        f"synthesis_run_id: '01HTEST00000000000000TEST01'\n"
    )


# ---------------------------------------------------------------------------
# Fixture 5 (regression): no synthesis state → passes exactly as v1.0.0
# ---------------------------------------------------------------------------


def test_no_synthesis_state_passes_as_legacy(tmp_path: Path) -> None:
    """A bundle with no synthesis state passes validate_synthesis_state without errors.

    This is the C-012 backward-compat regression test: the v1.0.0 contract is
    preserved — existing bundles without synthesis state are unaffected.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    # No .kittify/doctrine/ or .kittify/charter/provenance/ directories.

    result = validate_synthesis_state(repo)

    assert result.passed
    assert result.errors == []
    assert not result.synthesis_state_present


def test_empty_doctrine_tree_without_provenance_is_treated_as_legacy(tmp_path: Path) -> None:
    """An empty doctrine tree alone must not flip synthesis_state_present."""
    repo = tmp_path / "repo"
    (repo / ".kittify" / "doctrine").mkdir(parents=True)

    result = validate_synthesis_state(repo)

    assert result.passed
    assert result.errors == []
    assert not result.synthesis_state_present


def test_empty_provenance_tree_without_sidecars_is_treated_as_legacy(tmp_path: Path) -> None:
    """An empty provenance directory alone must not flip synthesis_state_present."""
    repo = tmp_path / "repo"
    (repo / ".kittify" / "charter" / "provenance").mkdir(parents=True)

    result = validate_synthesis_state(repo)

    assert result.passed
    assert result.errors == []
    assert not result.synthesis_state_present


def test_legacy_canonical_manifest_still_valid() -> None:
    """CANONICAL_MANIFEST from v1.0.0 is still importable and valid (C-012)."""
    assert CANONICAL_MANIFEST.schema_version == SCHEMA_VERSION
    assert len(CANONICAL_MANIFEST.tracked_files) >= 1


# ---------------------------------------------------------------------------
# Fixture 1: Valid post-synthesis bundle → passes
# ---------------------------------------------------------------------------


def test_valid_synthesis_bundle_passes(tmp_path: Path) -> None:
    """A fully-consistent synthesis bundle passes validate_synthesis_state."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Write artifact + matching provenance
    body = _tactic_body("my-tactic")
    content_hash = hashlib.sha256(body).hexdigest()
    _write_artifact(repo, "tactic", "my-tactic", "my-tactic.tactic.yaml", body)
    _write_provenance(repo, "tactic", "my-tactic", _prov_yaml("tactic", "my-tactic", content_hash))

    # Write synthesis manifest with matching hash
    guard = PathGuard(repo, extra_allowed_prefixes=[repo])
    manifest = _make_v2_manifest(
        artifacts=[
            ManifestArtifactEntry(
                kind="tactic",
                slug="my-tactic",
                path=".kittify/doctrine/tactics/my-tactic.tactic.yaml",
                provenance_path=".kittify/charter/provenance/tactic-my-tactic.yaml",
                content_hash=content_hash,
            )
        ],
    )
    manifest_path = repo / ".kittify" / "charter" / "synthesis-manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    dump_manifest(manifest, manifest_path, guard)

    result = validate_synthesis_state(repo)

    assert result.passed, f"Expected pass but got errors: {result.errors}"
    assert result.errors == []
    assert result.synthesis_state_present


# ---------------------------------------------------------------------------
# Fixture 2: Artifact without provenance → structured error
# ---------------------------------------------------------------------------


def test_artifact_without_provenance_is_error(tmp_path: Path) -> None:
    """Artifact file without a provenance sidecar produces a structured error."""
    repo = tmp_path / "repo"
    repo.mkdir()

    body = _tactic_body("orphan-tactic")
    _write_artifact(repo, "tactic", "orphan-tactic", "orphan-tactic.tactic.yaml", body)
    # No provenance written

    result = validate_synthesis_state(repo)

    assert not result.passed
    assert len(result.errors) >= 1
    assert any("orphan-tactic" in e for e in result.errors)
    assert any("provenance" in e.lower() for e in result.errors)


# ---------------------------------------------------------------------------
# Fixture 3: Provenance sidecar without artifact → structured error
# ---------------------------------------------------------------------------


def test_provenance_without_artifact_is_error(tmp_path: Path) -> None:
    """Provenance sidecar without a matching artifact produces a structured error."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Write provenance but no artifact
    # Create doctrine dir so synthesis_state_present is True
    (repo / ".kittify" / "doctrine" / "tactics").mkdir(parents=True, exist_ok=True)
    _write_provenance(repo, "tactic", "ghost-tactic", _prov_yaml("tactic", "ghost-tactic", "a" * 64))

    result = validate_synthesis_state(repo)

    assert not result.passed
    assert any("ghost-tactic" in e for e in result.errors)


def test_provenance_without_doctrine_tree_is_not_legacy(tmp_path: Path) -> None:
    """A provenance sidecar alone is synthesis state and must fail closed."""
    repo = tmp_path / "repo"
    repo.mkdir()

    _write_provenance(
        repo,
        "tactic",
        "sidecar-only",
        _prov_yaml("tactic", "sidecar-only", "a" * 64),
    )

    result = validate_synthesis_state(repo)

    assert result.synthesis_state_present
    assert not result.passed
    assert any("sidecar-only" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Fixture 4: Schema-invalid artifact (manifest hash mismatch) → error
# ---------------------------------------------------------------------------


def test_manifest_hash_mismatch_is_error(tmp_path: Path) -> None:
    """A manifest whose content_hash does not match on-disk bytes produces an error."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Write artifact with known content
    body = _tactic_body("hash-mismatch-tactic")
    _write_artifact(repo, "tactic", "hash-mismatch-tactic", "hash-mismatch-tactic.tactic.yaml", body)
    _write_provenance(repo, "tactic", "hash-mismatch-tactic", _prov_yaml("tactic", "hash-mismatch-tactic", "a" * 64))

    # Write manifest with WRONG hash
    guard = PathGuard(repo, extra_allowed_prefixes=[repo])
    manifest = _make_v2_manifest(
        artifacts=[
            ManifestArtifactEntry(
                kind="tactic",
                slug="hash-mismatch-tactic",
                path=".kittify/doctrine/tactics/hash-mismatch-tactic.tactic.yaml",
                provenance_path=".kittify/charter/provenance/tactic-hash-mismatch-tactic.yaml",
                content_hash="0" * 64,  # wrong hash
            )
        ],
    )
    manifest_path = repo / ".kittify" / "charter" / "synthesis-manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    dump_manifest(manifest, manifest_path, guard)

    result = validate_synthesis_state(repo)

    assert not result.passed
    assert any("manifest" in e.lower() or "integrity" in e.lower() for e in result.errors)


def test_invalid_manifest_yaml_is_reported(tmp_path: Path) -> None:
    """A malformed synthesis manifest surfaces a structured load error."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".kittify" / "doctrine").mkdir(parents=True, exist_ok=True)
    (repo / ".kittify" / "charter" / "provenance").mkdir(parents=True, exist_ok=True)
    manifest_path = repo / ".kittify" / "charter" / "synthesis-manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("artifacts: [\n", encoding="utf-8")

    result = validate_synthesis_state(repo)

    assert not result.passed
    assert any("could not load synthesis manifest" in error.lower() for error in result.errors)


def test_manifest_without_doctrine_tree_is_not_legacy(tmp_path: Path) -> None:
    """A synthesis manifest alone is synthesis state and must be validated."""
    repo = tmp_path / "repo"
    repo.mkdir()
    manifest_path = repo / ".kittify" / "charter" / "synthesis-manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("artifacts: [\n", encoding="utf-8")

    result = validate_synthesis_state(repo)

    assert result.synthesis_state_present
    assert not result.passed
    assert any("could not load synthesis manifest" in error.lower() for error in result.errors)


def test_manifest_absolute_artifact_path_fails_closed(tmp_path: Path) -> None:
    """A manifest cannot make validation read artifacts outside the repo root."""
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.tactic.yaml"
    outside.write_bytes(_tactic_body("outside"))
    content_hash = hashlib.sha256(outside.read_bytes()).hexdigest()

    guard = PathGuard(repo, extra_allowed_prefixes=[repo])
    manifest = _make_v2_manifest(
        artifacts=[
            ManifestArtifactEntry(
                kind="tactic",
                slug="outside",
                path=str(outside),
                provenance_path=".kittify/charter/provenance/tactic-outside.yaml",
                content_hash=content_hash,
            )
        ],
    )
    manifest_path = repo / ".kittify" / "charter" / "synthesis-manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    dump_manifest(manifest, manifest_path, guard)

    result = validate_synthesis_state(repo)

    assert result.synthesis_state_present
    assert not result.passed
    assert any("repo-relative" in error for error in result.errors), result.errors


# ---------------------------------------------------------------------------
# Stale .failed/ staging dirs produce warnings
# ---------------------------------------------------------------------------


def test_stale_failed_staging_dir_produces_warning(tmp_path: Path) -> None:
    """Stale .failed/ staging dirs produce a warning (not an error) — R-7."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Create a .failed/ staging directory (simulates preserved crash state)
    failed_dir = repo / ".kittify" / "charter" / ".staging" / "01KPE222TESTFAILED.failed"
    failed_dir.mkdir(parents=True)
    (failed_dir / "cause.yaml").write_text("reason: test\n")

    result = validate_synthesis_state(repo)

    # Should warn, but not error
    assert result.passed  # no errors
    assert any(".failed" in w for w in result.warnings)


def test_multiple_failed_dirs_multiple_warnings(tmp_path: Path) -> None:
    """Multiple .failed/ dirs each produce a warning."""
    repo = tmp_path / "repo"
    repo.mkdir()
    staging = repo / ".kittify" / "charter" / ".staging"
    staging.mkdir(parents=True)
    for i in range(3):
        failed = staging / f"RUN_ID_{i:03d}.failed"
        failed.mkdir()

    result = validate_synthesis_state(repo)
    assert result.passed
    assert len(result.warnings) == 3


def test_malformed_provenance_filename_is_error(tmp_path: Path) -> None:
    """Provenance filenames must be <kind>-<slug>.yaml."""
    repo = tmp_path / "repo"
    (repo / ".kittify" / "doctrine" / "tactics").mkdir(parents=True, exist_ok=True)
    bad_prov = repo / ".kittify" / "charter" / "provenance" / "badformat.yaml"
    bad_prov.parent.mkdir(parents=True, exist_ok=True)
    bad_prov.write_text("schema_version: '1'\n", encoding="utf-8")

    result = validate_synthesis_state(repo)

    assert not result.passed
    assert any("unexpected name format" in error.lower() for error in result.errors)


def test_unknown_provenance_kind_is_error(tmp_path: Path) -> None:
    """Unknown provenance kinds should fail validation with a clear error."""
    repo = tmp_path / "repo"
    (repo / ".kittify" / "doctrine" / "tactics").mkdir(parents=True, exist_ok=True)
    bad_prov = repo / ".kittify" / "charter" / "provenance" / "unknown-slug.yaml"
    bad_prov.parent.mkdir(parents=True, exist_ok=True)
    bad_prov.write_text("schema_version: '1'\n", encoding="utf-8")

    result = validate_synthesis_state(repo)

    assert not result.passed
    assert any("unknown kind 'unknown'" in error.lower() for error in result.errors)


def test_kind_and_slug_from_artifact_handles_directive_prefix_and_unknown_suffix(tmp_path: Path) -> None:
    """Directive filenames strip the numeric prefix; unknown suffixes return None."""
    directive_path = tmp_path / "001-project-decision.directive.yaml"
    unknown_path = tmp_path / "notes.yaml"

    assert _kind_and_slug_from_artifact(directive_path) == (
        "directive",
        "project-decision",
    )
    assert _kind_and_slug_from_artifact(unknown_path) == (None, None)


def test_check_artifacts_have_provenance_ignores_unrecognized_files(tmp_path: Path) -> None:
    """Artifacts outside the known filename rules should be skipped quietly."""
    repo = tmp_path / "repo"
    repo.mkdir()
    result = BundleValidationResult()

    _check_artifacts_have_provenance(
        repo_root=repo,
        artifact_files=[repo / ".kittify" / "doctrine" / "misc" / "notes.yaml"],
        provenance_root=repo / ".kittify" / "charter" / "provenance",
        result=result,
    )

    assert result.errors == []


def test_find_artifact_returns_none_for_unknown_kind(tmp_path: Path) -> None:
    """Unknown artifact kinds should short-circuit without scanning the tree."""
    doctrine_root = tmp_path / ".kittify" / "doctrine"
    doctrine_root.mkdir(parents=True)

    assert _find_artifact(doctrine_root, "unknown", "slug") is None


# ---------------------------------------------------------------------------
# RISK-2 remediation: manifest self-hash verification
# ---------------------------------------------------------------------------


def test_manifest_self_hash_mismatch_is_error(tmp_path: Path) -> None:
    """A tampered manifest_hash field produces a structured self-hash error.

    Exercises verify_manifest_hash() wired into _check_manifest_integrity().
    Valid per-artifact content_hash + corrupt manifest_hash must fail.
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    body = _tactic_body("selfhash-tactic")
    content_hash = hashlib.sha256(body).hexdigest()
    _write_artifact(repo, "tactic", "selfhash-tactic", "selfhash-tactic.tactic.yaml", body)
    _write_provenance(
        repo,
        "tactic",
        "selfhash-tactic",
        _prov_yaml("tactic", "selfhash-tactic", content_hash),
    )

    guard = PathGuard(repo, extra_allowed_prefixes=[repo])
    manifest = _make_v2_manifest(
        artifacts=[
            ManifestArtifactEntry(
                kind="tactic",
                slug="selfhash-tactic",
                path=".kittify/doctrine/tactics/selfhash-tactic.tactic.yaml",
                provenance_path=".kittify/charter/provenance/tactic-selfhash-tactic.yaml",
                content_hash=content_hash,
            )
        ],
    )
    manifest_path = repo / ".kittify" / "charter" / "synthesis-manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    dump_manifest(manifest, manifest_path, guard)

    # Corrupt the manifest_hash field on disk (tampered manifest simulation).
    text = manifest_path.read_text(encoding="utf-8")
    manifest_path.write_text(text.replace(manifest.manifest_hash, "0" * 64), encoding="utf-8")

    result = validate_synthesis_state(repo)

    assert not result.passed
    assert any("manifest" in e.lower() or "self-hash" in e.lower() or "mismatch" in e.lower() for e in result.errors), result.errors
