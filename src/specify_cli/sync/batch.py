"""Batch sync for offline queue replay via REST endpoint.

Provides per-event error parsing, categorization, actionable summaries,
and JSON failure report export.
"""

import gzip
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from .queue import OfflineQueue


# ---------------------------------------------------------------------------
# Error categorisation
# ---------------------------------------------------------------------------

ERROR_CATEGORIES: dict[str, list[str]] = {
    "schema_mismatch": ["invalid", "schema", "field", "missing", "type"],
    "auth_expired": ["token", "expired", "unauthorized", "401"],
    "server_error": ["internal", "500", "timeout", "unavailable"],
}

CATEGORY_ACTIONS: dict[str, str] = {
    "schema_mismatch": "Run `spec-kitty sync diagnose` to inspect invalid events",
    "auth_expired": "Run `spec-kitty auth login` to refresh credentials",
    "server_error": "Retry later or check server status",
    "unknown": "Inspect the failure report for details: --report <file.json>",
}


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
        status: One of ``"success"``, ``"duplicate"``, ``"rejected"``.
        error: Human-readable error message (only for rejected events).
        error_category: Categorised reason (only for rejected events).
    """

    event_id: str
    status: str  # "success", "duplicate", "rejected"
    error: Optional[str] = None
    error_category: Optional[str] = None


# ---------------------------------------------------------------------------
# Aggregate result
# ---------------------------------------------------------------------------


class BatchSyncResult:
    """Result of a batch sync operation.

    Retains backward-compatible counters **and** the new per-event detail
    list ``event_results``.
    """

    def __init__(self):
        self.total_events: int = 0
        self.synced_count: int = 0
        self.duplicate_count: int = 0
        self.error_count: int = 0
        self.error_messages: list[str] = []
        self.synced_ids: list[str] = []
        self.failed_ids: list[str] = []
        # NEW: per-event results for richer diagnostics
        self.event_results: list[BatchEventResult] = []

    @property
    def success_count(self) -> int:
        """Events successfully processed (synced or duplicate)."""
        return self.synced_count + self.duplicate_count

    # -- Derived helpers ------------------------------------------------

    @property
    def failed_results(self) -> list[BatchEventResult]:
        """Convenience: only rejected ``BatchEventResult`` entries."""
        return [r for r in self.event_results if r.status == "rejected"]

    @property
    def category_counts(self) -> dict[str, int]:
        """Counter of error categories among rejected events."""
        return dict(Counter(r.error_category for r in self.failed_results))


# ---------------------------------------------------------------------------
# Actionable summary
# ---------------------------------------------------------------------------


def format_sync_summary(result: BatchSyncResult) -> str:
    """Build a human-readable, actionable summary string.

    Example output::

        Synced: 42, Duplicates: 3, Failed: 60
          schema_mismatch: 45  -- Run `spec-kitty sync diagnose` to inspect invalid events
          auth_expired: 10  -- Run `spec-kitty auth login` to refresh credentials
          unknown: 5  -- Inspect the failure report for details: --report <file.json>
    """
    lines: list[str] = []
    lines.append(f"Synced: {result.synced_count}, Duplicates: {result.duplicate_count}, Failed: {result.error_count}")

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
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_events": result.total_events,
            "synced": result.synced_count,
            "duplicates": result.duplicate_count,
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


# ---------------------------------------------------------------------------
# Core sync
# ---------------------------------------------------------------------------


def _parse_event_results(
    raw_results: list[dict],
    result: BatchSyncResult,
) -> None:
    """Parse per-event results from an HTTP 200 response body.

    Populates *result* counters, id lists, error messages, and
    ``event_results``.
    """
    for event_result in raw_results:
        event_id = event_result.get("event_id")
        status = event_result.get("status")
        error_msg = event_result.get("error_message") or event_result.get("error")

        if status == "success":
            result.synced_count += 1
            result.synced_ids.append(event_id)
            result.event_results.append(BatchEventResult(event_id=event_id, status="success"))
        elif status == "duplicate":
            result.duplicate_count += 1
            result.synced_ids.append(event_id)
            result.event_results.append(BatchEventResult(event_id=event_id, status="duplicate"))
        else:
            # Treat any non-success/non-duplicate status as rejected
            error_text = error_msg or "Unknown error"
            category = categorize_error(error_text)
            result.error_count += 1
            result.failed_ids.append(event_id)
            result.error_messages.append(f"{event_id}: {error_text}")
            result.event_results.append(
                BatchEventResult(
                    event_id=event_id,
                    status="rejected",
                    error=error_text,
                    error_category=category,
                )
            )


def _parse_error_response(
    response_body: dict,
    events: list[dict],
    result: BatchSyncResult,
) -> None:
    """Parse an HTTP 400 error response, surfacing both ``error`` and ``details``.

    If ``details`` is a JSON string containing per-event reasons it is
    parsed; otherwise the raw string is included in the error message.
    """
    error_msg = response_body.get("error", "Bad request")
    details_raw = response_body.get("details", "")

    # Try to parse details as structured JSON
    per_event_details: list[dict] = []
    if isinstance(details_raw, str) and details_raw.strip():
        try:
            parsed = json.loads(details_raw)
            if isinstance(parsed, list):
                per_event_details = parsed
        except (json.JSONDecodeError, TypeError):
            pass  # treat as plain string
    elif isinstance(details_raw, list):
        per_event_details = details_raw

    if per_event_details:
        # Structured per-event details from the server
        for detail in per_event_details:
            eid = detail.get("event_id", "unknown")
            reason = detail.get("error") or detail.get("reason", error_msg)
            category = categorize_error(reason)
            result.error_count += 1
            result.failed_ids.append(eid)
            result.error_messages.append(f"{eid}: {reason}")
            result.event_results.append(
                BatchEventResult(
                    event_id=eid,
                    status="rejected",
                    error=reason,
                    error_category=category,
                )
            )
        # Account for events not covered by details
        detail_count = len(per_event_details)
        remaining = len(events) - detail_count
        if remaining > 0:
            for evt in events[detail_count:]:
                eid = evt.get("event_id", "unknown")
                category = categorize_error(error_msg)
                result.error_count += 1
                result.failed_ids.append(eid)
                result.error_messages.append(f"{eid}: {error_msg}")
                result.event_results.append(
                    BatchEventResult(
                        event_id=eid,
                        status="rejected",
                        error=error_msg,
                        error_category=category,
                    )
                )
    else:
        # No structured details -- fall back to top-level error + details text
        combined = error_msg
        if details_raw:
            combined = f"{error_msg}\nDetails: {details_raw}"
        result.error_messages.append(combined)
        result.error_count = len(events)
        result.failed_ids = [e.get("event_id") for e in events]
        category = categorize_error(combined)
        for evt in events:
            eid = evt.get("event_id", "unknown")
            result.event_results.append(
                BatchEventResult(
                    event_id=eid,
                    status="rejected",
                    error=combined,
                    error_category=category,
                )
            )


def batch_sync(
    queue: OfflineQueue,
    auth_token: str,
    server_url: str,
    limit: int = 1000,
    show_progress: bool = True,
) -> BatchSyncResult:
    """Sync offline queue to server via batch endpoint.

    Drains the offline queue and uploads events in a single batch request
    with gzip compression. Successfully synced events are removed from the
    queue; failed events have their ``retry_count`` incremented.

    Args:
        queue: OfflineQueue instance containing events to sync.
        auth_token: JWT access token for authentication.
        server_url: Server base URL (e.g., ``https://spec-kitty-dev.fly.dev``).
        limit: Maximum number of events to sync (default 1000).
        show_progress: Whether to print progress messages (default ``True``).

    Returns:
        BatchSyncResult with sync statistics, per-event results, and
        categorised error details.
    """
    result = BatchSyncResult()

    events = queue.drain_queue(limit=limit)
    result.total_events = len(events)

    if not events:
        if show_progress:
            print("No events to sync")
        return result

    if show_progress:
        print(f"Syncing {len(events)} events... (0/{len(events)})")

    # Compress payload with gzip
    payload = json.dumps({"events": events}).encode("utf-8")
    compressed = gzip.compress(payload)

    # POST to batch endpoint
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Encoding": "gzip",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            f"{server_url.rstrip('/')}/api/v1/events/batch/",
            data=compressed,
            headers=headers,
            timeout=60,
        )

        if response.status_code == 200:
            response_data = response.json()
            raw_results = response_data.get("results", [])
            _parse_event_results(raw_results, result)

            # Queue operations are transactional: remove synced/duplicate,
            # bump retry for failures in a single commit.
            queue.process_batch_results(result.event_results)

            if show_progress:
                print(format_sync_summary(result))

        elif response.status_code == 401:
            if show_progress:
                print("Batch sync failed: Authentication failed (401)")
            result.error_messages.append("Authentication failed")
            result.error_count = len(events)
            result.failed_ids = [e.get("event_id") for e in events]
            for evt in events:
                result.event_results.append(
                    BatchEventResult(
                        event_id=evt.get("event_id", "unknown"),
                        status="rejected",
                        error="Authentication failed",
                        error_category="auth_expired",
                    )
                )
            queue.process_batch_results(result.event_results)

        elif response.status_code == 400:
            response_body = response.json()
            _parse_error_response(response_body, events, result)
            queue.process_batch_results(result.event_results)
            if show_progress:
                print(f"Batch sync failed (400):\n{format_sync_summary(result)}")

        else:
            if show_progress:
                print(f"Batch sync failed: HTTP {response.status_code}")
            result.error_messages.append(f"HTTP {response.status_code}")
            result.error_count = len(events)
            result.failed_ids = [e.get("event_id") for e in events]
            for evt in events:
                result.event_results.append(
                    BatchEventResult(
                        event_id=evt.get("event_id", "unknown"),
                        status="rejected",
                        error=f"HTTP {response.status_code}",
                        error_category="server_error",
                    )
                )
            queue.process_batch_results(result.event_results)

    except requests.exceptions.Timeout:
        if show_progress:
            print("Batch sync failed: Request timeout")
        result.error_messages.append("Request timeout")
        result.error_count = len(events)
        result.failed_ids = [e.get("event_id") for e in events]
        for evt in events:
            result.event_results.append(
                BatchEventResult(
                    event_id=evt.get("event_id", "unknown"),
                    status="rejected",
                    error="Request timeout",
                    error_category="server_error",
                )
            )
        queue.process_batch_results(result.event_results)

    except requests.exceptions.ConnectionError as e:
        if show_progress:
            print(f"Batch sync failed: Connection error - {e}")
        result.error_messages.append(f"Connection error: {e}")
        result.error_count = len(events)
        result.failed_ids = [e.get("event_id") for e in events]
        for evt in events:
            result.event_results.append(
                BatchEventResult(
                    event_id=evt.get("event_id", "unknown"),
                    status="rejected",
                    error=f"Connection error: {e}",
                    error_category="server_error",
                )
            )
        queue.process_batch_results(result.event_results)

    except Exception as e:
        if show_progress:
            print(f"Batch sync failed: {e}")
        result.error_messages.append(str(e))
        result.error_count = len(events)
        result.failed_ids = [e.get("event_id") for e in events]
        for evt in events:
            result.event_results.append(
                BatchEventResult(
                    event_id=evt.get("event_id", "unknown"),
                    status="rejected",
                    error=str(e),
                    error_category=categorize_error(str(e)),
                )
            )
        queue.process_batch_results(result.event_results)

    return result


def sync_all_queued_events(
    queue: OfflineQueue,
    auth_token: str,
    server_url: str,
    batch_size: int = 1000,
    show_progress: bool = True,
) -> BatchSyncResult:
    """Sync all events from the queue in batches.

    Continues syncing in batches until queue is empty or all remaining events
    have exceeded retry limit.

    Args:
        queue: OfflineQueue instance.
        auth_token: JWT access token.
        server_url: Server base URL.
        batch_size: Events per batch (default 1000).
        show_progress: Whether to print progress.

    Returns:
        Aggregated BatchSyncResult across all batches.
    """
    total_result = BatchSyncResult()
    batch_num = 0

    while queue.size() > 0:
        batch_num += 1
        if show_progress:
            print(f"\n--- Batch {batch_num} ---")

        result = batch_sync(
            queue=queue,
            auth_token=auth_token,
            server_url=server_url,
            limit=batch_size,
            show_progress=show_progress,
        )

        total_result.total_events += result.total_events
        total_result.synced_count += result.synced_count
        total_result.duplicate_count += result.duplicate_count
        total_result.error_count += result.error_count
        total_result.synced_ids.extend(result.synced_ids)
        total_result.failed_ids.extend(result.failed_ids)
        total_result.error_messages.extend(result.error_messages)
        total_result.event_results.extend(result.event_results)

        # Stop if no progress made (all errors)
        if result.success_count == 0 and result.error_count > 0:
            if show_progress:
                print("Stopping: No events successfully synced in this batch")
            break

    if show_progress:
        print("\n=== Sync Complete ===")
        print(format_sync_summary(total_result))
        if queue.size() > 0:
            print(f"Remaining in queue: {queue.size()} events")

    return total_result
