"""Local event schema validation for the offline queue.

Validates queued events against the Pydantic ``Event`` model and
per-event-type payload rules before they are sent to the server.

The ``diagnose_events()`` function is the main entry point, used by
the ``spec-kitty sync diagnose`` CLI command.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from specify_cli.spec_kitty_events.models import Event
from .batch import categorize_error
from .emitter import _PAYLOAD_RULES, VALID_EVENT_TYPES, VALID_AGGREGATE_TYPES


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
    model_fields = {
        "event_id": event_data.get("event_id"),
        "event_type": event_data.get("event_type"),
        "aggregate_id": event_data.get("aggregate_id"),
        "payload": event_data.get("payload", {}),
        "timestamp": event_data.get("timestamp"),
        "node_id": event_data.get("node_id"),
        "lamport_clock": event_data.get("lamport_clock"),
        "causation_id": event_data.get("causation_id"),
    }
    try:
        Event(**model_fields)
    except PydanticValidationError as exc:
        for err in exc.errors():
            loc = " -> ".join(str(part) for part in err["loc"])
            errors.append(f"{loc}: {err['msg']}")


def _validate_extended_envelope(event_data: dict[str, Any], errors: list[str]) -> None:
    """Check envelope fields that the Pydantic model does not cover.

    These are fields required by the server contract but absent from the
    library's ``Event`` model (e.g. ``aggregate_type``, ``event_type``
    membership).
    """
    # aggregate_type must be a known value
    agg_type = event_data.get("aggregate_type")
    if agg_type is not None and agg_type not in VALID_AGGREGATE_TYPES:
        errors.append(f"aggregate_type: must be one of {sorted(VALID_AGGREGATE_TYPES)}, got {agg_type!r}")

    # event_type must be a known value
    etype = event_data.get("event_type")
    if etype is not None and etype not in VALID_EVENT_TYPES:
        errors.append(f"event_type: unknown event type {etype!r}; expected one of {sorted(VALID_EVENT_TYPES)}")


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
        errors.append(f"payload: missing required field(s) {sorted(missing)} for {event_type}")

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
                errors.append(f"payload.{field_name}: invalid value {value!r} for {event_type}")
