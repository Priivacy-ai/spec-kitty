"""ATDD tests for the auto-discovered runtime-state backfill upgrade migration (WP02).

Maps US3.1-US3.3 (spec.md) / T008 (tasks/WP02-upgrade-migration.md). All tests
call ``detect()``/``can_apply()``/``apply()`` directly on a
``RuntimeStateBackfillMigration`` instance -- the established pattern in
``test_unify_charter_activation_migration.py`` -- so the ``target_version``
guard never interferes. Fixtures are synthetic ``tmp_path/kitty-specs/``
corpora built via the shared WP03 fixture builder; the live repository is
never mutated.

Every fault-injection test exercises the REAL library verify over a REAL
fixture event log -- no ``cutover_mission``/``verify_backfill`` is mocked to
force a pass, matching WP01's own non-vacuous test discipline.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.migration.backfill_runtime_state import backfill_runtime_state
from specify_cli.upgrade.migrations import auto_discover_migrations
from specify_cli.upgrade.migrations.m_zz_runtime_state_backfill import (
    RuntimeStateBackfillMigration,
)
from specify_cli.upgrade.registry import MigrationRegistry
from tests.unit.migration._backfill_fixture import build_mission, corrupt_seed_value

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_STATUS_PHASE = "status_phase"
_CHARTER_PROMOTE_ANSWERS_ID = "unify_charter_activation_promote_answers"
_CHARTER_FINALIZE_ID = "consolidate_charter_bundle_fold"
_THIS_MIGRATION_ID = "runtime_state_backfill"


def _status_phase(feature_dir: Path) -> object:
    return json.loads((feature_dir / "meta.json").read_text())[_STATUS_PHASE]


def _has_status_phase(feature_dir: Path) -> bool:
    return _STATUS_PHASE in json.loads((feature_dir / "meta.json").read_text())


def _inject_conflicting_seed(feature_dir: Path, *, slot_value: str = "EVIL-DIVERGENT") -> None:
    """Corrupt the canonical assignee seed payload under its deterministic ID."""
    corrupt_seed_value(
        feature_dir,
        field_name="assignee",
        slot_name="assignee",
        value=slot_value,
    )


def _build_clean_mission(tmp_path: Path, *, slug: str = "clean-mission") -> Path:
    """A mission with a WP that carries zero evictable legacy runtime state.

    Unlike ``build_mission`` (which always seeds shell_pid/agent/assignee/
    tracker_refs/review), this WP has no runtime frontmatter and no subtask
    checkbox rows at all -- the genuine "nothing to migrate" corpus shape
    (US3.2's second sub-case, distinct from "no kitty-specs/ at all").
    """
    feature_dir = tmp_path / "kitty-specs" / slug
    tasks = feature_dir / "tasks"
    tasks.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_id": f"01{slug.upper().replace('-', '')}", "mission_slug": slug}),
        encoding="utf-8",
    )
    (tasks / "WP01-clean.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Clean WP\nexecution_mode: code_change\n---\n\n# WP01\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n## WP01 Clean\n\nNo subtasks recorded yet.\n", encoding="utf-8"
    )
    return feature_dir


# ---------------------------------------------------------------------------
# US3.1 -- legacy corpus migrates: seed -> verify -> flip, for every mission
# ---------------------------------------------------------------------------


def test_apply_migrates_legacy_corpus_seeds_verifies_and_flips(tmp_path: Path) -> None:
    alpha = build_mission(tmp_path, slug="alpha")
    beta = build_mission(tmp_path, slug="beta")

    migration = RuntimeStateBackfillMigration()
    assert migration.detect(tmp_path) is True

    result = migration.apply(tmp_path)

    assert result.success is True
    assert result.errors == []
    assert result.changes_made  # non-empty: something was migrated
    for feature_dir in (alpha, beta):
        assert _status_phase(feature_dir) == "1"


def test_apply_reduced_snapshot_matches_old_reader_by_count_and_value(tmp_path: Path) -> None:
    """The migration reuses the WP01 fail-closed verify -- prove it actually ran."""
    from specify_cli.migration.backfill_runtime_state import verify_backfill

    feature_dir = build_mission(tmp_path, slug="alpha")
    migration = RuntimeStateBackfillMigration()

    result = migration.apply(tmp_path)

    assert result.success is True
    verify = verify_backfill(feature_dir)
    assert verify.ok is True
    assert verify.mismatches == ()


def test_can_apply_mirrors_detect_on_legacy_corpus(tmp_path: Path) -> None:
    build_mission(tmp_path, slug="alpha")
    migration = RuntimeStateBackfillMigration()

    ok, reason = migration.can_apply(tmp_path)

    assert ok is True
    assert reason == ""


# ---------------------------------------------------------------------------
# US3.2 -- fresh install / no-legacy-state no-op
# ---------------------------------------------------------------------------


def test_detect_false_and_apply_noop_when_no_kitty_specs(tmp_path: Path) -> None:
    migration = RuntimeStateBackfillMigration()

    assert migration.detect(tmp_path) is False
    ok, reason = migration.can_apply(tmp_path)
    assert ok is False
    assert reason

    result = migration.apply(tmp_path)

    assert result.success is True
    assert result.changes_made == []
    assert not (tmp_path / "kitty-specs").exists()


def test_detect_false_when_mission_has_no_legacy_state(tmp_path: Path) -> None:
    _build_clean_mission(tmp_path)
    migration = RuntimeStateBackfillMigration()

    assert migration.detect(tmp_path) is False


def test_apply_noop_with_zero_event_writes_when_no_legacy_state(tmp_path: Path) -> None:
    feature_dir = _build_clean_mission(tmp_path)
    migration = RuntimeStateBackfillMigration()

    result = migration.apply(tmp_path)

    assert result.success is True
    assert result.changes_made == []
    # NFR-002: nothing was seeded -- no event log ever created for this mission.
    assert not (feature_dir / "status.events.jsonl").exists()


# ---------------------------------------------------------------------------
# US3.3 -- one mission fails verify -> the whole step aborts, no partial flip
# ---------------------------------------------------------------------------


def test_apply_aborts_on_first_verify_failure_naming_mission_and_mismatch(
    tmp_path: Path,
) -> None:
    alpha = build_mission(tmp_path, slug="alpha")
    beta = build_mission(tmp_path, slug="beta")
    gamma = build_mission(tmp_path, slug="gamma")

    # Corrupt beta with a REAL divergent same-slot annotation (fault injection,
    # not a mock) so its verify is genuinely red.
    backfill_runtime_state(beta)
    _inject_conflicting_seed(beta)
    beta_meta_before = (beta / "meta.json").read_bytes()
    gamma_meta_before = (gamma / "meta.json").read_bytes()

    migration = RuntimeStateBackfillMigration()
    result = migration.apply(tmp_path)

    assert result.success is False
    assert len(result.errors) == 1
    (error,) = result.errors
    # Names the failing mission...
    assert "beta" in error
    # ...and the specific mismatch...
    assert "assignee" in error
    # ...and gives an actionable remediation command.
    assert "backfill-runtime-state" in error
    assert "--mission beta" in error
    assert "--dry-run" in error

    # alpha sorts before beta -- it passed and stays flipped (per-mission
    # atomicity, not a corpus-wide rollback, D-03).
    assert _status_phase(alpha) == "1"
    # beta failed verify -- the flip never ran; meta.json is byte-identical.
    assert (beta / "meta.json").read_bytes() == beta_meta_before
    assert not _has_status_phase(beta)
    # gamma sorts after beta -- the abort means it was never even visited.
    assert (gamma / "meta.json").read_bytes() == gamma_meta_before
    assert not _has_status_phase(gamma)


# ---------------------------------------------------------------------------
# INV-5 / C-003 -- no repo-root event file (#2815)
# ---------------------------------------------------------------------------


def test_apply_writes_no_repo_root_event_file(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path, slug="alpha")
    migration = RuntimeStateBackfillMigration()

    result = migration.apply(tmp_path)

    assert result.success is True
    assert not (tmp_path / "status.events.jsonl").exists()
    assert not (tmp_path / "kitty-specs" / "status.events.jsonl").exists()
    # The event log DOES land under the mission directory itself.
    assert (feature_dir / "status.events.jsonl").exists()


# ---------------------------------------------------------------------------
# Idempotency (NFR-002 / INV-4)
# ---------------------------------------------------------------------------


def test_apply_twice_is_a_clean_noop_second_time(tmp_path: Path) -> None:
    feature_dir = build_mission(tmp_path, slug="alpha")
    migration = RuntimeStateBackfillMigration()

    first = migration.apply(tmp_path)
    assert first.success is True
    assert first.changes_made

    events_after_first = (feature_dir / "status.events.jsonl").read_bytes()
    meta_after_first = (feature_dir / "meta.json").read_bytes()

    second = migration.apply(tmp_path)

    assert second.success is True
    assert second.changes_made == []
    assert (feature_dir / "status.events.jsonl").read_bytes() == events_after_first
    assert (feature_dir / "meta.json").read_bytes() == meta_after_first


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------


def test_apply_dry_run_writes_nothing_and_reports_would_migrate(tmp_path: Path) -> None:
    """dry_run=True threads through to cutover_mission and writes nothing.

    Note: on a genuinely never-seeded corpus, the dry-run seed phase computes
    the would-seed count without writing, so the fail-closed verify -- which
    always reads the REAL on-disk event log -- legitimately cannot confirm
    parity yet (WP01's own ``test_dry_run_writes_nothing`` documents the same:
    ``would_flip`` mirrors ``verify.ok``, which is False pre-write). A dry-run
    preview therefore reports the would-seed count without treating that
    not-yet-confirmed verify as a fail-closed abort (only a REAL write that
    still fails verify, i.e. a live run, is fail-closed -- US3.3 covers that).
    """
    feature_dir = build_mission(tmp_path, slug="alpha")
    events_before = (feature_dir / "status.events.jsonl").read_bytes()
    meta_before = (feature_dir / "meta.json").read_bytes()

    migration = RuntimeStateBackfillMigration()
    result = migration.apply(tmp_path, dry_run=True)

    assert result.success is True
    assert result.errors == []
    assert result.changes_made
    assert any("dry-run" in change for change in result.changes_made)
    assert (feature_dir / "status.events.jsonl").read_bytes() == events_before
    assert (feature_dir / "meta.json").read_bytes() == meta_before


def test_apply_dry_run_after_real_seed_is_a_clean_noop(tmp_path: Path) -> None:
    """Once a mission is ACTUALLY seeded, a dry-run confirms nothing new to seed."""
    feature_dir = build_mission(tmp_path, slug="alpha")
    backfill_runtime_state(feature_dir)  # real, live seed first
    events_before = (feature_dir / "status.events.jsonl").read_bytes()
    meta_before = (feature_dir / "meta.json").read_bytes()

    migration = RuntimeStateBackfillMigration()
    result = migration.apply(tmp_path, dry_run=True)

    assert result.success is True
    assert result.changes_made == []  # already seeded -- nothing new would be seeded
    assert (feature_dir / "status.events.jsonl").read_bytes() == events_before
    assert (feature_dir / "meta.json").read_bytes() == meta_before


# ---------------------------------------------------------------------------
# Auto-discovery + ordering (the self-verifying guard on the filename choice)
# ---------------------------------------------------------------------------


def test_migration_is_auto_discovered_and_sorts_after_charter_folds() -> None:
    """A full, from-scratch discovery walk (the real ``spec-kitty upgrade`` shape).

    ``MigrationRegistry.clear()`` before rediscovery is the established
    isolation idiom in this suite (see ``tests/upgrade/test_auto_discovery.py``).
    It matters here specifically: this test module imports
    ``RuntimeStateBackfillMigration`` directly at module scope (for the other
    tests in this file), which would otherwise pre-register it ahead of the
    alphabetical ``pkgutil`` walk and produce a false pass/fail on tie-break
    order that has nothing to do with the real filesystem-discovery order.
    """
    MigrationRegistry.clear()
    auto_discover_migrations()

    assert MigrationRegistry.get_by_id(_THIS_MIGRATION_ID) is not None

    all_ids = [m.migration_id for m in MigrationRegistry.get_all()]
    assert _THIS_MIGRATION_ID in all_ids
    assert _CHARTER_PROMOTE_ANSWERS_ID in all_ids
    assert _CHARTER_FINALIZE_ID in all_ids

    this_index = all_ids.index(_THIS_MIGRATION_ID)
    assert this_index > all_ids.index(_CHARTER_PROMOTE_ANSWERS_ID), (
        "runtime_state_backfill must sort AFTER m_unify_charter_activation "
        "(FR-010) -- an m_<digits>_* filename would lose this same-version tie"
    )
    assert this_index > all_ids.index(_CHARTER_FINALIZE_ID), (
        "runtime_state_backfill must sort AFTER "
        "m_unify_charter_activation_finalize (FR-010)"
    )


def test_target_version_ties_with_charter_folds_not_higher() -> None:
    """Regression guard: a target_version above 3.2.6 is silently skipped by
    ``get_applicable()`` and HARD-FAILs ``test_migration_chain_integrity.py``."""
    assert RuntimeStateBackfillMigration.target_version == "3.2.6"
