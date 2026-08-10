"""Batch-sync result types, error categorisation, summaries and failure reports.

This module holds **no transmit surface**. The queue-backed drain that used to
live here — ``batch_sync`` and ``sync_all_queued_events``, plus their callee tree
— was retired by #3167 because it could POST queued events without traversing a
per-project consent decision, on a code path no production caller reached. See
``kitty-specs/chain-b-consent-bypass-3167-01KZ63HK/contracts/deletion-manifest.md``.

What remains, and who drives it:

* ``BatchEventResult`` / ``BatchSyncResult`` — the per-event and per-batch result
  types, consumed by ``sync/background.py``.
* ``categorize_error`` / ``ERROR_CATEGORIES`` / ``CATEGORY_ACTIONS`` — error
  classification, consumed by ``sync/diagnose.py``.
* ``run_final_sync_with_retries`` and its ``_final_sync_*`` helpers — the
  retry wrapper around a caller-supplied ``sync_operation``; it performs no I/O
  of its own and is driven by ``sync/background.py``.
* ``format_sync_summary`` / ``generate_failure_report`` / ``write_failure_report``
  — reporting, reached through the ``specify_cli.sync`` lazy map.

Do not add a ``requests.*`` or ``request_with_stdlib_fallback_sync`` call here:
this module was removed from the egress allowlist (``E15``) when the drain went,
so any new transmit primitive would be unconsented egress. The permanence guard
is ``tests/architectural/test_batch_drain_retired_3167.py``.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from specify_cli.sync._team import CATEGORY_MISSING_PRIVATE_TEAM
from .diagnostics import (
    SyncDiagnosticCode,
    classify_sync_error,
    emit_sync_diagnostic,
)
from kernel.clock import now_utc_iso


# ---------------------------------------------------------------------------
# Error categorisation
# ---------------------------------------------------------------------------

ERROR_CATEGORIES: dict[str, list[str]] = {
    "oversized_batch": [
        "batch payload exceeds decompressed byte limit",
        "sync_batch_too_large",
        "request_too_large",
        "payload too large",
    ],
    "oversized_event": [
        "single event exceeds decompressed byte limit",
        "event exceeds decompressed byte limit",
        "oversized event",
    ],
    "throttled": ["rate limit", "rate_limited", "too many requests", "throttle"],
    "schema_mismatch": ["invalid", "schema", "field", "missing", "type"],
    "auth_expired": ["token", "expired", "unauthorized", "401"],
    "unauthenticated": ["not authenticated", "no valid access token"],
    CATEGORY_MISSING_PRIVATE_TEAM: [
        "private teamspace",
        "private team",
        "direct ingress",
        CATEGORY_MISSING_PRIVATE_TEAM,
    ],
    "retryable_transport": [
        "timeout",
        "connection",
        "network",
        "unreachable",
        "unavailable",
    ],
    "server_error": ["internal", "500", "502", "503", "504", "server error"],
}

CATEGORY_ACTIONS: dict[str, str] = {
    "oversized_batch": "The CLI will retry with a smaller batch; upgrade if this persists",
    "oversized_event": "Inspect or remove the oversized event from the offline queue",
    "throttled": "Retry later; server indicated rate limiting",
    "schema_mismatch": "Run `spec-kitty sync diagnose` to inspect invalid events",
    "auth_expired": "Run `spec-kitty auth login` to refresh credentials",
    "unauthenticated": "Run `spec-kitty auth login` to authenticate",
    CATEGORY_MISSING_PRIVATE_TEAM: ("Private Teamspace access is required for direct ingress"),
    "retryable_transport": "Retry later or check network connectivity",
    "server_error": "Retry later or check server status",
    "unknown": "Inspect the failure report for details: --report <file.json>",
}

FINAL_SYNC_MAX_ATTEMPTS = 3
FINAL_SYNC_RETRY_BACKOFF_SECONDS = 1.0


def categorize_error(error_string: str) -> str:
    """Categorise an error message by keyword matching.

    Inspects *error_string* for keywords defined in ``ERROR_CATEGORIES``.
    Returns the first matching category or ``"unknown"`` if nothing matches.
    """
    if not error_string:
        return "unknown"
    lower = error_string.lower()
    for category, keywords in ERROR_CATEGORIES.items():
        if any(kw in lower for kw in keywords):
            return category
    return "unknown"


# ---------------------------------------------------------------------------
# Per-event result
# ---------------------------------------------------------------------------


@dataclass
class BatchEventResult:
    """Result of a single event within a batch response.

    Attributes:
        event_id: Unique event identifier.
        status: One of ``"success"``, ``"duplicate"``, ``"pending"``,
            ``"rejected"``, ``"failed_permanent"``, or ``"failed_transient"``.

            Queue mutation semantics (see ``OfflineQueue.process_batch_results``):

            * ``success`` / ``duplicate`` / ``failed_permanent`` -- row is
              **deleted** from the queue. Permanent failures (e.g. oversized
              events that can never be sent) are removed so the *dispatch*
              drain loop (``delivery/dispatcher.py``) can continue past them
              without stalling.
            * ``pending`` -- the server acknowledged the event but has not
              yet materialised it (per-event ``status`` of ``"queued"`` or
              ``"pending"`` inside a 200 response body). The queue row is
              **left untouched** (same disposition as ``failed_transient``)
              so the next daemon tick re-sends and the server's eventual
              ``success`` / ``duplicate`` response cleans it up. The CLI
              does **not** classify the event as a sync failure. See
              issue Priivacy-ai/spec-kitty#1182.
            * ``rejected`` -- per-event content rejection returned by the
              server inside a 200 response body. ``retry_count`` is
              **incremented**.
            * ``failed_transient`` -- batch-level failure where the server
              never evaluated individual events: HTTP 401/403/5xx, transport
              timeouts/connection errors, or the pre-flight "no Private
              Teamspace" skip. The queue row is **left untouched** (no DELETE,
              no ``retry_count`` bump) so transient outages cannot poison the
              retry counter. See issue Priivacy-ai/spec-kitty#889.

        error: Human-readable error message (only for failed events).
        error_category: Categorised reason (only for failed events).
    """

    event_id: str
    status: str  # "success" | "duplicate" | "pending" | "rejected" | "failed_permanent" | "failed_transient"
    error: str | None = None
    error_category: str | None = None


# ---------------------------------------------------------------------------
# Aggregate result
# ---------------------------------------------------------------------------


class BatchSyncResult:
    """Result of a batch sync operation.

    Retains backward-compatible counters **and** the new per-event detail
    list ``event_results``.
    """

    def __init__(self) -> None:
        self.total_events: int = 0
        self.synced_count: int = 0
        self.duplicate_count: int = 0
        # Per-event "queued"/"pending" responses from the server. The event
        # was durably accepted but has not yet been materialised; the CLI
        # MUST NOT classify these as sync failures. See issue
        # Priivacy-ai/spec-kitty#1182.
        self.pending_count: int = 0
        self.error_count: int = 0
        self.error_messages: list[str] = []
        self.synced_ids: list[str] = []
        self.pending_ids: list[str] = []
        self.failed_ids: list[str] = []
        # NEW: per-event results for richer diagnostics
        self.event_results: list[BatchEventResult] = []

    @property
    def success_count(self) -> int:
        """Events successfully processed (synced or duplicate).

        ``pending_count`` is intentionally excluded: pending events were
        accepted by the server but have not yet been materialised, so they
        are durable but not yet "done". Treat ``success_count`` as the
        terminal-success bucket and ``pending_count`` as in-flight.
        """
        return self.synced_count + self.duplicate_count

    # -- Derived helpers ------------------------------------------------

    @property
    def failed_results(self) -> list[BatchEventResult]:
        """Convenience: failed ``BatchEventResult`` entries.

        Includes per-event content rejections (``rejected``), permanent
        failures (``failed_permanent``), and batch-level transient failures
        (``failed_transient``). All three are surfaced to operators in the
        category summary; only ``rejected`` mutates ``retry_count`` in the
        queue. See ``BatchEventResult`` for full semantics.
        """
        return [
            r
            for r in self.event_results
            if r.status in ("rejected", "failed_permanent", "failed_transient")
        ]

    @property
    def category_counts(self) -> dict[str, int]:
        """Counter of error categories among rejected events."""
        return dict(Counter(r.error_category for r in self.failed_results))


def run_final_sync_with_retries(
    sync_operation: Callable[[], BatchSyncResult],
    *,
    sleep: Callable[[float], None] | None = None,
) -> BatchSyncResult:
    """Run final sync with bounded retry before emitting a non-fatal diagnostic.

    Final sync runs after the local command already succeeded, so exhausted
    attempts must never change the command exit behavior or write retry noise
    to stdout. Events remain durable in the queue for a later *dispatch* drain
    by the sync daemon (``delivery/selection.py``), not for the queue-backed
    drain this module used to hold — that one was retired by #3167.
    """
    last_result: BatchSyncResult | None = None
    last_error: BaseException | None = None
    sleeper = time.sleep if sleep is None else sleep

    for attempt in range(1, FINAL_SYNC_MAX_ATTEMPTS + 1):
        try:
            result = sync_operation()
        except Exception as exc:  # noqa: BLE001 - final sync is best effort
            last_error = exc
            maybe_result = _handle_final_sync_exception(exc, attempt, sleeper)
            if maybe_result is None:
                continue
            return maybe_result

        last_result = result
        last_error = None
        maybe_result = _handle_final_sync_result(result, attempt, sleeper)
        if maybe_result is not None:
            return maybe_result

    return _finalize_exhausted_final_sync(last_result, last_error)


def _has_final_sync_retry_remaining(attempt: int) -> bool:
    """Return True when another final-sync retry attempt is available."""
    return attempt < FINAL_SYNC_MAX_ATTEMPTS


def _sleep_before_final_sync_retry(
    attempt: int,
    sleeper: Callable[[float], None],
) -> bool:
    """Sleep for a retry when attempts remain and report whether we retried."""
    if not _has_final_sync_retry_remaining(attempt):
        return False
    sleeper(FINAL_SYNC_RETRY_BACKOFF_SECONDS)
    return True


def _handle_final_sync_exception(
    exc: BaseException,
    attempt: int,
    sleeper: Callable[[float], None],
) -> BatchSyncResult | None:
    """Retry or finalize an exception raised during final sync."""
    if _sleep_before_final_sync_retry(attempt, sleeper):
        return None
    _emit_final_sync_failure_diagnostic(str(exc))
    return _result_from_final_sync_exception(exc)


def _handle_final_sync_result(
    result: BatchSyncResult,
    attempt: int,
    sleeper: Callable[[float], None],
) -> BatchSyncResult | None:
    """Retry or finalize a completed final-sync result."""
    if not _should_retry_final_sync_result(result):
        if _is_failed_final_sync_result(result):
            _emit_final_sync_failure_diagnostic(_final_sync_result_error_text(result))
        return result
    if _sleep_before_final_sync_retry(attempt, sleeper):
        return None
    _emit_final_sync_failure_diagnostic(_final_sync_result_error_text(result))
    return result


def _finalize_exhausted_final_sync(
    last_result: BatchSyncResult | None,
    last_error: BaseException | None,
) -> BatchSyncResult:
    """Return the best available exhausted final-sync outcome."""
    if last_result is not None:
        _emit_final_sync_failure_diagnostic(_final_sync_result_error_text(last_result))
        return last_result
    if last_error is not None:
        _emit_final_sync_failure_diagnostic(str(last_error))
        return _result_from_final_sync_exception(last_error)
    return BatchSyncResult()


def _should_retry_final_sync_result(result: BatchSyncResult) -> bool:
    """Return True for transient-looking final-sync failures."""
    if not _is_failed_final_sync_result(result):
        return False
    categories = set(result.category_counts)
    if not categories:
        return True
    non_retryable_categories = {
        "auth_expired",
        "schema_mismatch",
        "unauthenticated",
        "unauthorized",
        CATEGORY_MISSING_PRIVATE_TEAM,
    }
    return not categories <= non_retryable_categories


def _is_failed_final_sync_result(result: BatchSyncResult) -> bool:
    """Return True when final sync made no progress and reported errors."""
    return result.error_count > 0 and result.success_count == 0


def _final_sync_result_error_text(result: BatchSyncResult) -> str:
    """Return a compact diagnostic detail string for an exhausted final sync."""
    if result.error_messages:
        return "; ".join(result.error_messages)
    if result.error_count:
        return f"{result.error_count} queued event(s) failed during final sync"
    return "final sync failed"


def _emit_final_sync_failure_diagnostic(error_text: str) -> None:
    """Emit the single non-fatal final-sync diagnostic for exhausted retries."""
    code: SyncDiagnosticCode = classify_sync_error(error_text)
    emit_sync_diagnostic(
        code,
        f"Final sync failed after local command success. Queued events remain durable and will be retried. Detail: {error_text}",
    )


def _result_from_final_sync_exception(exc: BaseException) -> BatchSyncResult:
    """Represent an exhausted final-sync exception as a non-fatal batch result."""
    result = BatchSyncResult()
    result.error_count = 1
    result.error_messages.append(str(exc))
    return result


# ---------------------------------------------------------------------------
# Actionable summary
# ---------------------------------------------------------------------------


def format_sync_summary(result: BatchSyncResult) -> str:
    """Build a human-readable, actionable summary string.

    Example output::

        Synced: 42, Duplicates: 3, Pending: 2, Failed: 60
          schema_mismatch: 45  -- Run `spec-kitty sync diagnose` to inspect invalid events
          auth_expired: 10  -- Run `spec-kitty auth login` to refresh credentials
          unknown: 5  -- Inspect the failure report for details: --report <file.json>

    The ``Pending`` segment is included only when ``result.pending_count``
    is non-zero (per-event ``queued`` / ``pending`` responses durably held
    by the server pending materialisation; see issue
    Priivacy-ai/spec-kitty#1182).
    """
    lines: list[str] = []
    if result.pending_count:
        lines.append(
            f"Synced: {result.synced_count}, Duplicates: {result.duplicate_count}, "
            f"Pending: {result.pending_count}, Failed: {result.error_count}"
        )
    else:
        lines.append(
            f"Synced: {result.synced_count}, Duplicates: {result.duplicate_count}, Failed: {result.error_count}"
        )

    category_counts = result.category_counts
    if category_counts:
        for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
            action = CATEGORY_ACTIONS.get(cat, "")
            if action:
                lines.append(f"  {cat}: {count}  -- {action}")
            else:
                lines.append(f"  {cat}: {count}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_failure_report(result: BatchSyncResult) -> dict:
    """Build a JSON-serialisable failure report dictionary.

    Includes metadata (timestamp, totals) and per-event failure details.
    """
    failed = result.failed_results
    return {
        "generated_at": now_utc_iso(),
        "summary": {
            "total_events": result.total_events,
            "synced": result.synced_count,
            "duplicates": result.duplicate_count,
            "pending": result.pending_count,
            "failed": result.error_count,
            "categories": result.category_counts,
        },
        "failures": [
            {
                "event_id": r.event_id,
                "error": r.error,
                "category": r.error_category,
            }
            for r in failed
        ],
    }


def write_failure_report(report_path: Path, result: BatchSyncResult) -> None:
    """Write a JSON failure report to *report_path*."""
    report_data = generate_failure_report(result)
    report_path.write_text(json.dumps(report_data, indent=2))
