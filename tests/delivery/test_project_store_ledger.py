"""Public contract for project-owned result and selection state."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from specify_cli.delivery.ledger import STATUS_TERMINAL_FAILED, SqliteDeliveryLedger
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.sync.consent import record_project_opt_in, record_project_opt_out
from specify_cli.sync.history_disclosure import (
    HistoryDisclosureCapability,
    HistoryDisclosureError,
    confirm_history_disclosure,
    preview_sealed_history,
)
from specify_cli.sync.project_store import ProjectSyncStore, ProjectUnitOfWork
from specify_cli.sync.queue import OfflineQueue

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


PROJECT = "aaaaaaaa-0000-0000-0000-000000000001"


def _project_only(store: ProjectSyncStore) -> None:
    authority = store.layout_generation()
    authority.begin_cutover("wp04-test")
    authority.publish_project_only("wp04-test", verify_exact=lambda: True)


def _capture(unit: ProjectUnitOfWork, store: ProjectSyncStore, event_id: str) -> None:
    EventJournal(unit, store.layout_generation()).append(
        Event(
            event_id=event_id,
            event_type="WPStatusChanged",
            payload=json.dumps({"project_uuid": PROJECT}).encode(),
            occurred_at="2026-08-10T00:00:00+00:00",
            created_at=f"2026-08-10T00:00:0{event_id[-1]}+00:00",
            project_uuid=PROJECT,
        )
    )


def _admit_current_target(store: ProjectSyncStore) -> None:
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, "
            "binding_audience) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                PROJECT,
                "https://app.spec-kitty.ai",
                "account-1",
                "teamspace-1",
                1,
                "admitted",
                "admission-1",
                "audience-1",
            ),
        )


def _confirmed_history(store: ProjectSyncStore) -> HistoryDisclosureCapability:
    preview = preview_sealed_history(store)
    return confirm_history_disclosure(
        store,
        preview,
        actor="test",
        idempotency_key="wp04-history",
        context=store.create_context(),
    )


def test_terminal_refusal_is_parked_and_selection_keeps_fifo_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT)
    _project_only(store)
    record_project_opt_in(PROJECT, actor="test")
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
        attempts_before_reselection = unit.execute(
            "SELECT COUNT(*) FROM delivery_attempts WHERE project_uuid = ?",
            (PROJECT,),
        ).fetchone()[0]

    assert parked is not None and parked.status == STATUS_TERMINAL_FAILED
    with store.unit_of_work() as unit:
        ledger = SqliteDeliveryLedger(unit, store.layout_generation())
        assert ledger.select_undelivered(
            target_id="target-2",
            event_universe=("event-1", "event-2", "event-3"),
        ) == ["event-2", "event-3"]
        assert (
            unit.execute(
                "SELECT COUNT(*) FROM delivery_attempts WHERE project_uuid = ?",
                (PROJECT,),
            ).fetchone()[0]
            == attempts_before_reselection
        ), "the compatibility projection must not write a duplicate attempt"


def test_fault_after_journal_and_result_rolls_back_one_outer_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT)
    _project_only(store)
    record_project_opt_in(PROJECT, actor="test")
    with pytest.raises(RuntimeError, match="fault"), store.unit_of_work() as unit:
        OfflineQueue(unit, store.layout_generation()).queue_event(
            {
                "event_id": "event-1",
                "event_type": "WPStatusChanged",
                "project_uuid": PROJECT,
                "payload": {"project_uuid": PROJECT},
            }
        )
        SqliteDeliveryLedger(unit, store.layout_generation()).record_pending("event-1", "target-1")
        raise RuntimeError("fault")

    with store.unit_of_work() as unit:
        assert EventJournal(unit, store.layout_generation()).count() == 0
        assert OfflineQueue(unit, store.layout_generation()).size() == 0
        assert SqliteDeliveryLedger(unit, store.layout_generation()).get("event-1", "target-1") is None


def test_sealed_history_stays_parked_and_opt_out_never_purges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT)
    _project_only(store)
    with store.unit_of_work() as unit:
        _capture(unit, store, "event-1")

    record_project_opt_in(PROJECT, actor="test")
    with store.unit_of_work() as unit:
        _capture(unit, store, "event-2")
        ledger = SqliteDeliveryLedger(unit, store.layout_generation())
        assert ledger.select_undelivered(
            target_id="target-1",
            event_universe=("event-1", "event-2"),
        ) == ["event-2"]

    record_project_opt_out(PROJECT, actor="test")
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, store.layout_generation())
        assert journal.count() == 2
        assert (
            SqliteDeliveryLedger(unit, store.layout_generation()).select_undelivered(
                target_id="target-1",
                event_universe=("event-1", "event-2"),
            )
            == []
        )


def test_fabricated_history_capability_cannot_select_sealed_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT)
    _project_only(store)
    with store.unit_of_work() as unit:
        _capture(unit, store, "event-1")
    record_project_opt_in(PROJECT, actor="test")
    _admit_current_target(store)
    genuine = _confirmed_history(store)
    forged = cast(
        HistoryDisclosureCapability,
        SimpleNamespace(project_uuid=PROJECT, row_ids=genuine.row_ids),
    )

    with store.unit_of_work() as unit:
        ledger = SqliteDeliveryLedger(unit, store.layout_generation())
        assert ledger.select_undelivered(
            target_id="target-1",
            event_universe=("event-1",),
            history_action=genuine,
        ) == ["event-1"]
        with pytest.raises(TypeError, match="history disclosure capability"):
            ledger.select_undelivered(
                target_id="target-1",
                event_universe=("event-1",),
                history_action=forged,
            )


def test_history_selection_revalidates_opt_out_and_exact_cohort(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT)
    _project_only(store)
    with store.unit_of_work() as unit:
        _capture(unit, store, "event-1")
    record_project_opt_in(PROJECT, actor="test")
    _admit_current_target(store)
    capability = _confirmed_history(store)

    with store.unit_of_work() as unit:
        unit.execute(
            "UPDATE journal_entries SET payload_json = ? WHERE project_uuid = ? AND entry_id = ?",
            ('{"changed":true}', PROJECT, "event-1"),
        )
        with pytest.raises(HistoryDisclosureError, match="cohort changed"):
            SqliteDeliveryLedger(unit, store.layout_generation()).select_undelivered(
                target_id="target-1",
                event_universe=("event-1",),
                history_action=capability,
            )

    record_project_opt_out(PROJECT, actor="test")
    with (
        store.unit_of_work() as unit,
        pytest.raises(HistoryDisclosureError, match="stale"),
    ):
        SqliteDeliveryLedger(unit, store.layout_generation()).select_undelivered(
            target_id="target-1",
            event_universe=("event-1",),
            history_action=capability,
        )
