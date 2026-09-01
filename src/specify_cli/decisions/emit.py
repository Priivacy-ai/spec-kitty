"""Decision Point event emission helpers.

Appends ``DecisionPointOpened(interview)`` and ``DecisionPointResolved(interview)``
events to ``kitty-specs/<mission_slug>/status.events.jsonl`` using the
public ``spec_kitty_events.decisionpoint`` payload models (4.0.0 contract).

Event envelope format (one JSON line, sorted keys):
    event_id, at, event_type, payload

The payload is validated by the Pydantic model before serialization.

After the local JSONL append succeeds, both events are also offered on the
same best-effort ``event.publish`` fan-out path already used by
``WPStatusChanged``/``MissionCreated`` (``status.fire_lifecycle_saas_fanout``
→ ``specify_cli.status.zeitgeist_bridge``). Fan-out is fire-and-forget: a
relay outage, missing credential, or codec rejection is logged and dropped,
never raised, and can never roll back or affect the local write that already
happened above it.

Defaults applied when the IndexEntry doesn't supply a value:
    - ``phase``:        ``entry.origin_flow.value.upper()``   (e.g. "CHARTER")
    - ``run_id``:       ``decision_id``                       (no run context in V1)
    - ``actor_type``:   ``"human"``
    - ``mission_type``: ``"software-dev"``
    - ``step_id`` (wire): ``entry.step_id`` if set, else ``entry.slot_key``
      (wire field name is always ``step_id`` for 4.0.0 compat)

Public API:
    emit_decision_opened(repo_root, mission_slug, *, decision_id, entry, actor) -> int
    emit_decision_resolved(repo_root, mission_slug, *, decision_id, entry, actor) -> int
"""

from __future__ import annotations

from mission_runtime import MissionArtifactKind, placement_seam
import json
import logging
from pathlib import Path
from typing import Literal

import ulid as _ulid_mod

from kernel.clock import now_utc
from specify_cli.decisions.models import IndexEntry
from specify_cli.events import sanitize_event_for_log
from spec_kitty_events.decisionpoint import (
    DECISION_POINT_OPENED,
    DECISION_POINT_RESOLVED,
    DECISIONPOINT_SCHEMA_VERSION,
    DecisionPointOpenedInterviewPayload,
    DecisionPointResolvedInterviewPayload,
)
from spec_kitty_events.decision_moment import (
    OriginFlow as _EventOriginFlow,
    OriginSurface,
    TerminalOutcome,
)

__all__ = [
    "emit_decision_opened",
    "emit_decision_resolved",
]

logger = logging.getLogger(__name__)

_EVENTS_FILENAME = "status.events.jsonl"
_MISSION_TYPE = "software-dev"  # default; V1 always software-dev
_ACTOR_TYPE: Literal["human", "llm", "service"] = "human"  # default; override for automated actors


def _generate_ulid() -> str:
    """Generate a new ULID string."""
    return str(_ulid_mod.ULID())


def _mission_dir(repo_root: Path, mission_slug: str) -> Path:
    """Return ``kitty-specs/<mission_slug>/`` via the kind-aware placement seam.

    write-side-seam-matrix-tracer-01KYP3MH WP02 (FR-010, #3055) Move A: routed
    through ``placement_seam(...).read_dir(STATUS_STATE)`` instead of the
    kind-blind ``resolve_feature_dir_for_mission`` — this drops
    ``decisions/emit.py`` off the coord-authority gate's allow-list (it no
    longer calls the kind-blind resolver at all). ``status.events.jsonl`` is
    the ``STATUS_STATE`` kind (``mission_runtime.artifacts``), matching
    ``decisions/service.py``'s existing read of the SAME directory — reads and
    writes agree on where the coord-owned decision/status log lives under
    every topology, closing a prior read/write split-brain risk.
    """
    mission_dir: Path = placement_seam(repo_root, mission_slug).read_dir(
        MissionArtifactKind.STATUS_STATE
    )
    return mission_dir


def _events_path(repo_root: Path, mission_slug: str) -> Path:
    """Return the path to ``status.events.jsonl``."""
    return _mission_dir(repo_root, mission_slug) / _EVENTS_FILENAME


def _append_raw_event(events_path: Path, event_dict: dict) -> int:  # type: ignore[type-arg]
    """Append *event_dict* as a JSON line to the events file.

    Creates parent directories if needed.
    PII fields are stripped via :func:`sanitize_event_for_log` before serialization.
    Returns the 1-based line count after the append (lamport proxy).
    """
    events_path.parent.mkdir(parents=True, exist_ok=True)
    sanitized = sanitize_event_for_log(event_dict)
    line = json.dumps(sanitized, sort_keys=True)
    with events_path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    # Count non-empty lines (proxy for Lamport clock value)
    with events_path.open("r", encoding="utf-8") as fh:
        return sum(1 for ln in fh if ln.strip())


def _queue_decision_fanout(
    events_path: Path,
    event_dict: dict,  # type: ignore[type-arg]
    *,
    mission_slug: str,
) -> None:
    """Best-effort ``event.publish`` fan-out for an already-persisted decision event.

    Mirrors ``lifecycle_events.py``'s ``_queue_lifecycle_event_if_enabled``: this
    is called only AFTER :func:`_append_raw_event` has returned, so a relay
    outage or codec rejection can never affect the canonical local write.
    ``fire_lifecycle_saas_fanout`` and every handler behind it already catch
    and log their own failures; the ``except`` here is one more belt against
    a defect in that chain reaching this seam, matching every other slot
    wrapper in ``zeitgeist_bridge.py`` (e.g. ``lifecycle_moment_handler``) --
    never let fan-out raise into a decision-emission caller.
    """
    from specify_cli.status import fire_lifecycle_saas_fanout

    envelope = {
        "event_id": event_dict["event_id"],
        "event_type": event_dict["event_type"],
        "aggregate_id": mission_slug,
        "schema_version": DECISIONPOINT_SCHEMA_VERSION,
        "timestamp": event_dict["at"],
        "payload": event_dict["payload"],
    }
    try:
        fire_lifecycle_saas_fanout(envelope=envelope, log_path=events_path)
    except Exception:
        logger.warning(
            "Zeitgeist fan-out failed for %s; canonical decision log unaffected",
            event_dict["event_type"],
            exc_info=True,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def emit_decision_opened(
    repo_root: Path,
    mission_slug: str,
    *,
    decision_id: str,
    entry: IndexEntry,
    actor: str,
) -> int:
    """Append a ``DecisionPointOpened`` (interview) event to status.events.jsonl.

    Args:
        repo_root:     Repository root (parent of ``kitty-specs/``).
        mission_slug:  The mission slug.
        decision_id:   The ULID decision_id (used as decision_point_id on the wire).
        entry:         The IndexEntry for the newly-opened decision.
        actor:         The actor performing the open (actor_id on the wire).

    Returns:
        Lamport proxy: 1-based line count of the appended event.

    Defaults:
        - phase      → ``entry.origin_flow.value.upper()``
        - run_id     → ``decision_id``
        - actor_type → ``"human"``
        - mission_type → ``"software-dev"``
        - step_id (wire) → ``entry.step_id or entry.slot_key``
    """
    now = now_utc()
    wire_step_id = entry.step_id if entry.step_id is not None else (entry.slot_key or "")

    payload = DecisionPointOpenedInterviewPayload(
        origin_surface=OriginSurface.PLANNING_INTERVIEW,
        decision_point_id=decision_id,
        mission_id=entry.mission_id,
        run_id=decision_id,  # default: use decision_id as run_id in V1
        mission_slug=entry.mission_slug,
        mission_type=_MISSION_TYPE,
        phase=entry.origin_flow.value.upper(),  # default: flow name uppercased
        origin_flow=_EventOriginFlow(entry.origin_flow.value),
        question=entry.question,
        options=tuple(entry.options),
        input_key=entry.input_key,
        step_id=wire_step_id,
        actor_id=actor,
        actor_type=_ACTOR_TYPE,
        state_entered_at=entry.created_at,
        recorded_at=now,
    )

    # canonical-producer-exempt: #1198 -- canonical local-only decisions JSONL envelope.
    event_dict = {
        "event_id": _generate_ulid(),
        "at": now.isoformat(),
        "event_type": DECISION_POINT_OPENED,
        "payload": json.loads(payload.model_dump_json()),
    }
    events_path = _events_path(repo_root, mission_slug)
    line_count = _append_raw_event(events_path, event_dict)
    _queue_decision_fanout(events_path, event_dict, mission_slug=mission_slug)
    return line_count


def emit_decision_resolved(
    repo_root: Path,
    mission_slug: str,
    *,
    decision_id: str,
    entry: IndexEntry,
    actor: str,
) -> int:
    """Append a ``DecisionPointResolved`` (interview) event to status.events.jsonl.

    The ``terminal_outcome`` is derived from ``entry.status``:
        - ``DecisionStatus.RESOLVED`` → ``TerminalOutcome.RESOLVED``
        - ``DecisionStatus.DEFERRED`` → ``TerminalOutcome.DEFERRED``
        - ``DecisionStatus.CANCELED`` → ``TerminalOutcome.CANCELED``

    Args:
        repo_root:    Repository root (parent of ``kitty-specs/``).
        mission_slug: The mission slug.
        decision_id:  The ULID decision_id (decision_point_id on wire).
        entry:        The IndexEntry AFTER the terminal state was applied.
        actor:        The actor performing the resolution.

    Returns:
        Lamport proxy: 1-based line count of the appended event.

    Defaults:
        - run_id       → ``decision_id``
        - mission_type → ``"software-dev"``
        - summary      → ``None``  (SaaS concern; slot reserved in V1)
        - actual_participants → ``()``
        - closed_locally_while_widened → ``False``
        - closure_message → ``None``
    """
    now = now_utc()
    outcome = TerminalOutcome(entry.status.value)
    resolved_by = entry.resolved_by or actor

    if outcome == TerminalOutcome.RESOLVED:
        payload = DecisionPointResolvedInterviewPayload(
            origin_surface=OriginSurface.PLANNING_INTERVIEW,
            decision_point_id=decision_id,
            mission_id=entry.mission_id,
            run_id=decision_id,  # default: use decision_id as run_id in V1
            mission_slug=entry.mission_slug,
            mission_type=_MISSION_TYPE,
            terminal_outcome=outcome,
            final_answer=entry.final_answer or "",
            other_answer=entry.other_answer,
            rationale=entry.rationale,
            resolved_by=resolved_by,
            state_entered_at=entry.resolved_at or now,
            recorded_at=now,
        )
    else:
        # deferred or canceled: final_answer must be absent, rationale required
        payload = DecisionPointResolvedInterviewPayload(
            origin_surface=OriginSurface.PLANNING_INTERVIEW,
            decision_point_id=decision_id,
            mission_id=entry.mission_id,
            run_id=decision_id,
            mission_slug=entry.mission_slug,
            mission_type=_MISSION_TYPE,
            terminal_outcome=outcome,
            rationale=entry.rationale or "no rationale",
            resolved_by=resolved_by,
            state_entered_at=entry.resolved_at or now,
            recorded_at=now,
        )

    # canonical-producer-exempt: #1198 -- canonical local-only decisions JSONL envelope.
    event_dict = {
        "event_id": _generate_ulid(),
        "at": now.isoformat(),
        "event_type": DECISION_POINT_RESOLVED,
        "payload": json.loads(payload.model_dump_json()),
    }
    events_path = _events_path(repo_root, mission_slug)
    line_count = _append_raw_event(events_path, event_dict)
    _queue_decision_fanout(events_path, event_dict, mission_slug=mission_slug)
    return line_count
