"""Tests for the m_0_10_12_charter_cleanup migration (stub).

This migration was superseded by 3.1.1_charter_rename. It is now a stub
that always returns detect() -> False and apply() -> success=True.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_0_10_12_charter_cleanup import (
    CharterCleanupMigration,
)

pytestmark = pytest.mark.fast


@pytest.fixture
def migration() -> CharterCleanupMigration:
    """Create migration instance."""
    return CharterCleanupMigration()


def test_detect_always_returns_false(migration: CharterCleanupMigration, tmp_path: Path) -> None:
    """Stub detect() returns False even when legacy state exists."""
    charter_dir = tmp_path / ".kittify" / "missions" / "software-dev" / "charter"
    charter_dir.mkdir(parents=True)
    assert migration.detect(tmp_path) is False


def test_detect_empty_project(migration: CharterCleanupMigration, tmp_path: Path) -> None:
    """Stub detect() returns False on empty project."""
    assert migration.detect(tmp_path) is False


def test_can_apply_returns_false(migration: CharterCleanupMigration, tmp_path: Path) -> None:
    """Stub can_apply() returns False with reason."""
    result, reason = migration.can_apply(tmp_path)
    assert result is False
    assert "superseded" in reason.lower() or "charter-rename" in reason.lower()


def test_apply_returns_success(migration: CharterCleanupMigration, tmp_path: Path) -> None:
    """Stub apply() returns MigrationResult with success=True."""
    result = migration.apply(tmp_path, dry_run=False)
    assert result.success is True


def test_apply_dry_run_returns_success(migration: CharterCleanupMigration, tmp_path: Path) -> None:
    """Stub apply() returns success in dry_run mode."""
    result = migration.apply(tmp_path, dry_run=True)
    assert result.success is True


def test_migration_metadata(migration: CharterCleanupMigration) -> None:
    """Stub retains correct migration ID and version."""
    assert migration.migration_id == "0.10.12_charter_cleanup"
    assert migration.target_version == "0.10.12"
