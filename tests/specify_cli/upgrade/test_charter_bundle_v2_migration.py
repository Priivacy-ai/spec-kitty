"""Tests for CharterBundleV2Migration (m_3_2_6_charter_bundle_v2).

Covers:
- T018: detect / apply / idempotency / dry_run / metadata stamp
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ruamel.yaml import YAML

from specify_cli.upgrade.migrations.m_3_2_6_charter_bundle_v2 import (
    CharterBundleV2Migration,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_yaml = YAML()
_yaml.default_flow_style = False
_yaml.explicit_start = False


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    import io
    buf = io.BytesIO()
    _yaml.dump(data, buf)
    path.write_bytes(buf.getvalue())


def _load_yaml(path: Path) -> dict:
    return _yaml.load(path)  # type: ignore[return-value]


def _create_v1_bundle(project_path: Path) -> None:
    """Create a minimal v1 charter bundle under project_path/.kittify/charter/."""
    charter_dir = project_path / ".kittify" / "charter"

    # metadata.yaml — no bundle_schema_version field (treated as v1)
    _write_yaml(
        charter_dir / "metadata.yaml",
        {
            "timestamp_utc": "2026-01-01T00:00:00Z",
            "extracted_at": "2026-01-01T00:00:00Z",
        },
    )

    # provenance sidecar — schema_version "1", missing v2 fields
    _write_yaml(
        charter_dir / "provenance" / "directive-use-prs.yaml",
        {
            "schema_version": "1",
            "artifact_urn": "drg:directive:directive-use-prs",
            "artifact_kind": "directive",
            "artifact_slug": "directive-use-prs",
            "artifact_content_hash": "a" * 64,
            "inputs_hash": "b" * 64,
            "adapter_id": "fixture",
            "adapter_version": "1.0.0",
            "generated_at": "2026-01-01T00:00:00Z",
            "source_section": "review_policy",
            "source_urns": ["drg:directive:DIR-001"],
            "corpus_snapshot_id": None,
            # Missing v2 fields: synthesizer_version, synthesis_run_id,
            #                    produced_at, source_input_ids
        },
    )

    # synthesis-manifest.yaml — schema_version "1", missing v2 fields
    _write_yaml(
        charter_dir / "synthesis-manifest.yaml",
        {
            "schema_version": "1",
            "created_at": "2026-01-01T00:00:00Z",
            "run_id": "01TEST000000000000000000001",
            "adapter_id": "fixture",
            "adapter_version": "1.0.0",
            "artifacts": [],
        },
    )


def _create_v2_bundle(project_path: Path) -> None:
    """Create a minimal v2 charter bundle under project_path/.kittify/charter/."""
    charter_dir = project_path / ".kittify" / "charter"

    _write_yaml(
        charter_dir / "metadata.yaml",
        {"bundle_schema_version": 2, "timestamp_utc": "2026-01-01T00:00:00Z"},
    )

    _write_yaml(
        charter_dir / "provenance" / "directive-use-prs.yaml",
        {
            "schema_version": "2",
            "artifact_urn": "drg:directive:directive-use-prs",
            "artifact_kind": "directive",
            "artifact_slug": "directive-use-prs",
            "artifact_content_hash": "a" * 64,
            "inputs_hash": "b" * 64,
            "adapter_id": "fixture",
            "adapter_version": "1.0.0",
            "generated_at": "2026-01-01T00:00:00Z",
            "source_section": "review_policy",
            "source_urns": ["drg:directive:DIR-001"],
            "synthesizer_version": "3.2.6",
            "synthesis_run_id": "01TEST000000000000000000001",
            "produced_at": "2026-01-01T00:00:00+00:00",
            "source_input_ids": ["drg:directive:DIR-001"],
            "corpus_snapshot_id": "(none)",
        },
    )

    # Compute a real manifest_hash for the v2 manifest.
    from doctrine.yaml_utils import canonical_yaml
    import hashlib

    fields_for_hash = {
        "schema_version": "2",
        "created_at": "2026-01-01T00:00:00Z",
        "run_id": "01TEST000000000000000000001",
        "adapter_id": "fixture",
        "adapter_version": "1.0.0",
        "synthesizer_version": "3.2.6",
        "artifacts": [],
    }
    manifest_hash = hashlib.sha256(canonical_yaml(fields_for_hash)).hexdigest()

    _write_yaml(
        charter_dir / "synthesis-manifest.yaml",
        {
            "schema_version": "2",
            "created_at": "2026-01-01T00:00:00Z",
            "run_id": "01TEST000000000000000000001",
            "adapter_id": "fixture",
            "adapter_version": "1.0.0",
            "synthesizer_version": "3.2.6",
            "manifest_hash": manifest_hash,
            "artifacts": [],
        },
    )


# ---------------------------------------------------------------------------
# detect() tests
# ---------------------------------------------------------------------------


def test_detect_v1_bundle_returns_true(tmp_path: Path) -> None:
    """detect() returns True for a v1 bundle (no bundle_schema_version in metadata)."""
    _create_v1_bundle(tmp_path)
    migration = CharterBundleV2Migration()
    assert migration.detect(tmp_path) is True


def test_detect_v2_bundle_returns_false(tmp_path: Path) -> None:
    """detect() returns False when the bundle is already at v2."""
    _create_v2_bundle(tmp_path)
    migration = CharterBundleV2Migration()
    assert migration.detect(tmp_path) is False


def test_detect_no_charter_returns_false(tmp_path: Path) -> None:
    """detect() returns False when no charter directory exists."""
    migration = CharterBundleV2Migration()
    assert migration.detect(tmp_path) is False


# ---------------------------------------------------------------------------
# apply() tests
# ---------------------------------------------------------------------------


def test_apply_migrates_sidecar_to_v2(tmp_path: Path) -> None:
    """apply() adds all v2 fields to a v1 sidecar."""
    _create_v1_bundle(tmp_path)
    migration = CharterBundleV2Migration()
    result = migration.apply(tmp_path)

    assert len(result.changes_made) > 0, "Expected changes_made to be non-empty"
    assert len(result.errors) == 0, f"Unexpected errors: {result.errors}"

    # Sidecar should now parse cleanly as ProvenanceEntry v2.
    from charter.synthesizer.synthesize_pipeline import ProvenanceEntry

    sidecar = _load_yaml(
        tmp_path / ".kittify" / "charter" / "provenance" / "directive-use-prs.yaml"
    )
    entry = ProvenanceEntry(**sidecar)
    assert entry.schema_version == "2"
    assert entry.synthesizer_version == "(pre-phase7-migration)"
    assert entry.corpus_snapshot_id == "(none)"
    assert entry.synthesis_run_id == "(pre-phase7-migration)"
    assert entry.source_input_ids == ["drg:directive:DIR-001"]


def test_apply_idempotent(tmp_path: Path) -> None:
    """Running apply() twice: second run reports no changes_made."""
    _create_v1_bundle(tmp_path)
    migration = CharterBundleV2Migration()
    migration.apply(tmp_path)
    result2 = migration.apply(tmp_path)
    assert result2.changes_made == [], (
        f"Second apply() should be a no-op; got: {result2.changes_made}"
    )


def test_apply_updates_metadata_yaml(tmp_path: Path) -> None:
    """apply() stamps bundle_schema_version: 2 in metadata.yaml."""
    _create_v1_bundle(tmp_path)
    CharterBundleV2Migration().apply(tmp_path)

    from doctrine.versioning import get_bundle_schema_version

    version = get_bundle_schema_version(tmp_path / ".kittify" / "charter")
    assert version == 2


def test_apply_manifest_gets_v2_fields(tmp_path: Path) -> None:
    """apply() upgrades synthesis-manifest.yaml to v2 with schema_version and manifest_hash."""
    _create_v1_bundle(tmp_path)
    CharterBundleV2Migration().apply(tmp_path)

    manifest = _load_yaml(
        tmp_path / ".kittify" / "charter" / "synthesis-manifest.yaml"
    )
    assert manifest["schema_version"] == "2"
    assert "synthesizer_version" in manifest
    assert len(manifest["manifest_hash"]) == 64, (
        f"manifest_hash should be a 64-char hex digest, got: {manifest['manifest_hash']!r}"
    )


def test_apply_dry_run_makes_no_changes(tmp_path: Path) -> None:
    """apply(dry_run=True) reports what would change but does not mutate files."""
    _create_v1_bundle(tmp_path)
    migration = CharterBundleV2Migration()
    result = migration.apply(tmp_path, dry_run=True)

    assert len(result.changes_made) > 0, (
        "dry_run should still report the files that would change"
    )

    # Files must NOT have been mutated.
    sidecar = _load_yaml(
        tmp_path / ".kittify" / "charter" / "provenance" / "directive-use-prs.yaml"
    )
    assert sidecar.get("schema_version") == "1", (
        "dry_run must not write the sidecar; schema_version should remain '1'"
    )


def test_apply_no_charter_returns_success_no_changes(tmp_path: Path) -> None:
    """apply() on a project with no charter dir returns success with no changes."""
    migration = CharterBundleV2Migration()
    result = migration.apply(tmp_path)
    assert result.success is True
    assert result.changes_made == []
    assert result.errors == []


def test_apply_result_success_true(tmp_path: Path) -> None:
    """apply() result.success is True on a clean v1->v2 migration."""
    _create_v1_bundle(tmp_path)
    result = CharterBundleV2Migration().apply(tmp_path)
    assert result.success is True
