"""Connection-free coalescing over the project-owned journal repository."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from kernel.clock import now_utc_iso

from .journal import CoalesceDecision, EventJournal, register_coalesce_strategy
from .models import Event


class DeliveredAnywhereQuery(Protocol):
    def delivered_anywhere(self, event_id: str) -> bool: ...


@dataclass(frozen=True, slots=True)
class SupersedeMarker:
    superseded_event_id: str
    superseded_by_event_id: str
    coalesce_key: str | None
    at: str


def read_supersede_markers(journal: EventJournal) -> list[SupersedeMarker]:
    return [SupersedeMarker(*row) for row in journal.supersede_rows()]


class CoalescingStrategy:
    """Latest-wins coalescing that never mutates a delivered payload."""

    def __init__(self, ledger: DeliveredAnywhereQuery) -> None:
        self._ledger = ledger

    def __call__(self, journal: EventJournal, event: Event) -> CoalesceDecision:
        key = event.coalesce_key
        if key is None:
            return CoalesceDecision()
        candidates = [row for row in journal.read_all() if row.coalesce_key == key]
        if not candidates:
            return CoalesceDecision()
        undelivered = [candidate for candidate in candidates if not self._ledger.delivered_anywhere(candidate.event_id)]
        if undelivered:
            journal.replace_undelivered_payload(undelivered[-1].event_id, event.payload)
            return CoalesceDecision(store_as_new=False)
        journal.record_supersede(
            candidates[-1].event_id,
            event.event_id,
            key,
            now_utc_iso(),
        )
        return CoalesceDecision()


def install(ledger: DeliveredAnywhereQuery) -> CoalescingStrategy:
    strategy = CoalescingStrategy(ledger)
    register_coalesce_strategy(strategy)
    return strategy


__all__ = [
    "CoalescingStrategy",
    "DeliveredAnywhereQuery",
    "SupersedeMarker",
    "install",
    "read_supersede_markers",
]
