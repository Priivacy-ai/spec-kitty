#!/usr/bin/env python3
"""Legacy mission-list/current/info coverage for the 1.x mission schema."""

from __future__ import annotations

from pathlib import Path


def test_mission_list_shows_both_missions_with_source(clean_project: Path, run_cli) -> None:
    """Mission list should show all available missions with source indicators."""
    result = run_cli(clean_project, "mission", "list")

    assert result.returncode == 0
    assert "Software Dev Kitty" in result.stdout or "software-dev" in result.stdout
    assert "Deep Research Kitty" in result.stdout or "research" in result.stdout
    assert "Source" in result.stdout or "project" in result.stdout
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
    assert "Phase" in result.stdout or "phase" in result.stdout.lower()
