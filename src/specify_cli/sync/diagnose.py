"""Local event schema validation for the offline queue.

Validates queued events against the Pydantic ``Event`` model and
per-event-type payload rules before they are sent to the server.

The ``diagnose_events()`` function is the main entry point, used by
the ``spec-kitty sync diagnose`` CLI command.

Also provides body upload queue diagnostics via ``diagnose_body_queue()``.

WP02 (#842): exposes :func:`emit_diagnostic`, the single canonical
routing helper for sync / auth / tracker diagnostics. It guarantees
the strict-JSON contract (FR-003, FR-004) — diagnostic content is
either nested into a caller-provided JSON envelope under the
``diagnostics`` top-level key, or written to **stderr**. It NEVER
writes to stdout.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from pydantic import ValidationError as PydanticValidationError

from spec_kitty_events import Event
from .batch import categorize_error
from .emitter import _PAYLOAD_RULES, VALID_EVENT_TYPES, VALID_AGGREGATE_TYPES

if TYPE_CHECKING:
    from .body_queue import BodyQueueStats, OfflineBodyUploadQueue


# ---------------------------------------------------------------------------
# Diagnostic routing helper (WP02 / #842)
# ---------------------------------------------------------------------------


# Categories the helper accepts.  Keep the literal narrow so that callers
# cannot drift the contract by inventing new buckets.  If a new bucket is
# needed, add it here AND extend the contract document.
DiagnosticCategory = Literal["sync", "auth", "tracker"]


def emit_diagnostic(
    message: str,
    *,
    category: DiagnosticCategory,
    json_mode: bool,
    envelope: dict[str, Any] | None = None,
) -> None:
    """Route a sync/auth/tracker diagnostic message safely.

    This helper is the canonical entry point for any module under
    ``specify_cli.sync``, ``specify_cli.auth``, or the tracker glue that
    wants to surface a diagnostic line during a CLI command. It enforces
    the strict-JSON envelope contract (#842, FR-003, FR-004):

    * Diagnostic content NEVER lands on **stdout**.
    * In ``--json`` mode, the caller may supply an *envelope* dict; the
      message is appended under ``envelope["diagnostics"][category]``
      so the consumer observes it programmatically.
    * Otherwise the message is written to **stderr**.

    Args:
        message: Human-readable diagnostic line.
        category: One of ``"sync"``, ``"auth"``, ``"tracker"``. Determines
            the nested key when an envelope is provided.
        json_mode: ``True`` when the calling CLI command is producing a
            ``--json`` payload. Drives the routing choice between
            envelope-nesting and stderr.
        envelope: Optional dict that will be the strict-JSON output for
            the current command. When supplied with ``json_mode=True``,
            the message is nested rather than printed.

    Routing matrix:

    +------------+----------------+--------------------------------------+
    | json_mode  | envelope       | destination                          |
    +============+================+======================================+
    | False      | (any)          | stderr                               |
    +------------+----------------+--------------------------------------+
    | True       | None           | stderr                               |
    +------------+----------------+--------------------------------------+
    | True       | dict           | envelope["diagnostics"][category]    |
    +------------+----------------+--------------------------------------+

    Notes:
        - The helper imports ``rich.console.Console`` lazily so that the
          stderr write benefits from rich formatting when available, but
          it falls back to ``print(..., file=sys.stderr)`` if rich is not
          importable for any reason.
        - Mutation of ``envelope`` is done in-place; the caller decides
          when to serialise.
    """
    if json_mode and envelope is not None:
        diagnostics = envelope.setdefault("diagnostics", {})
        if not isinstance(diagnostics, dict):
            # Envelope already used "diagnostics" for something else.
            # Surface to stderr instead of mutating a foreign structure.
            _write_stderr(message)
            return
        bucket = diagnostics.setdefault(category, [])
        if not isinstance(bucket, list):
            _write_stderr(message)
            return
        bucket.append(message)
        return

    # All non-envelope paths go to stderr — never stdout.
    _write_stderr(message)


def _write_stderr(message: str) -> None:
    """Write *message* to the *current* ``sys.stderr``.

    We deliberately re-read ``sys.stderr`` on every call rather than
    capturing it at import-time so tests (and any operator that swaps
    stderr in-process) see the message land where they expect.

    ``print(..., file=sys.stderr)`` is sufficient — rich formatting is
    deliberately avoided here because (a) the helper must work in
    minimal environments, and (b) rich's ``Console`` caches its output
    file at construction, which interferes with stream-redirection
    tests for the strict-JSON contract.
    """
    print(message, file=sys.stderr)


@dataclass
class DiagnoseResult:
    """Result of validating a single queued event.

    Attributes:
        event_id: The event's identifier (or ``"unknown"`` if missing).
        valid: ``True`` when the event passes all checks.
        errors: Human-readable descriptions of each validation failure.
        event_type: The ``event_type`` field value (or ``"unknown"``).
        error_category: Categorised label for the *first* error (reuses
            WP02's ``categorize_error`` for consistent grouping).
    """

    event_id: str
    valid: bool
    errors: list[str] = field(default_factory=list)
    event_type: str = ""
    error_category: str = ""


# -- Public API ---------------------------------------------------------------


def diagnose_events(queue_entries: list[dict[str, Any]]) -> list[DiagnoseResult]:
    """Validate a list of queued event dicts.

    Each entry is validated against:

    1. The Pydantic ``Event`` envelope model (required fields, types,
       ULID format, etc.).
    2. Per-event-type payload rules defined in ``emitter._PAYLOAD_RULES``.

    Returns one ``DiagnoseResult`` per entry.
    """
    return [_validate_event(entry) for entry in queue_entries]


# -- Internal helpers ----------------------------------------------------------


def _validate_event(event_data: dict[str, Any]) -> DiagnoseResult:
    """Validate a single event dict and return a ``DiagnoseResult``."""
    event_id = event_data.get("event_id", "unknown")
    event_type = event_data.get("event_type", "unknown")
    errors: list[str] = []

    # 1. Envelope validation via Pydantic Event model
    _validate_envelope(event_data, errors)

    # 2. Supplementary envelope checks not covered by the Pydantic model
    _validate_extended_envelope(event_data, errors)

    # 3. Payload validation against per-event-type rules
    if event_type in _PAYLOAD_RULES:
        _validate_payload(event_type, event_data.get("payload", {}), errors)

    valid = len(errors) == 0
    # Categorise the first error for consistent grouping with batch.py
    error_category = ""
    if errors:
        error_category = categorize_error(errors[0])

    return DiagnoseResult(
        event_id=str(event_id),
        valid=valid,
        errors=errors,
        event_type=str(event_type),
        error_category=error_category,
    )


def _validate_envelope(event_data: dict[str, Any], errors: list[str]) -> None:
    """Validate the event envelope against the Pydantic ``Event`` model.

    Extracts only the fields the model cares about so that extra fields
    (``team_slug``, ``project_uuid``, etc.) don't cause spurious failures.
    """
    # spec-kitty-events 4.0.0 added build_id, project_uuid, correlation_id as
    # required fields; fall back to safe defaults for events emitted under 3.x
    # schema that lack these fields.
    model_fields = {
        "event_id": event_data.get("event_id"),
        "event_type": event_data.get("event_type"),
        "aggregate_id": event_data.get("aggregate_id"),
        "payload": event_data.get("payload", {}),
        "timestamp": event_data.get("timestamp"),
        "node_id": event_data.get("node_id"),
        "lamport_clock": event_data.get("lamport_clock"),
        "causation_id": event_data.get("causation_id"),
        "build_id": event_data.get("build_id") or "unknown",
        "project_uuid": event_data.get("project_uuid") or "00000000-0000-0000-0000-000000000000",
        "correlation_id": event_data.get("correlation_id") or event_data.get("event_id"),
    }
    try:
        Event(**model_fields)
    except PydanticValidationError as exc:
        for err in exc.errors():
            loc = " -> ".join(str(part) for part in err["loc"])
            errors.append(f"{loc}: {err['msg']}")


def _validate_extended_envelope(
    event_data: dict[str, Any], errors: list[str]
) -> None:
    """Check envelope fields that the Pydantic model does not cover.

    These are fields required by the server contract but absent from the
    library's ``Event`` model (e.g. ``aggregate_type``, ``event_type``
    membership).
    """
    # aggregate_type must be a known value
    agg_type = event_data.get("aggregate_type")
    if agg_type is not None and agg_type not in VALID_AGGREGATE_TYPES:
        errors.append(
            f"aggregate_type: must be one of {sorted(VALID_AGGREGATE_TYPES)}, "
            f"got {agg_type!r}"
        )

    # event_type must be a known value
    etype = event_data.get("event_type")
    if etype is not None and etype not in VALID_EVENT_TYPES:
        errors.append(
            f"event_type: unknown event type {etype!r}; "
            f"expected one of {sorted(VALID_EVENT_TYPES)}"
        )


def _validate_payload(
    event_type: str,
    payload: dict[str, Any],
    errors: list[str],
) -> None:
    """Validate *payload* against the per-event-type rules in ``_PAYLOAD_RULES``.

    Checks required fields and per-field validators.
    """
    rules = _PAYLOAD_RULES.get(event_type)
    if rules is None:
        return

    # Required fields
    required: set[str] = rules.get("required", set())
    missing = required - set(payload.keys())
    if missing:
        errors.append(
            f"payload: missing required field(s) {sorted(missing)} "
            f"for {event_type}"
        )

    # Per-field validators
    validators: dict[str, Any] = rules.get("validators", {})
    for field_name, validator_fn in validators.items():
        if field_name in payload:
            value = payload[field_name]
            try:
                ok = validator_fn(value)
            except Exception:
                ok = False
            if not ok:
                errors.append(
                    f"payload.{field_name}: invalid value {value!r} "
                    f"for {event_type}"
                )


# -- Body queue diagnostics ---------------------------------------------------


def diagnose_body_queue(body_queue: OfflineBodyUploadQueue) -> dict[str, Any]:
    """Return body queue health diagnostics.

    Mirrors the event queue diagnostic pattern for consistency.
    """
    stats = body_queue.get_stats()
    return {
        "body_queue": {
            "total_tasks": stats.total_count,
            "ready_to_send": stats.ready_count,
            "in_backoff": stats.backoff_count,
            "max_retry_count": stats.max_retry_count,
            "oldest_task_age_seconds": (
                time.time() - stats.oldest_created_at
                if stats.oldest_created_at is not None
                else None
            ),
            "retry_distribution": stats.retry_histogram,
            "recorded_failure_count": body_queue.failure_count(),
            "recent_failures": [
                {
                    "artifact_path": failure.artifact_path,
                    "failure_reason": failure.failure_reason,
                    "failure_count": failure.failure_count,
                    "mission_slug": failure.mission_slug,
                    "target_branch": failure.target_branch,
                    "last_failed_at": failure.last_failed_at,
                }
                for failure in body_queue.get_recent_failures()
            ],
        }
    }


def print_body_queue_summary(stats: BodyQueueStats) -> None:
    """Print a human-readable body queue summary using Rich."""
    from rich.console import Console

    console = Console()
    console.print("[bold]Body Upload Queue[/bold]")
    console.print(f"  Total: {stats.total_count}")
    console.print(f"  Ready: {stats.ready_count}")
    console.print(f"  In backoff: {stats.backoff_count}")
    if stats.max_retry_count > 0:
        console.print(f"  Max retries: {stats.max_retry_count}")
    if stats.retry_histogram:
        parts = ", ".join(
            f"{k}={v}" for k, v in sorted(stats.retry_histogram.items())
        )
        console.print(f"  Retry distribution: {parts}")
