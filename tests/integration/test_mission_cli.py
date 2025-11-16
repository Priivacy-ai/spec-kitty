#!/usr/bin/env python3
"""Integration tests for spec-kitty mission CLI commands."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_cli(project_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = REPO_ROOT / "src"
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    command: List[str] = [sys.executable, "-m", "specify_cli.__init__", *args]
    return subprocess.run(
        command,
        cwd=str(project_path),
        capture_output=True,
        text=True,
        env=env,
    )


@pytest.fixture()
def test_project(tmp_path: Path) -> Path:
    """Create a temporary Spec Kitty project with git initialized."""
    project = tmp_path / "project"
    project.mkdir()

    shutil.copytree(
        REPO_ROOT / ".kittify",
        project / ".kittify",
        symlinks=True,
    )

    (project / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")

    subprocess.run(["git", "init"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.email", "ci@example.com"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "Spec Kitty CI"], cwd=project, check=True)
    subprocess.run(["git", "add", "."], cwd=project, check=True)
    subprocess.run(["git", "commit", "-m", "Initial project"], cwd=project, check=True)

    return project


@pytest.fixture()
def clean_project(test_project: Path) -> Path:
    """Return a clean git project with no worktrees."""
    return test_project


@pytest.fixture()
def dirty_project(test_project: Path) -> Path:
    """Return a project containing uncommitted changes."""
    dirty_file = test_project / "dirty.txt"
    dirty_file.write_text("pending changes\n", encoding="utf-8")
    return test_project


@pytest.fixture()
def project_with_worktree(test_project: Path) -> Path:
    """Return a project with simulated active worktree directories."""
    worktree_dir = test_project / ".worktrees" / "001-test-feature"
    worktree_dir.mkdir(parents=True)
    (worktree_dir / "README.md").write_text("feature placeholder\n", encoding="utf-8")
    return test_project


def test_mission_list_shows_available_missions(clean_project: Path) -> None:
    result = _run_cli(clean_project, "mission", "list")
    assert result.returncode == 0
    assert "Software Dev Kitty" in result.stdout
    assert "Deep Research Kitty" in result.stdout


def test_mission_current_shows_active_mission(clean_project: Path) -> None:
    result = _run_cli(clean_project, "mission", "current")
    assert result.returncode == 0
    assert "Active Mission" in result.stdout
    assert "Software Dev Kitty" in result.stdout


def test_mission_info_shows_specific_mission(clean_project: Path) -> None:
    result = _run_cli(clean_project, "mission", "info", "research")
    assert result.returncode == 0
    assert "Mission Details" in result.stdout
    assert "Deep Research Kitty" in result.stdout


def test_mission_switch_succeeds_on_clean_project(clean_project: Path) -> None:
    result = _run_cli(clean_project, "mission", "switch", "research", "--force")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Switched to mission" in result.stdout

    active_marker = clean_project / ".kittify" / "active-mission"
    assert active_marker.exists()
    if active_marker.is_symlink():
        assert "research" in os.readlink(active_marker)
    else:
        contents = active_marker.read_text(encoding="utf-8")
        assert "research" in contents


def test_mission_switch_blocks_when_git_dirty(dirty_project: Path) -> None:
    result = _run_cli(dirty_project, "mission", "switch", "research")
    assert result.returncode == 1
    assert "uncommitted changes" in result.stdout.lower()


def test_mission_switch_blocks_when_worktrees_present(project_with_worktree: Path) -> None:
    result = _run_cli(project_with_worktree, "mission", "switch", "research", "--force")
    assert result.returncode == 1
    assert "active features" in result.stdout.lower()
