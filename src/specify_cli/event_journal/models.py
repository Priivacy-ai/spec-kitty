"""On-disk schema and in-memory record for the append-only event journal (WP03).

This module is deliberately delivery-agnostic (FR-003): the :class:`Event`
record carries *no* target/server/delivery/queue-scope field, and the journal
domain imports nothing from ``specify_cli.delivery`` (C-001). The journal stores
payload bytes keyed by the producer's canonical ``event_id`` (never rewritten,
C-005) and the diagnostic ``drain_blocked_reason`` audit set by the emit layer
(T017); it does not itself interpret delivery state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# --- table + column identity (hoisted; Sonar S1192) -----------------------

TABLE_NAME = "event_journal"

COL_EVENT_ID = "event_id"
COL_EVENT_TYPE = "event_type"
COL_PAYLOAD = "payload"
COL_OCCURRED_AT = "occurred_at"
COL_CREATED_AT = "created_at"
COL_COALESCE_KEY = "coalesce_key"
COL_ARCHIVED_AT = "archived_at"
COL_DRAIN_BLOCKED_REASON = "drain_blocked_reason"

# Canonical column order shared by INSERT params and SELECT projection so
# ``journal.py`` never hand-codes column order (T013 step 4).
ORDERED_COLUMNS: tuple[str, ...] = (
    COL_EVENT_ID,
    COL_EVENT_TYPE,
    COL_PAYLOAD,
    COL_OCCURRED_AT,
    COL_CREATED_AT,
    COL_COALESCE_KEY,
    COL_ARCHIVED_AT,
    COL_DRAIN_BLOCKED_REASON,
)

_COLUMN_LIST = ", ".join(ORDERED_COLUMNS)
_PLACEHOLDERS = ", ".join("?" for _ in ORDERED_COLUMNS)

# Idempotent DDL (T013 step 3). ``PRIMARY KEY(event_id)`` makes re-capture a
# no-op via ``INSERT OR IGNORE`` (T014) rather than a payload mutation.
CREATE_TABLE_SQL = (
    f"CREATE TABLE IF NOT EXISTS {TABLE_NAME} (\n"
    f"    {COL_EVENT_ID} TEXT PRIMARY KEY,\n"
    f"    {COL_EVENT_TYPE} TEXT NOT NULL,\n"
    f"    {COL_PAYLOAD} BLOB NOT NULL,\n"
    f"    {COL_OCCURRED_AT} TEXT NOT NULL,\n"
    f"    {COL_CREATED_AT} TEXT NOT NULL,\n"
    f"    {COL_COALESCE_KEY} TEXT,\n"
    f"    {COL_ARCHIVED_AT} TEXT,\n"
    f"    {COL_DRAIN_BLOCKED_REASON} TEXT\n"
    ")"
)

# Index for WP08's coalescing lookups and for WP11 status reads.
CREATE_COALESCE_INDEX_SQL = (
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_coalesce "
    f"ON {TABLE_NAME} ({COL_COALESCE_KEY}, {COL_CREATED_AT})"
)
CREATE_TYPE_INDEX_SQL = (
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_type_created "
    f"ON {TABLE_NAME} ({COL_EVENT_TYPE}, {COL_CREATED_AT})"
)

# Re-capture is idempotent: a duplicate ``event_id`` is ignored, never updated
# (this is the IC-02 mutation trap the journal must avoid — see T014/Risks).
#
# S608 is suppressed on the DML below for the same reason as the sibling
# ``sync/queue.py``: every interpolated token is a hardcoded module constant
# (table/column identifiers), never user input — row *values* always travel via
# ``?`` placeholders. Identifiers cannot be parameterized in SQLite, so building
# the identifier portion from constants is the correct, injection-free pattern.
INSERT_SQL = f"INSERT OR IGNORE INTO {TABLE_NAME} ({_COLUMN_LIST}) VALUES ({_PLACEHOLDERS})"  # noqa: S608 — identifiers are static module constants
SELECT_ALL_SQL = f"SELECT {_COLUMN_LIST} FROM {TABLE_NAME} ORDER BY {COL_CREATED_AT} ASC, {COL_EVENT_ID} ASC"  # noqa: S608 — identifiers are static module constants
SELECT_BY_ID_SQL = f"SELECT {_COLUMN_LIST} FROM {TABLE_NAME} WHERE {COL_EVENT_ID} = ?"  # noqa: S608 — identifiers are static module constants
SELECT_BLOCKED_SQL = f"SELECT {_COLUMN_LIST} FROM {TABLE_NAME} WHERE {COL_DRAIN_BLOCKED_REASON} IS NOT NULL ORDER BY {COL_CREATED_AT} ASC, {COL_EVENT_ID} ASC"  # noqa: S608 — identifiers are static module constants
COUNT_SQL = f"SELECT COUNT(*) FROM {TABLE_NAME}"  # noqa: S608 — identifiers are static module constants
OLDEST_CREATED_AT_SQL = f"SELECT MIN({COL_CREATED_AT}) FROM {TABLE_NAME} WHERE {COL_ARCHIVED_AT} IS NULL"  # noqa: S608 — identifiers are static module constants
MARK_ARCHIVED_SQL = f"UPDATE {TABLE_NAME} SET {COL_ARCHIVED_AT} = ? WHERE {COL_EVENT_ID} = ? AND {COL_ARCHIVED_AT} IS NULL"  # noqa: S608 — identifiers are static module constants

# --- drain-blocked reason vocabulary (closed set; T017) -------------------
#
# A blocked drain records *why* on the journal row so status (WP11) can show it
# and later delivery (WP07) can clear it. The set is closed and deterministic so
# multiple simultaneous blockers resolve to a single canonical reason rather
# than a free-form blob (T017 edge case). Only the emit-time reasons
# (saas/auth/team) are reachable in WP03; the drain-time reasons are reserved
# for WP07's dispatcher.
DRAIN_BLOCKED_SAAS_DISABLED = "saas_disabled"
DRAIN_BLOCKED_MISSING_AUTH = "missing_auth"
DRAIN_BLOCKED_MISSING_TEAM = "missing_team"
DRAIN_BLOCKED_PRIVATE_TEAMSPACE = "private_teamspace_gate"
DRAIN_BLOCKED_DAEMON_LOCK = "daemon_lock"
DRAIN_BLOCKED_NETWORK = "network_unavailable"

DRAIN_BLOCKED_REASONS: frozenset[str] = frozenset(
    {
        DRAIN_BLOCKED_SAAS_DISABLED,
        DRAIN_BLOCKED_MISSING_AUTH,
        DRAIN_BLOCKED_MISSING_TEAM,
        DRAIN_BLOCKED_PRIVATE_TEAMSPACE,
        DRAIN_BLOCKED_DAEMON_LOCK,
        DRAIN_BLOCKED_NETWORK,
    }
)


@dataclass(frozen=True)
class Event:
    """An immutable, append-only journal record.

    Deliberately delivery-agnostic (FR-003): there is no ``target``,
    ``server``, ``delivery`` or ``queue_scope`` field. ``event_id`` is the
    producer's canonical id, stored verbatim and never rewritten (C-005).
    Timestamps are timezone-aware UTC ISO-8601 strings.
    """

    event_id: str
    event_type: str
    payload: bytes
    occurred_at: str
    created_at: str
    coalesce_key: str | None = None
    archived_at: str | None = None
    drain_blocked_reason: str | None = None


def event_to_params(event: Event) -> tuple[Any, ...]:
    """Return INSERT params in :data:`ORDERED_COLUMNS` order (pure)."""
    return (
        event.event_id,
        event.event_type,
        event.payload,
        event.occurred_at,
        event.created_at,
        event.coalesce_key,
        event.archived_at,
        event.drain_blocked_reason,
    )


def row_to_event(row: tuple[Any, ...]) -> Event:
    """Reconstruct an :class:`Event` from a row in :data:`ORDERED_COLUMNS` order.

    The ``payload`` column is a SQLite BLOB; coerce to ``bytes`` so an empty
    payload round-trips as ``b""`` rather than ``None`` (T013 edge case).
    """
    payload = row[2]
    return Event(
        event_id=str(row[0]),
        event_type=str(row[1]),
        payload=bytes(payload) if payload is not None else b"",
        occurred_at=str(row[3]),
        created_at=str(row[4]),
        coalesce_key=None if row[5] is None else str(row[5]),
        archived_at=None if row[6] is None else str(row[6]),
        drain_blocked_reason=None if row[7] is None else str(row[7]),
    )


__all__ = [
    "CREATE_COALESCE_INDEX_SQL",
    "CREATE_TABLE_SQL",
    "CREATE_TYPE_INDEX_SQL",
    "COUNT_SQL",
    "DRAIN_BLOCKED_DAEMON_LOCK",
    "DRAIN_BLOCKED_MISSING_AUTH",
    "DRAIN_BLOCKED_MISSING_TEAM",
    "DRAIN_BLOCKED_NETWORK",
    "DRAIN_BLOCKED_PRIVATE_TEAMSPACE",
    "DRAIN_BLOCKED_REASONS",
    "DRAIN_BLOCKED_SAAS_DISABLED",
    "Event",
    "INSERT_SQL",
    "MARK_ARCHIVED_SQL",
    "OLDEST_CREATED_AT_SQL",
    "ORDERED_COLUMNS",
    "SELECT_ALL_SQL",
    "SELECT_BLOCKED_SQL",
    "SELECT_BY_ID_SQL",
    "TABLE_NAME",
    "event_to_params",
    "row_to_event",
]
