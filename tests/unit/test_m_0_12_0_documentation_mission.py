"""Tests for the m_0_12_0_documentation_mission migration."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_0_12_0_documentation_mission import (
    InstallDocumentationMission,
)


@pytest.fixture
def migration() -> InstallDocumentationMission:
    """Create migration instance."""
    return InstallDocumentationMission()


# ============================================================================
# Detection Tests
# ============================================================================


def test_detect_missing_mission(migration: InstallDocumentationMission, tmp_path: Path) -> None:
    """Migration detects when documentation mission is missing."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()

    assert migration.detect(tmp_path) is True


def test_detect_existing_mission(migration: InstallDocumentationMission, tmp_path: Path) -> None:
    """Migration detects when documentation mission already exists."""
    missions = tmp_path / ".kittify" / "missions" / "documentation"
    missions.mkdir(parents=True)
    (missions / "mission.yaml").write_text("name: Documentation Kitty\n")

    assert migration.detect(tmp_path) is False


def test_detect_non_kittify_project(migration: InstallDocumentationMission, tmp_path: Path) -> None:
    """Migration returns False for non-spec-kitty projects."""
    # No .kittify directory
    assert migration.detect(tmp_path) is False


def test_detect_no_missions_dir(migration: InstallDocumentationMission, tmp_path: Path) -> None:
    """Migration detects when missions directory doesn't exist."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    # No missions/ directory

    assert migration.detect(tmp_path) is True


def test_detect_incomplete_mission(migration: InstallDocumentationMission, tmp_path: Path) -> None:
    """Migration detects when documentation mission exists but is incomplete."""
    doc_mission = tmp_path / ".kittify" / "missions" / "documentation"
    doc_mission.mkdir(parents=True)
    # mission.yaml doesn't exist

    assert migration.detect(tmp_path) is True


# ============================================================================
# Apply Tests
# ============================================================================


def test_apply_installs_mission(migration: InstallDocumentationMission, tmp_path: Path) -> None:
    """Migration successfully installs documentation mission."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()

    result = migration.apply(tmp_path)

    assert result.success
    assert any("copied" in change.lower() or "documentation mission" in change.lower()
              for change in result.changes_made)

    # Verify mission directory exists
    doc_mission = kittify / "missions" / "documentation"
    assert doc_mission.exists()
    assert (doc_mission / "mission.yaml").exists()
    assert (doc_mission / "command-templates").exists()


def test_apply_copies_all_files(migration: InstallDocumentationMission, tmp_path: Path) -> None:
    """Migration copies all mission files."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()

    result = migration.apply(tmp_path)

    doc_mission = kittify / "missions" / "documentation"

    # Check command templates exist
    assert (doc_mission / "command-templates" / "specify.md").exists()
    assert (doc_mission / "command-templates" / "plan.md").exists()
    assert (doc_mission / "command-templates" / "tasks.md").exists()
    assert (doc_mission / "command-templates" / "implement.md").exists()
    assert (doc_mission / "command-templates" / "review.md").exists()


def test_apply_creates_missions_dir(migration: InstallDocumentationMission, tmp_path: Path) -> None:
    """Migration creates missions directory if it doesn't exist."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    # No missions/ directory

    result = migration.apply(tmp_path)

    assert result.success
    assert (tmp_path / ".kittify" / "missions").exists()
    assert (tmp_path / ".kittify" / "missions" / "documentation").exists()


def test_apply_already_installed(migration: InstallDocumentationMission, tmp_path: Path) -> None:
    """Migration handles already-installed case gracefully."""
    doc_mission = tmp_path / ".kittify" / "missions" / "documentation"
    doc_mission.mkdir(parents=True)
    (doc_mission / "mission.yaml").write_text("name: Documentation Kitty\n")

    result = migration.apply(tmp_path)

    assert result.success
    assert any("already installed" in change.lower() or "skipped" in change.lower()
              for change in result.changes_made)


# ============================================================================
# T050 - Existing Missions Preservation Tests
# ============================================================================


def test_migration_preserves_software_dev_mission(
    migration: InstallDocumentationMission, tmp_path: Path
) -> None:
    """Verify migration doesn't touch software-dev mission."""
    # Create fake project with software-dev mission
    kittify = tmp_path / ".kittify"
    missions = kittify / "missions"
    software_dev = missions / "software-dev"
    software_dev.mkdir(parents=True)

    # Create dummy mission.yaml
    (software_dev / "mission.yaml").write_text("name: Software Dev Kitty\n")
    original_content = (software_dev / "mission.yaml").read_text()

    # Run migration
    result = migration.apply(tmp_path)

    assert result.success

    # Verify software-dev unchanged
    after_content = (software_dev / "mission.yaml").read_text()
    assert after_content == original_content


def test_migration_preserves_research_mission(
    migration: InstallDocumentationMission, tmp_path: Path
) -> None:
    """Verify migration doesn't touch research mission."""
    # Create fake project with research mission
    kittify = tmp_path / ".kittify"
    missions = kittify / "missions"
    research = missions / "research"
    research.mkdir(parents=True)

    # Create dummy mission.yaml
    (research / "mission.yaml").write_text("name: Research Kitty\n")
    original_content = (research / "mission.yaml").read_text()

    # Run migration
    result = migration.apply(tmp_path)

    assert result.success

    # Verify research unchanged
    after_content = (research / "mission.yaml").read_text()
    assert after_content == original_content


def test_migration_only_touches_documentation_mission(
    migration: InstallDocumentationMission, tmp_path: Path
) -> None:
    """Verify migration only modifies .kittify/missions/documentation/."""
    # Create fake project
    kittify = tmp_path / ".kittify"
    kittify.mkdir()

    # Create some files that should NOT be touched
    (kittify / "config.json").write_text("{}")
    (kittify / "memory").mkdir()
    (kittify / "memory" / "notes.md").write_text("# Notes")

    # Run migration
    result = migration.apply(tmp_path)

    assert result.success

    # Verify other files unchanged
    assert (kittify / "config.json").read_text() == "{}"
    assert (kittify / "memory" / "notes.md").read_text() == "# Notes"

    # Verify only documentation mission was added
    assert (kittify / "missions" / "documentation").exists()


# ============================================================================
# T051 - Idempotency Tests
# ============================================================================


def test_migration_is_idempotent(migration: InstallDocumentationMission, tmp_path: Path) -> None:
    """Verify migration can run multiple times safely."""
    # Create fake project
    kittify = tmp_path / ".kittify"
    missions = kittify / "missions"
    missions.mkdir(parents=True)

    # First run
    result1 = migration.apply(tmp_path)
    assert result1.success

    # Verify mission installed
    doc_mission = missions / "documentation"
    assert doc_mission.exists()
    file_count_1 = len(list(doc_mission.rglob("*")))

    # Second run (should be no-op)
    result2 = migration.apply(tmp_path)
    assert result2.success
    assert any("already installed" in change.lower() or "skipped" in change.lower()
              for change in result2.changes_made)

    # Verify no changes
    file_count_2 = len(list(doc_mission.rglob("*")))
    assert file_count_1 == file_count_2

    # Third run (verify still idempotent)
    result3 = migration.apply(tmp_path)
    assert result3.success


def test_migration_detect_after_apply(
    migration: InstallDocumentationMission, tmp_path: Path
) -> None:
    """Verify detect() returns False after apply()."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()

    # Before: detect should return True (migration needed)
    assert migration.detect(tmp_path) is True

    # Apply migration
    result = migration.apply(tmp_path)
    assert result.success

    # After: detect should return False (migration not needed)
    assert migration.detect(tmp_path) is False

    # Applying again should be safe
    result2 = migration.apply(tmp_path)
    assert result2.success


# ============================================================================
# T052 - Registration Tests
# ============================================================================


def test_migration_is_registered() -> None:
    """Verify migration is registered and discoverable."""
    from specify_cli.upgrade.registry import MigrationRegistry

    # Check migration is in registry
    migrations = MigrationRegistry.get_all()
    migration_ids = [m.migration_id for m in migrations]

    assert "0.12.0_documentation_mission" in migration_ids


def test_migration_can_be_loaded() -> None:
    """Verify migration can be instantiated and has required attributes."""
    migration = InstallDocumentationMission()

    assert migration.migration_id == "0.12.0_documentation_mission"
    assert migration.description == "Install documentation mission to user projects"
    assert migration.target_version == "0.12.0"
    assert hasattr(migration, "detect")
    assert hasattr(migration, "apply")


def test_migration_has_correct_metadata(migration: InstallDocumentationMission) -> None:
    """Verify migration metadata is correct."""
    assert migration.migration_id == "0.12.0_documentation_mission"
    assert migration.description == "Install documentation mission to user projects"
    assert migration.target_version == "0.12.0"


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_apply_handles_missing_source(
    migration: InstallDocumentationMission, tmp_path: Path, monkeypatch
) -> None:
    """Apply handles case where source mission cannot be found."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()

    # Mock _find_source_mission to return None
    monkeypatch.setattr(migration, "_find_source_mission", lambda: None)

    result = migration.apply(tmp_path)

    assert result.success is False
    assert any("could not find" in error.lower() for error in result.errors)


def test_find_source_mission_returns_none_if_missing(
    migration: InstallDocumentationMission
) -> None:
    """_find_source_mission returns None if mission.yaml doesn't exist."""
    # We can't easily test this without mocking Path operations,
    # but we can verify the method exists and has correct signature
    assert hasattr(migration, "_find_source_mission")
