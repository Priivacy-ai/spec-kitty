"""Scope: runner status classification unit tests — no real git or subprocesses."""

from __future__ import annotations

import pytest
from datetime import datetime
from pathlib import Path

from specify_cli.upgrade.metadata import ProjectMetadata
from specify_cli.upgrade.migrations.base import BaseMigration, MigrationResult
from specify_cli.upgrade.runner import MigrationRunner

pytestmark = pytest.mark.fast


class _NotNeededMigration(BaseMigration):
    migration_id = "9.9.9_not_needed"
    description = "No-op migration for status classification tests"
    target_version = "9.9.9"

    def detect(self, project_path: Path) -> bool:  # noqa: ARG002
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:  # noqa: ARG002
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:  # noqa: ARG002
        raise AssertionError("apply() must not run when detect() is False")


class _AppliedMigration(BaseMigration):
    migration_id = "9.9.9_applied"
    description = "Applied migration for status classification tests"
    target_version = "9.9.9"

    def detect(self, project_path: Path) -> bool:  # noqa: ARG002
        return True

    def can_apply(self, project_path: Path) -> tuple[bool, str]:  # noqa: ARG002
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:  # noqa: ARG002
        return MigrationResult(success=True, changes_made=["updated file"])


class _FailingMigration(BaseMigration):
    migration_id = "10.0.0_failed"
    description = "Failing migration for metadata persistence tests"
    target_version = "10.0.0"

    def detect(self, project_path: Path) -> bool:  # noqa: ARG002
        return True

    def can_apply(self, project_path: Path) -> tuple[bool, str]:  # noqa: ARG002
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:  # noqa: ARG002
        return MigrationResult(success=False, errors=["boom"])


def _setup_project(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".kittify").mkdir()
    return repo


def test_not_needed_migration_is_reported_as_skipped(monkeypatch, tmp_path: Path) -> None:
    project_path = _setup_project(tmp_path)
    runner = MigrationRunner(project_path)
    migration = _NotNeededMigration()

    monkeypatch.setattr(runner.detector, "detect_version", lambda: "1.0.0")
    monkeypatch.setattr(
        "specify_cli.upgrade.runner.MigrationRegistry.get_applicable",
        lambda _from, _to, project_path=None: [migration],  # noqa: ARG005
    )

    result = runner.upgrade("9.9.9", include_worktrees=False)

    assert result.success is True
    assert result.migrations_applied == []
    assert result.migrations_skipped == [migration.migration_id]
    assert any("not needed" in warning for warning in result.warnings)


def test_already_applied_migration_is_reported_as_skipped(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_path = _setup_project(tmp_path)
    metadata = ProjectMetadata(
        version="1.0.0",
        initialized_at=datetime.now(),
    )
    metadata.record_migration(_AppliedMigration.migration_id, "success", "already applied")
    metadata.save(project_path / ".kittify")

    runner = MigrationRunner(project_path)
    migration = _AppliedMigration()

    monkeypatch.setattr(runner.detector, "detect_version", lambda: "1.0.0")
    monkeypatch.setattr(
        "specify_cli.upgrade.runner.MigrationRegistry.get_applicable",
        lambda _from, _to, project_path=None: [migration],  # noqa: ARG005
    )

    result = runner.upgrade("9.9.9", include_worktrees=False)

    assert result.success is True
    assert result.migrations_applied == []
    assert result.migrations_skipped == [migration.migration_id]
    assert any("already applied" in warning for warning in result.warnings)


def test_upgrade_creates_worktree_metadata_when_only_kitty_specs_exists(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Worktrees without .kittify should still be upgraded when they have kitty-specs."""
    project_path = _setup_project(tmp_path)
    worktree = project_path / ".worktrees" / "001-feature-lane-a"
    (worktree / "kitty-specs" / "001-feature" / "tasks").mkdir(parents=True)
    (worktree / "kitty-specs" / "001-feature" / "tasks" / "WP01-test.md").write_text(
        "---\nwork_package_id: WP01\nlane: planned\ndependencies: []\n---\n# WP01\n",
        encoding="utf-8",
    )

    runner = MigrationRunner(project_path)
    migration = _AppliedMigration()

    monkeypatch.setattr(runner.detector, "detect_version", lambda: "1.0.0")
    monkeypatch.setattr(
        "specify_cli.upgrade.runner.MigrationRegistry.get_applicable",
        lambda _from, _to, project_path=None: [migration],  # noqa: ARG005
    )

    result = runner.upgrade("9.9.9", include_worktrees=True)

    assert result.success is True
    assert (worktree / ".kittify" / "metadata.yaml").exists()


def test_upgrade_rejects_downgrade_target(monkeypatch, tmp_path: Path) -> None:
    project_path = _setup_project(tmp_path)
    runner = MigrationRunner(project_path)

    monkeypatch.setattr(runner.detector, "detect_version", lambda: "2.0.9")

    result = runner.upgrade("1.0.0", include_worktrees=False)

    assert result.success is False
    assert result.errors == ["Refusing to downgrade project metadata from 2.0.9 to 1.0.0"]


def test_upgrade_persists_successful_migrations_before_later_failure(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_path = _setup_project(tmp_path)
    runner = MigrationRunner(project_path)
    first = _AppliedMigration()
    second = _FailingMigration()

    monkeypatch.setattr(runner.detector, "detect_version", lambda: "1.0.0")
    monkeypatch.setattr(
        "specify_cli.upgrade.runner.MigrationRegistry.get_applicable",
        lambda _from, _to, project_path=None: [first, second],  # noqa: ARG005
    )

    result = runner.upgrade("10.0.0", include_worktrees=False)
    metadata = ProjectMetadata.load(project_path / ".kittify")

    assert result.success is False
    assert result.migrations_applied == [first.migration_id]
    assert result.errors == ["boom"]
    assert metadata is not None
    assert metadata.has_migration(first.migration_id)
    assert any(record.id == second.migration_id and record.result == "failed" for record in metadata.applied_migrations)
