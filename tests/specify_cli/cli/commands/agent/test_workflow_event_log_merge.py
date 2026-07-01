"""Regression: coordination commits must not clobber the canonical event log (#1602).

The coordination workflow commit (``_commit_via_coordination_transaction``) used to
write the *main-checkout* copy of ``status.events.jsonl`` straight over the
coordination branch's copy. On lane-based missions the lane transitions live ONLY
on the coordination branch, while the main-checkout copy carries finalize/lifecycle
envelope events (``event_type``/``schema_version`` records the reducer skips) and
the bootstrap. Overwriting wiped the lane history — ``read_events()`` then returned
0 and the implement/review loop wedged with "no canonical status".

``_merge_event_log_bytes`` enforces the append-only invariant: every event already
on the coordination branch survives; only genuinely-new incoming events are added.
"""

from __future__ import annotations

import json

import pytest

from specify_cli.cli.commands.agent.workflow import _merge_event_log_bytes

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _lane_event(event_id: str, at: str, from_lane: str, to_lane: str) -> str:
    return json.dumps(
        {
            "actor": "claude",
            "at": at,
            "event_id": event_id,
            "execution_mode": "worktree",
            "force": False,
            "from_lane": from_lane,
            "mission_slug": "demo",
            "reason": None,
            "review_ref": None,
            "to_lane": to_lane,
            "wp_id": "WP01",
        },
        sort_keys=True,
    )


def _envelope_event(event_id: str, event_type: str) -> str:
    # Lifecycle/SaaS envelope shape: top-level event_type, no from/to_lane, no
    # top-level ``at`` (which the strict canonical merge would reject).
    return json.dumps(
        {
            "aggregate_id": "demo",
            "aggregate_type": "Mission",
            "event_id": event_id,
            "event_type": event_type,
            "schema_version": "5.0.0",
            "timestamp": "2026-06-01T00:00:00+00:00",
        },
        sort_keys=True,
    )


def _ids(blob: bytes) -> list[str]:
    out: list[str] = []
    for line in blob.decode().splitlines():
        if line.strip():
            out.append(json.loads(line)["event_id"])
    return out


def test_merge_preserves_coord_lane_history_against_clobbering_copy() -> None:
    # Coordination branch: the authoritative lane history (planned -> claimed ->
    # in_progress for WP01).
    coord = (
        _lane_event("01EVT0000000000000000PLAN", "2026-06-01T01:00:00+00:00", "planned", "planned")
        + "\n"
        + _lane_event("01EVT0000000000000CLAIM", "2026-06-01T02:00:00+00:00", "planned", "claimed")
        + "\n"
        + _lane_event("01EVT00000000000PROGRESS", "2026-06-01T03:00:00+00:00", "claimed", "in_progress")
        + "\n"
    ).encode()

    # Main-checkout copy that previously clobbered coord: only the bootstrap lane
    # event (shared id) + an envelope event — NONE of the claimed/in_progress
    # transitions.
    incoming = (
        _lane_event("01EVT0000000000000000PLAN", "2026-06-01T01:00:00+00:00", "planned", "planned")
        + "\n"
        + _envelope_event("01ENV0000000000000000001", "TasksStarted")
        + "\n"
    ).encode()

    merged = _merge_event_log_bytes(coord, incoming)
    merged_ids = _ids(merged)

    # Every coord event survives — the claimed/in_progress transitions are NOT lost.
    assert "01EVT0000000000000CLAIM" in merged_ids
    assert "01EVT00000000000PROGRESS" in merged_ids
    # The shared bootstrap event is not duplicated.
    assert merged_ids.count("01EVT0000000000000000PLAN") == 1
    # The genuinely-new envelope event is carried, appended after coord history.
    assert "01ENV0000000000000000001" in merged_ids
    assert merged_ids.index("01ENV0000000000000000001") > merged_ids.index(
        "01EVT00000000000PROGRESS"
    )
    # Coord history keeps its order (the reducer processes in file order).
    assert merged_ids[:3] == [
        "01EVT0000000000000000PLAN",
        "01EVT0000000000000CLAIM",
        "01EVT00000000000PROGRESS",
    ]


def test_merge_is_noop_when_incoming_is_subset() -> None:
    coord = (
        _lane_event("01EVT0000000000000000PLAN", "2026-06-01T01:00:00+00:00", "planned", "planned")
        + "\n"
        + _lane_event("01EVT0000000000000CLAIM", "2026-06-01T02:00:00+00:00", "planned", "claimed")
        + "\n"
    ).encode()
    # Incoming carries nothing coord lacks.
    incoming = (
        _lane_event("01EVT0000000000000000PLAN", "2026-06-01T01:00:00+00:00", "planned", "planned")
        + "\n"
    ).encode()

    merged = _merge_event_log_bytes(coord, incoming)

    assert merged == coord  # byte-identical: no clobber, no spurious growth


def test_merge_carries_new_transition_from_incoming() -> None:
    # The just-emitted transition can legitimately live only in the incoming copy;
    # it must be appended (chronologically newest), not dropped.
    coord = (
        _lane_event("01EVT0000000000000CLAIM", "2026-06-01T02:00:00+00:00", "planned", "claimed")
        + "\n"
    ).encode()
    incoming = (
        _lane_event("01EVT0000000000000CLAIM", "2026-06-01T02:00:00+00:00", "planned", "claimed")
        + "\n"
        + _lane_event("01EVT00000000000PROGRESS", "2026-06-01T03:00:00+00:00", "claimed", "in_progress")
        + "\n"
    ).encode()

    merged_ids = _ids(_merge_event_log_bytes(coord, incoming))

    assert merged_ids == ["01EVT0000000000000CLAIM", "01EVT00000000000PROGRESS"]
