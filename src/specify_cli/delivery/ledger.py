"""Per-event/per-target delivery ledger (WP05, IC-04; FR-002/FR-004/FR-015).

The **Delivery Ledger** is the durable answer to "was event *X* delivered to
target *Y*, when, with what result?" (**FR-002**). It is the single authority for
which events still need draining (**FR-004**) and which are permanently parked
(**FR-015**). It implements the WP04 :class:`~specify_cli.delivery.interfaces.DeliveryLedger`
Protocol so the WP07 dispatcher and WP08 coalescing bind to the abstraction, never
to this concretion (**C-001** seam).

Design decisions (documented per the WP's validation checklist):

* **Shape (`C-003`)** — one row per ``(event_id, target_id)`` with the composite
  ``PRIMARY KEY (event_id, target_id)``. Delivering to a second target adds rows
  keyed by that target's ``target_id``; **no schema change**. There is deliberately
  no per-event single-status column that would bake in a "one target" assumption.
* **Outcome vocabulary** — the six ledger states are the durable representation of
  the contract §4 ``DeliveryReceiver`` result vocabulary: ``success`` / ``duplicate``
  (terminal-success), ``pending`` / ``rejected`` / ``failed_transient`` (non-terminal,
  still draining) and ``terminal_failed`` (permanent, parked, retained).
* **FR-001 boundary** — recording a success/duplicate is a ledger **UPDATE**; this
  module has *no* path that touches or deletes a journal event. Deletion only ever
  happens via explicit ``sync gc``/``sync archive`` (WP11).
* **Selection (`FR-004`/`FR-015`)** — :meth:`SqliteDeliveryLedger.select_undelivered`
  returns events lacking a terminal-success delivery for the active target **and
  excludes ``terminal_failed``**, so an oversized/permanent event parks while the
  drain still progresses. :meth:`SqliteDeliveryLedger.select_pending` is the
  Protocol-shaped view over the ledger's own non-terminal rows.
* **Delivered-anywhere (`FR-011` precursor)** —
  :meth:`SqliteDeliveryLedger.delivered_anywhere` is scoped to **terminal-success**
  only (``success``/``duplicate``). A ``terminal_failed`` row never reached the
  target, so it does *not* freeze the event for coalescing (contract §3: "Once
  delivered anywhere, payload bytes are immutable").
* **Metadata merge** — attempt fields accumulate (``attempt_count`` increments,
  ``first_attempted_at`` is sticky, ``last_attempted_at`` advances). Optional
  detail fields (``last_http_status`` / ``last_error`` / ``last_response_json`` /
  ``server_drain_state`` / ``accepted_at`` / ``completed_at``) use last-non-null-wins
  (``COALESCE``) semantics so a later attempt that omits a field keeps the prior
  value rather than nulling it.

Per **C-001** nothing here imports ``sync/queue.py`` or ``specify_cli.events``.
"""
from __future__ import annotations

import contextlib
import sqlite3
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from specify_cli.core.time_utils import now_utc_iso

# -- Public table / index identity (locked contract; asserted by tests) --------
LEDGER_TABLE = "delivery_ledger"
LEDGER_INDEX_NAME = "idx_delivery_ledger_target_status"

# -- Ledger status vocabulary (mirrors contract §4 DeliveryReceiver results) ---
STATUS_SUCCESS = "success"
STATUS_DUPLICATE = "duplicate"
STATUS_PENDING = "pending"
STATUS_REJECTED = "rejected"
STATUS_FAILED_TRANSIENT = "failed_transient"
STATUS_TERMINAL_FAILED = "terminal_failed"

# "Delivered to this target" — both leave the selection set and freeze the event.
TERMINAL_SUCCESS_STATUSES = frozenset({STATUS_SUCCESS, STATUS_DUPLICATE})
# Every status that leaves the automatic selection set: terminal-success PLUS the
# permanent terminal-failed park (the single source of the "terminal" set reused
# by selection and by WP11's terminal-failure count — avoids S1192 duplication).
TERMINAL_STATUSES = TERMINAL_SUCCESS_STATUSES | {STATUS_TERMINAL_FAILED}

# Fixed-length param tuples backing the literal ``IN`` clauses below. Their length
# matches the ``(?, ?, ...)`` placeholder count in the SQL constants; both move
# together if the status vocabulary ever grows.
_TERMINAL_STATUS_PARAMS = (STATUS_SUCCESS, STATUS_DUPLICATE, STATUS_TERMINAL_FAILED)
_TERMINAL_SUCCESS_PARAMS = (STATUS_SUCCESS, STATUS_DUPLICATE)

_DRAIN_PENDING = "pending"


@dataclass(frozen=True)
class _ResultSpec:
    """How a ``record_result`` token maps onto a ledger status + upsert flags."""

    status: str
    set_accepted: bool = False
    set_completed: bool = False
    server_drain_state: str | None = None


# Operator token -> ledger status + upsert flags for the Protocol record_result
# surface. Aliases fold the contract §4 wire vocabulary onto the durable status:
# ``transient`` -> ``failed_transient``; ``failed_permanent`` -> ``terminal_failed``.
_RESULT_STATUS_SPEC: dict[str, _ResultSpec] = {
    "success": _ResultSpec(STATUS_SUCCESS, set_completed=True),
    "duplicate": _ResultSpec(STATUS_DUPLICATE, set_completed=True),
    "pending": _ResultSpec(STATUS_PENDING, set_accepted=True, server_drain_state=_DRAIN_PENDING),
    "rejected": _ResultSpec(STATUS_REJECTED),
    "transient": _ResultSpec(STATUS_FAILED_TRANSIENT),
    "failed_transient": _ResultSpec(STATUS_FAILED_TRANSIENT),
    "terminal_failed": _ResultSpec(STATUS_TERMINAL_FAILED, set_completed=True),
    "failed_permanent": _ResultSpec(STATUS_TERMINAL_FAILED, set_completed=True),
}
_RESULT_METADATA_KEYS = ("http_status", "error", "response_json", "server_drain_state", "at")

# -- Schema: per-(event_id, target_id) row + selection-supporting index --------
# The ``(target_id, status)`` index makes the selection predicate ("undelivered
# for target, excluding terminal statuses") index-assisted rather than a full
# table scan, so the dispatcher does no full-table rewrite per sync (plan IC-04).
_SCHEMA = """
CREATE TABLE IF NOT EXISTS delivery_ledger (
    event_id            TEXT NOT NULL,
    target_id           TEXT NOT NULL,
    status              TEXT NOT NULL,
    attempt_count       INTEGER NOT NULL DEFAULT 0,
    first_attempted_at  TEXT,
    last_attempted_at   TEXT,
    accepted_at         TEXT,
    completed_at        TEXT,
    server_drain_state  TEXT,
    last_http_status    INTEGER,
    last_error          TEXT,
    last_response_json  TEXT,
    PRIMARY KEY (event_id, target_id)
);
CREATE INDEX IF NOT EXISTS idx_delivery_ledger_target_status
    ON delivery_ledger (target_id, status);
"""

# Single upsert: insert a fresh attempt or merge into the existing pair-row.
# ``attempt_count`` increments, ``first_attempted_at`` is sticky, detail fields
# use last-non-null-wins so an attempt that omits a field keeps the prior value.
_UPSERT_SQL = """
INSERT INTO delivery_ledger (
    event_id, target_id, status, attempt_count,
    first_attempted_at, last_attempted_at, accepted_at, completed_at,
    server_drain_state, last_http_status, last_error, last_response_json
) VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(event_id, target_id) DO UPDATE SET
    status = excluded.status,
    attempt_count = delivery_ledger.attempt_count + 1,
    first_attempted_at = COALESCE(delivery_ledger.first_attempted_at, excluded.first_attempted_at),
    last_attempted_at = excluded.last_attempted_at,
    accepted_at = COALESCE(excluded.accepted_at, delivery_ledger.accepted_at),
    completed_at = COALESCE(excluded.completed_at, delivery_ledger.completed_at),
    server_drain_state = COALESCE(excluded.server_drain_state, delivery_ledger.server_drain_state),
    last_http_status = COALESCE(excluded.last_http_status, delivery_ledger.last_http_status),
    last_error = COALESCE(excluded.last_error, delivery_ledger.last_error),
    last_response_json = COALESCE(excluded.last_response_json, delivery_ledger.last_response_json)
"""

_GET_ROW_SQL = "SELECT * FROM delivery_ledger WHERE event_id = ? AND target_id = ?"
# Literal IN clauses (no f-strings) keep these as constant SQL — no dynamic SQL
# assembly, so there is no injection surface and bandit S608 stays silent.
_SELECT_PENDING_SQL = (
    "SELECT event_id FROM delivery_ledger "
    "WHERE target_id = ? AND status NOT IN (?, ?, ?) "
    "ORDER BY first_attempted_at, event_id LIMIT ?"
)
_TERMINAL_EVENT_IDS_SQL = (
    "SELECT event_id FROM delivery_ledger WHERE target_id = ? AND status IN (?, ?, ?)"
)
_DELIVERED_ANYWHERE_SQL = (
    "SELECT 1 FROM delivery_ledger WHERE event_id = ? AND status IN (?, ?) LIMIT 1"
)
_DELIVERED_TO_TARGET_SQL = (
    "SELECT 1 FROM delivery_ledger "
    "WHERE event_id = ? AND target_id = ? AND status IN (?, ?) LIMIT 1"
)


@dataclass(frozen=True)
class LedgerRow:
    """A single ``delivery_ledger`` row — the per-``(event_id, target_id)`` state.

    Answers FR-002's "delivered to Y, when, with what result?". Optional timestamp
    and HTTP-detail fields are ``None`` until the relevant transition occurs.
    """

    event_id: str
    target_id: str
    status: str
    attempt_count: int
    first_attempted_at: str | None
    last_attempted_at: str | None
    accepted_at: str | None
    completed_at: str | None
    server_drain_state: str | None
    last_http_status: int | None
    last_error: str | None
    last_response_json: str | None


def init_ledger(conn: sqlite3.Connection) -> None:
    """Create the ``delivery_ledger`` table + selection index idempotently.

    Safe to call on an existing database (``CREATE ... IF NOT EXISTS``), so a
    future WP that shares one connection across the journal/targets/ledger can
    initialize the schema without a migration.
    """
    conn.executescript(_SCHEMA)
    conn.commit()


def _coerce_result_token(result: object) -> str:
    """Normalize a delivery result to a canonical lower-snake status token.

    Accepts a plain status string or a ``DeliveryResult``-like object (WP06),
    reading ``.value`` then ``.name`` then ``str(result)``. ``terminal-failed``
    and ``TERMINAL_FAILED`` both fold to ``terminal_failed``.
    """
    if isinstance(result, str):
        token = result
    else:
        value = getattr(result, "value", None)
        name = getattr(result, "name", None)
        token = value if isinstance(value, str) else name if isinstance(name, str) else str(result)
    return token.strip().lower().replace("-", "_")


def _result_metadata(result: object) -> dict[str, Any]:
    """Extract optional ledger metadata carried on a non-string result object.

    A plain status string carries no metadata. A richer ``DeliveryResult`` may
    expose ``http_status`` / ``error`` / ``response_json`` / ``server_drain_state``
    / ``at``; only the present, non-``None`` attributes are forwarded.
    """
    if isinstance(result, str):
        return {}
    return {
        key: getattr(result, key)
        for key in _RESULT_METADATA_KEYS
        if getattr(result, key, None) is not None
    }


def _as_str(value: object) -> str:
    return str(value)


def _as_opt_str(value: object) -> str | None:
    return None if value is None else str(value)


def _row_to_ledger(row: sqlite3.Row) -> LedgerRow:
    """Build a :class:`LedgerRow` from a ``delivery_ledger`` row.

    ``row[...]`` values are dynamically typed (``sqlite3.Row`` returns ``Any``);
    the integer columns are coerced inline so the value object stays strictly typed.
    """
    http_status = row["last_http_status"]
    return LedgerRow(
        event_id=_as_str(row["event_id"]),
        target_id=_as_str(row["target_id"]),
        status=_as_str(row["status"]),
        attempt_count=int(row["attempt_count"]),
        first_attempted_at=_as_opt_str(row["first_attempted_at"]),
        last_attempted_at=_as_opt_str(row["last_attempted_at"]),
        accepted_at=_as_opt_str(row["accepted_at"]),
        completed_at=_as_opt_str(row["completed_at"]),
        server_drain_state=_as_opt_str(row["server_drain_state"]),
        last_http_status=None if http_status is None else int(http_status),
        last_error=_as_opt_str(row["last_error"]),
        last_response_json=_as_opt_str(row["last_response_json"]),
    )


class SqliteDeliveryLedger:
    """SQLite-backed :class:`~specify_cli.delivery.interfaces.DeliveryLedger`.

    Pass ``":memory:"`` (default) for an isolated in-process ledger or a file path
    for a persistent one. Implements the WP04 ``DeliveryLedger`` Protocol
    (:meth:`record_result`, :meth:`select_pending`, :meth:`delivered_anywhere`)
    plus typed per-outcome recorders and the universe-aware
    :meth:`select_undelivered` query the WP07 dispatcher uses for FR-004.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._transaction_depth = 0
        init_ledger(self._conn)

    # -- lifecycle ---------------------------------------------------------
    @property
    def connection(self) -> sqlite3.Connection:
        """The underlying connection (read access for status/diagnostic joins)."""
        return self._conn

    def close(self) -> None:
        self._conn.close()

    @contextlib.contextmanager
    def transaction(self) -> Any:
        """Group multiple ledger writes into one SQLite transaction."""
        outermost = self._transaction_depth == 0
        if outermost:
            self._conn.execute("BEGIN")
        self._transaction_depth += 1
        try:
            yield self
        except Exception:
            self._transaction_depth -= 1
            if outermost:
                self._conn.rollback()
            raise
        else:
            self._transaction_depth -= 1
            if outermost:
                self._conn.commit()

    def __enter__(self) -> SqliteDeliveryLedger:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- core upsert -------------------------------------------------------
    def _record(
        self,
        event_id: str,
        target_id: str,
        *,
        status: str,
        at: str | None = None,
        http_status: int | None = None,
        error: str | None = None,
        response_json: str | None = None,
        server_drain_state: str | None = None,
        set_accepted: bool = False,
        set_completed: bool = False,
    ) -> str:
        """Upsert the ``(event_id, target_id)`` row to *status*; return *status*.

        Never deletes a journal event (FR-001): this is the only write path and it
        only ever touches ``delivery_ledger``.
        """
        now = at or now_utc_iso()
        accepted_at = now if set_accepted else None
        completed_at = now if set_completed else None
        self._conn.execute(
            _UPSERT_SQL,
            (
                event_id,
                target_id,
                status,
                now,
                now,
                accepted_at,
                completed_at,
                server_drain_state,
                http_status,
                error,
                response_json,
            ),
        )
        if self._transaction_depth == 0:
            self._conn.commit()
        return status

    def _is_terminal_success(self, event_id: str, target_id: str) -> bool:
        """Whether the pair already holds a terminal-success status."""
        row = self.get(event_id, target_id)
        return row is not None and row.status in TERMINAL_SUCCESS_STATUSES

    # -- typed accessors ---------------------------------------------------
    def get(self, event_id: str, target_id: str) -> LedgerRow | None:
        """Return the ledger row for *(event_id, target_id)*, or ``None``."""
        row = self._conn.execute(_GET_ROW_SQL, (event_id, target_id)).fetchone()
        return None if row is None else _row_to_ledger(row)

    # -- T027: terminal-success recorders ----------------------------------
    def record_success(
        self,
        event_id: str,
        target_id: str,
        *,
        http_status: int | None = None,
        response_json: str | None = None,
        at: str | None = None,
    ) -> str:
        """Record a successful delivery (terminal-success); return the status.

        Idempotent re-delivery (NFR-003): recording success for a pair that is
        already terminal-success yields ``duplicate`` with no row duplication and
        the event IDs unchanged.
        """
        status = STATUS_DUPLICATE if self._is_terminal_success(event_id, target_id) else STATUS_SUCCESS
        return self._record(
            event_id,
            target_id,
            status=status,
            at=at,
            http_status=http_status,
            response_json=response_json,
            set_completed=True,
        )

    def record_duplicate(
        self,
        event_id: str,
        target_id: str,
        *,
        http_status: int | None = None,
        response_json: str | None = None,
        at: str | None = None,
    ) -> str:
        """Record a server-reported duplicate (terminal-success, distinct status)."""
        return self._record(
            event_id,
            target_id,
            status=STATUS_DUPLICATE,
            at=at,
            http_status=http_status,
            response_json=response_json,
            set_completed=True,
        )

    # -- T028: non-terminal recorders --------------------------------------
    def record_pending(
        self,
        event_id: str,
        target_id: str,
        *,
        server_drain_state: str = _DRAIN_PENDING,
        at: str | None = None,
    ) -> str:
        """Record an accepted-but-not-yet-drained delivery (non-terminal)."""
        return self._record(
            event_id,
            target_id,
            status=STATUS_PENDING,
            at=at,
            server_drain_state=server_drain_state,
            set_accepted=True,
        )

    def record_rejected(
        self,
        event_id: str,
        target_id: str,
        *,
        http_status: int | None = None,
        error: str | None = None,
        at: str | None = None,
    ) -> str:
        """Record a per-event content rejection (non-terminal; payload retained)."""
        return self._record(
            event_id,
            target_id,
            status=STATUS_REJECTED,
            at=at,
            http_status=http_status,
            error=error,
        )

    def record_transient(
        self,
        event_id: str,
        target_id: str,
        *,
        http_status: int | None = None,
        error: str | None = None,
        at: str | None = None,
    ) -> str:
        """Record a batch-level transient failure (non-terminal).

        Kept a distinct status from :meth:`record_rejected` so a 5xx/timeout batch
        failure is never conflated with a per-event content rejection.
        """
        return self._record(
            event_id,
            target_id,
            status=STATUS_FAILED_TRANSIENT,
            at=at,
            http_status=http_status,
            error=error,
        )

    # -- T029: terminal-failed recorder ------------------------------------
    def record_terminal_failed(
        self,
        event_id: str,
        target_id: str,
        *,
        http_status: int | None = None,
        error: str | None = None,
        response_json: str | None = None,
        at: str | None = None,
    ) -> str:
        """Record a permanent failure (e.g. oversized): parked, retained, inspectable.

        Excluded from future automatic selection (T030) but never deleted — the
        journal payload stays inspectable and operator-retryable (FR-015).
        """
        return self._record(
            event_id,
            target_id,
            status=STATUS_TERMINAL_FAILED,
            at=at,
            http_status=http_status,
            error=error,
            response_json=response_json,
            set_completed=True,
        )

    # -- Protocol surface: record_result -----------------------------------
    def record_result(self, *, event_id: str, target_id: str, result: object) -> None:
        """Record a delivery *result* (WP04 ``DeliveryLedger`` Protocol entry).

        *result* is a status token or a ``DeliveryResult``-like object (WP06). The
        token is folded onto a ledger status and any carried metadata
        (``http_status``/``error``/``response_json``/``at``) is forwarded.
        """
        token = _coerce_result_token(result)
        spec = _RESULT_STATUS_SPEC.get(token)
        if spec is None:
            raise ValueError(f"unknown delivery result vocabulary: {token!r}")
        status = spec.status
        if status == STATUS_SUCCESS and self._is_terminal_success(event_id, target_id):
            status = STATUS_DUPLICATE
        meta = _result_metadata(result)
        self._record(
            event_id,
            target_id,
            status=status,
            at=meta.get("at"),
            http_status=meta.get("http_status"),
            error=meta.get("error"),
            response_json=meta.get("response_json"),
            server_drain_state=spec.server_drain_state,
            set_accepted=spec.set_accepted,
            set_completed=spec.set_completed,
        )

    # -- Protocol surface: selection ---------------------------------------
    def select_pending(self, *, target_id: str, limit: int) -> Sequence[str]:
        """Return up to *limit* event IDs with a non-terminal row for *target_id*.

        The Protocol-shaped view over the ledger's own rows: events in ``pending``
        / ``rejected`` / ``failed_transient`` state, excluding terminal-success and
        terminal-failed. Index-assisted by ``(target_id, status)``. For a universe
        that includes never-attempted journal events, use :meth:`select_undelivered`.
        """
        rows = self._conn.execute(
            _SELECT_PENDING_SQL, (target_id, *_TERMINAL_STATUS_PARAMS, limit)
        ).fetchall()
        return [_as_str(row["event_id"]) for row in rows]

    def select_undelivered(
        self,
        *,
        target_id: str,
        event_universe: Iterable[str],
        limit: int | None = None,
    ) -> list[str]:
        """Return the *event_universe* events still needing delivery to *target_id*.

        "Undelivered for target" = no terminal-success row AND no ``terminal_failed``
        row for ``(event_id, target_id)`` (FR-004 / FR-015). Because identity is
        per-target, an event delivered to target A is still selectable for target B
        (FR-005 re-drain precursor). Preserves *event_universe* order.
        """
        excluded = self._terminal_event_ids(target_id)
        selected = [event_id for event_id in event_universe if event_id not in excluded]
        return selected if limit is None else selected[:limit]

    def _terminal_event_ids(self, target_id: str) -> set[str]:
        """Event IDs that have left the selection set for *target_id*.

        Terminal-success (delivered) plus ``terminal_failed`` (permanently parked).
        """
        rows = self._conn.execute(
            _TERMINAL_EVENT_IDS_SQL, (target_id, *_TERMINAL_STATUS_PARAMS)
        ).fetchall()
        return {_as_str(row["event_id"]) for row in rows}

    # -- Protocol surface: delivered_anywhere ------------------------------
    def delivered_anywhere(self, event_id: str) -> bool:
        """Whether *event_id* has a terminal-success delivery to ANY target.

        Scoped to terminal-**success** (``success``/``duplicate``): this is the WP08
        coalescing immutability gate (contract §3 "Once delivered anywhere, payload
        bytes are immutable"). A ``terminal_failed`` row never reached the target and
        therefore does **not** freeze the event.
        """
        row = self._conn.execute(
            _DELIVERED_ANYWHERE_SQL, (event_id, *_TERMINAL_SUCCESS_PARAMS)
        ).fetchone()
        return row is not None

    def delivered_to_target(self, event_id: str, target_id: str) -> bool:
        """Whether *(event_id, target_id)* holds a terminal-success delivery.

        The target-scoped sibling of :meth:`delivered_anywhere`: it answers
        "was this exact event delivered to *this* target?" (``success`` /
        ``duplicate`` only). WP11's :func:`~specify_cli.delivery.retention.gc_payloads`
        uses it to purge a payload **only** once every known target has received
        it, preserving re-drainability to a not-yet-delivered target (FR-005).
        """
        row = self._conn.execute(
            _DELIVERED_TO_TARGET_SQL, (event_id, target_id, *_TERMINAL_SUCCESS_PARAMS)
        ).fetchone()
        return row is not None


if TYPE_CHECKING:
    from specify_cli.delivery.interfaces import DeliveryLedger

    def _protocol_conformance(ledger: SqliteDeliveryLedger) -> DeliveryLedger:
        """Compile-time proof that the concrete ledger satisfies the WP04 Protocol.

        Never executed; mypy verifies ``SqliteDeliveryLedger`` is structurally a
        :class:`DeliveryLedger` so WP07/WP08 bind to the abstraction (C-001).
        """
        return ledger


__all__ = [
    "LEDGER_TABLE",
    "LEDGER_INDEX_NAME",
    "STATUS_SUCCESS",
    "STATUS_DUPLICATE",
    "STATUS_PENDING",
    "STATUS_REJECTED",
    "STATUS_FAILED_TRANSIENT",
    "STATUS_TERMINAL_FAILED",
    "TERMINAL_SUCCESS_STATUSES",
    "TERMINAL_STATUSES",
    "LedgerRow",
    "SqliteDeliveryLedger",
    "init_ledger",
]
