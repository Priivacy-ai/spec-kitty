"""Focused unit tests for the pure purge core (WP06).

The purge subsystem's census differentials and verdict logic were relocated out
of ``cli/commands/sync.py`` into :mod:`specify_cli.sync.sync_purge_core` — the
**pure** half of the core/exec split (no ``Console``, no filesystem, no SQLite).
These tests exercise every relocated differential/verdict branch **directly**
with stub :class:`_RawCensus` inputs (Sonar new-code coverage; plan IC-04), so a
regression in the arithmetic is caught here rather than only through the golden
CLI harness.

The observable purge command behaviour itself stays frozen by the WP02 golden
and the ``tests/cli/commands/test_sync_purge_3030.py`` suite; this file guards
the extracted pure functions in isolation.
"""

from __future__ import annotations

import pytest

from specify_cli.sync.sync_purge_core import (
    _PURGE_BODY,
    _PURGE_FRAMES,
    _PURGE_JOURNAL,
    _PURGE_LEDGER,
    _PURGE_NULL_KEY,
    _PurgeStoreOutcome,
    _purge_differential,
    _purge_faults,
    _purge_frames_scope,
    _purge_ledger_differential,
    _purge_ledger_view,
    _purge_left_behind,
    _purge_not_reached,
    _purge_outcomes,
    _purge_selector_line,
    _purge_stored_spelling_conflicts,
    _purge_unattributable_keys,
    _RawCensus,
)

_UUID_A = "aaaaaaaa-1111-1111-1111-111111111111"
_UUID_B = "bbbbbbbb-2222-2222-2222-222222222222"


# --------------------------------------------------------------------------- #
# _RawCensus — the shared pure data shape
# --------------------------------------------------------------------------- #

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


def test_raw_census_count_sums_only_the_named_keys() -> None:
    census = _RawCensus(total=6, by_key={_UUID_A: 2, _UUID_B: 3, _PURGE_NULL_KEY: 1})
    assert census.count(frozenset({_UUID_A})) == 2
    assert census.count(frozenset({_UUID_A, _UUID_B})) == 5
    assert census.count(frozenset({"absent"})) == 0


def test_raw_census_unbucketed_reports_rows_the_grouping_missed() -> None:
    # total exceeds the sum of the buckets: two rows the grouping could not place.
    census = _RawCensus(total=5, by_key={_UUID_A: 3})
    assert census.unbucketed == 2
    # a total-preserving census has zero unbucketed rows.
    assert _RawCensus(total=3, by_key={_UUID_A: 3}).unbucketed == 0


def test_empty_census_is_inert() -> None:
    empty = _RawCensus()
    assert empty.total == 0
    assert empty.count(frozenset({_UUID_A})) == 0
    assert empty.unbucketed == 0
    assert _purge_unattributable_keys(empty) == frozenset()
    assert _purge_left_behind(empty) == {}


# --------------------------------------------------------------------------- #
# _purge_unattributable_keys / _purge_left_behind — residue accounting
# --------------------------------------------------------------------------- #


def test_unattributable_keys_names_null_blank_and_whitespace() -> None:
    census = _RawCensus(
        total=4,
        by_key={_UUID_A: 1, _PURGE_NULL_KEY: 1, "": 1, "   ": 1},
    )
    assert _purge_unattributable_keys(census) == frozenset({_PURGE_NULL_KEY, "", "   "})


def test_left_behind_splits_null_from_blank_counts() -> None:
    census = _RawCensus(
        total=6,
        by_key={_UUID_A: 2, _PURGE_NULL_KEY: 3, "": 1, "  ": 1},
    )
    # NULL rows are their own count; blank + whitespace-only fold into identity_blank.
    assert _purge_left_behind(census) == {"identity_null": 3, "identity_blank": 2}


def test_left_behind_omits_absent_populations() -> None:
    assert _purge_left_behind(_RawCensus(total=2, by_key={_UUID_A: 2})) == {}
    assert _purge_left_behind(_RawCensus(total=1, by_key={_PURGE_NULL_KEY: 1})) == {"identity_null": 1}


# --------------------------------------------------------------------------- #
# _purge_differential — measured removal + out-of-scope change
# --------------------------------------------------------------------------- #


def test_differential_measures_removed_in_scope_and_change_outside() -> None:
    before = _RawCensus(total=5, by_key={_UUID_A: 3, _UUID_B: 2})
    after = _RawCensus(total=2, by_key={_UUID_B: 2})
    removed, others = _purge_differential(before, after, frozenset({_UUID_A}))
    assert removed == 3
    assert others == 0


def test_differential_flags_out_of_scope_change_absolutely() -> None:
    before = _RawCensus(total=3, by_key={_UUID_A: 3})
    # a row for another project APPEARED during the run — an absolute change.
    after = _RawCensus(total=1, by_key={_UUID_B: 1})
    removed, others = _purge_differential(before, after, frozenset({_UUID_A}))
    assert removed == 3
    assert others == 1


def test_differential_disjoint_scope_removes_nothing() -> None:
    before = _RawCensus(total=2, by_key={_UUID_A: 2})
    after = _RawCensus(total=2, by_key={_UUID_A: 2})
    removed, others = _purge_differential(before, after, frozenset({"unrelated"}))
    assert removed == 0
    assert others == 0


# --------------------------------------------------------------------------- #
# _purge_ledger_differential — derived, not grouped
# --------------------------------------------------------------------------- #


def test_ledger_differential_derives_removed_and_outside_change() -> None:
    before = _RawCensus(total=10, by_key={_PURGE_LEDGER: 4})
    after = _RawCensus(total=6, by_key={_PURGE_LEDGER: 0})
    removed, changed_outside = _purge_ledger_differential(before, after)
    assert removed == 4
    # total fell by 4 and the selection accounts for all 4: nothing outside changed.
    assert changed_outside == 0


def test_ledger_differential_surfaces_untracked_total_change() -> None:
    before = _RawCensus(total=10, by_key={_PURGE_LEDGER: 4})
    after = _RawCensus(total=5, by_key={_PURGE_LEDGER: 0})
    removed, changed_outside = _purge_ledger_differential(before, after)
    assert removed == 4
    # total fell by 5 but only 4 were selected: one row outside the selection moved.
    assert changed_outside == 1


# --------------------------------------------------------------------------- #
# _purge_ledger_view — --all covers the whole table (incl. ghosts)
# --------------------------------------------------------------------------- #


def test_ledger_view_passthrough_when_not_all() -> None:
    census = _RawCensus(total=7, by_key={_PURGE_LEDGER: 3})
    assert _purge_ledger_view(census, all_events=False) is census


def test_ledger_view_all_selects_the_whole_table() -> None:
    census = _RawCensus(total=7, by_key={_PURGE_LEDGER: 3}, unreadable=False)
    viewed = _purge_ledger_view(census, all_events=True)
    assert viewed.by_key == {_PURGE_LEDGER: 7}
    assert viewed.total == 7


# --------------------------------------------------------------------------- #
# _purge_stored_spelling_conflicts — cross-store spelling hazard
# --------------------------------------------------------------------------- #


def test_stored_spelling_conflicts_flags_case_variant() -> None:
    census = _RawCensus(total=1, by_key={_UUID_A.upper(): 1})
    assert _purge_stored_spelling_conflicts(_UUID_A, [census]) == [_UUID_A.upper()]


def test_stored_spelling_conflicts_ignore_exact_null_and_blank() -> None:
    census = _RawCensus(total=3, by_key={_UUID_A: 1, _PURGE_NULL_KEY: 1, "  ": 1})
    assert _purge_stored_spelling_conflicts(_UUID_A, [census]) == []


# --------------------------------------------------------------------------- #
# _purge_frames_scope — the keys a run claims for the frame store
# --------------------------------------------------------------------------- #


class _FramesResult:
    def __init__(self, *, unattributed_in_scope: bool) -> None:
        self.unattributed_in_scope = unattributed_in_scope


def test_frames_scope_all_claims_every_key() -> None:
    census = _RawCensus(total=2, by_key={_UUID_A: 1, _PURGE_NULL_KEY: 1})
    assert _purge_frames_scope(census, None, all_events=True, selector_uuid=_UUID_A) == frozenset({_UUID_A, _PURGE_NULL_KEY})


def test_frames_scope_none_result_claims_nothing() -> None:
    census = _RawCensus(total=1, by_key={_UUID_A: 1})
    assert _purge_frames_scope(census, None, all_events=False, selector_uuid=_UUID_A) == frozenset()


def test_frames_scope_unattributed_in_scope_adds_residue() -> None:
    census = _RawCensus(total=2, by_key={_UUID_A: 1, _PURGE_NULL_KEY: 1})
    result = _FramesResult(unattributed_in_scope=True)
    assert _purge_frames_scope(census, result, all_events=False, selector_uuid=_UUID_A) == frozenset({_UUID_A, _PURGE_NULL_KEY})


def test_frames_scope_attributed_only_the_selector() -> None:
    census = _RawCensus(total=2, by_key={_UUID_A: 1, _PURGE_NULL_KEY: 1})
    result = _FramesResult(unattributed_in_scope=False)
    assert _purge_frames_scope(census, result, all_events=False, selector_uuid=_UUID_A) == frozenset({_UUID_A})


# --------------------------------------------------------------------------- #
# _purge_selector_line — the operator-facing selector description
# --------------------------------------------------------------------------- #


def test_selector_line_project_names_the_matched_slug() -> None:
    line = _purge_selector_line(project="acme", identity_less=False, selector_uuid=_UUID_A, matched_slug="acme/app")
    assert _UUID_A in line and "acme/app" in line


def test_selector_line_identity_less_and_all() -> None:
    assert "no project identity" in _purge_selector_line(project=None, identity_less=True, selector_uuid="", matched_slug=None)
    assert "every event" in _purge_selector_line(project=None, identity_less=False, selector_uuid="", matched_slug=None)


# --------------------------------------------------------------------------- #
# _purge_outcomes / _purge_not_reached / _purge_faults — verdict assembly
# --------------------------------------------------------------------------- #


def _store_map(value: _RawCensus) -> dict[str, _RawCensus]:
    return dict.fromkeys((_PURGE_JOURNAL, _PURGE_LEDGER, _PURGE_BODY, _PURGE_FRAMES), value)


def _clean_outcomes() -> dict[str, _PurgeStoreOutcome]:
    """A project purge that removed the one in-scope journal/body row cleanly."""
    before = {
        _PURGE_JOURNAL: _RawCensus(total=2, by_key={_UUID_A: 1, _UUID_B: 1}),
        _PURGE_LEDGER: _RawCensus(total=1, by_key={_PURGE_LEDGER: 1}),
        _PURGE_BODY: _RawCensus(total=1, by_key={_UUID_A: 1}),
        _PURGE_FRAMES: _RawCensus(),
    }
    after = {
        _PURGE_JOURNAL: _RawCensus(total=1, by_key={_UUID_B: 1}),
        _PURGE_LEDGER: _RawCensus(total=0, by_key={_PURGE_LEDGER: 0}),
        _PURGE_BODY: _RawCensus(),
        _PURGE_FRAMES: _RawCensus(),
    }
    scopes = {
        _PURGE_JOURNAL: frozenset({_UUID_A}),
        _PURGE_LEDGER: frozenset({_PURGE_LEDGER}),
        _PURGE_BODY: frozenset({_UUID_A}),
        _PURGE_FRAMES: frozenset(),
    }
    return _purge_outcomes(
        before=before,
        after=after,
        scopes=scopes,
        locations={s: f"loc-{s}" for s in scopes},
        reported={_PURGE_JOURNAL: 1, _PURGE_LEDGER: 1, _PURGE_BODY: 1, _PURGE_FRAMES: None},
        result=None,
        ghosts_before=0,
        identity_less=False,
        in_checkout=True,
        frames_census_reported=0,
    )


def test_outcomes_measures_removed_and_left_behind() -> None:
    outcomes = _clean_outcomes()
    assert outcomes[_PURGE_JOURNAL].removed_observed == 1
    assert outcomes[_PURGE_JOURNAL].in_scope == 1
    assert outcomes[_PURGE_LEDGER].removed_observed == 1
    assert outcomes[_PURGE_BODY].removed_observed == 1


def test_outcomes_identity_less_annotates_body_and_frames() -> None:
    before = _store_map(_RawCensus())
    after = _store_map(_RawCensus())
    scopes = {s: frozenset() for s in before}
    outcomes = _purge_outcomes(
        before=before,
        after=after,
        scopes=scopes,
        locations=dict.fromkeys(before, "loc"),
        reported=dict.fromkeys(before),
        result=None,
        ghosts_before=0,
        identity_less=True,
        in_checkout=True,
        frames_census_reported=0,
    )
    assert "only --all reaches them" in outcomes[_PURGE_BODY].note
    assert outcomes[_PURGE_FRAMES].note == outcomes[_PURGE_BODY].note


def test_outcomes_no_checkout_notes_the_frame_store() -> None:
    before = _store_map(_RawCensus())
    outcomes = _purge_outcomes(
        before=before,
        after=_store_map(_RawCensus()),
        scopes={s: frozenset() for s in before},
        locations=dict.fromkeys(before, "loc"),
        reported=dict.fromkeys(before),
        result=None,
        ghosts_before=0,
        identity_less=False,
        in_checkout=False,
        frames_census_reported=0,
    )
    assert "no checkout resolved" in outcomes[_PURGE_FRAMES].note


def test_faults_empty_when_dry_run_removed_nothing() -> None:
    before = _store_map(_RawCensus())
    outcomes = _purge_outcomes(
        before=before,
        after=_store_map(_RawCensus()),
        scopes={s: frozenset() for s in before},
        locations=dict.fromkeys(before, "loc"),
        reported=dict.fromkeys(before),
        result=None,
        ghosts_before=0,
        identity_less=False,
        in_checkout=True,
        frames_census_reported=0,
    )
    faults = _purge_faults(
        outcomes=outcomes,
        before=before,
        after=_store_map(_RawCensus()),
        apply=False,
        others_total=0,
        frames_census_reported=0,
        frames_census_disagrees=False,
    )
    assert faults == []


def test_faults_flag_census_disagreement_and_outside_change() -> None:
    before = {
        _PURGE_JOURNAL: _RawCensus(total=1, by_key={_UUID_A: 1}),
        _PURGE_LEDGER: _RawCensus(total=1, by_key={_PURGE_LEDGER: 1}),
        _PURGE_BODY: _RawCensus(),
        _PURGE_FRAMES: _RawCensus(total=3, by_key={_UUID_A: 3}),
    }
    outcomes = _purge_outcomes(
        before=before,
        after=before,
        scopes={s: frozenset() for s in before},
        locations=dict.fromkeys(before, "loc"),
        reported=dict.fromkeys(before),
        result=None,
        ghosts_before=0,
        identity_less=False,
        in_checkout=True,
        frames_census_reported=99,
    )
    faults = _purge_faults(
        outcomes=outcomes,
        before=before,
        after=before,
        apply=False,
        others_total=2,
        frames_census_reported=99,
        frames_census_disagrees=True,
    )
    joined = "\n".join(faults)
    assert "the purge's census reads 99" in joined
    assert "outside the selection changed" in joined


def test_faults_flag_apply_removed_mismatch() -> None:
    before = {
        _PURGE_JOURNAL: _RawCensus(total=2, by_key={_UUID_A: 2}),
        _PURGE_LEDGER: _RawCensus(total=0, by_key={_PURGE_LEDGER: 0}),
        _PURGE_BODY: _RawCensus(),
        _PURGE_FRAMES: _RawCensus(),
    }
    # apply run, one journal row in scope, but the store shows nothing removed.
    after = dict(before)
    scopes = {
        _PURGE_JOURNAL: frozenset({_UUID_A}),
        _PURGE_LEDGER: frozenset({_PURGE_LEDGER}),
        _PURGE_BODY: frozenset(),
        _PURGE_FRAMES: frozenset(),
    }
    outcomes = _purge_outcomes(
        before=before,
        after=after,
        scopes=scopes,
        locations=dict.fromkeys(before, "loc"),
        reported=dict.fromkeys(before),
        result=None,
        ghosts_before=0,
        identity_less=False,
        in_checkout=True,
        frames_census_reported=0,
    )
    faults = _purge_faults(
        outcomes=outcomes,
        before=before,
        after=after,
        apply=True,
        others_total=0,
        frames_census_reported=0,
        frames_census_disagrees=False,
    )
    assert any("expected 2 row(s) to go, measured 0" in fault for fault in faults)


def test_not_reached_names_null_and_ghost_populations() -> None:
    after = {
        _PURGE_JOURNAL: _RawCensus(total=2, by_key={_PURGE_NULL_KEY: 2}),
        _PURGE_LEDGER: _RawCensus(),
        _PURGE_BODY: _RawCensus(),
        _PURGE_FRAMES: _RawCensus(),
    }
    rows = _purge_not_reached(
        after=after,
        journal_scope=frozenset({_UUID_A}),
        frames_scope=frozenset(),
        body_scope=frozenset(),
        ghosts_before=4,
        all_events=False,
    )
    populations = {row["population"]: row["count"] for row in rows}
    assert populations["journal_identity_null"] == 2
    assert populations["ledger_without_journal_row"] == 4


def test_not_reached_all_events_lists_other_checkouts_without_a_count() -> None:
    rows = _purge_not_reached(
        after=_store_map(_RawCensus()),
        journal_scope=frozenset(),
        frames_scope=frozenset(),
        body_scope=frozenset(),
        ghosts_before=0,
        all_events=True,
    )
    other = [row for row in rows if row["population"] == "local_commit_frames_other_checkouts"]
    assert other and other[0]["count"] is None
