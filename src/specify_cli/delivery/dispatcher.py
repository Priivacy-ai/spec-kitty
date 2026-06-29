"""The Sync Dispatcher — select -> post -> record over one active target (WP07).

This module is the seam where the mission's central behavioural shift becomes
observable: **a successful upload stops deleting the local event and instead
becomes a ledger update** (FR-001). It is the non-destructive replacement for the
old ``SyncQueue.process_batch_results`` success/duplicate/failed_permanent path,
which DELETED the local row — here those three outcomes become ledger writes and
the journal payload is **never** deleted (contract §3).

Three phases, each a small helper so the public :func:`dispatch` stays a thin
orchestrator (T044, complexity ceiling 15; ruff ``C901`` / Sonar ``S3776``):

1. **Select** (:func:`_select_undelivered`) — read the journal's event universe and
   delegate to the WP05 ledger's universe-aware ``select_undelivered`` query, which
   returns events with **no terminal-success and no terminal-failed** row for the
   active target (FR-004 / FR-015). No SQL lives here; no ``queue.py`` import.
2. **Post** (:func:`_post`) — hand the selected events to the active target's
   :class:`~specify_cli.delivery.receivers.DeliveryReceiver` (WP06). One dispatch
   path drives Teamspace / external / stub equivalently — there is **no** target-type
   conditional in this module (contract §4).
3. **Record** (:func:`_record`) — map each :class:`DeliveryResult` to a WP05 ledger
   write. ``success``/``duplicate`` -> terminal-success; ``pending``/``rejected``/
   ``transient`` -> their aligned ledger states; ``terminal_failed`` -> the WP05
   terminal-failed writer (parked, retained, excluded from future selection, FR-015).
   This phase never deletes a journal event — the journal is read-only here (FR-001).

**D-020 coalescing carry (FR-011).** The journal's coalescing seam defaults to a
no-op; the dispatcher is the live integration point that activates WP08's real
strategy via :func:`event_journal.coalesce.install`. Without this call, FR-011
coalescing is dead in production. WP08's ``coalesce`` module is a sibling dependency
that lands alongside this WP at merge; until it is present the install degrades
safely (the journal keeps its no-op seam) so a drain never breaks.

Per **C-001** this module imports nothing from ``sync/queue.py`` or
``specify_cli.events``; it consumes only the WP03 journal, WP05 ledger, and WP06
receiver public surfaces.
"""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.delivery.receivers import (
    DeliveryOutcome,
    DeliveryResult,
    OutboundEvent,
)
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event

if TYPE_CHECKING:
    from specify_cli.delivery.interfaces import DeliveryTarget
    from specify_cli.delivery.receivers import DeliveryReceiver


# --------------------------------------------------------------------------- #
# Dispatch summary — the dispatcher's observable, per-outcome output           #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class DispatchFailure:
    """Per-event non-success result captured for ``sync now --report``."""

    event_id: str
    outcome: str
    http_status: int | None = None
    error: str | None = None


@dataclass(frozen=True)
class DispatchSummary:
    """Per-outcome counts a single drain produced (the CLI/status observable surface).

    ``selected`` is how many journal events the drain pulled; the per-outcome fields
    sum to :attr:`recorded`. ``target_id`` is ``None`` only for a no-op drain (no
    active target was resolvable — T039 step 4).
    """

    target_id: str | None
    selected: int
    delivered: int
    duplicate: int
    pending: int
    rejected: int
    transient: int
    terminal_failed: int
    failures: tuple[DispatchFailure, ...] = ()

    @property
    def recorded(self) -> int:
        """Total ledger rows written/updated this drain (sum of the per-outcome counts)."""
        return (
            self.delivered
            + self.duplicate
            + self.pending
            + self.rejected
            + self.transient
            + self.terminal_failed
        )

    @classmethod
    def empty(cls) -> DispatchSummary:
        """The no-op result: no active target, nothing selected or recorded."""
        return cls(
            target_id=None,
            selected=0,
            delivered=0,
            duplicate=0,
            pending=0,
            rejected=0,
            transient=0,
            terminal_failed=0,
        )

    @classmethod
    def from_counts(
        cls,
        target_id: str,
        *,
        selected: int,
        counts: Mapping[DeliveryOutcome, int],
        failures: Sequence[DispatchFailure] = (),
    ) -> DispatchSummary:
        """Build a summary from a :class:`DeliveryOutcome` -> count mapping."""
        return cls(
            target_id=target_id,
            selected=selected,
            delivered=counts[DeliveryOutcome.SUCCESS],
            duplicate=counts[DeliveryOutcome.DUPLICATE],
            pending=counts[DeliveryOutcome.PENDING],
            rejected=counts[DeliveryOutcome.REJECTED],
            transient=counts[DeliveryOutcome.TRANSIENT],
            terminal_failed=counts[DeliveryOutcome.TERMINAL_FAILED],
            failures=tuple(failures),
        )


# --------------------------------------------------------------------------- #
# D-020: activate WP08 coalescing on the live dispatch path (FR-011)           #
# --------------------------------------------------------------------------- #


def _load_coalesce() -> Any:
    """Import WP08's ``event_journal.coalesce`` module (an isolated, patchable seam).

    Now that the sibling lane is merged this is a direct import, which the static
    no-dead-modules gate can see as a real caller (the prior string-based
    ``importlib.import_module`` indirection was a lane-staging device for when
    ``coalesce`` might not yet exist). The import stays a one-line indirection so
    tests can substitute the module and so :func:`_install_coalescing` owns the
    single ``ImportError`` guard that keeps the drain alive if the module is ever
    absent.
    """
    from specify_cli.event_journal import coalesce

    return coalesce


def _install_coalescing(ledger: SqliteDeliveryLedger) -> bool:
    """Register WP08's real coalescing strategy into the journal seam (D-020 / FR-011).

    The journal's coalescing seam defaults to a no-op; this is the live integration
    point that binds the strategy to the delivery *ledger* so "delivered anywhere?"
    is answered authoritatively. Returns ``True`` when the strategy was installed,
    ``False`` when WP08's ``coalesce`` module is not yet present in this checkout —
    in which case the journal safely keeps its no-op seam rather than breaking the
    drain (coalescing is simply inactive until the sibling WP lands).
    """
    try:
        coalesce: Any = _load_coalesce()
    except ImportError:
        return False
    coalesce.install(ledger)
    return True


# --------------------------------------------------------------------------- #
# Phase 1 — select undelivered events for the active target                    #
# --------------------------------------------------------------------------- #


def _select_undelivered(
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    target_id: str,
    *,
    limit: int | None = None,
) -> list[Event]:
    """Return journal events still needing delivery to *target_id* (FR-004 / FR-015).

    The journal supplies the **event universe** via its public ``read_all`` read API
    (deterministic ``created_at``/``event_id`` order); the WP05 ledger's universe-aware
    ``select_undelivered`` filters out every event that already has a terminal-success
    or terminal-failed row for the active target. Order is preserved so re-runs are
    reproducible. No SQL and no ``queue.py`` import lives here.
    """
    universe = journal.read_all()
    by_id = {event.event_id: event for event in universe}
    selected_ids = ledger.select_undelivered(
        target_id=target_id,
        event_universe=[event.event_id for event in universe],
        limit=limit,
    )
    return [by_id[event_id] for event_id in selected_ids]


# --------------------------------------------------------------------------- #
# Phase 2 — post selected events through the active receiver                    #
# --------------------------------------------------------------------------- #


def _decode_payload(event: Event) -> Mapping[str, Any]:
    """Project a journal event onto the wire envelope the receiver serialises.

    A JSON-object payload round-trips as-is; any non-JSON / non-object payload is
    wrapped in a minimal envelope so the batch body is always well-formed. The
    ``event_id`` the result keys back on comes from :class:`OutboundEvent`, never
    from the payload — so even a wrapped payload maps results correctly.
    """
    try:
        decoded = json.loads(event.payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        decoded = None
    if isinstance(decoded, Mapping):
        return decoded
    return {"event_id": event.event_id, "event_type": event.event_type}


def _post(
    receiver: DeliveryReceiver, events: Sequence[Event]
) -> list[DeliveryResult]:
    """Deliver *events* through the active *receiver* (one path; contract §4).

    An empty selection short-circuits without calling the receiver. The receiver
    owns the per-event result mapping (Teamspace / external / stub alike) — the
    dispatcher carries no target-type branch.
    """
    if not events:
        return []
    batch = [
        OutboundEvent(event_id=event.event_id, payload=_decode_payload(event))
        for event in events
    ]
    return list(receiver.deliver(batch))


# --------------------------------------------------------------------------- #
# Phase 3 — record each result to the WP05 ledger (never delete the journal)   #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _LedgerResult:
    """Adapt a WP06 :class:`DeliveryResult` onto the WP05 ``record_result`` surface.

    Exposes ``value`` (the outcome token the ledger folds to a status) plus the
    optional ``http_status``/``error`` metadata the ledger forwards — so a single
    ``record_result`` call carries both the state transition and its provenance.
    """

    value: str
    http_status: int | None
    error: str | None


def _record_one(
    ledger: SqliteDeliveryLedger, target_id: str, result: DeliveryResult
) -> None:
    """Map one receiver result to a ledger write — the journal is never touched.

    ``terminal_failed`` routes to the WP05 terminal-failed writer (T029): unlike the
    old ``queue.py`` DELETE, this **parks** the event (retained, inspectable) and
    relies on selector-exclusion (Phase 1) to keep the drain progressing (FR-015).
    Every other outcome folds onto its aligned ledger status via the Protocol
    ``record_result`` surface; ``success`` for an already-delivered pair is recorded
    as ``duplicate`` by the ledger (idempotent re-delivery, NFR-003).
    """
    if result.outcome is DeliveryOutcome.TERMINAL_FAILED:
        ledger.record_terminal_failed(
            result.event_id,
            target_id,
            http_status=result.http_status,
            error=result.error,
        )
        return
    ledger.record_result(
        event_id=result.event_id,
        target_id=target_id,
        result=_LedgerResult(
            value=result.outcome.value,
            http_status=result.http_status,
            error=result.error,
        ),
    )


def _record(
    ledger: SqliteDeliveryLedger,
    target_id: str,
    results: Sequence[DeliveryResult],
    *,
    selected: int,
) -> DispatchSummary:
    """Record every *result* and tally per-outcome counts into a :class:`DispatchSummary`."""
    counts: dict[DeliveryOutcome, int] = dict.fromkeys(DeliveryOutcome, 0)
    failures: list[DispatchFailure] = []
    with ledger.transaction():
        for result in results:
            _record_one(ledger, target_id, result)
            counts[result.outcome] += 1
            if result.outcome in {
                DeliveryOutcome.REJECTED,
                DeliveryOutcome.TRANSIENT,
                DeliveryOutcome.TERMINAL_FAILED,
            }:
                failures.append(
                    DispatchFailure(
                        event_id=result.event_id,
                        outcome=result.outcome.value,
                        http_status=result.http_status,
                        error=result.error,
                    )
                )
    return DispatchSummary.from_counts(
        target_id, selected=selected, counts=counts, failures=failures
    )


# --------------------------------------------------------------------------- #
# Public entry point — the thin select -> post -> record orchestrator           #
# --------------------------------------------------------------------------- #


def dispatch(
    *,
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    receiver: DeliveryReceiver,
    target: DeliveryTarget | None,
    limit: int | None = None,
) -> DispatchSummary:
    """Drain undelivered journal events to one active *target* (contract §3/§4).

    The single operator-selected active *target* is resolved upstream from the WP01
    ``ResolvedSyncTarget`` via the WP04 registry (C-003: no automatic fan-out); the
    *receiver* is resolved by WP12 mode policy. A ``None`` *target* — no active target
    is resolvable — is a no-op (nothing to drain), not an error (T039 step 4). The
    selection keys on ``target.target_id`` each invocation, so switching the active
    target re-selects the same retained events for the new target (FR-005 re-drain).

    Activates WP08 coalescing on this live path first (D-020 / FR-011), then runs
    select -> post -> record. A successful drain leaves the journal row count
    unchanged and writes terminal-success ledger rows (FR-001).
    """
    _install_coalescing(ledger)
    if target is None:
        return DispatchSummary.empty()
    events = _select_undelivered(journal, ledger, target.target_id, limit=limit)
    results = _post(receiver, events)
    return _record(ledger, target.target_id, results, selected=len(events))


__all__ = [
    "DispatchSummary",
    "dispatch",
]
