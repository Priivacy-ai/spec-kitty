"""PROVENANCE + PREFLIGHT + UPLOAD for ``sync import-history`` (WP-Y5, #2262).

Takes the synthesized envelope stream and materializes it into the SaaS
projection, reusing the WP06 delivery receiver as the transport seam rather
than hand-rolling HTTP:

* **PROVENANCE (stage 6):** a per-envelope ``envelope_sha256`` manifest, hashed
  with the same canonical-JSON shape the migration dry-run uses.
* **PREFLIGHT (stage 7):** POST each chunk to ``/api/v1/events/preflight/`` and
  gate on ``accepted`` — the server validates shape/ingress without mutating
  state. Every chunk is preflighted *before* any chunk uploads, so a *preflight*
  rejection anywhere leaves the projection untouched (fail-closed, INV-6).
* **UPLOAD (stage 8):** chunk the stream mission-atomically (no mission ever
  straddles a chunk boundary — see :func:`_chunked`) and hand each chunk to a
  :class:`DeliveryReceiver` (gzip + POST + response mapping + poison-batch
  bisection all live there). Delivery stops at the first chunk that reports any
  failure outcome, so a mid-upload delivery failure leaves at most a partial —
  and because chunks are Lamport-ordered and mission-atomic, any delivered
  prefix is a valid ordered prefix of whole missions (never an orphan). The
  report flags that state (``UploadReport.partial``) and a re-run completes
  idempotently: the server dedups on ``event_id``, so already-ingested events
  return ``duplicate``.

The transport is injectable: production passes an authed ``TeamspaceReceiver``
and the default ``requests`` poster; tests pass a ``StubReceiver`` and a fake
poster, so the whole stage runs with no network.

**CONSENT (#3030 FR-028).** Until 2026-07-30 this whole stage was ungated: a
grep for consent across ``sync/history_import/`` returned zero hits, and the only
gate was ``_resolve_gated_receiver``'s ``GateKind`` set — the exact set the
mission's root-cause §1 names as having no consent field — plus a
``Mode.TEAMSPACE`` check. The path is single-project by construction
(``build_import_plan`` yields one ``plan.identity.project_uuid``), so it held the
uuid and never asked it. It is now gated by construction rather than by another
check: :func:`_consented_batches` mints one
:class:`~specify_cli.delivery.consent_gate.ConsentedBatch` per chunk, which is
the only thing ``receiver.deliver`` accepts, and it runs **before the preflight**
— because ``run_server_preflight`` is a second sink carrying the same envelopes,
and a gate placed at the delivery call alone would have leaked every one of them.
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

from specify_cli.core.contract_gate import validate_outbound_payload
from specify_cli.delivery.consent_gate import (
    ConsentAnswer,
    ConsentedBatch,
    UnconsentedDelivery,
    consented_batch,
    resolve_consent_answer,
    resolve_envelope_project,
)
from specify_cli.delivery.receivers import (
    BATCH_TIMEOUT_SECONDS,
    DeliveryOutcome,
    DeliveryReceiver,
    DeliveryResult,
    HttpPoster,
    OutboundEvent,
    default_http_poster,
)
from specify_cli.migration.envelope_seam import envelope_sha256
from specify_cli.status import MISSION_CREATED

_PREFLIGHT_ENDPOINT_PATH = "/api/v1/events/preflight/"
# One delivery timeout policy for the whole SaaS transport: reuse the receiver's
# canonical batch timeout rather than re-declaring the same 60s value (#2884).
_PREFLIGHT_TIMEOUT_SECONDS = BATCH_TIMEOUT_SECONDS
# Conservative per-request size: well under the server's 1000-event cap and its
# 512 KiB decompressed byte ceiling. The receiver still auto-bisects on a 413.
_IMPORT_CHUNK_SIZE = 500
# The server's hard per-batch envelope cap. A single mission larger than
# _IMPORT_CHUNK_SIZE is deliberately NOT split (mission-atomic chunking, see
# _chunked) and becomes one oversized chunk — safe up to this many events per
# batch. A mission that exceeds even this cap is caught fail-closed before any
# network round-trip by _assert_batches_within_cap.
_SERVER_MAX_BATCH_SIZE = 1000
_MAX_REJECTED_SAMPLES = 5

# The outbound-envelope contract context every producer validates against
# (sync.emitter/batch/client all pass this to validate_outbound_payload). The
# import producer runs the same offline gate so its hand-assembled prefix
# envelopes fail fast locally, consistent with the rest of the fleet (#2884).
_ENVELOPE_CONTRACT_CONTEXT = "envelope"

Envelope = Mapping[str, Any]


# ── provenance (stage 6) ──────────────────────────────────────────────────────
#
# The canonical-JSON SHA-256 recipe is shared with the migration dry-run's
# row mapping — one owner (mission_state.envelope_sha256, re-exported through
# the envelope_seam), so the two checksums cannot drift (#2884).


@dataclass(frozen=True)
class ImportProvenanceEntry:
    """One provenance record for the import audit manifest."""

    event_id: str
    event_type: str
    envelope_sha256: str
    # Import envelopes are synthesized / replayed, not lifted verbatim from a
    # single on-disk JSONL row, so there is no row_sha256 to anchor.
    row_sha256: str | None = None


def build_provenance_manifest(envelopes: Sequence[Envelope]) -> list[ImportProvenanceEntry]:
    return [
        ImportProvenanceEntry(
            event_id=str(env["event_id"]),
            event_type=str(env["event_type"]),
            envelope_sha256=envelope_sha256(env),
        )
        for env in envelopes
    ]


# ── preflight (stage 7) ───────────────────────────────────────────────────────


class PreflightRejected(RuntimeError):
    """Raised when the server preflight refuses a chunk (fail-closed)."""

    def __init__(self, payload: Mapping[str, Any]) -> None:
        self.payload = dict(payload)
        reconciliation = self.payload.get("reconciliation") or self.payload.get("error") or self.payload
        super().__init__(f"server preflight rejected the batch: {reconciliation}")


def run_server_preflight(
    envelopes: Sequence[Envelope],
    *,
    server_url: str,
    auth_token: str,
    poster: HttpPoster = default_http_poster,
) -> dict[str, Any]:
    """POST ``{"events": [...]}`` to the preflight endpoint; raise if not accepted."""
    url = server_url.rstrip("/") + _PREFLIGHT_ENDPOINT_PATH
    body = gzip.compress(json.dumps({"events": [dict(env) for env in envelopes]}, separators=(",", ":")).encode("utf-8"))
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Encoding": "gzip",
        "Content-Type": "application/json",
    }
    try:
        response = poster(url, data=body, headers=headers, timeout=_PREFLIGHT_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        # A transport failure (unreachable host, timeout, TLS reset) during
        # preflight must fail closed as a graceful rejection, not escape as a raw
        # traceback — the delivery path maps the same error to a batch failure
        # (receivers.py::_attempt_batch_send); preflight now matches (#2884).
        raise PreflightRejected({"error": f"preflight transport failed: {exc}"}) from exc
    try:
        payload = response.json()
    except Exception as exc:  # non-JSON (5xx / proxy error) is a hard, fail-closed stop
        raise PreflightRejected({"error": f"preflight response was not JSON (HTTP {response.status_code})"}) from exc
    if response.status_code != 200 or not payload.get("accepted"):
        raise PreflightRejected(payload)
    return dict(payload)


def validate_import_envelopes(envelopes: Sequence[Envelope]) -> None:
    """Run the offline outbound-envelope contract gate over every envelope.

    Every other envelope producer (``sync.emitter``/``batch``/``client``)
    validates at emit/enqueue time; the import producer runs the same gate so
    its hand-assembled ``MissionCreated``/``WPCreated`` prefix envelopes fail
    fast locally instead of only at the server-preflight round-trip — closing
    the defense-in-depth gap the #2884 review flagged. Raises
    :class:`~specify_cli.core.contract_gate.ContractViolationError` on the first
    offending envelope, before any network call.
    """
    for env in envelopes:
        validate_outbound_payload(dict(env), _ENVELOPE_CONTRACT_CONTEXT)


def _assert_batches_within_cap(chunks: Sequence[Sequence[Envelope]]) -> None:
    """Fail closed if any mission-atomic chunk exceeds the server's batch cap.

    Mission-atomic chunking (:func:`_chunked`) never splits a mission, so a
    single mission larger than ``_SERVER_MAX_BATCH_SIZE`` becomes one oversized
    chunk that the server would reject at preflight. Catch it here, before the
    network round-trip, with an actionable message rather than an opaque
    server-side rejection (#2884).
    """
    for chunk in chunks:
        if len(chunk) > _SERVER_MAX_BATCH_SIZE:
            raise PreflightRejected(
                {
                    "error": (
                        f"a single mission is {len(chunk)} events, over the server's "
                        f"{_SERVER_MAX_BATCH_SIZE}-event batch cap; mission-atomic chunking "
                        "cannot split it. Import this mission on its own or trim its history."
                    )
                }
            )


# ── upload (stage 8) ──────────────────────────────────────────────────────────


@dataclass
class UploadReport:
    """Tally of per-event delivery outcomes for one import run.

    ``partial`` marks the distinct third state between success and total
    failure: a chunk failed mid-run, delivery stopped there, and
    ``undelivered_event_count`` events in later chunks were never attempted.
    ``delivered_through_chunk`` counts the chunks that were delivered cleanly
    before the stop.
    """

    success: int = 0
    duplicate: int = 0
    pending: int = 0
    rejected: int = 0
    rejected_samples: list[str] = field(default_factory=list)
    partial: bool = False
    delivered_through_chunk: int = 0
    undelivered_event_count: int = 0
    #: The run was refused locally before any network call because the project did
    #: not consent (FR-028). Distinct from ``rejected``, which is a server verdict:
    #: here nothing was transmitted, so there is nothing for the server to have
    #: judged. It counts into ``rejected`` as well, so ``ok`` is False and the
    #: caller's exit code is non-zero without needing to know about this field.
    refused: bool = False

    @property
    def total(self) -> int:
        return self.success + self.duplicate + self.pending + self.rejected

    @property
    def ok(self) -> bool:
        return self.pending == 0 and self.rejected == 0 and not self.partial


ConsentPredicate = Callable[[Sequence[str | None]], frozenset[str]]


def _refusal_report(envelopes: Sequence[Envelope], exc: UnconsentedDelivery) -> UploadReport:
    """Turn a local consent refusal into a non-zero, self-explaining report.

    Not an exception escaping to the CLI, deliberately: ``_run_import_apply``
    catches five specific exception types, and a sixth would surface as a
    traceback. Routing the refusal through the report the command already renders
    gives the operator the reason, the project, and exit 1 — the US1a AS-1
    contract ("refuses, names the projects, exits non-zero without POSTing")
    without a second rendering path.
    """
    return UploadReport(
        rejected=len(envelopes),
        rejected_samples=[str(exc)],
        refused=True,
    )


def _consent_answer(
    envelopes: Sequence[Envelope],
    *,
    checkout_root: Path | None,
    consent_predicate: ConsentPredicate | None,
) -> ConsentAnswer:
    """Ask the one resolver about every project present in the stream.

    **The question is keyed on the data, not on a root.** Candidates are the
    ``project_uuid`` of each envelope about to be sent, resolved through the same
    three-site chain the refusal uses — not ``plan.identity.project_uuid`` and not
    ``checkout_root``. That matters because "consent answered by where the code is
    standing rather than by whose data is moving" is this mission's recurring
    defect (cwd, ``repo_root``, machine-global arming, daemon scope, a
    checkout-level grant — five substitutions, five leaks). Asking about what is
    actually on the wire also keeps a future ``synthesize`` bug that mixed two
    projects into one stream from being authorised by an identity nobody
    re-checked: it would be refused here.

    ``checkout_root`` is therefore a **lookup aid, never an authorization key**.
    It is offered to the resolver only as a level-1 root so the project's own
    committed ``.kittify/config.yaml`` can be read at all; ``consent.py``'s
    ``_project_local_votes`` discards any root whose declared uuid differs from
    the one being asked about. So a wrong root cannot widen the answer — it can
    only be ignored (falling through to the machine index, then to deny) or, if
    it is unreadable, contribute a fault, which denies. Both directions are
    fail-closed, which is what makes this safe without a locality precondition.

    What would falsify that, and should be re-checked if either changes: (a) if
    ``_project_local_votes`` ever stopped filtering on the declared uuid, an
    offered root would begin speaking for a project that is not its own; (b) if a
    caller ever passed several roots harvested from elsewhere on the machine
    rather than the one checkout being imported.
    """
    projects = [resolve_envelope_project(env) for env in envelopes]
    roots = [checkout_root] if checkout_root is not None else None
    return resolve_consent_answer(projects, consent_predicate=consent_predicate, checkout_roots=roots)


def _consented_batches(
    chunks: Sequence[Sequence[Envelope]],
    answer: ConsentAnswer,
) -> list[ConsentedBatch]:
    """Mint one batch per chunk, or raise :class:`UnconsentedDelivery`.

    This is the gate. It is not an ``if``: the batches it returns are the only
    values ``receiver.deliver`` accepts, so a future caller that skips this step
    has nothing to hand the receiver.
    """
    return [
        consented_batch(
            [OutboundEvent(event_id=str(env["event_id"]), payload=env) for env in chunk],
            answer=answer,
        )
        for chunk in chunks
    ]


def upload_envelopes(
    envelopes: Sequence[Envelope],
    *,
    receiver: DeliveryReceiver,
    chunk_size: int = _IMPORT_CHUNK_SIZE,
    checkout_root: Path | None = None,
    consent_predicate: ConsentPredicate | None = None,
) -> UploadReport:
    """Chunk the stream (mission-atomically) and deliver, stopping on failure.

    Same delivery semantics as :func:`run_import_upload` minus the preflight:
    the first chunk with a failure outcome halts the run and the report records
    the partial state. Consent is resolved and the batches minted before the
    first chunk is handed to the receiver (FR-028).
    """
    chunks = list(_chunked(envelopes, chunk_size))
    _assert_batches_within_cap(chunks)
    answer = _consent_answer(envelopes, checkout_root=checkout_root, consent_predicate=consent_predicate)
    try:
        batches = _consented_batches(chunks, answer)
    except UnconsentedDelivery as exc:
        return _refusal_report(envelopes, exc)
    report = UploadReport()
    _deliver_chunks(batches, receiver, report)
    return report


def run_import_upload(
    envelopes: Sequence[Envelope],
    *,
    receiver: DeliveryReceiver,
    server_url: str,
    auth_token: str,
    poster: HttpPoster = default_http_poster,
    chunk_size: int = _IMPORT_CHUNK_SIZE,
    checkout_root: Path | None = None,
    consent_predicate: ConsentPredicate | None = None,
) -> UploadReport:
    """Preflight every chunk, then (only if all pass) upload chunks in order.

    Preflighting the whole stream before delivering anything is the fail-closed
    ordering: a **preflight** rejection in any chunk raises
    :class:`PreflightRejected` and nothing is uploaded (INV-6).

    A mid-upload *delivery* failure (after preflight passes) stops the run at
    the failed chunk — later chunks are never attempted, and the report records
    the partial state (``partial`` / ``delivered_through_chunk`` /
    ``undelivered_event_count``). The partial is safe: chunks are
    mission-atomic and carry monotonic per-mission Lamport clocks, so any
    delivered prefix is a valid ordered prefix of whole missions (a
    WPStatusChanged never lands before its WPCreated), never an orphan — and a
    re-run completes idempotently (the server dedups on ``event_id``). Note the
    import-once payload freeze: a fixed deterministic ``event_id`` means
    re-running after the on-disk facts change re-sends the *same* id, so the
    updated payload is dropped as a duplicate rather than overwriting.
    """
    chunks = list(_chunked(envelopes, chunk_size))
    _assert_batches_within_cap(chunks)
    # The consent gate runs BEFORE the preflight. ``run_server_preflight`` POSTs
    # the full envelope stream — mission slugs, project slug, payloads — so it is
    # a sink in its own right, and gating only the ``receiver.deliver`` call would
    # have left the leak intact while looking closed (E1's entry in the egress
    # inventory names the delivery line; the preflight line is the same breach).
    answer = _consent_answer(envelopes, checkout_root=checkout_root, consent_predicate=consent_predicate)
    try:
        batches = _consented_batches(chunks, answer)
    except UnconsentedDelivery as exc:
        return _refusal_report(envelopes, exc)
    for chunk in chunks:
        run_server_preflight(chunk, server_url=server_url, auth_token=auth_token, poster=poster)
    report = UploadReport()
    _deliver_chunks(batches, receiver, report)
    return report


# ── internals ─────────────────────────────────────────────────────────────────


def _deliver_chunks(batches: Sequence[ConsentedBatch], receiver: DeliveryReceiver, report: UploadReport) -> None:
    """Deliver chunks in order, stopping at the first chunk with a failure.

    A chunk whose delivery reports any outcome outside {success, duplicate,
    pending} — i.e. REJECTED / TERMINAL_FAILED / TRANSIENT — halts the run:
    subsequent chunks are never attempted and the report records the partial
    state. Everything delivered before the stop is a valid ordered prefix of
    whole missions (mission-atomic chunks, monotonic Lamport clocks), and a
    re-run resumes idempotently (the server dedups on ``event_id``).
    """
    for index, batch in enumerate(batches):
        failures_before = report.rejected
        for result in receiver.deliver(batch):
            _tally(report, result)
        if report.rejected > failures_before:
            report.delivered_through_chunk = index
            report.undelivered_event_count = sum(len(later) for later in batches[index + 1 :])
            report.partial = report.undelivered_event_count > 0
            return
        report.delivered_through_chunk = index + 1


def _tally(report: UploadReport, result: DeliveryResult) -> None:
    if result.outcome is DeliveryOutcome.SUCCESS:
        report.success += 1
    elif result.outcome is DeliveryOutcome.DUPLICATE:
        report.duplicate += 1
    elif result.outcome is DeliveryOutcome.PENDING:
        report.pending += 1
    else:  # REJECTED / TERMINAL_FAILED / TRANSIENT
        report.rejected += 1
        if len(report.rejected_samples) < _MAX_REJECTED_SAMPLES:
            report.rejected_samples.append(f"{result.event_id}: {result.error or result.outcome.value}")


def _chunked(items: Sequence[Envelope], size: int) -> Iterator[Sequence[Envelope]]:
    """Mission-atomic chunking: pack whole missions into chunks of ≤ *size* envelopes.

    The ordered stream is grouped into contiguous mission units — each unit
    starts at a ``MissionCreated`` and carries that mission's ``WPCreated[]`` +
    ``WPStatusChanged[]``; envelopes arriving before the first
    ``MissionCreated`` (synthetic/legacy streams) are singleton units. Units
    are packed greedily up to the *size* budget and a unit is NEVER split: a
    single mission larger than *size* becomes its own oversized chunk, which
    the server still accepts (``_SERVER_MAX_BATCH_SIZE`` = 1000 events/batch
    vs our conservative 500 budget).

    Recorded assumption, verified server-side: SaaS ``/events/preflight/``
    (apps/sync/views.py::preflight_sync_events →
    apps/sync/cutover_contract.py::_validate_event_batch) validates each
    envelope in isolation — schema/shape only, no cross-event
    referential-completeness check — so chunk boundaries are not
    correctness-bearing for preflight; mission-atomic chunking is
    defense-in-depth for delivery-prefix semantics.
    """
    chunk: list[Envelope] = []
    for unit in _mission_units(items):
        if chunk and len(chunk) + len(unit) > size:
            yield chunk
            chunk = []
        chunk.extend(unit)
    if chunk:
        yield chunk


def _mission_units(items: Sequence[Envelope]) -> Iterator[list[Envelope]]:
    """Group the ordered stream into contiguous per-mission units.

    A unit opens at each ``MissionCreated`` and absorbs every envelope up to
    the next one. Envelopes before the first ``MissionCreated`` have no mission
    prefix to stay atomic with, so each is its own singleton unit (this also
    preserves plain size-based packing for prefix-less synthetic streams).
    """
    unit: list[Envelope] = []
    for env in items:
        if env.get("event_type") == MISSION_CREATED:
            if unit:
                yield unit
            unit = [env]
        elif unit:
            unit.append(env)
        else:
            yield [env]
    if unit:
        yield unit
