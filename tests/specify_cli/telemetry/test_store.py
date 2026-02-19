"""Tests for SimpleJsonStore — JSONL-backed EventStore implementation.

Acceptance tests for WP01 (043-telemetry-foundation):
- FR-001: Event persistence to JSONL
- FR-002: Event retrieval with ordering
- FR-011: Empty/missing files return empty results
- FR-012: Malformed lines tolerated

Test IDs reference subtasks T001-T006.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from specify_cli.spec_kitty_events.models import Event
from specify_cli.spec_kitty_events.storage import EventStore


def make_event(
    *,
    event_id: str = "01HX0000000000000000000001",
    event_type: str = "ExecutionEvent",
    aggregate_id: str = "test-feature",
    lamport_clock: int = 1,
    node_id: str = "cli",
    payload: dict | None = None,
    causation_id: str | None = None,
) -> Event:
    """Factory for test events with sensible defaults."""
    return Event(
        event_id=event_id,
        event_type=event_type,
        aggregate_id=aggregate_id,
        timestamp=datetime.now(timezone.utc),
        node_id=node_id,
        lamport_clock=lamport_clock,
        causation_id=causation_id,
        payload=payload or {},
    )


# ---------------------------------------------------------------------------
# Acceptance test: SimpleJsonStore implements EventStore ABC (T001, T002)
# ---------------------------------------------------------------------------


class TestSimpleJsonStoreIsEventStore:
    """Verify SimpleJsonStore satisfies the EventStore contract."""

    def test_is_subclass_of_event_store(self) -> None:
        """T001/T002: SimpleJsonStore must implement EventStore ABC."""
        from specify_cli.telemetry.store import SimpleJsonStore

        assert issubclass(SimpleJsonStore, EventStore)

    def test_importable_from_telemetry_package(self) -> None:
        """T001: SimpleJsonStore exported from telemetry package."""
        from specify_cli.telemetry import SimpleJsonStore

        assert SimpleJsonStore is not None


# ---------------------------------------------------------------------------
# Acceptance test: Save and load events (T002, T003)
# ---------------------------------------------------------------------------


class TestSaveAndLoadEvents:
    """Verify core save/load round-trip and ordering."""

    def test_save_and_load_by_aggregate(self, tmp_path: Path) -> None:
        """T002: Save events with different aggregate_ids, load by aggregate,
        verify filtering and sort order."""
        from specify_cli.telemetry.store import SimpleJsonStore

        store = SimpleJsonStore(tmp_path / "events.jsonl")

        e1 = make_event(
            event_id="01HX0000000000000000000001",
            aggregate_id="feature-a",
            lamport_clock=2,
        )
        e2 = make_event(
            event_id="01HX0000000000000000000002",
            aggregate_id="feature-b",
            lamport_clock=1,
        )
        e3 = make_event(
            event_id="01HX0000000000000000000003",
            aggregate_id="feature-a",
            lamport_clock=1,
        )

        store.save_event(e1)
        store.save_event(e2)
        store.save_event(e3)

        # Load only feature-a events
        result = store.load_events("feature-a")
        assert len(result) == 2
        # Sorted by lamport_clock ascending
        assert result[0].event_id == e3.event_id  # clock=1
        assert result[1].event_id == e1.event_id  # clock=2

    def test_save_and_load_all(self, tmp_path: Path) -> None:
        """T002: Save events, load_all, verify all returned sorted."""
        from specify_cli.telemetry.store import SimpleJsonStore

        store = SimpleJsonStore(tmp_path / "events.jsonl")

        e1 = make_event(
            event_id="01HX0000000000000000000001",
            lamport_clock=3,
            node_id="node-b",
        )
        e2 = make_event(
            event_id="01HX0000000000000000000002",
            lamport_clock=1,
            node_id="node-a",
        )
        e3 = make_event(
            event_id="01HX0000000000000000000003",
            lamport_clock=1,
            node_id="node-b",
        )

        store.save_event(e1)
        store.save_event(e2)
        store.save_event(e3)

        result = store.load_all_events()
        assert len(result) == 3
        # Sorted by (lamport_clock, node_id)
        assert result[0].event_id == e2.event_id  # clock=1, node-a
        assert result[1].event_id == e3.event_id  # clock=1, node-b
        assert result[2].event_id == e1.event_id  # clock=3, node-b

    def test_sort_order_matches_in_memory_store(self, tmp_path: Path) -> None:
        """T002: Sort order must match InMemoryEventStore: (lamport_clock, node_id)."""
        from specify_cli.spec_kitty_events.storage import InMemoryEventStore
        from specify_cli.telemetry.store import SimpleJsonStore

        events = [
            make_event(
                event_id="01HX0000000000000000000001",
                lamport_clock=5,
                node_id="z",
            ),
            make_event(
                event_id="01HX0000000000000000000002",
                lamport_clock=1,
                node_id="a",
            ),
            make_event(
                event_id="01HX0000000000000000000003",
                lamport_clock=1,
                node_id="b",
            ),
            make_event(
                event_id="01HX0000000000000000000004",
                lamport_clock=3,
                node_id="a",
            ),
        ]

        json_store = SimpleJsonStore(tmp_path / "events.jsonl")
        mem_store = InMemoryEventStore()

        for e in events:
            json_store.save_event(e)
            mem_store.save_event(e)

        json_result = json_store.load_all_events()
        mem_result = mem_store.load_all_events()

        assert [e.event_id for e in json_result] == [
            e.event_id for e in mem_result
        ]


# ---------------------------------------------------------------------------
# Acceptance test: Empty/missing file (FR-011)
# ---------------------------------------------------------------------------


class TestEmptyAndMissingFile:
    """Verify empty/missing files return empty results without errors."""

    def test_load_from_nonexistent_file(self, tmp_path: Path) -> None:
        """FR-011: Load from non-existent file returns empty list."""
        from specify_cli.telemetry.store import SimpleJsonStore

        store = SimpleJsonStore(tmp_path / "nonexistent.jsonl")

        assert store.load_events("any") == []
        assert store.load_all_events() == []

    def test_load_from_empty_file(self, tmp_path: Path) -> None:
        """FR-011: Load from empty file returns empty list."""
        from specify_cli.telemetry.store import SimpleJsonStore

        jsonl_path = tmp_path / "empty.jsonl"
        jsonl_path.write_text("", encoding="utf-8")

        store = SimpleJsonStore(jsonl_path)
        assert store.load_all_events() == []


# ---------------------------------------------------------------------------
# Acceptance test: Idempotent writes (T004)
# ---------------------------------------------------------------------------


class TestIdempotentWrites:
    """Verify duplicate event_id is not written twice."""

    def test_duplicate_event_id_skipped(self, tmp_path: Path) -> None:
        """T004: Save same event twice, only one entry in file."""
        from specify_cli.telemetry.store import SimpleJsonStore

        store = SimpleJsonStore(tmp_path / "events.jsonl")
        event = make_event(event_id="01HX0000000000000000000001")

        store.save_event(event)
        store.save_event(event)

        result = store.load_all_events()
        assert len(result) == 1

        # Also verify file has exactly 1 line
        lines = [
            ln
            for ln in (tmp_path / "events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if ln.strip()
        ]
        assert len(lines) == 1

    def test_idempotent_across_store_instances(self, tmp_path: Path) -> None:
        """T004: Idempotency persists across store instances."""
        from specify_cli.telemetry.store import SimpleJsonStore

        path = tmp_path / "events.jsonl"
        event = make_event(event_id="01HX0000000000000000000001")

        store1 = SimpleJsonStore(path)
        store1.save_event(event)

        store2 = SimpleJsonStore(path)
        store2.save_event(event)

        result = store2.load_all_events()
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Acceptance test: Malformed line tolerance (T005, FR-012)
# ---------------------------------------------------------------------------


class TestMalformedLineTolerance:
    """Verify corrupted JSONL lines are skipped with warning."""

    def test_malformed_line_skipped(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """T005/FR-012: Malformed line skipped, valid events returned."""
        from specify_cli.telemetry.store import SimpleJsonStore

        jsonl_path = tmp_path / "events.jsonl"
        store = SimpleJsonStore(jsonl_path)

        # Save a valid event
        valid_event = make_event(event_id="01HX0000000000000000000001")
        store.save_event(valid_event)

        # Manually append a corrupt line
        with open(jsonl_path, "a", encoding="utf-8") as f:
            f.write("{this is not valid json}\n")

        # Create fresh store to bypass any caches
        store2 = SimpleJsonStore(jsonl_path)
        with caplog.at_level(logging.WARNING):
            result = store2.load_all_events()

        assert len(result) == 1
        assert result[0].event_id == valid_event.event_id
        assert any("malformed" in record.message.lower() or "skipping" in record.message.lower()
                    for record in caplog.records)

    def test_partial_json_line_skipped(self, tmp_path: Path) -> None:
        """T005: Partial JSON from crash is tolerated."""
        from specify_cli.telemetry.store import SimpleJsonStore

        jsonl_path = tmp_path / "events.jsonl"

        # Write partial JSON (simulating crash during write)
        with open(jsonl_path, "w", encoding="utf-8") as f:
            f.write('{"event_id": "01HX00000000000000000000\n')

        store = SimpleJsonStore(jsonl_path)
        result = store.load_all_events()
        assert result == []


# ---------------------------------------------------------------------------
# Acceptance test: Parent directory creation (T002)
# ---------------------------------------------------------------------------


class TestDirectoryCreation:
    """Verify store creates parent directories on save."""

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        """T002: Save to path with non-existent parent dirs."""
        from specify_cli.telemetry.store import SimpleJsonStore

        deep_path = tmp_path / "a" / "b" / "c" / "events.jsonl"
        store = SimpleJsonStore(deep_path)

        event = make_event(event_id="01HX0000000000000000000001")
        store.save_event(event)

        result = store.load_all_events()
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Acceptance test: Performance (non-functional)
# ---------------------------------------------------------------------------


class TestPerformance:
    """Verify performance meets non-functional requirements."""

    def test_1000_events_load_under_2_seconds(self, tmp_path: Path) -> None:
        """NFR: Load 1000 events completes in <2 seconds."""
        from specify_cli.telemetry.store import SimpleJsonStore

        store = SimpleJsonStore(tmp_path / "events.jsonl")

        for i in range(1000):
            event = make_event(
                event_id=f"01HX{i:022d}",
                lamport_clock=i,
            )
            store.save_event(event)

        # Fresh store instance to measure cold read
        store2 = SimpleJsonStore(tmp_path / "events.jsonl")

        start = time.monotonic()
        result = store2.load_all_events()
        elapsed = time.monotonic() - start

        assert len(result) == 1000
        assert elapsed < 2.0, f"Load took {elapsed:.2f}s, expected <2s"


# ---------------------------------------------------------------------------
# Acceptance test: JSONL format correctness
# ---------------------------------------------------------------------------


class TestJsonlFormat:
    """Verify the JSONL file format is correct and interoperable."""

    def test_each_line_is_valid_json(self, tmp_path: Path) -> None:
        """Events serialized as one JSON object per line."""
        from specify_cli.telemetry.store import SimpleJsonStore

        store = SimpleJsonStore(tmp_path / "events.jsonl")

        for i in range(3):
            store.save_event(
                make_event(
                    event_id=f"01HX{i:022d}",
                    lamport_clock=i,
                )
            )

        lines = [
            ln
            for ln in (tmp_path / "events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if ln.strip()
        ]
        assert len(lines) == 3

        for line in lines:
            data = json.loads(line)
            assert "event_id" in data
            assert "event_type" in data
            assert "timestamp" in data

    def test_json_round_trip_preserves_all_fields(self, tmp_path: Path) -> None:
        """Event survives write → read with all fields intact."""
        from specify_cli.telemetry.store import SimpleJsonStore

        store = SimpleJsonStore(tmp_path / "events.jsonl")

        original = make_event(
            event_id="01HX0000000000000000000001",
            event_type="ExecutionEvent",
            aggregate_id="my-feature",
            lamport_clock=42,
            node_id="test-node",
            payload={"model": "claude", "tokens": 100},
        )
        store.save_event(original)

        loaded = store.load_all_events()
        assert len(loaded) == 1
        restored = loaded[0]

        assert restored.event_id == original.event_id
        assert restored.event_type == original.event_type
        assert restored.aggregate_id == original.aggregate_id
        assert restored.lamport_clock == original.lamport_clock
        assert restored.node_id == original.node_id
        assert restored.payload == original.payload
