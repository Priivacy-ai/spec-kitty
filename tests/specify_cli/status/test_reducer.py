"""Tests for the deterministic status reducer."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch


from specify_cli.status.models import Lane, StatusEvent, StatusSnapshot
from specify_cli.status.reducer import (
    SNAPSHOT_FILENAME,
    materialize,
    materialize_to_json,
    reduce,
)
from specify_cli.status.store import append_event


def _make_event(
    *,
    event_id: str = "01HXYZ0000000000000000000A",
    feature_slug: str = "034-feature-name",
    wp_id: str = "WP01",
    from_lane: Lane = Lane.PLANNED,
    to_lane: Lane = Lane.CLAIMED,
    at: str = "2026-02-08T12:00:00Z",
    actor: str = "claude-opus",
    force: bool = False,
    execution_mode: str = "worktree",
    reason: str | None = None,
    review_ref: str | None = None,
) -> StatusEvent:
    """Helper to build StatusEvent with sensible defaults."""
    return StatusEvent(
        event_id=event_id,
        feature_slug=feature_slug,
        wp_id=wp_id,
        from_lane=from_lane,
        to_lane=to_lane,
        at=at,
        actor=actor,
        force=force,
        execution_mode=execution_mode,
        reason=reason,
        review_ref=review_ref,
    )


class TestReduceEmpty:
    """Tests for reducing an empty event list."""

    def test_reduce_empty_events(self) -> None:
        snapshot = reduce([])

        assert snapshot.feature_slug == ""
        assert snapshot.event_count == 0
        assert snapshot.last_event_id is None
        assert snapshot.work_packages == {}
        assert snapshot.summary == {
            "planned": 0,
            "claimed": 0,
            "in_progress": 0,
            "for_review": 0,
            "done": 0,
            "blocked": 0,
            "canceled": 0,
        }


class TestReduceSingleEvent:
    """Tests for reducing a single event."""

    def test_reduce_single_event(self) -> None:
        event = _make_event(
            event_id="01HXYZ0000000000000000000A",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-02-08T12:00:00Z",
            actor="claude-opus",
        )
        snapshot = reduce([event])

        assert snapshot.feature_slug == "034-feature-name"
        assert snapshot.event_count == 1
        assert snapshot.last_event_id == "01HXYZ0000000000000000000A"
        assert "WP01" in snapshot.work_packages
        wp = snapshot.work_packages["WP01"]
        assert wp["lane"] == "claimed"
        assert wp["actor"] == "claude-opus"
        assert wp["last_transition_at"] == "2026-02-08T12:00:00Z"
        assert wp["last_event_id"] == "01HXYZ0000000000000000000A"
        assert wp["force_count"] == 0
        assert snapshot.summary["claimed"] == 1


class TestReduceOrderedEvents:
    """Tests for reducing events already in order."""

    def test_reduce_ordered_events(self) -> None:
        events = [
            _make_event(
                event_id="01HXYZ0000000000000000000A",
                wp_id="WP01",
                from_lane=Lane.PLANNED,
                to_lane=Lane.CLAIMED,
                at="2026-02-08T12:00:00Z",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000B",
                wp_id="WP01",
                from_lane=Lane.CLAIMED,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T13:00:00Z",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000C",
                wp_id="WP01",
                from_lane=Lane.IN_PROGRESS,
                to_lane=Lane.FOR_REVIEW,
                at="2026-02-08T14:00:00Z",
            ),
        ]
        snapshot = reduce(events)

        assert snapshot.event_count == 3
        assert snapshot.work_packages["WP01"]["lane"] == "for_review"
        assert snapshot.summary["for_review"] == 1


class TestReduceOutOfOrder:
    """Tests for reducing events that arrive out of order."""

    def test_reduce_out_of_order_events(self) -> None:
        """Events are sorted by (at, event_id), so order in list doesn't matter."""
        events = [
            _make_event(
                event_id="01HXYZ0000000000000000000C",
                wp_id="WP01",
                from_lane=Lane.IN_PROGRESS,
                to_lane=Lane.FOR_REVIEW,
                at="2026-02-08T14:00:00Z",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000A",
                wp_id="WP01",
                from_lane=Lane.PLANNED,
                to_lane=Lane.CLAIMED,
                at="2026-02-08T12:00:00Z",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000B",
                wp_id="WP01",
                from_lane=Lane.CLAIMED,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T13:00:00Z",
            ),
        ]
        snapshot = reduce(events)

        assert snapshot.work_packages["WP01"]["lane"] == "for_review"
        assert snapshot.last_event_id == "01HXYZ0000000000000000000C"


class TestReduceDeduplication:
    """Tests for deduplication by event_id."""

    def test_reduce_deduplication(self) -> None:
        """Duplicate event_ids are deduplicated; first occurrence kept."""
        event = _make_event(
            event_id="01HXYZ0000000000000000000A",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-02-08T12:00:00Z",
            actor="claude-opus",
        )
        # Same event_id but different actor (simulating corruption)
        duplicate = _make_event(
            event_id="01HXYZ0000000000000000000A",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-02-08T12:00:00Z",
            actor="other-agent",
        )
        snapshot = reduce([event, duplicate])

        assert snapshot.event_count == 1
        assert snapshot.work_packages["WP01"]["actor"] == "claude-opus"


class TestReduceMultipleWPs:
    """Tests for reducing events across multiple work packages."""

    def test_reduce_multiple_wps(self) -> None:
        events = [
            _make_event(
                event_id="01HXYZ0000000000000000000A",
                wp_id="WP01",
                from_lane=Lane.PLANNED,
                to_lane=Lane.CLAIMED,
                at="2026-02-08T12:00:00Z",
                actor="agent-a",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000B",
                wp_id="WP02",
                from_lane=Lane.PLANNED,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T12:30:00Z",
                actor="agent-b",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000C",
                wp_id="WP03",
                from_lane=Lane.PLANNED,
                to_lane=Lane.BLOCKED,
                at="2026-02-08T13:00:00Z",
                actor="agent-c",
            ),
        ]
        snapshot = reduce(events)

        assert len(snapshot.work_packages) == 3
        assert snapshot.work_packages["WP01"]["lane"] == "claimed"
        assert snapshot.work_packages["WP02"]["lane"] == "in_progress"
        assert snapshot.work_packages["WP03"]["lane"] == "blocked"
        assert snapshot.summary["claimed"] == 1
        assert snapshot.summary["in_progress"] == 1
        assert snapshot.summary["blocked"] == 1


class TestReduceForceCount:
    """Tests for force_count tracking."""

    def test_reduce_force_count_tracked(self) -> None:
        events = [
            _make_event(
                event_id="01HXYZ0000000000000000000A",
                wp_id="WP01",
                from_lane=Lane.PLANNED,
                to_lane=Lane.CLAIMED,
                at="2026-02-08T12:00:00Z",
                force=False,
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000B",
                wp_id="WP01",
                from_lane=Lane.CLAIMED,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T13:00:00Z",
                force=True,
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000C",
                wp_id="WP01",
                from_lane=Lane.IN_PROGRESS,
                to_lane=Lane.FOR_REVIEW,
                at="2026-02-08T14:00:00Z",
                force=True,
            ),
        ]
        snapshot = reduce(events)

        assert snapshot.work_packages["WP01"]["force_count"] == 2


class TestSummaryCounts:
    """Tests that summary counts match WP states."""

    def test_summary_counts_match_wp_states(self) -> None:
        events = [
            _make_event(
                event_id="01HXYZ0000000000000000000A",
                wp_id="WP01",
                from_lane=Lane.PLANNED,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T12:00:00Z",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000B",
                wp_id="WP02",
                from_lane=Lane.PLANNED,
                to_lane=Lane.IN_PROGRESS,
                at="2026-02-08T12:00:00Z",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000C",
                wp_id="WP03",
                from_lane=Lane.PLANNED,
                to_lane=Lane.FOR_REVIEW,
                at="2026-02-08T13:00:00Z",
            ),
            _make_event(
                event_id="01HXYZ0000000000000000000D",
                wp_id="WP04",
                from_lane=Lane.FOR_REVIEW,
                to_lane=Lane.DONE,
                at="2026-02-08T14:00:00Z",
                actor="reviewer",
            ),
        ]
        snapshot = reduce(events)

        # Count lanes from WP states manually
        lane_counts: dict[str, int] = {lane.value: 0 for lane in Lane}
        for wp_state in snapshot.work_packages.values():
            lane_counts[wp_state["lane"]] += 1

        assert snapshot.summary == lane_counts


class TestByteIdenticalOutput:
    """Tests for deterministic JSON serialization."""

    def test_byte_identical_output(self) -> None:
        """Two calls to materialize_to_json with the same snapshot produce
        identical byte strings."""
        snapshot = StatusSnapshot(
            feature_slug="034-feature-name",
            materialized_at="2026-02-08T15:00:00Z",
            event_count=2,
            last_event_id="01HXYZ0000000000000000000B",
            work_packages={
                "WP01": {
                    "lane": "in_progress",
                    "actor": "claude-opus",
                    "last_transition_at": "2026-02-08T13:00:00Z",
                    "last_event_id": "01HXYZ0000000000000000000B",
                    "force_count": 0,
                },
            },
            summary={
                "planned": 0,
                "claimed": 0,
                "in_progress": 1,
                "for_review": 0,
                "done": 0,
                "blocked": 0,
                "canceled": 0,
            },
        )

        json_a = materialize_to_json(snapshot)
        json_b = materialize_to_json(snapshot)

        assert json_a == json_b
        assert json_a.endswith("\n")

        # Verify it's valid JSON
        parsed = json.loads(json_a)
        assert parsed["feature_slug"] == "034-feature-name"

    def test_byte_identical_across_reduce_calls(self) -> None:
        """Two reduce calls with the same events and a fixed materialized_at
        produce identical JSON."""
        events = [
            _make_event(
                event_id="01HXYZ0000000000000000000A",
                wp_id="WP01",
                from_lane=Lane.PLANNED,
                to_lane=Lane.CLAIMED,
                at="2026-02-08T12:00:00Z",
            ),
        ]

        fixed_time = "2026-02-08T15:00:00+00:00"
        with patch("specify_cli.status.reducer._now_utc", return_value=fixed_time):
            snapshot_a = reduce(events)
            snapshot_b = reduce(events)

        json_a = materialize_to_json(snapshot_a)
        json_b = materialize_to_json(snapshot_b)
        assert json_a == json_b


class TestMaterializeFile:
    """Tests for materialize() writing to disk."""

    def test_materialize_creates_status_json(self, tmp_path: Path) -> None:
        """materialize() reads events and writes status.json."""
        feature_dir = tmp_path / "kitty-specs" / "034-feature"
        feature_dir.mkdir(parents=True)

        event = _make_event(
            event_id="01HXYZ0000000000000000000A",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-02-08T12:00:00Z",
        )
        append_event(feature_dir, event)

        snapshot = materialize(feature_dir)

        status_path = feature_dir / SNAPSHOT_FILENAME
        assert status_path.exists()

        content = status_path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert parsed["feature_slug"] == "034-feature-name"
        assert parsed["event_count"] == 1
        assert "WP01" in parsed["work_packages"]

        # Snapshot returned matches file content
        assert snapshot.feature_slug == "034-feature-name"
        assert snapshot.event_count == 1

    def test_materialize_atomic_write(self, tmp_path: Path) -> None:
        """materialize() does not leave .tmp files behind."""
        feature_dir = tmp_path / "kitty-specs" / "034-feature"
        feature_dir.mkdir(parents=True)

        event = _make_event(
            event_id="01HXYZ0000000000000000000A",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-02-08T12:00:00Z",
        )
        append_event(feature_dir, event)

        materialize(feature_dir)

        # The .tmp file should not remain
        tmp_file = feature_dir / (SNAPSHOT_FILENAME + ".tmp")
        assert not tmp_file.exists()
        # But the final file should exist
        assert (feature_dir / SNAPSHOT_FILENAME).exists()

    def test_materialize_empty_events(self, tmp_path: Path) -> None:
        """materialize() with no events file still writes status.json."""
        feature_dir = tmp_path / "kitty-specs" / "034-feature"
        feature_dir.mkdir(parents=True)

        snapshot = materialize(feature_dir)

        status_path = feature_dir / SNAPSHOT_FILENAME
        assert status_path.exists()
        assert snapshot.feature_slug == ""
        assert snapshot.event_count == 0

    def test_materialize_overwrites_existing(self, tmp_path: Path) -> None:
        """materialize() overwrites an existing status.json."""
        feature_dir = tmp_path / "kitty-specs" / "034-feature"
        feature_dir.mkdir(parents=True)

        # Write initial event and materialize
        event1 = _make_event(
            event_id="01HXYZ0000000000000000000A",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-02-08T12:00:00Z",
        )
        append_event(feature_dir, event1)
        materialize(feature_dir)

        # Add another event and re-materialize
        event2 = _make_event(
            event_id="01HXYZ0000000000000000000B",
            wp_id="WP01",
            from_lane=Lane.CLAIMED,
            to_lane=Lane.IN_PROGRESS,
            at="2026-02-08T13:00:00Z",
        )
        append_event(feature_dir, event2)
        snapshot = materialize(feature_dir)

        assert snapshot.event_count == 2
        assert snapshot.work_packages["WP01"]["lane"] == "in_progress"
