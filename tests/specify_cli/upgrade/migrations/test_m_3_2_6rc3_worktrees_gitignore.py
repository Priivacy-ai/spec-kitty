"""Regression tests for the ``.worktrees/`` gitignore backfill (#3689).

Every mission worktree is a full checkout under ``.worktrees/``, but only
the <0.13.1 migration ever excluded that root (via the local-only
``.git/info/exclude``), so projects initialised since then show
``?? .worktrees/`` forever and a stray ``git add -A`` stages entire nested
checkouts. Fresh ``init`` now emits the entry from the state contract;
this migration heals existing projects.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from kernel.clock import now_utc

from specify_cli.upgrade.metadata import ProjectMetadata
from specify_cli.upgrade.migrations import auto_discover_migrations
from specify_cli.upgrade.migrations.m_3_2_6rc3_worktrees_gitignore_backfill import (
    _WORKTREES_ENTRY,
    WorktreesGitignoreBackfillMigration,
)
from specify_cli.upgrade.registry import MigrationRegistry
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
    ProjectMetadata(version=version, initialized_at=now_utc()).save(project_root / ".kittify")


def _read_gitignore(project_root: Path) -> str:
    return project_root.joinpath(".gitignore").read_text(encoding="utf-8")


def test_apply_adds_entry(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)

    WorktreesGitignoreBackfillMigration().apply(tmp_path)

    assert _WORKTREES_ENTRY in _read_gitignore(tmp_path)


def test_detect_true_when_missing(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, ".kittify/logs/")  # unrelated entry only

    assert WorktreesGitignoreBackfillMigration().detect(tmp_path) is True


@pytest.mark.parametrize("existing", [".worktrees/", ".worktrees", "/.worktrees/"])
def test_detect_false_when_equivalent_form_present(tmp_path: Path, existing: str) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, existing)

    assert WorktreesGitignoreBackfillMigration().detect(tmp_path) is False


def test_apply_reports_added_entry(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, ".kittify/logs/")

    result = WorktreesGitignoreBackfillMigration().apply(tmp_path)

    assert result.changes_made == [f"Added gitignore entry: {_WORKTREES_ENTRY}"]


def test_dry_run_reports_without_mutating(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, ".kittify/logs/")

    result = WorktreesGitignoreBackfillMigration().apply(tmp_path, dry_run=True)

    assert result.success
    assert result.changes_made == [f"Would add {_WORKTREES_ENTRY} to .gitignore"]
    assert _WORKTREES_ENTRY not in _read_gitignore(tmp_path)


def test_apply_is_idempotent(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, ".kittify/logs/")

    first = WorktreesGitignoreBackfillMigration().apply(tmp_path)
    second = WorktreesGitignoreBackfillMigration().apply(tmp_path)

    assert first.success and second.success
    assert second.changes_made == ["gitignore entry already present"]
    assert _read_gitignore(tmp_path).count(_WORKTREES_ENTRY) == 1


def test_entry_actually_makes_git_ignore_a_worktree(tmp_path: Path) -> None:
    """End to end against real git: after the backfill, a worktree checkout
    under ``.worktrees/`` is invisible to ``git status`` (#3689's observable)."""
    _init_git_repo(tmp_path)

    WorktreesGitignoreBackfillMigration().apply(tmp_path)

    nested = tmp_path / ".worktrees" / "demo-mission-abc123"
    nested.mkdir(parents=True)
    (nested / "file.txt").write_text("x\n", encoding="utf-8")

    check = subprocess.run(
        ["git", "-C", str(tmp_path), "check-ignore", ".worktrees/demo-mission-abc123/file.txt"],
        check=False,
        capture_output=True,
    )
    assert check.returncode == 0, "expected .worktrees/ contents to be gitignored"

    porcelain = subprocess.run(
        ["git", "-C", str(tmp_path), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert ".worktrees" not in porcelain


def test_backfill_fires_on_already_current_3_2_6rc3_project(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_metadata(tmp_path, "3.2.6rc3")
    _write_gitignore(tmp_path, ".kittify/logs/")  # logs present, .worktrees/ absent

    MigrationRegistry.clear()
    auto_discover_migrations()
    result = MigrationRunner(tmp_path).upgrade("3.2.6rc3", include_worktrees=False)

    assert result.success
    assert WorktreesGitignoreBackfillMigration.migration_id in result.migrations_applied
    assert _WORKTREES_ENTRY in _read_gitignore(tmp_path)
