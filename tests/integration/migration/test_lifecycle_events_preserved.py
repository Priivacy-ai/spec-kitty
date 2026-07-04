"""Regression: mission-state repair preserves canonical lifecycle events (#2376).

A completed mission's ``status.events.jsonl`` legitimately holds canonical
lifecycle events (``MissionCreated``, ``SpecifyStarted``, ``WPCreated``) whose
*only* per-mission home is this file (see
:mod:`specify_cli.status.lifecycle_events`). The repair previously quarantined
all ``event_type`` rows and emptied such a log. This test pins the corrected
contract: canonical lifecycle events are preserved in place; the log is never
emptied.

Decision-Moment rows (``DecisionPoint*``) are intentionally NOT preserved here —
their canonical store is ``decisions/index.json`` / ``DM-*.md``, so the copy in
status.events.jsonl is a prunable mirror (the shipped #980 behaviour, retained).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.migration.mission_state import _repair_mission

pytestmark = pytest.mark.integration

_MISSION_ID = "01KWN9D0MJ79NK1T90RWYY2Y7R"

# Canonical lifecycle events (event_type in LIFECYCLE_EVENT_TYPES) — no other
# per-mission home, so the repair MUST preserve them.
_LIFECYCLE_ROWS: list[dict] = [
    {
        "event_id": "01KWN9D17PATBTWVQCEEYDE7PW",
        "event_type": "MissionCreated",
        "aggregate_id": _MISSION_ID,
        "aggregate_type": "Mission",
        "schema_version": "5.0.0",
        "timestamp": "2026-07-04T00:45:35+00:00",
        "payload": {"mission_slug": "m"},
    },
    {
        "event_id": "01KWN9D2000000000000000001",
        "event_type": "SpecifyStarted",
        "aggregate_id": _MISSION_ID,
        "aggregate_type": "Mission",
        "schema_version": "5.0.0",
        "timestamp": "2026-07-04T00:46:00+00:00",
        "payload": {"mission_slug": "m"},
    },
    {
        "event_id": "01KWN9D3000000000000000002",
        "event_type": "WPCreated",
        "aggregate_id": "WP01",
        "aggregate_type": "WorkPackage",
        "schema_version": "5.0.0",
        "timestamp": "2026-07-04T00:47:00+00:00",
        "payload": {"mission_slug": "m", "wp_id": "WP01"},
    },
]

# Decision-Moment mirror row — canonical store is decisions/, so pruned.
_DECISION_ROW = {
    "event_id": "01KWN9YWCZBHNWQCKSY7EXMQDS",
    "event_type": "DecisionPointOpened",
    "at": "2026-07-04T00:55:20+00:00",
    "payload": {"decision_point_id": "d1", "mission_slug": "m"},
}


def _write_mission(tmp_path: Path, rows: list[dict]) -> tuple[Path, Path]:
    mission_dir = tmp_path / "kitty-specs" / "m"
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": "m",
                "mission_id": _MISSION_ID,
                "mission_type": "software-dev",
                "target_branch": "main",
                "created_at": "2026-07-04T00:45:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    log = mission_dir / "status.events.jsonl"
    log.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    return mission_dir, log


def _event_ids(text: str) -> set[str]:
    return {
        json.loads(line)["event_id"]
        for line in text.splitlines()
        if line.strip()
    }


def test_lifecycle_only_log_is_fully_preserved(tmp_path: Path) -> None:
    """The moov-shaped failure: a log of only canonical lifecycle events must
    survive intact with zero quarantines (it was being emptied to 0 bytes)."""
    mission_dir, log = _write_mission(tmp_path, list(_LIFECYCLE_ROWS))
    before_ids = _event_ids(log.read_text(encoding="utf-8"))

    result = _repair_mission(tmp_path, mission_dir, run_id="lifecycle-only")

    assert result.status != "error", result.validation_errors
    assert result.quarantined_rows == 0
    after_text = log.read_text(encoding="utf-8")
    assert after_text.strip(), "repair must not empty a lifecycle-only log"
    assert _event_ids(after_text) == before_ids


def test_lifecycle_preserved_decision_mirror_pruned(tmp_path: Path) -> None:
    """Mixed log: lifecycle events preserved; the DecisionPoint mirror is pruned
    (its canonical store is decisions/), and the log is not emptied."""
    mission_dir, log = _write_mission(
        tmp_path, [*_LIFECYCLE_ROWS, _DECISION_ROW]
    )

    result = _repair_mission(tmp_path, mission_dir, run_id="mixed")

    assert result.status != "error", result.validation_errors
    # Only the DecisionPoint mirror is quarantined.
    assert result.quarantined_rows == 1
    surviving = _event_ids(log.read_text(encoding="utf-8"))
    for row in _LIFECYCLE_ROWS:
        assert row["event_id"] in surviving
    assert _DECISION_ROW["event_id"] not in surviving


def test_backstop_never_empties_when_all_rows_preserved(tmp_path: Path) -> None:
    """Idempotence + backstop: re-running on a lifecycle-only log is a no-op and
    never empties it."""
    mission_dir, log = _write_mission(tmp_path, list(_LIFECYCLE_ROWS))

    _repair_mission(tmp_path, mission_dir, run_id="first")
    first = log.read_text(encoding="utf-8")
    _repair_mission(tmp_path, mission_dir, run_id="second")
    second = log.read_text(encoding="utf-8")

    assert first.strip()
    assert second.strip()
    assert _event_ids(second) == {row["event_id"] for row in _LIFECYCLE_ROWS}
