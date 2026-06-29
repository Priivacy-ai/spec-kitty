"""ATDD + unit coverage for the WP07 Sync Dispatcher (IC-05 / IC-05a).

Every assertion here is on **observable on-disk / ledger / receiver state** — never
on internal call order (NFR-001). The dispatcher is driven through the WP03 journal,
the WP05 ledger, and a WP06 receiver (the credential-free stub, SC-005); the five
contract §3 "Required tests" map onto the scenario tests below:

* A->B replay (FR-005 / SC-001, contract §3 row 1) — :func:`test_replay_to_new_target_redelivers_and_retains`.
* Re-sync skips already-successful (FR-004, contract §3 row 2) — :func:`test_resync_to_same_target_skips_delivered`.
* Non-destructive success (FR-001) — :func:`test_success_is_non_destructive`.
* Oversized / permanent failure progresses the drain (FR-015 / IC-05a, contract §3 row 4) —
  :func:`test_terminal_failed_parks_event_and_drain_progresses`.
* Idempotent re-delivery (NFR-003) — :func:`test_idempotent_redelivery_yields_duplicate`.

Plus focused unit tests over the select / post / record phases and the D-020
coalescing carry so each helper is exercised directly (T044 / coverage).
"""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import pytest

from specify_cli.delivery.dispatcher import (
    DispatchSummary,
    _decode_payload,
    _install_coalescing,
    _post,
    _record,
    _record_one,
    _select_undelivered,
    dispatch,
)
from specify_cli.delivery.ledger import (
    STATUS_DUPLICATE,
    STATUS_SUCCESS,
    STATUS_TERMINAL_FAILED,
    TERMINAL_SUCCESS_STATUSES,
    SqliteDeliveryLedger,
)
from specify_cli.delivery.receivers import (
    DeliveryOutcome,
    DeliveryResult,
    OutboundEvent,
    StubReceiver,
)
from specify_cli.delivery.targets import SqliteDeliveryTargetRegistry
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event

if TYPE_CHECKING:
    from specify_cli.delivery.interfaces import DeliveryTarget

pytestmark = pytest.mark.fast

_OCCURRED_AT = "2026-06-29T00:00:00+00:00"


# --------------------------------------------------------------------------- #
# Fixtures / builders                                                          #
# --------------------------------------------------------------------------- #


def _make_event(index: int) -> Event:
    """Build a distinct JSON-payload journal event with a deterministic timestamp."""
    event_id = f"evt-{index}"
    payload = json.dumps(
        {"event_id": event_id, "event_type": "mission.updated", "n": index}
    ).encode("utf-8")
    return Event(
        event_id=event_id,
        event_type="mission.updated",
        payload=payload,
        occurred_at=_OCCURRED_AT,
        created_at=f"2026-06-29T00:00:0{index}+00:00",
    )


@pytest.fixture
def journal(tmp_path: Any) -> EventJournal:
    """A journal seeded with three distinct events (the drain universe)."""
    jrnl = EventJournal(tmp_path / "journal.db")
    for index in range(3):
        jrnl.append(_make_event(index))
    return jrnl


@pytest.fixture
def ledger() -> SqliteDeliveryLedger:
    return SqliteDeliveryLedger(":memory:")


@pytest.fixture
def registry() -> SqliteDeliveryTargetRegistry:
    return SqliteDeliveryTargetRegistry(":memory:")


@pytest.fixture
def target_a(registry: SqliteDeliveryTargetRegistry) -> DeliveryTarget:
    return registry.register(
        url="https://a.example.com", team_slug="team", user_email="u@example.com"
    )


@pytest.fixture
def target_b(registry: SqliteDeliveryTargetRegistry) -> DeliveryTarget:
    return registry.register(
        url="https://b.example.com", team_slug="team", user_email="u@example.com"
    )


class _TerminalFailStub:
    """A real DeliveryReceiver (§4) that maps one chosen event to terminal-failed.

    Exercises the FR-015 mixed-batch path: every other event delivers successfully.
    No ``isinstance`` is needed in the dispatcher — it drives this through the same
    contract as :class:`StubReceiver`.
    """

    def __init__(self, *, fail_id: str) -> None:
        self._fail_id = fail_id
        self._delivered: list[str] = []

    @property
    def endpoint_url(self) -> str:
        return "http://localhost/__terminal-fail-stub__/api/v1/events/batch/"

    def auth_headers(self) -> dict[str, str]:
        return {}

    def gates(self) -> tuple[Any, ...]:
        return ()

    def deliver(self, batch: Sequence[OutboundEvent]) -> list[DeliveryResult]:
        results: list[DeliveryResult] = []
        for event in batch:
            if event.event_id == self._fail_id:
                results.append(
                    DeliveryResult(
                        event_id=event.event_id,
                        outcome=DeliveryOutcome.TERMINAL_FAILED,
                        http_status=413,
                        error="payload too large (oversized, permanent)",
                    )
                )
            else:
                self._delivered.append(event.event_id)
                results.append(
                    DeliveryResult(
                        event_id=event.event_id,
                        outcome=DeliveryOutcome.SUCCESS,
                        http_status=200,
                    )
                )
        return results

    def delivered_ids(self) -> tuple[str, ...]:
        return tuple(self._delivered)


class _FakeCoalesce:
    """Stand-in for WP08's ``event_journal.coalesce`` module (a merge-time sibling)."""

    def __init__(self) -> None:
        self.installed_with: object | None = None

    def install(self, ledger: object) -> str:
        self.installed_with = ledger
        return "fake-strategy"


# --------------------------------------------------------------------------- #
# Scenario 1 — A->B replay (FR-005 / SC-001, contract §3 row 1)                #
# --------------------------------------------------------------------------- #


def test_replay_to_new_target_redelivers_and_retains(
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    target_a: DeliveryTarget,
    target_b: DeliveryTarget,
) -> None:
    stub_a = StubReceiver()
    stub_b = StubReceiver()

    summary_a = dispatch(journal=journal, ledger=ledger, receiver=stub_a, target=target_a)
    assert summary_a.delivered == 3
    assert journal.count() == 3  # retention: nothing deleted on success (FR-001)
    assert set(stub_a.received_event_ids()) == {"evt-0", "evt-1", "evt-2"}
    for index in range(3):
        row = ledger.get(f"evt-{index}", target_a.target_id)
        assert row is not None and row.status in TERMINAL_SUCCESS_STATUSES

    # Switch the active target: the same retained events have no terminal-success
    # row for B, so they re-select and re-deliver — zero manual SQLite copying.
    summary_b = dispatch(journal=journal, ledger=ledger, receiver=stub_b, target=target_b)
    assert summary_b.delivered == 3
    assert journal.count() == 3  # still fully retained after BOTH drains (SC-002)
    assert set(stub_b.received_event_ids()) == {"evt-0", "evt-1", "evt-2"}
    for index in range(3):
        row = ledger.get(f"evt-{index}", target_b.target_id)
        assert row is not None and row.status in TERMINAL_SUCCESS_STATUSES


# --------------------------------------------------------------------------- #
# Scenario 2 — re-sync skips already-successful (FR-004, contract §3 row 2)    #
# --------------------------------------------------------------------------- #


def test_resync_to_same_target_skips_delivered(
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    target_a: DeliveryTarget,
) -> None:
    stub = StubReceiver()

    first = dispatch(journal=journal, ledger=ledger, receiver=stub, target=target_a)
    assert first.selected == 3 and first.delivered == 3

    second = dispatch(journal=journal, ledger=ledger, receiver=stub, target=target_a)
    assert second.selected == 0  # all terminal-successful for A → nothing to drain
    assert second.delivered == 0
    # The stub was not asked to deliver anything new on the second drain.
    assert len(stub.received_event_ids()) == 3


# --------------------------------------------------------------------------- #
# Scenario 3 — non-destructive success (FR-001)                               #
# --------------------------------------------------------------------------- #


def test_success_is_non_destructive(
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    target_a: DeliveryTarget,
) -> None:
    before = journal.count()
    stub = StubReceiver()

    dispatch(journal=journal, ledger=ledger, receiver=stub, target=target_a)

    assert journal.count() == before  # row count identical before/after (no DELETE)
    for index in range(3):
        event_id = f"evt-{index}"
        assert journal.read_by_id(event_id) is not None  # payload retained
        row = ledger.get(event_id, target_a.target_id)
        assert row is not None and row.status == STATUS_SUCCESS


# --------------------------------------------------------------------------- #
# Scenario 4 — oversized / permanent failure (FR-015 / IC-05a, §3 row 4)      #
# --------------------------------------------------------------------------- #


def test_terminal_failed_parks_event_and_drain_progresses(
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    target_a: DeliveryTarget,
) -> None:
    stub = _TerminalFailStub(fail_id="evt-1")

    summary = dispatch(journal=journal, ledger=ledger, receiver=stub, target=target_a)

    # The deliverable events progressed; the oversized one parked — drain did not stall.
    assert summary.delivered == 2
    assert summary.terminal_failed == 1
    assert stub.delivered_ids() == ("evt-0", "evt-2")

    # The oversized event is terminal-failed (NOT deleted, NOT success) and retained.
    parked = ledger.get("evt-1", target_a.target_id)
    assert parked is not None and parked.status == STATUS_TERMINAL_FAILED
    assert journal.count() == 3  # nothing destroyed
    assert journal.read_by_id("evt-1") is not None  # inspectable (FR-015)

    # The next drain does NOT re-select the parked event (selector-exclusion is how
    # we keep the drain progressing without destroying the payload).
    next_selection = _select_undelivered(journal, ledger, target_a.target_id)
    assert [event.event_id for event in next_selection] == []

    second = dispatch(journal=journal, ledger=ledger, receiver=stub, target=target_a)
    assert second.selected == 0  # parked + delivered all excluded


def test_terminal_failed_is_per_target(
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    target_a: DeliveryTarget,
    target_b: DeliveryTarget,
) -> None:
    dispatch(journal=journal, ledger=ledger, receiver=_TerminalFailStub(fail_id="evt-1"), target=target_a)

    # An event terminal-failed on A is still selectable for B (terminal-failed is
    # per-target, contract §3 / T043 edge case).
    selectable_for_b = _select_undelivered(journal, ledger, target_b.target_id)
    assert "evt-1" in [event.event_id for event in selectable_for_b]


# --------------------------------------------------------------------------- #
# Scenario 5 — idempotent re-delivery (NFR-003)                               #
# --------------------------------------------------------------------------- #


def test_idempotent_redelivery_yields_duplicate(
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    target_a: DeliveryTarget,
) -> None:
    stub = StubReceiver()
    events = _select_undelivered(journal, ledger, target_a.target_id)

    first_results = _post(stub, events)
    _record(ledger, target_a.target_id, first_results, selected=len(events))

    # Re-post the SAME events through the SAME stub: the server reports duplicates;
    # recording is idempotent — no row duplication and the event IDs are unchanged.
    repeat_results = _post(stub, events)
    summary = _record(ledger, target_a.target_id, repeat_results, selected=len(events))

    assert summary.duplicate == 3
    assert journal.count() == 3
    assert {event.event_id for event in journal.read_all()} == {"evt-0", "evt-1", "evt-2"}
    for index in range(3):
        row = ledger.get(f"evt-{index}", target_a.target_id)
        assert row is not None and row.status == STATUS_DUPLICATE
        assert row.attempt_count == 2  # merged onto one row, not duplicated


def test_record_rolls_back_batch_on_mid_record_failure(
    target_a: DeliveryTarget,
) -> None:
    """A ledger failure while recording a remote batch leaves no partial rows."""

    class _FailAfterFirstLedger(SqliteDeliveryLedger):
        calls = 0

        def record_result(self, *, event_id: str, target_id: str, result: object) -> None:
            self.calls += 1
            super().record_result(event_id=event_id, target_id=target_id, result=result)
            if self.calls == 1:
                raise sqlite3.OperationalError("synthetic ledger failure")

    ledger = _FailAfterFirstLedger(":memory:")
    results = [
        DeliveryResult(event_id="evt-a", outcome=DeliveryOutcome.SUCCESS),
        DeliveryResult(event_id="evt-b", outcome=DeliveryOutcome.SUCCESS),
    ]

    with pytest.raises(sqlite3.OperationalError):
        _record(ledger, target_a.target_id, results, selected=2)

    assert ledger.get("evt-a", target_a.target_id) is None
    assert ledger.get("evt-b", target_a.target_id) is None


# --------------------------------------------------------------------------- #
# No active target → no-op (T039 step 4)                                       #
# --------------------------------------------------------------------------- #


def test_no_active_target_is_a_noop(
    journal: EventJournal, ledger: SqliteDeliveryLedger
) -> None:
    stub = StubReceiver()

    summary = dispatch(journal=journal, ledger=ledger, receiver=stub, target=None)

    assert summary.target_id is None
    assert summary.selected == 0
    assert summary.recorded == 0
    assert stub.received_event_ids() == ()  # the receiver was never invoked
    assert journal.count() == 3  # nothing touched


# --------------------------------------------------------------------------- #
# Phase-level unit tests (T044: each phase independently testable)            #
# --------------------------------------------------------------------------- #


def test_select_undelivered_uses_universe_and_excludes_terminal(
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    target_a: DeliveryTarget,
) -> None:
    # Initially every journal event is undelivered for A.
    selected = _select_undelivered(journal, ledger, target_a.target_id)
    assert [event.event_id for event in selected] == ["evt-0", "evt-1", "evt-2"]

    # Mark one delivered and one terminal-failed → both leave the selection set.
    ledger.record_success("evt-0", target_a.target_id)
    ledger.record_terminal_failed("evt-2", target_a.target_id)
    remaining = _select_undelivered(journal, ledger, target_a.target_id)
    assert [event.event_id for event in remaining] == ["evt-1"]


def test_select_undelivered_honours_limit(
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    target_a: DeliveryTarget,
) -> None:
    selected = _select_undelivered(journal, ledger, target_a.target_id, limit=2)
    assert [event.event_id for event in selected] == ["evt-0", "evt-1"]


def test_post_empty_selection_short_circuits() -> None:
    stub = StubReceiver()
    assert _post(stub, []) == []
    assert stub.received_event_ids() == ()  # receiver not called for an empty batch


def test_record_one_terminal_failed_routes_to_terminal_writer(
    ledger: SqliteDeliveryLedger,
    target_a: DeliveryTarget,
) -> None:
    result = DeliveryResult(
        event_id="evt-0",
        outcome=DeliveryOutcome.TERMINAL_FAILED,
        http_status=413,
        error="too large",
    )
    _record_one(ledger, target_a.target_id, result)
    row = ledger.get("evt-0", target_a.target_id)
    assert row is not None
    assert row.status == STATUS_TERMINAL_FAILED
    assert row.last_http_status == 413
    assert row.last_error == "too large"


def test_record_one_non_terminal_forwards_metadata(
    ledger: SqliteDeliveryLedger,
    target_a: DeliveryTarget,
) -> None:
    result = DeliveryResult(
        event_id="evt-0",
        outcome=DeliveryOutcome.REJECTED,
        http_status=400,
        error="bad content",
    )
    _record_one(ledger, target_a.target_id, result)
    row = ledger.get("evt-0", target_a.target_id)
    assert row is not None
    assert row.status == "rejected"
    assert row.last_http_status == 400
    assert row.last_error == "bad content"


def test_decode_payload_parses_json_object() -> None:
    event = _make_event(7)
    decoded = _decode_payload(event)
    assert decoded["event_id"] == "evt-7"
    assert decoded["n"] == 7


def test_decode_payload_wraps_non_json_bytes() -> None:
    event = Event(
        event_id="evt-raw",
        event_type="mission.updated",
        payload=b"\x00\x01not-json",
        occurred_at=_OCCURRED_AT,
        created_at=_OCCURRED_AT,
    )
    decoded = _decode_payload(event)
    assert decoded["event_id"] == "evt-raw"
    assert decoded["event_type"] == "mission.updated"


def test_dispatch_summary_counts_and_recorded() -> None:
    empty = DispatchSummary.empty()
    assert empty.target_id is None
    assert empty.selected == 0
    assert empty.recorded == 0

    counts = dict.fromkeys(DeliveryOutcome, 0)
    counts[DeliveryOutcome.SUCCESS] = 2
    counts[DeliveryOutcome.PENDING] = 1
    summary = DispatchSummary.from_counts("tgt", selected=3, counts=counts)
    assert summary.delivered == 2
    assert summary.pending == 1
    assert summary.recorded == 3


# --------------------------------------------------------------------------- #
# D-020 coalescing carry — install(ledger) on the live dispatch path (FR-011) #
# --------------------------------------------------------------------------- #


def test_install_coalescing_invokes_install_with_ledger(
    ledger: SqliteDeliveryLedger,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeCoalesce()
    monkeypatch.setattr(
        "specify_cli.delivery.dispatcher._load_coalesce", lambda: fake
    )
    assert _install_coalescing(ledger) is True
    assert fake.installed_with is ledger


def test_install_coalescing_degrades_when_module_absent(
    ledger: SqliteDeliveryLedger,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _missing() -> Any:
        raise ModuleNotFoundError("no coalesce module in this lane")

    monkeypatch.setattr("specify_cli.delivery.dispatcher._load_coalesce", _missing)
    # The drain must not break when WP08's coalesce module is not yet merged.
    assert _install_coalescing(ledger) is False


def test_dispatch_activates_coalescing_on_live_path(
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    target_a: DeliveryTarget,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeCoalesce()
    monkeypatch.setattr(
        "specify_cli.delivery.dispatcher._load_coalesce", lambda: fake
    )
    stub = StubReceiver()

    dispatch(journal=journal, ledger=ledger, receiver=stub, target=target_a)

    # The live dispatch path registered the real coalescing strategy bound to the
    # delivery ledger (D-020): without this, FR-011 coalescing is dead in production.
    assert fake.installed_with is ledger
