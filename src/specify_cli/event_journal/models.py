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

# Project identity as a *derived projection* of the envelope (#3030 FR-006).
# The authoritative identity stays in the payload; these columns exist so
# consent is evaluable in SQL instead of by decoding every row (NFR-003).
# They carry no target/receiver identity, so C-003's boundary holds: the
# journal still knows nothing about *where* an event would be delivered.
COL_PROJECT_UUID = "project_uuid"
COL_PROJECT_SLUG = "project_slug"
# Reporting only. **Never an authorization key** (operator decision 2026-07-30).
#
# This column was briefly introduced as a consent key, on the reasoning that
# machine-global consent is recorded as ``[sync.repo_defaults."<repo_slug>"]`` and
# the drain could then resolve consent without standing in the checkout. That was
# reverted: a repo slug is a *mutable git remote*, which is exactly the record FR-019
# condemns. Keying consent on it means a fresh clone, a renamed remote or a
# re-``git init``ed repo silently inherits a decision nobody made about it — and it
# broke spec.md's recorded edge case that a re-initialised repo starts non-consented.
#
# The column stays because it is genuinely useful for the WP07 per-project report
# (naming *which* repo a row came from). Consent is resolved from ``project_uuid``
# alone, down the one chain in ``sync/consent.py``. Like ``project_slug``, this value
# is derived, can collide, and must never gate delivery.
COL_REPO_SLUG = "repo_slug"

#: Columns added after the original 8-column schema shipped. ``_ensure_schema``
#: ALTERs any journal file that predates them (#3030 T010). Additive and
#: nullable only (C-001), never dropped or retyped (C-002).
IDENTITY_COLUMNS: tuple[str, ...] = (COL_PROJECT_UUID, COL_PROJECT_SLUG, COL_REPO_SLUG)

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
    COL_PROJECT_UUID,
    COL_PROJECT_SLUG,
    COL_REPO_SLUG,
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
    f"    {COL_DRAIN_BLOCKED_REASON} TEXT,\n"
    f"    {COL_PROJECT_UUID} TEXT,\n"
    f"    {COL_PROJECT_SLUG} TEXT,\n"
    f"    {COL_REPO_SLUG} TEXT\n"
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
# #3030 NFR-003: the consent predicate must be an indexed lookup, not a
# full-table payload decode. ``created_at`` trails the uuid so the filtered read
# gets its FIFO ordering from the index too.
CREATE_PROJECT_INDEX_SQL = (
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_project_created "
    f"ON {TABLE_NAME} ({COL_PROJECT_UUID}, {COL_CREATED_AT})"
)

# Backfill seams (#3030 T012). Selection is restricted to rows that have no
# stored identity yet, which is what makes a resumed run idempotent and keeps it
# from re-deriving a value the predicate already trusts.
SELECT_MISSING_IDENTITY_SQL = (
    f"SELECT {COL_EVENT_ID}, {COL_PAYLOAD} FROM {TABLE_NAME} "  # noqa: S608 — identifiers are static module constants
    f"WHERE {COL_PROJECT_UUID} IS NULL ORDER BY {COL_CREATED_AT} ASC, {COL_EVENT_ID} ASC"
)
# NFR-004 is *lossless*, so the two reporting columns are COALESCEd rather than
# assigned: an absent derived value is not a correction. Without it, a row that
# already carried a ``repo_slug`` (capture stamps it from ``event["repo_slug"]``,
# independently of T011's uuid chain, and ``sync/migrate_journal.py`` moves legacy
# rows in) had that value overwritten with NULL whenever the payload had none —
# destroying the only record of which repo the row came from, which is the column's
# entire purpose. Not a leak, since neither slug is ever an authorization key
# (FR-019); data loss, and invisible until ``_raw_snapshot`` started selecting the
# column.
#
# ``project_uuid`` is a plain assignment: the ``IS NULL`` guard in the WHERE clause
# already proves there is no stored value to preserve, and that guard is what makes
# a resumed backfill unable to change a value the selection predicate already trusts.
SET_IDENTITY_SQL = (
    f"UPDATE {TABLE_NAME} SET {COL_PROJECT_UUID} = ?, "  # noqa: S608 — identifiers are static module constants
    f"{COL_PROJECT_SLUG} = COALESCE(?, {COL_PROJECT_SLUG}), "
    f"{COL_REPO_SLUG} = COALESCE(?, {COL_REPO_SLUG}) "
    f"WHERE {COL_EVENT_ID} = ? AND {COL_PROJECT_UUID} IS NULL"
)
# T017 (#3030 FR-008/NFR-003): the project-filtered read is an **identity
# projection** — event_id, created_at, project_uuid and the blocked reason, with
# NO payload BLOB and NO LIMIT.
#
# No LIMIT is load-bearing, not an oversight. ``ledger.select_undelivered``
# fetches the full terminal-id set and slices the already-filtered universe, so
# pushing a LIMIT into this SQL would let already-delivered terminal rows fill the
# window and then be stripped by the ledger — an empty selection while consented
# undelivered rows sit behind them. That is exactly the starvation NFR-002 bans,
# and the ledger is a separate SQLite file so no join can rescue it.
#
# No payload BLOB because an unlimited read that still materialised every payload
# of a 100k-row project would satisfy NFR-003's letter and miss its point.
# Payloads are hydrated via ``read_by_ids`` over the ledger-selected batch only.
# ``project_slug`` is in the projection for #3030 T021/N1: the WP07 per-project
# report renders a project's human-readable name and, when no ``repo_slug`` was
# recorded, the slug is the ONLY name it has — grouping the unresolved-identity
# bucket without it reported nameable projects as nameless (N1-a). Deriving it from
# the payload instead would mean decoding every BLOB, the exact cost this projection
# exists to avoid. Label only: like ``repo_slug`` above it is derived, can collide,
# and never gates delivery — ``project_uuid`` remains the sole selection authority.
_IDENTITY_PROJECTION_COLUMNS = ", ".join(
    (
        COL_EVENT_ID,
        COL_CREATED_AT,
        COL_PROJECT_UUID,
        COL_PROJECT_SLUG,
        COL_REPO_SLUG,
        COL_DRAIN_BLOCKED_REASON,
    )
)


def select_identity_projection_sql(project_count: int) -> str:
    """Build FR-008's project-**filtered** identity read for *project_count* uuids.

    The filter is mandatory, and the parameter has no "all projects" spelling on
    purpose. An unfiltered variant of this statement is what shipped: the drain read
    every row of every project ordered by ``created_at`` and applied the project
    predicate in Python afterwards, which left ``CREATE_PROJECT_INDEX_SQL`` created
    and referenced by no query at all. NFR-003's stated mechanism is "indexed column
    lookup only", and an ``IN`` predicate on the index's leading column is the only
    thing that delivers it — so there is no way to ask this module for a scan.

    ``project_count`` must be >= 1. Zero consented projects is not an empty filter
    (which SQL would read as "every project"); it means there is nothing to select,
    and the caller returns early rather than issuing a query.
    """
    if project_count < 1:
        raise ValueError(
            "select_identity_projection_sql requires at least one project uuid: an "
            "empty IN-list would silently widen to every project on the machine"
        )
    placeholders = ", ".join("?" for _ in range(project_count))
    return (
        f"SELECT {_IDENTITY_PROJECTION_COLUMNS} FROM {TABLE_NAME} "  # noqa: S608 — identifiers are static module constants
        f"WHERE {COL_PROJECT_UUID} IN ({placeholders}) "
        f"ORDER BY {COL_CREATED_AT} ASC, {COL_EVENT_ID} ASC"
    )


def select_by_ids_sql(id_count: int) -> str:
    """Build a batched by-id payload read for *id_count* event ids.

    Hydration used to run ``SELECT_BY_ID_SQL`` once per event, and
    ``EventJournal._connect`` opens a **new** SQLite connection per public call — so
    a 1,000-event batch cost 1,000 connection open/closes plus 1,000 WAL pragmas.
    Batching lets one connection serve the whole batch. Row *order* is not specified
    here: SQLite is free to return an ``IN`` set in any order, so the caller
    re-imposes the ledger's selection order (see ``EventJournal.read_by_ids``).
    """
    if id_count < 1:
        raise ValueError("select_by_ids_sql requires at least one event id")
    placeholders = ", ".join("?" for _ in range(id_count))
    return (
        f"SELECT {_COLUMN_LIST} FROM {TABLE_NAME} "  # noqa: S608 — identifiers are static module constants
        f"WHERE {COL_EVENT_ID} IN ({placeholders})"
    )


# NFR-003: enumerate the *distinct* projects present without reading every row.
#
# ``SELECT DISTINCT project_uuid`` would also use the index, but SQLite has no loose
# index scan for it: it walks every index entry, so the enumeration would still be
# O(rows). This recursive formulation is the classic index skip-scan — each step is
# one ``MIN()`` seek from the previous uuid, so the whole enumeration is
# O(distinct_projects x log rows) and is what makes consent resolvable without
# touching the store. Measured on a 100k-row / 20-project journal: 0.18ms here
# versus 7.8ms for ``SELECT DISTINCT`` and 213ms for the unfiltered read it replaces.
#
# NULL is excluded: it is not a project. Rows with no stored identity are
# permanently unselectable and are counted under FR-011
# (``COUNT_MISSING_IDENTITY_SQL``), never lazily re-resolved (T018).
DISTINCT_PROJECT_UUIDS_SQL = (
    f"WITH RECURSIVE distinct_project({COL_PROJECT_UUID}) AS (\n"  # noqa: S608 — identifiers are static module constants
    f"    SELECT MIN({COL_PROJECT_UUID}) FROM {TABLE_NAME} "
    f"WHERE {COL_PROJECT_UUID} IS NOT NULL\n"
    "    UNION ALL\n"
    f"    SELECT (SELECT MIN({COL_PROJECT_UUID}) FROM {TABLE_NAME} "
    f"WHERE {COL_PROJECT_UUID} > distinct_project.{COL_PROJECT_UUID})\n"
    f"    FROM distinct_project WHERE {COL_PROJECT_UUID} IS NOT NULL\n"
    ")\n"
    f"SELECT {COL_PROJECT_UUID} FROM distinct_project "
    f"WHERE {COL_PROJECT_UUID} IS NOT NULL"
)

COUNT_MISSING_IDENTITY_SQL = (
    f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE {COL_PROJECT_UUID} IS NULL"  # noqa: S608 — identifiers are static module constants
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
    project_uuid: str | None = None
    project_slug: str | None = None
    repo_slug: str | None = None


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
        event.project_uuid,
        event.project_slug,
        event.repo_slug,
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
        project_uuid=None if row[8] is None else str(row[8]),
        project_slug=None if row[9] is None else str(row[9]),
        repo_slug=None if row[10] is None else str(row[10]),
    )


__all__ = [
    "COUNT_MISSING_IDENTITY_SQL",
    "CREATE_COALESCE_INDEX_SQL",
    "CREATE_PROJECT_INDEX_SQL",
    "CREATE_TABLE_SQL",
    "CREATE_TYPE_INDEX_SQL",
    "COUNT_SQL",
    "DISTINCT_PROJECT_UUIDS_SQL",
    "IDENTITY_COLUMNS",
    "SELECT_MISSING_IDENTITY_SQL",
    "SET_IDENTITY_SQL",
    "TABLE_NAME",
    "select_by_ids_sql",
    "select_identity_projection_sql",
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
    # ORDERED_COLUMNS is not exported: it is this module's internal INSERT/SELECT
    # column-order contract (``_COLUMN_LIST`` / ``_PLACEHOLDERS`` /
    # ``event_to_params`` / ``row_to_event`` all consume it here), and nothing
    # outside needs it. ``TABLE_NAME`` was listed twice; the duplicate is dropped.
    "SELECT_ALL_SQL",
    "SELECT_BLOCKED_SQL",
    "SELECT_BY_ID_SQL",
    "event_to_params",
    "row_to_event",
]
