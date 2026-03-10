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
            "approved": 0,
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


class TestRollbackPrecedence:
    """Tests for concurrent rollback event precedence (kills _is_rollback_event
    and _should_apply_event mutants)."""

    def test_rollback_beats_concurrent_forward_event(self) -> None:
        """A rollback (for_review→in_progress with review_ref) wins over a
        concurrent forward event even when the rollback sorts second."""
        # Forward event sorts first (lower event_id)
        fwd = _make_event(
            event_id="01HXYZ0000000000000000000A",
            wp_id="WP01",
            from_lane=Lane.IN_PROGRESS,
            to_lane=Lane.FOR_REVIEW,
            at="2026-02-08T12:00:00Z",
            review_ref=None,
        )
        # Rollback sorts second (higher event_id) but should win
        rollback = _make_event(
            event_id="01HXYZ0000000000000000000B",
            wp_id="WP01",
            from_lane=Lane.FOR_REVIEW,
            to_lane=Lane.IN_PROGRESS,
            at="2026-02-08T12:00:00Z",  # same timestamp = concurrent
            review_ref="PR#123",
        )
        snapshot = reduce([fwd, rollback])
        # Rollback beats the forward event: WP01 should end in in_progress
        assert snapshot.work_packages["WP01"]["lane"] == "in_progress"

    def test_forward_does_not_beat_concurrent_rollback(self) -> None:
        """A concurrent forward event does not override a rollback that sorts first."""
        # Rollback sorts first (lower event_id)
        rollback = _make_event(
            event_id="01HXYZ0000000000000000000A",
            wp_id="WP01",
            from_lane=Lane.FOR_REVIEW,
            to_lane=Lane.IN_PROGRESS,
            at="2026-02-08T12:00:00Z",
            review_ref="PR#42",
        )
        # Forward sorts second but should NOT override the rollback
        fwd = _make_event(
            event_id="01HXYZ0000000000000000000B",
            wp_id="WP01",
            from_lane=Lane.IN_PROGRESS,
            to_lane=Lane.FOR_REVIEW,
            at="2026-02-08T12:00:00Z",  # same timestamp = concurrent
            review_ref=None,
        )
        snapshot = reduce([rollback, fwd])
        # Forward should not beat rollback: WP01 remains in_progress
        assert snapshot.work_packages["WP01"]["lane"] == "in_progress"

    def test_rollback_requires_review_ref_to_win(self) -> None:
        """for_review→in_progress WITHOUT review_ref is not a rollback and does
        not win over a concurrent forward event in normal sort order."""
        fwd = _make_event(
            event_id="01HXYZ0000000000000000000A",
            wp_id="WP01",
            from_lane=Lane.IN_PROGRESS,
            to_lane=Lane.FOR_REVIEW,
            at="2026-02-08T12:00:00Z",
            review_ref=None,
        )
        # Not a rollback: no review_ref, so both events are "forward"
        not_rollback = _make_event(
            event_id="01HXYZ0000000000000000000B",
            wp_id="WP01",
            from_lane=Lane.FOR_REVIEW,
            to_lane=Lane.IN_PROGRESS,
            at="2026-02-08T12:00:00Z",  # concurrent
            review_ref=None,  # no review_ref → NOT a rollback
        )
        snapshot = reduce([fwd, not_rollback])
        # Without review_ref the later event wins in sort order
        assert snapshot.work_packages["WP01"]["lane"] == "in_progress"

    def test_rollback_requires_from_for_review(self) -> None:
        """A transition to in_progress from a non-for_review lane is NOT a rollback."""
        # claimed → in_progress with review_ref: NOT a rollback (wrong from_lane)
        not_rollback = _make_event(
            event_id="01HXYZ0000000000000000000A",
            wp_id="WP01",
            from_lane=Lane.CLAIMED,  # not FOR_REVIEW
            to_lane=Lane.IN_PROGRESS,
            at="2026-02-08T12:00:00Z",
            review_ref="PR#123",  # has review_ref but from_lane is wrong
        )
        fwd = _make_event(
            event_id="01HXYZ0000000000000000000B",
            wp_id="WP01",
            from_lane=Lane.IN_PROGRESS,
            to_lane=Lane.FOR_REVIEW,
            at="2026-02-08T12:00:00Z",  # concurrent
            review_ref=None,
        )
        snapshot = reduce([not_rollback, fwd])
        # not_rollback is not a rollback, so fwd (second in sort) wins normally
        assert snapshot.work_packages["WP01"]["lane"] == "for_review"

    def test_rollback_requires_to_in_progress(self) -> None:
        """for_review→done is NOT a rollback even with review_ref."""
        fwd = _make_event(
            event_id="01HXYZ0000000000000000000A",
            wp_id="WP01",
            from_lane=Lane.IN_PROGRESS,
            to_lane=Lane.FOR_REVIEW,
            at="2026-02-08T12:00:00Z",
            review_ref=None,
        )
        # for_review→done with review_ref: NOT a rollback (wrong to_lane)
        not_rollback = _make_event(
            event_id="01HXYZ0000000000000000000B",
            wp_id="WP01",
            from_lane=Lane.FOR_REVIEW,
            to_lane=Lane.DONE,  # not IN_PROGRESS
            at="2026-02-08T12:00:00Z",  # concurrent
            review_ref="PR#123",
        )
        snapshot = reduce([fwd, not_rollback])
        # not_rollback is not a rollback, so it wins by sort order (later)
        assert snapshot.work_packages["WP01"]["lane"] == "done"

    def test_non_concurrent_events_are_not_affected_by_rollback_logic(self) -> None:
        """Events at different timestamps follow normal sort order."""
        early = _make_event(
            event_id="01HXYZ0000000000000000000A",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-02-08T11:00:00Z",
        )
        later = _make_event(
            event_id="01HXYZ0000000000000000000B",
            wp_id="WP01",
            from_lane=Lane.CLAIMED,
            to_lane=Lane.IN_PROGRESS,
            at="2026-02-08T12:00:00Z",  # different timestamp
        )
        snapshot = reduce([later, early])  # reversed order, still sorted correctly
        assert snapshot.work_packages["WP01"]["lane"] == "in_progress"


class TestNowUtcTimezone:
    """Tests for _now_utc producing timezone-aware output."""

    def test_materialized_at_contains_utc_offset(self) -> None:
        """materialized_at must be UTC-aware (contains +00:00 or Z)."""
        snapshot = reduce([])
        # datetime.now(timezone.utc).isoformat() produces "+00:00"
        # datetime.now(None).isoformat() produces no offset
        assert snapshot.materialized_at is not None
        assert "+" in snapshot.materialized_at or snapshot.materialized_at.endswith("Z")

    def test_reduce_nonempty_materialized_at_is_not_none(self) -> None:
        """reduce() with events must set materialized_at to a non-None string."""
        event = _make_event(
            event_id="01HXYZ0000000000000000000A",
            wp_id="WP01",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
            at="2026-02-08T12:00:00Z",
        )
        snapshot = reduce([event])
        assert snapshot.materialized_at is not None
        assert isinstance(snapshot.materialized_at, str)
        assert len(snapshot.materialized_at) > 0


class TestMaterializeToJsonFormat:
    """Tests for materialize_to_json JSON formatting specifics."""

    def _make_snapshot(self) -> StatusSnapshot:
        return StatusSnapshot(
            feature_slug="034-feature",
            materialized_at="2026-02-08T15:00:00Z",
            event_count=1,
            last_event_id="01HXYZ0000000000000000000A",
            work_packages={
                "WP01": {
                    "lane": "claimed",
                    "actor": "agent",
                    "last_transition_at": "2026-02-08T12:00:00Z",
                    "last_event_id": "01HXYZ0000000000000000000A",
                    "force_count": 0,
                }
            },
            summary={lane.value: 0 for lane in Lane},
        )

    def test_keys_are_sorted(self) -> None:
        """sort_keys=True: top-level keys appear in lexicographic order."""
        import json

        snapshot = self._make_snapshot()
        json_str = materialize_to_json(snapshot)
        parsed = json.loads(json_str)
        keys = list(parsed.keys())
        assert keys == sorted(keys), f"Keys not sorted: {keys}"

    def test_indent_is_two_spaces(self) -> None:
        """indent=2: lines inside the object are indented with exactly 2 spaces."""
        snapshot = self._make_snapshot()
        json_str = materialize_to_json(snapshot)
        lines = json_str.splitlines()
        # At least one line starts with exactly 2-space indent
        indented_lines = [ln for ln in lines if ln.startswith("  ") and not ln.startswith("   ")]
        assert len(indented_lines) > 0, "Expected lines with 2-space indent"
        # No lines should start with 3-space indent at the top level
        three_space_lines = [ln for ln in lines if ln.startswith("   ") and not ln.startswith("    ")]
        assert len(three_space_lines) == 0, f"Unexpected 3-space indent: {three_space_lines}"

    def test_non_ascii_not_escaped(self) -> None:
        """ensure_ascii=False: non-ASCII characters appear as-is, not \\uXXXX."""
        snapshot = StatusSnapshot(
            feature_slug="034-féature-ü",  # non-ASCII
            materialized_at="2026-02-08T15:00:00Z",
            event_count=0,
            last_event_id=None,
            work_packages={},
            summary={lane.value: 0 for lane in Lane},
        )
        json_str = materialize_to_json(snapshot)
        assert "féature-ü" in json_str, "Non-ASCII should appear verbatim"
        # With ensure_ascii=True, 'é' → '\\u00e9', 'ü' → '\\u00fc'
        assert "\\u00e9" not in json_str
        assert "\\u00fc" not in json_str

    def test_ends_with_newline(self) -> None:
        """Output ends with a trailing newline."""
        snapshot = self._make_snapshot()
        json_str = materialize_to_json(snapshot)
        assert json_str.endswith("\n")

    def test_different_key_order_produces_same_output(self) -> None:
        """sort_keys=True means dicts with keys in different order produce identical output."""
        import json

        snapshot_a = StatusSnapshot(
            feature_slug="034-feature",
            materialized_at="2026-02-08T15:00:00Z",
            event_count=1,
            last_event_id="01HXYZ0000000000000000000A",
            work_packages={
                "WP01": {
                    "lane": "claimed",
                    "actor": "agent",
                    "last_transition_at": "2026-02-08T12:00:00Z",
                    "last_event_id": "01HXYZ0000000000000000000A",
                    "force_count": 0,
                }
            },
            summary={lane.value: 0 for lane in Lane},
        )
        json_str = materialize_to_json(snapshot_a)
        parsed = json.loads(json_str)
        # Re-serialise with random key order: sort_keys must normalise it
        import io

        out = io.StringIO()
        json.dump(parsed, out, sort_keys=True, indent=2, ensure_ascii=False)
        assert json_str == out.getvalue() + "\n"
