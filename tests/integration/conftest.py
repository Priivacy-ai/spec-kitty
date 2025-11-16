from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def run_cli() -> Callable[[Path, str], subprocess.CompletedProcess[str]]:
    """Return a helper that executes the Spec Kitty CLI within a project."""

    def _run_cli(project_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        src_path = REPO_ROOT / "src"
        env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
        # Ensure CLI can resolve bundled templates when running from source checkout
        env.setdefault("SPEC_KITTY_TEMPLATE_ROOT", str(REPO_ROOT))
        command = [sys.executable, "-m", "specify_cli.__init__", *args]
        return subprocess.run(
            command,
            cwd=str(project_path),
            capture_output=True,
            text=True,
            env=env,
        )

    return _run_cli


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
