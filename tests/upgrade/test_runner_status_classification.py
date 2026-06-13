"""Scope: runner status classification unit tests — no real git or subprocesses."""

from __future__ import annotations

import pytest
import yaml
from datetime import datetime
from pathlib import Path

from specify_cli.migration.schema_version import REQUIRED_SCHEMA_VERSION
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
    worktree_metadata_path = worktree / ".kittify" / "metadata.yaml"
    assert worktree_metadata_path.exists()
    worktree_metadata = yaml.safe_load(worktree_metadata_path.read_text(encoding="utf-8"))
    assert worktree_metadata["spec_kitty"]["schema_version"] == REQUIRED_SCHEMA_VERSION


def test_worktree_upgrade_stamps_schema_version_after_metadata_save(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_path = _setup_project(tmp_path)
    worktree = project_path / ".worktrees" / "001-feature-lane-a"
    (worktree / ".kittify").mkdir(parents=True)
    ProjectMetadata(
        version="1.0.0",
        initialized_at=datetime.now(),
    ).save(worktree / ".kittify")

    runner = MigrationRunner(project_path)
    migration = _AppliedMigration()

    monkeypatch.setattr(runner.detector, "detect_version", lambda: "1.0.0")
    monkeypatch.setattr(
        "specify_cli.upgrade.runner.MigrationRegistry.get_applicable",
        lambda _from, _to, project_path=None: [migration],  # noqa: ARG005
    )

    result = runner.upgrade("9.9.9", include_worktrees=True)

    assert result.success is True
    main_metadata = yaml.safe_load(
        (project_path / ".kittify" / "metadata.yaml").read_text(encoding="utf-8")
    )
    worktree_metadata = yaml.safe_load(
        (worktree / ".kittify" / "metadata.yaml").read_text(encoding="utf-8")
    )
    assert main_metadata["spec_kitty"]["schema_version"] == REQUIRED_SCHEMA_VERSION
    assert worktree_metadata["spec_kitty"]["schema_version"] == REQUIRED_SCHEMA_VERSION


def test_no_migrations_stamps_existing_worktree_schema_version(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_path = _setup_project(tmp_path)
    ProjectMetadata(
        version="1.0.0",
        initialized_at=datetime.now(),
    ).save(project_path / ".kittify")
    worktree = project_path / ".worktrees" / "001-feature-lane-a"
    (worktree / ".kittify").mkdir(parents=True)
    ProjectMetadata(
        version="1.0.0",
        initialized_at=datetime.now(),
    ).save(worktree / ".kittify")

    runner = MigrationRunner(project_path)

    monkeypatch.setattr(runner.detector, "detect_version", lambda: "1.0.0")
    monkeypatch.setattr(
        "specify_cli.upgrade.runner.MigrationRegistry.get_applicable",
        lambda _from, _to, project_path=None: [],  # noqa: ARG005
    )

    result = runner.upgrade("1.0.0", include_worktrees=True)

    assert result.success is True
    main_metadata = yaml.safe_load(
        (project_path / ".kittify" / "metadata.yaml").read_text(encoding="utf-8")
    )
    worktree_metadata = yaml.safe_load(
        (worktree / ".kittify" / "metadata.yaml").read_text(encoding="utf-8")
    )
    assert main_metadata["spec_kitty"]["schema_version"] == REQUIRED_SCHEMA_VERSION
    assert worktree_metadata["spec_kitty"]["schema_version"] == REQUIRED_SCHEMA_VERSION


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


# ---------------------------------------------------------------------------
# Issue #1872: not-applicable ("skipped") migrations must be recorded once,
# not re-appended on every upgrade run over the same version range.
# ---------------------------------------------------------------------------


def test_record_migration_is_idempotent_for_identical_records() -> None:
    """Recording the same (id, result) twice is a no-op (issue #1872)."""
    metadata = ProjectMetadata(version="1.0.0", initialized_at=datetime.now())

    first = metadata.record_migration("9.9.9_not_needed", "skipped", "Not applicable")
    second = metadata.record_migration("9.9.9_not_needed", "skipped", "Not applicable")

    assert first is True
    assert second is False
    assert len([m for m in metadata.applied_migrations if m.id == "9.9.9_not_needed"]) == 1


def test_record_migration_appends_on_result_transition() -> None:
    """A genuine failed -> success transition still appends (issue #1872)."""
    metadata = ProjectMetadata(version="1.0.0", initialized_at=datetime.now())

    assert metadata.record_migration("10.0.0_x", "failed", "boom") is True
    assert metadata.record_migration("10.0.0_x", "success", "fixed") is True

    results = [m.result for m in metadata.applied_migrations if m.id == "10.0.0_x"]
    assert results == ["failed", "success"]
    assert metadata.has_migration("10.0.0_x") is True


def test_repeated_not_needed_upgrade_does_not_grow_applied_migrations(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Re-running an upgrade with a not-applicable migration records it once."""
    project_path = _setup_project(tmp_path)
    migration = _NotNeededMigration()

    def _run() -> None:
        runner = MigrationRunner(project_path)
        monkeypatch.setattr(runner.detector, "detect_version", lambda: "1.0.0")
        monkeypatch.setattr(
            "specify_cli.upgrade.runner.MigrationRegistry.get_applicable",
            lambda _from, _to, project_path=None: [migration],  # noqa: ARG005
        )
        runner.upgrade("9.9.9", include_worktrees=False)

    _run()
    _run()

    metadata = ProjectMetadata.load(project_path / ".kittify")
    assert metadata is not None
    skipped = [m for m in metadata.applied_migrations if m.id == migration.migration_id]
    assert len(skipped) == 1
    assert skipped[0].result == "skipped"


def test_worktree_skipped_migration_keeps_last_upgraded_at_stable_on_rerun(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """A no-op skipped re-run must not bump the worktree's last_upgraded_at (issue #1872)."""
    project_path = _setup_project(tmp_path)
    worktree = project_path / ".worktrees" / "001-feature-lane-a"
    (worktree / ".kittify").mkdir(parents=True)
    ProjectMetadata(version="1.0.0", initialized_at=datetime.now()).save(worktree / ".kittify")
    migration = _NotNeededMigration()

    def _run() -> None:
        runner = MigrationRunner(project_path)
        monkeypatch.setattr(runner.detector, "detect_version", lambda: "1.0.0")
        monkeypatch.setattr(
            "specify_cli.upgrade.runner.MigrationRegistry.get_applicable",
            lambda _from, _to, project_path=None: [migration],  # noqa: ARG005
        )
        runner.upgrade("9.9.9", include_worktrees=True)

    _run()
    wt_kittify = worktree / ".kittify"
    after_first = ProjectMetadata.load(wt_kittify)
    assert after_first is not None
    stamp_first = after_first.last_upgraded_at

    _run()
    after_second = ProjectMetadata.load(wt_kittify)
    assert after_second is not None

    # Exactly one skipped record, and the timestamp did not move on the no-op re-run.
    skipped = [m for m in after_second.applied_migrations if m.id == migration.migration_id]
    assert len(skipped) == 1
    assert after_second.last_upgraded_at == stamp_first


# ---------------------------------------------------------------------------
# Issue #1871: compare-before-write at the metadata boundary. A no-op upgrade
# must not churn metadata.yaml (bytes/mtime) or advance last_upgraded_at.
# ---------------------------------------------------------------------------


def test_save_skips_write_when_only_timestamp_changes(tmp_path: Path) -> None:
    """save() is a no-op when only last_upgraded_at would change (issue #1871)."""
    kdir = tmp_path / ".kittify"
    kdir.mkdir()
    metadata = ProjectMetadata(version="1.0.0", initialized_at=datetime(2026, 1, 1))

    assert metadata.save(kdir) is True  # first write
    path = kdir / "metadata.yaml"
    before = path.read_bytes()

    # Only the volatile timestamp differs → masked-equal → skip the write.
    metadata.last_upgraded_at = datetime(2026, 6, 13, 12, 0, 0)
    assert metadata.save(kdir) is False
    assert path.read_bytes() == before

    # A material change (version) is written.
    metadata.version = "2.0.0"
    assert metadata.save(kdir) is True
    assert path.read_bytes() != before


def test_root_upgrade_no_op_keeps_metadata_stable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Re-running a no-op upgrade does not rewrite root metadata.yaml (issue #1871)."""
    project_path = _setup_project(tmp_path)
    migration = _NotNeededMigration()

    def _run() -> None:
        runner = MigrationRunner(project_path)
        monkeypatch.setattr(runner.detector, "detect_version", lambda: "1.0.0")
        monkeypatch.setattr(
            "specify_cli.upgrade.runner.MigrationRegistry.get_applicable",
            lambda _from, _to, project_path=None: [migration],  # noqa: ARG005
        )
        runner.upgrade("9.9.9", include_worktrees=False)

    _run()
    path = project_path / ".kittify" / "metadata.yaml"
    after_first = path.read_bytes()
    meta_first = ProjectMetadata.load(project_path / ".kittify")
    assert meta_first is not None
    stamp_first = meta_first.last_upgraded_at

    _run()
    # Byte-identical: neither save() nor _stamp_schema_version rewrote it.
    assert path.read_bytes() == after_first
    meta_second = ProjectMetadata.load(project_path / ".kittify")
    assert meta_second is not None
    assert meta_second.last_upgraded_at == stamp_first
