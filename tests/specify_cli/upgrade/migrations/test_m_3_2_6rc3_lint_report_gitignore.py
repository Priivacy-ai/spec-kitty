"""Regression tests for the ``.kittify/lint-report.json`` gitignore backfill (#3435).

``spec-kitty charter lint`` writes this report as a side effect of what is
advertised as a read-only diagnostic. On an already-initialised project
lacking the gitignore entry, the report shows up untracked and trips
``record-analysis``'s dirty-tree guard on a file the operator never
knowingly created.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from kernel.clock import now_utc

from specify_cli.upgrade.metadata import ProjectMetadata
from specify_cli.upgrade.migrations import auto_discover_migrations
from specify_cli.upgrade.migrations.m_3_2_6rc3_lint_report_gitignore_backfill import (
    LintReportGitignoreBackfillMigration,
    _LINT_REPORT_ENTRY,
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

    LintReportGitignoreBackfillMigration().apply(tmp_path)

    assert _LINT_REPORT_ENTRY in _read_gitignore(tmp_path)


def test_detect_true_when_missing(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, ".kittify/logs/")  # unrelated entry only

    assert LintReportGitignoreBackfillMigration().detect(tmp_path) is True


def test_detect_false_when_present(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, _LINT_REPORT_ENTRY)

    assert LintReportGitignoreBackfillMigration().detect(tmp_path) is False


def test_apply_reports_added_entry(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, ".kittify/logs/")

    result = LintReportGitignoreBackfillMigration().apply(tmp_path)

    assert result.changes_made == [f"Added gitignore entry: {_LINT_REPORT_ENTRY}"]


def test_dry_run_reports_without_mutating(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, ".kittify/logs/")

    result = LintReportGitignoreBackfillMigration().apply(tmp_path, dry_run=True)

    assert result.success
    assert result.changes_made == [f"Would add {_LINT_REPORT_ENTRY} to .gitignore"]
    assert _LINT_REPORT_ENTRY not in _read_gitignore(tmp_path)


def test_dry_run_reports_no_changes_when_already_present(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, _LINT_REPORT_ENTRY)

    result = LintReportGitignoreBackfillMigration().apply(tmp_path, dry_run=True)

    assert result.success
    assert result.changes_made == []


def test_apply_is_idempotent(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_gitignore(tmp_path, _LINT_REPORT_ENTRY)

    first = LintReportGitignoreBackfillMigration().apply(tmp_path)
    second = LintReportGitignoreBackfillMigration().apply(tmp_path)

    assert first.success
    assert second.success
    assert _read_gitignore(tmp_path).count(_LINT_REPORT_ENTRY) == 1


@pytest.mark.parametrize("dangling", [False, True])
def test_symlinked_gitignore_is_rejected_without_external_write(tmp_path: Path, dangling: bool) -> None:
    _init_git_repo(tmp_path)
    external = tmp_path.parent / f"lint-external-{tmp_path.name}.txt"
    external.unlink(missing_ok=True)
    if not dangling:
        external.write_text("outside\n", encoding="utf-8")
    tmp_path.joinpath(".gitignore").symlink_to(external)

    migration = LintReportGitignoreBackfillMigration()
    assert migration.detect(tmp_path) is True
    ok, reason = migration.can_apply(tmp_path)
    result = migration.apply(tmp_path)

    assert ok is False
    assert "symlink" in reason.lower()
    assert result.success is False
    if not dangling:
        assert external.read_text(encoding="utf-8") == "outside\n"
    else:
        assert not external.exists()


def test_backfill_fires_on_already_current_3_2_6rc3_project(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _write_metadata(tmp_path, "3.2.6rc3")
    _write_gitignore(tmp_path, ".kittify/logs/")  # logs present, lint-report absent

    MigrationRegistry.clear()
    auto_discover_migrations()
    result = MigrationRunner(tmp_path).upgrade("3.2.6rc3", include_worktrees=False)

    assert result.success
    assert LintReportGitignoreBackfillMigration.migration_id in result.migrations_applied
    assert _LINT_REPORT_ENTRY in _read_gitignore(tmp_path)
