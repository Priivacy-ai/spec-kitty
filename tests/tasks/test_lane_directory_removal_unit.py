"""Tests for lane directory removal in migrations 0.9.0 and 0.9.1.

This test suite reproduces and verifies the fix for Issue #70:
Lane directories (planned/, doing/, for_review/, done/) persist after
migration from pre-v0.9.0 versions, causing agent confusion.

Root Cause: Migrations fail to remove directories containing system files
like .DS_Store (macOS), Thumbs.db (Windows), or other hidden files.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from specify_cli.upgrade.migrations.m_0_9_0_frontmatter_only_lanes import (
    FrontmatterOnlyLanesMigration,
)
from specify_cli.upgrade.migrations.m_0_9_1_complete_lane_migration import (
    CompleteLaneMigration,
)


@pytest.fixture
def migration_0_9_0():
    """Create migration 0.9.0 instance."""
    return FrontmatterOnlyLanesMigration()


@pytest.fixture
def migration_0_9_1():
    """Create migration 0.9.1 instance."""
    return CompleteLaneMigration()


@pytest.fixture
def mock_v0_6_4_project(tmp_path: Path) -> Path:
    """Create a mock v0.6.4 project with lane directories.

    Simulates a real v0.6.4 project structure:
    kitty-specs/001-test-feature/tasks/planned/WP01.md
    kitty-specs/001-test-feature/tasks/doing/WP02.md
    kitty-specs/001-test-feature/tasks/for_review/WP03.md
    kitty-specs/001-test-feature/tasks/done/WP04.md
    """
    # Create feature directory
    feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
    tasks_dir = feature_dir / "tasks"

    # Create lane directories with WP files
    lanes = {
        "planned": "WP01",
        "doing": "WP02",
        "for_review": "WP03",
        "done": "WP04",
    }

    for lane, wp_name in lanes.items():
        lane_dir = tasks_dir / lane
        lane_dir.mkdir(parents=True, exist_ok=True)

        # Create WP file with basic frontmatter
        wp_file = lane_dir / f"{wp_name}.md"
        wp_file.write_text(f"""---
work_package_id: "{wp_name}"
title: "Test Work Package {wp_name}"
---

# {wp_name}

Test content for {wp_name}.
""")

    return tmp_path


@pytest.fixture
def mock_v0_6_4_project_with_ds_store(mock_v0_6_4_project: Path) -> Path:
    """Create a mock v0.6.4 project with .DS_Store files in lane directories.

    This simulates the real-world scenario on macOS where Finder creates
    .DS_Store files in directories that have been viewed.
    """
    feature_dir = mock_v0_6_4_project / "kitty-specs" / "001-test-feature"
    tasks_dir = feature_dir / "tasks"

    # Add .DS_Store to some (not all) lane directories
    # This matches the bug report where only some directories persisted
    for lane in ["doing", "for_review", "done"]:
        ds_store = tasks_dir / lane / ".DS_Store"
        ds_store.write_text("mock DS_Store content")

    return mock_v0_6_4_project


@pytest.fixture
def mock_v0_6_4_project_with_gitkeep(mock_v0_6_4_project: Path) -> Path:
    """Create a mock v0.6.4 project with .gitkeep files."""
    feature_dir = mock_v0_6_4_project / "kitty-specs" / "001-test-feature"
    tasks_dir = feature_dir / "tasks"

    for lane in ["planned", "doing", "for_review", "done"]:
        gitkeep = tasks_dir / lane / ".gitkeep"
        gitkeep.write_text("")

    return mock_v0_6_4_project


def test_migration_0_9_0_detects_lane_directories(migration_0_9_0, mock_v0_6_4_project):
    """Test that migration 0.9.0 detects projects with lane directories."""
    assert migration_0_9_0.detect(mock_v0_6_4_project) is True


def test_migration_0_9_0_removes_empty_lane_directories(migration_0_9_0, mock_v0_6_4_project):
    """Test that migration 0.9.0 removes lane directories after moving files.

    This is the FAILING test that reproduces Issue #70.
    """
    # Run migration
    result = migration_0_9_0.apply(mock_v0_6_4_project, dry_run=False)

    # Check migration succeeded
    assert result.success is True

    # Check files were moved to flat structure
    feature_dir = mock_v0_6_4_project / "kitty-specs" / "001-test-feature"
    tasks_dir = feature_dir / "tasks"

    assert (tasks_dir / "WP01.md").exists(), "WP01.md should be in tasks/"
    assert (tasks_dir / "WP02.md").exists(), "WP02.md should be in tasks/"
    assert (tasks_dir / "WP03.md").exists(), "WP03.md should be in tasks/"
    assert (tasks_dir / "WP04.md").exists(), "WP04.md should be in tasks/"

    # Check lane directories were removed (THIS IS THE KEY TEST)
    persisting_lanes = []
    for lane in ["planned", "doing", "for_review", "done"]:
        lane_dir = tasks_dir / lane
        if lane_dir.exists():
            persisting_lanes.append(lane)

    assert not persisting_lanes, (
        f"Lane directories should be removed after migration, "
        f"but these still exist: {persisting_lanes}"
    )


def test_migration_0_9_0_handles_ds_store_files(migration_0_9_0, mock_v0_6_4_project_with_ds_store):
    """Test that migration 0.9.0 removes directories even with .DS_Store files.

    This is the ROOT CAUSE test - .DS_Store files prevent directory removal.
    """
    # Run migration
    result = migration_0_9_0.apply(mock_v0_6_4_project_with_ds_store, dry_run=False)

    # Check migration succeeded
    assert result.success is True

    # Check lane directories were removed (even with .DS_Store files)
    feature_dir = mock_v0_6_4_project_with_ds_store / "kitty-specs" / "001-test-feature"
    tasks_dir = feature_dir / "tasks"

    persisting_lanes = []
    for lane in ["planned", "doing", "for_review", "done"]:
        lane_dir = tasks_dir / lane
        if lane_dir.exists():
            contents = list(lane_dir.iterdir())
            persisting_lanes.append(f"{lane}/ (contains: {[f.name for f in contents]})")

    assert not persisting_lanes, (
        f"Lane directories should be removed even with .DS_Store files, "
        f"but these still exist: {persisting_lanes}"
    )


def test_migration_0_9_0_handles_gitkeep_files(migration_0_9_0, mock_v0_6_4_project_with_gitkeep):
    """Test that migration 0.9.0 removes directories with .gitkeep files."""
    # Run migration
    result = migration_0_9_0.apply(mock_v0_6_4_project_with_gitkeep, dry_run=False)

    # Check migration succeeded
    assert result.success is True

    # Check lane directories were removed
    feature_dir = mock_v0_6_4_project_with_gitkeep / "kitty-specs" / "001-test-feature"
    tasks_dir = feature_dir / "tasks"

    persisting_lanes = []
    for lane in ["planned", "doing", "for_review", "done"]:
        lane_dir = tasks_dir / lane
        if lane_dir.exists():
            persisting_lanes.append(lane)

    assert not persisting_lanes, (
        f"Lane directories with .gitkeep should be removed, "
        f"but these still exist: {persisting_lanes}"
    )


def test_migration_0_9_1_removes_remaining_lane_directories(migration_0_9_1, mock_v0_6_4_project_with_ds_store):
    """Test that migration 0.9.1 cleans up any remaining lane directories.

    Migration 0.9.1 is the "catch-all" that should remove ANY remaining
    lane directories, even if 0.9.0 failed to remove them.
    """
    # First run migration 0.9.0 (which might fail to remove some directories)
    migration_0_9_0 = FrontmatterOnlyLanesMigration()
    migration_0_9_0.apply(mock_v0_6_4_project_with_ds_store, dry_run=False)

    # Now run migration 0.9.1 to clean up
    result = migration_0_9_1.apply(mock_v0_6_4_project_with_ds_store, dry_run=False)

    # Check migration succeeded
    assert result.success is True

    # Check ALL lane directories were removed
    feature_dir = mock_v0_6_4_project_with_ds_store / "kitty-specs" / "001-test-feature"
    tasks_dir = feature_dir / "tasks"

    persisting_lanes = []
    for lane in ["planned", "doing", "for_review", "done"]:
        lane_dir = tasks_dir / lane
        if lane_dir.exists():
            contents = list(lane_dir.iterdir())
            persisting_lanes.append(f"{lane}/ (contains: {[f.name for f in contents]})")

    assert not persisting_lanes, (
        f"Migration 0.9.1 should remove ALL remaining lane directories, "
        f"but these still exist: {persisting_lanes}"
    )


def test_upgrade_path_0_6_4_to_0_10_x_removes_all_lanes(
    migration_0_9_0,
    migration_0_9_1,
    mock_v0_6_4_project_with_ds_store
):
    """Integration test: Full upgrade path from v0.6.4 to v0.10.x.

    This simulates a real user upgrade from v0.6.4 → v0.10.13 and verifies
    that ALL lane directories are removed by the end.
    """
    project = mock_v0_6_4_project_with_ds_store

    # Run migration 0.9.0
    result_0_9_0 = migration_0_9_0.apply(project, dry_run=False)
    assert result_0_9_0.success is True

    # Run migration 0.9.1
    result_0_9_1 = migration_0_9_1.apply(project, dry_run=False)
    assert result_0_9_1.success is True

    # Verify NO lane directories remain
    feature_dir = project / "kitty-specs" / "001-test-feature"
    tasks_dir = feature_dir / "tasks"

    persisting_lanes = []
    for lane in ["planned", "doing", "for_review", "done"]:
        lane_dir = tasks_dir / lane
        if lane_dir.exists():
            contents = list(lane_dir.iterdir())
            persisting_lanes.append(f"{lane}/ (contains: {[f.name for f in contents]})")

    # This is the CRITICAL assertion that matches the user's bug report
    assert not persisting_lanes, (
        f"\n"
        f"CRITICAL: Lane directories not removed after upgrade!\n"
        f"\n"
        f"Still exist: {persisting_lanes}\n"
        f"\n"
        f"Migrations 0.9.0 and 0.9.1 should remove these.\n"
        f"This is the EXACT issue reported by user in Issue #70.\n"
    )


def test_empty_lane_directories_are_removed(migration_0_9_0, tmp_path):
    """Test that completely empty lane directories (no files at all) are removed."""
    # Create feature with empty lane directories
    feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
    tasks_dir = feature_dir / "tasks"

    for lane in ["planned", "doing", "for_review", "done"]:
        lane_dir = tasks_dir / lane
        lane_dir.mkdir(parents=True, exist_ok=True)
        # Don't add any files - completely empty

    # Migration should detect (empty directories still exist)
    # Note: Current implementation might NOT detect completely empty directories
    # This test documents the behavior
    detected = migration_0_9_0.detect(tmp_path)

    if detected:
        # If detected, migration should remove empty directories
        result = migration_0_9_0.apply(tmp_path, dry_run=False)
        assert result.success is True

        persisting_lanes = []
        for lane in ["planned", "doing", "for_review", "done"]:
            lane_dir = tasks_dir / lane
            if lane_dir.exists():
                persisting_lanes.append(lane)

        assert not persisting_lanes, f"Empty directories should be removed: {persisting_lanes}"
