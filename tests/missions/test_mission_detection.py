"""Tests for mission detection (issue #93 fix)."""



import pytest
from specify_cli.cli.commands.mission_type import _detect_current_mission

pytestmark = pytest.mark.fast

def test_detect_current_mission_from_kitty_specs(tmp_path, monkeypatch):
    """Test _detect_current_mission from kitty-specs directory."""
    # Create kitty-specs/001-research/ directory
    mission_dir = tmp_path / "kitty-specs" / "001-research"
    mission_dir.mkdir(parents=True)

    # Change to the mission directory
    monkeypatch.chdir(mission_dir)

    # Should detect "001-research"
    result = _detect_current_mission(tmp_path)
    assert result == "001-research"


def test_detect_current_mission_from_worktree(tmp_path, monkeypatch):
    """Test _detect_current_mission from worktree."""
    # Create kitty-specs/001-research/ directory (mission must exist for validation)
    mission_dir = tmp_path / "kitty-specs" / "001-research"
    mission_dir.mkdir(parents=True)

    # Create .worktrees/001-research-WP01/ directory
    worktree_dir = tmp_path / ".worktrees" / "001-research-WP01"
    worktree_dir.mkdir(parents=True)

    # Change to the worktree directory
    monkeypatch.chdir(worktree_dir)

    # Should detect "001-research" (WP## suffix removed)
    result = _detect_current_mission(tmp_path)
    assert result == "001-research"


def test_detect_current_mission_from_worktree_no_wp_suffix(tmp_path, monkeypatch):
    """Test _detect_current_mission from worktree without WP suffix."""
    # Create kitty-specs/001-research/ directory (mission must exist for validation)
    mission_dir = tmp_path / "kitty-specs" / "001-research"
    mission_dir.mkdir(parents=True)

    # Create .worktrees/001-research/ directory (no WP## suffix)
    worktree_dir = tmp_path / ".worktrees" / "001-research"
    worktree_dir.mkdir(parents=True)

    # Change to the worktree directory
    monkeypatch.chdir(worktree_dir)

    # Should detect "001-research"
    result = _detect_current_mission(tmp_path)
    assert result == "001-research"


def test_detect_current_mission_from_project_root(tmp_path, monkeypatch):
    """Test _detect_current_mission from project root."""
    # Change to project root (no kitty-specs or .worktrees in path)
    monkeypatch.chdir(tmp_path)

    # Should return None (no mission context)
    result = _detect_current_mission(tmp_path)
    assert result is None


def test_detect_current_mission_from_nested_kitty_specs(tmp_path, monkeypatch):
    """Test _detect_current_mission from nested path in kitty-specs."""
    # Create kitty-specs/001-research/tasks/ directory
    tasks_dir = tmp_path / "kitty-specs" / "001-research" / "tasks"
    tasks_dir.mkdir(parents=True)

    # Change to the tasks directory
    monkeypatch.chdir(tasks_dir)

    # Should detect "001-research" (immediate child of kitty-specs)
    result = _detect_current_mission(tmp_path)
    assert result == "001-research"


def test_detect_current_mission_handles_exceptions(tmp_path, monkeypatch):
    """Test _detect_current_mission handles exceptions gracefully."""
    # Create a directory that will cause cwd() to fail (simulate error)
    # This is hard to trigger in practice, but test the exception handling

    # For this test, just verify it doesn't crash with unusual paths
    unusual_dir = tmp_path / "some" / "unusual" / "path"
    unusual_dir.mkdir(parents=True)
    monkeypatch.chdir(unusual_dir)

    # Should return None (no kitty-specs or .worktrees)
    result = _detect_current_mission(tmp_path)
    assert result is None
