#!/usr/bin/env python3
"""CLI-backed integration tests for mission system (per-feature model v0.8.0+)."""

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


def test_mission_list_shows_both_missions_with_source(clean_project: Path, run_cli) -> None:
    """Mission list should show all available missions with source indicators."""
    result = run_cli(clean_project, "mission", "list")

    assert result.returncode == 0
    # Should show mission names
    assert "Software Dev Kitty" in result.stdout or "software-dev" in result.stdout
    assert "Deep Research Kitty" in result.stdout or "research" in result.stdout
    # Should show source column (per-feature model)
    assert "Source" in result.stdout or "project" in result.stdout
    # Should mention per-feature selection
    assert "/spec-kitty.specify" in result.stdout or "per-feature" in result.stdout.lower()


def test_mission_current_shows_default(clean_project: Path, run_cli) -> None:
    """Mission current should show the default mission (software-dev)."""
    result = run_cli(clean_project, "mission", "current")

    assert result.returncode == 0
    assert "Software Dev Kitty" in result.stdout


def test_mission_info_shows_details(clean_project: Path, run_cli) -> None:
    """Mission info should show details for a specific mission."""
    result = run_cli(clean_project, "mission", "info", "research")

    assert result.returncode == 0
    assert "Deep Research Kitty" in result.stdout or "research" in result.stdout.lower()
    # Should show workflow phases
    assert "Phase" in result.stdout or "phase" in result.stdout.lower()
