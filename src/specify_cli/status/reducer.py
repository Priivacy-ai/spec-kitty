"""Deterministic reducer for status event logs.

Replays a list of StatusEvent records into a StatusSnapshot, applying
deduplication, deterministic sorting, and rollback-aware conflict
resolution for concurrent events from parallel worktrees.

WP03 (additive): Also computes a RetrospectiveSnapshot from retrospective.*
events in the raw event log and attaches it to the StatusSnapshot under the
``retrospective`` field. Existing consumers see no change (default None).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from specify_cli.core.paths import safe_mission_slug
from specify_cli.mission_metadata import resolve_mission_identity

from .models import (
    NON_DISPLAY_LANES,
    InnerStateChanged,
    Lane,
    RetrospectiveSnapshot,
    StatusEvent,
    StatusSnapshot,
    WPInnerStateDelta,
)
from .store import read_event_stream, read_events_raw

#: Per-WP runtime slots carried forward across lane transitions (per-field
#: independence, FR-002). A transition updates ``lane``/``actor``/… and MUST
#: preserve these — the pre-mission reducer rebuilt the dict carrying forward
#: only ``force_count``, which would erase runtime state on the next
#: transition (the reducer replace-dict hazard).
_RUNTIME_SLOTS: tuple[str, ...] = (
    "shell_pid",
    "shell_pid_created_at",
    "subtasks",
    "notes",
    "tracker_refs",
    "agent",
    "assignee",
    "review",
)

SNAPSHOT_FILENAME = "status.json"


def _is_rollback_event(event: StatusEvent) -> bool:
    """Check if an event represents a reviewer rollback.

    Current review rejection rolls back from in_review to in_progress.
    Legacy logs represented the same outcome as for_review to in_progress
    with a review reference.
    """
    if event.to_lane != Lane.IN_PROGRESS:
        return False
    if event.from_lane == Lane.IN_REVIEW:
        return True
    return event.from_lane == Lane.FOR_REVIEW and event.review_ref is not None


def _wp_state_from_event(
    event: StatusEvent,
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build a WP state dict from a lane transition.

    Carries forward ``force_count`` **and** every untouched runtime slot from
    ``previous`` (per-field independence, FR-002) so a later transition never
    silently erases ``shell_pid``/``subtasks``/``notes``/``tracker_refs``/…
    (the reducer replace-dict hazard).

    The ``planned -> claimed`` transition is the only transition that writes a
    runtime slot: it extracts ``shell_pid``/``shell_pid_created_at``/``agent``
    from its ``policy_metadata`` sidecar into the snapshot slots (FR-004 claim
    path). ``policy_metadata`` may be ``None`` — read defensively.
    """
    prior_force_count = 0
    if previous is not None:
        prior_force_count = previous.get("force_count", 0)

    state: dict[str, Any] = {
        "lane": str(event.to_lane),
        "actor": event.actor,
        "last_transition_at": event.at,
        "last_event_id": event.event_id,
        "force_count": prior_force_count + (1 if event.force else 0),
    }

    # Preserve untouched runtime slots across the transition.
    if previous is not None:
        for slot in _RUNTIME_SLOTS:
            if slot in previous:
                state[slot] = previous[slot]

    # Claim exception (FR-004): the only transition that writes a runtime slot.
    if event.from_lane == Lane.PLANNED and event.to_lane == Lane.CLAIMED:
        meta = event.policy_metadata or {}
        shell_pid = meta.get("shell_pid")
        if shell_pid is not None:
            state["shell_pid"] = shell_pid
        shell_pid_created_at = meta.get("shell_pid_created_at")
        if shell_pid_created_at is not None:
            state["shell_pid_created_at"] = shell_pid_created_at
        agent = meta.get("agent")
        if agent is not None:
            state["agent"] = agent

    return state


def _apply_annotation_delta(state: dict[str, Any], delta: WPInnerStateDelta) -> None:
    """Fold a typed :class:`WPInnerStateDelta` into a per-WP snapshot dict.

    Per-field merge rules (only present delta fields are applied; absent fields
    leave the slot untouched):

    - ``shell_pid`` / ``shell_pid_created_at`` / ``agent`` / ``assignee`` /
      ``review``: **replace**.
    - ``subtasks``: **per-subtask replace** (merge by subtask id).
    - ``note``: **append** to the ``notes`` list.
    - ``tracker_refs`` (additive) **unions** into the ``tracker_refs`` slot;
      ``tracker_refs_replace`` (present) **wholesale-replaces** the slot
      (dedup-preserving order) and takes precedence when both are present — the
      replace channel is what lets a ``--replace`` drop stale refs rather than
      resurrect them.

    Never increments ``force_count``.
    """
    if delta.shell_pid is not None:
        state["shell_pid"] = delta.shell_pid
    if delta.shell_pid_created_at is not None:
        state["shell_pid_created_at"] = delta.shell_pid_created_at
    if delta.subtasks is not None:
        current_subtasks: dict[str, str] = dict(state.get("subtasks") or {})
        for subtask_id, status in delta.subtasks.items():
            current_subtasks[subtask_id] = str(status)
        state["subtasks"] = current_subtasks
    if delta.note is not None:
        notes: list[str] = list(state.get("notes") or [])
        notes.append(delta.note)
        state["notes"] = notes
    if delta.tracker_refs_replace is not None:
        state["tracker_refs"] = _dedup_preserve_order(delta.tracker_refs_replace)
    elif delta.tracker_refs is not None:
        merged: list[str] = list(state.get("tracker_refs") or [])
        for ref in delta.tracker_refs:
            if ref not in merged:
                merged.append(ref)
        state["tracker_refs"] = merged
    if delta.agent is not None:
        state["agent"] = delta.agent
    if delta.assignee is not None:
        state["assignee"] = delta.assignee
    if delta.review is not None:
        state["review"] = delta.review.to_dict()


def _dedup_preserve_order(refs: list[str]) -> list[str]:
    """Return ``refs`` with duplicates removed, preserving first-seen order."""
    seen: set[str] = set()
    result: list[str] = []
    for ref in refs:
        if ref not in seen:
            seen.add(ref)
            result.append(ref)
    return result


def _should_apply_event(
    current_state: dict[str, Any] | None,
    new_event: StatusEvent,
    all_events: list[StatusEvent],
) -> bool:
    """Determine whether new_event should be applied given the current state.

    Implements rollback-aware precedence: if the current state was set by
    a forward transition and a concurrent rollback event exists for the
    same WP, the rollback wins.

    If there is no current state, the event always applies.
    If events are not concurrent (different timestamps), the later one
    wins naturally through sort order.
    """
    if current_state is None:
        return True

    current_event_id = current_state.get("last_event_id")
    current_timestamp = current_state.get("last_transition_at")

    # If this event has the same timestamp as the current state's event,
    # they are concurrent. Check rollback precedence.
    if current_timestamp == new_event.at:
        # If the new event is a rollback, it beats a forward transition
        if _is_rollback_event(new_event):
            # Check if the current state was set by a non-rollback event
            current_setter = None
            for ev in all_events:
                if ev.event_id == current_event_id:
                    current_setter = ev
                    break
            if current_setter is not None and not _is_rollback_event(current_setter):
                return True  # Rollback beats forward

        # If the current state was set by a rollback, don't let a
        # concurrent forward event override it
        if current_event_id is not None:
            current_setter = None
            for ev in all_events:
                if ev.event_id == current_event_id:
                    current_setter = ev
                    break
            if current_setter is not None and _is_rollback_event(current_setter) and not _is_rollback_event(new_event):
                return False  # Forward does not beat rollback

    # Default: apply the event (later in sort order wins)
    return True


def reduce(
    events: list[StatusEvent],
    annotations: list[InnerStateChanged] | None = None,
) -> StatusSnapshot:
    """Deterministically reduce events (+ annotations) into a snapshot.

    Event-kind partition fold (NOT a timestamp-interleaved single pass):

    1. Deduplicate transitions by event_id (keep first occurrence)
    2. Sort transitions by (at, event_id) ascending
    3. Fold all transitions with rollback-aware precedence, preserving each
       WP's untouched runtime slots (and folding the ``planned -> claimed``
       ``policy_metadata`` sidecar into the snapshot slots)
    4. Fold **all annotations** in a dedicated post-transition pass, applying
       the per-field ``WPInnerStateDelta`` merge. A same-``at`` transition can
       never clobber an annotation slot; annotations never bump ``force_count``.
       This pass is a single O(annotations) walk keyed by ``wp_id`` — it does
       NOT re-scan the transition list (NFR-005).
    5. Build summary counts for the 9 active/display lanes
       (lanes in ``NON_DISPLAY_LANES`` — currently ``GENESIS`` and
       ``UNINITIALIZED`` — are excluded; neither ever appears as the
       current lane of a materialised WP)

    ``annotations`` defaults to ``None`` (treated as empty) so every existing
    ``reduce(read_events(...))`` caller keeps its behaviour. An
    annotation-only stream materialises a runtime-only WP entry.

    An empty stream (no transitions and no annotations) returns a snapshot with
    mission_slug="", all zero counts, and no work packages.
    """
    annotations = annotations or []
    if not events and not annotations:
        return StatusSnapshot(
            mission_slug="",
            materialized_at="",  # No events → no last-event timestamp; stable empty string
            event_count=0,
            last_event_id=None,
            work_packages={},
            summary={lane.value: 0 for lane in Lane if lane not in NON_DISPLAY_LANES},
        )

    # Step 1: Deduplicate by event_id (keep first occurrence)
    seen_ids: set[str] = set()
    unique_events: list[StatusEvent] = []
    for event in events:
        if event.event_id not in seen_ids:
            seen_ids.add(event.event_id)
            unique_events.append(event)

    # Step 2: Sort by (at, event_id) ascending
    sorted_events = sorted(unique_events, key=lambda e: (e.at, e.event_id))

    # Step 3 & 4: Iterate and apply events with rollback-aware precedence
    wp_states: dict[str, dict[str, Any]] = {}
    # The event's mission_slug is UNTRUSTED (verbatim from a status.events.jsonl
    # row). Sanitize it HERE — the single seam where the snapshot's slug is set —
    # so a crafted traversal slug (e.g. "../../../../tmp/evil") is downgraded to
    # "" at the source. Every derived-view writer already falls back to the
    # trusted feature_dir.name when the slug is empty (`slug or feature_dir.name`),
    # so this one chokepoint fail-closes all current and future path sinks.
    # An annotation-only stream has no transition to source the slug from.
    mission_slug = safe_mission_slug(sorted_events[0].mission_slug, "") if sorted_events else ""

    for event in sorted_events:
        current = wp_states.get(event.wp_id)
        if _should_apply_event(current, event, sorted_events):
            wp_states[event.wp_id] = _wp_state_from_event(event, current)

    # Step 4: Annotation post-pass (event-kind partition — folded AFTER every
    # transition, never interleaved by timestamp). A single O(annotations) walk
    # keyed by wp_id; it does NOT re-scan the transition list. An annotation for
    # a wp_id with no prior transition materialises a runtime-only WP entry.
    for annotation in annotations:
        wp_state = wp_states.get(annotation.wp_id)
        if wp_state is None:
            wp_state = _runtime_only_wp_state(annotation.actor)
            wp_states[annotation.wp_id] = wp_state
        _apply_annotation_delta(wp_state, annotation.delta)

    # Step 5: Build summary counts for the 9 active/display lanes.
    # Lanes in NON_DISPLAY_LANES (GENESIS, UNINITIALIZED) are excluded —
    # neither is ever the current lane of a materialised WP (post-finalize
    # there are none).
    summary: dict[str, int] = {lane.value: 0 for lane in Lane if lane not in NON_DISPLAY_LANES}
    for wp_state in wp_states.values():
        lane_val = wp_state["lane"]
        if lane_val in summary:
            summary[lane_val] += 1

    # ``materialized_at``/``last_event_id`` derive from the last transition
    # (deterministic). Annotations are off-axis and do not move these markers.
    last_transition = sorted_events[-1] if sorted_events else None
    return StatusSnapshot(
        mission_slug=mission_slug,
        materialized_at=last_transition.at if last_transition is not None else "",
        event_count=len(sorted_events),
        last_event_id=last_transition.event_id if last_transition is not None else None,
        work_packages=wp_states,
        summary=summary,
    )


def _runtime_only_wp_state(actor: str) -> dict[str, Any]:
    """Seed a per-WP snapshot entry for an annotation with no prior transition.

    Such a WP never traversed the FSM, so it has no display lane — it sits in
    the non-display ``UNINITIALIZED`` lane and is therefore excluded from the
    board summary. The annotation delta then folds its runtime slots on top.
    """
    return {
        "lane": str(Lane.UNINITIALIZED),
        "actor": actor,
        "last_transition_at": None,
        "last_event_id": None,
        "force_count": 0,
    }


def _reduce_retrospective(raw_events: list[dict[str, Any]]) -> RetrospectiveSnapshot:
    """Compute a RetrospectiveSnapshot from raw event-log entries.

    Scans the raw event list for retrospective.* events (identified by the
    ``event_name`` key) and computes the current snapshot state.

    Logic:
    - absent: no retrospective.* events at all.
    - pending: retrospective.requested or .started seen, but no terminal event.
    - Terminal status (completed/skipped/failed): determined by the latest
      terminal event, sorted by (at, event_id) descending.
    - Proposal counts aggregated from proposal.generated/applied/rejected events.
    - mode: from the most recent retrospective.requested payload.
    - record_path: from the most recent terminal event payload, if present.
    """
    retro_events = [e for e in raw_events if "event_name" in e and str(e.get("event_name", "")).startswith("retrospective.")]

    if not retro_events:
        return RetrospectiveSnapshot(status="absent")

    # Sort all retro events by (at, event_id) ascending
    def _sort_key(e: dict[str, Any]) -> tuple[str, str]:
        return (str(e.get("at", "")), str(e.get("event_id", "")))

    retro_events_sorted = sorted(retro_events, key=_sort_key)

    # Determine terminal status from latest completed/skipped/failed event
    terminal_names = {"retrospective.completed", "retrospective.skipped", "retrospective.failed"}
    terminal_events = [e for e in retro_events_sorted if e.get("event_name") in terminal_names]

    # Determine mode from most recent requested event
    requested_events = [e for e in retro_events_sorted if e.get("event_name") == "retrospective.requested"]
    mode = None
    if requested_events:
        latest_requested = requested_events[-1]
        payload = latest_requested.get("payload") or {}
        mode_data = payload.get("mode")
        if mode_data is not None:
            try:
                from specify_cli.retrospective.schema import Mode
                mode = Mode.model_validate(mode_data)
            except Exception:
                mode = None

    # Determine status
    retro_status: Literal["completed", "skipped", "failed", "pending"]
    if terminal_events:
        latest_terminal = terminal_events[-1]
        terminal_name: str = str(latest_terminal.get("event_name", ""))
        if terminal_name == "retrospective.completed":
            retro_status = "completed"
        elif terminal_name == "retrospective.skipped":
            retro_status = "skipped"
        else:
            retro_status = "failed"

        # Extract record_path from terminal payload
        record_path: str | None = None
        payload = latest_terminal.get("payload") or {}
        rp = payload.get("record_path")
        if rp is not None:
            record_path = str(rp)
    else:
        # Non-terminal retro events present (requested/started)
        retro_status = "pending"
        record_path = None

    # Proposal counts
    proposals_total = sum(
        1 for e in retro_events if e.get("event_name") == "retrospective.proposal.generated"
    )
    proposals_applied = sum(
        1 for e in retro_events if e.get("event_name") == "retrospective.proposal.applied"
    )
    proposals_rejected = sum(
        1 for e in retro_events if e.get("event_name") == "retrospective.proposal.rejected"
    )
    proposals_pending = max(0, proposals_total - proposals_applied - proposals_rejected)

    return RetrospectiveSnapshot(
        status=retro_status,
        mode=mode,
        record_path=record_path,
        proposals_total=proposals_total,
        proposals_applied=proposals_applied,
        proposals_rejected=proposals_rejected,
        proposals_pending=proposals_pending,
    )


def materialize_to_json(snapshot: StatusSnapshot) -> str:
    """Serialize a snapshot to a deterministic JSON string.

    Uses ``sort_keys=True``, ``indent=2``, and ``ensure_ascii=False``
    for human-readable, byte-identical output across platforms.
    Returns the JSON string with a trailing newline.
    """
    return (
        json.dumps(
            snapshot.to_dict(),
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )


def materialize_snapshot(feature_dir: Path) -> StatusSnapshot:
    """Read events and reduce them to the exact snapshot materialize() writes.

    This helper is intentionally read-only. It keeps production materialization
    semantics in one place so callers such as doctor/audit can compare a
    persisted status.json without creating temp files or replacing status.json.

    Reads via ``read_event_stream`` so off-axis ``InnerStateChanged``
    annotations are surfaced to ``reduce()`` and folded into the runtime slots.
    """
    stream = read_event_stream(feature_dir)
    snapshot = reduce(stream.transitions, stream.annotations)
    identity = resolve_mission_identity(feature_dir)
    snapshot.mission_number = (
        str(identity.mission_number)
        if identity.mission_number is not None
        else None
    )
    snapshot.mission_type = identity.mission_type

    # Additive WP03: compute RetrospectiveSnapshot from raw events (includes
    # retrospective.* entries that are not StatusEvent objects).
    raw_events = read_events_raw(feature_dir)
    retro_snapshot = _reduce_retrospective(raw_events)
    # Only attach non-absent snapshots to avoid changing serialized output for
    # missions that have no retrospective events at all.
    if retro_snapshot.status != "absent":
        snapshot.retrospective = retro_snapshot

    return snapshot


def materialize(feature_dir: Path) -> StatusSnapshot:
    """Read events, reduce to snapshot, and write status.json atomically.

    Skips the write when content is byte-identical to the existing file.
    Writes to a temporary file first, then uses ``os.replace`` for an
    atomic rename to avoid partial writes.

    WP03 (additive): Also scans raw events for retrospective.* entries and
    attaches a RetrospectiveSnapshot to the snapshot under ``retrospective``.
    Default is None for missions with no retrospective events (backwards-compat).

    Returns the materialized snapshot.
    """
    snapshot = materialize_snapshot(feature_dir)
    json_str = materialize_to_json(snapshot)

    out_path = feature_dir / SNAPSHOT_FILENAME
    tmp_path = feature_dir / (SNAPSHOT_FILENAME + ".tmp")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Skip write when content unchanged (FR-001, NFR-001)
    if out_path.exists() and out_path.read_text(encoding="utf-8") == json_str:
        return snapshot

    tmp_path.write_text(json_str, encoding="utf-8")
    os.replace(str(tmp_path), str(out_path))

    return snapshot
