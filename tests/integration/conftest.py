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

    This fixture guarantees that tests will never accidentally use a
    pip-installed version of spec-kitty-cli from the host system.
    """
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    # Single source of truth: pyproject.toml
    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    source_version = pyproject["project"]["version"]

    # Isolation settings
    src_path = REPO_ROOT / "src"
    env["PYTHONPATH"] = str(src_path)  # Source only, no existing PYTHONPATH
    env["SPEC_KITTY_CLI_VERSION"] = source_version  # Override version detection
    env["SPEC_KITTY_TEST_MODE"] = "1"  # Signal test mode (fail-fast on fixture bugs)
    env["SPEC_KITTY_TEMPLATE_ROOT"] = str(REPO_ROOT)  # Find bundled templates

    return env


@pytest.fixture()
def run_cli(isolated_env: dict[str, str]) -> Callable[[Path, str], subprocess.CompletedProcess[str]]:
    """Return a helper that executes the Spec Kitty CLI within a project.

    Uses isolated_env to guarantee tests run against source code, not
    installed packages. This prevents version mismatch errors.
    """

    def _run_cli(project_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
        command = [str(get_venv_python()), "-m", "specify_cli.__init__", *args]
        return subprocess.run(
            command,
            cwd=str(project_path),
            capture_output=True,
            text=True,
            env=isolated_env,
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

    # Copy missions from new location (src/specify_cli/missions/ -> .kittify/missions/)
    missions_src = REPO_ROOT / "src" / "specify_cli" / "missions"
    missions_dest = project / ".kittify" / "missions"
    if missions_src.exists():
        shutil.copytree(missions_src, missions_dest, dirs_exist_ok=True)

    (project / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")

    subprocess.run(["git", "init", "-b", "main"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.email", "ci@example.com"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "Spec Kitty CI"], cwd=project, check=True)
    subprocess.run(["git", "add", "."], cwd=project, check=True)
    subprocess.run(["git", "commit", "-m", "Initial project"], cwd=project, check=True)

    # Update metadata.yaml to current version to avoid version mismatch errors
    metadata_file = project / ".kittify" / "metadata.yaml"
    if metadata_file.exists():
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = yaml.safe_load(f) or {}

        # Align project version with the CLI version used by tests.
        current_version = get_installed_version()
        if current_version is None:
            with open(REPO_ROOT / "pyproject.toml", "rb") as f:
                pyproject = tomllib.load(f)
            current_version = pyproject["project"]["version"] or "unknown"

        # Update version in nested spec_kitty.version structure
        if "spec_kitty" not in metadata:
            metadata["spec_kitty"] = {}
        metadata["spec_kitty"]["version"] = current_version

        with open(metadata_file, "w", encoding="utf-8") as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)

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


@pytest.fixture()
def dual_branch_repo(tmp_path: Path) -> Path:
    """Create test repo with both main and 2.x branches.

    Returns a repository with:
    - main branch (initial commit)
    - 2.x branch (branched from main)
    - .kittify/ structure initialized
    - Git configured for tests
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    # Copy .kittify structure
    shutil.copytree(
        REPO_ROOT / ".kittify",
        repo / ".kittify",
        symlinks=True,
    )

    # Copy missions
    missions_src = REPO_ROOT / "src" / "specify_cli" / "missions"
    missions_dest = repo / ".kittify" / "missions"
    if missions_src.exists() and not missions_dest.exists():
        shutil.copytree(missions_src, missions_dest)

    # Initialize git with main branch
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    (repo / "README.md").write_text("# Test Repo\n", encoding="utf-8")
    (repo / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create 2.x branch from main
    subprocess.run(["git", "branch", "2.x"], cwd=repo, check=True, capture_output=True)

    # Update metadata.yaml to current version
    metadata_file = repo / ".kittify" / "metadata.yaml"
    if metadata_file.exists():
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = yaml.safe_load(f) or {}

        from tests.test_isolation_helpers import get_installed_version
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

    return repo
