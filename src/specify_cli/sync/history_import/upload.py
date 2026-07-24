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
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from specify_cli.delivery.receivers import (
    DeliveryOutcome,
    DeliveryReceiver,
    DeliveryResult,
    HttpPoster,
    OutboundEvent,
    _requests_post,
)
from specify_cli.migration.envelope_seam import envelope_sha256
from specify_cli.status import MISSION_CREATED

_PREFLIGHT_ENDPOINT_PATH = "/api/v1/events/preflight/"
_PREFLIGHT_TIMEOUT_SECONDS = 60.0
# Conservative per-request size: well under the server's 1000-event cap and its
# 512 KiB decompressed byte ceiling. The receiver still auto-bisects on a 413.
_IMPORT_CHUNK_SIZE = 500
# The server's hard per-batch envelope cap. A single mission larger than
# _IMPORT_CHUNK_SIZE is deliberately NOT split (mission-atomic chunking, see
# _chunked) and becomes one oversized chunk — safe because the server accepts
# up to this many events per batch, double our conservative budget.
_SERVER_MAX_BATCH_SIZE = 1000
_MAX_REJECTED_SAMPLES = 5

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
    poster: HttpPoster = _requests_post,
) -> dict[str, Any]:
    """POST ``{"events": [...]}`` to the preflight endpoint; raise if not accepted."""
    url = server_url.rstrip("/") + _PREFLIGHT_ENDPOINT_PATH
    body = gzip.compress(json.dumps({"events": [dict(env) for env in envelopes]}, separators=(",", ":")).encode("utf-8"))
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Encoding": "gzip",
        "Content-Type": "application/json",
    }
    response = poster(url, data=body, headers=headers, timeout=_PREFLIGHT_TIMEOUT_SECONDS)
    try:
        payload = response.json()
    except Exception as exc:  # non-JSON (5xx / proxy error) is a hard, fail-closed stop
        raise PreflightRejected({"error": f"preflight response was not JSON (HTTP {response.status_code})"}) from exc
    if response.status_code != 200 or not payload.get("accepted"):
        raise PreflightRejected(payload)
    return dict(payload)


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

    @property
    def total(self) -> int:
        return self.success + self.duplicate + self.pending + self.rejected

    @property
    def ok(self) -> bool:
        return self.rejected == 0 and not self.partial


def upload_envelopes(
    envelopes: Sequence[Envelope],
    *,
    receiver: DeliveryReceiver,
    chunk_size: int = _IMPORT_CHUNK_SIZE,
) -> UploadReport:
    """Chunk the stream (mission-atomically) and deliver, stopping on failure.

    Same delivery semantics as :func:`run_import_upload` minus the preflight:
    the first chunk with a failure outcome halts the run and the report records
    the partial state.
    """
    report = UploadReport()
    _deliver_chunks(list(_chunked(envelopes, chunk_size)), receiver, report)
    return report


def run_import_upload(
    envelopes: Sequence[Envelope],
    *,
    receiver: DeliveryReceiver,
    server_url: str,
    auth_token: str,
    poster: HttpPoster = _requests_post,
    chunk_size: int = _IMPORT_CHUNK_SIZE,
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
    for chunk in chunks:
        run_server_preflight(chunk, server_url=server_url, auth_token=auth_token, poster=poster)
    report = UploadReport()
    _deliver_chunks(chunks, receiver, report)
    return report


# ── internals ─────────────────────────────────────────────────────────────────


def _deliver_chunks(chunks: Sequence[Sequence[Envelope]], receiver: DeliveryReceiver, report: UploadReport) -> None:
    """Deliver chunks in order, stopping at the first chunk with a failure.

    A chunk whose delivery reports any outcome outside {success, duplicate,
    pending} — i.e. REJECTED / TERMINAL_FAILED / TRANSIENT — halts the run:
    subsequent chunks are never attempted and the report records the partial
    state. Everything delivered before the stop is a valid ordered prefix of
    whole missions (mission-atomic chunks, monotonic Lamport clocks), and a
    re-run resumes idempotently (the server dedups on ``event_id``).
    """
    for index, chunk in enumerate(chunks):
        outbound = [OutboundEvent(event_id=str(env["event_id"]), payload=env) for env in chunk]
        failures_before = report.rejected
        for result in receiver.deliver(outbound):
            _tally(report, result)
        if report.rejected > failures_before:
            report.delivered_through_chunk = index
            report.undelivered_event_count = sum(len(later) for later in chunks[index + 1 :])
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
