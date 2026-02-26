from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Iterator

import pytest

from tests.utils import REPO_ROOT, run, run_tasks_cli, write_wp


def pytest_configure(config: pytest.Config) -> None:
    # HARDCODED: Never open browser windows during tests.
    # Propagates to subprocesses too (e.g. dashboard CLI spawned by tests).
    os.environ["PWHEADLESS"] = "1"

    # Block webbrowser.open() in the test process itself.
    import webbrowser
    webbrowser.open = lambda *args, **kwargs: None  # type: ignore[assignment]
    webbrowser.open_new = lambda *args, **kwargs: None  # type: ignore[assignment]
    webbrowser.open_new_tab = lambda *args, **kwargs: None  # type: ignore[assignment]

    config.addinivalue_line(
        "markers",
        "adversarial: adversarial scenarios for merge and dependency handling",
    )


@pytest.fixture(autouse=True)
def _enable_saas_sync_feature_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep legacy sync/auth tests enabled unless a test opts out explicitly."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")


def _venv_python(venv_dir: Path) -> Path:
    candidate = venv_dir / "bin" / "python"
    if candidate.exists():
        return candidate
    return venv_dir / "Scripts" / "python.exe"


def _venv_pip(venv_dir: Path) -> Path:
    candidate = venv_dir / "bin" / "pip"
    if candidate.exists():
        return candidate
    return venv_dir / "Scripts" / "pip.exe"


def _venv_has_required_runtime(venv_dir: Path) -> bool:
    """Return True when the cached venv can run the CLI runtime deps."""
    python = _venv_python(venv_dir)
    if not python.exists():
        return False
    probe = (
        "import importlib.util,sys;"
        "mods=['typer','rich','httpx','yaml'];"
        "missing=[m for m in mods if importlib.util.find_spec(m) is None];"
        "sys.exit(1 if missing else 0)"
    )
    result = subprocess.run(
        [str(python), "-c", probe],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _create_test_venv(venv_dir: Path) -> None:
    """Create the test venv, with an offline-safe fallback."""
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    pip = _venv_pip(venv_dir)
    try:
        subprocess.run([str(pip), "install", "-e", str(REPO_ROOT)], check=True)
    except subprocess.CalledProcessError:
        # Fallback for offline/dev shells where build deps cannot be downloaded.
        shutil.rmtree(venv_dir, ignore_errors=True)
        subprocess.run(
            [sys.executable, "-m", "venv", "--system-site-packages", str(venv_dir)],
            check=True,
        )

    if not _venv_has_required_runtime(venv_dir):
        raise RuntimeError(
            "Test venv is missing runtime dependencies (typer/rich/httpx/yaml)."
        )


@pytest.fixture(scope="session", autouse=True)
def test_venv() -> Path:
    """Create and cache a test venv for isolated CLI execution."""
    venv_dir = REPO_ROOT / ".pytest_cache" / "spec-kitty-test-venv"
    venv_marker = venv_dir / "VERSION"

    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        source_version = tomllib.load(f)["project"]["version"]

    rebuild = False
    if not venv_dir.exists():
        rebuild = True
    elif not venv_marker.exists():
        rebuild = True
    elif venv_marker.read_text(encoding="utf-8").strip() != source_version:
        rebuild = True
    elif not _venv_has_required_runtime(venv_dir):
        rebuild = True

    if rebuild:
        shutil.rmtree(venv_dir, ignore_errors=True)
        _create_test_venv(venv_dir)
        venv_marker.write_text(source_version, encoding="utf-8")

    os.environ["SPEC_KITTY_TEST_VENV"] = str(venv_dir)
    return venv_dir


@pytest.fixture()
def temp_repo(tmp_path: Path) -> Iterator[Path]:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    run(["git", "init"], cwd=repo_dir)
    run(["git", "config", "user.name", "Spec Kitty"], cwd=repo_dir)
    run(["git", "config", "user.email", "spec@example.com"], cwd=repo_dir)
    yield repo_dir


@pytest.fixture()
def feature_repo(temp_repo: Path) -> Path:
    feature_slug = "001-demo-feature"
    feature_dir = temp_repo / "kitty-specs" / feature_slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks").mkdir(exist_ok=True)
    (feature_dir / "spec.md").write_text("Spec content", encoding="utf-8")
    (feature_dir / "plan.md").write_text("Plan content", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("- [x] Initial task", encoding="utf-8")
    (feature_dir / "quickstart.md").write_text("Quickstart", encoding="utf-8")
    (feature_dir / "data-model.md").write_text("Data model", encoding="utf-8")
    (feature_dir / "research.md").write_text("Research", encoding="utf-8")
    write_wp(temp_repo, feature_slug, "planned", "WP01")
    run(["git", "add", "."], cwd=temp_repo)
    run(["git", "commit", "-m", "Initial commit"], cwd=temp_repo)
    return temp_repo


@pytest.fixture()
def feature_slug() -> str:
    return "001-demo-feature"


@pytest.fixture()
def ensure_imports():
    # Import helper modules so tests can reference them directly.
    import task_helpers  # noqa: F401
    import acceptance_support  # noqa: F401


@pytest.fixture()
def merge_repo(temp_repo: Path) -> tuple[Path, Path, str]:
    repo = temp_repo
    (repo / "README.md").write_text("main", encoding="utf-8")
    (repo / ".gitignore").write_text(".worktrees/\n", encoding="utf-8")
    run(["git", "add", "README.md", ".gitignore"], cwd=repo)
    run(["git", "commit", "-m", "initial"], cwd=repo)
    run(["git", "branch", "-M", "main"], cwd=repo)

    feature_slug = "002-feature"
    run(["git", "checkout", "-b", feature_slug], cwd=repo)
    feature_file = repo / "FEATURE.txt"
    feature_file.write_text("feature work", encoding="utf-8")
    feature_dir = repo / "kitty-specs" / feature_slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text("{}\n", encoding="utf-8")
    run(["git", "add", "FEATURE.txt", "kitty-specs"], cwd=repo)
    run(["git", "commit", "-m", "feature work"], cwd=repo)

    run(["git", "checkout", "main"], cwd=repo)

    worktree_dir = repo / ".worktrees" / feature_slug
    worktree_dir.parent.mkdir(exist_ok=True)
    run(["git", "worktree", "add", str(worktree_dir), feature_slug], cwd=repo)

    return repo, worktree_dir, feature_slug


@pytest.fixture
def mock_worktree(tmp_path: Path) -> dict[str, Path]:
    """
    Create temporary worktree structure for testing path resolution.

    Creates a minimal spec-kitty project structure with a feature worktree.

    Returns:
        Dictionary with 'repo_root', 'worktree_path', and 'feature_dir' paths
    """
    repo_root = tmp_path
    worktree = repo_root / ".worktrees" / "test-feature"
    worktree.mkdir(parents=True)

    # Create .kittify marker in repo root
    kittify = repo_root / ".kittify"
    kittify.mkdir()

    # Create feature directory in worktree
    feature_dir = worktree / "kitty-specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)

    return {
        "repo_root": repo_root,
        "worktree_path": worktree,
        "feature_dir": feature_dir
    }


@pytest.fixture
def mock_main_repo(tmp_path: Path) -> Path:
    """
    Create temporary main repository structure for testing.

    Creates a minimal spec-kitty project structure in the main repo
    (not a worktree).

    Returns:
        Path to the temporary repository root
    """
    # Create .kittify marker
    kittify = tmp_path / ".kittify"
    kittify.mkdir()

    # Create specs directory
    specs = tmp_path / "kitty-specs"
    specs.mkdir()

    return tmp_path


@pytest.fixture
def conflicting_wps_repo(tmp_path: Path) -> tuple[Path, list[tuple[Path, str, str]]]:
    """
    Create repo with overlapping WP file changes for conflict testing.

    Returns:
        Tuple of (repo_root, wp_workspaces) where wp_workspaces is a list
        of (worktree_path, wp_id, branch_name) tuples with 3 WPs that
        have overlapping file modifications.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    run(["git", "init"], cwd=repo)
    run(["git", "config", "user.name", "Test"], cwd=repo)
    run(["git", "config", "user.email", "test@example.com"], cwd=repo)

    # Create initial commit
    (repo / "README.md").write_text("main", encoding="utf-8")
    (repo / "shared.txt").write_text("original", encoding="utf-8")
    run(["git", "add", "."], cwd=repo)
    run(["git", "commit", "-m", "init"], cwd=repo)
    run(["git", "branch", "-M", "main"], cwd=repo)

    # Create feature with WP tasks
    feature_slug = "017-conflict-test"
    feature_dir = repo / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    wp_workspaces = []

    # Create 3 WPs that all modify shared.txt
    for wp_num in [1, 2, 3]:
        wp_id = f"WP{wp_num:02d}"
        branch_name = f"{feature_slug}-{wp_id}"

        # Create WP task file
        wp_file = tasks_dir / f"{wp_id}.md"
        wp_file.write_text(
            f"""---
work_package_id: {wp_id}
title: Test WP {wp_num}
lane: doing
dependencies: []
---

# {wp_id} Content
""",
            encoding="utf-8",
        )

        # Create worktree
        worktree_dir = repo / ".worktrees" / branch_name
        run(["git", "worktree", "add", str(worktree_dir), "-b", branch_name], cwd=repo)

        # Modify shared.txt (this will conflict)
        (worktree_dir / "shared.txt").write_text(f"{wp_id} changes\n", encoding="utf-8")

        # Also modify WP-specific file (no conflict)
        (worktree_dir / f"{wp_id}.txt").write_text(f"{wp_id} specific\n", encoding="utf-8")

        run(["git", "add", "."], cwd=worktree_dir)
        run(["git", "commit", "-m", f"Add {wp_id} changes"], cwd=worktree_dir)

        wp_workspaces.append((worktree_dir, wp_id, branch_name))

    run(["git", "checkout", "main"], cwd=repo)

    return repo, wp_workspaces


@pytest.fixture
def git_stale_workspace(tmp_path: Path) -> dict[str, Path]:
    """
    Create main repo + stale WP worktree.

    The main branch will have commits that the WP branch doesn't have,
    simulating a stale workspace that needs syncing.

    Returns:
        Dictionary with 'repo_root', 'main_branch', 'worktree_path', 'feature_slug' keys
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    run(["git", "init"], cwd=repo)
    run(["git", "config", "user.name", "Test"], cwd=repo)
    run(["git", "config", "user.email", "test@example.com"], cwd=repo)

    # Create initial commit on main
    (repo / "README.md").write_text("initial", encoding="utf-8")
    run(["git", "add", "."], cwd=repo)
    run(["git", "commit", "-m", "initial commit"], cwd=repo)
    run(["git", "branch", "-M", "main"], cwd=repo)

    # Create feature branch and worktree
    feature_slug = "018-stale-test"
    branch_name = f"{feature_slug}-WP01"
    worktree_dir = repo / ".worktrees" / branch_name
    run(["git", "worktree", "add", str(worktree_dir), "-b", branch_name], cwd=repo)

    # Make commit in worktree
    (worktree_dir / "WP01.txt").write_text("WP01 work", encoding="utf-8")
    run(["git", "add", "."], cwd=worktree_dir)
    run(["git", "commit", "-m", "WP01 work"], cwd=worktree_dir)

    # Advance main branch (making worktree stale)
    run(["git", "checkout", "main"], cwd=repo)
    (repo / "main_advance.txt").write_text("main advanced", encoding="utf-8")
    run(["git", "add", "."], cwd=repo)
    run(["git", "commit", "-m", "advance main"], cwd=repo)

    return {
        "repo_root": repo,
        "main_branch": "main",
        "worktree_path": worktree_dir,
        "feature_slug": feature_slug,
        "branch_name": branch_name,
    }


@pytest.fixture
def dirty_worktree_repo(tmp_path: Path) -> tuple[Path, Path]:
    """
    Add uncommitted changes to a WP worktree.

    Returns:
        Tuple of (repo_root, dirty_worktree_path)
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    run(["git", "init"], cwd=repo)
    run(["git", "config", "user.name", "Test"], cwd=repo)
    run(["git", "config", "user.email", "test@example.com"], cwd=repo)

    # Create initial commit
    (repo / "README.md").write_text("test", encoding="utf-8")
    run(["git", "add", "."], cwd=repo)
    run(["git", "commit", "-m", "init"], cwd=repo)
    run(["git", "branch", "-M", "main"], cwd=repo)

    # Create feature with WP tasks
    feature_slug = "019-dirty-test"
    feature_dir = repo / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    wp_file = tasks_dir / "WP01.md"
    wp_file.write_text(
        """---
work_package_id: WP01
title: Test WP
lane: doing
dependencies: []
---

# WP01 Content
""",
        encoding="utf-8",
    )

    # Create worktree
    branch_name = f"{feature_slug}-WP01"
    worktree_dir = repo / ".worktrees" / branch_name
    run(["git", "worktree", "add", str(worktree_dir), "-b", branch_name], cwd=repo)

    # Make commit
    (worktree_dir / "WP01.txt").write_text("committed", encoding="utf-8")
    run(["git", "add", "."], cwd=worktree_dir)
    run(["git", "commit", "-m", "WP01 commit"], cwd=worktree_dir)

    # Add uncommitted changes
    (worktree_dir / "uncommitted.txt").write_text("dirty changes", encoding="utf-8")

    run(["git", "checkout", "main"], cwd=repo)

    return repo, worktree_dir
