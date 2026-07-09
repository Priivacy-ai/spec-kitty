"""Coalescing with delivered-event immutability (WP08, IC-02a; FR-011/NFR-002).

Re-introduces event coalescing **safely**, now that the WP05 delivery ledger can
answer "delivered anywhere?". The single hard rule (contract section 3 coalescing
bullet; FR-011): **coalescing may mutate only events that have no terminal
delivery to any target. Once an event is delivered anywhere, its payload bytes are
immutable.**

Design (the anti-spaghetti seam from plan IC-01/IC-02):

* This module **registers** a strategy into WP03's no-op seam via
  :func:`~specify_cli.event_journal.register_coalesce_strategy`; it never edits
  ``journal.py``. The journal calls the strategy inside ``append`` and hands it the
  ``(journal, event)`` pair — the strategy itself consults the delivery ledger, so
  the journal domain keeps importing nothing from ``specify_cli.delivery`` (C-001).
* Eligibility is decided **only** through the injected ledger's
  ``delivered_anywhere`` query (the authority for "is this event immutable now?").
  We do not re-query delivery state ourselves.
* :class:`CoalescingStrategy` depends on the structural :class:`DeliveredAnywhereQuery`
  Protocol — not the concrete ledger — so this module imports nothing from the
  delivery domain (C-001). The real ledger is injected at :func:`install` time.

Coalescing semantics:

* An event with ``coalesce_key is None`` is **never** coalesced — always a distinct
  row.
* When an incoming keyed event finds an **undelivered** prior sharing its key, it
  collapses (latest-wins): the undelivered prior's payload is updated in place
  (allowed — it is not yet immutable), the prior keeps its own ``event_id`` (no id
  rewrite, C-005), and the incoming event is **not** stored as a separate row.
* When every prior sharing the key is **delivered**, the incoming event becomes a
  **new** row (its own ``event_id``) and the most-recent delivered prior is marked
  ``superseded`` via a coalesce-owned sidecar table — **the prior's payload bytes
  are never touched** (FR-011, NFR-002). Supersession is metadata, not destruction:
  the prior stays inspectable and re-drainable.
* Mixed eligibility (a delivered *and* an undelivered prior share the key): the
  strategy coalesces into the most-recent undelivered prior and never the delivered
  one.

The journal exposes no non-payload marker write, so the ``superseded`` marker lives
in a dedicated, coalesce-owned ``coalesce_superseded`` sidecar table in the journal
DB (located via the journal's published ``db_path``) rather than by editing
``journal.py`` — keeping the whole feature inside this module's owned files.
"""
from __future__ import annotations

import contextlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from specify_cli.core.time_utils import now_utc_iso

from .journal import CoalesceDecision, register_coalesce_strategy
from .models import (
    COL_EVENT_ID,
    COL_PAYLOAD,
    TABLE_NAME,
)

if TYPE_CHECKING:
    from .journal import EventJournal
    from .models import Event

# --- delivery authority seam (structural; no import from specify_cli.delivery) ---


class DeliveredAnywhereQuery(Protocol):
    """The single delivery-state question coalescing needs (WP05's authority).

    A structural Protocol (not the concrete ledger) so this module — which lives in
    the journal domain — imports nothing from ``specify_cli.delivery`` (C-001). The
    real ledger is injected at :func:`install` time.
    """

    def delivered_anywhere(self, event_id: str) -> bool: ...


# --- coalesce-owned ``superseded`` sidecar (never mutates a delivered payload) ---

SUPERSEDED_TABLE = "coalesce_superseded"

_COL_SUPERSEDED = "superseded_event_id"
_COL_SUPERSEDED_BY = "superseded_by_event_id"
_COL_KEY = "coalesce_key"
_COL_AT = "at"
_SUPERSEDED_COLUMNS = (_COL_SUPERSEDED, _COL_SUPERSEDED_BY, _COL_KEY, _COL_AT)
_SUPERSEDED_COL_LIST = ", ".join(_SUPERSEDED_COLUMNS)
_SUPERSEDED_PLACEHOLDERS = ", ".join("?" for _ in _SUPERSEDED_COLUMNS)

# Every SQL constant below interpolates **only** static module/table/column
# identifiers (SQLite cannot parameterize identifiers); row *values* always travel
# via ``?`` placeholders. This is the same injection-free pattern the sibling
# ``event_journal/models.py`` documents — the per-line S608 suppression marks each
# DML f-string where bandit's heuristic is a false positive here.
_CREATE_SUPERSEDED_SQL = (
    f"CREATE TABLE IF NOT EXISTS {SUPERSEDED_TABLE} (\n"
    f"    {_COL_SUPERSEDED} TEXT NOT NULL,\n"
    f"    {_COL_SUPERSEDED_BY} TEXT NOT NULL,\n"
    f"    {_COL_KEY} TEXT,\n"
    f"    {_COL_AT} TEXT NOT NULL,\n"
    f"    PRIMARY KEY ({_COL_SUPERSEDED}, {_COL_SUPERSEDED_BY})\n"
    ")"
)
_INSERT_SUPERSEDED_SQL = (
    f"INSERT OR IGNORE INTO {SUPERSEDED_TABLE} ({_SUPERSEDED_COL_LIST}) "  # noqa: S608 — static identifiers; values via ? placeholders
    f"VALUES ({_SUPERSEDED_PLACEHOLDERS})"
)
_SELECT_SUPERSEDED_SQL = (
    f"SELECT {_SUPERSEDED_COL_LIST} FROM {SUPERSEDED_TABLE} "  # noqa: S608 — static identifiers; values via ? placeholders
    f"ORDER BY {_COL_AT} ASC, {_COL_SUPERSEDED} ASC"
)
# The journal exposes no payload-update method; collapsing an *undelivered* row is a
# direct UPDATE on the journal table (only ever called for events the strategy has
# classified undelivered, so a delivered payload is never written — FR-011).
_UPDATE_PAYLOAD_SQL = (
    f"UPDATE {TABLE_NAME} SET {COL_PAYLOAD} = ? WHERE {COL_EVENT_ID} = ?"  # noqa: S608 — static identifiers; values via ? placeholders
)


@dataclass(frozen=True)
class SupersedeMarker:
    """A ``prior -> successor`` supersession link (metadata, not a payload write)."""

    superseded_event_id: str
    superseded_by_event_id: str
    coalesce_key: str | None
    at: str


def _connect(db_path: Path) -> sqlite3.Connection:
    """Open a connection to the journal DB and ensure the sidecar schema exists."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    with contextlib.suppress(sqlite3.DatabaseError):
        conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(_CREATE_SUPERSEDED_SQL)
    conn.commit()
    return conn


def _candidates(journal: EventJournal, coalesce_key: str) -> list[Event]:
    """Prior journal events sharing *coalesce_key*, oldest-first (read-only).

    Uses the journal's public ``read_all`` read API (ordered ``created_at`` ASC,
    ``event_id`` ASC) so the newest candidate is last — keeping candidate discovery
    decoupled from the journal's internals.
    """
    return [event for event in journal.read_all() if event.coalesce_key == coalesce_key]


def _collapse_into(db_path: Path, target_event_id: str, payload: bytes) -> None:
    """Latest-wins collapse: write *payload* onto an **undelivered** prior row.

    Called only for an event the strategy has classified as undelivered, so this
    never touches a delivered (immutable) payload. The prior keeps its ``event_id``
    (no id rewrite, C-005); the incoming event is not stored as a separate row.
    """
    with contextlib.closing(_connect(db_path)) as conn:
        conn.execute(_UPDATE_PAYLOAD_SQL, (payload, target_event_id))
        conn.commit()


def _record_supersede(
    db_path: Path,
    superseded_event_id: str,
    superseded_by_event_id: str,
    coalesce_key: str,
) -> None:
    """Record a ``prior -> successor`` marker without mutating the prior payload."""
    with contextlib.closing(_connect(db_path)) as conn:
        conn.execute(
            _INSERT_SUPERSEDED_SQL,
            (superseded_event_id, superseded_by_event_id, coalesce_key, now_utc_iso()),
        )
        conn.commit()


def read_supersede_markers(journal: EventJournal) -> list[SupersedeMarker]:
    """Return all ``superseded`` markers recorded for *journal*, oldest-first."""
    with contextlib.closing(_connect(journal.db_path)) as conn:
        rows = conn.execute(_SELECT_SUPERSEDED_SQL).fetchall()
    return [
        SupersedeMarker(
            superseded_event_id=str(row[0]),
            superseded_by_event_id=str(row[1]),
            coalesce_key=None if row[2] is None else str(row[2]),
            at=str(row[3]),
        )
        for row in rows
    ]


class CoalescingStrategy:
    """The WP08 coalescing strategy plugged into WP03's seam.

    Holds the injected delivery authority (:class:`DeliveredAnywhereQuery`) and is
    invoked as ``strategy(journal, event)`` by ``EventJournal.append``. Returns a
    :class:`~specify_cli.event_journal.CoalesceDecision`; any coalescing side effect
    (collapsing an undelivered prior, or recording a ``superseded`` marker) is
    performed here before the journal decides whether to store the incoming row.
    """

    def __init__(self, ledger: DeliveredAnywhereQuery) -> None:
        self._ledger = ledger

    def __call__(self, journal: EventJournal, event: Event) -> CoalesceDecision:
        key = event.coalesce_key
        if key is None:
            return CoalesceDecision(store_as_new=True)
        candidates = _candidates(journal, key)
        if not candidates:
            return CoalesceDecision(store_as_new=True)
        undelivered = [
            candidate
            for candidate in candidates
            if not self._ledger.delivered_anywhere(candidate.event_id)
        ]
        if undelivered:
            # Coalesce into the most-recent undelivered prior (deterministic: newest
            # by created_at). Never coalesces into a delivered prior (FR-011).
            _collapse_into(journal.db_path, undelivered[-1].event_id, event.payload)
            return CoalesceDecision(store_as_new=False)
        # Every prior is delivered: the incoming event becomes a new row and the
        # most-recent delivered prior is superseded (its payload is never touched).
        _record_supersede(journal.db_path, candidates[-1].event_id, event.event_id, key)
        return CoalesceDecision(store_as_new=True)


def install(ledger: DeliveredAnywhereQuery) -> CoalescingStrategy:
    """Register a :class:`CoalescingStrategy` bound to *ledger* into WP03's seam.

    Idempotent / re-entrant safe: the seam stores a single strategy reference, so a
    double-install replaces rather than stacks (a double-import never doubles the
    coalescing effect). Returns the installed strategy for inspection/teardown.
    """
    strategy = CoalescingStrategy(ledger)
    register_coalesce_strategy(strategy)
    return strategy


__all__ = [
    "CoalescingStrategy",
    "DeliveredAnywhereQuery",
    "SUPERSEDED_TABLE",
    "SupersedeMarker",
    "install",
    "read_supersede_markers",
]
