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
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from specify_cli.core.time_utils import now_utc_iso
from specify_cli.paths import get_runtime_root

from .models import (
    COUNT_SQL,
    CREATE_COALESCE_INDEX_SQL,
    CREATE_TABLE_SQL,
    CREATE_TYPE_INDEX_SQL,
    DRAIN_BLOCKED_MISSING_AUTH,
    DRAIN_BLOCKED_MISSING_TEAM,
    DRAIN_BLOCKED_SAAS_DISABLED,
    INSERT_SQL,
    MARK_ARCHIVED_SQL,
    OLDEST_CREATED_AT_SQL,
    SELECT_ALL_SQL,
    SELECT_BLOCKED_SQL,
    SELECT_BY_ID_SQL,
    Event,
    event_to_params,
    row_to_event,
)

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
            conn.execute(CREATE_COALESCE_INDEX_SQL)
            conn.execute(CREATE_TYPE_INDEX_SQL)
            conn.commit()

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
) -> Event:
    """Durably capture a Teamspace-bound fact *before* the delivery gates.

    The journal write is unconditional for Teamspace-bound families; ``gate``
    only decides the recorded ``drain_blocked_reason`` (delivery eligibility),
    never whether the write happens (FR-017, contract §2). A request to skip the
    write for a Teamspace-bound family fails loudly (C-008, T018).
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
    )
    journal.append(event)
    return event


__all__ = [
    "ANONYMOUS_PRODUCER",
    "CaptureGateState",
    "CoalesceDecision",
    "CoalesceStrategy",
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
