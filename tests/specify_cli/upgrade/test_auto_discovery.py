"""Tests for automatic migration discovery system.

Validates that migrations are auto-discovered from filesystem
without requiring manual imports in __init__.py.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.upgrade.migrations import auto_discover_migrations
from specify_cli.upgrade.registry import MigrationRegistry


class TestAutoDiscovery:
    """Test automatic migration discovery."""

    def test_auto_discover_finds_all_migrations(self):
        """All migration files matching m_*.py pattern are discovered."""
        # Clear registry
        MigrationRegistry.clear()

        # Count migration files in directory
        migrations_dir = Path(__file__).parent.parent.parent.parent / "src" / "specify_cli" / "upgrade" / "migrations"
        migration_files = list(migrations_dir.glob("m_*.py"))
        expected_count = len(migration_files)

        # Run auto-discovery
        auto_discover_migrations()

        # Verify all discovered
        discovered = MigrationRegistry.get_all()
        assert len(discovered) == expected_count, (
            f"Expected {expected_count} migrations (matching m_*.py pattern), "
            f"but discovered {len(discovered)}"
        )

    def test_auto_discover_is_idempotent(self):
        """Running auto-discovery multiple times doesn't cause issues."""
        MigrationRegistry.clear()

        # Run discovery twice
        auto_discover_migrations()
        count_first = len(MigrationRegistry.get_all())

        auto_discover_migrations()
        count_second = len(MigrationRegistry.get_all())

        # Should have same count (no duplicates)
        assert count_first == count_second

    def test_auto_discover_skips_non_migration_files(self):
        """Files not matching m_*.py pattern are skipped."""
        MigrationRegistry.clear()
        auto_discover_migrations()

        # Get all migration IDs
        migration_ids = [m.migration_id for m in MigrationRegistry.get_all()]

        # Should not include base.py, __init__.py, or test files
        assert "base" not in migration_ids
        assert "__init__" not in migration_ids
        assert "test_" not in " ".join(migration_ids)

    def test_auto_discover_handles_import_errors_gracefully(self, capsys):
        """Import errors are logged but don't crash discovery."""
        MigrationRegistry.clear()

        # Mock pkgutil to return a fake module that will fail import
        with patch("specify_cli.upgrade.migrations.pkgutil.iter_modules") as mock_iter:
            # Create a fake module info
            class FakeModuleInfo:
                name = "m_fake_broken"

            # Return our fake module plus one real one
            mock_iter.return_value = [FakeModuleInfo()]

            # This should log a warning but not crash
            auto_discover_migrations()

            # Check stderr for warning
            captured = capsys.readouterr()
            assert "Warning" in captured.err or "Failed to import" in captured.err

    def test_auto_discover_imports_base_module(self):
        """The base.py module is also imported (needed for BaseMigration)."""
        # This is implicitly tested - if base.py isn't imported,
        # the migration classes won't have BaseMigration available
        # and the whole system would crash

        MigrationRegistry.clear()
        auto_discover_migrations()

        # If we got here without crashing, base.py was imported correctly
        assert len(MigrationRegistry.get_all()) > 0

    def test_discovered_migrations_have_required_attributes(self):
        """All discovered migrations have required attributes."""
        MigrationRegistry.clear()
        auto_discover_migrations()

        for migration in MigrationRegistry.get_all():
            # Check required attributes exist
            assert hasattr(migration, "migration_id")
            assert hasattr(migration, "description")
            assert hasattr(migration, "target_version")

            # Check they're not empty
            assert migration.migration_id
            assert migration.description
            assert migration.target_version

    def test_discovered_migrations_are_sorted_by_version(self):
        """Migrations are returned in version order."""
        MigrationRegistry.clear()
        auto_discover_migrations()

        migrations = MigrationRegistry.get_all()

        # Extract versions
        versions = [m.target_version for m in migrations]

        # Verify they're in ascending order
        from packaging.version import Version
        sorted_versions = sorted(versions, key=Version)

        assert versions == sorted_versions, "Migrations should be sorted by target_version"

    def test_auto_discover_called_on_module_import(self):
        """Auto-discovery runs automatically when migrations module is imported."""
        # This test verifies the module-level call works
        # We can't really test this without reimporting, but we can verify
        # that importing the module populates the registry

        # Import fresh (this happens in conftest or test setup)
        from specify_cli.upgrade import migrations  # noqa: F401

        # Verify registry is populated
        assert len(MigrationRegistry.get_all()) > 0

    def test_all_migration_files_have_registration_decorator(self):
        """All m_*.py files use @MigrationRegistry.register decorator."""
        migrations_dir = Path(__file__).parent.parent.parent.parent / "src" / "specify_cli" / "upgrade" / "migrations"

        for migration_file in migrations_dir.glob("m_*.py"):
            # Read file content
            content = migration_file.read_text()

            # Check for @MigrationRegistry.register
            assert "@MigrationRegistry.register" in content, (
                f"Migration {migration_file.name} missing @MigrationRegistry.register decorator"
            )


class TestAutoDiscoveryIntegration:
    """Integration tests for auto-discovery with upgrade workflow."""

    def test_upgrade_command_uses_auto_discovered_migrations(self, tmp_path):
        """The upgrade command can use auto-discovered migrations."""
        from specify_cli.upgrade.detector import VersionDetector
        from specify_cli.upgrade.runner import MigrationRunner

        # Create a fake project
        kittify_dir = tmp_path / ".kittify"
        kittify_dir.mkdir()

        # Create metadata with old version
        metadata_file = kittify_dir / "metadata.json"
        metadata_file.write_text('{"version": "0.1.0", "applied_migrations": []}')

        # Get applicable migrations
        detector = VersionDetector(tmp_path)
        current_version = detector.detect_version()

        # This should work with auto-discovered migrations
        applicable = MigrationRegistry.get_applicable(
            from_version="0.1.0",
            to_version="999.0.0",  # Get all migrations
            project_path=tmp_path
        )

        # Should have many migrations
        assert len(applicable) > 20, "Should have discovered many migrations"

    def test_auto_discovery_performance(self):
        """Auto-discovery completes quickly (< 1 second)."""
        import time

        MigrationRegistry.clear()

        start = time.time()
        auto_discover_migrations()
        duration = time.time() - start

        # Should be very fast (usually < 100ms, but allow 1s for CI)
        assert duration < 1.0, f"Auto-discovery took {duration:.2f}s (should be < 1s)"


class TestBackwardCompatibility:
    """Ensure auto-discovery doesn't break existing behavior."""

    def test_manual_registration_still_works(self):
        """Manual @MigrationRegistry.register still works for tests."""
        from specify_cli.upgrade.migrations.base import BaseMigration, MigrationResult

        MigrationRegistry.clear()

        @MigrationRegistry.register
        class TestMigration(BaseMigration):
            migration_id = "test_manual"
            description = "Test manual registration"
            target_version = "999.0.0"

            def detect(self, project_path):
                return False

            def can_apply(self, project_path):
                return True, ""

            def apply(self, project_path, dry_run=False):
                return MigrationResult(success=True)

        # Verify it registered
        assert MigrationRegistry.get_by_id("test_manual") is not None

    def test_clear_registry_still_works(self):
        """MigrationRegistry.clear() still works (needed for test isolation)."""
        auto_discover_migrations()
        assert len(MigrationRegistry.get_all()) > 0

        MigrationRegistry.clear()
        assert len(MigrationRegistry.get_all()) == 0

        # Can re-discover
        auto_discover_migrations()
        assert len(MigrationRegistry.get_all()) > 0
