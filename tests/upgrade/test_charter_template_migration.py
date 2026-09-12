"""Tests for charter template migration (m_0_13_0_update_charter_templates) stub.

This migration was superseded by 3.1.1_charter_rename. The runner-reachable
contract is that its detection stays disabled while its registry identity remains.
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


def test_migration_metadata(migration) -> None:
    """Stub retains correct migration ID and version."""
    assert migration.migration_id == "0.13.0_update_charter_templates"
    assert migration.target_version == "0.13.0"
