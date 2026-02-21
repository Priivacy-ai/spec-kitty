"""Tests for migration m_2_0_0_constitution_directory."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

from specify_cli.upgrade.migrations.m_2_0_0_constitution_directory import Migration


class TestConstitutionDirectoryMigration:
    """Test the constitution directory migration."""

    def test_scenario_1_old_exists_new_doesnt(self, tmp_path: Path):
        """Scenario 1: Old path exists, new doesn't → file moved."""
        # Setup
        old_path = tmp_path / ".kittify" / "memory" / "constitution.md"
        old_path.parent.mkdir(parents=True)
        old_path.write_text("# Project Constitution\n\nTest content")

        # Run migration
        migration = Migration()
        with patch("specify_cli.constitution.sync.sync") as mock_sync:
            mock_sync.return_value = Mock(synced=True, files_written=["governance.yaml"], error=None)
            changes = migration.apply(tmp_path, dry_run=False)

        # Verify file was moved
        new_path = tmp_path / ".kittify" / "constitution" / "constitution.md"
        assert new_path.exists()
        assert new_path.read_text() == "# Project Constitution\n\nTest content"
        assert not old_path.exists()

        # Verify changes reported
        assert any("Moved" in change for change in changes)
        assert any("Initial extraction" in change for change in changes)

    def test_scenario_1_dry_run(self, tmp_path: Path):
        """Scenario 1 with dry_run: Should not move file but report what would happen."""
        # Setup
        old_path = tmp_path / ".kittify" / "memory" / "constitution.md"
        old_path.parent.mkdir(parents=True)
        old_path.write_text("# Test")

        # Run migration in dry-run mode
        migration = Migration()
        changes = migration.apply(tmp_path, dry_run=True)

        # Verify file was NOT moved
        assert old_path.exists()
        new_path = tmp_path / ".kittify" / "constitution" / "constitution.md"
        assert not new_path.exists()

        # Verify changes reported
        assert any("Would move" in change for change in changes)

    def test_scenario_2_both_exist(self, tmp_path: Path):
        """Scenario 2: Both paths exist → skip (user already migrated manually)."""
        # Setup
        old_path = tmp_path / ".kittify" / "memory" / "constitution.md"
        old_path.parent.mkdir(parents=True)
        old_path.write_text("# Old")

        new_path = tmp_path / ".kittify" / "constitution" / "constitution.md"
        new_path.parent.mkdir(parents=True)
        new_path.write_text("# New")

        # Run migration
        migration = Migration()
        changes = migration.apply(tmp_path, dry_run=False)

        # Verify both files still exist
        assert old_path.exists()
        assert new_path.exists()

        # Verify changes reported
        assert any("already at" in change and "old copy" in change for change in changes)

    def test_scenario_3_new_exists_old_doesnt(self, tmp_path: Path):
        """Scenario 3: New exists, old doesn't → skip (already migrated)."""
        # Setup
        new_path = tmp_path / ".kittify" / "constitution" / "constitution.md"
        new_path.parent.mkdir(parents=True)
        new_path.write_text("# New")

        # Run migration
        migration = Migration()
        changes = migration.apply(tmp_path, dry_run=False)

        # Verify only new file exists
        assert new_path.exists()
        old_path = tmp_path / ".kittify" / "memory" / "constitution.md"
        assert not old_path.exists()

        # Verify changes reported
        assert any("already at" in change for change in changes)

    def test_scenario_4_neither_exists(self, tmp_path: Path):
        """Scenario 4: Neither exists → skip (no constitution)."""
        # Run migration
        migration = Migration()
        changes = migration.apply(tmp_path, dry_run=False)

        # Verify no files created
        old_path = tmp_path / ".kittify" / "memory" / "constitution.md"
        new_path = tmp_path / ".kittify" / "constitution" / "constitution.md"
        assert not old_path.exists()
        assert not new_path.exists()

        # Verify changes reported
        assert any("No constitution found" in change for change in changes)

    def test_initial_sync_triggered(self, tmp_path: Path):
        """Initial sync should be triggered after moving file."""
        # Setup
        old_path = tmp_path / ".kittify" / "memory" / "constitution.md"
        old_path.parent.mkdir(parents=True)
        old_path.write_text("# Test")

        # Run migration
        migration = Migration()
        with patch("specify_cli.constitution.sync.sync") as mock_sync:
            mock_sync.return_value = Mock(synced=True, files_written=["governance.yaml", "agents.yaml"], error=None)
            changes = migration.apply(tmp_path, dry_run=False)

            # Verify sync was called
            new_path = tmp_path / ".kittify" / "constitution" / "constitution.md"
            mock_sync.assert_called_once_with(new_path, force=True)

        # Verify extraction reported
        assert any("Initial extraction: 2 YAML files created" in change for change in changes)

    def test_initial_sync_failure_graceful(self, tmp_path: Path):
        """Initial sync failure should not block migration."""
        # Setup
        old_path = tmp_path / ".kittify" / "memory" / "constitution.md"
        old_path.parent.mkdir(parents=True)
        old_path.write_text("# Test")

        # Run migration with sync failure
        migration = Migration()
        with patch("specify_cli.constitution.sync.sync") as mock_sync:
            mock_sync.return_value = Mock(synced=False, files_written=[], error="AI unavailable")
            changes = migration.apply(tmp_path, dry_run=False)

        # Verify file was still moved
        new_path = tmp_path / ".kittify" / "constitution" / "constitution.md"
        assert new_path.exists()

        # Verify warning reported
        assert any("Warning: Initial extraction failed" in change for change in changes)

    def test_initial_sync_exception_graceful(self, tmp_path: Path):
        """Initial sync exception should not block migration."""
        # Setup
        old_path = tmp_path / ".kittify" / "memory" / "constitution.md"
        old_path.parent.mkdir(parents=True)
        old_path.write_text("# Test")

        # Run migration with sync exception
        migration = Migration()
        with patch("specify_cli.constitution.sync.sync") as mock_sync:
            mock_sync.side_effect = ImportError("Module not found")
            changes = migration.apply(tmp_path, dry_run=False)

        # Verify file was still moved
        new_path = tmp_path / ".kittify" / "constitution" / "constitution.md"
        assert new_path.exists()

        # Verify warning reported
        assert any("Warning: Initial extraction skipped" in change for change in changes)

    def test_idempotency(self, tmp_path: Path):
        """Running migration twice should be safe (idempotent)."""
        # Setup
        old_path = tmp_path / ".kittify" / "memory" / "constitution.md"
        old_path.parent.mkdir(parents=True)
        old_path.write_text("# Test")

        # Run migration first time
        migration = Migration()
        with patch("specify_cli.constitution.sync.sync"):
            changes1 = migration.apply(tmp_path, dry_run=False)

        # Verify moved
        new_path = tmp_path / ".kittify" / "constitution" / "constitution.md"
        assert new_path.exists()
        assert any("Moved" in change for change in changes1)

        # Run migration second time
        with patch("specify_cli.constitution.sync.sync"):
            changes2 = migration.apply(tmp_path, dry_run=False)

        # Verify skipped (scenario 3)
        assert any("already at" in change for change in changes2)

    def test_migration_metadata(self):
        """Test migration version and description."""
        migration = Migration()
        assert migration.version == "2.0.0"
        assert "constitution" in migration.description.lower()
        assert "directory" in migration.description.lower()

    def test_creates_new_directory(self, tmp_path: Path):
        """Migration should create .kittify/constitution/ directory."""
        # Setup
        old_path = tmp_path / ".kittify" / "memory" / "constitution.md"
        old_path.parent.mkdir(parents=True)
        old_path.write_text("# Test")

        # Run migration
        migration = Migration()
        with patch("specify_cli.constitution.sync.sync"):
            migration.apply(tmp_path, dry_run=False)

        # Verify directory created
        new_dir = tmp_path / ".kittify" / "constitution"
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_preserves_memory_directory(self, tmp_path: Path):
        """Migration should NOT delete .kittify/memory/ directory (other files may exist)."""
        # Setup
        memory_dir = tmp_path / ".kittify" / "memory"
        memory_dir.mkdir(parents=True)
        constitution = memory_dir / "constitution.md"
        constitution.write_text("# Test")
        other_file = memory_dir / "other.txt"
        other_file.write_text("Other content")

        # Run migration
        migration = Migration()
        with patch("specify_cli.constitution.sync.sync"):
            migration.apply(tmp_path, dry_run=False)

        # Verify memory directory still exists with other file
        assert memory_dir.exists()
        assert other_file.exists()
        assert not constitution.exists()  # Constitution moved

    def test_relative_paths_in_changes(self, tmp_path: Path):
        """Changes should report relative paths for readability."""
        # Setup
        old_path = tmp_path / ".kittify" / "memory" / "constitution.md"
        old_path.parent.mkdir(parents=True)
        old_path.write_text("# Test")

        # Run migration
        migration = Migration()
        with patch("specify_cli.constitution.sync.sync"):
            changes = migration.apply(tmp_path, dry_run=False)

        # Verify relative paths used
        assert any(
            ".kittify/memory/constitution.md" in change and ".kittify/constitution/constitution.md" in change
            for change in changes
        )
