"""Explicit purge acceptance tests at the UUID-owned physical-store boundary."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

from specify_cli.delivery.ledger import (
    STATUS_REJECTED,
    STATUS_SUCCESS,
    SqliteDeliveryLedger,
)
from specify_cli.delivery.retention import (
    purge_identity_less_events,
    purge_project_events,
)
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

_TARGET_A = "aaaaaaaa-0000-0000-0000-00000000000a"
_OTHER_B = "bbbbbbbb-0000-0000-0000-00000000000b"
_TARGET_ID = "tgt_teamspace"


def _event(event_id: str, project_uuid: str | None, index: int) -> Event:
    return Event(
        event_id=event_id,
        event_type="mission.updated",
        payload=json.dumps({"event_id": event_id, "project_uuid": project_uuid}).encode(),
        occurred_at="2026-07-29T00:00:00+00:00",
        created_at=f"2026-07-29T00:00:{index:02d}+00:00",
        project_uuid=project_uuid,
    )


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectSyncStore:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    value = ProjectSyncStore(_TARGET_A)
    authority = value.layout_generation()
    authority.begin_cutover("purge-tests")
    authority.publish_project_only("purge-tests", verify_exact=lambda: True)
    return value


@dataclass(frozen=True)
class _Repositories:
    journal: EventJournal
    ledger: SqliteDeliveryLedger


@pytest.fixture
def repositories(store: ProjectSyncStore) -> Iterator[_Repositories]:
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        for index in range(1, 4):
            journal.append(_event(f"a-{index}", _TARGET_A, index))
        ledger = SqliteDeliveryLedger(unit, store.layout_generation())
        ledger.record_success("a-1", _TARGET_ID)
        ledger.record_rejected("a-2", _TARGET_ID, error="nope")
        yield _Repositories(journal, ledger)


@pytest.fixture
def journal(repositories: _Repositories) -> EventJournal:
    return repositories.journal


@pytest.fixture
def ledger(repositories: _Repositories) -> SqliteDeliveryLedger:
    return repositories.ledger


def _journal_ids(journal: EventJournal) -> set[str]:
    return {event.event_id for event in journal.read_all()}


def _ledger_ids(ledger: SqliteDeliveryLedger) -> set[str]:
    return {row.event_id for row in ledger.rows()}


class TestDryRunIsTheDefault:
    def test_purge_without_dry_run_argument_changes_nothing(
        self,
        journal: EventJournal,
        ledger: SqliteDeliveryLedger,
    ) -> None:
        result = purge_project_events(_TARGET_A, journal=journal, ledger=ledger)
        assert result.dry_run is True
        assert _journal_ids(journal) == {"a-1", "a-2", "a-3"}
        assert _ledger_ids(ledger) == {"a-1", "a-2"}

    def test_dry_run_reports_exactly_what_a_real_run_would_remove(
        self,
        journal: EventJournal,
        ledger: SqliteDeliveryLedger,
    ) -> None:
        preview = purge_project_events(_TARGET_A, journal=journal, ledger=ledger)
        assert set(preview.purged_event_ids) == {"a-1", "a-2", "a-3"}
        assert preview.target_before == preview.target_after == 3
        assert preview.ledger_rows_selected == 2
        real = purge_project_events(_TARGET_A, journal=journal, ledger=ledger, dry_run=False)
        assert set(real.purged_event_ids) == set(preview.purged_event_ids)
        assert real.ledger_rows_removed == preview.ledger_rows_selected

    def test_dry_run_reports_the_forensic_state_breakdown_before_deletion(
        self,
        journal: EventJournal,
        ledger: SqliteDeliveryLedger,
    ) -> None:
        preview = purge_project_events(_TARGET_A, journal=journal, ledger=ledger)
        assert preview.ledger_status_before == {
            STATUS_SUCCESS: 1,
            STATUS_REJECTED: 1,
        }
        assert preview.never_attempted == 1


class TestExactness:
    def test_purge_removes_all_of_the_target_and_nothing_else(
        self,
        journal: EventJournal,
        ledger: SqliteDeliveryLedger,
    ) -> None:
        result = purge_project_events(_TARGET_A, journal=journal, ledger=ledger, dry_run=False)
        assert _journal_ids(journal) == set()
        assert result.target_after == 0
        assert result.other_project_journal_differential == 0
        assert result.other_ledger_differential == 0
        assert result.is_exact is True

    def test_the_other_projects_ledger_history_survives(
        self,
        journal: EventJournal,
        ledger: SqliteDeliveryLedger,
        store: ProjectSyncStore,
    ) -> None:
        other = ProjectSyncStore(_OTHER_B)
        with other.unit_of_work() as unit:
            other_journal = EventJournal(unit, other.layout_generation())
            other_journal.append(_event("b-1", _OTHER_B, 1))
            other_ledger = SqliteDeliveryLedger(unit, other.layout_generation())
            other_ledger.record_success("b-1", _TARGET_ID)
        purge_project_events(_TARGET_A, journal=journal, ledger=ledger, dry_run=False)
        with other.unit_of_work() as unit:
            observed = SqliteDeliveryLedger(unit, other.layout_generation())
            assert _ledger_ids(observed) == {"b-1"}
        assert store.database_path != other.database_path

    def test_the_target_projects_ledger_history_is_removed(
        self,
        journal: EventJournal,
        ledger: SqliteDeliveryLedger,
    ) -> None:
        result = purge_project_events(_TARGET_A, journal=journal, ledger=ledger, dry_run=False)
        assert result.ledger_rows_removed == 2
        assert _ledger_ids(ledger) == set()

    def test_purging_an_absent_project_is_a_no_op_not_an_error(
        self,
        journal: EventJournal,
        ledger: SqliteDeliveryLedger,
    ) -> None:
        with pytest.raises(ValueError, match="owner"):
            purge_project_events(_OTHER_B, journal=journal, ledger=ledger, dry_run=False)
        assert _journal_ids(journal) == {"a-1", "a-2", "a-3"}

    def test_a_blank_selector_removes_nothing(
        self,
        journal: EventJournal,
        ledger: SqliteDeliveryLedger,
    ) -> None:
        with pytest.raises(ValueError, match="owner"):
            purge_project_events("", journal=journal, ledger=ledger, dry_run=False)
        assert _journal_ids(journal) == {"a-1", "a-2", "a-3"}


class TestIdentityLessRows:
    def test_a_project_purge_never_touches_identity_less_rows(
        self,
        journal: EventJournal,
    ) -> None:
        with pytest.raises(ValueError, match="owner"):
            journal.append(_event("none-1", None, 6))
        assert _journal_ids(journal) == {"a-1", "a-2", "a-3"}

    def test_identity_less_rows_are_visible_in_the_census(
        self,
        journal: EventJournal,
        ledger: SqliteDeliveryLedger,
    ) -> None:
        result = purge_project_events(_TARGET_A, journal=journal, ledger=ledger)
        assert result.journal_before == {_TARGET_A: 3}
        assert "" not in result.journal_before

    def test_identity_less_rows_have_their_own_selector(
        self,
        journal: EventJournal,
        ledger: SqliteDeliveryLedger,
    ) -> None:
        result = purge_identity_less_events(journal=journal, ledger=ledger)
        assert result.dry_run is True
        assert result.purged_event_ids == ()
        assert _journal_ids(journal) == {"a-1", "a-2", "a-3"}


class TestUndeliveredOnlyScope:
    def test_undelivered_only_keeps_delivered_history(
        self,
        journal: EventJournal,
        ledger: SqliteDeliveryLedger,
    ) -> None:
        result = purge_project_events(
            _TARGET_A,
            journal=journal,
            ledger=ledger,
            dry_run=False,
            undelivered_only=True,
        )
        assert set(result.purged_event_ids) == {"a-2", "a-3"}
        assert _journal_ids(journal) == {"a-1"}
        assert _ledger_ids(ledger) == {"a-1"}
        assert result.other_project_journal_differential == 0
        assert result.other_ledger_differential == 0
        assert result.is_exact is True
