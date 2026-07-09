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
  but **only** for events already delivered to **all known targets**
  (:meth:`SqliteDeliveryLedger.delivered_to_target` for every known target id).
  An event still owed to any not-yet-delivered target is skipped so its payload
  — the only durable copy re-drainable to that target (FR-005) — is never
  silently erased. When no known targets are supplied the operation purges
  nothing (it cannot establish full delivery), and the ledger rows always
  survive.

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
from pathlib import Path
from typing import TYPE_CHECKING, Any

from specify_cli.core.time_utils import now_utc_iso
from specify_cli.event_journal.models import COL_EVENT_ID, TABLE_NAME

if TYPE_CHECKING:
    from specify_cli.delivery.ledger import SqliteDeliveryLedger
    from specify_cli.event_journal import EventJournal

# Built from the journal's own canonical identifiers; ``event_id`` always travels
# via a ``?`` placeholder, so there is no dynamic SQL and no injection surface
# (mirrors the static-identifier pattern in ``event_journal/models.py``).
_PURGE_SQL = f"DELETE FROM {TABLE_NAME} WHERE {COL_EVENT_ID} = ?"  # noqa: S608 — static module-constant identifiers; value via ?


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
    timestamp = at or now_utc_iso()
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


def _delivered_to_all_known_targets(
    ledger: SqliteDeliveryLedger,
    event_id: str,
    known_target_ids: Sequence[str] | None,
) -> bool:
    """Whether *event_id* reached **every** known target (the purge predicate).

    Returns ``False`` (purge-nothing safe default) when *known_target_ids* is
    falsy/empty: with no target universe the operation cannot establish full
    delivery, so it must not erase a payload that may still be owed to an
    unknown target. Otherwise the event must have a terminal-success delivery to
    every known target before its payload can be reclaimed (FR-005).
    """
    if not known_target_ids:
        return False
    return all(ledger.delivered_to_target(event_id, target_id) for target_id in known_target_ids)


def gc_payloads(
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    *,
    event_ids: Sequence[str] | None = None,
    known_target_ids: Sequence[str] | None = None,
) -> RetentionResult:
    """Purge fully-delivered payloads, preserve re-drainable durability + ledger (FR-010).

    Deletes the journal payload row for each candidate event **only** once it has
    a terminal-success delivery to every id in *known_target_ids*
    (:meth:`SqliteDeliveryLedger.delivered_to_target`). An event still owed to any
    not-yet-delivered known target is skipped — its payload is the only durable
    copy re-drainable to that target and must not be erased silently (FR-005). A
    missing event is likewise skipped. When *known_target_ids* is falsy/empty the
    operation purges nothing (it cannot establish full delivery — a safe default
    so existing callers degrade to purge-nothing). The delivery ledger is never
    touched, so history/provenance survives the purge. When *event_ids* is
    omitted, every stored event (live or archived) is a candidate.
    """
    before = _total_payload_bytes(journal)
    purged: list[str] = []
    skipped: list[str] = []
    for event_id in _candidate_ids(journal, event_ids, live_only=False):
        stored = journal.read_by_id(event_id)
        if stored is None or not _delivered_to_all_known_targets(ledger, event_id, known_target_ids):
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
