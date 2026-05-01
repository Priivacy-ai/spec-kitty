"""Tests for InvocationWriter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.invocation.errors import AlreadyClosedError, InvocationError, InvocationWriteError
from specify_cli.invocation.record import InvocationRecord
from specify_cli.invocation.writer import EVENTS_DIR, InvocationWriter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_INVOCATION_ID = "01ABCDEFGHJKMNPQRSTVWXYZ12"
_INVOCATION_ID_2 = "01BCDEFGHJKMNPQRSTVWXYZ123"


def _make_record(invocation_id: str = _INVOCATION_ID, **overrides: object) -> InvocationRecord:
    defaults: dict[str, object] = {
        "event": "started",
        "invocation_id": invocation_id,
        "profile_id": "implementer-fixture",
        "action": "generate",
        "request_text": "test request",
        "governance_context_hash": "abcdef0123456789",
        "governance_context_available": True,
        "actor": "claude",
        "started_at": "2026-04-21T12:00:00+00:00",
    }
    defaults.update(overrides)
    return InvocationRecord(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWriteStartedCreatesFile:
    def test_write_started_creates_file(self, tmp_path: Path) -> None:
        writer = InvocationWriter(tmp_path)
        record = _make_record()
        file_path = writer.write_started(record)
        assert file_path.exists()

    def test_write_started_contains_valid_json_line(self, tmp_path: Path) -> None:
        writer = InvocationWriter(tmp_path)
        record = _make_record()
        file_path = writer.write_started(record)
        lines = [line for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["event"] == "started"
        assert data["invocation_id"] == _INVOCATION_ID
        assert data["profile_id"] == "implementer-fixture"

    def test_write_started_creates_events_dir(self, tmp_path: Path) -> None:
        writer = InvocationWriter(tmp_path)
        events_dir = tmp_path / EVENTS_DIR
        assert not events_dir.exists()
        writer.write_started(_make_record())
        assert events_dir.exists()


class TestWriteCompletedAppendsLine:
    def test_write_completed_appends_second_line(self, tmp_path: Path) -> None:
        writer = InvocationWriter(tmp_path)
        record = _make_record()
        writer.write_started(record)
        writer.write_completed(_INVOCATION_ID, tmp_path, outcome="done")
        file_path = writer.invocation_path(_INVOCATION_ID)
        lines = [line for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) == 2
        completed_data = json.loads(lines[1])
        assert completed_data["event"] == "completed"
        assert completed_data["outcome"] == "done"
        assert completed_data["profile_id"] == "implementer-fixture"

    def test_write_completed_returns_completed_record(self, tmp_path: Path) -> None:
        writer = InvocationWriter(tmp_path)
        writer.write_started(_make_record())
        completed = writer.write_completed(_INVOCATION_ID, tmp_path, outcome="done")
        assert completed.event == "completed"
        assert completed.outcome == "done"

    def test_write_completed_reads_profile_id_from_started_event(self, tmp_path: Path) -> None:
        """write_completed reads profile_id from the file's first line (started event)."""
        writer = InvocationWriter(tmp_path)
        writer.write_started(_make_record(profile_id="reviewer-fixture"))
        completed = writer.write_completed(_INVOCATION_ID, tmp_path)
        assert completed.profile_id == "reviewer-fixture"


class TestWriteStartedAppendOnly:
    def test_write_started_mode_is_exclusive_create(self, tmp_path: Path) -> None:
        """A second write_started with the same id raises InvocationWriteError (x mode)."""
        writer = InvocationWriter(tmp_path)
        writer.write_started(_make_record())
        with pytest.raises(InvocationWriteError, match="ULID collision"):
            writer.write_started(_make_record())


class TestWriteStartedCollisionRaises:
    def test_preexisting_file_raises_invocation_write_error(self, tmp_path: Path) -> None:
        writer = InvocationWriter(tmp_path)
        # Pre-create the file manually (simulating collision).
        events_dir = tmp_path / EVENTS_DIR
        events_dir.mkdir(parents=True)
        collision_path = events_dir / f"{_INVOCATION_ID}.jsonl"
        collision_path.write_text("existing content\n", encoding="utf-8")
        with pytest.raises(InvocationWriteError):
            writer.write_started(_make_record())


class TestAlreadyClosed:
    def test_double_complete_raises_already_closed_error(self, tmp_path: Path) -> None:
        writer = InvocationWriter(tmp_path)
        writer.write_started(_make_record())
        writer.write_completed(_INVOCATION_ID, tmp_path, outcome="done")
        with pytest.raises(AlreadyClosedError):
            writer.write_completed(_INVOCATION_ID, tmp_path, outcome="done")

    def test_complete_nonexistent_invocation_raises_invocation_error(self, tmp_path: Path) -> None:
        writer = InvocationWriter(tmp_path)
        with pytest.raises(InvocationError):
            writer.write_completed("no-such-id", tmp_path)


class TestInvocationPathFormat:
    def test_path_is_invocation_id_only(self, tmp_path: Path) -> None:
        """Filename must be <invocation_id>.jsonl — NOT <profile_id>-<invocation_id>.jsonl."""
        writer = InvocationWriter(tmp_path)
        path = writer.invocation_path(_INVOCATION_ID)
        assert path.name == f"{_INVOCATION_ID}.jsonl"
        # Confirm there is no profile_id prefix
        assert "implementer" not in path.name
