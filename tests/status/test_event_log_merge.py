"""Tests for semantic merging of status.events.jsonl files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import app as cli_app
from specify_cli.status.event_log_merge import (
    EventLogMergeError,
    merge_event_log_files,
    merge_event_payloads,
)

pytestmark = pytest.mark.fast

runner = CliRunner()


def _event(event_id: str, at: str, wp_id: str = "WP01") -> dict[str, object]:
    return {
        "actor": "tester",
        "at": at,
        "event_id": event_id,
        "execution_mode": "worktree",
        "force": False,
        "from_lane": "planned",
        "mission_slug": "079-post-555-release-hardening",
        "reason": None,
        "review_ref": None,
        "to_lane": "claimed",
        "wp_id": wp_id,
    }


def _write_jsonl(path: Path, payloads: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(payload, sort_keys=True) + "\n" for payload in payloads),
        encoding="utf-8",
    )


def test_merge_event_payloads_deduplicates_and_sorts() -> None:
    base = [_event("01AAA000000000000000000001", "2026-04-09T06:00:00Z")]
    ours = [_event("01BBB000000000000000000002", "2026-04-09T06:02:00Z")]
    theirs = [
        _event("01AAA000000000000000000001", "2026-04-09T06:00:00Z"),
        _event("01CCC000000000000000000003", "2026-04-09T06:01:00Z"),
    ]

    merged = merge_event_payloads(base, ours, theirs)

    assert [payload["event_id"] for payload in merged] == [
        "01AAA000000000000000000001",
        "01CCC000000000000000000003",
        "01BBB000000000000000000002",
    ]


def test_merge_event_payloads_rejects_conflicting_duplicate_event_id() -> None:
    original = _event("01DDD000000000000000000004", "2026-04-09T06:00:00Z")
    conflicting = dict(original)
    conflicting["to_lane"] = "blocked"

    with pytest.raises(EventLogMergeError, match="Conflicting payloads"):
        merge_event_payloads([original], [conflicting])


def test_merge_event_log_files_writes_union_to_output_path(tmp_path: Path) -> None:
    base_path = tmp_path / "base.jsonl"
    ours_path = tmp_path / "ours.jsonl"
    theirs_path = tmp_path / "theirs.jsonl"
    output_path = tmp_path / "merged.jsonl"

    _write_jsonl(base_path, [_event("01AAA000000000000000000001", "2026-04-09T06:00:00Z")])
    _write_jsonl(ours_path, [_event("01BBB000000000000000000002", "2026-04-09T06:01:00Z")])
    _write_jsonl(theirs_path, [_event("01CCC000000000000000000003", "2026-04-09T06:02:00Z")])

    merge_event_log_files(
        base_path=base_path,
        ours_path=ours_path,
        theirs_path=theirs_path,
        output_path=output_path,
    )

    lines = output_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert [json.loads(line)["event_id"] for line in lines] == [
        "01AAA000000000000000000001",
        "01BBB000000000000000000002",
        "01CCC000000000000000000003",
    ]


def test_merge_driver_event_log_cli_reports_validation_errors(tmp_path: Path) -> None:
    base_path = tmp_path / "base.jsonl"
    ours_path = tmp_path / "ours.jsonl"
    theirs_path = tmp_path / "theirs.jsonl"
    _write_jsonl(base_path, [_event("01AAA000000000000000000001", "2026-04-09T06:00:00Z")])
    ours_path.write_text("{bad json}\n", encoding="utf-8")
    _write_jsonl(theirs_path, [_event("01BBB000000000000000000002", "2026-04-09T06:01:00Z")])

    result = runner.invoke(
        cli_app,
        [
            "merge-driver-event-log",
            str(base_path),
            str(ours_path),
            str(theirs_path),
        ],
    )

    assert result.exit_code == 1
    assert "invalid JSON" in result.output
