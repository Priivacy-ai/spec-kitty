#!/usr/bin/env python3
"""CLI-backed integration tests for mission system (per-feature model v0.8.0+).

Tests mission_list/current/info use the 0.x MissionConfig schema.
On 2.x, mission files use v1 State Machine DSL format which MissionConfig
cannot parse. The switch/blocked tests still work on 2.x (they test error paths).
"""

from __future__ import annotations

from pathlib import Path

import pytest

def test_mission_switch_shows_helpful_error(clean_project: Path, run_cli) -> None:
    """Mission switch command should show helpful error about per-feature missions."""
    result = run_cli(clean_project, "mission", "switch", "research")

    # Should fail with exit code 1
    assert result.returncode == 1
    # Should explain that command was removed
    output = result.stdout + result.stderr
    assert "removed" in output.lower() or "v0.8.0" in output.lower()
    # Should point to new workflow
    assert "/spec-kitty.specify" in output


def test_mission_switch_blocked_by_worktrees_via_cli(project_with_worktree: Path, run_cli) -> None:
    """Mission switch should show per-feature error even with worktrees."""
    result = run_cli(project_with_worktree, "mission", "switch", "research")

    # Should fail (v0.8.0+ switch is removed)
    assert result.returncode != 0
    # Should mention the command was removed
    output = result.stdout + result.stderr
    assert "removed" in output.lower() or "/spec-kitty.specify" in output
