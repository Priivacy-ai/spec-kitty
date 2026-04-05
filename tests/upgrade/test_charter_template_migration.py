"""Tests for charter template migration (m_0_13_0_update_charter_templates) stub.

This migration was superseded by 3.1.1_charter_rename. It is now a stub
that always returns detect() -> False and apply() -> success=True.
"""

from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_0_13_0_update_charter_templates import (
    UpdateCharterTemplatesMigration,
)

pytestmark = pytest.mark.fast


@pytest.fixture
def migration():
    """Return the migration instance."""
    return UpdateCharterTemplatesMigration()


def test_detect_always_returns_false(tmp_path: Path, migration) -> None:
    """Stub detect() always returns False (migration is inert)."""
    assert migration.detect(tmp_path) is False


def test_can_apply_always_returns_false(tmp_path: Path, migration) -> None:
    """Stub can_apply() returns False with superseded reason."""
    result, reason = migration.can_apply(tmp_path)
    assert result is False
    assert "superseded" in reason.lower() or "charter-rename" in reason.lower()


def test_apply_returns_success(tmp_path: Path, migration) -> None:
    """Stub apply() returns success without modifying filesystem."""
    result = migration.apply(tmp_path, dry_run=False)
    assert result.success is True


def test_apply_dry_run_returns_success(tmp_path: Path, migration) -> None:
    """Stub apply() dry_run also returns success."""
    result = migration.apply(tmp_path, dry_run=True)
    assert result.success is True


def test_migration_metadata(migration) -> None:
    """Stub retains correct migration ID and version."""
    assert migration.migration_id == "0.13.0_update_charter_templates"
    assert migration.target_version == "0.13.0"
