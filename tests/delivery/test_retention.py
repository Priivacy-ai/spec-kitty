"""Targeted tests for WP11 ``gc_payloads`` full-delivery purge predicate (FR-005).

Pin the **observable** retention behaviour that protects re-drainability: a
payload is reclaimed only once it has reached **every known target**, never on a
single ``delivered_anywhere`` hit. These tests use real domain objects (journal +
ledger), not mocks (NFR-001), and assert on-disk journal state plus the
:meth:`SqliteDeliveryLedger.select_undelivered` drain view.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.delivery.retention import RetentionResult, gc_payloads
from specify_cli.event_journal import Event, EventJournal

pytestmark = pytest.mark.fast

TARGET_A = "target-a"
TARGET_B = "target-b"


def _event(event_id: str, *, payload: bytes = b"payload-bytes") -> Event:
    at = "2026-06-01T00:00:00+00:00"
    return Event(
        event_id=event_id,
        event_type="mission.update",
        payload=payload,
        occurred_at=at,
        created_at=at,
    )


@pytest.fixture
def journal(tmp_path: Path) -> EventJournal:
    return EventJournal(tmp_path / "event_journal" / "journal.db")


@pytest.fixture
def ledger() -> SqliteDeliveryLedger:
    return SqliteDeliveryLedger()


def test_gc_keeps_event_undelivered_to_a_known_target(
    journal: EventJournal, ledger: SqliteDeliveryLedger
) -> None:
    """E1 delivered to target-a only is NOT purged when target-b is also known.

    The payload remains the durable, re-drainable copy for target-b (FR-005):
    the journal row survives AND the event is still selectable for target-b.
    """
    journal.append(_event("E1"))
    ledger.record_success("E1", TARGET_A)  # delivered_anywhere() would be True

    result = gc_payloads(journal, ledger, known_target_ids=(TARGET_A, TARGET_B))

    assert isinstance(result, RetentionResult)
    assert "E1" in result.skipped
    assert result.purged_count == 0
    # Journal payload row kept — durability preserved for the unmet target.
    assert journal.read_by_id("E1") is not None
    # Still owed to (re-drainable for) target-b.
    assert ledger.select_undelivered(target_id=TARGET_B, event_universe=["E1"]) == ["E1"]
    # Already delivered to target-a, so not re-selected there.
    assert ledger.select_undelivered(target_id=TARGET_A, event_universe=["E1"]) == []


def test_gc_purges_event_delivered_to_all_known_targets(
    journal: EventJournal, ledger: SqliteDeliveryLedger
) -> None:
    """Once E1 has reached every known target its payload is reclaimable."""
    journal.append(_event("E1"))
    ledger.record_success("E1", TARGET_A)
    ledger.record_success("E1", TARGET_B)

    result = gc_payloads(journal, ledger, known_target_ids=(TARGET_A, TARGET_B))

    assert "E1" in result.purged
    assert result.skipped_count == 0
    assert journal.read_by_id("E1") is None
    # Ledger history/provenance survives the purge (FR-010).
    assert ledger.delivered_to_target("E1", TARGET_A) is True
    assert ledger.delivered_to_target("E1", TARGET_B) is True


def test_gc_with_no_known_targets_purges_nothing(
    journal: EventJournal, ledger: SqliteDeliveryLedger
) -> None:
    """Empty known-target universe => purge nothing, even if delivered_anywhere.

    Without a target universe the operation cannot establish full delivery, so
    the safe default is to reclaim nothing (existing callers degrade to a no-op).
    """
    journal.append(_event("E1"))
    ledger.record_success("E1", TARGET_A)
    assert ledger.delivered_anywhere("E1") is True

    result = gc_payloads(journal, ledger, known_target_ids=())

    assert "E1" in result.skipped
    assert result.purged_count == 0
    assert journal.read_by_id("E1") is not None


def test_gc_default_known_targets_is_purge_nothing(
    journal: EventJournal, ledger: SqliteDeliveryLedger
) -> None:
    """Omitting known_target_ids (None default) keeps existing callers safe."""
    journal.append(_event("E1"))
    ledger.record_success("E1", TARGET_A)

    result = gc_payloads(journal, ledger)  # no known_target_ids -> purge-nothing

    assert "E1" in result.skipped
    assert result.purged_count == 0
    assert journal.read_by_id("E1") is not None


def test_delivered_to_target_is_target_scoped(ledger: SqliteDeliveryLedger) -> None:
    """The new ledger helper is terminal-success for the exact (event, target)."""
    ledger.record_success("E1", TARGET_A)
    assert ledger.delivered_to_target("E1", TARGET_A) is True
    assert ledger.delivered_to_target("E1", TARGET_B) is False
    # A non-terminal-success row does not count as delivered.
    ledger.record_rejected("E2", TARGET_A)
    assert ledger.delivered_to_target("E2", TARGET_A) is False
