#!/usr/bin/env python3
"""Integration tests for spec-kitty mission CLI commands."""

from __future__ import annotations

from pathlib import Path


def test_mission_list_shows_available_missions(clean_project: Path, run_cli) -> None:
    result = run_cli(clean_project, "mission", "list")
    assert result.returncode == 0
    # Rich table may wrap names across lines, so check key words individually
    assert "Software" in result.stdout and "Dev" in result.stdout and "Kitty" in result.stdout
    assert "Deep" in result.stdout and "Research" in result.stdout


def test_mission_current_shows_active_mission(clean_project: Path, run_cli) -> None:
    result = run_cli(clean_project, "mission", "current")
    assert result.returncode == 0
    assert "Active Mission" in result.stdout
    # Rich may wrap mission name across lines
    assert "Software" in result.stdout and "Dev" in result.stdout


def test_mission_info_shows_specific_mission(clean_project: Path, run_cli) -> None:
    result = run_cli(clean_project, "mission", "info", "research")
    assert result.returncode == 0
    assert "Mission Details" in result.stdout
    # Rich may wrap mission name across lines
    assert "Deep" in result.stdout and "Research" in result.stdout
