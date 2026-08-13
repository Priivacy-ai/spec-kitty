"""T012 — replacement for the #3334 red-first repro (canonical marks, guard
docstring). REPLACES ``tests/regression/test_issue_3334_failed_upgrade_wedges_repair.py``,
which pinned the wrong contract (that a missing ``schema_version`` combined
with 3.x ``migrations.applied`` history should not classify ``LEGACY`` — i.e.
it asked ``compat/planner.py`` to change, which C-004 forbids) and would have
stayed perma-red under this WP's actual (root-cause) fix.

Open P0: https://github.com/Priivacy-ai/spec-kitty/issues/3334

Root cause (verified live, see ``metadata.py``): ``ProjectMetadata.save()``
rebuilt ``metadata.yaml`` from a fixed dict that never included
``schema_version`` -- the field survived only via a separate,
success-path-gated ``_stamp_schema_version`` helper. A *failed* migration
still runs ``_record_migration_result`` -> ``metadata.save()`` to persist the
failure record, which silently stripped ``schema_version`` from disk. Because
``ProjectMetadata.has_migration()`` ignores ``"failed"`` records, re-running
``spec-kitty upgrade`` just re-attempts (and re-fails) the same migration
forever, so the schema stamp is never restored: a project with real 3.x
history gets permanently misclassified alongside a genuinely-never-migrated
pre-3.x project, and every non-exempt command is blocked (exit 4) with no way
back in.

Fix (#3334, C-008): ``ProjectMetadata`` round-trips ``schema_version`` like
any other field, so the failure-recording ``save()`` can no longer strip it.

Two starting fixtures, not one
-------------------------------
The WP's four required assertions do not all hold on a single fixture, and
this was verified empirically (not assumed) against the real
``compat.planner.decide()`` truth table:

* ``compat.planner.decide()`` Row 3 blocks **any** UNSAFE command
  (``"plan"`` included -- it is unregistered in the safety registry, so it
  fails closed to UNSAFE) whenever ``ProjectState`` is ``STALE`` *or*
  ``LEGACY``. Both states hit the exact same row. So a fixture whose
  ``schema_version`` is genuinely STALE (``< MIN_SUPPORTED_SCHEMA``, i.e.
  non-``REQUIRED``) will legitimately keep blocking ``"plan"`` after the
  fix too -- that block is *correct*, unrelated gate behaviour (a project
  that really is behind on schema really should not run a mutating command
  before migrating), not the #3334 wedge.
* The bug's *practical, realistic* shape is a project that was already at
  ``REQUIRED_SCHEMA_VERSION`` (``COMPATIBLE``) getting knocked down to
  ``LEGACY`` by an unrelated failed migration. That is exactly where "does
  the gate stop blocking after the fix" is a real, RED-before/GREEN-after
  question -- and it was confirmed RED against the pre-fix code before this
  test was written (metadata.py stashed, script rerun: pre-fix
  ``get_project_schema_version`` -> ``None`` and
  ``check_schema_version(root, "plan")`` -> ``SystemExit(4)``; post-fix ->
  ``3`` / no exit).

So: ``test_failed_migration_preserves_stale_schema_version`` pins the
load-bearing, non-fakeable *preservation* guarantee (assertion 1) against a
genuinely STALE, non-``REQUIRED`` value, and separately proves the STALE
project is blocked *no worse* than an equivalent project that never
experienced a failure (not further degraded into ``LEGACY``/``CORRUPT``).
``test_failed_migration_on_compatible_project_keeps_gate_passable`` pins the
literal "gate does not raise" guarantee (assertion 2) against the realistic
COMPATIBLE-starting-point scenario where it is actually RED before the fix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.migration.gate import check_schema_version
from specify_cli.migration.schema_version import (
    MIN_SUPPORTED_SCHEMA,
    REQUIRED_SCHEMA_VERSION,
    get_project_schema_version,
)
from specify_cli.upgrade.migrations.base import BaseMigration, MigrationResult
from specify_cli.upgrade.registry import MigrationRegistry
from specify_cli.upgrade.runner import MigrationRunner

pytestmark = [pytest.mark.integration]

# Genuinely STALE: below MIN_SUPPORTED_SCHEMA and NOT REQUIRED_SCHEMA_VERSION.
# A hardcoded `== 3` / `== REQUIRED_SCHEMA_VERSION` assertion would still pass
# even if a regression made the code always re-stamp REQUIRED regardless of
# what was actually on disk -- this pins genuine *preservation*, not a
# coincidental constant.
_STALE_SCHEMA_VERSION = MIN_SUPPORTED_SCHEMA - 1
assert _STALE_SCHEMA_VERSION != REQUIRED_SCHEMA_VERSION
assert _STALE_SCHEMA_VERSION >= 0

_FROM_VERSION = "3.2.0"
_TARGET_VERSION = "3.2.1"

_HISTORY_RECORD = (
    "  - id: m_3_0_0_canonical_context\n"
    "    applied_at: '2026-01-01T00:00:00+00:00'\n"
    "    result: success\n"
    "    notes: null\n"
)


def _write_metadata(kittify_dir: Path, *, schema_version: int) -> None:
    kittify_dir.mkdir(parents=True, exist_ok=True)
    (kittify_dir / "metadata.yaml").write_text(
        "spec_kitty:\n"
        f"  version: '{_FROM_VERSION}'\n"
        "  initialized_at: '2026-01-01T00:00:00+00:00'\n"
        "  last_upgraded_at: '2026-01-01T00:00:00+00:00'\n"
        f"  schema_version: {schema_version}\n"
        "environment:\n"
        "  python_version: '3.12'\n"
        "  platform: linux\n"
        "  platform_version: ''\n"
        "migrations:\n"
        "  applied:\n"
        f"{_HISTORY_RECORD}",
        encoding="utf-8",
    )


def _write_genuine_pre_3x_metadata(kittify_dir: Path) -> None:
    """A project that has NEVER been migrated: no schema_version key at all,
    and no 3.x migration history -- the negative control (assertion 4)."""
    kittify_dir.mkdir(parents=True, exist_ok=True)
    (kittify_dir / "metadata.yaml").write_text(
        "spec_kitty:\n"
        "  version: '0.9.0'\n"
        "  initialized_at: '2025-01-01T00:00:00+00:00'\n"
        "environment:\n"
        "  python_version: '3.10'\n"
        "  platform: linux\n"
        "  platform_version: ''\n"
        "migrations:\n"
        "  applied: []\n",
        encoding="utf-8",
    )


def _register_stub_failing_migration(migration_id: str) -> type[BaseMigration]:
    """Register (and return) a migration that always fails, following the
    injection pattern from ``tests/upgrade/test_upgrade_worktree_commit.py``
    (``_InvariantStubMigration``): ``MigrationRegistry.clear()`` then
    ``@MigrationRegistry.register`` a fresh ``BaseMigration`` subclass whose
    ``apply()`` returns ``MigrationResult(success=False, ...)``.

    Version window (the real trap, per the WP): ``MigrationRegistry.get_applicable``
    only selects a migration when ``from_v < target <= to_v``. The stub's
    ``target_version`` is deliberately set to ``_TARGET_VERSION`` (the same
    value ``upgrade()`` is called with below) so that
    ``Version(_FROM_VERSION) < Version(_TARGET_VERSION) <= Version(_TARGET_VERSION)``
    holds and the stub is actually selected and applied -- without this the
    failing migration never runs and the repro would be vacuous.
    """
    MigrationRegistry.clear()

    class _StubFailingMigration(BaseMigration):
        description = "Stub migration that always fails, for #3334 recoverability repro"
        target_version = _TARGET_VERSION

        def detect(self, project_path: Path) -> bool:  # noqa: ARG002
            return True

        def can_apply(self, project_path: Path) -> tuple[bool, str]:  # noqa: ARG002
            return True, ""

        def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:  # noqa: ARG002
            return MigrationResult(success=False, errors=["stub failure for #3334 repro"])

    _StubFailingMigration.migration_id = migration_id
    MigrationRegistry.register(_StubFailingMigration)
    return _StubFailingMigration


def test_failed_migration_preserves_stale_schema_version(tmp_path: Path) -> None:
    """Assertion (1): a real failed migration, driven through the real
    ``MigrationRunner.upgrade()``, must not strip a present-but-STALE
    ``schema_version`` -- it must come back out exactly as it went in.

    Also demonstrates the failure does not degrade the project any further
    than an equivalent STALE project that never experienced a failed
    migration at all (same gate outcome, same exit code): the STALE project
    stays exactly as recoverable as it always was, not worse.
    """
    project_root = tmp_path / "project"
    _write_metadata(project_root / ".kittify", schema_version=_STALE_SCHEMA_VERSION)

    control_root = tmp_path / "control"
    _write_metadata(control_root / ".kittify", schema_version=_STALE_SCHEMA_VERSION)
    # Control project is already at its target version -- no migration runs,
    # so it represents "STALE, never touched by a failure".
    (control_root / ".kittify" / "metadata.yaml").write_text(
        (control_root / ".kittify" / "metadata.yaml")
        .read_text(encoding="utf-8")
        .replace(_FROM_VERSION, _TARGET_VERSION),
        encoding="utf-8",
    )

    try:
        _register_stub_failing_migration("test_3334_stub_failing_stale")

        result = MigrationRunner(project_root).upgrade(
            _TARGET_VERSION, dry_run=False, include_worktrees=False
        )
        assert result.success is False, "the stub migration must have run and failed"

        # --- Non-fakeable assert (1): preserved at the STALE pre-value, not
        # silently re-stamped to REQUIRED/3 and not stripped to None. ---
        post_failure_schema_version = get_project_schema_version(project_root)
        assert post_failure_schema_version == _STALE_SCHEMA_VERSION
        assert post_failure_schema_version != REQUIRED_SCHEMA_VERSION

        # Equivalence: the post-failure project is blocked identically to a
        # STALE project that was never touched by a failure -- not degraded
        # into LEGACY/CORRUPT by the failed migration.
        with pytest.raises(SystemExit) as failed_exc:
            check_schema_version(project_root, "plan")
        with pytest.raises(SystemExit) as control_exc:
            check_schema_version(control_root, "plan")
        assert failed_exc.value.code == control_exc.value.code == 4
    finally:
        MigrationRegistry.clear()


def test_failed_migration_on_compatible_project_keeps_gate_passable(tmp_path: Path) -> None:
    """Assertion (2): a project already at REQUIRED_SCHEMA_VERSION that is
    hit by an unrelated failing migration must not be knocked down to
    LEGACY -- the real gate must not block a subsequent command.

    This is the realistic #3334 shape: most real projects that hit this bug
    were already fully migrated (schema_version == REQUIRED) and were struck
    by some later, unrelated migration failure. Verified RED against the
    pre-fix code (schema_version -> None, SystemExit(4)) before writing this
    test; GREEN after the fix (schema_version stays REQUIRED, no SystemExit).
    """
    project_root = tmp_path / "project"
    _write_metadata(project_root / ".kittify", schema_version=REQUIRED_SCHEMA_VERSION)

    try:
        _register_stub_failing_migration("test_3334_stub_failing_compatible")

        result = MigrationRunner(project_root).upgrade(
            _TARGET_VERSION, dry_run=False, include_worktrees=False
        )
        assert result.success is False, "the stub migration must have run and failed"

        assert get_project_schema_version(project_root) == REQUIRED_SCHEMA_VERSION

        # --- Non-fakeable assert (2): the real gate does not raise. ---
        check_schema_version(project_root, "plan")  # must not raise SystemExit
    finally:
        MigrationRegistry.clear()


def test_successful_migration_advances_schema_version_to_required(tmp_path: Path) -> None:
    """T010 (renata pin): a *successful* upgrade still advances
    ``schema_version`` to ``REQUIRED_SCHEMA_VERSION``, via the existing
    success-path ``_stamp_schema_version`` call in
    ``MigrationRunner.upgrade()`` (``runner.py:189-190``). The mask-entry
    drop and the ``save()`` round-trip change in this WP touch the exact
    save() path that stamp relies on staying consistent with, so this must
    not be left to accidental coverage from an unrelated suite-green run.

    See also ``tests/upgrade/test_runner_status_classification.py::
    test_worktree_upgrade_stamps_schema_version_after_metadata_save``, which
    pins the same invariant for both the main project and a worktree via a
    different (mocked ``get_applicable``) harness.
    """
    project_root = tmp_path / "project"
    _write_metadata(project_root / ".kittify", schema_version=_STALE_SCHEMA_VERSION)

    MigrationRegistry.clear()

    class _StubSucceedingMigration(BaseMigration):
        migration_id = "test_3334_stub_succeeding"
        description = "Stub migration that always succeeds"
        target_version = _TARGET_VERSION

        def detect(self, project_path: Path) -> bool:  # noqa: ARG002
            return True

        def can_apply(self, project_path: Path) -> tuple[bool, str]:  # noqa: ARG002
            return True, ""

        def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:  # noqa: ARG002
            return MigrationResult(success=True, changes_made=["stub applied"])

    try:
        MigrationRegistry.register(_StubSucceedingMigration)

        result = MigrationRunner(project_root).upgrade(
            _TARGET_VERSION, dry_run=False, include_worktrees=False
        )
        assert result.success is True, result.errors

        assert get_project_schema_version(project_root) == REQUIRED_SCHEMA_VERSION
    finally:
        MigrationRegistry.clear()


def test_dry_run_leaves_metadata_byte_identical(tmp_path: Path) -> None:
    """Assertion (3): dry_run against the failing migration writes nothing."""
    project_root = tmp_path / "project"
    _write_metadata(project_root / ".kittify", schema_version=_STALE_SCHEMA_VERSION)
    metadata_path = project_root / ".kittify" / "metadata.yaml"
    before = metadata_path.read_bytes()

    try:
        _register_stub_failing_migration("test_3334_stub_failing_dry_run")

        result = MigrationRunner(project_root).upgrade(
            _TARGET_VERSION, dry_run=True, include_worktrees=False
        )
        assert result.success is False

        after = metadata_path.read_bytes()
        assert after == before, "dry_run must not write metadata.yaml at all"
    finally:
        MigrationRegistry.clear()


def test_genuine_pre_3x_project_stays_legacy_blocked(tmp_path: Path) -> None:
    """Assertion (4) -- negative guard: a project that was NEVER migrated
    (no schema_version, no 3.x history) must still classify LEGACY and the
    real gate must still block with SystemExit(4). This fix must not weaken
    the gate for genuinely unmigrated projects (C-004)."""
    project_root = tmp_path / "project"
    _write_genuine_pre_3x_metadata(project_root / ".kittify")

    assert get_project_schema_version(project_root) is None

    with pytest.raises(SystemExit) as exc_info:
        check_schema_version(project_root, "plan")
    assert exc_info.value.code == 4
