"""Owned unit test (WP04/T017, #2684): ``_check_unchecked_subtasks`` follows
the reduced-snapshot ``subtasks`` slot, not ``tasks.md`` bytes and not a
``HistoryAdded`` narrative record.

FR-003 / SC-003 (AC-3): the review gate's notion of "unchecked" must be
event-sourced, not markdown-gated. WP01 ships the reducer + snapshot +
``emit_inner_state_changed``; WP02 ships ``_guard_subtasks``'s own snapshot
re-source (behind the ``req.feature_dir`` seam); WP04 owns the OTHER half of
the wire: ``mark-status`` emits the completion delta (T015) and
``_check_unchecked_subtasks`` (``tasks_shared.py:412``, T016) re-sources
completion from that same reduced snapshot. This file is the owned,
NON-VACUOUS proof that T016's wiring actually reads the right mechanism.

**The crux (discriminating, not concordant)**: every fixture below makes
``tasks.md`` and the reduced snapshot *disagree*. A concordant fixture (both
sources say the same thing) would pass even if the reader silently reverted
to the legacy markdown byte — only a contradiction proves the snapshot is the
actual resolution source. Two directions are covered (mirror requirement):

* snapshot-complete / markdown-unchecked -> gate must return ``[]``
  (the log's completion is honored even though the checkbox is stale).
* snapshot-incomplete / markdown-checked -> gate must return the incomplete
  ids (a genuinely-incomplete WP is not waved through just because the
  checkbox was hand-edited or never evicted back).

A third test proves the gate never consults the ``HistoryAdded`` narrative
emission path (``specify_cli.sync.events.emit_history_added``, the mechanism
``_ms_emit_history`` fires) — a plausible-looking wrong implementation could
have keyed off "was a HistoryAdded note ever recorded for this task" instead
of the true ``subtasks`` slot; this pins that it does not.

The already-merged regression test
``tests/regression/test_issue_2684_subtask_completion_event_sourced.py`` is
the end-to-end companion proof (real CLI, real event log) — it is NOT owned
here and is not edited by this WP.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.cli.commands.agent.tasks_shared import _check_unchecked_subtasks
from specify_cli.status.models import InnerStateChanged, Lane, StatusEvent, WPInnerStateDelta
from specify_cli.status.store import append_annotations_atomic_verified, append_event

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_MISSION_SLUG = "check-unchecked-snapshot-source"

#: WP01's three canonical subtask rows — the authored roster (static design
#: intent, per T016 step 2: membership always comes from tasks.md).
_TASKS_MD_ALL_UNCHECKED = (
    "# Tasks\n\n## WP01 - repro\n"
    "- [ ] T001 alpha\n"
    "- [ ] T002 beta\n"
    "- [ ] T003 gamma\n"
)

_TASKS_MD_ALL_CHECKED = (
    "# Tasks\n\n## WP01 - repro\n"
    "- [x] T001 alpha\n"
    "- [x] T002 beta\n"
    "- [x] T003 gamma\n"
)


def _ulid(suffix: str) -> str:
    """Build a syntactically valid 26-char ULID from a short suffix."""
    return ("01KX" + suffix).ljust(26, "0")[:26]


def _seed_feature_dir(tmp_path: Path, tasks_md: str) -> Path:
    """Minimal primary-partition mission dir: ``kitty-specs/<slug>/tasks.md``.

    No ``meta.json`` is written by default — ``_phase1_dual_write_enabled``
    (``status/emit.py``) treats a missing/malformed ``meta.json`` as False,
    which is the default, PRE-CUTOVER state every mission starts in (legacy
    ``tasks.md`` remains the tolerated authority). Snapshot-sourced fixtures
    must explicitly opt in via :func:`_seed_phase1_flag` (mirrors
    ``tests/agent/cli/commands/test_tasks_helpers.py``'s
    ``_check_unchecked_subtasks`` fixtures — no coord/lanes.json complexity
    needed for a primary-partition read).
    """
    feature_dir = tmp_path / "kitty-specs" / _MISSION_SLUG
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks.md").write_text(tasks_md, encoding="utf-8")
    return feature_dir


def _seed_phase1_flag(feature_dir: Path) -> None:
    """Opt a fixture's mission into the phase-1 dual-write cutover.

    Matches the foundation convention (``status/emit.py::
    _phase1_dual_write_enabled`` / WP01's ``_infer_subtasks_complete`` / WP02's
    ``_snapshot_unchecked_subtasks``): flag ON -> snapshot-sourced completion,
    flag OFF (the default, no ``meta.json``) -> legacy ``tasks.md``.
    """
    (feature_dir / "meta.json").write_text(
        json.dumps({"status_phase": "1"}), encoding="utf-8"
    )


def _seed_claim_transition(feature_dir: Path, wp_id: str) -> None:
    """Seed a ``planned -> in_progress`` transition so the WP has a snapshot entry."""
    append_event(
        feature_dir,
        StatusEvent(
            event_id=_ulid("TRN" + wp_id),
            mission_slug=_MISSION_SLUG,
            wp_id=wp_id,
            from_lane=Lane.PLANNED,
            to_lane=Lane.IN_PROGRESS,
            at="2026-01-01T00:00:00+00:00",
            actor="test",
            force=True,
            execution_mode="worktree",
        ),
    )


def _seed_subtasks_annotation(feature_dir: Path, wp_id: str, subtasks: dict[str, Lane]) -> None:
    """Seed an ``InnerStateChanged`` ``subtasks`` delta — the T015 emit shape."""
    append_annotations_atomic_verified(
        feature_dir,
        [
            InnerStateChanged(
                event_id=_ulid("ANN" + wp_id),
                wp_id=wp_id,
                at="2026-01-01T00:01:00+00:00",
                actor="test",
                delta=WPInnerStateDelta(subtasks=subtasks),
            )
        ],
    )


def _check(tmp_path: Path, feature_dir: Path, wp_id: str) -> list[str]:
    with patch(
        "specify_cli.cli.commands.agent.tasks.get_main_repo_root", return_value=tmp_path
    ):
        # cast: the project's mypy config sets follow_imports="skip" for
        # specify_cli.* (see reducer.py's precedent comment), which makes this
        # cross-module call resolve as ``Any`` under isolated-file mypy runs
        # even though the real signature returns ``list[str]``. Type-only, no
        # behaviour change.
        result: list[str] = _check_unchecked_subtasks(tmp_path, _MISSION_SLUG, wp_id, False)
        return result


# ---------------------------------------------------------------------------
# The crux: discriminating (contradicting) fixtures, both directions.
# ---------------------------------------------------------------------------


def test_gate_follows_snapshot_complete_over_unchecked_markdown(tmp_path: Path) -> None:
    """Snapshot says DONE; tasks.md checkboxes are UNCHECKED — the gate must
    return ``[]`` (complete), honoring the log over the stale markdown byte.

    This is the exact #2684 eviction end-state: ``mark-status`` (T015) records
    completion in the log without flipping the checkbox; a reader that still
    trusted ``tasks.md`` would wrongly report all three subtasks incomplete.
    """
    feature_dir = _seed_feature_dir(tmp_path, _TASKS_MD_ALL_UNCHECKED)
    _seed_phase1_flag(feature_dir)  # flag ON -> snapshot-sourced completion
    _seed_claim_transition(feature_dir, "WP01")
    _seed_subtasks_annotation(
        feature_dir, "WP01", {"T001": Lane.DONE, "T002": Lane.DONE, "T003": Lane.DONE}
    )

    result = _check(tmp_path, feature_dir, "WP01")

    assert result == [], (
        "the gate must resolve completion from the reduced snapshot, not the "
        f"stale unchecked tasks.md bytes; got {result!r}"
    )


def test_gate_follows_snapshot_incomplete_over_checked_markdown(tmp_path: Path) -> None:
    """Mirror case: snapshot says one subtask is still incomplete while
    tasks.md shows every checkbox CHECKED — the gate must still refuse on the
    log's incomplete id, not wave it through because the markdown was
    hand-edited (or never evicted) to look done.
    """
    feature_dir = _seed_feature_dir(tmp_path, _TASKS_MD_ALL_CHECKED)
    _seed_phase1_flag(feature_dir)  # flag ON -> snapshot-sourced completion
    _seed_claim_transition(feature_dir, "WP01")
    _seed_subtasks_annotation(
        feature_dir, "WP01", {"T001": Lane.DONE, "T002": Lane.IN_PROGRESS, "T003": Lane.DONE}
    )

    result = _check(tmp_path, feature_dir, "WP01")

    assert result == ["T002"], (
        "the gate must resolve completion from the reduced snapshot (T002 is "
        f"NOT done there), not the fully-checked tasks.md bytes; got {result!r}"
    )


# ---------------------------------------------------------------------------
# The gate never consults the HistoryAdded narrative-emission path.
# ---------------------------------------------------------------------------


def test_gate_never_calls_history_added_emitter(tmp_path: Path) -> None:
    """``_ms_emit_history`` records a ``HistoryAdded`` narrative note via
    ``specify_cli.sync.events.emit_history_added`` — a render-only Activity-Log
    feed, structurally distinct from the ``subtasks`` authority slot. Pin that
    ``_check_unchecked_subtasks`` never calls it (a wrong implementation could
    plausibly key off "was a HistoryAdded note ever recorded" as a completion
    heuristic instead of reading the true snapshot slot)."""
    feature_dir = _seed_feature_dir(tmp_path, _TASKS_MD_ALL_UNCHECKED)
    _seed_phase1_flag(feature_dir)  # flag ON -> snapshot-sourced completion
    _seed_claim_transition(feature_dir, "WP01")
    _seed_subtasks_annotation(
        feature_dir, "WP01", {"T001": Lane.DONE, "T002": Lane.DONE, "T003": Lane.DONE}
    )

    with patch("specify_cli.sync.events.emit_history_added") as history_mock:
        result = _check(tmp_path, feature_dir, "WP01")

    history_mock.assert_not_called()
    assert result == []


# ---------------------------------------------------------------------------
# Companion sanity: the flag-gated legacy fallback (T016 step 3) still works
# for the transitional dual-write compat window, and for a WP the log has
# never touched (pre-backfill safety, avoiding a legacy-checked-WP regression).
# ---------------------------------------------------------------------------


def test_flag_off_uses_legacy_tasks_md_even_when_snapshot_contradicts(tmp_path: Path) -> None:
    """The default, PRE-CUTOVER state (no ``meta.json`` / flag OFF) keeps
    trusting ``tasks.md`` as the tolerated authority, even though the snapshot
    disagrees. Matches the WP01/WP02 convention: flag OFF -> legacy, since
    WP01 lands before WP03 flips/verifies the flag and the default must never
    read an empty/pre-backfill snapshot."""
    feature_dir = _seed_feature_dir(tmp_path, _TASKS_MD_ALL_CHECKED)
    # No _seed_phase1_flag(...) call: flag stays OFF (the default).
    _seed_claim_transition(feature_dir, "WP01")
    _seed_subtasks_annotation(feature_dir, "WP01", {"T001": Lane.IN_PROGRESS})

    result = _check(tmp_path, feature_dir, "WP01")

    # tasks.md is fully checked; the pre-cutover (flag OFF) default trusts it.
    assert result == []


def test_wp_never_touched_by_log_falls_back_to_legacy_markdown(tmp_path: Path) -> None:
    """Under the phase-1 cutover (flag ON), a WP the event log has never
    recorded a ``subtasks`` slot for (e.g. a pre-WP04 mission whose subtasks
    were checked the legacy way) must not be reported fully-incomplete just
    because the snapshot is silent — it falls back to the legacy
    ``tasks.md`` read (C-001 symmetric window; avoids a regression for
    untouched WPs; T016 edge case)."""
    feature_dir = _seed_feature_dir(tmp_path, _TASKS_MD_ALL_CHECKED)
    _seed_phase1_flag(feature_dir)  # flag ON -> exercises the snapshot path's fallback
    _seed_claim_transition(feature_dir, "WP01")
    # No subtasks annotation seeded at all: the snapshot has a WP01 entry
    # (from the claim transition) but no "subtasks" key.

    result = _check(tmp_path, feature_dir, "WP01")

    assert result == []  # tasks.md says fully checked; legacy fallback honors it


def test_no_events_at_all_falls_back_to_legacy_markdown(tmp_path: Path) -> None:
    """Under the phase-1 cutover (flag ON), an empty event log (no
    transitions, no annotations — pure pre-backfill) never crashes and
    tolerates the legacy ``tasks.md`` fallback."""
    feature_dir = _seed_feature_dir(tmp_path, _TASKS_MD_ALL_UNCHECKED)
    _seed_phase1_flag(feature_dir)  # flag ON -> exercises the empty-stream fallback

    result = _check(tmp_path, feature_dir, "WP01")

    assert result == ["T001", "T002", "T003"]
