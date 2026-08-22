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

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from specify_cli.delivery.consent_gate import (
    ConsentAnswer,
    ProjectTransportDisclosure,
    ProjectTransportRefusal,
    ProjectTransportResultError,
    consented_batch,
    default_transport_deadline,
    execute_project_transport_batch,
    stable_transport_id,
)
from specify_cli.delivery.ledger import SqliteDeliveryLedger
from specify_cli.delivery.receivers import (
    DeliveryEffectCertainty,
    DeliveryOutcome,
    DeliveryResult,
    OutboundEvent,
    disclosed_event_payload_bytes,
)
from specify_cli.delivery.targets import compute_target_id
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.sync.project_context import ProjectSyncContext
from specify_cli.sync.project_identity import CanonicalProjectUUID
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.saas_client.admission import (
    ProjectWriteAdmissionProof,
    attach_admission_proof,
)
from .selection import select_consented

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
    active target was resolvable — T039 step 4). ``retryable_event_ids`` carries
    pending/rejected/transient IDs separately from reportable failures so a
    multi-batch command can skip them in-memory while leaving them durably
    selectable for the next command.
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
    retryable_event_ids: tuple[str, ...] = ()

    @property
    def recorded(self) -> int:
        """Total ledger rows written/updated this drain (sum of the per-outcome counts)."""
        return self.delivered + self.duplicate + self.pending + self.rejected + self.transient + self.terminal_failed

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
        retryable_event_ids: Sequence[str] = (),
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
            retryable_event_ids=tuple(retryable_event_ids),
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


@dataclass(frozen=True)
class _Selected:
    """The drain's hydrated batch **and** the consent answer that cleared it.

    The pair travels together because the receiver's input type requires the
    answer (#3030 FR-028) and re-resolving it in phase 2 would be a second
    consent chain (C-003) — one that could disagree with the SQL predicate that
    chose these very rows if consent were revoked between the two calls.
    """

    events: list[Event]
    answer: ConsentAnswer
    recovery_event_ids: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class _EventTransportEnvelope:
    """One exact proof-bearing Event wire item and its durable authority."""

    event_id: str
    target_id: str
    wire_payload: Mapping[str, Any]
    disclosure: ProjectTransportDisclosure


def _select_undelivered(
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    target_id: str,
    *,
    context: ProjectSyncContext,
    limit: int | None = None,
    exclude: frozenset[str] = frozenset(),
    recovery_event_ids: frozenset[str] = frozenset(),
) -> _Selected:
    """Return journal events still needing delivery to *target_id* (FR-004 / FR-015).

    The journal supplies the **event universe** via FR-008's project-filtered
    identity read (deterministic ``created_at``/``event_id`` order); the WP05
    ledger's universe-aware ``select_undelivered`` filters out every event that
    already has a terminal-success or terminal-failed row for the active target.
    Order is preserved so re-runs are reproducible. No SQL and no ``queue.py``
    import lives here.

    *exclude* is a caller-supplied, in-memory skip set applied to the universe
    **before** the ledger query, so the ``limit`` still fills with selectable
    events. It is a transient, per-call filter (a drain pass uses it to advance
    past events that made no progress this pass); it never changes durable ledger
    state, so the ledger's non-terminal re-selection contract is preserved.
    """
    # T017/T018 (#3030 FR-007/FR-008): the universe is built from a
    # **project-filtered** identity read — distinct-project probe, consent, then an
    # indexed ``project_uuid IN (…)`` predicate — BEFORE the ledger query and before
    # any limit. Previously this was ``journal.read_all()`` (every row of every
    # project, no project predicate anywhere), which is the seam the 2026-07-27 leak
    # went through, and then an unfiltered identity read filtered in Python, which
    # closed the leak but left NFR-003's indexed lookup unimplemented.
    #
    # Ordering is load-bearing: consent filtering must precede the ledger's limit,
    # or 2,000 non-consented rows ahead of 10 consented ones fill the window and
    # the drain starves permanently (NFR-002/SC-002).
    selection = select_consented(journal, context=context)
    universe_ids = [event_id for event_id in selection.event_ids if event_id not in exclude]

    selected_ids = ledger.select_undelivered(
        target_id=target_id,
        event_universe=universe_ids,
        limit=limit,
        recovery_event_ids=recovery_event_ids,
    )

    # Payloads are hydrated only for the batch the ledger actually selected, so an
    # unlimited universe read never materialises every payload (NFR-003). One
    # batched read over one connection: the per-event ``read_by_id`` this replaces
    # opened a fresh SQLite connection per event, so a 1,000-event batch cost 1,000
    # connection open/closes.
    durable_recovery_ids = ledger.retryable_recovery_event_ids(
        target_id=target_id,
        event_universe=selected_ids,
    )
    return _Selected(
        events=journal.read_by_ids(selected_ids),
        answer=selection.answer,
        recovery_event_ids=durable_recovery_ids | recovery_event_ids,
    )


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


def _transport_outcome_for_delivery_result(
    result: DeliveryResult,
) -> tuple[str, str | None]:
    """Map the receiver's per-event vocabulary onto WP06's result vocabulary."""
    from specify_cli.sync.transport_attempts import DeliveryOutcome as TransportOutcome

    if result.outcome is DeliveryOutcome.SUCCESS:
        return TransportOutcome.DELIVERED.value, None
    if result.outcome is DeliveryOutcome.DUPLICATE:
        return TransportOutcome.DUPLICATE.value, None
    if result.outcome is DeliveryOutcome.PENDING:
        if result.effect_certainty is DeliveryEffectCertainty.ACCEPTED_PENDING:
            return TransportOutcome.PENDING.value, None
        return TransportOutcome.UNKNOWN.value, None
    if result.outcome is DeliveryOutcome.REJECTED:
        if result.effect_certainty is DeliveryEffectCertainty.KNOWN_NO_EFFECT:
            return TransportOutcome.RETRYABLE_NO_EFFECT.value, None
        return TransportOutcome.UNKNOWN.value, None
    if result.outcome is DeliveryOutcome.TRANSIENT:
        if result.effect_certainty is DeliveryEffectCertainty.KNOWN_NO_EFFECT:
            return TransportOutcome.RETRYABLE_NO_EFFECT.value, None
        return TransportOutcome.UNKNOWN.value, None
    if result.outcome is DeliveryOutcome.TERMINAL_FAILED:
        return (
            TransportOutcome.REFUSED.value,
            (result.error_category or result.error or result.outcome.value).strip() or result.outcome.value,
        )
    return TransportOutcome.UNKNOWN.value, None


def _dispatcher_payload_reference(event_id: str, target_id: str) -> str:
    """Structured correlation stored inside the canonical WP06 attempt metadata."""
    return json.dumps(
        {
            "schema": "spec-kitty.dispatcher.v1",
            "event_id": event_id,
            "target_id": target_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def prepare_event_transport(
    payload: Mapping[str, Any],
    *,
    event_id: str,
    project_uuid: str,
    context: ProjectSyncContext,
) -> _EventTransportEnvelope:
    """Build the canonical HTTP/WebSocket Event item from store-minted authority.

    Event ID is the SaaS-native idempotency identity.  Both interactive transports
    therefore use the same attempt ID, exact proof-bearing bytes, and result
    correlation instead of creating one HTTP attempt and another WebSocket ledger.
    """
    target = context.target_audience
    if target is None or context.epoch_id is None or context.consent_generation is None or context.admission_generation is None or context.binding_audience is None:
        raise ValueError("Event transport requires an admitted project context")
    canonical_project = context.project_uuid.storage_token
    if project_uuid != canonical_project:
        raise ValueError("Event project UUID does not match its project context")
    wire_event_id = payload.get("event_id")
    if wire_event_id is not None and str(wire_event_id) != event_id:
        raise ValueError("Event wire identity does not match the journal event ID")
    target_id = compute_target_id(
        target_identity=target.target_identity,
        account_identity=target.account_identity,
        private_teamspace_id=target.private_teamspace_id,
        project_uuid=context.project_uuid,
        configuration_generation=target.configuration_generation,
    )
    # ``event_id`` is the SaaS-native result correlation key.  The attempt ID
    # below carries the project/target uniqueness; inventing a composite native
    # identity here would make WP06 recovery query a key SaaS never returns.
    native_identity = event_id
    presented_project = payload.get("project_uuid")
    if presented_project is not None and str(presented_project) != canonical_project:
        raise ValueError("Event payload cannot override its project authority")
    if {"admission_generation", "binding_audience"} & payload.keys():
        raise ValueError("Event payload cannot supply ambient admission authority")
    # Legacy Event envelopes already carry their project identity.  Validate it
    # above, then let the shared proof helper mint the complete authority tuple;
    # it deliberately refuses any caller-supplied proof field.
    base = {key: value for key, value in payload.items() if key != "project_uuid"}
    base.setdefault("event_id", event_id)
    base["type"] = "event"
    base["spec_kitty_delivery_identity"] = native_identity
    proof = ProjectWriteAdmissionProof(
        project_uuid=canonical_project,
        admission_generation=int(context.admission_generation),
        binding_audience=context.binding_audience,
    )
    wire = attach_admission_proof(base, proof)
    outbound = OutboundEvent(event_id=event_id, payload=wire)
    payload_hash = (
        "sha256:"
        + hashlib.sha256(  # noqa: TID251 - exact transport bytes, not charter content
            disclosed_event_payload_bytes(outbound)
        ).hexdigest()
    )
    disclosure = ProjectTransportDisclosure(
        project_uuid=canonical_project,
        epoch_id=context.epoch_id,
        consent_generation=context.consent_generation,
        target_identity=target.target_identity,
        account_identity=target.account_identity,
        private_teamspace_id=target.private_teamspace_id,
        # ``TargetAudience.project_uuid`` is declared ``CanonicalProjectUUID | str``
        # (the union covers unvalidated constructor input) but its ``__post_init__``
        # always normalizes it to a ``CanonicalProjectUUID`` in-place — a fact
        # ``object.__setattr__`` narrowing does not carry through to mypy. Re-parsing
        # here is a genuine no-op on the already-normalized value (see
        # ``CanonicalProjectUUID.parse``'s ``isinstance(value, cls)`` fast path) and
        # gives a properly narrowed ``CanonicalProjectUUID`` to read ``storage_token`` from.
        target_project_uuid=CanonicalProjectUUID.parse(target.project_uuid).storage_token,
        target_generation=target.configuration_generation,
        admission_generation=str(context.admission_generation),
        binding_audience=context.binding_audience,
        write_kind="event",
        native_identity=native_identity,
        payload_hash=payload_hash,
        payload_reference=_dispatcher_payload_reference(event_id, target_id),
        attempt_id="event:" + stable_transport_id("attempt", canonical_project, target_id, event_id),
        deadline_at=default_transport_deadline(),
        reconciliation_policy="native_identity_retry",
    )
    return _EventTransportEnvelope(
        event_id=event_id,
        target_id=target_id,
        wire_payload=wire,
        disclosure=disclosure,
    )


def _target_id_for_event(
    event: Event,
    *,
    target: DeliveryTarget,
    context: ProjectSyncContext,
) -> str:
    project_uuid = event.project_uuid
    if project_uuid is None:
        raise ValueError("event has no project_uuid")
    if str(target.project_uuid.storage_token) != project_uuid:
        raise ValueError("target project_uuid does not match event project_uuid")
    target_id = compute_target_id(
        target_identity=target.target_identity,
        account_identity=target.account_identity,
        private_teamspace_id=target.private_teamspace_id,
        project_uuid=target.project_uuid,
        configuration_generation=target.configuration_generation,
    )
    if target.target_id != target_id:
        raise ValueError("target_id does not match the admitted audience tuple")
    if context.epoch_id is None or context.consent_generation is None:
        raise ValueError("dispatch requires a consenting project context")
    return str(target_id)


def _correlate_batch_results(
    value: object,
    *,
    disclosures_by_event: Mapping[str, ProjectTransportDisclosure],
) -> tuple[list[DeliveryResult], Mapping[str, tuple[str, str | None]]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("receiver did not return a per-event result sequence")
    by_event: dict[str, DeliveryResult] = {}
    for item in value:
        if not isinstance(item, DeliveryResult):
            raise ValueError("receiver returned a non-DeliveryResult item")
        if item.event_id not in disclosures_by_event:
            raise ValueError(f"receiver returned result for unselected event {item.event_id}")
        if item.event_id in by_event:
            raise ValueError(f"receiver returned duplicate result for event {item.event_id}")
        by_event[item.event_id] = item
    missing = set(disclosures_by_event) - set(by_event)
    if missing:
        raise ValueError(f"receiver omitted results for events: {', '.join(sorted(missing))}")
    outcomes = {disclosures_by_event[event_id].attempt_id: _transport_outcome_for_delivery_result(result) for event_id, result in by_event.items()}
    return [by_event[event_id] for event_id in disclosures_by_event], outcomes


def _post(
    receiver: DeliveryReceiver,
    events: Sequence[Event],
    answer: ConsentAnswer,
    *,
    target: DeliveryTarget | None = None,
    context: ProjectSyncContext | None = None,
    target_id: str | None = None,
    recovery_event_ids: frozenset[str] = frozenset(),
) -> list[DeliveryResult]:
    """Deliver *events* through the active *receiver* (one path; contract §4).

    An empty selection short-circuits without calling the receiver. The receiver
    owns the per-event result mapping (Teamspace / external / stub alike) — the
    dispatcher carries no target-type branch.

    Attribution is taken from the journal's **stored** ``project_uuid`` column,
    never re-derived from the payload here: C-003 makes the column the sole
    selection authority, and ``_decode_payload`` wraps an undecodable payload in a
    minimal envelope that carries no identity at all — deriving from that would
    turn a legacy row into an unattributable one and refuse a batch selection had
    already cleared.
    """
    del target_id  # retained only so legacy empty-selection unit tests stay no-I/O.
    if not events:
        return []
    if target is None:
        raise TypeError("non-empty dispatcher post requires a DeliveryTarget final-gate audience")
    if context is None:
        raise TypeError("non-empty dispatcher post requires the immutable selected ProjectSyncContext")
    immediate: list[DeliveryResult] = []
    outbounds: list[OutboundEvent] = []
    disclosures: list[ProjectTransportDisclosure] = []
    projects: dict[str, str] = {}
    for event in events:
        try:
            target_id = _target_id_for_event(event, target=target, context=context)
            assert event.project_uuid is not None
            prepared = prepare_event_transport(
                _decode_payload(event),
                event_id=event.event_id,
                project_uuid=event.project_uuid,
                context=context,
            )
            if prepared.target_id != target_id:
                raise ValueError("dispatcher target does not match context audience")
            outbound = OutboundEvent(
                event_id=prepared.event_id,
                payload=prepared.wire_payload,
            )
            disclosure = prepared.disclosure
        except ValueError as exc:
            immediate.append(
                DeliveryResult(
                    event_id=event.event_id,
                    outcome=DeliveryOutcome.TERMINAL_FAILED,
                    error=f"project_not_admitted: {exc}",
                )
            )
            continue
        outbounds.append(outbound)
        disclosures.append(disclosure)
        assert event.project_uuid is not None
        projects[event.event_id] = event.project_uuid
    if not disclosures:
        return immediate
    event_ids = [event.event_id for event in events if event.event_id in projects]
    disclosures_by_event = dict(zip(event_ids, disclosures, strict=True))
    correlated_results: list[DeliveryResult] = []

    def _send() -> object:
        return list(receiver.deliver(consented_batch(outbounds, answer=answer, event_projects=projects)))

    def _classify(value: object) -> Mapping[str, tuple[str, str | None]]:
        nonlocal correlated_results
        correlated_results, outcomes = _correlate_batch_results(value, disclosures_by_event=disclosures_by_event)
        return outcomes

    recovery_attempt_ids = frozenset(disclosure.attempt_id for event_id, disclosure in disclosures_by_event.items() if event_id in recovery_event_ids)
    gated = execute_project_transport_batch(
        disclosures,
        send=_send,
        classify=_classify,
        restart_attempt_ids=recovery_attempt_ids,
    )
    if isinstance(gated, ProjectTransportRefusal):
        for event_id, disclosure in disclosures_by_event.items():
            if disclosure.attempt_id == gated.attempt_id:
                return immediate + [
                    DeliveryResult(
                        event_id=event_id,
                        outcome=DeliveryOutcome.TERMINAL_FAILED,
                        error=f"{gated.category}: {gated.diagnostic}",
                        error_category=gated.category,
                        effect_certainty=DeliveryEffectCertainty.TERMINAL,
                    )
                ]
        raise ProjectTransportResultError(f"transport gate refused uncorrelated attempt {gated.attempt_id}")
    return immediate + correlated_results


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


def _record_one(ledger: SqliteDeliveryLedger, target_id: str, result: DeliveryResult) -> None:
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
    retryable_event_ids: list[str] = []
    with ledger.transaction():
        for result in results:
            _record_one(ledger, target_id, result)
            counts[result.outcome] += 1
            if result.outcome in {
                DeliveryOutcome.PENDING,
                DeliveryOutcome.REJECTED,
                DeliveryOutcome.TRANSIENT,
            }:
                retryable_event_ids.append(result.event_id)
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
        target_id,
        selected=selected,
        counts=counts,
        failures=failures,
        retryable_event_ids=retryable_event_ids,
    )


def _summarize_results(
    target_id: str,
    results: Sequence[DeliveryResult],
    *,
    selected: int,
) -> DispatchSummary:
    """Summarize live WP06-recorded results without writing a second ledger row."""
    counts: dict[DeliveryOutcome, int] = dict.fromkeys(DeliveryOutcome, 0)
    failures: list[DispatchFailure] = []
    retryable_event_ids: list[str] = []
    for result in results:
        counts[result.outcome] += 1
        if result.outcome in {
            DeliveryOutcome.PENDING,
            DeliveryOutcome.REJECTED,
            DeliveryOutcome.TRANSIENT,
        }:
            retryable_event_ids.append(result.event_id)
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
        target_id,
        selected=selected,
        counts=counts,
        failures=failures,
        retryable_event_ids=retryable_event_ids,
    )


# --------------------------------------------------------------------------- #
# Public entry point — the thin select -> post -> record orchestrator           #
# --------------------------------------------------------------------------- #


def dispatch(
    *,
    store: ProjectSyncStore | None = None,
    journal: EventJournal | None = None,
    ledger: SqliteDeliveryLedger | None = None,
    receiver: DeliveryReceiver,
    target: DeliveryTarget | None,
    context: ProjectSyncContext | None = None,
    limit: int | None = None,
    exclude: frozenset[str] = frozenset(),
    recovery_event_ids: frozenset[str] = frozenset(),
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

    *exclude* is an optional in-memory skip set (event IDs) applied to this
    selection only. A multi-batch drain uses it to advance past events that made
    no progress earlier in the same pass, so a permanent content rejection cannot
    head-of-line-block deliverable events behind it. It never mutates the ledger,
    so those events stay selectable on the next drain.
    """
    if target is None:
        return DispatchSummary.empty()
    if store is not None:
        if context is None:
            raise TypeError("dispatch(store=...) requires a caller-owned immutable ProjectSyncContext")
        with store.unit_of_work() as unit:
            phase_journal = EventJournal(unit, store.layout_generation())
            phase_ledger = SqliteDeliveryLedger(unit, store.layout_generation())
            _install_coalescing(phase_ledger)
            selected = _select_undelivered(
                phase_journal,
                phase_ledger,
                target.target_id,
                context=context,
                limit=limit,
                exclude=exclude,
                recovery_event_ids=recovery_event_ids,
            )
        results = _post(
            receiver,
            selected.events,
            selected.answer,
            target=target,
            context=context,
            recovery_event_ids=selected.recovery_event_ids,
        )
        return _summarize_results(target.target_id, results, selected=len(selected.events))
    if journal is None or ledger is None or context is None:
        raise TypeError("dispatch requires either ProjectSyncStore or journal, ledger, and ProjectSyncContext")
    _install_coalescing(ledger)
    selected = _select_undelivered(
        journal,
        ledger,
        target.target_id,
        context=context,
        limit=limit,
        exclude=exclude,
        recovery_event_ids=recovery_event_ids,
    )
    results = _post(
        receiver,
        selected.events,
        selected.answer,
        target=target,
        context=context,
        recovery_event_ids=selected.recovery_event_ids,
    )
    return _record(ledger, target.target_id, results, selected=len(selected.events))


__all__ = [
    "DispatchSummary",
    "dispatch",
    "prepare_event_transport",
]
