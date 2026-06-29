"""Explicit GC/archive payload retention (WP11, IC-08; FR-010, contract §3).

These are the **only** destructive payload operations in the event-sync domain
and they run **exclusively under explicit operator action** — the WP12
``sync archive`` / ``sync gc`` commands call them. They are deliberately *not*
wired into ``sync now`` or the dispatcher, so a normal capture+deliver cycle
never deletes a source payload (US4 acceptance scenario 3).

Both operations mutate only journal payload state and **never touch the delivery
ledger**, so the per-event/per-target delivery history and provenance is always
preserved (**FR-010**, contract §3: "``sync gc``/``sync archive`` are the only
destructive payload operations and preserve delivery history/provenance").

* :func:`archive_payloads` is non-destructive: it stamps the journal's archived
  marker through the WP03 public :meth:`EventJournal.mark_archived`, moving
  events off the live "retained" growth surface without deleting bytes. It is
  idempotent — an already-archived event is skipped.
* :func:`gc_payloads` is destructive: it purges (deletes) journal payload rows,
  but **only** for events already delivered somewhere
  (:meth:`SqliteDeliveryLedger.delivered_anywhere`). An undelivered event is
  skipped so the durability the spec requires (e.g. a not-yet-delivered
  Teamspace-bound payload) is never silently erased. The ledger rows survive.

Per **C-001** this module consumes the WP03 journal + WP05 ledger public
surfaces. The destructive purge writes the journal store directly using the
journal's *own* canonical schema identifiers (:mod:`specify_cli.event_journal.models`)
rather than re-deriving the table name — this module is the sanctioned
destructive owner the journal explicitly defers ``gc``/``archive`` to.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from specify_cli.event_journal.models import COL_EVENT_ID, TABLE_NAME

if TYPE_CHECKING:
    from specify_cli.delivery.ledger import SqliteDeliveryLedger
    from specify_cli.event_journal import EventJournal

# Built from the journal's own canonical identifiers; ``event_id`` always travels
# via a ``?`` placeholder, so there is no dynamic SQL and no injection surface
# (mirrors the static-identifier pattern in ``event_journal/models.py``).
_PURGE_SQL = f"DELETE FROM {TABLE_NAME} WHERE {COL_EVENT_ID} = ?"  # noqa: S608 — static module-constant identifiers; value via ?


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class RetentionResult:
    """Observable outcome of one explicit retention operation (NFR-001).

    ``archived`` / ``purged`` / ``skipped`` carry the affected event ids so WP12
    can print and tests can assert on observable results. The journal payload
    size before/after is always recorded so the bounded-growth surface stays
    visible even for an explicit operation (NFR-004).
    """

    operation: str
    archived: tuple[str, ...] = ()
    purged: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()
    journal_size_bytes_before: int = 0
    journal_size_bytes_after: int = 0

    @property
    def archived_count(self) -> int:
        return len(self.archived)

    @property
    def purged_count(self) -> int:
        return len(self.purged)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped)


def _retained_payload_bytes(journal: EventJournal) -> int:
    """Live (non-archived) payload volume — the bounded-growth surface."""
    return sum(len(event.payload) for event in journal.read_all() if event.archived_at is None)


def _total_payload_bytes(journal: EventJournal) -> int:
    """Total stored payload volume (all rows) — what GC can reclaim."""
    return sum(len(event.payload) for event in journal.read_all())


def _candidate_ids(journal: EventJournal, event_ids: Sequence[str] | None, *, live_only: bool) -> list[str]:
    """Resolve the operation's candidate event ids (explicit list, or scan)."""
    if event_ids is not None:
        return list(event_ids)
    events = journal.read_all()
    if live_only:
        return [event.event_id for event in events if event.archived_at is None]
    return [event.event_id for event in events]


def archive_payloads(journal: EventJournal, *, event_ids: Sequence[str] | None = None, at: str | None = None) -> RetentionResult:
    """Archive payloads — stamp the journal marker, delete nothing (FR-010).

    Marks each still-live candidate event archived via the WP03 public
    :meth:`EventJournal.mark_archived`. Already-archived or missing events are
    skipped, so the operation is idempotent. The delivery ledger is untouched.
    When *event_ids* is omitted, every currently-retained event is archived.
    """
    timestamp = at or _utc_now_iso()
    before = _retained_payload_bytes(journal)
    archived: list[str] = []
    skipped: list[str] = []
    for event_id in _candidate_ids(journal, event_ids, live_only=True):
        stored = journal.read_by_id(event_id)
        if stored is None or stored.archived_at is not None:
            skipped.append(event_id)
            continue
        journal.mark_archived(event_id, timestamp)
        archived.append(event_id)
    return RetentionResult(
        "archive",
        archived=tuple(archived),
        skipped=tuple(skipped),
        journal_size_bytes_before=before,
        journal_size_bytes_after=_retained_payload_bytes(journal),
    )


def gc_payloads(journal: EventJournal, ledger: SqliteDeliveryLedger, *, event_ids: Sequence[str] | None = None) -> RetentionResult:
    """Purge delivered payloads, preserve undelivered durability + ledger (FR-010).

    Deletes the journal payload row for each candidate event that has been
    delivered somewhere (:meth:`SqliteDeliveryLedger.delivered_anywhere`). An
    undelivered or missing event is skipped — its payload is the only durable
    copy and must not be erased silently. The delivery ledger is never touched,
    so history/provenance survives the purge. When *event_ids* is omitted, every
    stored event (live or archived) is a candidate.
    """
    before = _total_payload_bytes(journal)
    purged: list[str] = []
    skipped: list[str] = []
    for event_id in _candidate_ids(journal, event_ids, live_only=False):
        stored = journal.read_by_id(event_id)
        if stored is None or not ledger.delivered_anywhere(event_id):
            skipped.append(event_id)
            continue
        purged.append(event_id)
    _purge_journal_rows(journal.db_path, purged)
    return RetentionResult(
        "gc",
        purged=tuple(purged),
        skipped=tuple(skipped),
        journal_size_bytes_before=before,
        journal_size_bytes_after=_total_payload_bytes(journal),
    )


def _purge_journal_rows(db_path: Path, event_ids: Sequence[str]) -> None:
    """Delete the named journal payload rows (the sole destructive write)."""
    if not event_ids:
        return
    connection: Any = sqlite3.connect(str(db_path))
    try:
        connection.executemany(_PURGE_SQL, [(event_id,) for event_id in event_ids])
        connection.commit()
    finally:
        connection.close()


__all__ = [
    "RetentionResult",
    "archive_payloads",
    "gc_payloads",
]
