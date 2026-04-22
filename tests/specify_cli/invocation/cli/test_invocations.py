"""Integration tests for spec-kitty invocations list CLI surface.

Covers:
- Empty log → empty JSON array
- 3 records → 3 results
- --limit 2 with 5 files → at most 2 results
- --profile implementer-fixture filters by content, not filename
- Status: open vs closed shown correctly
- Performance gate: < 200 ms at 10 000 files (NFR-008)
"""

from __future__ import annotations

import datetime
import json
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import app as cli_app
from specify_cli.cli.commands.invocations_cmd import (
    EVENTS_DIR,
    INDEX_PATH,
    _iter_records,
    _read_first_line,
    _read_last_line,
    append_to_index,
)

# Marked for mutmut sandbox skip — subprocess CLI invocation.
pytestmark = pytest.mark.non_sandbox

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_events_dir(base: Path) -> Path:
    events_dir = base / EVENTS_DIR
    events_dir.mkdir(parents=True, exist_ok=True)
    return events_dir


def _write_started(
    events_dir: Path,
    *,
    invocation_id: str,
    profile_id: str = "implementer-fixture",
    action: str = "implement",
    started_at: str | None = None,
) -> Path:
    if started_at is None:
        started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    record = {
        "event": "started",
        "invocation_id": invocation_id,
        "profile_id": profile_id,
        "action": action,
        "started_at": started_at,
    }
    path = events_dir / f"{invocation_id}.jsonl"
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return path


def _write_completed(path: Path, *, invocation_id: str, outcome: str = "done") -> None:
    record = {
        "event": "completed",
        "invocation_id": invocation_id,
        "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "outcome": outcome,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _new_ulid() -> str:
    """Generate a new ULID string using the codebase's available library."""
    import ulid as _ulid_mod  # python-ulid: ULID() generates a new one

    return str(_ulid_mod.ULID())


def create_fixture_invocations(
    events_dir: Path,
    count: int,
    profile_id: str = "implementer-fixture",
    *,
    write_index: bool = True,
) -> None:
    """Create *count* synthetic JSONL files for benchmarking.

    When *write_index* is True (the default) also appends entries to the
    invocation index so the benchmark tests the fast index-based path.
    """
    events_dir.mkdir(parents=True, exist_ok=True)
    # Derive repo_root from events_dir: events_dir = <root>/.kittify/events/profile-invocations
    repo_root = events_dir.parent.parent.parent
    for _ in range(count):
        inv_id = _new_ulid()
        started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        record = {
            "event": "started",
            "invocation_id": inv_id,
            "profile_id": profile_id,
            "action": "implement",
            "started_at": started_at,
        }
        path = events_dir / f"{inv_id}.jsonl"
        path.write_text(json.dumps(record) + "\n", encoding="utf-8")
        if write_index:
            append_to_index(repo_root, record)


# ---------------------------------------------------------------------------
# Unit tests for helpers
# ---------------------------------------------------------------------------


class TestReadFirstLine:
    def test_reads_first_line(self, tmp_path: Path) -> None:
        path = tmp_path / "test.jsonl"
        first = {"event": "started", "invocation_id": "A"}
        second = {"event": "completed", "invocation_id": "A"}
        path.write_text(
            json.dumps(first) + "\n" + json.dumps(second) + "\n",
            encoding="utf-8",
        )
        result = _read_first_line(path)
        assert result is not None
        assert result["event"] == "started"

    def test_returns_none_for_empty_file(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.jsonl"
        path.write_text("", encoding="utf-8")
        assert _read_first_line(path) is None

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        path = tmp_path / "missing.jsonl"
        assert _read_first_line(path) is None


class TestReadLastLine:
    def test_reads_last_line_of_single_line_file(self, tmp_path: Path) -> None:
        path = tmp_path / "single.jsonl"
        record = {"event": "started", "invocation_id": "A"}
        path.write_text(json.dumps(record) + "\n", encoding="utf-8")
        result = _read_last_line(path)
        assert result is not None
        assert result["event"] == "started"

    def test_reads_last_line_of_two_line_file(self, tmp_path: Path) -> None:
        path = tmp_path / "two.jsonl"
        first = {"event": "started", "invocation_id": "A"}
        last = {"event": "completed", "invocation_id": "A"}
        path.write_text(
            json.dumps(first) + "\n" + json.dumps(last) + "\n",
            encoding="utf-8",
        )
        result = _read_last_line(path)
        assert result is not None
        assert result["event"] == "completed"

    def test_returns_none_for_empty_file(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.jsonl"
        path.write_text("", encoding="utf-8")
        assert _read_last_line(path) is None


# ---------------------------------------------------------------------------
# Integration tests via CLI (monkeypatched repo root)
# ---------------------------------------------------------------------------


class TestInvocationsListJSON:
    def test_empty_log_returns_empty_array(self, tmp_path: Path) -> None:
        """Empty log directory → empty JSON array."""
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(
                "specify_cli.cli.commands.invocations_cmd.find_repo_root",
                lambda: tmp_path,
            )
            result = runner.invoke(cli_app, ["invocations", "list", "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data == []

    def test_three_records_returns_three(self, tmp_path: Path) -> None:
        """After creating 3 records, list returns 3."""
        events_dir = _make_events_dir(tmp_path)
        for _ in range(3):
            _write_started(events_dir, invocation_id=_new_ulid())

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(
                "specify_cli.cli.commands.invocations_cmd.find_repo_root",
                lambda: tmp_path,
            )
            result = runner.invoke(cli_app, ["invocations", "list", "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert len(data) == 3

    def test_limit_caps_results(self, tmp_path: Path) -> None:
        """--limit 2 with 5 files returns at most 2 records."""
        events_dir = _make_events_dir(tmp_path)
        for _ in range(5):
            _write_started(events_dir, invocation_id=_new_ulid())

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(
                "specify_cli.cli.commands.invocations_cmd.find_repo_root",
                lambda: tmp_path,
            )
            result = runner.invoke(cli_app, ["invocations", "list", "--limit", "2", "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert len(data) <= 2

    def test_profile_filter_reads_content_not_filename(self, tmp_path: Path) -> None:
        """--profile implementer-fixture filters out reviewer-fixture records.

        Filenames are ``<invocation_id>.jsonl`` with no profile prefix —
        filtering MUST read the ``profile_id`` field from file content.
        """
        events_dir = _make_events_dir(tmp_path)
        # 2 implementer records
        for _ in range(2):
            _write_started(
                events_dir,
                invocation_id=_new_ulid(),
                profile_id="implementer-fixture",
            )
        # 1 reviewer record — same filename pattern, different profile_id in content
        _write_started(
            events_dir,
            invocation_id=_new_ulid(),
            profile_id="reviewer-fixture",
        )

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(
                "specify_cli.cli.commands.invocations_cmd.find_repo_root",
                lambda: tmp_path,
            )
            result = runner.invoke(
                cli_app,
                ["invocations", "list", "--profile", "implementer-fixture", "--json"],
            )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert len(data) == 2
        assert all(r["profile_id"] == "implementer-fixture" for r in data)

    def test_status_open_vs_closed(self, tmp_path: Path) -> None:
        """Closed records carry status=closed; open records carry status=open."""
        events_dir = _make_events_dir(tmp_path)

        open_id = _new_ulid()
        _write_started(events_dir, invocation_id=open_id)

        closed_id = _new_ulid()
        closed_path = _write_started(events_dir, invocation_id=closed_id)
        _write_completed(closed_path, invocation_id=closed_id, outcome="done")

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(
                "specify_cli.cli.commands.invocations_cmd.find_repo_root",
                lambda: tmp_path,
            )
            result = runner.invoke(cli_app, ["invocations", "list", "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        statuses = {r["invocation_id"]: r["status"] for r in data}
        assert statuses[open_id] == "open"
        assert statuses[closed_id] == "closed"

    def test_no_events_dir_returns_empty(self, tmp_path: Path) -> None:
        """When .kittify/events/profile-invocations does not exist, return []."""
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(
                "specify_cli.cli.commands.invocations_cmd.find_repo_root",
                lambda: tmp_path,
            )
            result = runner.invoke(cli_app, ["invocations", "list", "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data == []


# ---------------------------------------------------------------------------
# Performance gate (NFR-008)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_list_performance_10k(tmp_path: Path) -> None:
    """invocations list for 100 records from 10 000 files must complete in < 200 ms.

    This validates NFR-008: the command must not become unusably slow even when
    the audit log has grown to 10 000 JSONL files.

    Uses the index-based path (write_index=True) which is the production path
    when InvocationWriter.write_started() is used.
    """
    events_dir = tmp_path / EVENTS_DIR
    # write_index=True (default) — mimics production InvocationWriter behaviour.
    create_fixture_invocations(events_dir, 10_000, write_index=True)

    start = time.monotonic()
    records = list(_iter_records(events_dir, None, 100, repo_root=tmp_path))
    elapsed = time.monotonic() - start

    assert len(records) == 100, f"Expected 100 records, got {len(records)}"
    assert elapsed < 0.200, (
        f"Performance gate failed: {elapsed:.3f}s (threshold: 0.200s). "
        "The index-based path should meet this threshold — check index I/O."
    )
