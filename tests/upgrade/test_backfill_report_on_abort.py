"""ATDD tests for report-on-abort of the corpus backfill migration (WP05).

Maps FR-005 / NFR-003 / US2-AC1 (spec.md). The corpus cutover
(:class:`RuntimeStateBackfillMigration`) aborts the whole step on the first
mission whose fail-closed verify fails. Before WP05 that abort discarded the
per-mission results it had already accumulated (m_zz ``apply()`` at :284-286),
so the operator-facing :class:`MigrationResult` was SILENT about the missions
and files the non-atomic walk had already written to disk.

report-on-abort (research US2, the PRIMARY path — NOT a corpus rollback: the
per-mission "already-flipped missions stay flipped" design is intentional,
D-03) instead ENUMERATES every mission/file already persisted before the abort,
machine-readably, via the new ``MigrationResult.partial_writes`` channel.

Every test drives the REAL library verify over a REAL fixture event log — the
same non-vacuous fault-injection discipline as WP02's sibling suite
(``tests/specify_cli/upgrade/test_runtime_state_backfill_migration.py``); no
``cutover_mission``/``verify_backfill`` is mocked to force an outcome.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.migration.backfill_runtime_state import backfill_runtime_state
from specify_cli.upgrade.migrations.base import PartialWrite
from specify_cli.upgrade.migrations.m_zz_runtime_state_backfill import (
    RuntimeStateBackfillMigration,
)
from tests.unit.migration._backfill_fixture import build_mission, corrupt_seed_value

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_STATUS_EVENTS_FILENAME = "status.events.jsonl"
_META_FILENAME = "meta.json"


def _inject_conflicting_seed(feature_dir: Path) -> None:
    """Corrupt the canonical assignee seed payload under its deterministic ID."""
    corrupt_seed_value(
        feature_dir,
        field_name="assignee",
        slot_name="assignee",
        value="EVIL-DIVERGENT",
    )


def _has_status_phase(feature_dir: Path) -> bool:
    return "status_phase" in json.loads((feature_dir / _META_FILENAME).read_text())


def _missions_in(writes: list[PartialWrite]) -> set[str]:
    return {w.mission for w in writes}


def _paths_for(writes: list[PartialWrite], mission: str) -> set[str]:
    return {w.path for w in writes if w.mission == mission}


# ---------------------------------------------------------------------------
# FR-005 / US2-AC1 -- a non-atomic abort enumerates every mission/file written
# ---------------------------------------------------------------------------


def test_abort_enumerates_every_mission_file_already_written(tmp_path: Path) -> None:
    """The abort result lists the files persisted for missions BEFORE the failure.

    ``alpha`` sorts first: apply() seeds it and flips it (both
    ``status.events.jsonl`` and ``meta.json`` written this run). ``beta`` (sorted
    next) fails the fail-closed verify and triggers the whole-step abort. Before
    WP05 the accumulated result was discarded — the operator had no
    machine-readable account of alpha's on-disk residue. It must now be
    enumerated.
    """
    alpha = build_mission(tmp_path, slug="alpha")
    beta = build_mission(tmp_path, slug="beta")
    gamma = build_mission(tmp_path, slug="gamma")

    # Corrupt beta with a REAL divergent same-slot annotation (fault injection,
    # not a mock) so its verify is genuinely red on a live run.
    backfill_runtime_state(beta)
    _inject_conflicting_seed(beta)

    migration = RuntimeStateBackfillMigration()
    result = migration.apply(tmp_path)

    # The step aborted (unchanged WP02 contract).
    assert result.success is False
    assert len(result.errors) == 1
    assert "beta" in result.errors[0]

    # FR-005: the abort is no longer silent about the partial write.
    assert result.partial_writes, "abort discarded the partial-write account (the bug)"

    # alpha was fully written (seeded + flipped) BEFORE the abort -> both files.
    assert "alpha" in _missions_in(result.partial_writes)
    assert _paths_for(result.partial_writes, "alpha") == {
        str(alpha / _STATUS_EVENTS_FILENAME),
        str(alpha / _META_FILENAME),
    }

    # gamma sorts AFTER beta -- the abort means it was never visited, so nothing
    # was written for it and it must not appear in the account.
    assert "gamma" not in _missions_in(result.partial_writes)
    assert not _has_status_phase(gamma)

    # The account is machine-readable: every entry names a mission and a real,
    # on-disk path (not a prose blob).
    for write in result.partial_writes:
        assert isinstance(write, PartialWrite)
        assert write.mission
        assert Path(write.path).exists()


def test_abort_account_paths_are_derived_from_slug_and_project_path(tmp_path: Path) -> None:
    """Each enumerated path is ``<project>/kitty-specs/<slug>/<file>`` (FR-005).

    Pins the derivation contract: the migration reconstructs the two per-mission
    file paths from the mission slug and the project root, so the account stays
    truthful even though ``cutover_mission`` canonicalizes the write target
    internally.
    """
    alpha = build_mission(tmp_path, slug="alpha")
    beta = build_mission(tmp_path, slug="beta")
    backfill_runtime_state(beta)
    _inject_conflicting_seed(beta)

    result = migration_apply(tmp_path)

    kitty_specs = tmp_path / "kitty-specs"
    for write in result.partial_writes:
        assert Path(write.path).parent == kitty_specs / write.mission
    # alpha's event log path resolves exactly under its own mission directory.
    assert str(alpha / _STATUS_EVENTS_FILENAME) in _paths_for(result.partial_writes, "alpha")


def test_clean_run_reports_empty_partial_write_account(tmp_path: Path) -> None:
    """AC2: a successful (non-abort) run carries no partial-write account.

    The channel is abort-only bookkeeping — a clean corpus cutover reports its
    outcome through ``changes_made`` (truthful count), not ``partial_writes``.
    """
    build_mission(tmp_path, slug="alpha")
    build_mission(tmp_path, slug="beta")

    result = migration_apply(tmp_path)

    assert result.success is True
    assert result.partial_writes == []
    assert result.changes_made  # something was migrated (truthful count)


def migration_apply(project_path: Path):  # small helper to keep the tests terse
    return RuntimeStateBackfillMigration().apply(project_path)
