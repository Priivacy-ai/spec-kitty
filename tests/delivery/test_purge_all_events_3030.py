"""FR-017/C-002: explicit total purge over one project-owned aggregate."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from specify_cli.delivery.ledger import LEDGER_TABLE, SqliteDeliveryLedger
from specify_cli.delivery.retention import (
    PURGE_ALL_CONFIRMATION,
    ProjectPurgeResult,
    PurgeNotConfirmedError,
    purge_all_events,
    purge_identity_less_events,
    purge_project_events,
)
from specify_cli.event_journal import Event, EventJournal
from specify_cli.sync.layout_generation import LayoutMode
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

AT = "2026-07-30T00:00:00+00:00"
PROJECT_UUID = "aaaaaaaa-0000-0000-0000-00000000000a"


def _event(event_id: str, *, archived: str | None = None) -> Event:
    return Event(
        event_id=event_id,
        event_type="WPStatusChanged",
        payload=b'{"payload":"confidential"}',
        occurred_at=AT,
        created_at=AT,
        project_uuid=PROJECT_UUID,
        archived_at=archived,
    )


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))


@pytest.fixture
def store() -> ProjectSyncStore:
    project_store = ProjectSyncStore(PROJECT_UUID)
    authority = project_store.layout_generation()
    if authority.read_state().mode is LayoutMode.LEGACY:
        authority.begin_cutover("purge-all-test")
        authority.publish_project_only("purge-all-test", verify_exact=lambda: True)
    with project_store.unit_of_work() as unit:
        journal = EventJournal(unit, authority)
        ledger = SqliteDeliveryLedger(unit, authority)
        for event in (
            _event("E-delivered"),
            _event("E-never"),
            _event("E-archived", archived=AT),
            _event("E-refused"),
        ):
            journal.append(event)
        ledger.record_success("E-delivered", "target-a")
        ledger.record_rejected("E-refused", "target-a", error="refused")
    return project_store


def _counts(store: ProjectSyncStore) -> tuple[int, int]:
    """Independent raw-SQL census of the per-project store's own tables."""
    connection = sqlite3.connect(str(store.database_path))
    try:
        journal = connection.execute("SELECT COUNT(*) FROM journal_entries").fetchone()
        ledger = connection.execute(f"SELECT COUNT(*) FROM {LEDGER_TABLE}").fetchone()  # noqa: S608
        return int(journal[0]), int(ledger[0])
    finally:
        connection.close()


def _purge(store: ProjectSyncStore, *, dry_run: bool = True, confirmation: str = "") -> ProjectPurgeResult:
    with store.unit_of_work() as unit:
        authority = store.layout_generation()
        return purge_all_events(
            journal=EventJournal(unit, authority),
            ledger=SqliteDeliveryLedger(unit, authority),
            dry_run=dry_run,
            confirmation=confirmation,
        )


def test_the_union_of_the_existing_selectors_is_not_total(store: ProjectSyncStore) -> None:
    """Historical node: project ownership makes the lawful selector total now."""
    with store.unit_of_work() as unit:
        authority = store.layout_generation()
        journal = EventJournal(unit, authority)
        ledger = SqliteDeliveryLedger(unit, authority)
        result = purge_project_events(PROJECT_UUID, journal=journal, ledger=ledger, dry_run=False)
        identityless = purge_identity_less_events(journal=journal, ledger=ledger, dry_run=False)
        assert result.purged_count == 4
        assert identityless.purged_count == 0
    assert _counts(store) == (0, 0)


def test_purge_all_empties_both_stores(store: ProjectSyncStore) -> None:
    assert _counts(store) == (4, 2)
    _purge(store, dry_run=False, confirmation=PURGE_ALL_CONFIRMATION)
    assert _counts(store) == (0, 0)


def test_purge_all_reaches_the_populations_the_union_misses(
    store: ProjectSyncStore,
) -> None:
    result = _purge(store, dry_run=False, confirmation=PURGE_ALL_CONFIRMATION)
    assert set(result.purged_event_ids) == {
        "E-delivered",
        "E-never",
        "E-archived",
        "E-refused",
    }


def test_purge_all_reports_totality_consistently_with_the_independent_count(
    store: ProjectSyncStore,
) -> None:
    before = _counts(store)
    result = _purge(store, dry_run=False, confirmation=PURGE_ALL_CONFIRMATION)
    assert result.purged_count == before[0]
    assert result.ledger_rows_removed == before[1]
    assert result.target_after == 0
    assert result.other_project_journal_differential == 0
    assert result.other_ledger_differential == 0
    assert result.is_exact


def test_the_journal_census_accounts_for_every_stored_row(
    store: ProjectSyncStore,
) -> None:
    from specify_cli.delivery.retention import _journal_census

    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        census = _journal_census(journal)
        assert census == {PROJECT_UUID: journal.count()}


def test_dry_run_is_the_default_and_deletes_nothing(store: ProjectSyncStore) -> None:
    before = _counts(store)
    result = _purge(store)
    assert result.dry_run
    assert result.purged_count == 4
    assert _counts(store) == before


def test_the_dry_run_predicts_exactly_what_the_real_run_deletes(
    store: ProjectSyncStore,
) -> None:
    preview = _purge(store)
    executed = _purge(store, dry_run=False, confirmation=PURGE_ALL_CONFIRMATION)
    assert preview.purged_event_ids == executed.purged_event_ids
    assert preview.ledger_rows_selected == executed.ledger_rows_removed


def test_a_confirmed_dry_run_still_deletes_nothing(store: ProjectSyncStore) -> None:
    before = _counts(store)
    result = _purge(store, confirmation=PURGE_ALL_CONFIRMATION)
    assert result.dry_run
    assert _counts(store) == before


def test_an_unconfirmed_destructive_run_refuses_loudly(
    store: ProjectSyncStore,
) -> None:
    before = _counts(store)
    with pytest.raises(PurgeNotConfirmedError):
        _purge(store, dry_run=False)
    assert _counts(store) == before


def test_a_wrong_confirmation_phrase_refuses(store: ProjectSyncStore) -> None:
    before = _counts(store)
    for attempt in (
        "yes",
        "PURGE",
        PURGE_ALL_CONFIRMATION.upper(),
        PURGE_ALL_CONFIRMATION + "!",
    ):
        with pytest.raises(PurgeNotConfirmedError):
            _purge(store, dry_run=False, confirmation=attempt)
    assert _counts(store) == before


def test_a_failure_between_the_two_stores_is_not_atomic_and_leaves_the_journal(store: ProjectSyncStore, monkeypatch: pytest.MonkeyPatch) -> None:
    """Historical node: the aggregate transaction now rolls both tables back."""
    original = EventJournal.purge_events

    def _delete_then_fail(self: EventJournal, event_ids: list[str]) -> None:
        original(self, event_ids)
        raise OSError("disk failure after aggregate delete")

    monkeypatch.setattr(EventJournal, "purge_events", _delete_then_fail)
    with pytest.raises(OSError, match="aggregate delete"):
        _purge(store, dry_run=False, confirmation=PURGE_ALL_CONFIRMATION)
    assert _counts(store) == (4, 2), "one UoW must roll journal and ledger back together"
