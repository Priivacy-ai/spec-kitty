"""WP06 (T028) -- unit tests for the pure status.emit helpers.

These tests pin the FR-032 contract that the status domain stays free
of coordination-layer concerns: ``build_status_event`` is a pure
constructor and ``append_event_jsonl`` is a pure single-line append
with no commit, materialization, or fan-out side effect.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.status.emit import (
    append_event_jsonl,
    build_status_event,
)
from specify_cli.status.models import Lane, StatusEvent


class TestBuildStatusEvent:
    """``build_status_event`` is a pure constructor."""

    def test_returns_status_event_with_required_fields(self) -> None:
        event = build_status_event(
            mission_slug="034-feature",
            wp_id="WP01",
            from_lane="planned",
            to_lane="claimed",
            actor="claude",
        )
        assert isinstance(event, StatusEvent)
        assert event.mission_slug == "034-feature"
        assert event.wp_id == "WP01"
        assert event.from_lane == Lane.PLANNED
        assert event.to_lane == Lane.CLAIMED
        assert event.actor == "claude"
        assert event.event_id  # non-empty ULID
        assert event.at  # non-empty ISO timestamp

    def test_mission_id_threads_through_when_provided(self) -> None:
        event = build_status_event(
            mission_slug="my-mission-01ABCDEF",
            wp_id="WP02",
            from_lane="claimed",
            to_lane="in_progress",
            actor="implementer-ivan",
            mission_id="01ABCDEFGHJKMNPQRSTVWXYZ12",
        )
        assert event.mission_id == "01ABCDEFGHJKMNPQRSTVWXYZ12"

    def test_mission_id_defaults_to_none_for_legacy_callers(self) -> None:
        event = build_status_event(
            mission_slug="legacy",
            wp_id="WP01",
            from_lane="planned",
            to_lane="claimed",
            actor="claude",
        )
        assert event.mission_id is None

    def test_each_call_produces_a_distinct_event_id(self) -> None:
        event_a = build_status_event(
            mission_slug="m", wp_id="WP01", from_lane="planned",
            to_lane="claimed", actor="claude",
        )
        event_b = build_status_event(
            mission_slug="m", wp_id="WP01", from_lane="planned",
            to_lane="claimed", actor="claude",
        )
        assert event_a.event_id != event_b.event_id

    def test_no_io_side_effects(self, tmp_path: Path) -> None:
        # Building an event must not touch the filesystem under tmp_path.
        before = set(tmp_path.iterdir())
        build_status_event(
            mission_slug="m", wp_id="WP01", from_lane="planned",
            to_lane="claimed", actor="claude",
        )
        after = set(tmp_path.iterdir())
        assert before == after


class TestAppendEventJsonl:
    """``append_event_jsonl`` is a pure single-line append with no commit."""

    def test_appends_a_single_line_with_canonical_keys(
        self, tmp_path: Path
    ) -> None:
        events_path = tmp_path / "status.events.jsonl"
        event = build_status_event(
            mission_slug="034-feature", wp_id="WP01",
            from_lane="planned", to_lane="claimed", actor="claude",
        )

        append_event_jsonl(events_path, event)

        assert events_path.exists()
        lines = events_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        payload = json.loads(lines[0])
        assert payload["wp_id"] == "WP01"
        assert payload["to_lane"] == "claimed"
        assert payload["event_id"] == event.event_id

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        deep_path = tmp_path / "kitty-specs" / "feat" / "status.events.jsonl"
        event = build_status_event(
            mission_slug="m", wp_id="WP01",
            from_lane="planned", to_lane="claimed", actor="claude",
        )
        append_event_jsonl(deep_path, event)
        assert deep_path.exists()

    def test_appends_preserve_prior_content(self, tmp_path: Path) -> None:
        events_path = tmp_path / "status.events.jsonl"
        first = build_status_event(
            mission_slug="m", wp_id="WP01",
            from_lane="planned", to_lane="claimed", actor="claude",
        )
        second = build_status_event(
            mission_slug="m", wp_id="WP01",
            from_lane="claimed", to_lane="in_progress", actor="claude",
        )
        append_event_jsonl(events_path, first)
        append_event_jsonl(events_path, second)

        lines = events_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["event_id"] == first.event_id
        assert json.loads(lines[1])["event_id"] == second.event_id
