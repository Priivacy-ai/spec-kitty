"""Local-first canonical lifecycle event persistence.

This module is the durable, local-first writer for the canonical event
stream that records project initialization, mission creation,
spec/plan/tasks artifact lifecycle, and work-package creation. Lifecycle
events land on disk synchronously *before* any best-effort SaaS outbox
fan-out, so local dashboards and TeamSpace import always have a complete
history even when the scoped sync boundary is unavailable.

Two log targets exist:

* **Project-level log** (``<repo_root>/.kittify/canonical-events.jsonl``)
  carries project-wide events such as ``ProjectInitialized``.

* **Mission-level log** (``<feature_dir>/status.events.jsonl``) is
  shared with the existing ``WPStatusChanged`` reducer; lifecycle events
  carry a top-level ``event_type`` field and are intentionally skipped
  by :mod:`specify_cli.status.store`'s ``StatusEvent`` reader.

Idempotency
-----------

Each appender is keyed by ``(event_type, deduplication tuple)`` so
re-running the producer (e.g. ``finalize-tasks`` on an existing
mission) is a no-op for already-recorded events. This makes the
canonical stream a safe target for repair / replay tooling.

The schema mirrors the contracts defined in
``spec_kitty_events.project_lifecycle`` (sibling repo). The
``project_lifecycle`` module is referenced via string constants here
so that the CLI does not hard-fail when an older release of
``spec-kitty-events`` is installed; the payloads are forward-compatible
with the typed contracts.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
from datetime import datetime, UTC
from pathlib import Path
from typing import Any
from collections.abc import Iterable, Mapping

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event type constants — kept in sync with spec_kitty_events.project_lifecycle
# ---------------------------------------------------------------------------

PROJECT_INITIALIZED = "ProjectInitialized"
MISSION_CREATED = "MissionCreated"
SPECIFY_STARTED = "SpecifyStarted"
SPECIFY_COMPLETED = "SpecifyCompleted"
PLAN_STARTED = "PlanStarted"
PLAN_COMPLETED = "PlanCompleted"
TASKS_STARTED = "TasksStarted"
TASKS_COMPLETED = "TasksCompleted"
WP_CREATED = "WPCreated"
REVIEWER_SELF_APPROVAL = "ReviewerSelfApproval"

LIFECYCLE_EVENT_TYPES = frozenset({
    PROJECT_INITIALIZED,
    MISSION_CREATED,
    SPECIFY_STARTED,
    SPECIFY_COMPLETED,
    PLAN_STARTED,
    PLAN_COMPLETED,
    TASKS_STARTED,
    TASKS_COMPLETED,
    WP_CREATED,
    REVIEWER_SELF_APPROVAL,
})

PROJECT_EVENTS_FILENAME = "canonical-events.jsonl"
MISSION_EVENTS_FILENAME = "status.events.jsonl"


# ---------------------------------------------------------------------------
# Path resolvers
# ---------------------------------------------------------------------------


def project_event_log_path(repo_root: Path) -> Path:
    """Return the canonical project-level event log path for *repo_root*."""
    return repo_root / ".kittify" / PROJECT_EVENTS_FILENAME


def mission_event_log_path(feature_dir: Path) -> Path:
    """Return the canonical mission-level event log path for *feature_dir*."""
    return feature_dir / MISSION_EVENTS_FILENAME


# ---------------------------------------------------------------------------
# Reading & writing
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _generate_event_id() -> str:
    try:
        from ulid import ULID  # type: ignore[import-not-found]

        return str(ULID())
    except Exception:  # pragma: no cover — fallback for stripped envs
        import uuid

        return uuid.uuid4().hex


def _read_lifecycle_lines(path: Path) -> list[dict[str, Any]]:
    """Best-effort read of lifecycle event dicts from a JSONL file.

    Tolerates missing files, blank lines, and corrupted lines (the
    bad lines are skipped with a debug log). Only entries that carry
    a top-level ``event_type`` are returned: any sibling format (e.g.
    ``WPStatusChanged`` payloads written by the status reducer) is
    filtered out so callers can scan lifecycle history in isolation.
    """
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.debug("Could not read lifecycle log %s: %s", path, exc)
        return []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            logger.debug("Skipping non-JSON lifecycle line in %s", path)
            continue
        if isinstance(obj, dict) and isinstance(obj.get("event_type"), str):
            out.append(obj)
    return out


def _atomic_append(path: Path, line: str) -> None:
    """Append a single JSON line to *path*, creating parents as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()
        with contextlib.suppress(OSError):
            os.fsync(fh.fileno())


# canonical-producer-exempt: #1198 -- local lifecycle JSONL envelope.
def _build_envelope(
    event_type: str,
    payload: Mapping[str, Any],
    *,
    aggregate_id: str,
    aggregate_type: str,
    project_uuid: str | None = None,
    project_slug: str | None = None,
    schema_version: str = "5.0.0",
) -> dict[str, Any]:
    return {  # canonical-producer-exempt: #1198 — see function-level comment above
        "event_id": _generate_event_id(),
        "event_type": event_type,
        "aggregate_id": aggregate_id,
        "aggregate_type": aggregate_type,
        "schema_version": schema_version,
        "timestamp": _now_iso(),
        "payload": dict(payload),
        "project_uuid": project_uuid,
        "project_slug": project_slug,
    }


def _repo_root_for_lifecycle_log(log_path: Path | None) -> Path | None:
    if log_path is None:
        return None
    resolved = log_path.resolve()
    if resolved.name == PROJECT_EVENTS_FILENAME and resolved.parent.name == ".kittify":
        return resolved.parent.parent
    if (
        resolved.name == MISSION_EVENTS_FILENAME
        and resolved.parent.parent.name == "kitty-specs"
    ):
        return resolved.parent.parent.parent
    return None


def _validate_lifecycle_payload(event_type: str, payload: Mapping[str, Any]) -> None:
    """Validate lifecycle payloads against the canonical events contract.

    Delegates to ``spec_kitty_events.conformance.validate_event`` so every
    event type the events package recognises (lifecycle, status, dossier,
    build, …) is checked under the same canonical rules.

    Phase-2 widening (issues Priivacy-ai/spec-kitty#1198 / #1200): we now
    pass ``strict=True`` and raise on both ``model_violations`` and
    ``schema_violations`` for known event types. The previous behavior
    raised only on model violations, which let JSON-schema-level drift
    (missing required fields, additionalProperties=false breaches) reach
    the SaaS boundary as a runtime canary failure instead of a producer
    emit-time error.

    Local-only event types (``spec_kitty_events.LOCAL_ONLY_EVENT_TYPES``)
    skip strict validation by design — the set is currently empty but
    reserved for future internal-only event types.

    Unknown event types (event_type not in ``_EVENT_TYPE_TO_MODEL``) pass
    through quietly so unrecognised types don't become sudden hard
    failures. The producer lint catches the corresponding hand-rolled
    dict at static analysis time.
    """
    from spec_kitty_events import LOCAL_ONLY_EVENT_TYPES
    from spec_kitty_events.conformance import validate_event
    from spec_kitty_events.conformance.validators import _EVENT_TYPE_TO_MODEL

    if event_type in LOCAL_ONLY_EVENT_TYPES:
        return

    if event_type not in _EVENT_TYPE_TO_MODEL:
        return

    result = validate_event(dict(payload), event_type, strict=True)
    if result.model_violations or result.schema_violations:
        model_details = [f"{v.field}: {v.message}" for v in result.model_violations]
        schema_details = [
            f"{v.json_path}: {v.message}" for v in result.schema_violations
        ]
        details = "; ".join((*model_details, *schema_details))
        raise ValueError(
            f"Lifecycle payload for {event_type!r} fails canonical contract: "
            f"{details}"
        )


def _canonical_lifecycle_payload_for_saas(
    event_type: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Project a local lifecycle payload to the strict SaaS wire shape.

    Local Started events keep ``artifact_path`` so local replay and dashboards
    can identify the artifact opened by the phase transition. The canonical
    ``spec-kitty-events`` Started payloads intentionally do not expose that
    field, so the SaaS fan-out strips it before strict validation and queueing.
    """
    projected = dict(payload)
    if event_type.endswith("Started"):
        projected.pop("artifact_path", None)
    return projected


def _build_saas_lifecycle_event(
    envelope: Mapping[str, Any],
    *,
    log_path: Path | None = None,
) -> dict[str, Any] | None:
    """Return a SaaS-materializable lifecycle event for the scoped outbox.

    Local lifecycle JSONL intentionally keeps its local-first shape. The SaaS
    queue, however, must carry the same canonical envelope fields as normal
    sync events or live ingress rejects the batch.
    """
    from specify_cli.status.adapters import fire_lifecycle_saas_fanout

    fire_lifecycle_saas_fanout(envelope=envelope, log_path=log_path)
    return None


def _queue_lifecycle_event_if_enabled(
    envelope: Mapping[str, Any],
    *,
    log_path: Path | None = None,
) -> None:
    """Best-effort SaaS outbox fan-out for canonical lifecycle events."""
    _build_saas_lifecycle_event(envelope, log_path=log_path)


def _match_lifecycle_event(
    candidate: Mapping[str, Any],
    *,
    event_type: str,
    dedup_keys: Mapping[str, Any],
) -> bool:
    if candidate.get("event_type") != event_type:
        return False
    payload = candidate.get("payload") or {}
    if not isinstance(payload, Mapping):
        return False
    return all(
        _dedup_value_matches(key, payload.get(key), expected)
        for key, expected in dedup_keys.items()
    )


def _dedup_value_matches(key: str, actual: Any, expected: Any) -> bool:
    if actual == expected:
        return True
    if key == "artifact_path" and isinstance(actual, str) and isinstance(expected, str):
        return Path(actual).name == Path(expected).name
    return False


def has_lifecycle_event(
    log_path: Path,
    *,
    event_type: str,
    dedup_keys: Mapping[str, Any],
) -> bool:
    """Return True if the log already contains a matching lifecycle event."""
    return any(
        _match_lifecycle_event(entry, event_type=event_type, dedup_keys=dedup_keys)
        for entry in _read_lifecycle_lines(log_path)
    )


def append_lifecycle_event(
    log_path: Path,
    event_type: str,
    payload: Mapping[str, Any],
    *,
    aggregate_id: str,
    aggregate_type: str,
    project_uuid: str | None = None,
    project_slug: str | None = None,
    dedup_keys: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Append a lifecycle event to *log_path* unless an idempotent match exists.

    Returns the persisted event envelope, or ``None`` when the append was
    skipped because an event with the same ``(event_type, dedup_keys)``
    tuple is already on disk. Failures fall back to a debug log; the
    function never raises so callers can chain it safely behind a
    fire-and-forget ``contextlib.suppress`` if they choose.
    """
    if event_type not in LIFECYCLE_EVENT_TYPES:
        logger.debug("Refusing to append unknown lifecycle event type %r", event_type)
        return None

    if dedup_keys and has_lifecycle_event(
        log_path, event_type=event_type, dedup_keys=dedup_keys
    ):
        logger.debug(
            "Lifecycle event %s already present in %s; skipping append",
            event_type,
            log_path,
        )
        return None

    envelope = _build_envelope(
        event_type,
        payload,
        aggregate_id=aggregate_id,
        aggregate_type=aggregate_type,
        project_uuid=project_uuid,
        project_slug=project_slug,
    )
    try:
        _atomic_append(log_path, json.dumps(envelope, sort_keys=True))
    except OSError as exc:
        logger.warning("Could not persist %s event to %s: %s", event_type, log_path, exc)
        return None
    _queue_lifecycle_event_if_enabled(envelope, log_path=log_path)
    return envelope


# ---------------------------------------------------------------------------
# Convenience helpers (per event type)
# ---------------------------------------------------------------------------


def emit_project_initialized(
    repo_root: Path,
    *,
    project_uuid: str,
    project_slug: str | None,
    actor: str = "cli",
    runtime_version: str | None = None,
    initialized_at: str | None = None,
) -> dict[str, Any] | None:
    """Record a local ``ProjectInitialized`` event for *repo_root*.

    Idempotent on ``project_uuid``: re-running ``spec-kitty init`` (or any
    bootstrap flow) on an already-initialized project is a no-op.

    The payload is constructed via the canonical
    :class:`spec_kitty_events.project_lifecycle.ProjectInitializedPayload`
    so producer-time validation rejects any field that drifts from the
    contract (issues Priivacy-ai/spec-kitty#1198 / #1200).
    """
    from spec_kitty_events.project_lifecycle import ProjectInitializedPayload

    log_path = project_event_log_path(repo_root)
    payload = ProjectInitializedPayload(
        project_uuid=project_uuid,
        project_slug=project_slug,
        actor=actor,
        runtime_version=runtime_version,
        initialized_at=initialized_at or _now_iso(),
    ).model_dump(mode="json", exclude_none=False)
    return append_lifecycle_event(
        log_path,
        PROJECT_INITIALIZED,
        payload,
        aggregate_id=project_uuid,
        aggregate_type="Project",
        project_uuid=project_uuid,
        project_slug=project_slug,
        dedup_keys={"project_uuid": project_uuid},
    )


def emit_mission_created_local(
    feature_dir: Path,
    *,
    mission_slug: str,
    mission_id: str | None,
    mission_number: int | None,
    mission_type: str,
    target_branch: str,
    wp_count: int = 0,
    project_uuid: str | None = None,
    project_slug: str | None = None,
    friendly_name: str | None = None,
    purpose_tldr: str | None = None,
    purpose_context: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any] | None:
    """Record a local ``MissionCreated`` event for *feature_dir*.

    Idempotent on ``mission_slug``. The mission's
    ``status.events.jsonl`` is created on first call.

    ``mission_type`` and ``wp_count`` are required by the canonical
    ``mission_created_payload`` schema (events 5.1.0). This helper does not
    take an actor because the payload schema declares ``additionalProperties:
    false`` with no ``actor`` property.
    See Priivacy-ai/spec-kitty#1199 for the full required-field surface.

    The payload is constructed via the canonical
    :class:`spec_kitty_events.lifecycle.MissionCreatedPayload` so
    producer-time validation rejects extras / missing required fields
    (issues Priivacy-ai/spec-kitty#1198 / #1200).
    """
    from spec_kitty_events.lifecycle import MissionCreatedPayload

    log_path = mission_event_log_path(feature_dir)

    # MissionCreatedPayload requires friendly_name / purpose_tldr /
    # purpose_context (min_length=1). Fall back to mission_slug-derived
    # defaults so this helper never raises on legitimate callers that
    # omit them — see the local-first semantics in
    # ``spec-kitty agent mission create``.
    effective_friendly_name = (friendly_name or "").strip() or mission_slug
    effective_purpose_tldr = (purpose_tldr or "").strip() or effective_friendly_name
    effective_purpose_context = (
        (purpose_context or "").strip()
        or f"Local mission for {effective_friendly_name} (target branch: {target_branch})."
    )

    payload_model = MissionCreatedPayload(
        mission_id=mission_id,
        mission_slug=mission_slug,
        mission_number=mission_number,
        mission_type=mission_type,
        target_branch=target_branch,
        wp_count=wp_count,
        friendly_name=effective_friendly_name,
        purpose_tldr=effective_purpose_tldr,
        purpose_context=effective_purpose_context,
        created_at=created_at or _now_iso(),
    )
    payload: dict[str, Any] = payload_model.model_dump(
        mode="json", exclude_none=False
    )

    return append_lifecycle_event(
        log_path,
        MISSION_CREATED,
        payload,
        aggregate_id=mission_id or mission_slug,
        aggregate_type="Mission",
        project_uuid=project_uuid,
        project_slug=project_slug,
        dedup_keys={"mission_slug": mission_slug},
    )


def emit_artifact_phase(
    feature_dir: Path,
    *,
    event_type: str,
    mission_slug: str,
    mission_number: int | None = None,
    actor: str = "cli",
    artifact_path: str | None = None,
    summary: str | None = None,
    wp_count: int | None = None,
    project_uuid: str | None = None,
    project_slug: str | None = None,
    at: str | None = None,
) -> dict[str, Any] | None:
    """Append a Specify/Plan/Tasks lifecycle event for the mission.

    Started and completed events dedupe on
    ``(event_type, mission_slug, artifact_path)`` when an artifact path is
    known, falling back to ``(event_type, mission_slug)`` for legacy callers.
    The local log keeps ``artifact_path`` on Started events so dashboards and
    mission-creation replay know which artifact was opened.

    Started/Completed split (issues Priivacy-ai/spec-kitty#1198 / #1203
    "dormant mask"): the canonical pydantic payload models in
    ``spec_kitty_events.project_lifecycle`` declare ``extra="forbid"``,
    so ``summary`` / ``wp_count`` remain Completed-only. ``artifact_path`` is
    local lifecycle metadata for Started events; the SaaS fan-out path strips
    it before strict canonical validation.
    """
    from spec_kitty_events.project_lifecycle import (
        PlanCompletedPayload,
        PlanStartedPayload,
        SpecifyCompletedPayload,
        SpecifyStartedPayload,
        TasksCompletedPayload,
        TasksStartedPayload,
    )

    _PAYLOAD_MODEL_FOR_EVENT_TYPE: dict[str, type] = {
        SPECIFY_STARTED: SpecifyStartedPayload,
        SPECIFY_COMPLETED: SpecifyCompletedPayload,
        PLAN_STARTED: PlanStartedPayload,
        PLAN_COMPLETED: PlanCompletedPayload,
        TASKS_STARTED: TasksStartedPayload,
        TASKS_COMPLETED: TasksCompletedPayload,
    }

    payload_model_cls = _PAYLOAD_MODEL_FOR_EVENT_TYPE.get(event_type)
    if payload_model_cls is None:
        raise ValueError(f"Unsupported artifact phase event_type: {event_type!r}")

    # Common fields all six payloads share.
    fields: dict[str, Any] = {
        "mission_slug": mission_slug,
        "mission_number": mission_number,
        "actor": actor,
        "at": at or _now_iso(),
    }
    # Completed-only fields. Passing these on Started variants is
    # rejected by ``extra="forbid"`` on the typed model — the dormant
    # mask is now closed.
    if event_type.endswith("Completed"):
        if artifact_path is not None:
            fields["artifact_path"] = artifact_path
        if summary is not None:
            fields["summary"] = summary
        if event_type == TASKS_COMPLETED and wp_count is not None:
            fields["wp_count"] = wp_count

    payload: dict[str, Any] = payload_model_cls(**fields).model_dump(
        mode="json", exclude_none=False
    )
    if event_type.endswith("Started") and artifact_path is not None:
        payload["artifact_path"] = artifact_path

    dedup: dict[str, Any] = {"mission_slug": mission_slug}
    if artifact_path is not None:
        dedup["artifact_path"] = artifact_path

    log_path = mission_event_log_path(feature_dir)
    return append_lifecycle_event(
        log_path,
        event_type,
        payload,
        aggregate_id=mission_slug,
        aggregate_type="Mission",
        project_uuid=project_uuid,
        project_slug=project_slug,
        dedup_keys=dedup,
    )


def emit_wp_created_local(
    feature_dir: Path,
    *,
    mission_slug: str,
    wp_id: str,
    wp_title: str,
    wp_path: str | None = None,
    depends_on: Iterable[str] | None = None,
    actor: str = "cli",
    mission_number: int | None = None,
    created_at: str | None = None,
    project_uuid: str | None = None,
    project_slug: str | None = None,
) -> dict[str, Any] | None:
    """Record a local ``WPCreated`` event keyed by ``(mission_slug, wp_id)``.

    Payload is constructed via the canonical
    :class:`spec_kitty_events.project_lifecycle.WPCreatedPayload` so
    schema drift is rejected at the producer boundary
    (issues Priivacy-ai/spec-kitty#1198 / #1200).
    """
    from spec_kitty_events.project_lifecycle import WPCreatedPayload

    payload_model = WPCreatedPayload(
        mission_slug=mission_slug,
        mission_number=mission_number,
        wp_id=wp_id,
        wp_title=wp_title,
        wp_path=wp_path,
        depends_on=list(depends_on or []),
        actor=actor,
        created_at=created_at or _now_iso(),
    )
    payload: dict[str, Any] = payload_model.model_dump(
        mode="json", exclude_none=False
    )

    log_path = mission_event_log_path(feature_dir)
    return append_lifecycle_event(
        log_path,
        WP_CREATED,
        payload,
        aggregate_id=wp_id,
        aggregate_type="WorkPackage",
        project_uuid=project_uuid,
        project_slug=project_slug,
        dedup_keys={"mission_slug": mission_slug, "wp_id": wp_id},
    )


def emit_reviewer_self_approval(
    feature_dir: Path,
    *,
    mission_slug: str,
    wp_id: str,
    implementing_actor: str,
    intended_reviewer: str,
    failure_reason: str,
    fallback_approved: bool = True,
    project_uuid: str | None = None,
    project_slug: str | None = None,
    at: str | None = None,
) -> dict[str, Any] | None:
    """Record that a WP was approved by its implementing actor after reviewer failure."""
    payload = {
        "mission_slug": mission_slug,
        "wp_id": wp_id,
        "implementing_actor": implementing_actor,
        "intended_reviewer": intended_reviewer,
        "failure_reason": failure_reason,
        "fallback_approved": fallback_approved,
        "timestamp": at or _now_iso(),
    }
    log_path = mission_event_log_path(feature_dir)
    return append_lifecycle_event(
        log_path,
        REVIEWER_SELF_APPROVAL,
        payload,
        aggregate_id=wp_id,
        aggregate_type="WorkPackage",
        project_uuid=project_uuid,
        project_slug=project_slug,
        dedup_keys={
            "mission_slug": mission_slug,
            "wp_id": wp_id,
            "implementing_actor": implementing_actor,
            "intended_reviewer": intended_reviewer,
            "failure_reason": failure_reason,
        },
    )


# ---------------------------------------------------------------------------
# Diagnostics / merge guard helpers
# ---------------------------------------------------------------------------


def read_lifecycle_events(log_path: Path) -> list[dict[str, Any]]:
    """Public read-only accessor for the lifecycle log (skips malformed lines)."""
    return _read_lifecycle_lines(log_path)


def _iter_status_event_objects(text: str) -> Iterable[dict[str, Any]]:
    """Yield reducer-style status events from raw mission log text."""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "event_type" not in obj:
            yield obj


def _is_bootstrap_status_event(obj: Mapping[str, Any]) -> bool:
    """Return True when the reducer event is the forced bootstrap planned event."""
    return bool(obj.get("force")) and obj.get("to_lane") == "planned" and obj.get("from_lane") in (None, "planned")


def has_non_bootstrap_status_history(feature_dir: Path) -> bool:
    """Return True when the mission status log contains a non-bootstrap event.

    Bootstrap-only history is the pathological state described in
    issue #1069: the canonical event log contains only forced
    ``planned -> planned`` events emitted by ``finalize-tasks`` even
    though work packages have advanced past planned on the local
    filesystem. This helper reads ``status.events.jsonl`` directly
    (without invoking the status reducer) so it can be used as a
    cheap pre-merge guard.
    """
    log_path = mission_event_log_path(feature_dir)
    if not log_path.exists():
        return False
    try:
        text = log_path.read_text(encoding="utf-8")
    except OSError:
        return False
    for obj in _iter_status_event_objects(text):
        to_lane = obj.get("to_lane")
        if to_lane != "planned":
            return True
        if _is_bootstrap_status_event(obj):
            # Bootstrap planned event — skip.
            continue
        # Non-bootstrap planned event (e.g. legitimate planned -> planned
        # repair with a non-None from_lane mismatch is unreachable but
        # treat any other planned event defensively as real history).
        return True
    return False


__all__ = [
    "PROJECT_INITIALIZED",
    "MISSION_CREATED",
    "SPECIFY_STARTED",
    "SPECIFY_COMPLETED",
    "PLAN_STARTED",
    "PLAN_COMPLETED",
    "TASKS_STARTED",
    "TASKS_COMPLETED",
    "WP_CREATED",
    "REVIEWER_SELF_APPROVAL",
    "LIFECYCLE_EVENT_TYPES",
    "PROJECT_EVENTS_FILENAME",
    "MISSION_EVENTS_FILENAME",
    "project_event_log_path",
    "mission_event_log_path",
    "append_lifecycle_event",
    "has_lifecycle_event",
    "emit_project_initialized",
    "emit_mission_created_local",
    "emit_artifact_phase",
    "emit_wp_created_local",
    "emit_reviewer_self_approval",
    "read_lifecycle_events",
    "has_non_bootstrap_status_history",
]
