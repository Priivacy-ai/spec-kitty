"""Tests for LamportClock persistence and operations (T037).

Covers:
- tick() increments
- receive() updates to max
- JSON persistence (save/load)
- Atomic write (temp file + rename)
- Missing file initialises value=0
- Corrupt file recovery
- generate_node_id() stability
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from specify_cli.sync.clock import LamportClock, generate_node_id


class TestTick:
    """Test LamportClock.tick()."""

    def test_tick_increments_value(self, tmp_path: Path):
        """tick() returns incremented value."""
        clock = LamportClock(value=0, node_id="test", _storage_path=tmp_path / "c.json")
        assert clock.tick() == 1
        assert clock.tick() == 2
        assert clock.value == 2

    def test_tick_from_nonzero(self, tmp_path: Path):
        """tick() works from a nonzero starting value."""
        clock = LamportClock(value=99, node_id="test", _storage_path=tmp_path / "c.json")
        assert clock.tick() == 100

    def test_tick_persists(self, tmp_path: Path):
        """tick() persists the value to disk."""
        path = tmp_path / "c.json"
        clock = LamportClock(value=0, node_id="test", _storage_path=path)
        clock.tick()
        clock.tick()

        data = json.loads(path.read_text())
        assert data["value"] == 2


class TestReceive:
    """Test LamportClock.receive()."""

    def test_receive_updates_to_max_plus_one(self, tmp_path: Path):
        """receive() updates to max(local, remote) + 1."""
        clock = LamportClock(value=5, node_id="test", _storage_path=tmp_path / "c.json")
        result = clock.receive(10)
        assert result == 11
        assert clock.value == 11

    def test_receive_when_local_is_higher(self, tmp_path: Path):
        """receive() still increments when local > remote."""
        clock = LamportClock(value=20, node_id="test", _storage_path=tmp_path / "c.json")
        result = clock.receive(5)
        assert result == 21
        assert clock.value == 21

    def test_receive_when_equal(self, tmp_path: Path):
        """receive() increments when local == remote."""
        clock = LamportClock(value=10, node_id="test", _storage_path=tmp_path / "c.json")
        result = clock.receive(10)
        assert result == 11

    def test_receive_persists(self, tmp_path: Path):
        """receive() persists the updated value."""
        path = tmp_path / "c.json"
        clock = LamportClock(value=5, node_id="test", _storage_path=path)
        clock.receive(100)

        data = json.loads(path.read_text())
        assert data["value"] == 101


class TestPersistence:
    """Test save/load roundtrip."""

    def test_save_creates_file(self, tmp_path: Path):
        """save() creates the JSON file."""
        path = tmp_path / "c.json"
        clock = LamportClock(value=42, node_id="test123", _storage_path=path)
        clock.save()
        assert path.exists()

    def test_save_load_roundtrip(self, tmp_path: Path):
        """save() then load() preserves value and node_id."""
        path = tmp_path / "c.json"
        clock1 = LamportClock(value=42, node_id="test123", _storage_path=path)
        clock1.save()

        clock2 = LamportClock.load(path)
        assert clock2.value == 42
        assert clock2.node_id == "test123"

    def test_save_includes_updated_at(self, tmp_path: Path):
        """Saved JSON includes updated_at timestamp."""
        path = tmp_path / "c.json"
        clock = LamportClock(value=0, node_id="test", _storage_path=path)
        clock.save()

        data = json.loads(path.read_text())
        assert "updated_at" in data
        assert "T" in data["updated_at"]  # ISO format

    def test_load_creates_parent_directories(self, tmp_path: Path):
        """save() creates parent directories as needed."""
        path = tmp_path / "deep" / "nested" / "clock.json"
        clock = LamportClock(value=5, node_id="test", _storage_path=path)
        clock.save()
        assert path.exists()


class TestAtomicWrite:
    """Test atomic write behaviour."""

    def test_no_partial_writes(self, tmp_path: Path):
        """Save uses temp file + rename to avoid partial writes."""
        path = tmp_path / "c.json"
        clock = LamportClock(value=0, node_id="test", _storage_path=path)

        # Do many rapid saves
        for i in range(100):
            clock.value = i
            clock.save()

        # Final value should be consistent
        data = json.loads(path.read_text())
        assert data["value"] == 99

    def test_no_temp_files_left(self, tmp_path: Path):
        """No .tmp files left after save."""
        path = tmp_path / "c.json"
        clock = LamportClock(value=0, node_id="test", _storage_path=path)
        clock.save()

        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_save_cleans_up_temp_on_failure(self, tmp_path: Path, monkeypatch):
        """Temp file is removed if atomic replace fails."""
        path = tmp_path / "c.json"
        clock = LamportClock(value=0, node_id="test", _storage_path=path)

        def fail_replace(_src, _dst):
            raise OSError("replace failed")

        monkeypatch.setattr(os, "replace", fail_replace)

        with pytest.raises(OSError):
            clock.save()

        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0


class TestMissingFile:
    """Test load() with missing or corrupt files."""

    def test_missing_file_initializes_zero(self, tmp_path: Path):
        """Missing clock file initializes with value=0."""
        path = tmp_path / "nonexistent.json"
        clock = LamportClock.load(path)
        assert clock.value == 0

    def test_corrupt_json_initializes_zero(self, tmp_path: Path):
        """Corrupt JSON file initializes with value=0."""
        path = tmp_path / "corrupt.json"
        path.write_text("{invalid json")

        clock = LamportClock.load(path)
        assert clock.value == 0

    def test_empty_file_initializes_zero(self, tmp_path: Path):
        """Empty file initializes with value=0."""
        path = tmp_path / "empty.json"
        path.write_text("")

        clock = LamportClock.load(path)
        assert clock.value == 0

    def test_load_default_path(self):
        """load() without path uses default ~/.spec-kitty/clock.json."""
        # Just test it doesn't raise
        clock = LamportClock.load()
        assert isinstance(clock, LamportClock)


class TestGenerateNodeId:
    """Test generate_node_id()."""

    def test_returns_12_char_hex(self):
        """Node ID is 12 hex characters."""
        nid = generate_node_id()
        assert len(nid) == 12
        assert all(c in "0123456789abcdef" for c in nid)

    def test_stable_across_calls(self):
        """Same machine returns same node_id."""
        assert generate_node_id() == generate_node_id()

    def test_default_node_id_matches(self, tmp_path: Path):
        """Default node_id in clock matches generate_node_id()."""
        clock = LamportClock(_storage_path=tmp_path / "c.json")
        assert clock.node_id == generate_node_id()
