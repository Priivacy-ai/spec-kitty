#!/usr/bin/env python3
"""Integration tests for spec-kitty mission CLI commands.

These tests use the 0.x MissionConfig schema which expects traditional
mission.yaml format. On 2.x, mission files use the v1 State Machine DSL
format (from feature 037) which MissionConfig cannot parse.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.branch_contract import IS_2X_BRANCH, LEGACY_0X_ONLY_REASON

pytestmark = pytest.mark.skipif(IS_2X_BRANCH, reason=LEGACY_0X_ONLY_REASON)


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
