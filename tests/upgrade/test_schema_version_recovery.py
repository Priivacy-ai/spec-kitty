"""#3334 red-first: a failed migration must PRESERVE ``schema_version``.

Scope: ``MigrationRunner.upgrade`` + ``ProjectMetadata.save`` schema-version
handling on the abort path (FR-002 / FR-012, US1 acceptance scenarios 3, 4, 6).

FR-002 is **preserve, not re-stamp-to-target**. ``_stamp_schema_version`` writes
the *target* schema (``REQUIRED_SCHEMA_VERSION``); a naive ``try/finally`` that
stamped it on the abort path would advance a FAILED/LEGACY project to the target
and open the gate on a half-backfilled corpus. The correct behaviour: capture the
pre-run on-disk ``schema_version`` before the migration loop and restore that
captured value on abort (and stop ``save()`` erasing it); stamp the target only on
success. Invariant proven here: **a failed migration NEVER advances
``schema_version``.**

The mid-loop abort is forced with a synthetic always-failing migration
(trigger-agnostic — it touches no duplicate-key artifact), so the P0 proof
isolates the save/stamp ordering defect and cannot be masked by FR-008 artifact
healing.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from kernel.clock import now_utc

from specify_cli.migration.schema_version import (
    REQUIRED_SCHEMA_VERSION,
    get_project_schema_version,
)
from specify_cli.upgrade import metadata as metadata_module
from specify_cli.upgrade.metadata import ProjectMetadata
from specify_cli.upgrade.migrations.base import BaseMigration, MigrationResult
from specify_cli.upgrade.runner import MigrationRunner

# Green regression-guard coverage for WP01's runner-surface abort-restore (the
# #3334 *erasure* class is owned by main's ProjectMetadata round-trip fix +
# tests). ``fast``/``unit`` route the nodes into fast-tests-upgrade
# (``tests/upgrade/ -m fast``). No ``@pytest.mark.regression``: these are green
# permanent tests, not a red-first open-P0 reproduction, so they do not belong
# in the ADR 2026-07-17-1 red-first regression home (``tests/regression/``).
pytestmark = [pytest.mark.fast, pytest.mark.unit]

_GET_APPLICABLE = "specify_cli.upgrade.runner.MigrationRegistry.get_applicable"


class _AlwaysFailingMigration(BaseMigration):
    """Synthetic, trigger-agnostic migration that always fails mid-loop."""

    migration_id = "99.0.0_synthetic_always_fail"
    description = "Synthetic always-failing migration for the #3334 red-first repro"
    target_version = "99.0.0"

    def detect(self, project_path: Path) -> bool:  # noqa: ARG002
        return True

    def can_apply(self, project_path: Path) -> tuple[bool, str]:  # noqa: ARG002
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:  # noqa: ARG002
        return MigrationResult(
            success=False,
            errors=["synthetic mid-loop abort (#3334 repro)"],
        )


class _SuccessMigration(BaseMigration):
    """Migration that applies cleanly once and is idempotent thereafter."""

    migration_id = "99.0.0_synthetic_success"
    description = "Synthetic succeeding migration for FR-012 resumable no-op"
    target_version = "99.0.0"

    def detect(self, project_path: Path) -> bool:  # noqa: ARG002
        return True

    def can_apply(self, project_path: Path) -> tuple[bool, str]:  # noqa: ARG002
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:  # noqa: ARG002
        return MigrationResult(success=True, changes_made=["cut over one mission"])


def _write_metadata(kittify_dir: Path, version: str, schema_version: int | None) -> None:
    """Write a ``metadata.yaml`` with an explicit (or absent) ``schema_version``.

    Written directly (not via the code under test) so the fixture cannot mask a
    save/stamp regression.
    """
    kittify_dir.mkdir(parents=True, exist_ok=True)
    spec_kitty: dict[str, object] = {
        "version": version,
        "initialized_at": now_utc().isoformat(),
    }
    if schema_version is not None:
        spec_kitty["schema_version"] = schema_version
    data = {"spec_kitty": spec_kitty, "environment": {}, "migrations": {"applied": []}}
    (kittify_dir / "metadata.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _run_failing_upgrade(monkeypatch: pytest.MonkeyPatch, project_path: Path) -> object:
    runner = MigrationRunner(project_path)
    monkeypatch.setattr(
        _GET_APPLICABLE,
        lambda _from, _to, project_path=None: [_AlwaysFailingMigration()],  # noqa: ARG005
    )
    return runner.upgrade("99.0.0", include_worktrees=False)


# ---------------------------------------------------------------------------
# US1 acceptance scenario 3 (NFR-001) — #3334 red-first: preserve schema_version.
# ---------------------------------------------------------------------------


def test_failed_migration_preserves_required_schema_version(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A mid-loop abort on a REQUIRED-schema project keeps schema_version intact.

    Red on the pre-fix tree (the in-loop failed-migration ``save()`` rewrites
    metadata.yaml without ``schema_version`` and the compensating stamp only
    runs on success), green after the preserve/restore fix.
    """
    project_path = tmp_path / "repo"
    _write_metadata(project_path / ".kittify", version="3.0.0", schema_version=REQUIRED_SCHEMA_VERSION)

    result = _run_failing_upgrade(monkeypatch, project_path)

    assert result.success is False
    assert get_project_schema_version(project_path) == REQUIRED_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# US1 acceptance scenario 4 — invariant: a failed migration NEVER advances.
# ---------------------------------------------------------------------------


def test_failed_migration_does_not_advance_legacy_schema(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A legacy project (no schema_version) is never advanced to the target."""
    project_path = tmp_path / "repo"
    _write_metadata(project_path / ".kittify", version="3.0.0", schema_version=None)

    result = _run_failing_upgrade(monkeypatch, project_path)

    assert result.success is False
    # Invariant: still legacy (None) — NOT stamped up to REQUIRED_SCHEMA_VERSION.
    assert get_project_schema_version(project_path) is None


def test_failed_migration_does_not_advance_below_required_schema(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A ``< REQUIRED`` project keeps its own schema; it is not advanced.

    Also red on the pre-fix tree: the pre-run value 2 is erased to ``None``.
    """
    below_required = REQUIRED_SCHEMA_VERSION - 1  # type: ignore[operator]
    project_path = tmp_path / "repo"
    _write_metadata(project_path / ".kittify", version="3.0.0", schema_version=below_required)

    result = _run_failing_upgrade(monkeypatch, project_path)

    assert result.success is False
    assert get_project_schema_version(project_path) == below_required
    assert get_project_schema_version(project_path) != REQUIRED_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# T002 unit (isolation): the runner's post-loop restore holds even when a
# save() caller erases schema_version — proving the guarantee is orchestration
# level, not merely a side effect of save() preservation.
# ---------------------------------------------------------------------------


def test_runner_restores_pre_run_schema_even_if_save_erases_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Runner restores the captured pre-run schema after an erasing save().

    We force ``ProjectMetadata.save`` to drop ``schema_version`` (simulating a
    lossy caller / the pre-fix save-rewrite) and assert the runner still lands
    the pre-run value on the abort path.
    """
    project_path = tmp_path / "repo"
    _write_metadata(project_path / ".kittify", version="3.0.0", schema_version=REQUIRED_SCHEMA_VERSION)

    def _erasing_save(self: ProjectMetadata, kittify_dir: Path) -> bool:
        data = {
            "spec_kitty": {
                "version": self.version,
                "initialized_at": self.initialized_at.isoformat(),
            },
            "migrations": {
                "applied": [
                    {"id": m.id, "applied_at": m.applied_at.isoformat(), "result": m.result, "notes": m.notes}
                    for m in self.applied_migrations
                ]
            },
        }
        (kittify_dir / "metadata.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        return True

    monkeypatch.setattr(metadata_module.ProjectMetadata, "save", _erasing_save)

    result = _run_failing_upgrade(monkeypatch, project_path)

    assert result.success is False
    assert get_project_schema_version(project_path) == REQUIRED_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Guard: a SUCCESSFUL upgrade still advances/stamps the target schema — the
# preserve-on-failure path must not leak into the success path.
# ---------------------------------------------------------------------------


def test_successful_upgrade_stamps_target_schema(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project_path = tmp_path / "repo"
    below_required = REQUIRED_SCHEMA_VERSION - 1  # type: ignore[operator]
    _write_metadata(project_path / ".kittify", version="3.0.0", schema_version=below_required)

    runner = MigrationRunner(project_path)
    monkeypatch.setattr(
        _GET_APPLICABLE,
        lambda _from, _to, project_path=None: [_SuccessMigration()],  # noqa: ARG005
    )
    result = runner.upgrade("99.0.0", include_worktrees=False)

    assert result.success is True
    assert get_project_schema_version(project_path) == REQUIRED_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# US1 acceptance scenario 6 (FR-012) — resumable no-op: a re-run after a
# completed upgrade applies ZERO migrations.
# ---------------------------------------------------------------------------


def test_rerun_after_successful_upgrade_applies_zero_migrations(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project_path = tmp_path / "repo"
    _write_metadata(project_path / ".kittify", version="3.0.0", schema_version=REQUIRED_SCHEMA_VERSION)
    migration = _SuccessMigration()

    def _run() -> object:
        runner = MigrationRunner(project_path)
        monkeypatch.setattr(
            _GET_APPLICABLE,
            lambda _from, _to, project_path=None: [migration],  # noqa: ARG005
        )
        return runner.upgrade("99.0.0", include_worktrees=False)

    first = _run()
    assert first.success is True
    assert first.migrations_applied == [migration.migration_id]

    second = _run()
    assert second.success is True
    # FR-012: safe no-op/resume — the already-applied migration is not re-run.
    assert second.migrations_applied == []
    assert second.migrations_skipped == [migration.migration_id]
    assert get_project_schema_version(project_path) == REQUIRED_SCHEMA_VERSION
