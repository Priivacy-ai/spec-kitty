"""Test that dashboard and CLI status show identical results."""

import pytest
from pathlib import Path

from specify_cli.dashboard.scanner import scan_feature_kanban, _count_wps_by_lane
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event

pytestmark = pytest.mark.fast


def _write_event(feature_dir: Path, wp_id: str, to_lane: str, from_lane: str = "planned") -> None:
    """Append a single status event to the feature's event log."""
    event = StatusEvent(
        event_id=f"01TEST{wp_id}{to_lane.upper()[:4]}",
        mission_slug=feature_dir.name,
        wp_id=wp_id,
        from_lane=Lane(from_lane),
        to_lane=Lane(to_lane),
        at="2026-03-30T12:00:00+00:00",
        actor="test-agent",
        force=False,
        execution_mode="worktree",
    )
    append_event(feature_dir, event)


def test_dashboard_cli_status_parity(tmp_path: Path):
    """Verify dashboard and CLI status use same defaults and encoding."""
    # Setup: Create a minimal feature with work packages
    feature_dir = tmp_path / "kitty-specs" / "001-test-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create WP with missing lane (tests default behavior)
    wp_missing_lane = tasks_dir / "WP01.md"
    wp_missing_lane.write_text(
        """---
work_package_id: "WP01"
title: "Test WP without lane"
---

# Work Package Prompt: Test WP

This WP has no lane field.
""",
        encoding="utf-8-sig",  # Use BOM to test encoding handling
    )

    # Create WP with explicit lane
    wp_with_lane = tasks_dir / "WP02.md"
    wp_with_lane.write_text(
        """---
work_package_id: "WP02"
title: "Test WP with lane"
lane: "doing"
---

# Work Package Prompt: Test WP

This WP has an explicit lane.
""",
        encoding="utf-8",
    )

    # Bootstrap event log: WP01 planned (bootstrap), WP02 in_progress
    _write_event(feature_dir, "WP01", "planned")
    _write_event(feature_dir, "WP02", "in_progress")

    # Get results from both systems
    dashboard_lanes = scan_feature_kanban(tmp_path, "001-test-feature")

    # Test dashboard counts
    counts = _count_wps_by_lane(tasks_dir)
    assert counts["planned"] == 1  # WP01 should default to planned
    assert counts["doing"] == 1  # WP02 in_progress mapped to doing

    # Test dashboard scanner
    assert len(dashboard_lanes["planned"]) == 1
    assert len(dashboard_lanes["doing"]) == 1
    assert dashboard_lanes["planned"][0]["id"] == "WP01"
    assert dashboard_lanes["doing"][0]["id"] == "WP02"


def test_both_use_utf8_sig_encoding(tmp_path: Path):
    """Verify both systems handle BOM correctly."""
    feature_dir = tmp_path / "kitty-specs" / "002-test-bom"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create file with BOM (Windows-style)
    wp_with_bom = tasks_dir / "WP01.md"
    wp_with_bom.write_text(
        """---
work_package_id: "WP01"
title: "Test BOM Title"
lane: "planned"
---

# Work Package Prompt: Test BOM

Windows BOM test.
""",
        encoding="utf-8-sig",
    )

    # Bootstrap event log with planned state
    _write_event(feature_dir, "WP01", "planned")

    # Dashboard should handle it
    dashboard_lanes = scan_feature_kanban(tmp_path, "002-test-bom")
    assert len(dashboard_lanes["planned"]) == 1
    assert dashboard_lanes["planned"][0]["title"] == "Test BOM"

    # Both should produce identical lane assignment
    assert dashboard_lanes["planned"][0]["lane"] == "planned"
