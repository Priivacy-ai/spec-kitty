"""Tests for migration m_2_0_0_charter_directory (stub).

This migration was superseded by 3.1.1_charter_rename. It is now a stub
that always returns detect() -> False and apply() -> success=True.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_2_0_0_charter_directory import (
    CharterDirectoryMigration,
)

pytestmark = pytest.mark.fast


class TestCharterDirectoryMigrationStub:
    """Test the charter directory migration stub behavior."""

    def test_detect_always_returns_false(self, tmp_path: Path) -> None:
        """Stub detect() always returns False regardless of filesystem state."""
        migration = CharterDirectoryMigration()

        # Even with legacy state present, stub should not detect
        legacy = tmp_path / ".kittify" / "memory" / "charter.md"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("# Legacy")

        assert migration.detect(tmp_path) is False

    def test_detect_empty_project(self, tmp_path: Path) -> None:
        """Stub detect() returns False on empty project."""
        migration = CharterDirectoryMigration()
        assert migration.detect(tmp_path) is False

    def test_can_apply_returns_false(self, tmp_path: Path) -> None:
        """Stub can_apply() always returns False with reason."""
        migration = CharterDirectoryMigration()
        result, reason = migration.can_apply(tmp_path)
        assert result is False
        assert "superseded" in reason.lower() or "charter-rename" in reason.lower()

    def test_apply_returns_success(self, tmp_path: Path) -> None:
        """Stub apply() returns MigrationResult with success=True."""
        migration = CharterDirectoryMigration()
        result = migration.apply(tmp_path, dry_run=False)
        assert result.success is True

    def test_apply_dry_run_returns_success(self, tmp_path: Path) -> None:
        """Stub apply() returns success even in dry_run mode."""
        migration = CharterDirectoryMigration()
        result = migration.apply(tmp_path, dry_run=True)
        assert result.success is True

    def test_migration_metadata(self) -> None:
        """Stub retains correct migration ID and target version."""
        migration = CharterDirectoryMigration()
        assert migration.migration_id == "2.0.0_charter_directory"
        assert migration.target_version == "2.0.0"
        assert "charter" in migration.description.lower() or "superseded" in migration.description.lower()
