"""Tests for emit_execution_event() and FileClockStorage."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.telemetry.emit import emit_execution_event
from specify_cli.telemetry._clock import FileClockStorage
from specify_cli.telemetry.store import SimpleJsonStore


# ── T014: Unit tests for emission ──────────────────────────────────────


def test_emit_creates_event(tmp_path: Path) -> None:
    """emit_execution_event writes a valid event to the JSONL store."""
    emit_execution_event(
        feature_dir=tmp_path,
        feature_slug="043-telemetry",
        wp_id="WP03",
        agent="claude",
        role="implementer",
        model="claude-sonnet-4",
        input_tokens=1000,
        output_tokens=500,
        cost_usd=0.02,
        duration_ms=3000,
        success=True,
        exit_code=0,
    )

    store = SimpleJsonStore(tmp_path / "execution.events.jsonl")
    events = store.load_all_events()
    assert len(events) == 1

    ev = events[0]
    assert ev.event_type == "ExecutionEvent"
    assert ev.aggregate_id == "043-telemetry"
    assert ev.payload["wp_id"] == "WP03"
    assert ev.payload["agent"] == "claude"
    assert ev.payload["role"] == "implementer"
    assert ev.payload["model"] == "claude-sonnet-4"
    assert ev.payload["input_tokens"] == 1000
    assert ev.payload["output_tokens"] == 500
    assert ev.payload["cost_usd"] == 0.02
    assert ev.payload["duration_ms"] == 3000
    assert ev.payload["success"] is True
    assert ev.payload["exit_code"] == 0
    assert ev.payload["error"] is None
    assert ev.lamport_clock == 1
    assert ev.node_id == "cli:WP03"
    assert len(ev.event_id) == 26


def test_emit_minimal_fields(tmp_path: Path) -> None:
    """emit_execution_event works with only required fields (optional fields are None)."""
    emit_execution_event(
        feature_dir=tmp_path,
        feature_slug="043-telemetry",
        wp_id="WP01",
        agent="opencode",
        role="reviewer",
    )

    store = SimpleJsonStore(tmp_path / "execution.events.jsonl")
    events = store.load_all_events()
    assert len(events) == 1

    ev = events[0]
    assert ev.payload["model"] is None
    assert ev.payload["input_tokens"] is None
    assert ev.payload["output_tokens"] is None
    assert ev.payload["cost_usd"] is None
    assert ev.payload["duration_ms"] == 0
    assert ev.payload["success"] is True
    assert ev.payload["error"] is None
    assert ev.payload["exit_code"] == 0


def test_emit_increments_clock(tmp_path: Path) -> None:
    """Three consecutive emits produce lamport_clock values 1, 2, 3."""
    for _ in range(3):
        emit_execution_event(
            feature_dir=tmp_path,
            feature_slug="feat",
            wp_id="WP01",
            agent="claude",
            role="implementer",
        )

    store = SimpleJsonStore(tmp_path / "execution.events.jsonl")
    events = store.load_all_events()
    assert len(events) == 3
    assert [e.lamport_clock for e in events] == [1, 2, 3]


def test_emit_clock_persists(tmp_path: Path) -> None:
    """Clock value survives across separate calls (new clock instance each time)."""
    emit_execution_event(
        feature_dir=tmp_path,
        feature_slug="feat",
        wp_id="WP01",
        agent="claude",
        role="implementer",
    )

    # Second call with same WP — a fresh LamportClock is constructed
    # but reads persisted value from the same node slot ("cli:WP01").
    emit_execution_event(
        feature_dir=tmp_path,
        feature_slug="feat",
        wp_id="WP01",
        agent="claude",
        role="implementer",
    )

    store = SimpleJsonStore(tmp_path / "execution.events.jsonl")
    events = store.load_all_events()
    assert events[0].lamport_clock == 1
    assert events[1].lamport_clock == 2


def test_emit_swallows_errors(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """If the store raises, no exception propagates and a warning is logged."""
    with patch.object(
        SimpleJsonStore, "save_event", side_effect=OSError("disk full")
    ):
        with caplog.at_level(logging.WARNING):
            # Must NOT raise
            emit_execution_event(
                feature_dir=tmp_path,
                feature_slug="feat",
                wp_id="WP01",
                agent="claude",
                role="implementer",
            )

    assert any("Telemetry emission failed" in r.message for r in caplog.records)


def test_emit_creates_dirs(tmp_path: Path) -> None:
    """emit_execution_event creates parent directories if they don't exist."""
    nested = tmp_path / "deep" / "nested" / "feature"
    emit_execution_event(
        feature_dir=nested,
        feature_slug="feat",
        wp_id="WP01",
        agent="claude",
        role="implementer",
    )

    assert (nested / "execution.events.jsonl").exists()
    assert (nested / ".telemetry-clock.json").exists()


# ── FileClockStorage tests ────────────────────────────────────────────


def test_file_clock_storage_round_trip(tmp_path: Path) -> None:
    """Save and load a clock value."""
    clock_file = tmp_path / "clock.json"
    storage = FileClockStorage(clock_file)

    assert storage.load("node-a") == 0
    storage.save("node-a", 5)
    assert storage.load("node-a") == 5


def test_file_clock_storage_multiple_nodes(tmp_path: Path) -> None:
    """Multiple nodes coexist in the same file."""
    clock_file = tmp_path / "clock.json"
    storage = FileClockStorage(clock_file)

    storage.save("a", 10)
    storage.save("b", 20)

    assert storage.load("a") == 10
    assert storage.load("b") == 20


def test_file_clock_storage_corrupt_file(tmp_path: Path) -> None:
    """Corrupt JSON returns 0 without raising."""
    clock_file = tmp_path / "clock.json"
    clock_file.write_text("not json", encoding="utf-8")

    storage = FileClockStorage(clock_file)
    assert storage.load("node") == 0


def test_file_clock_storage_negative_value(tmp_path: Path) -> None:
    """Negative clock values are rejected."""
    storage = FileClockStorage(tmp_path / "clock.json")
    with pytest.raises(ValueError, match="≥ 0"):
        storage.save("node", -1)


def test_file_clock_storage_creates_dirs(tmp_path: Path) -> None:
    """Parent directories are created on save."""
    clock_file = tmp_path / "a" / "b" / "clock.json"
    storage = FileClockStorage(clock_file)
    storage.save("node", 1)
    assert clock_file.exists()
