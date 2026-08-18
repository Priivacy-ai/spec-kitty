"""Snapshot value-equality round-trip (WP10, C-8 / FR-015).

Property: replaying a persisted event log reproduces the reduced snapshot's
projected fields **by value** (deep equality), not merely by key-presence.

Design guards against the two ways this could be a fake:

* **Non-vacuity** — the generator is *asserted* to emit ≥1
  ``review_result``-carrying event, and the resulting projection is asserted to
  carry a non-``None`` ``review_result`` value. A property that never exercises
  the field under test passes trivially and proves nothing.

* **Value-level (not key-level)** — a negative case corrupts a persisted
  ``review_result`` *value* (keeping the key intact) and asserts the replayed
  projection then **differs** from the faithful snapshot. A key-presence-only
  assertion would miss this; value equality catches it.

The round-trip is a real persist→read→reduce cycle: events are written to a
``status.events.jsonl`` file and re-read through the production
``read_event_stream`` → ``reduce`` path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.status.models import Lane, ReviewResult, StatusEvent, StatusSnapshot
from specify_cli.status.reducer import reduce
from specify_cli.status.store import EVENTS_FILENAME, read_event_stream

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_MISSION = "worktree-root-resolution-01M0B59R"
_MISSION_ID = "01M0B59RAAAAAAAAAAAAAAAAAA"


def _event(
    seq: int,
    wp_id: str,
    from_lane: Lane,
    to_lane: Lane,
    *,
    review_result: ReviewResult | None = None,
) -> StatusEvent:
    return StatusEvent(
        event_id=f"01J{seq:023d}",
        mission_slug=_MISSION,
        wp_id=wp_id,
        from_lane=from_lane,
        to_lane=to_lane,
        at=f"2026-08-18T21:{seq:02d}:00+00:00",
        actor="claude",
        force=False,
        execution_mode="worktree",
        review_ref=(review_result.reference if review_result else None),
        review_result=review_result,
        mission_id=_MISSION_ID,
    )


def _generate_events() -> list[StatusEvent]:
    """A non-vacuous event log: at least one ``review_result``-carrying event.

    Two WPs walk the lifecycle; WP-A reaches ``approved`` carrying a verdict so
    the reduced projection has a populated ``review_result`` slot to round-trip.
    """
    verdict = ReviewResult(
        reviewer="reviewer-rachel",
        verdict="approved",
        reference="approval://wp-a",
    )
    return [
        _event(1, "WPA", Lane.PLANNED, Lane.CLAIMED),
        _event(2, "WPA", Lane.CLAIMED, Lane.IN_PROGRESS),
        _event(3, "WPA", Lane.IN_PROGRESS, Lane.FOR_REVIEW),
        _event(4, "WPA", Lane.FOR_REVIEW, Lane.IN_REVIEW),
        _event(5, "WPA", Lane.IN_REVIEW, Lane.APPROVED, review_result=verdict),
        _event(6, "WPB", Lane.PLANNED, Lane.CLAIMED),
        _event(7, "WPB", Lane.CLAIMED, Lane.IN_PROGRESS),
    ]


def _persist(feature_dir: Path, rows: list[dict[str, object]]) -> None:
    text = "".join(json.dumps(row) + "\n" for row in rows)
    (feature_dir / EVENTS_FILENAME).write_text(text, encoding="utf-8")


def _replay(feature_dir: Path) -> StatusSnapshot:
    stream = read_event_stream(feature_dir)
    return reduce(stream.transitions, stream.annotations)


def _projected_review_results(snapshot: StatusSnapshot) -> dict[str, object]:
    return {
        wp_id: state.get("review_result")
        for wp_id, state in snapshot.work_packages.items()
    }


def test_generator_is_non_vacuous() -> None:
    """The generator MUST emit ≥1 ``review_result``-carrying event."""
    events = _generate_events()
    carriers = [e for e in events if e.review_result is not None]
    assert carriers, "generator must emit at least one review_result event"


def test_snapshot_round_trips_by_value(tmp_path: Path) -> None:
    """Faithful replay reproduces the projected fields by value (FR-015)."""
    events = _generate_events()

    # Baseline snapshot from the in-memory events.
    baseline = reduce(events, [])

    # Non-vacuity at the projection level: the field under test is populated.
    baseline_projection = _projected_review_results(baseline)
    assert baseline_projection["WPA"] is not None, (
        "projection must carry a non-None review_result (non-vacuous property)"
    )

    # Persist → read → reduce (a real round-trip through the serializer).
    _persist(tmp_path, [e.to_dict() for e in events])
    replayed = _replay(tmp_path)

    # Deep, value-level equality on the full per-WP projection.
    assert replayed.work_packages == baseline.work_packages, (
        "replayed projection must equal the snapshot by value"
    )
    assert _projected_review_results(replayed) == baseline_projection


def test_corrupted_value_replay_fails(tmp_path: Path) -> None:
    """Negative case: a corrupted ``review_result`` VALUE breaks equality.

    Proves the round-trip assertion is value-level, not key-presence: the key
    survives corruption, only the value changes, and the faithful snapshot must
    then NOT equal the corrupted replay.
    """
    events = _generate_events()
    baseline = reduce(events, [])

    rows = [e.to_dict() for e in events]
    corrupted = False
    for row in rows:
        rr = row.get("review_result")
        if isinstance(rr, dict):
            rr["verdict"] = "changes_requested"  # same key, different value
            rr["reference"] = "feedback://corrupted"
            corrupted = True
    assert corrupted, "expected a persisted review_result value to corrupt"

    _persist(tmp_path, rows)
    replayed = _replay(tmp_path)

    # Key still present on both sides — but the VALUE differs, so a value-level
    # comparison must fail (a key-only fake would wrongly pass here).
    assert "review_result" in replayed.work_packages["WPA"]
    assert replayed.work_packages != baseline.work_packages, (
        "a corrupted review_result value must break value-level equality"
    )
    assert (
        _projected_review_results(replayed)["WPA"]
        != _projected_review_results(baseline)["WPA"]
    )
