"""Coalescing-with-delivered-event-immutability tests (WP08 / T046-T050).

These assert observable on-disk/ledger state (NFR-001): undelivered events with
the same coalesce key collapse to one row; a *delivered* event's stored payload
bytes are byte-for-byte immutable (NFR-002 / FR-011); a post-delivery coalescible
event becomes a NEW row plus a ``superseded`` marker linking prior->new without
mutating the prior payload (contract section 3). Delivery state is recorded via
the *real* WP05 ledger over SQLite, never a mock that lies about delivery.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.event_journal import Event, EventJournal, reset_coalesce_strategy
from specify_cli.event_journal.coalesce import (
    CoalescingStrategy,
    install,
    read_supersede_markers,
)

pytestmark = pytest.mark.fast

TARGET = "target-A"
T1 = "2026-06-29T00:00:01+00:00"
T2 = "2026-06-29T00:00:02+00:00"
T3 = "2026-06-29T00:00:03+00:00"


@pytest.fixture(autouse=True)
def _reset_seam() -> Iterator[None]:
    """Reset the coalesce seam before/after every test so a registered strategy
    never leaks into another test (e.g. WP03's no-coalescing invariant)."""
    reset_coalesce_strategy()
    yield
    reset_coalesce_strategy()


@pytest.fixture()
def journal(tmp_path: Path) -> EventJournal:
    return EventJournal(tmp_path / "event_journal" / "journal-test.db")


@pytest.fixture()
def ledger() -> Iterator[SqliteDeliveryLedger]:
    led = SqliteDeliveryLedger(":memory:")
    yield led
    led.close()


@pytest.fixture()
def strategy(ledger: SqliteDeliveryLedger) -> CoalescingStrategy:
    return install(ledger)


def _event(event_id: str, *, payload: bytes, key: str | None, created_at: str = T1) -> Event:
    return Event(
        event_id=event_id,
        event_type="WpStatusChanged",
        payload=payload,
        occurred_at=created_at,
        created_at=created_at,
        coalesce_key=key,
    )


def _payload_on_disk(db_path: Path, event_id: str) -> bytes:
    """Read an event's payload BLOB straight from the journal DB on disk.

    Deliberately bypasses the in-memory ``Event`` so a sneaky in-place UPDATE of a
    delivered event would be caught by the byte-for-byte assertion (T049).
    """
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT payload FROM event_journal WHERE event_id = ?", (event_id,)
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    return bytes(row[0])


# -- T050: no-key never coalesces -----------------------------------------------


def test_event_without_coalesce_key_is_never_coalesced(
    journal: EventJournal, strategy: CoalescingStrategy
) -> None:
    journal.append(_event("evt-1", payload=b"a", key=None, created_at=T1))
    journal.append(_event("evt-2", payload=b"b", key=None, created_at=T2))
    assert {e.event_id for e in journal.read_all()} == {"evt-1", "evt-2"}
    assert read_supersede_markers(journal) == []


# -- T050: undelivered collapse -------------------------------------------------


def test_undelivered_events_with_same_key_collapse_to_one_row(
    journal: EventJournal, strategy: CoalescingStrategy
) -> None:
    journal.append(_event("evt-1", payload=b"v1", key="grp", created_at=T1))
    journal.append(_event("evt-2", payload=b"v2", key="grp", created_at=T2))

    keyed = [e for e in journal.read_all() if e.coalesce_key == "grp"]
    assert len(keyed) == 1, "two undelivered same-key events must collapse to one row"
    # latest-wins collapse: the surviving (undelivered) row keeps its own id (C-005,
    # no id rewrite) but carries the most recent payload.
    assert keyed[0].event_id == "evt-1"
    assert _payload_on_disk(journal.db_path, "evt-1") == b"v2"
    assert journal.read_by_id("evt-2") is None
    assert read_supersede_markers(journal) == []


# -- T049: REQUIRED DB immutability test (NFR-002) ------------------------------


def test_coalesce_against_delivered_event_leaves_bytes_unchanged(
    journal: EventJournal, ledger: SqliteDeliveryLedger, strategy: CoalescingStrategy
) -> None:
    journal.append(_event("evt-1", payload=b"original-bytes", key="grp", created_at=T1))
    before = _payload_on_disk(journal.db_path, "evt-1")
    assert before == b"original-bytes"

    ledger.record_success("evt-1", TARGET)
    assert ledger.delivered_anywhere("evt-1") is True

    journal.append(_event("evt-2", payload=b"new-bytes", key="grp", created_at=T2))

    after = _payload_on_disk(journal.db_path, "evt-1")
    assert after == before == b"original-bytes", "delivered event payload must be immutable"

    new_row = journal.read_by_id("evt-2")
    assert new_row is not None
    assert new_row.event_id == "evt-2"
    assert new_row.payload == b"new-bytes"

    markers = read_supersede_markers(journal)
    assert len(markers) == 1
    assert markers[0].superseded_event_id == "evt-1"
    assert markers[0].superseded_by_event_id == "evt-2"
    assert markers[0].coalesce_key == "grp"


def test_superseded_prior_remains_inspectable_and_not_archived(
    journal: EventJournal, ledger: SqliteDeliveryLedger, strategy: CoalescingStrategy
) -> None:
    journal.append(_event("evt-1", payload=b"original", key="grp", created_at=T1))
    ledger.record_success("evt-1", TARGET)
    journal.append(_event("evt-2", payload=b"successor", key="grp", created_at=T2))

    prior = journal.read_by_id("evt-1")
    assert prior is not None, "supersession is metadata, never destruction"
    assert prior.archived_at is None, "prior stays re-drainable, not archived"
    assert journal.count() == 2


def test_second_delivered_event_is_not_mutated_by_later_coalescible(
    journal: EventJournal, ledger: SqliteDeliveryLedger, strategy: CoalescingStrategy
) -> None:
    journal.append(_event("evt-3", payload=b"delivered-2", key="grp2", created_at=T1))
    before = _payload_on_disk(journal.db_path, "evt-3")
    ledger.record_success("evt-3", TARGET)

    journal.append(_event("evt-4", payload=b"would-coalesce", key="grp2", created_at=T2))

    assert _payload_on_disk(journal.db_path, "evt-3") == before
    new_row = journal.read_by_id("evt-4")
    assert new_row is not None and new_row.payload == b"would-coalesce"
    markers = read_supersede_markers(journal)
    assert any(
        m.superseded_event_id == "evt-3" and m.superseded_by_event_id == "evt-4"
        for m in markers
    )


# -- T050: mixed eligibility (delivered + undelivered prior share a key) --------


def test_mixed_eligibility_coalesces_into_undelivered_never_delivered(
    journal: EventJournal, ledger: SqliteDeliveryLedger, strategy: CoalescingStrategy
) -> None:
    # delivered prior
    journal.append(_event("evt-d", payload=b"delivered", key="grp3", created_at=T1))
    ledger.record_success("evt-d", TARGET)
    delivered_before = _payload_on_disk(journal.db_path, "evt-d")
    # undelivered prior arrives -> new row + supersede(evt-d -> evt-u)
    journal.append(_event("evt-u", payload=b"undelivered", key="grp3", created_at=T2))
    # incoming coalescible event with both a delivered and an undelivered prior
    journal.append(_event("evt-x", payload=b"latest", key="grp3", created_at=T3))

    # the delivered prior is never mutated and never superseded by evt-x
    assert _payload_on_disk(journal.db_path, "evt-d") == delivered_before
    assert not any(
        m.superseded_by_event_id == "evt-x" for m in read_supersede_markers(journal)
    )
    # evt-x collapsed into the *undelivered* prior evt-u (no new row for evt-x)
    assert journal.read_by_id("evt-x") is None
    assert _payload_on_disk(journal.db_path, "evt-u") == b"latest"
    assert journal.count() == 2


# -- T048: idempotent registration ----------------------------------------------


def test_registration_is_idempotent(
    journal: EventJournal, ledger: SqliteDeliveryLedger
) -> None:
    install(ledger)
    install(ledger)  # double-install must not stack strategies

    journal.append(_event("evt-1", payload=b"original", key="grp", created_at=T1))
    ledger.record_success("evt-1", TARGET)
    journal.append(_event("evt-2", payload=b"new", key="grp", created_at=T2))

    # exactly one marker, not one-per-installed-strategy
    assert len(read_supersede_markers(journal)) == 1
    assert _payload_on_disk(journal.db_path, "evt-1") == b"original"
