"""Migration Robustness Tests."""
from __future__ import annotations

import multiprocessing
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from specify_cli.upgrade.metadata import ProjectMetadata
from specify_cli.upgrade.migrations.base import BaseMigration, MigrationResult
from specify_cli.upgrade.migrations.m_0_12_1_remove_kitty_specs_from_gitignore import (
    RemoveKittySpecsFromGitignoreMigration,
)
from specify_cli.upgrade.registry import MigrationRegistry
from specify_cli.upgrade.runner import MigrationRunner

# Get migrations directory path
MIGRATIONS_DIR = Path(__file__).parents[3] / "src" / "specify_cli" / "upgrade" / "migrations"

pytestmark = [pytest.mark.adversarial]

LOCK_FILENAME = ".upgrade.lock"
FLAKY_MARKER = ".kittify/.flaky-migration"


class LockingMigration(BaseMigration):
    migration_id = "0.0.1_locking_migration"
    description = "Test migration that uses a file lock"
    target_version = "0.0.1"

    def detect(self, project_path: Path) -> bool:
        return True

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        lock_path = project_path / LOCK_FILENAME
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False, "Upgrade lock already held"
        self._lock_fd = fd
        self._lock_path = lock_path
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        try:
            time.sleep(0.6)
            return MigrationResult(success=True, changes_made=["Lock acquired"])
        finally:
            lock_fd = getattr(self, "_lock_fd", None)
            lock_path = getattr(self, "_lock_path", None)
            if lock_fd is not None:
                os.close(lock_fd)
            if lock_path is not None:
                try:
                    lock_path.unlink()
                except OSError:
                    pass


class FlakyMigration(BaseMigration):
    migration_id = "0.0.2_flaky_migration"
    description = "Fails once, then succeeds"
    target_version = "0.0.2"

    def detect(self, project_path: Path) -> bool:
        return True

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        marker = project_path / FLAKY_MARKER
        if marker.exists():
            return MigrationResult(success=True, changes_made=["Recovered"])

        if not dry_run:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("failed", encoding="utf-8")

        return MigrationResult(success=False, errors=["Simulated migration failure"])


@pytest.fixture()
def registry_restore() -> Any:
    original = MigrationRegistry._migrations.copy()
    yield
    MigrationRegistry._migrations = original


@pytest.fixture()
def migration_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    kittify_dir = project / ".kittify"
    kittify_dir.mkdir(parents=True)
    metadata = ProjectMetadata(
        version="0.0.0",
        initialized_at=datetime.now(),
        python_version="3.11",
        platform="test",
        platform_version="test",
    )
    metadata.save(kittify_dir)
    return project


def _register_migrations(*migrations: type[BaseMigration]) -> None:
    MigrationRegistry.clear()
    for migration in migrations:
        MigrationRegistry.register(migration)


def _run_upgrade_concurrent(
    project_path: str,
    ready_queue: multiprocessing.Queue,
    go_event: multiprocessing.Event,
    result_queue: multiprocessing.Queue,
) -> None:
    _register_migrations(LockingMigration)
    ready_queue.put("ready")
    go_event.wait()
    runner = MigrationRunner(Path(project_path))
    result = runner.upgrade("0.0.1", include_worktrees=False, force=True)
    result_queue.put((result.success, result.errors))


class TestAtomicWrites:
    def test_metadata_save_interruption_leaves_partial_file(self, tmp_path: Path, monkeypatch):
        kittify_dir = tmp_path / ".kittify"
        kittify_dir.mkdir(parents=True)
        metadata = ProjectMetadata(
            version="0.0.0",
            initialized_at=datetime.now(),
            python_version="3.11",
            platform="test",
            platform_version="test",
        )
        metadata.save(kittify_dir)
        metadata_path = kittify_dir / "metadata.yaml"
        before = metadata_path.read_text(encoding="utf-8")

        import specify_cli.upgrade.metadata as metadata_module

        def _boom(*_args, **_kwargs):
            raise RuntimeError("simulated crash")

        monkeypatch.setattr(metadata_module.yaml, "dump", _boom)

        with pytest.raises(RuntimeError):
            metadata.save(kittify_dir)

        after = metadata_path.read_text(encoding="utf-8")
        assert after != before
        assert "Spec Kitty Project Metadata" in after
        assert "spec_kitty:" not in after


@pytest.mark.slow
class TestConcurrentMigration:
    def test_concurrent_upgrade_handled(self, migration_project: Path, registry_restore: Any):
        ctx = multiprocessing.get_context("spawn")
        ready_queue: multiprocessing.Queue = ctx.Queue()
        result_queue: multiprocessing.Queue = ctx.Queue()
        go_event = ctx.Event()

        processes = [
            ctx.Process(
                target=_run_upgrade_concurrent,
                args=(str(migration_project), ready_queue, go_event, result_queue),
            )
            for _ in range(2)
        ]

        for process in processes:
            process.start()

        for _ in range(2):
            ready_queue.get(timeout=10)

        go_event.set()

        results = [result_queue.get(timeout=20) for _ in range(2)]

        for process in processes:
            process.join(timeout=20)

        successes = [success for success, _errors in results]
        assert successes.count(True) == 1
        assert successes.count(False) == 1
        assert any(
            any("Cannot apply" in err or "Upgrade lock" in err for err in errors)
            for success, errors in results
            if not success
        )


class TestPartialMigrationRecovery:
    def test_failed_migration_can_retry(self, migration_project: Path, registry_restore: Any):
        _register_migrations(FlakyMigration)
        runner = MigrationRunner(migration_project)

        first = runner.upgrade("0.0.2", include_worktrees=False, force=True)
        assert not first.success

        second = runner.upgrade("0.0.2", include_worktrees=False, force=True)
        assert second.success

        metadata = ProjectMetadata.load(migration_project / ".kittify")
        assert metadata is not None
        assert metadata.has_migration(FlakyMigration.migration_id)


class TestPermissionErrors:
    def test_readonly_gitignore_clear_error(self, migration_project: Path) -> None:
        gitignore = migration_project / ".gitignore"
        gitignore.write_text("kitty-specs\n", encoding="utf-8")
        gitignore.chmod(0o444)

        try:
            migration = RemoveKittySpecsFromGitignoreMigration()
            result = migration.apply(migration_project)
            assert not result.success
            assert any("Failed to write .gitignore" in err for err in result.errors)
        finally:
            gitignore.chmod(0o644)


class TestMigrationRegistryCompleteness:
    """Verify all migration files are properly imported and registered.

    CRITICAL: This test prevents the 0.13.2 release blocker bug where
    migrations existed but weren't imported in __init__.py.
    """

    def test_all_migration_files_are_registered(self) -> None:
        """Verify every m_*.py file in migrations/ is imported and registered.

        This prevents silent bugs where migrations exist but never run during
        `spec-kitty upgrade` because they weren't imported in __init__.py.

        Bug prevented: 0.13.2 release blocker (4 migrations missing from registry)
        """
        # Find all migration files (m_*.py, excluding __init__.py)
        migration_files = sorted([
            f.stem for f in MIGRATIONS_DIR.glob("m_*.py")
            if f.stem != "__init__"
        ])

        # Get all registered migrations
        registered_migrations = MigrationRegistry.get_all()

        # The count must match - if files exist but aren't registered, they're not imported
        assert len(migration_files) == len(registered_migrations), (
            f"Migration registry incomplete!\n"
            f"Found {len(migration_files)} migration files in {MIGRATIONS_DIR}\n"
            f"but only {len(registered_migrations)} are registered.\n\n"
            f"Migration files ({len(migration_files)}):\n"
            + "\n".join(f"  - {f}" for f in migration_files)
            + f"\n\nRegistered migrations ({len(registered_migrations)}):\n"
            + "\n".join(f"  - {m.migration_id}" for m in registered_migrations)
            + "\n\nLikely cause: Missing imports in "
            "src/specify_cli/upgrade/migrations/__init__.py\n"
            "Add: from . import <migration_file_name>"
        )
