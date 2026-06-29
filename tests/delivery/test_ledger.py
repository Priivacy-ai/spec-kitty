"""Acceptance tests for the per-event/per-target delivery ledger (WP05).

These tests pin **observable ledger/DB state** (NFR-001), never internal call
order. The headline behaviours they lock are:

* the full delivery-outcome matrix (NFR-002): ``success``, ``duplicate``,
  ``pending``, ``rejected``, ``failed_transient`` and ``terminal_failed``;
* a successful/duplicate delivery is a ledger UPDATE that never deletes a journal
  event (FR-001 boundary, contract §3);
* the selection query returns undelivered-for-target and **excludes
  terminal-failed** so an oversized/permanent event parks while the drain still
  progresses (FR-004 / FR-015);
* identity is per-target — an event delivered to target A is still selectable for
  target B (FR-005 re-drain precursor);
* the delivered-anywhere immutability gate consumed by WP08 (FR-011 precursor);
* idempotent re-delivery yields ``duplicate`` with no corruption and unchanged
  event IDs (NFR-003);
* the selection-supporting index is part of the locked contract.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from specify_cli.delivery.ledger import (
    LEDGER_INDEX_NAME,
    LEDGER_TABLE,
    STATUS_DUPLICATE,
    STATUS_FAILED_TRANSIENT,
    STATUS_PENDING,
    STATUS_REJECTED,
    STATUS_SUCCESS,
    STATUS_TERMINAL_FAILED,
    LedgerRow,
    SqliteDeliveryLedger,
    init_ledger,
)

pytestmark = pytest.mark.fast

TARGET_A = "tgt-a"
TARGET_B = "tgt-b"
EVT_1 = "evt-1"
EVT_2 = "evt-2"
EVT_3 = "evt-3"

# A stand-in for the journal's event universe (the ledger never owns/deletes it).
JOURNAL = (EVT_1, EVT_2, EVT_3)


def _ts(second: int) -> str:
    """Deterministic ISO-8601 UTC timestamp for stable assertions."""
    return f"2026-06-29T00:00:{second:02d}+00:00"


@pytest.fixture
def ledger() -> Iterator[SqliteDeliveryLedger]:
    led = SqliteDeliveryLedger(":memory:")
    try:
        yield led
    finally:
        led.close()


# ---------------------------------------------------------------------------
# T026 — schema: per-(event_id, target_id) row, PK, selection index
# ---------------------------------------------------------------------------


def test_table_pk_and_selection_index_present(ledger: SqliteDeliveryLedger) -> None:
    conn = ledger.connection
    tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert LEDGER_TABLE in tables

    info = list(conn.execute(f"PRAGMA table_info({LEDGER_TABLE})"))
    pk = sorted((r["pk"], r["name"]) for r in info if r["pk"])
    assert [name for _, name in pk] == ["event_id", "target_id"]

    indexes = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert LEDGER_INDEX_NAME in indexes


def test_init_is_idempotent() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_ledger(conn)
    conn.execute(
        f"INSERT INTO {LEDGER_TABLE} (event_id, target_id, status, attempt_count) "
        "VALUES (?, ?, ?, ?)",
        (EVT_1, TARGET_A, STATUS_PENDING, 1),
    )
    conn.commit()
    # Re-running init must not raise and must not drop existing rows.
    init_ledger(conn)
    count = conn.execute(f"SELECT COUNT(*) AS n FROM {LEDGER_TABLE}").fetchone()["n"]
    assert count == 1
    conn.close()


def test_pending_row_roundtrips_with_optional_fields_unset(ledger: SqliteDeliveryLedger) -> None:
    ledger.record_pending(EVT_1, TARGET_A, at=_ts(1))
    row = ledger.get(EVT_1, TARGET_A)
    assert row is not None
    assert row.status == STATUS_PENDING
    assert row.server_drain_state == "pending"
    assert row.accepted_at == _ts(1)
    assert row.completed_at is None
    assert row.last_http_status is None
    assert row.last_error is None
    assert row.last_response_json is None


def test_pk_collapses_repeated_pair_into_one_row(ledger: SqliteDeliveryLedger) -> None:
    ledger.record_pending(EVT_1, TARGET_A, at=_ts(1))
    ledger.record_transient(EVT_1, TARGET_A, http_status=503, error="boom", at=_ts(2))
    rows = ledger.connection.execute(
        f"SELECT COUNT(*) AS n FROM {LEDGER_TABLE} WHERE event_id = ? AND target_id = ?",
        (EVT_1, TARGET_A),
    ).fetchone()
    assert rows["n"] == 1


# ---------------------------------------------------------------------------
# T027 — success/duplicate are terminal-success rows; never delete the journal
# ---------------------------------------------------------------------------


def test_record_success_is_terminal_and_does_not_delete_journal(
    ledger: SqliteDeliveryLedger,
) -> None:
    journal = list(JOURNAL)
    ledger.record_success(EVT_1, TARGET_A, http_status=200, response_json='{"ok":true}', at=_ts(5))
    row = ledger.get(EVT_1, TARGET_A)
    assert row is not None
    assert row.status == STATUS_SUCCESS
    assert row.completed_at == _ts(5)
    assert row.last_http_status == 200
    assert row.attempt_count == 1
    # FR-001 boundary: the ledger has no path that mutates the journal universe,
    # and exposes no event-delete surface at all.
    assert journal == list(JOURNAL)
    assert not any(
        hasattr(ledger, name) for name in ("delete_event", "delete_journal", "remove_event")
    )


def test_duplicate_is_distinct_status_but_treated_as_delivered(
    ledger: SqliteDeliveryLedger,
) -> None:
    ledger.record_duplicate(EVT_1, TARGET_A, http_status=200, at=_ts(5))
    row = ledger.get(EVT_1, TARGET_A)
    assert row is not None
    assert row.status == STATUS_DUPLICATE
    # Treated as delivered for selection: no longer undelivered for target A.
    assert EVT_1 not in ledger.select_undelivered(target_id=TARGET_A, event_universe=JOURNAL)
    assert ledger.delivered_anywhere(EVT_1) is True


# ---------------------------------------------------------------------------
# T028 — pending / rejected / failed_transient remain selectable (non-terminal)
# ---------------------------------------------------------------------------


def test_nonterminal_states_remain_selectable(ledger: SqliteDeliveryLedger) -> None:
    ledger.record_pending(EVT_1, TARGET_A, at=_ts(1))
    ledger.record_rejected(EVT_2, TARGET_A, http_status=422, error="too big", at=_ts(2))
    ledger.record_transient(EVT_3, TARGET_A, http_status=503, error="upstream", at=_ts(3))
    selected = ledger.select_undelivered(target_id=TARGET_A, event_universe=JOURNAL)
    assert set(selected) == {EVT_1, EVT_2, EVT_3}
    assert ledger.get(EVT_2, TARGET_A).status == STATUS_REJECTED
    assert ledger.get(EVT_3, TARGET_A).status == STATUS_FAILED_TRANSIENT


def test_batch_transient_does_not_flip_per_event_rejection(ledger: SqliteDeliveryLedger) -> None:
    # A per-event content rejection and a separate batch-level transient failure
    # stay distinguishable by their durable status; neither becomes terminal.
    ledger.record_rejected(EVT_1, TARGET_A, http_status=422, error="content", at=_ts(1))
    ledger.record_transient(EVT_2, TARGET_A, http_status=500, error="batch", at=_ts(1))
    assert ledger.get(EVT_1, TARGET_A).status == STATUS_REJECTED
    assert ledger.get(EVT_2, TARGET_A).status == STATUS_FAILED_TRANSIENT
    selected = ledger.select_undelivered(target_id=TARGET_A, event_universe=JOURNAL)
    assert {EVT_1, EVT_2} <= set(selected)


def test_attempt_metadata_accumulates_across_attempts(ledger: SqliteDeliveryLedger) -> None:
    ledger.record_transient(EVT_1, TARGET_A, http_status=503, error="a", at=_ts(1))
    ledger.record_transient(EVT_1, TARGET_A, http_status=503, error="b", at=_ts(2))
    row = ledger.get(EVT_1, TARGET_A)
    assert row is not None
    assert row.attempt_count == 2
    assert row.first_attempted_at == _ts(1)
    assert row.last_attempted_at == _ts(2)


def test_transient_then_success_transitions_cleanly(ledger: SqliteDeliveryLedger) -> None:
    ledger.record_transient(EVT_1, TARGET_A, http_status=503, error="upstream", at=_ts(1))
    ledger.record_success(EVT_1, TARGET_A, http_status=200, at=_ts(2))
    row = ledger.get(EVT_1, TARGET_A)
    assert row is not None
    assert row.status == STATUS_SUCCESS
    assert row.completed_at == _ts(2)
    assert row.attempt_count == 2
    assert EVT_1 not in ledger.select_undelivered(target_id=TARGET_A, event_universe=JOURNAL)


# ---------------------------------------------------------------------------
# T029 — terminal-failed: permanent, retained, inspectable, selector-excluded
# ---------------------------------------------------------------------------


def test_terminal_failed_excluded_from_selection_but_retained(
    ledger: SqliteDeliveryLedger,
) -> None:
    journal = list(JOURNAL)
    ledger.record_terminal_failed(
        EVT_1, TARGET_A, http_status=413, error="payload too large", at=_ts(7)
    )
    # Excluded from selection so the drain progresses past the oversized event.
    assert EVT_1 not in ledger.select_undelivered(target_id=TARGET_A, event_universe=JOURNAL)
    # Inspectable and retained; the journal is never deleted.
    row = ledger.get(EVT_1, TARGET_A)
    assert row is not None
    assert row.status == STATUS_TERMINAL_FAILED
    assert row.last_http_status == 413
    assert row.completed_at == _ts(7)
    assert journal == list(JOURNAL)
    # Distinguishable from the retryable failure states.
    assert row.status not in {STATUS_FAILED_TRANSIENT, STATUS_REJECTED}


def test_terminal_failed_is_not_delivered_anywhere(ledger: SqliteDeliveryLedger) -> None:
    ledger.record_terminal_failed(EVT_1, TARGET_A, http_status=413, error="oversized", at=_ts(7))
    # A permanent failure never reached the target, so it does NOT freeze the
    # event for coalescing (delivered_anywhere is scoped to terminal-SUCCESS).
    assert ledger.delivered_anywhere(EVT_1) is False


# ---------------------------------------------------------------------------
# T030 — selection query: undelivered-for-target, excluding terminal-failed
# ---------------------------------------------------------------------------


def test_delivered_to_a_still_selectable_for_b(ledger: SqliteDeliveryLedger) -> None:
    ledger.record_success(EVT_1, TARGET_A, http_status=200, at=_ts(5))
    assert EVT_1 not in ledger.select_undelivered(target_id=TARGET_A, event_universe=JOURNAL)
    assert EVT_1 in ledger.select_undelivered(target_id=TARGET_B, event_universe=JOURNAL)


def test_select_undelivered_empty_universe(ledger: SqliteDeliveryLedger) -> None:
    assert ledger.select_undelivered(target_id=TARGET_A, event_universe=()) == []


def test_row_for_other_target_only_is_still_selectable(ledger: SqliteDeliveryLedger) -> None:
    ledger.record_success(EVT_1, TARGET_B, http_status=200, at=_ts(5))
    assert EVT_1 in ledger.select_undelivered(target_id=TARGET_A, event_universe=JOURNAL)


def test_select_undelivered_respects_limit(ledger: SqliteDeliveryLedger) -> None:
    selected = ledger.select_undelivered(target_id=TARGET_A, event_universe=JOURNAL, limit=2)
    assert len(selected) == 2
    assert selected == [EVT_1, EVT_2]


def test_select_pending_protocol_returns_nonterminal_rows(ledger: SqliteDeliveryLedger) -> None:
    ledger.record_pending(EVT_1, TARGET_A, at=_ts(1))
    ledger.record_success(EVT_2, TARGET_A, http_status=200, at=_ts(2))
    ledger.record_terminal_failed(EVT_3, TARGET_A, http_status=413, error="big", at=_ts(3))
    pending = list(ledger.select_pending(target_id=TARGET_A, limit=10))
    assert pending == [EVT_1]


def test_select_pending_respects_limit(ledger: SqliteDeliveryLedger) -> None:
    ledger.record_pending(EVT_1, TARGET_A, at=_ts(1))
    ledger.record_rejected(EVT_2, TARGET_A, http_status=422, error="x", at=_ts(2))
    assert list(ledger.select_pending(target_id=TARGET_A, limit=1)) == [EVT_1]


# ---------------------------------------------------------------------------
# T031 — delivered-anywhere query (WP08 immutability gate)
# ---------------------------------------------------------------------------


def test_delivered_anywhere_true_on_any_terminal_success(ledger: SqliteDeliveryLedger) -> None:
    ledger.record_success(EVT_1, TARGET_B, http_status=200, at=_ts(5))
    ledger.record_pending(EVT_1, TARGET_A, at=_ts(6))
    # Terminal success to ANY target freezes the event even while another target
    # is still pending.
    assert ledger.delivered_anywhere(EVT_1) is True


def test_delivered_anywhere_false_for_only_nonterminal_rows(
    ledger: SqliteDeliveryLedger,
) -> None:
    ledger.record_pending(EVT_1, TARGET_A, at=_ts(1))
    ledger.record_rejected(EVT_1, TARGET_B, http_status=422, error="x", at=_ts(2))
    assert ledger.delivered_anywhere(EVT_1) is False
    assert ledger.delivered_anywhere("unknown-event") is False


# ---------------------------------------------------------------------------
# T032 — idempotent re-delivery (NFR-003) + Protocol record_result surface
# ---------------------------------------------------------------------------


def test_idempotent_redelivery_yields_duplicate_unchanged_event_ids(
    ledger: SqliteDeliveryLedger,
) -> None:
    first = ledger.record_success(EVT_1, TARGET_A, http_status=200, at=_ts(5))
    second = ledger.record_success(EVT_1, TARGET_A, http_status=200, at=_ts(6))
    assert first == STATUS_SUCCESS
    assert second == STATUS_DUPLICATE
    # No row duplication; event IDs unchanged (NFR-003 / contract "no corruption").
    rows = ledger.connection.execute(
        f"SELECT event_id FROM {LEDGER_TABLE} WHERE target_id = ?", (TARGET_A,)
    ).fetchall()
    assert [r["event_id"] for r in rows] == [EVT_1]
    assert ledger.delivered_anywhere(EVT_1) is True


def test_record_result_dispatches_full_vocabulary(ledger: SqliteDeliveryLedger) -> None:
    cases = {
        "success": STATUS_SUCCESS,
        "duplicate": STATUS_DUPLICATE,
        "pending": STATUS_PENDING,
        "rejected": STATUS_REJECTED,
        "transient": STATUS_FAILED_TRANSIENT,
        "terminal-failed": STATUS_TERMINAL_FAILED,
    }
    for i, (token, expected) in enumerate(cases.items()):
        event_id = f"evt-{token}"
        ledger.record_result(event_id=event_id, target_id=TARGET_A, result=token)
        row = ledger.get(event_id, TARGET_A)
        assert row is not None
        assert row.status == expected, f"{token} -> {row.status}"
        assert i >= 0  # keep the loop body referenced


def test_record_result_unknown_vocabulary_raises(ledger: SqliteDeliveryLedger) -> None:
    with pytest.raises(ValueError, match="unknown delivery result"):
        ledger.record_result(event_id=EVT_1, target_id=TARGET_A, result="bananas")


def test_record_result_accepts_enum_like_result_with_metadata(
    ledger: SqliteDeliveryLedger,
) -> None:
    class _Result:
        def __init__(self) -> None:
            self.value = "success"
            self.http_status = 201
            self.response_json = '{"ok":1}'

    ledger.record_result(event_id=EVT_1, target_id=TARGET_A, result=_Result())
    row = ledger.get(EVT_1, TARGET_A)
    assert row is not None
    assert row.status == STATUS_SUCCESS
    assert row.last_http_status == 201
    assert row.last_response_json == '{"ok":1}'


def test_protocol_methods_present_and_typed(ledger: SqliteDeliveryLedger) -> None:
    # The three DeliveryLedger Protocol methods WP07/WP08 bind to.
    assert callable(ledger.record_result)
    assert callable(ledger.select_pending)
    assert callable(ledger.delivered_anywhere)
    assert ledger.record_result(event_id=EVT_1, target_id=TARGET_A, result="pending") is None


def test_get_returns_none_for_missing_pair(ledger: SqliteDeliveryLedger) -> None:
    assert ledger.get("nope", "nope") is None


def test_record_result_success_is_idempotent_via_protocol(
    ledger: SqliteDeliveryLedger,
) -> None:
    # Re-recording success through the Protocol surface flips to duplicate too.
    ledger.record_result(event_id=EVT_1, target_id=TARGET_A, result="success")
    ledger.record_result(event_id=EVT_1, target_id=TARGET_A, result="success")
    row = ledger.get(EVT_1, TARGET_A)
    assert row is not None
    assert row.status == STATUS_DUPLICATE
    assert row.attempt_count == 2


def test_ledger_is_a_context_manager() -> None:
    with SqliteDeliveryLedger(":memory:") as led:
        led.record_success(EVT_1, TARGET_A, http_status=200, at=_ts(5))
        assert led.delivered_anywhere(EVT_1) is True


def test_terminal_status_sets_are_consistent() -> None:
    from specify_cli.delivery.ledger import TERMINAL_STATUSES, TERMINAL_SUCCESS_STATUSES

    expected_success = frozenset({STATUS_SUCCESS, STATUS_DUPLICATE})
    expected_terminal = expected_success | {STATUS_TERMINAL_FAILED}
    assert expected_success == TERMINAL_SUCCESS_STATUSES
    assert expected_terminal == TERMINAL_STATUSES


def test_ledger_row_is_immutable_value_object() -> None:
    row = LedgerRow(
        event_id=EVT_1,
        target_id=TARGET_A,
        status=STATUS_PENDING,
        attempt_count=1,
        first_attempted_at=_ts(1),
        last_attempted_at=_ts(1),
        accepted_at=_ts(1),
        completed_at=None,
        server_drain_state="pending",
        last_http_status=None,
        last_error=None,
        last_response_json=None,
    )
    with pytest.raises((AttributeError, TypeError)):
        row.status = STATUS_SUCCESS  # type: ignore[misc]
