"""T021/SC-004 + T020/NFR-007: operator visibility (#3030 WP07).

`sync doctor` read **healthy** throughout the 2026-07-27 incident. Its queue-health
block reads `OfflineQueue().get_queue_stats()`, which is empty after `sync migrate`,
so the operator saw "Queue size 0" while 9,133 events sat in the journal — 1,322 of
them belonging to projects that had never opted in. A fix the operator cannot verify
is not a fix, and a report rendered from the wrong store reproduces the same
false-green.

So the load-bearing assertion here is **reconciliation**: the per-project totals must
account for every retained journal row. A report that silently omits rows is the
incident's failure mode wearing a new table.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.delivery.status_report import build_per_project_store_report
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event

pytestmark = [pytest.mark.fast]

CONSENTED = "aaaaaaaa-0000-0000-0000-000000000001"
SILENT = "bbbbbbbb-0000-0000-0000-000000000002"
OPTED_OUT = "cccccccc-0000-0000-0000-000000000003"


@pytest.fixture(autouse=True)
def _home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    from specify_cli.sync.consent import set_project_consent

    set_project_consent(CONSENTED, True)
    set_project_consent(OPTED_OUT, False)
    # SILENT deliberately gets no record — absence, not refusal.


def _event(event_id: str, uuid: str | None, created_at: str) -> Event:
    return Event(
        event_id=event_id,
        event_type="WorkPackageApproved",
        payload=json.dumps({"event_id": event_id}).encode(),
        occurred_at=created_at,
        created_at=created_at,
        project_uuid=uuid,
    )


def _seeded_journal(tmp_path: Path) -> EventJournal:
    journal = EventJournal(tmp_path / "journal.db")
    for i in range(7):
        journal.append(_event(f"evt-ok-{i}", CONSENTED, f"2026-07-01T00:00:0{i}Z"))
    for i in range(4):
        journal.append(_event(f"evt-silent-{i}", SILENT, f"2026-06-01T00:00:0{i}Z"))
    for i in range(2):
        journal.append(_event(f"evt-out-{i}", OPTED_OUT, f"2026-06-15T00:00:0{i}Z"))
    journal.append(_event("evt-anon-0", None, "2026-05-01T00:00:00Z"))
    return journal


def test_sc004_report_names_every_project_with_count_age_and_consent(
    tmp_path: Path,
) -> None:
    report = _seeded_journal(tmp_path)
    result = build_per_project_store_report(report)

    by_uuid = {row.project_uuid: row for row in result.rows}
    assert set(by_uuid) == {CONSENTED, SILENT, OPTED_OUT, None}

    assert by_uuid[CONSENTED].event_count == 7
    assert by_uuid[CONSENTED].consent_granted is True
    assert by_uuid[CONSENTED].oldest_created_at == "2026-07-01T00:00:00Z"

    assert by_uuid[SILENT].event_count == 4
    assert by_uuid[SILENT].consent_granted is False, "absence of a record is not consent"

    assert by_uuid[OPTED_OUT].event_count == 2
    assert by_uuid[OPTED_OUT].consent_granted is False


def test_the_report_reconciles_against_the_journals_retained_count(
    tmp_path: Path,
) -> None:
    """FR-015's load-bearing property — no row may go uncounted.

    The incident's false-green was a report that rendered from a store holding
    nothing. A per-project table that omits rows is the same failure with a nicer
    layout, so reconciliation is asserted rather than assumed.
    """
    journal = _seeded_journal(tmp_path)

    result = build_per_project_store_report(journal)

    assert result.retained_event_count == 14
    assert result.counted_event_total == 14
    assert result.reconciles is True


def test_identity_less_rows_are_counted_not_dropped(tmp_path: Path) -> None:
    """FR-011: fail-closed denial must be observable, not silent data loss."""
    journal = _seeded_journal(tmp_path)

    result = build_per_project_store_report(journal)

    assert result.unresolved_identity_count == 1
    anon = next(row for row in result.rows if row.is_unresolved_identity)
    assert anon.event_count == 1
    assert anon.consent_granted is False
    assert "unselectable" in anon.consent_reason


def test_non_consenting_projects_are_flagged_for_the_operator(tmp_path: Path) -> None:
    journal = _seeded_journal(tmp_path)
    result = build_per_project_store_report(journal)

    flagged = {row.project_uuid for row in result.non_consenting_rows}
    assert flagged == {SILENT, OPTED_OUT, None}


def test_the_unresolved_identity_bucket_sorts_last(tmp_path: Path) -> None:
    """It must not hide at the top of a long table."""
    journal = _seeded_journal(tmp_path)
    result = build_per_project_store_report(journal)
    assert result.rows[-1].is_unresolved_identity


def test_report_distinguishes_which_consent_level_answered(tmp_path: Path) -> None:
    """Without this an operator cannot tell a project-local grant from a stale cache."""
    journal = _seeded_journal(tmp_path)
    result = build_per_project_store_report(journal)

    by_uuid = {row.project_uuid: row for row in result.rows}
    assert by_uuid[CONSENTED].consent_level == "machine_index"
    assert by_uuid[SILENT].consent_level == "absent"
    assert by_uuid[None].consent_level == "unresolved_identity"


def test_an_empty_journal_reconciles_trivially(tmp_path: Path) -> None:
    result = build_per_project_store_report(EventJournal(tmp_path / "empty.db"))
    assert result.rows == ()
    assert result.reconciles is True


# --- T020 / NFR-007: the report must not read the retired store --------------


def test_report_does_not_read_the_legacy_offline_queue(tmp_path: Path) -> None:
    """The incident's false-green, pinned.

    `OfflineQueue().get_queue_stats()` is empty after `sync migrate`. If the
    per-project report ever reads it, a contaminated store shows as healthy again.
    This asserts the report is built purely from the journal by proving it still
    reports correctly when the legacy queue is untouched and empty.
    """
    journal = _seeded_journal(tmp_path)

    from specify_cli.sync.queue import OfflineQueue

    legacy = OfflineQueue()
    assert legacy.size() == 0, "precondition: the legacy queue is empty"

    result = build_per_project_store_report(journal)

    assert result.retained_event_count == 14, (
        "the report must derive from the journal, not the retired queue — an "
        "empty legacy queue must never make a contaminated journal look healthy"
    )
    assert len(result.non_consenting_rows) == 3
