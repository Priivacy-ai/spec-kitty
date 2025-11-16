#!/usr/bin/env python3
"""Integration tests for spec-kitty mission CLI commands."""

from __future__ import annotations

from pathlib import Path


def test_mission_list_shows_available_missions(clean_project: Path, run_cli) -> None:
    result = run_cli(clean_project, "mission", "list")
    assert result.returncode == 0
    assert "Software Dev Kitty" in result.stdout
    assert "Deep Research Kitty" in result.stdout


def test_mission_current_shows_active_mission(clean_project: Path, run_cli) -> None:
    result = run_cli(clean_project, "mission", "current")
    assert result.returncode == 0
    assert "Active Mission" in result.stdout
    assert "Software Dev Kitty" in result.stdout


def test_mission_info_shows_specific_mission(clean_project: Path, run_cli) -> None:
    result = run_cli(clean_project, "mission", "info", "research")
    assert result.returncode == 0
    assert "Mission Details" in result.stdout
    assert "Deep Research Kitty" in result.stdout
