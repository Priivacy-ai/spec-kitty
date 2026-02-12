"""Shared fixtures for end-to-end CLI smoke tests.

These tests exercise the full spec-kitty workflow via subprocess calls
against a temporary git repository, verifying that the CLI commands
compose correctly end-to-end.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Callable

import pytest
import yaml

from tests.test_isolation_helpers import get_installed_version, get_venv_python

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def isolated_env() -> dict[str, str]:
    """Create isolated environment blocking host spec-kitty installation.

    Ensures tests use source code exclusively via:
    - PYTHONPATH set to source only (no inheritance)
    - SPEC_KITTY_CLI_VERSION from pyproject.toml
    - SPEC_KITTY_TEST_MODE=1 to enforce test behavior
    - SPEC_KITTY_TEMPLATE_ROOT to source templates
    """
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    source_version = pyproject["project"]["version"]

    src_path = REPO_ROOT / "src"
    env["PYTHONPATH"] = str(src_path)
    env["SPEC_KITTY_CLI_VERSION"] = source_version
    env["SPEC_KITTY_TEST_MODE"] = "1"
    env["SPEC_KITTY_TEMPLATE_ROOT"] = str(REPO_ROOT)

    return env


@pytest.fixture()
def run_cli(isolated_env: dict[str, str]) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Return a helper that executes the Spec Kitty CLI within a project.

    Uses isolated_env to guarantee tests run against source code, not
    installed packages.
    """

    def _run_cli(project_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
        command = [str(get_venv_python()), "-m", "specify_cli.__init__", *args]
        return subprocess.run(
            command,
            cwd=str(project_path),
            capture_output=True,
            text=True,
            env=isolated_env,
            timeout=60,
        )

    return _run_cli


@pytest.fixture()
def e2e_project(tmp_path: Path) -> Path:
    """Create a temporary Spec Kitty project with git and .kittify initialized.

    This is the foundation fixture for E2E tests. It:
    - Copies .kittify from the real repo root
    - Copies missions from src/specify_cli/missions/
    - Initializes git with main branch and initial commit
    - Aligns metadata version with source to avoid mismatch errors
    """
    project = tmp_path / "e2e-project"
    project.mkdir()

    # Copy .kittify structure from the real repo
    shutil.copytree(
        REPO_ROOT / ".kittify",
        project / ".kittify",
        symlinks=True,
    )

    # Copy missions from source location
    missions_src = REPO_ROOT / "src" / "specify_cli" / "missions"
    missions_dest = project / ".kittify" / "missions"
    if missions_src.exists() and not missions_dest.exists():
        shutil.copytree(missions_src, missions_dest)

    # Create .gitignore
    (project / ".gitignore").write_text(
        "__pycache__/\n.worktrees/\n",
        encoding="utf-8",
    )

    # Initialize git
    subprocess.run(["git", "init", "-b", "main"], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "e2e@example.com"],
        cwd=project, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "E2E Test"],
        cwd=project, check=True, capture_output=True,
    )
    subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial project"],
        cwd=project, check=True, capture_output=True,
    )

    # Align metadata version with source to avoid version mismatch errors
    metadata_file = project / ".kittify" / "metadata.yaml"
    if metadata_file.exists():
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = yaml.safe_load(f) or {}

        current_version = get_installed_version()
        if current_version is None:
            with open(REPO_ROOT / "pyproject.toml", "rb") as f:
                pyproject = tomllib.load(f)
            current_version = pyproject["project"]["version"] or "unknown"

        if "spec_kitty" not in metadata:
            metadata["spec_kitty"] = {}
        metadata["spec_kitty"]["version"] = current_version

        with open(metadata_file, "w", encoding="utf-8") as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)

        # Commit the version update
        subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Align metadata version", "--allow-empty"],
            cwd=project, check=True, capture_output=True,
        )

    # Create a minimal source directory for realism
    src_dir = project / "src"
    src_dir.mkdir()
    (src_dir / "__init__.py").write_text("", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add source skeleton"],
        cwd=project, check=True, capture_output=True,
    )

    return project
