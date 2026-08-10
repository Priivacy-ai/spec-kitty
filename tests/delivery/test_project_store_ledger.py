"""Public contract for project-owned result and selection state."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.delivery.ledger import STATUS_TERMINAL_FAILED, SqliteDeliveryLedger
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.sync.project_store import ProjectSyncStore


PROJECT = "aaaaaaaa-0000-0000-0000-000000000001"


def _project_only(store: ProjectSyncStore) -> None:
    authority = store.layout_generation()
    authority.begin_cutover("wp04-test")
    authority.publish_project_only("wp04-test", verify_exact=lambda: True)


def _capture(unit: object, store: ProjectSyncStore, event_id: str) -> None:
    EventJournal(unit, store.layout_generation()).append(  # type: ignore[arg-type]
        Event(
            event_id=event_id,
            event_type="WPStatusChanged",
            payload=json.dumps({"project_uuid": PROJECT}).encode(),
            occurred_at="2026-08-10T00:00:00+00:00",
            created_at=f"2026-08-10T00:00:0{event_id[-1]}+00:00",
            project_uuid=PROJECT,
        )
    )


def test_terminal_refusal_is_parked_and_selection_keeps_fifo_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT)
    _project_only(store)
    with store.unit_of_work() as unit:
        for event_id in ("event-1", "event-2", "event-3"):
            _capture(unit, store, event_id)
        ledger = SqliteDeliveryLedger(unit, store.layout_generation())
        ledger.record_terminal_failed("event-1", "target-1", error="refused")
        ledger.record_success("event-2", "target-1")
        assert ledger.select_undelivered(
            target_id="target-1",
            event_universe=("event-1", "event-2", "event-3"),
        ) == ["event-3"]
        parked = ledger.get("event-1", "target-1")

    assert parked is not None and parked.status == STATUS_TERMINAL_FAILED
    with store.unit_of_work() as unit:
        ledger = SqliteDeliveryLedger(unit, store.layout_generation())
        assert ledger.select_undelivered(
            target_id="target-2",
            event_universe=("event-1", "event-2", "event-3"),
        ) == ["event-1", "event-2", "event-3"]


def test_fault_after_journal_and_result_rolls_back_one_outer_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT)
    _project_only(store)
    with pytest.raises(RuntimeError, match="fault"), store.unit_of_work() as unit:
        _capture(unit, store, "event-1")
        SqliteDeliveryLedger(unit, store.layout_generation()).record_pending(
            "event-1", "target-1"
        )
        raise RuntimeError("fault")

    with store.unit_of_work() as unit:
        assert EventJournal(unit, store.layout_generation()).count() == 0
        assert SqliteDeliveryLedger(unit, store.layout_generation()).get("event-1", "target-1") is None
