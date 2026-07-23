"""PROVENANCE + PREFLIGHT + UPLOAD for ``sync import-history`` (WP-Y5, #2262).

Takes the synthesized envelope stream and materializes it into the SaaS
projection, reusing the WP06 delivery receiver as the transport seam rather
than hand-rolling HTTP:

* **PROVENANCE (stage 6):** a per-envelope ``envelope_sha256`` manifest, hashed
  with the same canonical-JSON shape the migration dry-run uses.
* **PREFLIGHT (stage 7):** POST each chunk to ``/api/v1/events/preflight/`` and
  gate on ``accepted`` — the server validates shape/ingress without mutating
  state. Every chunk is preflighted *before* any chunk uploads, so a rejection
  anywhere leaves the projection untouched (fail-closed, INV-6).
* **UPLOAD (stage 8):** chunk the stream and hand each chunk to a
  :class:`DeliveryReceiver` (gzip + POST + response mapping + poison-batch
  bisection all live there). The server dedups on ``event_id``, so a re-run is
  idempotent (already-ingested events return ``duplicate``).

The transport is injectable: production passes an authed ``TeamspaceReceiver``
and the default ``requests`` poster; tests pass a ``StubReceiver`` and a fake
poster, so the whole stage runs with no network.
"""

from __future__ import annotations

import gzip
import hashlib
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

_PREFLIGHT_ENDPOINT_PATH = "/api/v1/events/preflight/"
_PREFLIGHT_TIMEOUT_SECONDS = 60.0
# Conservative per-request size: well under the server's 1000-event cap and its
# 512 KiB decompressed byte ceiling. The receiver still auto-bisects on a 413.
_IMPORT_CHUNK_SIZE = 500
_MAX_REJECTED_SAMPLES = 5

Envelope = Mapping[str, Any]


# ── provenance (stage 6) ──────────────────────────────────────────────────────


def envelope_sha256(envelope: Envelope) -> str:
    """Canonical-JSON SHA-256 of an envelope (matches the dry-run row-mapping)."""
    canonical = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()  # noqa: TID251 - body checksum for the import provenance manifest


@dataclass(frozen=True)
class ProvenanceEntry:
    """One provenance record for the import audit manifest."""

    event_id: str
    event_type: str
    envelope_sha256: str
    # Import envelopes are synthesized / replayed, not lifted verbatim from a
    # single on-disk JSONL row, so there is no row_sha256 to anchor.
    row_sha256: str | None = None


def build_provenance_manifest(envelopes: Sequence[Envelope]) -> list[ProvenanceEntry]:
    return [
        ProvenanceEntry(
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
    """Tally of per-event delivery outcomes for one import run."""

    success: int = 0
    duplicate: int = 0
    pending: int = 0
    rejected: int = 0
    rejected_samples: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.success + self.duplicate + self.pending + self.rejected

    @property
    def ok(self) -> bool:
        return self.rejected == 0


def upload_envelopes(
    envelopes: Sequence[Envelope],
    *,
    receiver: DeliveryReceiver,
    chunk_size: int = _IMPORT_CHUNK_SIZE,
) -> UploadReport:
    """Chunk the stream and deliver each chunk through the receiver, tallying outcomes."""
    report = UploadReport()
    for chunk in _chunked(envelopes, chunk_size):
        outbound = [OutboundEvent(event_id=str(env["event_id"]), payload=env) for env in chunk]
        for result in receiver.deliver(outbound):
            _tally(report, result)
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
    """Preflight every chunk, then (only if all pass) upload every chunk.

    Preflighting the whole stream before delivering anything is the fail-closed
    ordering: a rejection in any chunk raises :class:`PreflightRejected` and
    nothing is uploaded (INV-6).
    """
    chunks = list(_chunked(envelopes, chunk_size))
    for chunk in chunks:
        run_server_preflight(chunk, server_url=server_url, auth_token=auth_token, poster=poster)
    report = UploadReport()
    for chunk in chunks:
        outbound = [OutboundEvent(event_id=str(env["event_id"]), payload=env) for env in chunk]
        for result in receiver.deliver(outbound):
            _tally(report, result)
    return report


# ── internals ─────────────────────────────────────────────────────────────────


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
    for start in range(0, len(items), size):
        yield items[start : start + size]
