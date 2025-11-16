#!/usr/bin/env python3
"""CLI-backed integration tests for mission switching workflows."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_mission_switch_via_cli_happy_path(clean_project: Path, run_cli) -> None:
    """Mission switch command should succeed on clean project via CLI."""
    # Verify starting mission
    result = run_cli(clean_project, "mission", "current")
    assert result.returncode == 0
    assert "Software Dev Kitty" in result.stdout

    # Switch to research via CLI
    result = run_cli(clean_project, "mission", "switch", "research", "--force")
    assert result.returncode == 0
    assert "Switched to mission" in result.stdout.lower() or "research" in result.stdout.lower()

    # Verify switch worked
    result = run_cli(clean_project, "mission", "current")
    assert result.returncode == 0
    assert "Deep Research Kitty" in result.stdout or "research" in result.stdout.lower()


def test_mission_switch_blocked_by_worktrees_via_cli(project_with_worktree: Path, run_cli) -> None:
    """Mission switch should fail when worktrees exist (via CLI)."""
    result = run_cli(project_with_worktree, "mission", "switch", "research")

    assert result.returncode != 0
    # Should mention worktrees or active features in error
    output = result.stdout + result.stderr
    assert "worktree" in output.lower() or "active" in output.lower() or "feature" in output.lower()


def test_mission_switch_blocked_by_dirty_git_via_cli(dirty_project: Path, run_cli) -> None:
    """Mission switch should fail with uncommitted changes (via CLI)."""
    result = run_cli(dirty_project, "mission", "switch", "research")

    assert result.returncode != 0
    # Should mention uncommitted changes
    output = result.stdout + result.stderr
    assert "uncommitted" in output.lower() or "changes" in output.lower() or "commit" in output.lower()


def test_mission_switch_shows_path_warnings_via_cli(clean_project: Path, run_cli) -> None:
    """Mission switch should warn about missing paths via CLI."""
    # Don't create required directories for research mission
    # Switch should warn but succeed
    result = run_cli(clean_project, "mission", "switch", "research", "--force")

    # Should succeed (warnings non-blocking)
    assert result.returncode == 0
    output = (result.stdout + result.stderr).lower()
    assert "path convention warnings" in output or "expects workspace path" in output, "Mission switch did not emit path warnings"

    # May show warnings about missing paths (implementation-dependent)
    # Just verify switch succeeded
    result = run_cli(clean_project, "mission", "current")
    assert "research" in result.stdout.lower()


def test_mission_switch_back_via_cli(clean_project: Path, run_cli) -> None:
    """Should be able to switch back to original mission via CLI."""
    import subprocess

    # Switch to research
    result = run_cli(clean_project, "mission", "switch", "research", "--force")
    assert result.returncode == 0

    # Commit any files created by switch (keeps git clean)
    subprocess.run(["git", "add", "-A"], cwd=clean_project, capture_output=True)
    subprocess.run(["git", "commit", "-m", "After switch"], cwd=clean_project, capture_output=True)

    # Switch back to software-dev
    result = run_cli(clean_project, "mission", "switch", "software-dev", "--force")
    assert result.returncode == 0

    # Verify we're back
    result = run_cli(clean_project, "mission", "current")
    assert "Software Dev Kitty" in result.stdout


def test_mission_list_shows_both_missions(clean_project: Path, run_cli) -> None:
    """Mission list should show all available missions."""
    result = run_cli(clean_project, "mission", "list")

    assert result.returncode == 0
    assert "Software Dev Kitty" in result.stdout
    assert "Deep Research Kitty" in result.stdout
    # Should mark active mission
    assert "✓" in result.stdout or "Active" in result.stdout
