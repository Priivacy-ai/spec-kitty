"""Tests for the historical status migration upgrade wrapper — tombstone.

HistoricalStatusMigration (2.0.0_historical_status_migration) was converted
to a permanent no-op in WP05 when status.migrate was deleted. The event log
is the sole authority; bootstrapping events from frontmatter is no longer
needed.
"""

from __future__ import annotations

import pytest

from specify_cli.upgrade.migrations.m_2_0_0_historical_status_migration import (
    HistoricalStatusMigration,
)

pytestmark = pytest.mark.fast


def test_detect_always_false(tmp_path) -> None:
    """After WP05, detect() always returns False (migration superseded)."""
    # Create a feature with WPs to prove detect() ignores them
    tasks_dir = tmp_path / "kitty-specs" / "900-test" / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "WP01-test.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\n\n# WP01\n",
        encoding="utf-8",
    )

    migration = HistoricalStatusMigration()
    assert migration.detect(tmp_path) is False


def test_can_apply_always_true(tmp_path) -> None:
    """After WP05, can_apply() always returns True (migration is a no-op)."""
    migration = HistoricalStatusMigration()
    ok, msg = migration.can_apply(tmp_path)
    assert ok is True


def test_apply_is_noop(tmp_path) -> None:
    """After WP05, apply() returns success with no-op message and creates no files."""
    tasks_dir = tmp_path / "kitty-specs" / "910-test" / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "WP01-test.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test\nlane: done\n---\n\n# WP01\n",
        encoding="utf-8",
    )

    migration = HistoricalStatusMigration()
    result = migration.apply(tmp_path)

    assert result.success is True
    # No event log should have been created
    events_file = tmp_path / "kitty-specs" / "910-test" / "status.events.jsonl"
    assert not events_file.exists()


def test_migration_id() -> None:
    """Migration ID is preserved for registry idempotency."""
    migration = HistoricalStatusMigration()
    assert migration.migration_id == "2.0.0_historical_status_migration"


def test_target_version() -> None:
    migration = HistoricalStatusMigration()
    assert migration.target_version == "2.0.0"


def test_description_reflects_noop() -> None:
    """Description mentions no-op or event log authority."""
    migration = HistoricalStatusMigration()
    desc = migration.description.lower()
    assert "no-op" in desc or "sole authority" in desc or "removed" in desc


def test_registered_in_registry() -> None:
    from specify_cli.upgrade.registry import MigrationRegistry

    registered_ids = [m.migration_id for m in MigrationRegistry.get_all()]
    assert "2.0.0_historical_status_migration" in registered_ids
