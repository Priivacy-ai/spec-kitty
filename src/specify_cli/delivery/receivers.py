"""The single ``DeliveryReceiver`` contract + its three receivers (WP06, IC-04a).

This module is the load-bearing artifact of **FR-014** and the spec's
**DeliveryReceiver** Key Entity. It defines *one* dispatch contract that every
delivery-target type implements, plus the three concrete receivers (Teamspace,
external, stub). The WP07 dispatcher consumes **only** this contract — it must
never branch on target type (``isinstance``), because every §4 aspect is modeled
here as data the dispatcher reads uniformly.

Contract §4 interface matrix (the success boundary):

============  =================================  ====================  ==================
Aspect        Teamspace                          External              Stub
============  =================================  ====================  ==================
Endpoint      ``{server}/api/v1/events/batch/``  operator URL          localhost/in-proc
Auth          ``Bearer <token>``                 operator-supplied/``{}``  none (``{}``)
Gates         SaaS + Private-Teamspace + auth    endpoint-configured   none
Results       success/duplicate/pending/         same mapping          same mapping
              rejected/terminal-failed/transient
Retry         ledger attempt state               ledger attempt state  ledger attempt state
============  =================================  ====================  ==================

Three binding rules (§4):

1. The dispatcher depends on the contract, not target-specific conditionals. Gate
   evaluation is per-receiver *data* (:class:`ReceiverGate`) evaluated by the shared
   :func:`evaluate_gates` helper, never hard-coded in the dispatcher.
2. The stub is a **real** receiver implementing this same contract — not a test-only
   alternate dispatch path. It maps results through the **same** :func:`map_batch_response`
   helper as the wire receivers, so its ledger state is indistinguishable from a
   Teamspace delivery for equivalent payloads (SC-005 / SC-007).
3. Batch *wire* semantics stay compatible with ``contracts/batch-api-contract.md``;
   this mission only shifts the *local* event-row behaviour from delete-on-success to
   ledger-on-success (NFR-006, additive).

A receiver **maps** a transport response to a per-event :class:`DeliveryResult`; it
does **not** write the ledger (the WP07 dispatcher records to the WP05 ledger) and it
does **not** own retry counters (retry is expressed via the result outcome the
dispatcher feeds to the ledger attempt state).

Relationship to :mod:`specify_cli.delivery.interfaces`: WP04 published an early
``DeliveryReceiver`` placeholder there. The contract-faithful §4 protocol lives
*here* (this WP's owned file); ``interfaces.py`` is intentionally not edited (it is
not in this WP's ``owned_files``). WP07 imports the protocol from this module.

Per **C-001** nothing here imports ``sync/queue.py`` or ``specify_cli.events``; the
batch transport pattern mirrors ``sync/batch.py`` as a read-only reference only.
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from threading import Lock
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import requests

from specify_cli.core.batch_partition import create_aware_midpoint

# -- Locked wire constants (S1192: hoisted, used across receivers/tests) --------
BATCH_ENDPOINT_PATH = "/api/v1/events/batch/"
BATCH_TIMEOUT_SECONDS = 60.0
# Loopback, in-process sink for the credential-free stub. Intentionally HTTP: the
# stub never opens a socket (it records in memory); the URL is identity only.
STUB_ENDPOINT_URL = "http://localhost/__spec-kitty-delivery-stub__" + BATCH_ENDPOINT_PATH

_H_AUTHORIZATION = "Authorization"
_H_CONTENT_ENCODING = "Content-Encoding"
_H_CONTENT_TYPE = "Content-Type"
_GZIP = "gzip"
_JSON = "application/json"

_NON_BATCH_BODY_ERROR = "non-batch response shape (no 'results' list)"
_OVERSIZED_ERROR = "payload too large (oversized, permanent)"
_BATCH_OVERSIZED_ERROR = "batch payload too large; retry with a smaller batch"
_TRANSPORT_ERROR_PREFIX = "transport failure"


# -- §4 result vocabulary ------------------------------------------------------


class DeliveryOutcome(StrEnum):
    """The exact six §4 per-event result values (no extras, none missing).

    A ``str`` enum so ``outcome.value`` folds directly onto the WP05 ledger's
    ``record_result`` vocabulary (``success`` / ``duplicate`` / ``pending`` /
    ``rejected`` / ``transient`` / ``terminal_failed``).
    """

    SUCCESS = "success"
    DUPLICATE = "duplicate"
    PENDING = "pending"
    REJECTED = "rejected"
    TERMINAL_FAILED = "terminal_failed"
    TRANSIENT = "transient"


@dataclass(frozen=True)
class OutboundEvent:
    """One event handed to a receiver for delivery (the batch input unit).

    Transport-agnostic and decoupled from the journal table (C-001): it carries
    only the ``event_id`` the result keys back to and the envelope ``payload`` that
    the wire receivers serialize into the batch body. The WP07 dispatcher builds
    these from journal rows; receivers never re-resolve identity.
    """

    event_id: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class DeliveryResult:
    """One per-event delivery outcome — the value the dispatcher maps to a ledger row.

    Transport-agnostic on purpose: ``raw`` keeps the original per-event response
    entry for diagnostics, but the WP05 ledger only needs ``event_id`` + ``outcome``
    (+ optional ``http_status`` / ``error``). ``pending`` is a legitimate
    non-terminal outcome and is never coerced to ``transient``.
    """

    event_id: str
    outcome: DeliveryOutcome
    http_status: int | None = None
    error: str | None = None
    raw: Mapping[str, Any] | None = None


# -- §4 gates: per-receiver declarative data, evaluated by a shared helper ------


class GateKind(StrEnum):
    """The delivery-eligibility requirements a receiver may declare (contract §4).

    Each value names a field on :class:`GateContext`; evaluation reads that field.
    Gates are pure *data* — they never read globals/env — so the dispatcher can
    answer "are this receiver's gates satisfied?" uniformly (FR-014, §4 rule 1).

    **There is deliberately no consent member (#3030 FR-001, declined 2026-07-30.)**
    FR-001 asked for exactly that — "a new ``GateKind`` plus a consent port injected
    into the dispatcher" — and spec.md names its absence the *first* root cause of the
    2026-07-27 incident. It was audited and declined on three grounds, none of which
    is "too hard":

    1. **The per-project half is superseded, by an explicit decision.** A gate cannot
       carry it: :class:`GateContext` is run-scoped booleans with no project
       dimension, and :func:`evaluate_gates` yields one decision per receiver per
       run. C-003 (2026-07-29) settled that project consent is represented **once**,
       in selection, via the stored ``project_uuid`` column plus ``consent.py``'s
       resolver. A ``GateKind`` would be the second representation C-003 forbids.
    2. **The machine-level half already ships here, in a better form.** The one thing
       a run-scoped gate *can* express is a whole-batch, pre-network abort — and
       :func:`_cross_project_refusal` is that, in this module, at that position. It is
       strictly better than a gate would have been: a blocked
       :class:`GateDecision` is binary and has no per-event outcome vocabulary, so a
       gate could only have aborted the drain. Read
       :func:`_cross_project_refusal`'s note on why the refusal must be
       ``TRANSIENT``: routing a locally-decided batch refusal to ``TERMINAL_FAILED``
       permanently destroyed the *consented* project's events too, making the safety
       net worse than the leak. A gate has no way to say "refuse this window without
       parking these events".
    3. **The one residual case is not computable, so a gate would be decoration.**
       That case is real: when the machine-global consent index is unreadable or
       corrupt, ``SyncConfig._load`` returns ``{}`` (its documented "missing or
       invalid" behaviour), so every project on the machine resolves to
       ``ConsentLevel.ABSENT`` with reason "no consent record" — a machine fault
       silently reported as twenty projects that never opted in, and a drain that
       delivers nothing while looking idle. But **no layer can currently tell
       "unreadable" from "absent"**: the distinction is destroyed in ``_load``, below
       both ``consent.py`` and this module. Nothing could populate a
       ``consent_resolvable`` context field truthfully, so the gate would report a
       fact no one can observe. Fixing that conflation in ``sync/config.py`` is the
       prerequisite, and it is an observability defect, not a delivery gate.

       Note the asymmetry: a resolver that *raises* already propagates out of
       ``dispatch`` — loud, and not the gap. Only the swallowed-fault path is silent.

    If that conflation is ever fixed, revisit — but as a reported abort, and only
    after deciding what a blocked run does to the events it did not attempt.
    """

    SAAS_ENABLED = "saas_enabled"
    PRIVATE_TEAMSPACE = "private_teamspace"
    AUTH = "auth_present"
    ENDPOINT_CONFIGURED = "endpoint_configured"


@dataclass(frozen=True)
class GateContext:
    """Ambient delivery-eligibility facts the dispatcher supplies at evaluation time.

    All fields are explicit so no gate predicate ever reaches into global/env state
    (FR-014). The dispatcher populates this (e.g. ``endpoint_configured`` from the
    receiver's ``endpoint_url``, ``auth_present`` from resolved credentials) before
    calling :func:`evaluate_gates`.
    """

    saas_enabled: bool = False
    private_teamspace: bool = False
    auth_present: bool = False
    endpoint_configured: bool = False


@dataclass(frozen=True)
class ReceiverGate:
    """A single declarative delivery-eligibility requirement.

    Pure data: it names a :class:`GateKind`; :meth:`is_satisfied` reads the matching
    :class:`GateContext` field. No callable reaches into global state.
    """

    kind: GateKind

    @property
    def name(self) -> str:
        return self.kind.value

    def is_satisfied(self, context: GateContext) -> bool:
        return bool(getattr(context, self.kind.value))


@dataclass(frozen=True)
class GateDecision:
    """Outcome of evaluating a receiver's whole gate set against a context."""

    satisfied: bool
    unsatisfied: tuple[ReceiverGate, ...] = ()

    @property
    def blocked(self) -> bool:
        return not self.satisfied


def evaluate_gates(receiver: DeliveryReceiver, context: GateContext) -> GateDecision:
    """Evaluate every gate a *receiver* declares against *context*.

    A receiver with **no** gates (the stub) yields an all-satisfied decision, not an
    error. This is the single seam the WP07 dispatcher uses — there is no per-target
    ``if`` anywhere in the gate path.
    """
    unsatisfied = tuple(gate for gate in receiver.gates() if not gate.is_satisfied(context))
    return GateDecision(satisfied=not unsatisfied, unsatisfied=unsatisfied)


# -- The one contract (§4) -----------------------------------------------------


@runtime_checkable
class DeliveryReceiver(Protocol):
    """The single dispatch contract every delivery-target type implements (FR-014).

    Five §4 aspects: :attr:`endpoint_url`, :meth:`auth_headers`, :meth:`gates`,
    :meth:`deliver` (per-event result mapping), and retry-via-:class:`DeliveryResult`.
    The dispatcher drives any receiver through this protocol with no target-specific
    conditionals.
    """

    @property
    def endpoint_url(self) -> str: ...

    def auth_headers(self) -> dict[str, str]: ...

    def gates(self) -> tuple[ReceiverGate, ...]: ...

    def deliver(self, batch: Sequence[OutboundEvent]) -> Sequence[DeliveryResult]: ...


# -- Shared transport poster seam (testable: inject a fake) --------------------


@runtime_checkable
class HttpResponse(Protocol):
    """The minimal response surface the receivers read (``requests.Response`` fits)."""

    @property
    def status_code(self) -> int: ...

    def json(self) -> Any: ...


class HttpPoster(Protocol):
    """A POST transport. ``requests.post`` is the default; tests inject a fake."""

    def __call__(self, url: str, *, data: bytes, headers: Mapping[str, str], timeout: float) -> HttpResponse: ...


def default_http_poster(url: str, *, data: bytes, headers: Mapping[str, str], timeout: float) -> HttpResponse:
    """Default poster: a thin, typed wrapper over ``requests.post`` (mirrors batch.py).

    The single public name for the default poster (#2884) — cross-package
    callers (e.g. ``sync.history_import``) and in-module default-arg sites
    all bind this one name rather than an underscore-private alias.
    """
    return requests.post(url, data=data, headers=dict(headers), timeout=timeout)


# -- The shared result mapper (one mapper, reused by all three receivers) -------


# -- Cross-project refusal + terminal rejection (spec-kitty#3030, WP01) --------

#: Server ``error_category`` values that mean "never retry this event".
#:
#: Must match the literal the SaaS ingress emits — see ``spec-kitty-saas#585``
#: FR-004, which sends a per-event refusal inside the 200 ``results`` list. Before
#: this, ``TERMINAL_FAILED`` was reachable from exactly one predicate (an oversized
#: single event), so *every* server refusal became ``REJECTED`` and was retried
#: forever with no ceiling — the "4,141 rejected / 0 terminal failures" signal in
#: the 2026-07-27 incident (folds spec-kitty#3005).
TERMINAL_REJECTION_CATEGORIES: frozenset[str] = frozenset({"project_not_consented", "project_refused"})

_CROSS_PROJECT_ERROR = "refused before send: batch spans more than one project ({projects}); authorization and delivery must be scoped to the same project"


def _event_project(event: OutboundEvent) -> str | None:
    """Resolve an event's project identity from the envelope, or ``None``.

    Mirrors the three sites identity is written to (``namespace.project_uuid``,
    top-level, ``payload.project_uuid``). ``None`` means *unresolvable here* — it is
    deliberately **not** treated as a project, because counting it as one would
    refuse ordinary batches containing a legacy identity-less row. Denying
    unresolvable identity is the selection seam's job, where the stored column is
    the sole authority.
    """
    payload = event.payload
    namespace = payload.get("namespace")
    if isinstance(namespace, Mapping) and namespace.get("project_uuid"):
        return str(namespace["project_uuid"])
    if payload.get("project_uuid"):
        return str(payload["project_uuid"])
    subject = payload.get("subject")
    if isinstance(subject, Mapping) and subject.get("project_uuid"):
        return str(subject["project_uuid"])
    return None


def _cross_project_refusal(
    events: Sequence[OutboundEvent],
) -> list[DeliveryResult] | None:
    """Refuse a batch that spans >1 project, **before** any network call (FR-004).

    Belt-and-braces behind the selection predicate: if selection ever regresses,
    this turns a silent cross-project leak into a loud refusal rather than letting
    it reach the wire.

    The refusal is ``TRANSIENT``, deliberately **not** ``TERMINAL_FAILED``. This
    net fires on a batch whose events are individually deliverable — what
    regressed is the *window*, not the events. ``TERMINAL_FAILED`` routes to
    ``ledger.record_terminal_failed`` -> ``STATUS_TERMINAL_FAILED``, which
    ``select_undelivered`` excludes **forever**: one refused window permanently
    destroyed the *consented* project's events as well, making the safety net more
    destructive than the leak it catches. Spec US1a AS-1 requires the opposite —
    refuse "without mutating delivery state or bumping retry counts".

    ``TRANSIENT`` is the closest outcome the §4 vocabulary has to "not attempted,
    still selectable": it is non-terminal, so the events round-trip back into
    ``select_undelivered`` and deliver once the window narrows to one project; it
    carries no ceiling that could later escalate to a terminal park; and unlike
    ``PENDING`` it does not falsely claim the server accepted anything. The
    residual deviation from AS-1 is one ``attempt_count`` increment plus a
    ``last_error`` stamp per event — provenance, not destruction. Expressing the
    refusal with **zero** ledger writes needs a seventh, local-only outcome the
    dispatcher skips recording, which cannot be wired truthfully without also
    changing ``DispatchSummary`` and its per-field combiner in
    ``cli/commands/sync.py``.
    """
    projects = {p for p in (_event_project(e) for e in events) if p is not None}
    if len(projects) <= 1:
        return None
    error = _CROSS_PROJECT_ERROR.format(projects=", ".join(sorted(projects)))
    return _all_outcome(events, DeliveryOutcome.TRANSIENT, http_status=None, error=error, body=None)


_PER_EVENT_OUTCOME: dict[str, DeliveryOutcome] = {
    "success": DeliveryOutcome.SUCCESS,
    "accepted": DeliveryOutcome.SUCCESS,
    "warning": DeliveryOutcome.SUCCESS,
    "duplicate": DeliveryOutcome.DUPLICATE,
    "pending": DeliveryOutcome.PENDING,
    "queued": DeliveryOutcome.PENDING,
    "rejected": DeliveryOutcome.REJECTED,
}


def _build_payload(events: Sequence[OutboundEvent]) -> bytes:
    """Serialize the batch body exactly as the wire contract expects (§3.1)."""
    return json.dumps({"events": [dict(e.payload) for e in events]}).encode("utf-8")


def _error_text(entry: Mapping[str, Any]) -> str | None:
    """Pull a rejection reason, accepting both ``error_message`` and ``error`` (§3.2)."""
    reason = entry.get("error_message") or entry.get("error")
    return None if reason is None else str(reason)


def _looks_like_batch_response(body: Mapping[str, Any] | None) -> bool:
    return isinstance(body, Mapping) and isinstance(body.get("results"), list)


def _all_outcome(
    events: Sequence[OutboundEvent],
    outcome: DeliveryOutcome,
    *,
    http_status: int | None,
    error: str | None,
    body: Mapping[str, Any] | None,
) -> list[DeliveryResult]:
    """Map every event in a batch to the same outcome (batch-level classification)."""
    return [
        DeliveryResult(
            event_id=event.event_id,
            outcome=outcome,
            http_status=http_status,
            error=error,
            raw=body,
        )
        for event in events
    ]


def _map_single_ok(event: OutboundEvent, entry: Mapping[str, Any] | None) -> DeliveryResult:
    """Map one per-event 200 result. Absent entry → ``pending`` (not silent success)."""
    if entry is None:
        return DeliveryResult(event_id=event.event_id, outcome=DeliveryOutcome.PENDING, http_status=200)
    status = str(entry.get("status", "")).strip().lower()
    outcome = _PER_EVENT_OUTCOME.get(status)
    if outcome is None:
        return DeliveryResult(
            event_id=event.event_id,
            outcome=DeliveryOutcome.REJECTED,
            http_status=200,
            error=_error_text(entry) or f"unknown per-event status: {status!r}",
            raw=entry,
        )
    error = _error_text(entry) if outcome is DeliveryOutcome.REJECTED else None
    if outcome is DeliveryOutcome.REJECTED:
        category = str(entry.get("error_category", "")).strip().lower()
        if category in TERMINAL_REJECTION_CATEGORIES:
            # FR-014: a refusal the server will never accept is terminal, not
            # retryable. Without this the event re-POSTs on every drain forever
            # and is reported as a non-failure.
            outcome = DeliveryOutcome.TERMINAL_FAILED
    return DeliveryResult(event_id=event.event_id, outcome=outcome, http_status=200, error=error, raw=entry)


def _map_ok_results(events: Sequence[OutboundEvent], body: Mapping[str, Any] | None) -> list[DeliveryResult]:
    """Map an HTTP 200 batch response. A non-batch shape → transient (defensive)."""
    if not _looks_like_batch_response(body):
        return _all_outcome(events, DeliveryOutcome.TRANSIENT, http_status=200, error=_NON_BATCH_BODY_ERROR, body=body)
    assert body is not None  # narrowed by _looks_like_batch_response
    by_id: dict[Any, Mapping[str, Any]] = {entry.get("event_id"): entry for entry in body["results"] if isinstance(entry, Mapping)}
    return [_map_single_ok(event, by_id.get(event.event_id)) for event in events]


def _structured_details(body: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    """Extract a structured per-event ``details`` list from an HTTP 400 body (§3.3)."""
    if body is None:
        return []
    raw = body.get("details")
    if isinstance(raw, str) and raw.strip():
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return []
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, Mapping)]
    return []


def _detail_reason(detail: Mapping[str, Any], fallback: str) -> str:
    return str(detail.get("detail") or detail.get("error") or detail.get("reason") or fallback)


def _map_400(events: Sequence[OutboundEvent], body: Mapping[str, Any] | None) -> list[DeliveryResult]:
    """HTTP 400 → per-event ``rejected`` (content rejection; payload retained, retryable)."""
    top_error = str((body or {}).get("error", "batch validation failed"))
    by_id = {detail.get("event_id"): detail for detail in _structured_details(body)}
    out: list[DeliveryResult] = []
    for event in events:
        detail = by_id.get(event.event_id)
        reason = _detail_reason(detail, top_error) if detail is not None else top_error
        out.append(
            DeliveryResult(
                event_id=event.event_id,
                outcome=DeliveryOutcome.REJECTED,
                http_status=400,
                error=reason,
                raw=body,
            )
        )
    return out


def _is_oversized(http_status: int, body: Mapping[str, Any] | None) -> bool:
    """Whether a batch failure is an oversized/permanent failure (→ terminal-failed)."""
    if http_status == 413:
        return True
    text = str(body.get("error", "")).lower() if body else ""
    return "too large" in text or "oversized" in text


def _http_error_text(http_status: int, body: Mapping[str, Any] | None) -> str:
    reason = body.get("error") if body else None
    return str(reason) if reason else f"HTTP {http_status}"


def _map_batch_failure(events: Sequence[OutboundEvent], *, http_status: int, body: Mapping[str, Any] | None) -> list[DeliveryResult]:
    """Classify a non-200 batch response.

    Oversized/permanent → ``terminal_failed`` (FR-015); 400 content failure →
    per-event ``rejected``; 401/403/408/429/5xx/other → ``transient`` for the whole
    batch (do **not** poison per-event retry counts — spec "content rejection vs
    transient failure").
    """
    if _is_oversized(http_status, body) and len(events) == 1:
        return _all_outcome(events, DeliveryOutcome.TERMINAL_FAILED, http_status=http_status, error=_OVERSIZED_ERROR, body=body)
    if _is_oversized(http_status, body):
        return _all_outcome(
            events,
            DeliveryOutcome.TRANSIENT,
            http_status=http_status,
            error=_BATCH_OVERSIZED_ERROR,
            body=body,
        )
    if http_status == 400:
        return _map_400(events, body)
    return _all_outcome(
        events,
        DeliveryOutcome.TRANSIENT,
        http_status=http_status,
        error=_http_error_text(http_status, body),
        body=body,
    )


def map_batch_response(
    batch: Sequence[OutboundEvent],
    *,
    http_status: int,
    body: Mapping[str, Any] | None,
) -> list[DeliveryResult]:
    """The single response→result mapper shared by Teamspace / external / stub.

    Maps a batch HTTP response to one :class:`DeliveryResult` per event using the
    contract §4 vocabulary. Having one mapper (not three) is what makes the stub's
    ledger state identical to Teamspace's for equivalent payloads (SC-007).
    """
    if http_status == 200:
        return _map_ok_results(batch, body)
    return _map_batch_failure(batch, http_status=http_status, body=body)


def _safe_json(response: HttpResponse) -> Mapping[str, Any] | None:
    """Parse a response body, returning ``None`` for non-JSON / non-object bodies."""
    try:
        body = response.json()
    except (ValueError, json.JSONDecodeError):
        return None
    return body if isinstance(body, Mapping) else None


# -- Poison-batch bisection (FR-001..FR-004, #2736) -----------------------------


def _is_poison_400(status: int | None, body: Mapping[str, Any] | None) -> bool:
    """Whether a response is the #2736 poison signature: whole-batch 400, no details.

    A content-rejection HTTP 400 that carries only a single top-level ``error`` (no
    structured per-event ``details``) and is not an oversized/permanent failure. That
    is the exact case where the all-or-nothing server hides *which* event is invalid,
    so the culprit can only be found by bisection. A 400 that already carries per-event
    ``details`` needs no bisection — it is mapped directly by :func:`map_batch_response`.
    """
    if status != 400:
        return False
    if _is_oversized(400, body):
        return False
    return not _structured_details(body)


def _wp_id_of(event: OutboundEvent) -> Hashable:
    """Create-aware split key: the event's ``wp_id`` when resolvable, else ``event_id``.

    Falls back to the always-unique ``event_id`` so an event without a resolvable
    ``wp_id`` can never falsely read as an adjacent same-key pair at the midpoint.
    """
    inner = event.payload.get("payload")
    if isinstance(inner, Mapping):
        wp_id = inner.get("wp_id")
        if wp_id is not None:
            return str(wp_id)
    return event.event_id


# -- The HTTP receivers (Teamspace + external share the transport) -------------


class _HttpReceiver:
    """Shared HTTP-batch transport + mapping for the wire receivers (Teamspace/external).

    Subclasses declare :attr:`endpoint_url`, :meth:`auth_headers`, and :meth:`gates`;
    delivery (build → gzip → POST → map) is shared so the result-mapping logic is
    never duplicated (S1192). A transport-level timeout/connection error maps to a
    batch-wide ``transient`` (http_status ``None``) without poisoning retries.
    """

    _poster: HttpPoster

    @property
    def endpoint_url(self) -> str:  # pragma: no cover - overridden
        raise NotImplementedError

    def auth_headers(self) -> dict[str, str]:
        return {}

    def gates(self) -> tuple[ReceiverGate, ...]:
        return ()

    def deliver(self, batch: Sequence[OutboundEvent]) -> Sequence[DeliveryResult]:
        events = list(batch)
        if not events:
            return []
        refusal = _cross_project_refusal(events)
        if refusal is not None:
            return refusal
        return self._bisect_send(events)

    def _attempt_batch_send(self, events: Sequence[OutboundEvent]) -> tuple[int | None, Mapping[str, Any] | None]:
        """POST *events* once and return ``(status, body)``; a single clean send seam.

        A transport-level timeout/connection error returns ``(None, {"error": <exc>})``
        — a ``None`` status still signals "do not split" to the recursion (classify the
        whole batch as ``transient`` without splitting it, since splitting a transport
        failure would only multiply transients), while the body's ``error`` threads the
        underlying exception detail (timeout vs connection-refused vs DNS) through to
        the mapped result so it is not lost behind the bare ``transport failure``
        constant.
        """
        headers = {**self.auth_headers(), _H_CONTENT_ENCODING: _GZIP, _H_CONTENT_TYPE: _JSON}
        payload = gzip.compress(_build_payload(events))
        try:
            response = self._poster(self.endpoint_url, data=payload, headers=headers, timeout=BATCH_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            return None, {"error": str(exc)}
        return response.status_code, _safe_json(response)

    def _bisect_send(self, events: Sequence[OutboundEvent]) -> list[DeliveryResult]:
        """Deliver *events*, recursively isolating a poison-batch culprit (#2736).

        On the poison signature (:func:`_is_poison_400`) with ``len > 1`` the batch is
        split at a create-aware midpoint and BOTH halves are re-POSTed **sequentially,
        left-before-right** — that ordering is what guarantees a batch-spanning
        create/status pair keeps ``create``-before-``status`` receipt order (no midpoint
        can, so the recursion must). The ``len == 1`` base maps the isolated culprit to
        its own ``rejected`` reason; every other response defers to the shared mapper.
        """
        if not events:
            # Self-defending leaf (mirrors deliver()'s guard): the midpoint clamp
            # ``max(1, min(mid, len - 1))`` collapses to ``1`` for ``len == 0``, which
            # would split ``[]`` into two more empty batches and recurse forever if a
            # future caller ever reached _bisect_send([]) directly. Short-circuit
            # before any POST.
            return []
        status, body = self._attempt_batch_send(events)
        if status is None:
            detail = body.get("error") if body else None
            error = f"{_TRANSPORT_ERROR_PREFIX}: {detail}" if detail else _TRANSPORT_ERROR_PREFIX
            return _all_outcome(
                events,
                DeliveryOutcome.TRANSIENT,
                http_status=None,
                error=error,
                body=None,
            )
        if _is_poison_400(status, body):
            if len(events) == 1:
                return _map_400(events, body)
            mid = create_aware_midpoint(events, key_of=_wp_id_of)
            # R1 (#2736): the primitive returns an EDGE index for a degenerate
            # batch whose straddling events share a wp_id. For a 2-element
            # same-wp_id create/status pair the reachable edge value is ``0``
            # (``len`` is unreachable — the right-nudge only snaps left). Feeding
            # that raw index back would make one half empty and the other the full
            # batch, so the right recursion never shrinks -> RecursionError
            # (NFR-002 termination breach). The two-sided clamp keeps ``len``
            # guarded defensively even though only ``0`` is reachable today.
            # Clamp to 0 < mid < len so both halves are strictly non-empty and
            # smaller. Only reached when len > 1, so len - 1 >= 1 — always valid.
            # Splitting a same-key pair is correct: the sequential left-before-right
            # recursion still delivers create (left) before status (right).
            mid = max(1, min(mid, len(events) - 1))
            return self._bisect_send(events[:mid]) + self._bisect_send(events[mid:])
        return map_batch_response(events, http_status=status, body=body)


# -- Module-level gate sets (data, hoisted once) -------------------------------

_TEAMSPACE_GATES: tuple[ReceiverGate, ...] = (
    ReceiverGate(kind=GateKind.SAAS_ENABLED),
    ReceiverGate(kind=GateKind.PRIVATE_TEAMSPACE),
    ReceiverGate(kind=GateKind.AUTH),
)
_EXTERNAL_GATES: tuple[ReceiverGate, ...] = (ReceiverGate(kind=GateKind.ENDPOINT_CONFIGURED),)


class TeamspaceReceiver(_HttpReceiver):
    """The production receiver: the SaaS batch path expressed through the §4 contract.

    Endpoint is ``{resolved_server_url}/api/v1/events/batch/`` (the resolved URL comes
    from the WP04 target authority — never re-derived here, contract §1 / FR-016);
    auth is ``Bearer <token>``; gates are SaaS-enabled + Private-Teamspace + auth.
    """

    def __init__(
        self,
        *,
        resolved_server_url: str,
        auth_token: str,
        poster: HttpPoster = default_http_poster,
    ) -> None:
        self._server_url = resolved_server_url.rstrip("/")
        self._auth_token = auth_token
        self._poster = poster

    @property
    def endpoint_url(self) -> str:
        return f"{self._server_url}{BATCH_ENDPOINT_PATH}"

    def auth_headers(self) -> dict[str, str]:
        return {_H_AUTHORIZATION: f"Bearer {self._auth_token}"}

    def gates(self) -> tuple[ReceiverGate, ...]:
        return _TEAMSPACE_GATES


class ExternalReceiver(_HttpReceiver):
    """An operator-owned endpoint via the **same** ledger machinery (FR-007).

    Generalizes the target: it speaks the batch contract and reuses the shared
    mapper, so the stub is just a special case. Its only gate is
    ``endpoint-configured`` — **no** Teamspace gating (no SaaS-enabled, no
    Private-Teamspace, no Bearer requirement). Auth is operator-supplied or ``{}``.
    """

    def __init__(
        self,
        *,
        endpoint_url: str,
        auth_headers: Mapping[str, str] | None = None,
        poster: HttpPoster = default_http_poster,
    ) -> None:
        self._endpoint_url = endpoint_url
        self._auth_headers = dict(auth_headers) if auth_headers else {}
        self._poster = poster

    @property
    def endpoint_url(self) -> str:
        return self._endpoint_url

    def auth_headers(self) -> dict[str, str]:
        return dict(self._auth_headers)

    def gates(self) -> tuple[ReceiverGate, ...]:
        return _EXTERNAL_GATES


class StubReceiver:
    """A localhost / in-process sink with **no credentials** (FR-008, US3, SC-005).

    A **real** :class:`DeliveryReceiver` living in the production module — not a
    test-only dispatch fork (§4 rule 2). It records received events for assertions
    and maps outcomes through the **same** :func:`map_batch_response` path as the
    wire receivers, so the ledger state it produces is indistinguishable from a
    Teamspace delivery for equivalent payloads (SC-007). A repeat ``event_id`` maps
    to ``duplicate``, mirroring Teamspace idempotency (NFR-003). The sink is guarded
    by a lock so a daemon test exercising it concurrently cannot corrupt it.
    """

    def __init__(self, *, endpoint_url: str = STUB_ENDPOINT_URL) -> None:
        self._endpoint_url = endpoint_url
        self._received: list[OutboundEvent] = []
        self._seen_ids: set[str] = set()
        self._lock = Lock()

    @property
    def endpoint_url(self) -> str:
        return self._endpoint_url

    def auth_headers(self) -> dict[str, str]:
        return {}

    def gates(self) -> tuple[ReceiverGate, ...]:
        return ()

    def deliver(self, batch: Sequence[OutboundEvent]) -> Sequence[DeliveryResult]:
        events = list(batch)
        if not events:
            return []
        with self._lock:
            synthetic = [{"event_id": e.event_id, "status": self._record(e)} for e in events]
        return map_batch_response(events, http_status=200, body={"results": synthetic})

    def _record(self, event: OutboundEvent) -> str:
        """Record *event* in the sink; return its wire status (caller holds the lock)."""
        if event.event_id in self._seen_ids:
            return "duplicate"
        self._seen_ids.add(event.event_id)
        self._received.append(event)
        return "success"

    def received_events(self) -> tuple[OutboundEvent, ...]:
        with self._lock:
            return tuple(self._received)

    def received_event_ids(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(event.event_id for event in self._received)


if TYPE_CHECKING:
    # Compile-time proof that each concrete receiver satisfies the one §4 protocol so
    # the WP07 dispatcher binds to the abstraction with no target-type branches.
    def _protocol_conformance(
        teamspace: TeamspaceReceiver, external: ExternalReceiver, stub: StubReceiver
    ) -> tuple[DeliveryReceiver, DeliveryReceiver, DeliveryReceiver]:
        return teamspace, external, stub


__all__ = [
    "BATCH_ENDPOINT_PATH",
    "BATCH_TIMEOUT_SECONDS",
    "STUB_ENDPOINT_URL",
    "default_http_poster",
    "DeliveryOutcome",
    "OutboundEvent",
    "DeliveryResult",
    "GateKind",
    "GateContext",
    "ReceiverGate",
    "GateDecision",
    "DeliveryReceiver",
    "HttpResponse",
    "HttpPoster",
    "evaluate_gates",
    "map_batch_response",
    "TeamspaceReceiver",
    "ExternalReceiver",
    "StubReceiver",
]
