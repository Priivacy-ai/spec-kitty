"""Tests for the m_0_10_12_charter_cleanup migration (stub).

This migration was superseded by 3.1.1_charter_rename. The runner-reachable
contract is that legacy state stays disabled while its registry identity remains.
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


def test_migration_metadata(migration: CharterCleanupMigration) -> None:
    """Stub retains correct migration ID and version."""
    assert migration.migration_id == "0.10.12_charter_cleanup"
    assert migration.target_version == "0.10.12"
