"""ATDD unit tests for FR-002: cutover read/write partition decoupling.

Red-first proof (contract C-CUTOVER-1, WP01 T003/T004) for
``migration/runtime_state_cutover.py``'s ``cutover_mission``: the legacy
``tasks/`` frontmatter read must anchor on the **PRIMARY** leg (``feature_dir``),
while the seed-event **write** stays on the **COORD** leg (``status_dir``) and
the ``status_phase`` flip stays on **PRIMARY** — I-02.

Before the fix, ``_seed_phase``/``_verify_phase`` read ``tasks/`` from
``status_feature_dir`` (the COORD leg). Under coordination topology ``tasks/``
is COORD *residue* — possibly stale/absent there, since it is a
PRIMARY-partition artifact. A PRIMARY mission carrying genuine evictable
runtime state (``has_evictable_state() == True``) would silently seed
NOTHING (``seeded_count == 0``) while still flipping ``status_phase`` to
snapshot authority — a silent data-loss eviction. This file pins that the fix
closes it: the read now anchors on PRIMARY, so the genuine runtime IS seeded,
while the event log still lands on COORD (not PRIMARY — I-02 unchanged).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.migration import runtime_state_cutover as rsc
from specify_cli.migration.backfill_runtime_state import read_legacy_runtime
from tests.unit.migration._backfill_fixture import build_mission

pytestmark = [pytest.mark.fast]

_STATUS_PHASE = "status_phase"
_EVENTS_FILE = "status.events.jsonl"


def _build_stale_coord_leg(status_dir: Path) -> None:
    """Materialise an "absent/stale COORD tasks/" leg: an otherwise-empty dir.

    No ``tasks/`` directory at all — the exact shape the contract's red-first
    repro calls for ("absent/stale COORD ``tasks/``"). No pre-existing
    ``status.events.jsonl`` either, so :func:`~specify_cli.status.store.read_event_stream`
    degrades to an empty stream (no claim anchor from the event log — the
    anchor must synthesize from PRIMARY's own ``shell_pid_created_at``).

    Deliberately no ``meta.json`` is written here: ``meta.json`` is the
    PRIMARY_METADATA kind and lives on the PRIMARY leg only (see
    ``core/paths.py`` around ``resolve_target_branch`` — the coordination
    worktree's mission dir has no ``meta.json``, by construction of the
    partition split). Writing one onto the COORD leg would certify a corpus
    shape production never produces.
    """
    status_dir.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# T003 — red-first: PRIMARY evictable state + absent COORD tasks/
# ---------------------------------------------------------------------------


def test_evictable_primary_runtime_is_seeded_despite_absent_coord_tasks(tmp_path: Path) -> None:
    """PRIMARY carries genuine runtime; COORD ``tasks/`` is absent — no silent loss.

    Pins the no-loss invariant: ``seeded_count > 0`` AND the flip still
    succeeds (PRIMARY carried real evictable state that MUST be seeded before
    ``status_phase`` flips to snapshot authority).
    """
    primary_root = tmp_path / "primary"
    feature_dir = build_mission(primary_root, with_transitions=False)

    # Precondition (non-vacuity): PRIMARY genuinely carries evictable runtime
    # state — this is not a trivially-empty fixture.
    legacy = read_legacy_runtime(feature_dir)
    assert legacy["WP01"].has_evictable_state()

    status_dir = tmp_path / "coord-leg"
    _build_stale_coord_leg(status_dir)
    # The COORD leg carries NO tasks/ dir at all — "absent" COORD residue.
    assert not (status_dir / "tasks").is_dir()

    result = rsc.cutover_mission(feature_dir, status_feature_dir=status_dir)

    assert result.error is None
    assert result.seeded_count > 0, "PRIMARY evictable runtime must be seeded, not silently dropped"
    assert result.verify is not None and result.verify.ok
    assert result.flipped is True
    assert json.loads((feature_dir / "meta.json").read_text())[_STATUS_PHASE] == "1"


def test_seed_event_log_lands_on_coord_leg_not_primary(tmp_path: Path) -> None:
    """The seed-event write lands on COORD; PRIMARY's event log is untouched (I-02)."""
    primary_root = tmp_path / "primary"
    feature_dir = build_mission(primary_root, with_transitions=False)
    assert not (feature_dir / _EVENTS_FILE).exists()

    status_dir = tmp_path / "coord-leg"
    _build_stale_coord_leg(status_dir)

    result = rsc.cutover_mission(feature_dir, status_feature_dir=status_dir)

    assert result.seeded_count > 0
    # The event log was written on the COORD leg...
    coord_events_path = status_dir / _EVENTS_FILE
    assert coord_events_path.exists()
    coord_rows = [json.loads(line) for line in coord_events_path.read_text(encoding="utf-8").splitlines()]
    assert len(coord_rows) == result.seeded_count
    # ...and NEVER on PRIMARY (I-02: the write leg stays COORD).
    assert not (feature_dir / _EVENTS_FILE).exists()


def test_single_leg_caller_still_reads_and_writes_the_same_dir(tmp_path: Path) -> None:
    """Byte-unchanged single-leg behavior: no ``status_feature_dir`` => one dir.

    The three pre-existing single-leg callers (the corpus walk, the CLI
    backfill command, ``m_zz_runtime_state_backfill.py``) never pass
    ``status_feature_dir`` — this pins that ``cutover_mission`` collapses back
    to the single-dir shape those callers already exercise (NFR-002 byte-
    unchanged behavior), reading AND writing the very same directory.
    """
    feature_dir = build_mission(tmp_path)  # with_transitions default True

    result = rsc.cutover_mission(feature_dir)

    assert result.flipped is True
    assert result.error is None
    events_path = feature_dir / _EVENTS_FILE
    assert events_path.exists()
    assert json.loads((feature_dir / "meta.json").read_text())[_STATUS_PHASE] == "1"
