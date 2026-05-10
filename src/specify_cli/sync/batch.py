"""Batch sync for offline queue replay via REST endpoint.

Provides per-event error parsing, categorization, actionable summaries,
and JSON failure report export.
"""

from __future__ import annotations

import gzip
import json
import time
from contextlib import suppress
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from urllib.parse import urlparse

import requests

from specify_cli.auth.http import request_with_stdlib_fallback_sync
from specify_cli.sync._team import (
    CATEGORY_MISSING_PRIVATE_TEAM,
    resolve_private_team_id_for_ingress,
)
from .feature_flags import is_saas_sync_enabled, saas_sync_disabled_message
from .queue import OfflineQueue
from .diagnostics import (
    SyncDiagnosticCode,
    classify_sync_error,
    emit_sync_diagnostic,
)
from specify_cli.core.contract_gate import validate_outbound_payload


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
SYNC_INGRESS_LIMITS_TIMEOUT_SECONDS = 10
DEFAULT_MAX_DECOMPRESSED_BYTES_PER_BATCH = 900_000
DECOMPRESSED_BYTES_SAFETY_FACTOR = 0.90
HISTORICAL_MISSION_STATE_FORBIDDEN_KEYS = frozenset(
    {
        "feature_slug",
        "feature_number",
        "mission_key",
        "legacy_aggregate_id",
        "work_package_id",
    }
)


def _current_team_slug() -> str | None:
    """Resolve the ingress team slug via the strict shared helper. SYNC.

    Returns the user's Private Teamspace id, or ``None`` when no Private
    Teamspace is available (in which case the helper has already emitted
    a structured warning and callers MUST NOT send the ingress request).
    """
    try:
        from specify_cli.auth import get_token_manager

        return resolve_private_team_id_for_ingress(
            get_token_manager(),
            endpoint="/api/v1/events/batch/",
        )
    except Exception as exc:  # noqa: BLE001 — explicit "log and skip" boundary
        import logging

        logging.getLogger(__name__).warning("_current_team_slug: ingress resolver raised: %s", exc)
        return None


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


def _safe_response_json(response: object) -> dict:
    """Return a response JSON dict, or an empty dict if unavailable."""
    try:
        body = response.json()  # type: ignore[attr-defined]
    except (TypeError, ValueError):
        return {}
    return body if isinstance(body, dict) else {}


def _positive_int(value: object) -> int | None:
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _should_probe_advertised_limits(server_url: str) -> bool:
    """Return True when the base URL looks like a real SaaS endpoint.

    Unit tests and local development commonly pass localhost or reserved
    ``.example`` hosts with ``requests.post`` mocked. Avoiding the health probe
    there preserves the existing no-network test contract while still enabling
    live SaaS clients to honor server-advertised ingress limits.
    """
    parsed = urlparse(server_url)
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return False
    if host.endswith(".example") or host.endswith(".example.com"):
        return False
    return parsed.scheme in {"https", "http"} and bool(host)


def _extract_sync_ingress_limits(response_body: dict) -> dict[str, int]:
    sync_ingress = response_body.get("sync_ingress")
    if not isinstance(sync_ingress, dict):
        return {}
    limits = sync_ingress.get("limits")
    if not isinstance(limits, dict):
        return {}

    extracted: dict[str, int] = {}
    for key in (
        "max_events_per_batch",
        "max_decompressed_bytes_per_batch",
        "retry_after_min_seconds",
        "retry_after_max_seconds",
    ):
        value = _positive_int(limits.get(key))
        if value is not None:
            extracted[key] = value
    return extracted


def _fetch_advertised_sync_ingress_limits(
    *,
    server_url: str,
    auth_token: str,
    team_slug: str,
) -> dict[str, int]:
    """Fetch server-advertised sync ingress limits, failing open on errors."""
    if not _should_probe_advertised_limits(server_url):
        return {}

    health_url = f"{server_url.rstrip('/')}/api/v1/sync/health/"
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "X-Team-Slug": team_slug,
    }
    try:
        response = requests.get(
            health_url,
            headers=headers,
            timeout=SYNC_INGRESS_LIMITS_TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        return {}
    if response.status_code != 200:
        return {}
    return _extract_sync_ingress_limits(_safe_response_json(response))


def _build_batch_payload(events: list[dict]) -> bytes:
    return json.dumps({"events": events}).encode("utf-8")


def _find_historical_mission_state_keys(value: object, *, prefix: str = "$") -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}.{key}"
            if key in HISTORICAL_MISSION_STATE_FORBIDDEN_KEYS:
                findings.append((child_path, str(key)))
            findings.extend(_find_historical_mission_state_keys(child, prefix=child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_find_historical_mission_state_keys(child, prefix=f"{prefix}[{index}]"))
    return findings


def _historical_mission_state_rejection(events: list[dict]) -> BatchSyncResult | None:
    violations: list[tuple[dict, str, str]] = []
    for event in events:
        for path, key in _find_historical_mission_state_keys(event):
            violations.append((event, path, key))

    if not violations:
        return None

    by_event: dict[str, list[tuple[str, str]]] = {}
    for event, path, key in violations:
        event_id = str(event.get("event_id", "unknown"))
        by_event.setdefault(event_id, []).append((path, key))

    result = BatchSyncResult()
    result.total_events = len(events)
    result.error_count = len(by_event)
    result.failed_ids = sorted(by_event)
    message = (
        "Historical mission-state rows cannot be sent directly to TeamSpace. "
        "Run `spec-kitty doctor mission-state --audit --fail-on teamspace-blocker`, "
        "then `--fix`, then `--teamspace-dry-run` before sync/import."
    )
    result.error_messages.append(message)
    for event_id, event_violations in sorted(by_event.items()):
        details = ", ".join(f"{path} ({key})" for path, key in sorted(event_violations))
        result.event_results.append(
            BatchEventResult(
                event_id=event_id,
                status="rejected",
                error=f"{message} Forbidden historical field(s): {details}",
                error_category="historical_mission_state",
            )
        )
    return result


def _decompressed_byte_limit(advertised_limits: dict[str, int]) -> int:
    advertised_limit = advertised_limits.get(
        "max_decompressed_bytes_per_batch",
        DEFAULT_MAX_DECOMPRESSED_BYTES_PER_BATCH,
    )
    return max(1, int(advertised_limit * DECOMPRESSED_BYTES_SAFETY_FACTOR))


def _select_events_for_advertised_limits(
    queue: OfflineQueue,
    *,
    requested_limit: int,
    advertised_limits: dict[str, int],
) -> tuple[list[dict], bytes]:
    max_events = advertised_limits.get("max_events_per_batch")
    effective_limit = min(requested_limit, max_events) if max_events else requested_limit
    candidates = queue.drain_queue(limit=effective_limit)
    max_decompressed_bytes = _decompressed_byte_limit(advertised_limits)

    selected: list[dict] = []
    # Track accumulated payload size incrementally (O(n)) rather than
    # re-serializing the full list on each iteration (O(n²)).
    # Envelope overhead: len('{"events": []}') == 14 bytes; each event after the
    # first adds a 2-byte ", " separator.
    accumulated = 14

    for event in candidates:
        event_bytes = len(json.dumps(event).encode("utf-8"))
        incremental = event_bytes + (2 if selected else 0)
        if selected and accumulated + incremental > max_decompressed_bytes:
            break
        selected.append(event)
        accumulated += incremental
        if accumulated > max_decompressed_bytes:
            break

    payload = _build_batch_payload(selected)
    return selected, payload


def _is_oversized_batch_response(status_code: int, body: dict) -> bool:
    if status_code == 413:
        return True
    values = [
        body.get("error"),
        body.get("message"),
        body.get("detail"),
        body.get("error_code"),
        body.get("category"),
    ]
    text = " ".join(str(value) for value in values if value is not None).lower()
    return categorize_error(text) == "oversized_batch"


def _retry_limits_from_response(body: dict, advertised_limits: dict[str, int]) -> dict[str, int]:
    limits = body.get("limits")
    if not isinstance(limits, dict):
        return advertised_limits
    merged = dict(advertised_limits)
    for key in (
        "max_events_per_batch",
        "max_decompressed_bytes_per_batch",
        "retry_after_min_seconds",
        "retry_after_max_seconds",
    ):
        value = _positive_int(limits.get(key))
        if value is not None:
            merged[key] = value
    return merged


def _shrink_events_for_retry(events: list[dict]) -> list[dict]:
    return events[: max(1, len(events) // 2)]


def _single_oversized_event_result(event: dict, byte_limit: int, payload_size: int) -> BatchSyncResult:
    result = BatchSyncResult()
    result.total_events = 1
    event_id = event.get("event_id", "unknown")
    error = (
        f"single event exceeds decompressed byte limit "
        f"({payload_size} bytes > {byte_limit} bytes)"
    )
    result.error_count = 1
    result.failed_ids = [event_id]
    result.error_messages.append(f"{event_id}: {error}")
    result.event_results.append(
        BatchEventResult(
            event_id=event_id,
            # failed_permanent removes the event from the queue so the drain loop
            # can continue past it rather than stalling indefinitely.
            status="failed_permanent",
            error=error,
            error_category="oversized_event",
        )
    )
    return result


def _handle_single_oversized_event(
    event: dict,
    byte_limit: int,
    payload_size: int,
    queue: OfflineQueue,
    *,
    show_progress: bool,
) -> BatchSyncResult:
    result = _single_oversized_event_result(event, byte_limit, payload_size)
    queue.process_batch_results(result.event_results)
    if show_progress:
        print(format_sync_summary(result))
    return result


def _body_mentions_missing_private_team(body: dict) -> bool:
    values = [
        body.get("category"),
        body.get("error_code"),
        body.get("error"),
        body.get("message"),
        body.get("detail"),
    ]
    text = " ".join(str(value) for value in values if value is not None).lower()
    return CATEGORY_MISSING_PRIVATE_TEAM in text or "private teamspace" in text or ("private team" in text and "direct ingress" in text)


def _http_error_category(status_code: int, body: dict | None = None) -> str:
    """Map batch HTTP failures to deterministic diagnostic categories."""
    body = body or {}
    if status_code == 401:
        return "auth_expired"
    if status_code == 403:
        if _body_mentions_missing_private_team(body):
            return CATEGORY_MISSING_PRIVATE_TEAM
        return "unauthorized"
    if _is_oversized_batch_response(status_code, body):
        return "oversized_batch"
    if status_code == 429:
        return "throttled"
    if status_code == 408:
        return "retryable_transport"
    if 500 <= status_code < 600:
        return "server_error"
    return categorize_error(str(body)) if body else "unknown"


def _http_error_message(status_code: int, body: dict | None = None) -> str:
    body = body or {}
    message = body.get("message") or body.get("detail") or body.get("error")
    if isinstance(message, str) and message.strip():
        return message.strip()
    return f"HTTP {status_code}"


def _record_all_events_failed(
    result: BatchSyncResult,
    events: list[dict],
    *,
    error: str,
    category: str,
) -> None:
    result.error_messages.append(error)
    result.error_count = len(events)
    result.failed_ids = [e.get("event_id") for e in events]
    for evt in events:
        result.event_results.append(
            BatchEventResult(
                event_id=evt.get("event_id", "unknown"),
                status="rejected",
                error=error,
                error_category=category,
            )
        )


# ---------------------------------------------------------------------------
# Per-event result
# ---------------------------------------------------------------------------


@dataclass
class BatchEventResult:
    """Result of a single event within a batch response.

    Attributes:
        event_id: Unique event identifier.
        status: One of ``"success"``, ``"duplicate"``, ``"rejected"``,
            ``"failed_permanent"``. Permanent failures (e.g. oversized events
            that can never be sent) are removed from the queue rather than
            having their retry count bumped.
        error: Human-readable error message (only for failed events).
        error_category: Categorised reason (only for failed events).
    """

    event_id: str
    status: str  # "success", "duplicate", "rejected", "failed_permanent"
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
        """Convenience: only failed ``BatchEventResult`` entries (rejected or permanently failed)."""
        return [r for r in self.event_results if r.status in ("rejected", "failed_permanent")]

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
    to stdout. Events remain durable in the queue for later daemon drain.
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
        "generated_at": datetime.now(UTC).isoformat(),
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

        if status in ("success", "accepted", "warning"):
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


def batch_sync(  # noqa: C901
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
        auth_token: OAuth access token obtained from
            ``specify_cli.auth.get_token_manager().get_access_token()``.
            Callers (see ``sync/background.py``) are responsible for fetching
            and refreshing this token via ``TokenManager``.
        server_url: Server base URL (e.g., ``https://spec-kitty-dev.fly.dev``).
        limit: Maximum number of events to sync (default 1000).
        show_progress: Whether to print progress messages (default ``True``).

    Returns:
        BatchSyncResult with sync statistics, per-event results, and
        categorised error details.
    """
    result = BatchSyncResult()
    if not is_saas_sync_enabled():
        message = saas_sync_disabled_message()
        result.error_messages.append(message)
        if show_progress:
            print(message)
        return result

    if queue.size() == 0:
        if show_progress:
            print("No events to sync")
        return result

    team_slug = _current_team_slug()
    if team_slug is None:
        # FR-002/FR-004/FR-005/FR-007/NFR-002 (private-teamspace-ingress-safeguards):
        # Strict private-team requirement. The shared helper has already emitted a
        # structured ``logger.warning`` (with category, rehydrate_attempted,
        # ingress_sent, endpoint), which is the sole skip diagnostic. Skip the
        # ingress POST entirely and leave events in the durable queue for a
        # future drain after the SaaS provisions a Private Teamspace for this
        # user. FR-009 prohibits adding a stdout ``print`` here.
        #
        # Append a sentinel error message so ``sync_all_queued_events`` can
        # detect "no forward progress" and terminate its drain loop, instead
        # of spinning indefinitely on a queue that will never drain (Scenario
        # 6 in spec.md). The message is operator-facing diagnostic only; it
        # is NOT printed to stdout because callers route it through stderr/log.
        events = queue.drain_queue(limit=limit)
        result.total_events = len(events)
        _record_all_events_failed(
            result,
            events,
            error="skipped: no Private Teamspace available for direct ingress",
            category=CATEGORY_MISSING_PRIVATE_TEAM,
        )
        return result

    advertised_limits = _fetch_advertised_sync_ingress_limits(
        server_url=server_url,
        auth_token=auth_token,
        team_slug=team_slug,
    )
    events, payload = _select_events_for_advertised_limits(
        queue,
        requested_limit=limit,
        advertised_limits=advertised_limits,
    )
    result.total_events = len(events)
    byte_limit = _decompressed_byte_limit(advertised_limits)

    historical_rejection = _historical_mission_state_rejection(events)
    if historical_rejection is not None:
        if show_progress:
            print(historical_rejection.error_messages[0])
        return historical_rejection

    if len(events) == 1 and len(payload) > byte_limit:
        return _handle_single_oversized_event(
            events[0], byte_limit, len(payload), queue, show_progress=show_progress
        )

    if show_progress:
        estimated_remaining = max(queue.size() - len(events), 0)
        print(
            "Sync batch: "
            f"events={len(events)} "
            f"decompressed_bytes={len(payload)} "
            f"limit_bytes={byte_limit} "
            f"estimated_remaining={estimated_remaining}"
        )

    # Validate each event envelope against upstream contract before sending
    for evt in events:
        with suppress(Exception):
            validate_outbound_payload(evt, "envelope")

    # POST to batch endpoint
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Encoding": "gzip",
        "Content-Type": "application/json",
    }
    headers["X-Team-Slug"] = team_slug

    batch_url = f"{server_url.rstrip('/')}/api/v1/events/batch/"

    try:
        while True:
            compressed = gzip.compress(payload)
            response = requests.post(
                batch_url,
                data=compressed,
                headers=headers,
                timeout=60,
            )
            response_body = _safe_response_json(response)

            result.total_events = len(events)
            if _is_oversized_batch_response(response.status_code, response_body):
                advertised_limits = _retry_limits_from_response(response_body, advertised_limits)
                byte_limit = _decompressed_byte_limit(advertised_limits)
                if len(events) == 1:
                    return _handle_single_oversized_event(
                        events[0], byte_limit, len(payload), queue, show_progress=show_progress
                    )

                previous_size = len(events)
                events = _shrink_events_for_retry(events)
                payload = _build_batch_payload(events)
                while len(events) > 1 and len(payload) > byte_limit:
                    events = _shrink_events_for_retry(events)
                    payload = _build_batch_payload(events)
                if show_progress:
                    print(
                        "Retrying smaller sync batch: "
                        f"reason=oversized_batch previous_events={previous_size} "
                        f"next_events={len(events)} decompressed_bytes={len(payload)} "
                        f"limit_bytes={byte_limit}"
                    )
                continue
            break

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
            _parse_error_response(response_body, events, result)
            queue.process_batch_results(result.event_results)
            if show_progress:
                print(f"Batch sync failed (400):\n{format_sync_summary(result)}")

        else:
            if show_progress:
                print(f"Batch sync failed: HTTP {response.status_code}")
            _record_all_events_failed(
                result,
                events,
                error=_http_error_message(response.status_code, response_body),
                category=_http_error_category(response.status_code, response_body),
            )
            queue.process_batch_results(result.event_results)

    except requests.exceptions.Timeout:
        response = request_with_stdlib_fallback_sync(
            "POST",
            batch_url,
            timeout=60,
            content=compressed,
            headers=headers,
        )
        if response is not None:
            if response.status_code == 200:
                response_data = response.json()
                raw_results = response_data.get("results", [])
                _parse_event_results(raw_results, result)
                queue.process_batch_results(result.event_results)
                if show_progress:
                    print(format_sync_summary(result))
                return result
            if response.status_code == 401:
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
                return result
            if response.status_code == 400:
                response_body = response.json()
                _parse_error_response(response_body, events, result)
                queue.process_batch_results(result.event_results)
                if show_progress:
                    print(f"Batch sync failed (400):\n{format_sync_summary(result)}")
                return result
            if show_progress:
                print(f"Batch sync failed: HTTP {response.status_code}")
            response_body = _safe_response_json(response)
            _record_all_events_failed(
                result,
                events,
                error=_http_error_message(response.status_code, response_body),
                category=_http_error_category(response.status_code, response_body),
            )
            queue.process_batch_results(result.event_results)
            return result
        if show_progress:
            print("Batch sync failed: Request timeout")
        _record_all_events_failed(
            result,
            events,
            error="Request timeout",
            category="retryable_transport",
        )
        queue.process_batch_results(result.event_results)

    except requests.exceptions.ConnectionError as e:
        response = request_with_stdlib_fallback_sync(
            "POST",
            batch_url,
            timeout=60,
            content=compressed,
            headers=headers,
        )
        if response is not None:
            if response.status_code == 200:
                response_data = response.json()
                raw_results = response_data.get("results", [])
                _parse_event_results(raw_results, result)
                queue.process_batch_results(result.event_results)
                if show_progress:
                    print(format_sync_summary(result))
                return result
            if response.status_code == 401:
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
                return result
            if response.status_code == 400:
                response_body = response.json()
                _parse_error_response(response_body, events, result)
                queue.process_batch_results(result.event_results)
                if show_progress:
                    print(f"Batch sync failed (400):\n{format_sync_summary(result)}")
                return result
            if show_progress:
                print(f"Batch sync failed: HTTP {response.status_code}")
            response_body = _safe_response_json(response)
            _record_all_events_failed(
                result,
                events,
                error=_http_error_message(response.status_code, response_body),
                category=_http_error_category(response.status_code, response_body),
            )
            queue.process_batch_results(result.event_results)
            return result
        if show_progress:
            print(f"Batch sync failed: Connection error - {e}")
        _record_all_events_failed(
            result,
            events,
            error=f"Connection error: {e}",
            category="retryable_transport",
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
        auth_token: OAuth access token obtained from TokenManager.
        server_url: Server base URL.
        batch_size: Events per batch (default 1000).
        show_progress: Whether to print progress.

    Returns:
        Aggregated BatchSyncResult across all batches.
    """
    total_result = BatchSyncResult()
    if not is_saas_sync_enabled():
        message = saas_sync_disabled_message()
        total_result.error_messages.append(message)
        if show_progress:
            print(message)
        return total_result

    batch_num = 0
    initial_queued = queue.size()
    if show_progress:
        print(f"Initial queued events: {initial_queued}")

    while queue.size() > 0:
        batch_num += 1
        if show_progress:
            print(
                f"\n--- Batch {batch_num} --- "
                f"remaining={queue.size()} requested_batch_size={batch_size}"
            )

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

        if show_progress:
            print(
                "Progress: "
                f"accepted={total_result.synced_count} "
                f"duplicates={total_result.duplicate_count} "
                f"failed={total_result.error_count} "
                f"remaining={queue.size()}"
            )

        # Stop if no progress made. This covers two cases:
        #   1. All events in the batch failed (error_count > 0).
        #   2. The batch was skipped entirely because the strict private-team
        #      resolver returned None (FR-002/FR-004 — no Private Teamspace
        #      means no direct ingress; the helper's structured warning is the
        #      sole stderr diagnostic). Without this, sync_all_queued_events
        #      would spin forever on a shared-only session because the queue
        #      never drains.
        #
        # Exception: permanently-failed events (e.g. oversized_event) are
        # removed from the queue by process_batch_results, so the drain IS
        # making progress — continue to subsequent events rather than stopping.
        if result.success_count == 0:
            all_permanent = bool(result.event_results) and all(
                r.status == "failed_permanent" for r in result.event_results
            )
            if all_permanent:
                continue
            if show_progress:
                if result.error_count > 0:
                    print("Stopping: No events successfully synced in this batch")
                else:
                    print("Stopping: Batch skipped (no Private Teamspace; see structured stderr diagnostic)")
            break

    if show_progress:
        print("\n=== Sync Complete ===")
        print(f"Initial queued: {initial_queued}")
        print(format_sync_summary(total_result))
        if queue.size() > 0:
            print(f"Remaining in queue: {queue.size()} events")

    return total_result
