"""Tests for target_branch migration (0.13.7 → 0.13.8)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_0_13_8_target_branch import TargetBranchMigration


@pytest.fixture
def repo_with_features(tmp_path: Path) -> Path:
    """Create a test repository with multiple features."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    kitty_specs = repo_root / "kitty-specs"
    kitty_specs.mkdir()

    # Feature 020 - legacy feature without target_branch
    feature_020 = kitty_specs / "020-legacy-feature"
    feature_020.mkdir()
    meta_020 = {
        "feature_number": "020",
        "slug": "020-legacy-feature",
        "mission": "software-dev",
    }
    (feature_020 / "meta.json").write_text(json.dumps(meta_020, indent=2))

    # Feature 024 - legacy feature without target_branch
    feature_024 = kitty_specs / "024-another-feature"
    feature_024.mkdir()
    meta_024 = {
        "feature_number": "024",
        "slug": "024-another-feature",
        "mission": "software-dev",
    }
    (feature_024 / "meta.json").write_text(json.dumps(meta_024, indent=2))

    # Feature 025 - should auto-detect as 2.x from spec.md
    feature_025 = kitty_specs / "025-cli-event-log-integration"
    feature_025.mkdir()
    meta_025 = {
        "feature_number": "025",
        "slug": "025-cli-event-log-integration",
        "mission": "software-dev",
    }
    (feature_025 / "meta.json").write_text(json.dumps(meta_025, indent=2))

    # Add spec.md with target branch marker
    spec_025 = """# Feature 025: CLI Event Log Integration

**Target Branch**: 2.x

This feature targets the 2.x branch for SaaS platform development.
"""
    (feature_025 / "spec.md").write_text(spec_025)

    return repo_root


def test_detect_finds_features_without_target_branch(repo_with_features: Path):
    """Test migration detects features missing target_branch field."""
    migration = TargetBranchMigration()

    # Should detect that migration is needed
    needs_migration = migration.detect(repo_with_features)
    assert needs_migration is True


def test_detect_skips_when_all_have_target_branch(tmp_path: Path):
    """Test migration skips when all features have target_branch."""
    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"
    feature_dir = kitty_specs / "020-feature"
    feature_dir.mkdir(parents=True)

    meta = {
        "feature_number": "020",
        "slug": "020-feature",
        "target_branch": "main",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    migration = TargetBranchMigration()
    needs_migration = migration.detect(repo_root)
    assert needs_migration is False


def test_can_apply_returns_true(repo_with_features: Path):
    """Test migration can always be applied."""
    migration = TargetBranchMigration()

    can_apply, message = migration.can_apply(repo_with_features)
    assert can_apply is True
    assert message == ""


def test_apply_adds_target_branch_to_legacy_features(repo_with_features: Path):
    """Test migration adds target_branch='main' to legacy features."""
    migration = TargetBranchMigration()

    result = migration.apply(repo_with_features, dry_run=False)

    assert result.success is True
    assert len(result.changes_made) >= 2  # At least 020 and 024

    # Check Feature 020
    meta_020_file = repo_with_features / "kitty-specs" / "020-legacy-feature" / "meta.json"
    meta_020 = json.loads(meta_020_file.read_text())
    assert meta_020["target_branch"] == "main"

    # Check Feature 024
    meta_024_file = repo_with_features / "kitty-specs" / "024-another-feature" / "meta.json"
    meta_024 = json.loads(meta_024_file.read_text())
    assert meta_024["target_branch"] == "main"


def test_apply_detects_025_as_2x_target(repo_with_features: Path):
    """Test migration auto-detects Feature 025 as 2.x from spec.md."""
    migration = TargetBranchMigration()

    result = migration.apply(repo_with_features, dry_run=False)

    assert result.success is True

    # Check Feature 025
    meta_025_file = (
        repo_with_features / "kitty-specs" / "025-cli-event-log-integration" / "meta.json"
    )
    meta_025 = json.loads(meta_025_file.read_text())
    assert meta_025["target_branch"] == "2.x"

    # Should have a warning about auto-detection
    assert any("auto-detected" in warning for warning in result.warnings)


def test_apply_dry_run_does_not_modify_files(repo_with_features: Path):
    """Test dry run doesn't modify any files."""
    migration = TargetBranchMigration()

    # Read original meta files
    meta_020_before = (
        repo_with_features / "kitty-specs" / "020-legacy-feature" / "meta.json"
    ).read_text()

    result = migration.apply(repo_with_features, dry_run=True)

    assert result.success is True
    assert len(result.changes_made) >= 2

    # Verify file unchanged
    meta_020_after = (
        repo_with_features / "kitty-specs" / "020-legacy-feature" / "meta.json"
    ).read_text()
    assert meta_020_before == meta_020_after

    # Check dry run messages
    assert any("Would add" in change for change in result.changes_made)


def test_apply_skips_features_with_existing_target_branch(tmp_path: Path):
    """Test migration skips features that already have target_branch."""
    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"

    # Feature already has target_branch
    feature_dir = kitty_specs / "020-feature"
    feature_dir.mkdir(parents=True)
    meta = {
        "feature_number": "020",
        "slug": "020-feature",
        "target_branch": "main",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    migration = TargetBranchMigration()
    result = migration.apply(repo_root, dry_run=False)

    # Should succeed but make no changes
    assert result.success is True
    assert len(result.changes_made) == 0


def test_apply_handles_malformed_json(tmp_path: Path):
    """Test migration handles malformed JSON gracefully."""
    repo_root = tmp_path / "repo"
    kitty_specs = repo_root / "kitty-specs"

    # Create feature with malformed JSON
    feature_dir = kitty_specs / "020-broken"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text("{invalid json")

    migration = TargetBranchMigration()
    result = migration.apply(repo_root, dry_run=False)

    # Should fail but report error
    assert result.success is False
    assert len(result.errors) == 1
    assert "Malformed JSON" in result.errors[0]


def test_apply_handles_missing_kitty_specs(tmp_path: Path):
    """Test migration handles missing kitty-specs directory."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    # No kitty-specs directory created

    migration = TargetBranchMigration()
    result = migration.apply(repo_root, dry_run=False)

    assert result.success is True
    assert "No features found" in result.changes_made[0]


def test_migration_preserves_json_formatting(repo_with_features: Path):
    """Test migration preserves pretty-printed JSON formatting."""
    migration = TargetBranchMigration()

    result = migration.apply(repo_with_features, dry_run=False)
    assert result.success is True

    # Check JSON is still pretty-printed
    meta_file = repo_with_features / "kitty-specs" / "020-legacy-feature" / "meta.json"
    content = meta_file.read_text()

    # Should have indentation
    assert "  " in content  # 2-space indent
    # Should end with newline
    assert content.endswith("\n")
    # Should be valid JSON
    meta = json.loads(content)
    assert "target_branch" in meta


def test_migration_metadata():
    """Test migration has correct metadata."""
    migration = TargetBranchMigration()

    assert migration.migration_id == "0.13.8_target_branch"
    assert migration.description == "Add target_branch field to feature metadata"
    assert migration.target_version == "0.13.8"
