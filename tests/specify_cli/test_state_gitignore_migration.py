"""Tests for the m_2_0_9_state_gitignore migration."""

from pathlib import Path

import pytest

from specify_cli.state_contract import get_runtime_gitignore_entries
from specify_cli.upgrade.migrations.m_2_0_9_state_gitignore import (
    StateGitignoreMigration,
)


@pytest.fixture()
def migration():
    return StateGitignoreMigration()


def test_migration_adds_entries_to_empty_gitignore(tmp_path: Path, migration):
    """Migration adds all runtime entries to an empty .gitignore."""
    (tmp_path / ".gitignore").write_text("")
    result = migration.apply(tmp_path)

    assert result.success
    content = (tmp_path / ".gitignore").read_text()
    assert ".kittify/.dashboard" in content
    assert ".kittify/runtime/" in content
    assert ".kittify/merge-state.json" in content
    assert ".kittify/events/" in content
    assert ".kittify/dossiers/" in content


def test_migration_idempotent(tmp_path: Path, migration):
    """Applying migration twice produces the same .gitignore content."""
    (tmp_path / ".gitignore").write_text("")
    migration.apply(tmp_path)
    content_after_first = (tmp_path / ".gitignore").read_text()

    migration.apply(tmp_path)
    content_after_second = (tmp_path / ".gitignore").read_text()

    assert content_after_first == content_after_second


def test_migration_preserves_existing(tmp_path: Path, migration):
    """Migration preserves pre-existing .gitignore entries."""
    (tmp_path / ".gitignore").write_text("*.pyc\n__pycache__/\n")
    migration.apply(tmp_path)

    content = (tmp_path / ".gitignore").read_text()
    assert "*.pyc" in content
    assert "__pycache__/" in content
    assert ".kittify/runtime/" in content


def test_should_apply_false_when_complete(tmp_path: Path, migration):
    """detect() returns False when all entries are already present."""
    entries = get_runtime_gitignore_entries()
    (tmp_path / ".gitignore").write_text("\n".join(entries) + "\n")

    assert not migration.detect(tmp_path)


def test_should_apply_true_when_missing(tmp_path: Path, migration):
    """detect() returns True when entries are missing."""
    (tmp_path / ".gitignore").write_text("*.pyc\n")

    assert migration.detect(tmp_path)


def test_should_apply_true_when_no_gitignore(tmp_path: Path, migration):
    """detect() returns True when .gitignore doesn't exist."""
    assert migration.detect(tmp_path)


def test_dry_run_no_changes(tmp_path: Path, migration):
    """Dry run does not modify .gitignore."""
    (tmp_path / ".gitignore").write_text("")
    result = migration.apply(tmp_path, dry_run=True)

    assert result.success
    assert (tmp_path / ".gitignore").read_text() == ""


def test_migration_creates_gitignore_if_missing(tmp_path: Path, migration):
    """Migration creates .gitignore when it doesn't exist."""
    result = migration.apply(tmp_path)

    assert result.success
    assert (tmp_path / ".gitignore").exists()
    content = (tmp_path / ".gitignore").read_text()
    assert ".kittify/runtime/" in content


def test_can_apply(tmp_path: Path, migration):
    """can_apply returns True for valid project path."""
    can, reason = migration.can_apply(tmp_path)
    assert can
    assert reason == ""


def test_can_apply_missing_path(tmp_path: Path, migration):
    """can_apply returns False for non-existent path."""
    can, reason = migration.can_apply(tmp_path / "nonexistent")
    assert not can
    assert "does not exist" in reason
