"""NFR-005 verification: recovery never breaks reducer determinism or append-only integrity.

Maps **NFR-005** / **US2-AC3** (spec.md) and the binding plan revision item 8
(``§Post-Plan Adversarial Revisions``): after a *half-applied* corpus backfill —
some missions cut over, then an abort on the first mission whose fail-closed
verify fails (WP05's report-on-abort path) — the recovered ``status.events.jsonl``
must satisfy two invariants:

1. **Reducer determinism (no divergence).** ``reduce()`` over the recovered log
   yields the *same* snapshot as ``reduce()`` over (pre-abort log ∪ committed
   cutover events), regardless of the order those two sets are presented in. The
   reducer sorts by ``(at, event_id)`` and de-dups on ``event_id`` (WP03
   :func:`~specify_cli.status.reducer.reduce`), so recovery ordering cannot move
   the snapshot — and a *duplicated* committed batch (what a crash-then-retry
   could leave) folds to the identical snapshot.
2. **Idempotent re-run appends no duplicate transitions.** After the partial
   backfill, ``detect()``/``_mission_needs_cutover`` skips the already-cut-over
   mission (it is at snapshot authority), and even the always-executed
   ``cutover_mission`` seed step is byte-idempotent — so a second migration run
   appends **zero** new rows to the recovered mission's log (the #3334
   regression assertion).

This suite composes shipped behaviour (WP01 schema-preserve + WP05
report-on-abort + WP03 reducer de-dup); it must PASS once both dependencies are
present. A failure here is a real event-log integrity gap, not a red-first stub.

Every test drives the REAL library backfill/cutover over a REAL fixture event
log with genuine fault injection (a divergent same-slot annotation) — no
``cutover_mission``/``verify_backfill`` is mocked to force an outcome, matching
WP05's non-vacuous discipline
(``tests/upgrade/test_backfill_report_on_abort.py``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from specify_cli.migration.backfill_runtime_state import backfill_runtime_state
from specify_cli.status.reducer import reduce
from specify_cli.status.store import (
    EventStream,
    read_event_stream,
    read_event_stream_from_text,
    read_events_raw,
)
from specify_cli.upgrade.migrations.m_zz_runtime_state_backfill import (
    RuntimeStateBackfillMigration,
    _mission_needs_cutover,
)
from tests.unit.migration._backfill_fixture import build_mission, corrupt_seed_value

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_STATUS_EVENTS_FILENAME = "status.events.jsonl"
_META_FILENAME = "meta.json"


def _inject_conflicting_seed(feature_dir: Path) -> None:
    """Corrupt the canonical assignee seed payload so *feature_dir*'s verify is red.

    A REAL divergent same-slot annotation (fault injection, not a mock), mirroring
    ``tests/upgrade/test_backfill_report_on_abort.py``: the live fail-closed verify
    genuinely reports a mismatch, which drives the whole-step abort.
    """
    corrupt_seed_value(
        feature_dir,
        field_name="assignee",
        slot_name="assignee",
        value="EVIL-DIVERGENT",
    )


def _has_status_phase(feature_dir: Path) -> bool:
    return "status_phase" in json.loads((feature_dir / _META_FILENAME).read_text())


def _snapshot_dict(stream: EventStream) -> dict[str, object]:
    """Reduce a stream to its deterministic snapshot dict (transitions + annotations)."""
    snapshot_dict: dict[str, object] = reduce(stream.transitions, stream.annotations).to_dict()
    return snapshot_dict


@dataclass(frozen=True)
class _HalfApplied:
    """The recovered state of a corpus backfill that aborted mid-walk.

    ``alpha`` was fully cut over (seeded + flipped) BEFORE the abort; ``beta``
    (sorted next) failed the fail-closed verify and aborted the whole step;
    ``gamma`` (sorted after) was never visited. ``alpha_pre_abort_text`` is
    alpha's on-disk event log captured BEFORE the migration ran — the "pre-abort
    log" half of the NFR-005 union.
    """

    alpha: Path
    beta: Path
    gamma: Path
    alpha_pre_abort_text: str


def _seed_half_applied_backfill(tmp_path: Path) -> _HalfApplied:
    """Build a half-applied backfill and return the recovered corpus handles.

    Reuses WP05's report-on-abort path: ``alpha`` cuts over, then ``beta``'s
    fault-injected divergent seed trips the fail-closed verify and aborts the
    walk, leaving the corpus half-applied (``gamma`` untouched).
    """
    alpha = build_mission(tmp_path, slug="alpha")
    beta = build_mission(tmp_path, slug="beta")
    gamma = build_mission(tmp_path, slug="gamma")

    # Capture alpha's pre-abort event log BEFORE any cutover writes to it.
    alpha_pre_abort_text = (alpha / _STATUS_EVENTS_FILENAME).read_text(encoding="utf-8")

    # Fault-inject beta with a REAL divergent same-slot annotation so its live
    # verify is genuinely red (drives the abort) — not a mocked outcome.
    backfill_runtime_state(beta)
    _inject_conflicting_seed(beta)

    result = RuntimeStateBackfillMigration().apply(tmp_path)

    # Sanity: the walk really was half-applied (WP05 contract).
    assert result.success is False, "fixture must abort mid-walk (beta verify red)"
    assert not _has_status_phase(gamma), "gamma sorts after beta -> never visited"
    assert _has_status_phase(alpha), "alpha sorts before beta -> cut over pre-abort"

    return _HalfApplied(
        alpha=alpha,
        beta=beta,
        gamma=gamma,
        alpha_pre_abort_text=alpha_pre_abort_text,
    )


# ---------------------------------------------------------------------------
# NFR-005 / US2-AC3 -- INVARIANT 1: reducer determinism after recovery
# ---------------------------------------------------------------------------


def test_reduce_over_recovered_log_equals_pre_abort_union_committed(tmp_path: Path) -> None:
    """AC1: ``reduce(recovered) == reduce(pre-abort ∪ committed)`` — no divergence.

    The recovered log is (by append-only construction) exactly
    ``pre-abort ∪ committed cutover events``. This test reconstructs that union
    INDEPENDENTLY (pre-abort captured before the run; committed = recovered minus
    pre-abort by ``event_id``) and reduces it in the OPPOSITE on-disk order
    (committed first, then pre-abort). Order-invariance of the snapshot is the
    proof that recovery ordering never moves the reduced state.
    """
    fixture = _seed_half_applied_backfill(tmp_path)

    # Append-only integrity: the cutover NEVER rewrote alpha's prior lines — the
    # recovered log begins with the byte-identical pre-abort prefix.
    recovered_text = (fixture.alpha / _STATUS_EVENTS_FILENAME).read_text(encoding="utf-8")
    assert recovered_text.startswith(fixture.alpha_pre_abort_text), (
        "recovery mutated pre-abort rows -> append-only integrity broken"
    )

    recovered = read_event_stream(fixture.alpha)
    recovered_snapshot = _snapshot_dict(recovered)

    # Independently split the union into its two halves.
    pre_abort = read_event_stream_from_text(fixture.alpha, fixture.alpha_pre_abort_text)
    pre_ids = {e.event_id for e in pre_abort.transitions} | {
        a.event_id for a in pre_abort.annotations
    }
    committed_transitions = [e for e in recovered.transitions if e.event_id not in pre_ids]
    committed_annotations = [a for a in recovered.annotations if a.event_id not in pre_ids]

    # Non-vacuous: the cutover genuinely committed events for alpha this run.
    assert committed_transitions or committed_annotations, (
        "fixture committed nothing for alpha -> the union invariant would be trivial"
    )

    # reduce(pre-abort ∪ committed), presented committed-first (the OPPOSITE of the
    # on-disk order) -> must match reduce(recovered).
    reordered_union = EventStream(
        transitions=committed_transitions + pre_abort.transitions,
        annotations=committed_annotations + pre_abort.annotations,
    )
    assert _snapshot_dict(reordered_union) == recovered_snapshot, (
        "reducer diverged when the recovered log was presented in a different order"
    )


def test_duplicated_committed_batch_folds_to_the_same_snapshot(tmp_path: Path) -> None:
    """AC1 (de-dup mechanism): a duplicated committed batch reduces identically.

    ``reduce()`` de-dups on ``event_id`` (WP03), so even if recovery re-appended
    the committed cutover events a second time (a crash-then-retry residue), the
    snapshot is unchanged — the exact append-only-integrity guarantee NFR-005
    names. This exercises the reducer's de-dup leg directly, complementing the
    detect()-gating leg proven below.
    """
    fixture = _seed_half_applied_backfill(tmp_path)

    recovered = read_event_stream(fixture.alpha)
    recovered_snapshot = _snapshot_dict(recovered)

    pre_abort = read_event_stream_from_text(fixture.alpha, fixture.alpha_pre_abort_text)
    pre_ids = {e.event_id for e in pre_abort.transitions} | {
        a.event_id for a in pre_abort.annotations
    }
    committed_transitions = [e for e in recovered.transitions if e.event_id not in pre_ids]
    committed_annotations = [a for a in recovered.annotations if a.event_id not in pre_ids]
    assert committed_transitions or committed_annotations

    duplicated = EventStream(
        transitions=recovered.transitions + committed_transitions,
        annotations=recovered.annotations + committed_annotations,
    )
    assert _snapshot_dict(duplicated) == recovered_snapshot, (
        "reducer failed to de-dup a duplicated committed batch on event_id"
    )


# ---------------------------------------------------------------------------
# NFR-005 / #3334 -- INVARIANT 2: idempotent re-run appends no duplicates
# ---------------------------------------------------------------------------


def test_rerun_after_partial_backfill_appends_no_duplicate_transitions(tmp_path: Path) -> None:
    """AC2: a second migration run appends NO new rows to the cut-over mission's log.

    Two cooperating mechanisms guarantee this: ``_mission_needs_cutover`` reports
    alpha as no-longer-needing cutover (it is at snapshot authority), and the
    always-executed ``cutover_mission`` seed step is byte-idempotent (deterministic
    seed ids already on disk). Together they mean the recovered mission's event log
    is byte-identical across the re-run — no duplicate transitions, ever.
    """
    fixture = _seed_half_applied_backfill(tmp_path)
    recovered_text = (fixture.alpha / _STATUS_EVENTS_FILENAME).read_text(encoding="utf-8")

    # detect()-gating: the cut-over mission is skipped; the still-corrupt one is not.
    assert _mission_needs_cutover(fixture.alpha) is False, (
        "already-cut-over mission must be skipped by the idempotency gate"
    )
    assert _mission_needs_cutover(fixture.beta) is True, (
        "the aborted (never-flipped) mission still needs cutover"
    )

    before_snapshot = _snapshot_dict(read_event_stream(fixture.alpha))

    # Re-run the whole migration. It walks alpha (a no-op cutover) then aborts on
    # beta again (still corrupt) -- deterministic.
    second_result = RuntimeStateBackfillMigration().apply(tmp_path)
    assert second_result.success is False, "beta is still corrupt -> the re-run still aborts"

    # No new rows appended for alpha: the on-disk log is byte-identical.
    assert (fixture.alpha / _STATUS_EVENTS_FILENAME).read_text(encoding="utf-8") == recovered_text, (
        "re-run appended rows to the already-cut-over mission's log"
    )

    # No event_id occurs twice in the recovered log (append-only, de-dup-safe).
    ids = [row["event_id"] for row in read_events_raw(fixture.alpha) if "event_id" in row]
    assert len(ids) == len(set(ids)), "re-run introduced duplicate event ids"

    # Reducer determinism across the re-run: the snapshot is unchanged.
    assert _snapshot_dict(read_event_stream(fixture.alpha)) == before_snapshot, (
        "the reduced snapshot changed across an idempotent re-run"
    )
