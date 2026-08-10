"""Append-only event journal — the WP03 authoritative surface.

The journal is a durable, **producer-scoped** (user|team / repo-local), local
payload store that does **not** know delivery state (FR-003, C-001):

* It **never deletes** a payload on the normal path (FR-001, contract §3). The
  only mutation is :meth:`EventJournal.mark_archived`, which sets a marker and
  removes nothing; ``sync gc``/``archive`` (WP11) own destructive operations.
* Re-capturing the same ``event_id`` is idempotent (``INSERT OR IGNORE``) and
  never mutates stored bytes — the IC-02 trap the old ``queue.py`` fell into.
* It exposes a **no-op coalescing seam** (:func:`register_coalesce_strategy`)
  so WP08 can register a real strategy **without editing this module**. With no
  strategy registered every produced event is a distinct row (plan IC-02).
* :func:`capture_teamspace_bound` is the capture-first writer the emit layer
  calls: it records the fact (with a classified ``drain_blocked_reason``)
  *before* any delivery gate decides whether delivery may proceed (FR-017,
  contract §2). It refuses to silently drop a Teamspace-bound family (C-008).

This module imports nothing from ``specify_cli.delivery`` (FR-003, C-001).
"""
from __future__ import annotations

import contextlib
import sqlite3
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from kernel.clock import now_utc_iso
from specify_cli.paths import get_runtime_root

from .models import (
    COUNT_MISSING_IDENTITY_SQL,
    COUNT_SQL,
    CREATE_COALESCE_INDEX_SQL,
    CREATE_PROJECT_INDEX_SQL,
    CREATE_TABLE_SQL,
    CREATE_TYPE_INDEX_SQL,
    DISTINCT_PROJECT_UUIDS_SQL,
    DRAIN_BLOCKED_MISSING_AUTH,
    DRAIN_BLOCKED_MISSING_TEAM,
    DRAIN_BLOCKED_SAAS_DISABLED,
    IDENTITY_COLUMNS,
    INSERT_SQL,
    MARK_ARCHIVED_SQL,
    OLDEST_CREATED_AT_SQL,
    SELECT_ALL_SQL,
    SELECT_BLOCKED_SQL,
    SELECT_BY_ID_SQL,
    SELECT_IDENTITY_PROJECTION_ALL_SQL,
    SELECT_MISSING_IDENTITY_SQL,
    SET_IDENTITY_SQL,
    TABLE_NAME,
    Event,
    event_to_params,
    row_to_event,
    select_by_ids_sql,
    select_identity_projection_sql,
)

#: Max ``?`` placeholders per statement. SQLite's compiled ceiling is 999 on older
#: builds and 32,766 from 3.32; batching well under the lower bound keeps a wide
#: drain working on any interpreter that ships with the CLI, at the cost of one
#: extra statement per 500 events — still O(batch/500) rather than O(batch)
#: connections, which is the property NFR-003 needs.
_MAX_SQL_VARIABLES = 500

# --- producer-scoped path resolution (NEVER server-scoped) ----------------

JOURNAL_SUBDIR = "event_journal"
ANONYMOUS_PRODUCER = "local"
_SAFE_TOKEN_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789._-")
_MAX_TOKEN_LEN = 64


def _producer_token(user_id: str | None, team_slug: str | None) -> str:
    """Derive a filesystem-safe token from producer identity only.

    Scope is keyed on ``user_id``/``team_slug`` — **never** on a server URL or
    ``derived_queue_scope`` (those belong to the delivery side, WP04/WP05). When
    identity is unknown the journal falls back to a producer-anonymous local
    token so capture never blocks on identity (FR-017).
    """
    user = (user_id or "").strip().lower()
    team = (team_slug or "").strip().lower()
    if not user and not team:
        return ANONYMOUS_PRODUCER
    raw = f"{user}|{team}"
    safe = "".join(ch if ch in _SAFE_TOKEN_CHARS else "_" for ch in raw)
    safe = safe[:_MAX_TOKEN_LEN].strip("_")
    return safe or ANONYMOUS_PRODUCER


def resolve_journal_path(
    *, user_id: str | None = None, team_slug: str | None = None
) -> Path:
    """Resolve the producer-scoped journal DB path under the spec-kitty home.

    Honours ``SPEC_KITTY_HOME`` via :func:`get_runtime_root`. ``get_runtime_root``
    is typed ``Any`` here (mypy ``follow_imports=skip`` for ``specify_cli.*``);
    coerce at the typed boundary.
    """
    base: Path = get_runtime_root().base
    token = _producer_token(user_id, team_slug)
    return base / JOURNAL_SUBDIR / f"journal-{token}.db"


# --- coalescing seam (default no-op; WP08 fills via registration) ---------


@dataclass(frozen=True)
class CoalesceDecision:
    """A coalescing strategy's decision for a single produced event.

    ``store_as_new`` True (the default) stores the event as a distinct row.
    WP08 may extend this contract; the registration API is the stable seam.
    """

    store_as_new: bool = True


class CoalesceStrategy(Protocol):
    """Pluggable coalescing hook called inside :meth:`EventJournal.append`.

    WP08 registers a real strategy via :func:`register_coalesce_strategy` and
    consults the delivery ledger *itself* — the journal hands the strategy the
    ``(journal, event)`` pair but never imports ``delivery`` (FR-003, C-001).
    """

    def __call__(self, journal: EventJournal, event: Event) -> CoalesceDecision: ...


def _no_op_coalesce(journal: EventJournal, event: Event) -> CoalesceDecision:
    """Default strategy: store every produced event as a distinct row (IC-02)."""
    del journal, event
    return CoalesceDecision(store_as_new=True)


_active_coalesce_strategy: CoalesceStrategy = _no_op_coalesce


def register_coalesce_strategy(strategy: CoalesceStrategy) -> None:
    """Register the active coalescing strategy (the only contract WP08 needs)."""
    global _active_coalesce_strategy
    _active_coalesce_strategy = strategy


def reset_coalesce_strategy() -> None:
    """Restore the default no-op strategy (test isolation / teardown)."""
    global _active_coalesce_strategy
    _active_coalesce_strategy = _no_op_coalesce


# --- deferred (transactional) append seam ---------------------------------


class JournalTransaction:
    """A deferred, single-transaction view over the journal.

    Unlike :meth:`EventJournal.append` (which autocommits each row), appends
    here are **staged** on one open connection and are *not* committed per row;
    the caller commits the whole batch exactly once via :meth:`commit` (or
    discards it via :meth:`rollback`). This lets a multi-step writer keep a
    journal batch and an *external* store (e.g. the migration provenance audit)
    all-or-nothing: stage everything, then commit both — or roll both back so a
    downstream failure can never leave an orphan committed journal row.

    :meth:`read_by_id` reads through the *same* connection, so within-batch
    dedupe sees staged-but-uncommitted rows. The coalescing seam is intentionally
    bypassed: callers of the deferred path own their own dedupe semantics.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._committed = False

    @property
    def committed(self) -> bool:
        return self._committed

    def append(self, event: Event) -> None:
        """Stage one append (``INSERT OR IGNORE``) without committing."""
        self._conn.execute(INSERT_SQL, event_to_params(event))

    def read_by_id(self, event_id: str) -> Event | None:
        """Read an event, seeing this transaction's staged-but-uncommitted rows."""
        rows = self._conn.execute(SELECT_BY_ID_SQL, (event_id,)).fetchall()
        return row_to_event(rows[0]) if rows else None

    def commit(self) -> None:
        """Durably commit every staged append as a single transaction."""
        self._conn.commit()
        self._committed = True

    def rollback(self) -> None:
        """Discard every staged (uncommitted) append in this transaction."""
        self._conn.rollback()
        self._committed = False


# --- the append-only store ------------------------------------------------


@dataclass(frozen=True)
class EventIdentityRow:
    """One journal row's identity, with no payload attached (#3030 T017).

    The unit the consent predicate operates on. Carrying no payload is what makes
    an unlimited universe read cheap enough for NFR-003.
    """

    event_id: str
    created_at: str
    project_uuid: str | None
    repo_slug: str | None
    drain_blocked_reason: str | None
    # Label only, added for #3030 T021's operator report. Defaulted so the field
    # order stays stable for existing keyword constructions; selection never reads
    # it — ``project_uuid`` is the sole authority (delivery/selection.py).
    project_slug: str | None = None


class EventJournal:
    """SQLite-backed, append-only, producer-scoped payload store."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._ensure_schema()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db_path))
        # WAL improves concurrent-writer behaviour (two processes on one repo);
        # it is a best-effort optimisation, so a filesystem that rejects it
        # must not break capture.
        with contextlib.suppress(sqlite3.DatabaseError):
            conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _ensure_schema(self) -> None:
        with contextlib.closing(self._connect()) as conn:
            conn.execute(CREATE_TABLE_SQL)
            # #3030 T010: must run BEFORE any statement derived from
            # ``_COLUMN_LIST``. ``CREATE TABLE IF NOT EXISTS`` is a no-op on an
            # existing file, so without this every journal written before the
            # identity columns existed would raise ``no such column`` on the
            # first read.
            self._migrate_add_identity_columns(conn)
            conn.execute(CREATE_COALESCE_INDEX_SQL)
            conn.execute(CREATE_TYPE_INDEX_SQL)
            conn.execute(CREATE_PROJECT_INDEX_SQL)
            conn.commit()

    @staticmethod
    def _migrate_add_identity_columns(conn: sqlite3.Connection) -> None:
        """Add the project-identity columns to journals that predate them.

        Additive and idempotent, mirroring the in-repo precedent at
        ``sync/queue.py`` (``PRAGMA table_info`` → ``ALTER TABLE … ADD COLUMN``).
        Nothing is dropped, retyped or rewritten, so an older CLI keeps reading
        and writing the same file (C-001, C-002).

        Lives inside ``_ensure_schema`` deliberately: that runs unconditionally
        on construction, so ``get_journal``'s instance cache cannot skip it.
        """
        existing = {
            row[1] for row in conn.execute(f"PRAGMA table_info({TABLE_NAME})")
        }
        for column in IDENTITY_COLUMNS:
            if column not in existing:
                conn.execute(f"ALTER TABLE {TABLE_NAME} ADD COLUMN {column} TEXT")  # noqa: S608 - identifiers are module constants, not input
        conn.commit()

    def iter_rows_missing_identity(self) -> list[tuple[str, bytes]]:
        """Return ``(event_id, payload)`` for rows with no stored identity yet.

        Storage-level seam for the #3030 T012 backfill. The journal deliberately
        does not resolve identity itself — that chain lives in
        ``sync/project_identity.py`` and the journal must stay ignorant of
        consent policy (C-003). Restricting to ``project_uuid IS NULL`` is what
        makes a resumed backfill idempotent.
        """
        with contextlib.closing(self._connect()) as conn:
            return [
                (str(event_id), bytes(payload) if payload is not None else b"")
                for event_id, payload in conn.execute(SELECT_MISSING_IDENTITY_SQL)
            ]

    def set_project_identity(
        self, entries: list[tuple[str, str | None, str | None, str | None]]
    ) -> int:
        """Write resolved identity for *entries* as one transaction.

        Each entry is ``(event_id, project_uuid, project_slug, repo_slug)`` and the
        write sets all three identity columns. Returns the number of rows actually
        updated. Only ever fills a NULL uuid — ``SET_IDENTITY_SQL``'s
        ``project_uuid IS NULL`` guard means an already-identified row is never
        rewritten, so a re-run cannot change a value the selection predicate already
        trusts. Nothing *outside the three identity columns* is touched (NFR-004),
        and no row is ever deleted (C-002).

        Batched deliberately: a per-row commit over a 42-day history would be
        thousands of fsyncs, and a partial run must leave every remaining row
        NULL — i.e. unselectable — rather than *appearing* consented.
        """
        if not entries:
            return 0
        with contextlib.closing(self._connect()) as conn:
            cursor = conn.executemany(
                SET_IDENTITY_SQL,
                [
                    (uuid, slug, repo, event_id)
                    for event_id, uuid, slug, repo in entries
                ],
            )
            updated = cursor.rowcount
            conn.commit()
        return max(updated, 0)

    def count_missing_identity(self) -> int:
        """Count rows with no resolvable project identity (#3030 T013/FR-011).

        These are permanently unselectable by the consent predicate, so the
        count is what makes fail-closed denial observable instead of silent
        data loss. WP07 surfaces it.
        """
        with contextlib.closing(self._connect()) as conn:
            row = conn.execute(COUNT_MISSING_IDENTITY_SQL).fetchone()
        return int(row[0]) if row else 0

    def distinct_project_uuids(self) -> list[str]:
        """Return the distinct non-NULL ``project_uuid`` values present, ascending.

        The cheap half of FR-008's read: consent must be resolved before a project
        filter can be applied, so the drain first needs to know *which* projects the
        store holds. ``DISTINCT_PROJECT_UUIDS_SQL`` answers that with one index seek
        per distinct project rather than a walk over every row, so the answer costs
        O(projects x log rows) — this is the read that keeps NFR-003's promise
        independent of store size.

        NULL is not a project and is excluded. Such rows are permanently
        unselectable and are reported through :meth:`count_missing_identity`
        (FR-011), never re-resolved at selection time (T018).
        """
        with contextlib.closing(self._connect()) as conn:
            return [str(row[0]) for row in conn.execute(DISTINCT_PROJECT_UUIDS_SQL)]

    def read_identity_projection_for_report(self) -> list[EventIdentityRow]:
        """EVERY row's identity, unfiltered — operator REPORTING only (#3030 T021).

        Deliberately a separate method from :meth:`read_identity_projection`, whose
        ``project_uuids`` filter is mandatory. That filter still cannot be
        *parameterised* into a scan — no argument widens it — and the two statements
        share only their column list, so editing one predicate cannot silently change
        the other.

        What this method does weaken is the **capability removal**. Before it existed,
        an unfiltered read was unwritable; now it is one substituted call. Keeping it
        out of the drain is therefore **convention, not structure** — the convention
        held six hours in practice (a second, non-reporting consumer landed the same
        day), which is why `tests/architectural/` carries a guard on this symbol.
        NFR-001's structural fence is `ConsentedBatch`: a receiver cannot be handed
        events without a resolved consent answer, so even a scanning drain cannot
        deliver an unconsented row.

        FR-015/SC-004 asks a question the filtered read cannot answer at any
        parameterisation — "whose data is in this store?". The projects to name are the
        ones not yet known to consent, so the uuid set cannot be supplied up front, and
        the rows whose ``project_uuid`` IS NULL (FR-011's fail-closed denials, which the
        WP07 report must surface rather than drop) are excluded from
        ``distinct_project_uuids`` by definition.

        Cost is bounded by call site: once per explicit ``sync doctor`` / ``sync
        status`` / ``sync migrate``, never on a drain tick. No payload BLOB is read
        here either, so the cost is a projection scan rather than a materialisation.
        """
        with contextlib.closing(self._connect()) as conn:
            return [
                EventIdentityRow(
                    event_id=str(row[0]),
                    created_at=str(row[1]),
                    project_uuid=None if row[2] is None else str(row[2]),
                    project_slug=None if row[3] is None else str(row[3]),
                    repo_slug=None if row[4] is None else str(row[4]),
                    drain_blocked_reason=None if row[5] is None else str(row[5]),
                )
                for row in conn.execute(SELECT_IDENTITY_PROJECTION_ALL_SQL)
            ]

    def read_identity_projection(
        self, *, project_uuids: Sequence[str]
    ) -> list[EventIdentityRow]:
        """Return the identity of every row belonging to *project_uuids* (T017).

        FR-008's project-filtered universe read, and the only query in the journal
        with a ``project_uuid`` predicate — i.e. the only reason
        ``CREATE_PROJECT_INDEX_SQL`` exists. No payload BLOB is decoded and **no
        LIMIT** is applied; both properties are load-bearing and are explained on
        :func:`~specify_cli.event_journal.models.select_identity_projection_sql`.

        *project_uuids* is required. The predecessor took no filter at all — it read
        every row of every project ``ORDER BY created_at`` and left the caller to
        filter in Python, which is how a 100k-row journal cost a full scan plus a
        sort per drain batch while the index went unused. An empty sequence returns
        ``[]`` without querying: no consenting project means nothing to select, and
        an empty ``IN`` list would read as "every project".
        """
        uuids = [uuid for uuid in project_uuids if uuid]
        if not uuids:
            return []
        with contextlib.closing(self._connect()) as conn:
            return [
                EventIdentityRow(
                    event_id=str(row[0]),
                    created_at=str(row[1]),
                    project_uuid=None if row[2] is None else str(row[2]),
                    project_slug=None if row[3] is None else str(row[3]),
                    repo_slug=None if row[4] is None else str(row[4]),
                    drain_blocked_reason=None if row[5] is None else str(row[5]),
                )
                for row in conn.execute(
                    select_identity_projection_sql(len(uuids)), tuple(uuids)
                )
            ]

    def append(self, event: Event) -> None:
        """Append an event as a distinct row (idempotent on ``event_id``).

        The coalescing seam runs first; with the default no-op strategy it
        always proceeds to a plain ``INSERT OR IGNORE``. A strategy that raises
        propagates *before* any write, so the journal is never partially
        mutated (T015 edge case). Re-appending an existing ``event_id`` is a
        no-op — stored bytes are never updated (FR-001 / IC-02).
        """
        decision = _active_coalesce_strategy(self, event)
        if not decision.store_as_new:
            return
        with contextlib.closing(self._connect()) as conn:
            conn.execute(INSERT_SQL, event_to_params(event))
            conn.commit()

    def record(self, event: Event) -> None:
        """Alias of :meth:`append` (capture-first ergonomics)."""
        self.append(event)

    @contextlib.contextmanager
    def transaction(self) -> Iterator[JournalTransaction]:
        """Open a deferred, commit-once append batch over the journal.

        Yields a :class:`JournalTransaction` whose appends are staged on a single
        open connection. The caller must call :meth:`JournalTransaction.commit`
        to persist the batch; if the block exits (normally or via an exception)
        without an explicit commit, every staged append is rolled back. This is
        the only path that does *not* autocommit per row, so a multi-store writer
        can keep the journal batch all-or-nothing with an external store and never
        leave an orphan committed journal row on a downstream failure.
        """
        conn = self._connect()
        txn = JournalTransaction(conn)
        try:
            yield txn
        finally:
            if not txn.committed:
                with contextlib.suppress(sqlite3.Error):
                    conn.rollback()
            conn.close()

    def read_all(self) -> list[Event]:
        with contextlib.closing(self._connect()) as conn:
            rows = conn.execute(SELECT_ALL_SQL).fetchall()
        return [row_to_event(row) for row in rows]

    def read_by_id(self, event_id: str) -> Event | None:
        with contextlib.closing(self._connect()) as conn:
            rows = conn.execute(SELECT_BY_ID_SQL, (event_id,)).fetchall()
        return row_to_event(rows[0]) if rows else None

    def read_by_ids(self, event_ids: Sequence[str]) -> list[Event]:
        """Read many events over **one** connection, in the order requested.

        The drain's payload-hydration seam (NFR-003). Hydration used to call
        :meth:`read_by_id` per event and :meth:`_connect` opens a fresh SQLite
        connection — with its own WAL pragma — on every public call, so a
        1,000-event batch cost 1,000 connection open/closes. Here the whole batch
        shares one connection and one statement per 500 ids.

        Ids absent from the store are simply missing from the result; the caller
        does not have to reconcile a ``None`` per event. Order follows *event_ids*,
        not SQLite's ``IN``-set order, because the ledger's selection order is what
        makes a drain reproducible and FIFO.
        """
        wanted = list(event_ids)
        if not wanted:
            return []
        found: dict[str, Event] = {}
        with contextlib.closing(self._connect()) as conn:
            for start in range(0, len(wanted), _MAX_SQL_VARIABLES):
                chunk = wanted[start : start + _MAX_SQL_VARIABLES]
                for row in conn.execute(select_by_ids_sql(len(chunk)), tuple(chunk)):
                    event = row_to_event(row)
                    found[event.event_id] = event
        return [found[event_id] for event_id in wanted if event_id in found]

    def read_blocked(self) -> list[Event]:
        """Return rows carrying a ``drain_blocked_reason`` (WP11 diagnostics)."""
        with contextlib.closing(self._connect()) as conn:
            rows = conn.execute(SELECT_BLOCKED_SQL).fetchall()
        return [row_to_event(row) for row in rows]

    def count(self) -> int:
        with contextlib.closing(self._connect()) as conn:
            row = conn.execute(COUNT_SQL).fetchone()
        return int(row[0]) if row else 0

    def oldest_created_at(self) -> str | None:
        """Oldest ``created_at`` among live (non-archived) rows, or ``None``."""
        with contextlib.closing(self._connect()) as conn:
            row = conn.execute(OLDEST_CREATED_AT_SQL).fetchone()
        return str(row[0]) if row and row[0] is not None else None

    def mark_archived(self, event_id: str, at: str) -> None:
        """Set the ``archived_at`` marker (no row removal).

        This is the **only** mutation the journal exposes and is deliberately
        kept out of the capture/append path. Destructive ``gc``/``archive``
        semantics are owned by WP11; this just stamps the marker (FR-001).
        """
        with contextlib.closing(self._connect()) as conn:
            conn.execute(MARK_ARCHIVED_SQL, (at, event_id))
            conn.commit()


# --- journal factory (producer-scoped, lightly cached) --------------------

_JOURNAL_CACHE: dict[str, EventJournal] = {}


def get_journal(
    *, user_id: str | None = None, team_slug: str | None = None
) -> EventJournal:
    """Return the producer-scoped journal, reusing a cached instance per path."""
    path = resolve_journal_path(user_id=user_id, team_slug=team_slug)
    key = str(path)
    journal = _JOURNAL_CACHE.get(key)
    if journal is None:
        journal = EventJournal(path)
        _JOURNAL_CACHE[key] = journal
    return journal


def reset_journal_cache() -> None:
    """Clear the journal-instance cache (test isolation across homes)."""
    _JOURNAL_CACHE.clear()


# --- capture-first orchestration (called from the emit layer) -------------


@dataclass(frozen=True)
class CaptureGateState:
    """A point-in-time snapshot of the drain gates the emit layer evaluated.

    The journal stores the *classified* reason but does not itself read auth,
    sync flags, or the network — the emit layer evaluates the gates and passes
    the result in, keeping the journal free of delivery/auth coupling (C-001).
    """

    saas_enabled: bool
    checkout_enabled: bool
    authenticated: bool
    team_slug: str | None


def classify_drain_blocked_reason(gate: CaptureGateState) -> str | None:
    """Map gate state to a single canonical ``drain_blocked_reason`` (T017).

    Precedence is coarse-gate-first so an operator sees the root cause
    (the checkout is opted out) rather than a downstream symptom. Returns
    ``None`` when the event is ready to drain.
    """
    if not gate.saas_enabled or not gate.checkout_enabled:
        return DRAIN_BLOCKED_SAAS_DISABLED
    if not gate.authenticated:
        return DRAIN_BLOCKED_MISSING_AUTH
    if gate.team_slug is None:
        return DRAIN_BLOCKED_MISSING_TEAM
    return None


class TeamspaceBoundDropError(RuntimeError):
    """Raised when a Teamspace-bound family is asked to skip the journal write.

    Enforces C-008: such a fact is never silently dropped. Full OPT_OUT/TRASH
    classification (local-only vs Teamspace-bound vs discardable) is WP09's
    responsibility; WP03 only guarantees the Teamspace-bound write happens.
    """

    def __init__(self, *, event_id: str) -> None:
        super().__init__(
            f"Refusing to silently drop Teamspace-bound event {event_id!r}: "
            "capture-first requires a durable journal write (C-008)."
        )
        self.event_id = event_id


def capture_teamspace_bound(
    *,
    journal: EventJournal,
    event_id: str,
    event_type: str,
    payload: bytes,
    occurred_at: str,
    gate: CaptureGateState,
    coalesce_key: str | None = None,
    is_teamspace_bound: bool = True,
    skip_journal: bool = False,
    created_at: str | None = None,
    project_uuid: str | None = None,
    project_slug: str | None = None,
    repo_slug: str | None = None,
) -> Event:
    """Durably capture a Teamspace-bound fact *before* the delivery gates.

    For every event that reaches this function the write is unconditional:
    ``gate`` decides only the recorded ``drain_blocked_reason`` (delivery
    eligibility), never whether the write happens (FR-017, contract §2). A
    request to skip the write for a Teamspace-bound family fails loudly
    (C-008, T018).

    **Amended 2026-07-29 (#3030 NFR-005, operator decision).** "Unconditional"
    is now scoped to events that get here. Whether a capture happens at all is
    decided *upstream* by per-project consent: ``EventEmitter._capture_to_journal``
    (``sync/emitter.py``) refuses to call this function when the checkout has
    not consented, so a non-consenting project's events never reach the journal.
    Capture-first durability therefore applies to consenting projects only.

    This deliberately reverses the original contract, which held that a
    Teamspace-bound fact must survive even when every gate blocks. The reason:
    that invariant made the journal a machine-global pool of every local
    project's payloads, and one consenting checkout shipped the lot (the
    2026-07-27 incident, 1,322 events from 5 never-opted-in projects). The
    invariant is preserved *within* a consenting project and abandoned across
    project boundaries.

    Note the axis: consent, not Teamspace-boundedness. Nothing here decides an
    event is not Teamspace-bound in order to skip it — ``TeamspaceBoundDropError``
    still fires for that, and the consent refusal happens before this function
    is ever called.
    """
    if is_teamspace_bound and skip_journal:
        raise TeamspaceBoundDropError(event_id=event_id)
    event = Event(
        event_id=event_id,
        event_type=event_type,
        payload=payload,
        occurred_at=occurred_at,
        created_at=created_at or now_utc_iso(),
        coalesce_key=coalesce_key,
        archived_at=None,
        drain_blocked_reason=classify_drain_blocked_reason(gate),
        # #3030 FR-006: the identity projection is written at capture time, not
        # only by T012's backfill. Without this every NEW row lands with a NULL
        # project_uuid, and NULL is permanently unselectable — the drain would go
        # silent for live traffic while the backfill kept history deliverable.
        project_uuid=project_uuid,
        project_slug=project_slug,
        repo_slug=repo_slug,
    )
    journal.append(event)
    return event


__all__ = [
    "ANONYMOUS_PRODUCER",
    "CaptureGateState",
    "CoalesceDecision",
    "CoalesceStrategy",
    "EventIdentityRow",
    "EventJournal",
    "JOURNAL_SUBDIR",
    "JournalTransaction",
    "TeamspaceBoundDropError",
    "capture_teamspace_bound",
    "classify_drain_blocked_reason",
    "get_journal",
    "register_coalesce_strategy",
    "reset_coalesce_strategy",
    "reset_journal_cache",
    "resolve_journal_path",
]
