"""Tests for mission_v1 event emission (WP05).

Covers:
- emit_event writes correct JSONL structure
- Read-back produces correct event dicts
- Multiple events produce multiple JSONL lines
- emit_event with feature_dir=None does not write a file
- emit_event with read-only directory logs warning, no exception
- read_events on non-existent file returns empty list
- read_events skips corrupt lines gracefully
- Timestamps are ISO 8601 UTC
- MissionModel callbacks emit events during state transitions
"""

from __future__ import annotations

import copy
import json
import logging
import stat
from datetime import datetime
from pathlib import Path

import pytest

from specify_cli.mission_v1.events import (
    MISSION_EVENTS_FILE,
    emit_event,
    read_events,
)


# ---------------------------------------------------------------------------
# T019 / T020 -- emit_event and JSONL writer
# ---------------------------------------------------------------------------


class TestEmitEvent:
    """Tests for the emit_event function."""

    def test_writes_jsonl_line(self, tmp_path: Path) -> None:
        """emit_event writes a single JSONL line to the feature dir."""
        emit_event("phase_entered", {"state": "plan"}, "test-mission", tmp_path)

        events_file = tmp_path / MISSION_EVENTS_FILE
        assert events_file.exists()

        lines = events_file.read_text().splitlines()
        assert len(lines) == 1

        event = json.loads(lines[0])
        assert event["type"] == "phase_entered"
        assert event["mission"] == "test-mission"
        assert event["payload"] == {"state": "plan"}
        assert "timestamp" in event

    def test_event_structure(self, tmp_path: Path) -> None:
        """Emitted event has exactly the expected keys."""
        emit_event("guard_failed", {"guard": "has_spec"}, "my-mission", tmp_path)

        events = read_events(tmp_path)
        assert len(events) == 1

        event = events[0]
        assert set(event.keys()) == {"type", "timestamp", "mission", "payload"}
        assert event["type"] == "guard_failed"
        assert event["mission"] == "my-mission"
        assert event["payload"] == {"guard": "has_spec"}

    def test_timestamp_is_iso8601_utc(self, tmp_path: Path) -> None:
        """Timestamp is a valid ISO 8601 string in UTC."""
        emit_event("phase_entered", {"state": "alpha"}, "ts-test", tmp_path)

        events = read_events(tmp_path)
        ts = events[0]["timestamp"]

        # Must parse as ISO 8601
        parsed = datetime.fromisoformat(ts)
        # Must be UTC (offset-aware with +00:00)
        assert parsed.tzinfo is not None
        assert parsed.utcoffset().total_seconds() == 0

    def test_multiple_events_append(self, tmp_path: Path) -> None:
        """Multiple emit_event calls produce multiple JSONL lines."""
        emit_event("phase_entered", {"state": "alpha"}, "multi", tmp_path)
        emit_event("phase_exited", {"state": "alpha"}, "multi", tmp_path)
        emit_event("phase_entered", {"state": "beta"}, "multi", tmp_path)

        events = read_events(tmp_path)
        assert len(events) == 3
        assert events[0]["type"] == "phase_entered"
        assert events[0]["payload"]["state"] == "alpha"
        assert events[1]["type"] == "phase_exited"
        assert events[2]["type"] == "phase_entered"
        assert events[2]["payload"]["state"] == "beta"

    def test_sorted_keys_in_jsonl(self, tmp_path: Path) -> None:
        """JSONL lines have sorted keys for deterministic output."""
        emit_event("phase_entered", {"state": "x"}, "sorted", tmp_path)

        events_file = tmp_path / MISSION_EVENTS_FILE
        raw_line = events_file.read_text().strip()
        parsed = json.loads(raw_line)
        keys = list(parsed.keys())
        assert keys == sorted(keys)

    def test_no_feature_dir_no_file(self, tmp_path: Path) -> None:
        """emit_event with feature_dir=None writes no file."""
        emit_event("phase_entered", {"state": "alpha"}, "test")
        # No file anywhere
        events_file = tmp_path / MISSION_EVENTS_FILE
        assert not events_file.exists()

    def test_readonly_dir_logs_warning_no_exception(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """emit_event on a read-only directory logs a warning but does not raise."""
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()

        # Make directory read-only
        readonly_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)

        try:
            with caplog.at_level(logging.WARNING):
                # This must NOT raise
                emit_event("phase_entered", {"state": "x"}, "test", readonly_dir)

            assert any("Failed to emit event" in r.message for r in caplog.records)
        finally:
            # Restore write permission for cleanup
            readonly_dir.chmod(stat.S_IRWXU)

    def test_default_mission_name_empty(self, tmp_path: Path) -> None:
        """Default mission_name is empty string."""
        emit_event("phase_entered", {"state": "x"}, feature_dir=tmp_path)

        events = read_events(tmp_path)
        assert events[0]["mission"] == ""


# ---------------------------------------------------------------------------
# T020 -- read_events
# ---------------------------------------------------------------------------


class TestReadEvents:
    """Tests for the read_events function."""

    def test_nonexistent_file_returns_empty(self, tmp_path: Path) -> None:
        """read_events on a directory with no events file returns []."""
        assert read_events(tmp_path) == []

    def test_empty_file_returns_empty(self, tmp_path: Path) -> None:
        """read_events on an empty file returns []."""
        (tmp_path / MISSION_EVENTS_FILE).write_text("")
        assert read_events(tmp_path) == []

    def test_corrupt_line_skipped(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Corrupt JSONL lines are skipped with a warning, valid lines returned."""
        events_file = tmp_path / MISSION_EVENTS_FILE
        events_file.write_text(
            '{"type":"good","timestamp":"2026-01-01T00:00:00+00:00","mission":"t","payload":{}}\n'
            "NOT VALID JSON\n"
            '{"type":"also_good","timestamp":"2026-01-01T00:00:01+00:00","mission":"t","payload":{}}\n'
        )

        with caplog.at_level(logging.WARNING):
            events = read_events(tmp_path)

        assert len(events) == 2
        assert events[0]["type"] == "good"
        assert events[1]["type"] == "also_good"
        assert any("Corrupt event line" in r.message for r in caplog.records)

    def test_blank_lines_ignored(self, tmp_path: Path) -> None:
        """Blank lines in the JSONL file are silently skipped."""
        events_file = tmp_path / MISSION_EVENTS_FILE
        events_file.write_text(
            '{"type":"a","timestamp":"2026-01-01T00:00:00+00:00","mission":"t","payload":{}}\n'
            "\n"
            "\n"
            '{"type":"b","timestamp":"2026-01-01T00:00:01+00:00","mission":"t","payload":{}}\n'
        )

        events = read_events(tmp_path)
        assert len(events) == 2


# ---------------------------------------------------------------------------
# Shared config for callback tests (MarkupMachine mutates state dicts,
# so every test MUST deepcopy before passing to StateMachineMission).
# ---------------------------------------------------------------------------

_CALLBACK_CONFIG: dict = {
    "mission": {
        "name": "callback-test",
        "version": "1.0.0",
        "description": "Tests callback wiring",
    },
    "initial": "alpha",
    "states": [
        {"name": "alpha"},
        {"name": "beta"},
        {"name": "done"},
    ],
    "transitions": [
        {"trigger": "advance", "source": "alpha", "dest": "beta"},
        {"trigger": "advance", "source": "beta", "dest": "done"},
    ],
}


# ---------------------------------------------------------------------------
# T021 -- MissionModel callback wiring
# ---------------------------------------------------------------------------


class TestMissionModelCallbackWiring:
    """Tests that MissionModel callbacks emit events during transitions."""

    def test_enter_event_emitted_on_transition(self, tmp_path: Path) -> None:
        """Transitioning to a new state emits a phase_entered event."""
        from specify_cli.mission_v1.runner import StateMachineMission

        mission = StateMachineMission(copy.deepcopy(_CALLBACK_CONFIG), feature_dir=tmp_path)

        mission.trigger("advance")  # alpha -> beta
        assert mission.state == "beta"

        events = read_events(tmp_path)
        entered = [e for e in events if e["type"] == "phase_entered"]
        assert len(entered) >= 1
        assert any(e["payload"]["state"] == "beta" for e in entered)

    def test_exit_event_emitted_on_transition(self, tmp_path: Path) -> None:
        """Leaving a state emits a phase_exited event."""
        from specify_cli.mission_v1.runner import StateMachineMission

        mission = StateMachineMission(copy.deepcopy(_CALLBACK_CONFIG), feature_dir=tmp_path)

        mission.trigger("advance")  # alpha -> beta

        events = read_events(tmp_path)
        exited = [e for e in events if e["type"] == "phase_exited"]
        assert len(exited) >= 1
        assert any(e["payload"]["state"] == "alpha" for e in exited)

    def test_mission_name_in_emitted_events(self, tmp_path: Path) -> None:
        """Events contain the mission name from the config."""
        from specify_cli.mission_v1.runner import StateMachineMission

        mission = StateMachineMission(copy.deepcopy(_CALLBACK_CONFIG), feature_dir=tmp_path)

        mission.trigger("advance")  # alpha -> beta

        events = read_events(tmp_path)
        assert len(events) >= 1
        assert all(e["mission"] == "callback-test" for e in events)

    def test_no_feature_dir_callbacks_no_error(self) -> None:
        """Callbacks with no feature_dir do not raise."""
        from specify_cli.mission_v1.runner import StateMachineMission

        # No feature_dir -- events not persisted, but no crash
        mission = StateMachineMission(copy.deepcopy(_CALLBACK_CONFIG))
        mission.trigger("advance")  # alpha -> beta
        assert mission.state == "beta"

    def test_transition_produces_exit_then_enter(self, tmp_path: Path) -> None:
        """A single transition produces phase_exited then phase_entered in order."""
        from specify_cli.mission_v1.runner import StateMachineMission

        mission = StateMachineMission(copy.deepcopy(_CALLBACK_CONFIG), feature_dir=tmp_path)

        mission.trigger("advance")  # alpha -> beta

        events = read_events(tmp_path)
        # Filter to only transition events (exit alpha + enter beta)
        transition_events = [e for e in events if e["type"] in ("phase_exited", "phase_entered")]
        assert len(transition_events) == 2
        assert transition_events[0]["type"] == "phase_exited"
        assert transition_events[0]["payload"]["state"] == "alpha"
        assert transition_events[1]["type"] == "phase_entered"
        assert transition_events[1]["payload"]["state"] == "beta"

    def test_multiple_transitions_accumulate_events(self, tmp_path: Path) -> None:
        """Two transitions produce 4 events (2 exits + 2 enters)."""
        from specify_cli.mission_v1.runner import StateMachineMission

        mission = StateMachineMission(copy.deepcopy(_CALLBACK_CONFIG), feature_dir=tmp_path)

        mission.trigger("advance")  # alpha -> beta
        mission.trigger("advance")  # beta -> done
        assert mission.state == "done"

        events = read_events(tmp_path)
        assert len(events) == 4
        types = [e["type"] for e in events]
        assert types == [
            "phase_exited",  # exit alpha
            "phase_entered",  # enter beta
            "phase_exited",  # exit beta
            "phase_entered",  # enter done
        ]
