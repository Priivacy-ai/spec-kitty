"""Regression tests for FR-010: read_events tolerates non-lane-transition events.

The status event log (`status.events.jsonl`) is shared by two cooperating
subsystems with incompatible schemas:

- The status emitter writes lane-transition events (carrying ``wp_id``,
  ``from_lane``, ``to_lane``).
- The Decision Moment Protocol writes mission-level events
  (``DecisionPointOpened``, ``DecisionPointResolved``,
  ``DecisionPointDeferred``, ``DecisionPointCanceled``,
  ``DecisionPointWidened``) that carry a top-level ``event_type`` field
  instead of ``wp_id``.

`read_events()` discriminates on ``event_type`` PRESENCE (not a specific
value allowlist) so it tolerates current AND future mission-level event
types while still failing loud on malformed lane-transition events that
lack BOTH ``wp_id`` AND ``event_type``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from specify_cli.status.store import StoreError, read_events


def _write_events_jsonl(feature_dir: Path, events: list[dict[str, Any]]) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    events_path = feature_dir / "status.events.jsonl"
    events_path.write_text(
        "\n".join(json.dumps(e, sort_keys=True) for e in events) + "\n",
        encoding="utf-8",
    )


def _make_lane_event(event_id: str, wp_id: str, to_lane: str = "claimed") -> dict[str, Any]:
    return {
        "event_id": event_id,
        "mission_slug": "demo",
        "wp_id": wp_id,
        "from_lane": "planned",
        "to_lane": to_lane,
        "at": "2026-04-27T12:00:00+00:00",
        "actor": "test",
        "force": False,
        "execution_mode": "worktree",
    }


def _make_decision_opened(event_id: str) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "event_type": "DecisionPointOpened",
        "at": "2026-04-27T11:00:00+00:00",
        "payload": {
            "decision_point_id": "01TESTDECISION0000000000",
            "mission_slug": "demo",
            "input_key": "demo_question",
            "question": "demo?",
        },
    }


def _make_decision_resolved(event_id: str) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "event_type": "DecisionPointResolved",
        "at": "2026-04-27T11:30:00+00:00",
        "payload": {
            "decision_point_id": "01TESTDECISION0000000000",
            "mission_slug": "demo",
            "final_answer": "yes",
        },
    }


def test_read_events_skips_decision_point_events_returns_lane_events(
    tmp_path: Path,
) -> None:
    """Mixed event log: skip DecisionPoint events, preserve lane events in order."""
    feature_dir = tmp_path / "feature"

    events: list[dict[str, Any]] = [
        _make_decision_opened("01EVT0001"),
        _make_lane_event("01EVT0002", "WP01"),
        _make_decision_resolved("01EVT0003"),
        _make_lane_event("01EVT0004", "WP02"),
    ]
    _write_events_jsonl(feature_dir, events)

    result = read_events(feature_dir)

    assert len(result) == 2, [e.event_id for e in result]
    assert [e.event_id for e in result] == ["01EVT0002", "01EVT0004"]
    assert [e.wp_id for e in result] == ["WP01", "WP02"]


def test_read_events_with_only_decision_events_returns_empty(
    tmp_path: Path,
) -> None:
    """Decision-only event log returns empty list (no lane transitions to surface)."""
    feature_dir = tmp_path / "feature"
    _write_events_jsonl(
        feature_dir,
        [_make_decision_opened("01EVT0001"), _make_decision_resolved("01EVT0002")],
    )
    assert read_events(feature_dir) == []


def test_read_events_still_raises_on_invalid_json(tmp_path: Path) -> None:
    """Preserve existing fail-loud contract for malformed JSON."""
    feature_dir = tmp_path / "feature"
    feature_dir.mkdir(parents=True)
    (feature_dir / "status.events.jsonl").write_text("{not json", encoding="utf-8")

    with pytest.raises(StoreError, match="Invalid JSON on line 1"):
        read_events(feature_dir)


def test_read_events_still_raises_on_event_missing_wp_id_AND_event_type(
    tmp_path: Path,
) -> None:
    """A corrupted lane-transition event missing wp_id MUST still raise.

    The event_type-presence guard intentionally only skips events whose
    wire format identifies them as non-lane-transition. A lane-transition
    event missing wp_id but ALSO missing event_type is corrupted and must
    surface, not silently disappear. Preserves the contract that malformed
    lane events fail loudly.
    """
    feature_dir = tmp_path / "feature"

    # Has neither wp_id nor event_type — a corrupted lane event.
    corrupted = _make_lane_event("01EVT0006", "WP04")
    del corrupted["wp_id"]
    _write_events_jsonl(feature_dir, [corrupted])

    with pytest.raises(StoreError, match="Invalid event structure on line 1"):
        read_events(feature_dir)


def test_read_events_still_raises_on_malformed_lane_event(tmp_path: Path) -> None:
    """A lane-transition event with a bad from_lane MUST still raise.

    Pins the discriminator choice (event_type PRESENCE, not wp_id ABSENCE).
    A future regression to ``if "wp_id" not in obj: continue`` would silently
    swallow this malformed lane event instead of preserving the existing
    fail-loud contract for malformed lane fields.
    """
    feature_dir = tmp_path / "feature"

    # has wp_id (so passes the event_type-presence guard) but bad lane name
    bad = _make_lane_event("01EVT0005", "WP03")
    bad["from_lane"] = "not_a_lane"
    _write_events_jsonl(feature_dir, [bad])

    with pytest.raises(StoreError, match="Invalid event structure on line 1"):
        read_events(feature_dir)
