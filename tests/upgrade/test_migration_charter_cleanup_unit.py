"""Tests for the m_0_10_12_charter_cleanup migration."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_0_10_12_charter_cleanup import (
    CharterCleanupMigration,
)


@pytest.fixture
def migration() -> CharterCleanupMigration:
    """Create migration instance."""
    return CharterCleanupMigration()


def test_detects_charter_dir(migration: CharterCleanupMigration, tmp_path: Path) -> None:
    """Detect returns True when charter directory exists."""
    charter_dir = tmp_path / ".kittify" / "missions" / "software-dev" / "charter"
    charter_dir.mkdir(parents=True)

    assert migration.detect(tmp_path) is True


def test_detects_no_missions(migration: CharterCleanupMigration, tmp_path: Path) -> None:
    """Detect returns False when missions directory missing."""
    assert migration.detect(tmp_path) is False


def test_apply_removes_charter(migration: CharterCleanupMigration, tmp_path: Path) -> None:
    """Apply removes mission charters."""
    charter_dir = tmp_path / ".kittify" / "missions" / "software-dev" / "charter"
    charter_dir.mkdir(parents=True)
    (charter_dir / "principles.md").write_text("# Test")

    result = migration.apply(tmp_path, dry_run=False)

    assert result.success is True
    assert not charter_dir.exists()
    assert any("Removed software-dev/charter/" in change for change in result.changes_made)


def test_apply_dry_run(migration: CharterCleanupMigration, tmp_path: Path) -> None:
    """Dry run reports removal without changing filesystem."""
    charter_dir = tmp_path / ".kittify" / "missions" / "research" / "charter"
    charter_dir.mkdir(parents=True)

    result = migration.apply(tmp_path, dry_run=True)

    assert result.success is True
    assert charter_dir.exists()
    assert any("Would remove research/charter/" in change for change in result.changes_made)


def test_apply_idempotent(migration: CharterCleanupMigration, tmp_path: Path) -> None:
    """Apply is idempotent when run twice."""
    charter_dir = tmp_path / ".kittify" / "missions" / "research" / "charter"
    charter_dir.mkdir(parents=True)

    result1 = migration.apply(tmp_path, dry_run=False)
    result2 = migration.apply(tmp_path, dry_run=False)

    assert result1.success is True
    assert result2.success is True
