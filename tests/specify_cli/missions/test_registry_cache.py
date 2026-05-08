"""Regression tests for MissionRegistry cache fixes (P1 + P2).

P1: Two-level cache — list_missions() must detect status.events.jsonl changes
    without a kitty-specs/ directory mutation (FR-002).

P2: Strong-reference WP registry store — workpackages_for() must return the
    same Python object on repeated calls (FR-003).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _bootstrap_mission(tmp_path: Path) -> tuple[Path, Path]:
    """Create a minimal mission fixture with one WP in 'claimed' lane.

    Returns (mission_dir, events_file).
    """
    mission_dir = tmp_path / "kitty-specs" / "test-mission-01ABCDEF"
    mission_dir.mkdir(parents=True)

    (mission_dir / "meta.json").write_text(
        json.dumps({
            "mission_id": "01ABCDEFGHIJKLMNOPQRSTUVWX",
            "mission_slug": "test-mission-01ABCDEF",
            "friendly_name": "Test",
            "mission_type": "software-dev",
            "target_branch": "main",
        }),
        encoding="utf-8",
    )

    events_file = mission_dir / "status.events.jsonl"
    events_file.write_text(
        json.dumps({
            "event_id": "01A",
            "at": "2026-01-01T00:00:00+00:00",
            "wp_id": "WP01",
            "from_lane": "planned",
            "to_lane": "claimed",
            "actor": "claude",
            "feature_slug": "test-mission-01ABCDEF",
            "force": False,
            "evidence": None,
            "reason": None,
            "review_ref": None,
            "execution_mode": "worktree",
        }, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "WP01-example.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Example\nlane: claimed\n---\n",
        encoding="utf-8",
    )

    return mission_dir, events_file


# ─────────────────────────────────────────────────────────────────────────────
# P1 regression — list_missions() detects status.events.jsonl changes
# ─────────────────────────────────────────────────────────────────────────────


def test_list_missions_reflects_appended_event(tmp_path: Path) -> None:
    """P1: Appending a done event must be visible on the next list_missions() call
    on the same MissionRegistry instance — no stale cache hit.
    """
    from specify_cli.missions.registry import MissionRegistry

    _mission_dir, events_file = _bootstrap_mission(tmp_path)

    registry = MissionRegistry(tmp_path)
    records = registry.list_missions()
    assert len(records) == 1, "expected exactly one mission"
    assert records[0].lane_counts.claimed == 1, "initial: WP01 should be claimed"
    assert records[0].lane_counts.done == 0, "initial: no WPs done"

    # Force a different mtime_ns to guarantee the per-mission cache key changes.
    stat = os.stat(events_file)
    os.utime(events_file, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))

    # Append a done event (write full file to avoid partial-write race).
    existing = events_file.read_text(encoding="utf-8")
    done_event = json.dumps({
        "event_id": "01B",
        "at": "2026-01-01T00:01:00+00:00",
        "wp_id": "WP01",
        "from_lane": "claimed",
        "to_lane": "done",
        "actor": "claude",
        "feature_slug": "test-mission-01ABCDEF",
        "force": False,
        "evidence": None,
        "reason": None,
        "review_ref": None,
        "execution_mode": "worktree",
    }, sort_keys=True) + "\n"
    events_file.write_text(existing + done_event, encoding="utf-8")

    # Same registry instance — must see updated counts (P1 fix).
    records2 = registry.list_missions()
    assert len(records2) == 1
    assert records2[0].lane_counts.done == 1, (
        f"P1: list_missions() returned stale lane counts — "
        f"expected done=1 but got done={records2[0].lane_counts.done}"
    )
    assert records2[0].lane_counts.claimed == 0, (
        f"P1: claimed should be 0 after WP01 moved to done, got {records2[0].lane_counts.claimed}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# P2 regression — workpackages_for() returns the same instance
# ─────────────────────────────────────────────────────────────────────────────


def test_workpackages_for_returns_same_instance(tmp_path: Path) -> None:
    """P2: workpackages_for() called twice with the same mission_id must return
    the exact same Python object (identity check), confirming the strong-reference
    store replaced the WeakValueDictionary.
    """
    from specify_cli.missions.registry import MissionRegistry

    _mission_dir, _events_file = _bootstrap_mission(tmp_path)

    registry = MissionRegistry(tmp_path)
    registry.list_missions()  # warm the cache

    mission_id = "01ABCDEFGHIJKLMNOPQRSTUVWX"
    wp_reg1 = registry.workpackages_for(mission_id)
    wp_reg2 = registry.workpackages_for(mission_id)

    assert wp_reg1 is not None, "workpackages_for() returned None"
    assert wp_reg1 is wp_reg2, (
        "P2: workpackages_for() returned different instances — "
        "WeakValueDictionary GC'd the registry between calls"
    )
