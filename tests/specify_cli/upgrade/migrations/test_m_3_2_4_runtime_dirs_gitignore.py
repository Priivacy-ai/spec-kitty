"""Regression tests for the ``.kittify/migrations/`` + ``.kittify/logs/`` gitignore backfill (#2384).

Sibling to the #2369 derived-views backfill: these generated ``.kittify/``
subtrees (mission-state repair manifests/quarantine, orchestrator per-WP logs)
must be gitignored on already-initialised projects too, or they show up
untracked and fail ``spec-kitty accept``'s ``git_dirty`` check.
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from specify_cli.upgrade.migrations import auto_discover_migrations
from specify_cli.upgrade.migrations.m_3_2_4_runtime_dirs_gitignore_backfill import (
    RuntimeDirsGitignoreBackfillMigration,
    _RUNTIME_DIR_ENTRIES,
)
from specify_cli.upgrade.metadata import ProjectMetadata
from specify_cli.upgrade.runner import MigrationRunner

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _init_git_repo(project_root: Path) -> None:
    subprocess.run(["git", "-C", str(project_root), "init", "-q"], check=True)


def _write_gitignore(project_root: Path, *entries: str) -> None:
    project_root.joinpath(".gitignore").write_text(
        "# Added by Spec Kitty CLI (auto-managed)\n" + "\n".join(entries) + "\n",
        encoding="utf-8",
    )


def _write_metadata(project_root: Path, version: str) -> None:
    ProjectMetadata(version=version, initialized_at=datetime.now()).save(
        project_root / ".kittify"
    )


def _read_gitignore(project_root: Path) -> str:
    return project_root.joinpath(".gitignore").read_text(encoding="utf-8")


def test_apply_adds_both_entries(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)

    RuntimeDirsGitignoreBackfillMigration().apply(tmp_path)

    text = _read_gitignore(tmp_path)
    for entry in _RUNTIME_DIR_ENTRIES:
        assert entry in text


def test_detect_true_when_either_missing(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, ".kittify/migrations/")  # logs/ still missing

    assert RuntimeDirsGitignoreBackfillMigration().detect(tmp_path) is True


def test_detect_false_when_both_present(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, *_RUNTIME_DIR_ENTRIES)

    assert RuntimeDirsGitignoreBackfillMigration().detect(tmp_path) is False


def test_trailing_slash_variant_counts_as_present(tmp_path: Path) -> None:
    """A hand-added slash-less entry ignores the same dir — no duplicate added."""
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, ".kittify/migrations", ".kittify/logs")

    migration = RuntimeDirsGitignoreBackfillMigration()
    assert migration.detect(tmp_path) is False
    result = migration.apply(tmp_path)
    assert result.changes_made == ["gitignore entries already present"]
    text = _read_gitignore(tmp_path)
    assert text.count(".kittify/migrations") == 1
    assert text.count(".kittify/logs") == 1


def test_apply_reports_only_missing(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, ".kittify/migrations/")

    result = RuntimeDirsGitignoreBackfillMigration().apply(tmp_path)

    assert result.changes_made == ["Added gitignore entries: .kittify/logs/"]


def test_dry_run_reports_without_mutating(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, ".kittify/migrations/")

    result = RuntimeDirsGitignoreBackfillMigration().apply(tmp_path, dry_run=True)

    assert result.success
    assert result.changes_made == ["Would add .kittify/logs/ to .gitignore"]
    assert ".kittify/logs/" not in _read_gitignore(tmp_path)


def test_apply_is_idempotent(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, *_RUNTIME_DIR_ENTRIES)

    first = RuntimeDirsGitignoreBackfillMigration().apply(tmp_path)
    second = RuntimeDirsGitignoreBackfillMigration().apply(tmp_path)

    assert first.success
    assert second.success
    text = _read_gitignore(tmp_path)
    for entry in _RUNTIME_DIR_ENTRIES:
        assert text.count(entry) == 1


def test_backfill_fires_on_already_current_3_2_4_project(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_metadata(tmp_path, "3.2.4")
    _write_gitignore(tmp_path, ".kittify/derived/")  # derived present, new dirs absent

    auto_discover_migrations()
    result = MigrationRunner(tmp_path).upgrade("3.2.4", include_worktrees=False)

    assert result.success
    assert (
        RuntimeDirsGitignoreBackfillMigration.migration_id in result.migrations_applied
    )
    text = _read_gitignore(tmp_path)
    assert ".kittify/migrations/" in text
    assert ".kittify/logs/" in text
