"""Characterization tests for the m_0_8_0_worktree_agents_symlink migration's
OSError -> shutil.copy2 fallback path.

These tests simulate the Windows symlink-permission failure on POSIX runners by
patching os.symlink via monkeypatch.setattr. Both the happy fallback case and the
dual-failure (copy2 also raises) case are covered so the fallback arm has regression
protection on every CI pass — not just on Windows runners.

Doctrine applied:
- function-over-form-testing: assertions are on the resulting file content and
  MigrationResult.changes_made / .errors / .success fields, never on call counts
  or internal state.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from specify_cli.upgrade.migrations.m_0_8_0_worktree_agents_symlink import (
    WorktreeAgentsSymlinkMigration,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def migration() -> WorktreeAgentsSymlinkMigration:
    """Return a fresh migration instance for each test."""
    return WorktreeAgentsSymlinkMigration()


@pytest.fixture
def repo_with_worktree(tmp_path: Path) -> tuple[Path, Path]:
    """Build a minimal repo layout with one worktree directory.

    Layout:
        <tmp_path>/
          .kittify/
            AGENTS.md      ← source file the migration reads
          .worktrees/
            test-worktree/ ← simulated worktree (no .kittify yet)

    Returns (repo_root, worktree_path).
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    kittify = repo_root / ".kittify"
    kittify.mkdir()

    # Use a sentinel string so a content mismatch is immediately visible
    agents_content = f"agents content for WP02 test {tmp_path.name}"
    (kittify / "AGENTS.md").write_text(agents_content, encoding="utf-8")

    worktrees_dir = repo_root / ".worktrees"
    worktrees_dir.mkdir()

    worktree = worktrees_dir / "test-worktree"
    worktree.mkdir()

    return repo_root, worktree


# ---------------------------------------------------------------------------
# T008 — Happy fallback: os.symlink raises -> shutil.copy2 succeeds
# ---------------------------------------------------------------------------


def test_migration_symlink_fallback_copies_file_when_symlink_raises(
    migration: WorktreeAgentsSymlinkMigration,
    repo_with_worktree: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When os.symlink raises OSError, the migration falls back to shutil.copy2.

    Observable outcomes asserted:
    - result.success is True
    - result.errors is empty
    - The worktree's .kittify/AGENTS.md exists as a regular file (not a symlink)
    - File content matches the source AGENTS.md
    - result.changes_made contains an entry with '(symlink failed)'
    """
    repo_root, worktree = repo_with_worktree

    # Arrange — patch os.symlink to simulate Windows symlink-permission failure
    def _raise_symlink(*args: object, **kwargs: object) -> None:
        raise OSError("not permitted")

    monkeypatch.setattr(os, "symlink", _raise_symlink)

    # Act
    result = migration.apply(repo_root)

    # Assert — result-level
    assert result.success is True
    assert result.errors == []

    # Assert — file-level (no symlink, real file, correct content)
    wt_agents = worktree / ".kittify" / "AGENTS.md"
    assert wt_agents.exists(), "AGENTS.md must exist in the worktree after copy fallback"
    assert wt_agents.is_symlink() is False, "AGENTS.md must be a regular file, not a symlink"

    source_content = (repo_root / ".kittify" / "AGENTS.md").read_text(encoding="utf-8")
    assert wt_agents.read_text(encoding="utf-8") == source_content

    # Assert — changes list carries the fallback marker
    assert any("(symlink failed)" in entry for entry in result.changes_made), (
        f"Expected '(symlink failed)' in changes_made; got: {result.changes_made}"
    )


# ---------------------------------------------------------------------------
# T009 — Dual failure: os.symlink raises AND shutil.copy2 also raises
# ---------------------------------------------------------------------------


def test_migration_dual_failure_records_error_when_copy2_also_raises(
    migration: WorktreeAgentsSymlinkMigration,
    repo_with_worktree: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When both os.symlink and shutil.copy2 raise OSError, the dual-failure
    is recorded in MigrationResult.errors and no AGENTS.md is created.

    Observable outcomes asserted:
    - result.success is False
    - result.errors contains an entry with 'copy also failed:'
    - The worktree's .kittify/AGENTS.md does NOT exist
    """
    repo_root, worktree = repo_with_worktree

    # Arrange — patch both os.symlink and shutil.copy2 to raise
    def _raise_symlink(*args: object, **kwargs: object) -> None:
        raise OSError("not permitted")

    def _raise_copy2(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "symlink", _raise_symlink)
    monkeypatch.setattr(shutil, "copy2", _raise_copy2)

    # Act
    result = migration.apply(repo_root)

    # Assert — result-level
    assert result.success is False
    assert any("copy also failed:" in entry for entry in result.errors), (
        f"Expected 'copy also failed:' in errors; got: {result.errors}"
    )

    # Assert — no AGENTS.md was created in the worktree
    wt_agents = worktree / ".kittify" / "AGENTS.md"
    assert not wt_agents.exists(), "AGENTS.md must NOT exist after dual failure"
