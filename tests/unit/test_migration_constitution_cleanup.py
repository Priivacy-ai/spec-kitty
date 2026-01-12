"""Tests for the m_0_10_12_constitution_cleanup migration."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_0_10_12_constitution_cleanup import (
    ConstitutionCleanupMigration,
)


@pytest.fixture
def migration() -> ConstitutionCleanupMigration:
    """Create migration instance."""
    return ConstitutionCleanupMigration()


def test_detects_constitution_dir(migration: ConstitutionCleanupMigration, tmp_path: Path) -> None:
    """Detect returns True when constitution directory exists."""
    constitution_dir = tmp_path / ".kittify" / "missions" / "software-dev" / "constitution"
    constitution_dir.mkdir(parents=True)

    assert migration.detect(tmp_path) is True


def test_detects_no_missions(migration: ConstitutionCleanupMigration, tmp_path: Path) -> None:
    """Detect returns False when missions directory missing."""
    assert migration.detect(tmp_path) is False


def test_apply_removes_constitution(migration: ConstitutionCleanupMigration, tmp_path: Path) -> None:
    """Apply removes mission constitutions."""
    constitution_dir = tmp_path / ".kittify" / "missions" / "software-dev" / "constitution"
    constitution_dir.mkdir(parents=True)
    (constitution_dir / "principles.md").write_text("# Test")

    result = migration.apply(tmp_path, dry_run=False)

    assert result.success is True
    assert not constitution_dir.exists()
    assert any("Removed software-dev/constitution/" in change for change in result.changes_made)


def test_apply_dry_run(migration: ConstitutionCleanupMigration, tmp_path: Path) -> None:
    """Dry run reports removal without changing filesystem."""
    constitution_dir = tmp_path / ".kittify" / "missions" / "research" / "constitution"
    constitution_dir.mkdir(parents=True)

    result = migration.apply(tmp_path, dry_run=True)

    assert result.success is True
    assert constitution_dir.exists()
    assert any("Would remove research/constitution/" in change for change in result.changes_made)


def test_apply_idempotent(migration: ConstitutionCleanupMigration, tmp_path: Path) -> None:
    """Apply is idempotent when run twice."""
    constitution_dir = tmp_path / ".kittify" / "missions" / "research" / "constitution"
    constitution_dir.mkdir(parents=True)

    result1 = migration.apply(tmp_path, dry_run=False)
    result2 = migration.apply(tmp_path, dry_run=False)

    assert result1.success is True
    assert result2.success is True
