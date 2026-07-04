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

The fixtures are built through the canonical event producers (C-007 / #1248) —
``emit_mission_created_local`` / ``emit_artifact_phase`` / ``emit_wp_created_local``
for the lifecycle rows and ``emit_decision_opened`` for the Decision-Moment
mirror — rather than hand-assembled ``{event_type, payload}`` dicts. The producers
generate realistic Crockford ULID ``event_id`` values, which the assertions read
back from the on-disk log.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from spec_kitty_events.decisionpoint import DECISION_POINT_OPENED

from specify_cli.decisions.emit import emit_decision_opened
from specify_cli.decisions.models import DecisionStatus, IndexEntry, OriginFlow
from specify_cli.migration.mission_state import _repair_mission
from specify_cli.status.lifecycle_events import (
    SPECIFY_STARTED,
    emit_artifact_phase,
    emit_mission_created_local,
    emit_wp_created_local,
    mission_event_log_path,
)

pytestmark = pytest.mark.integration

_MISSION_ID = "01KWN9D0MJ79NK1T90RWYY2Y7R"
_DECISION_ID = "01KWN9YWCZBHNWQCKSY7EXMQDS"


def _seed_meta(mission_dir: Path) -> None:
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


def _emit_lifecycle_events(mission_dir: Path) -> set[str]:
    """Emit the three canonical lifecycle events; return their ``event_id`` set.

    Uses the durable local-first producers (their *only* per-mission home is
    ``status.events.jsonl``), so the repair MUST preserve every emitted row.
    """
    created = emit_mission_created_local(
        mission_dir,
        mission_slug="m",
        mission_id=_MISSION_ID,
        mission_number=None,
        mission_type="software-dev",
        target_branch="main",
        created_at="2026-07-04T00:45:35+00:00",
    )
    specify = emit_artifact_phase(
        mission_dir,
        event_type=SPECIFY_STARTED,
        mission_slug="m",
        at="2026-07-04T00:46:00+00:00",
    )
    wp = emit_wp_created_local(
        mission_dir,
        mission_slug="m",
        wp_id="WP01",
        wp_title="Decompose the god-module",
        created_at="2026-07-04T00:47:00+00:00",
    )
    assert created is not None
    assert specify is not None
    assert wp is not None
    return {created["event_id"], specify["event_id"], wp["event_id"]}


def _emit_decision_mirror(tmp_path: Path, mission_dir: Path) -> str:
    """Emit a canonical ``DecisionPointOpened`` mirror; return its ``event_id``.

    Its canonical store is ``decisions/``, so the copy in ``status.events.jsonl``
    is a prunable mirror the repair quarantines.
    """
    entry = IndexEntry(
        decision_id=_DECISION_ID,
        origin_flow=OriginFlow.PLAN,
        input_key="merge-strategy",
        question="Which merge strategy for the god-module split?",
        options=("consolidate", "defer"),
        status=DecisionStatus.OPEN,
        created_at=datetime(2026, 7, 4, 0, 55, 20, tzinfo=UTC),
        mission_id=_MISSION_ID,
        mission_slug="m",
        step_id="plan.q1",
    )
    emit_decision_opened(
        tmp_path, "m", decision_id=_DECISION_ID, entry=entry, actor="claude"
    )
    return _find_event_id(mission_event_log_path(mission_dir), DECISION_POINT_OPENED)


def _write_mission(
    tmp_path: Path, *, with_decision: bool
) -> tuple[Path, Path, set[str], str | None]:
    """Seed a mission whose event log is built via canonical producers.

    Returns ``(mission_dir, log, lifecycle_event_ids, decision_event_id)``.
    ``decision_event_id`` is ``None`` when ``with_decision`` is false.
    """
    mission_dir = tmp_path / "kitty-specs" / "m"
    mission_dir.mkdir(parents=True)
    _seed_meta(mission_dir)

    lifecycle_ids = _emit_lifecycle_events(mission_dir)
    decision_id = _emit_decision_mirror(tmp_path, mission_dir) if with_decision else None

    return mission_dir, mission_event_log_path(mission_dir), lifecycle_ids, decision_id


def _find_event_id(log: Path, event_type: str) -> str:
    for line in log.read_text(encoding="utf-8").splitlines():
        obj = json.loads(line)
        if obj.get("event_type") == event_type:
            return str(obj["event_id"])
    raise AssertionError(f"no {event_type} row was written to {log}")


def _event_ids(text: str) -> set[str]:
    return {
        json.loads(line)["event_id"]
        for line in text.splitlines()
        if line.strip()
    }


def test_lifecycle_only_log_is_fully_preserved(tmp_path: Path) -> None:
    """The moov-shaped failure: a log of only canonical lifecycle events must
    survive intact with zero quarantines (it was being emptied to 0 bytes)."""
    mission_dir, log, _lifecycle_ids, _ = _write_mission(tmp_path, with_decision=False)
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
    mission_dir, log, lifecycle_ids, decision_id = _write_mission(
        tmp_path, with_decision=True
    )
    assert decision_id is not None

    result = _repair_mission(tmp_path, mission_dir, run_id="mixed")

    assert result.status != "error", result.validation_errors
    # Only the DecisionPoint mirror is quarantined.
    assert result.quarantined_rows == 1
    surviving = _event_ids(log.read_text(encoding="utf-8"))
    for event_id in lifecycle_ids:
        assert event_id in surviving
    assert decision_id not in surviving


def test_backstop_never_empties_when_all_rows_preserved(tmp_path: Path) -> None:
    """Idempotence + backstop: re-running on a lifecycle-only log is a no-op and
    never empties it."""
    mission_dir, log, lifecycle_ids, _ = _write_mission(tmp_path, with_decision=False)

    _repair_mission(tmp_path, mission_dir, run_id="first")
    first = log.read_text(encoding="utf-8")
    _repair_mission(tmp_path, mission_dir, run_id="second")
    second = log.read_text(encoding="utf-8")

    assert first.strip()
    assert second.strip()
    assert _event_ids(second) == lifecycle_ids
