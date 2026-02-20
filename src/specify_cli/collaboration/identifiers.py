"""Identifier helpers for collaboration events."""

from __future__ import annotations

import uuid

from specify_cli.events.ulid_utils import generate_event_id


def resolve_project_uuid(
    mission_id: str,
    mission_run_id: str | None = None,
    explicit_project_uuid: str | None = None,
) -> uuid.UUID:
    """Resolve a stable UUID for event ``project_uuid`` fields.

    ``project_uuid`` may come from SaaS, but local/offline flows often only have
    mission IDs or run IDs that are not UUIDs (e.g. ULIDs, slugs).
    This helper makes that safe and deterministic:
    1. Use explicit UUID if valid.
    2. Use mission_run_id if it is a valid UUID.
    3. Derive UUIDv5 from mission_run_id.
    4. Derive UUIDv5 from mission_id.
    """
    for raw in (explicit_project_uuid, mission_run_id):
        if not raw:
            continue
        try:
            return uuid.UUID(raw)
        except (ValueError, AttributeError, TypeError):
            # Deterministic fallback for non-UUID IDs (ULID/slug/etc.)
            prefix = "project" if raw == explicit_project_uuid else "mission-run"
            return uuid.uuid5(uuid.NAMESPACE_URL, f"{prefix}:{raw}")

    return uuid.uuid5(uuid.NAMESPACE_URL, f"mission:{mission_id}")


def resolve_correlation_id(mission_run_id: str | None) -> str:
    """Resolve a valid correlation ID for event models.

    Event schema requires ULID-like identifiers (min length 26). Some local
    tests and offline flows use short placeholders (e.g. ``run-1``), which
    should not fail event construction.
    """
    if isinstance(mission_run_id, str) and len(mission_run_id) >= 26:
        return mission_run_id
    return generate_event_id()
