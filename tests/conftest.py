from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from collections.abc import Callable, Iterator

import pytest
import yaml

from tests.branch_contract import IS_2X_BRANCH
from tests.mutmut_env import prepare_mutants_environment_from_cwd
from tests.test_isolation_helpers import get_installed_version
from tests.utils import REPO_ROOT, run, write_wp


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register pytest-asyncio ini keys for environments without the plugin."""
    parser.addini("asyncio_mode", "pytest-asyncio compatibility option")
    parser.addini(
        "asyncio_default_fixture_loop_scope",
        "pytest-asyncio compatibility option",
    )


def pytest_configure(config: pytest.Config) -> None:
    try:
        prepare_mutants_environment_from_cwd()
    except OSError as exc:
        import warnings
        warnings.warn(f"Failed to prepare mutants environment: {exc}", stacklevel=1)

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
    config.addinivalue_line(
        "markers",
        "real_worktree_detection: opt out of autouse worktree detection neutralization",
    )


@pytest.fixture(autouse=True)
def _enable_saas_sync_feature_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep legacy sync/auth tests enabled unless a test opts out explicitly."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")


@pytest.fixture(autouse=True)
def _neutralize_worktree_detection(request, monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent worktree detection from failing tests run inside a worktree.

    The ``@require_main_repo`` decorator checks the physical CWD for a
    ``.worktrees`` path component.  When the test suite itself runs inside
    a spec-kitty worktree (e.g. during WP implementation), every CLI
    invocation via ``CliRunner`` inherits that CWD and is incorrectly
    rejected.  Patching ``detect_execution_context`` to always return
    MAIN_REPO makes the tests location-independent.

    Tests that explicitly test worktree detection should use the
    ``@pytest.mark.real_worktree_detection`` marker to opt out.
    """
    if "real_worktree_detection" in {m.name for m in request.node.iter_markers()}:
        return

    from specify_cli.core.context_validation import (
        CurrentContext,
        ExecutionContext,
    )

    def _always_main_repo(cwd=None):
        return CurrentContext(
            location=ExecutionContext.MAIN_REPO,
            cwd=Path.cwd(),
            repo_root=None,
            worktree_name=None,
            worktree_path=None,
        )

    monkeypatch.setattr(
        "specify_cli.core.context_validation.detect_execution_context",
        _always_main_repo,
    )


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


def _venv_site_packages(venv_dir: Path) -> Path:
    python = _venv_python(venv_dir)
    result = subprocess.run(
        [
            str(python),
            "-c",
            "import site; print(site.getsitepackages()[0])",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def _seed_offline_test_venv(venv_dir: Path, source_version: str) -> None:
    """Seed a fallback venv without requiring network access."""
    site_packages = _venv_site_packages(venv_dir)
    site_packages.mkdir(parents=True, exist_ok=True)

    host_site_packages = [
        path for path in sys.path if "site-packages" in path and Path(path).exists()
    ]
    if host_site_packages:
        (site_packages / "host-site-packages.pth").write_text(
            "\n".join(host_site_packages) + "\n",
            encoding="utf-8",
        )

    (site_packages / "spec-kitty-src.pth").write_text(
        f"{REPO_ROOT / 'src'}\n",
        encoding="utf-8",
    )

    dist_info_dir = site_packages / f"spec_kitty_cli-{source_version}.dist-info"
    dist_info_dir.mkdir(exist_ok=True)
    (dist_info_dir / "METADATA").write_text(
        "\n".join(
            [
                "Metadata-Version: 2.1",
                "Name: spec-kitty-cli",
                f"Version: {source_version}",
                "Summary: Local offline test install shim",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (dist_info_dir / "top_level.txt").write_text("specify_cli\n", encoding="utf-8")
    (dist_info_dir / "INSTALLER").write_text("offline-shim\n", encoding="utf-8")
    (dist_info_dir / "RECORD").write_text("", encoding="utf-8")


def _create_test_venv(venv_dir: Path, source_version: str) -> None:
    """Create the test venv, with an offline-safe fallback."""
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    pip = _venv_pip(venv_dir)
    try:
        subprocess.run([str(pip), "install", "-e", str(REPO_ROOT)], check=True)
    except subprocess.CalledProcessError:
        # Fallback for offline/dev shells where build deps cannot be downloaded.
        shutil.rmtree(venv_dir, ignore_errors=True)
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        _seed_offline_test_venv(venv_dir, source_version)

    if not _venv_has_required_runtime(venv_dir):
        raise RuntimeError("Test venv is missing runtime dependencies (typer/rich/httpx/yaml).")


@pytest.fixture(scope="session", autouse=True)
def test_venv() -> Path:
    """Create and cache a test venv for isolated CLI execution."""
    venv_dir = REPO_ROOT / ".pytest_cache" / "spec-kitty-test-venv"
    venv_marker = venv_dir / "VERSION"

    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        source_version = tomllib.load(f)["project"]["version"]

    rebuild = False
    if (
        not venv_dir.exists()
        or not venv_marker.exists()
        or venv_marker.read_text(encoding="utf-8").strip() != source_version
        or not _venv_has_required_runtime(venv_dir)
    ):
        rebuild = True

    if rebuild:
        shutil.rmtree(venv_dir, ignore_errors=True)
        _create_test_venv(venv_dir, source_version)
        venv_marker.write_text(source_version, encoding="utf-8")

    os.environ["SPEC_KITTY_TEST_VENV"] = str(venv_dir)
    return venv_dir


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
    from tests.test_isolation_helpers import get_venv_python  # noqa: F401 (side-effect: ensures venv exists)

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        source_version = tomllib.load(f)["project"]["version"]

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
    installed packages. This prevents version mismatch errors.
    """
    from tests.test_isolation_helpers import get_venv_python

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
    # Bootstrap event log with planned status for WP01
    import json
    from datetime import datetime, UTC
    event = {
        "event_id": "01TESTFIXTUREWP01",
        "feature_slug": feature_slug,
        "wp_id": "WP01",
        "from_lane": "planned",
        "to_lane": "planned",
        "actor": "test-fixture",
        "at": datetime.now(UTC).isoformat(),
        "force": True,
        "reason": "fixture bootstrap",
        "evidence": None,
        "review_ref": None,
        "execution_mode": "worktree",
    }
    events_path = feature_dir / "status.events.jsonl"
    events_path.write_text(json.dumps(event, sort_keys=True) + "\n", encoding="utf-8")
    run(["git", "add", "."], cwd=temp_repo)
    run(["git", "commit", "-m", "Initial commit"], cwd=temp_repo)
    return temp_repo


@pytest.fixture()
def feature_slug() -> str:
    return "001-demo-feature"


@pytest.fixture()
def ensure_imports() -> None:
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

    return {"repo_root": repo_root, "worktree_path": worktree, "feature_dir": feature_dir}


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
def git_stale_workspace(tmp_path: Path) -> dict[str, Path | str]:
    """
    Create main repo + stale lane worktree.

    The main branch will have commits that the lane branch doesn't have,
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

    # Create lane branch and worktree
    feature_slug = "018-stale-test"
    branch_name = f"kitty/mission-{feature_slug}-lane-a"
    worktree_dir = repo / ".worktrees" / f"{feature_slug}-lane-a"
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
    Add uncommitted changes to a lane worktree.

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
dependencies: []
---

# WP01 Content
""",
        encoding="utf-8",
    )

    # Create worktree
    branch_name = f"kitty/mission-{feature_slug}-lane-a"
    worktree_dir = repo / ".worktrees" / f"{feature_slug}-lane-a"
    run(["git", "worktree", "add", str(worktree_dir), "-b", branch_name], cwd=repo)

    # Make commit
    (worktree_dir / "WP01.txt").write_text("committed", encoding="utf-8")
    run(["git", "add", "."], cwd=worktree_dir)
    run(["git", "commit", "-m", "WP01 commit"], cwd=worktree_dir)

    # Add uncommitted changes
    (worktree_dir / "uncommitted.txt").write_text("dirty changes", encoding="utf-8")

    run(["git", "checkout", "main"], cwd=repo)

    return repo, worktree_dir


# ---------------------------------------------------------------------------
# Fixtures promoted from integration/conftest.py for use in slice directories
# ---------------------------------------------------------------------------


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
    if missions_src.exists() and not missions_dest.exists():
        shutil.copytree(missions_src, missions_dest)

    (project / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")

    subprocess.run(["git", "init", "-b", "main"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.email", "ci@example.com"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "Spec Kitty CI"], cwd=project, check=True)
    subprocess.run(["git", "add", "."], cwd=project, check=True)
    subprocess.run(["git", "commit", "-m", "Initial project"], cwd=project, check=True)

    # Update metadata.yaml to current version to avoid version mismatch errors
    metadata_file = project / ".kittify" / "metadata.yaml"
    if metadata_file.exists():
        with open(metadata_file, encoding="utf-8") as f:
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

    shutil.copytree(
        REPO_ROOT / ".kittify",
        repo / ".kittify",
        symlinks=True,
    )

    missions_src = REPO_ROOT / "src" / "specify_cli" / "missions"
    missions_dest = repo / ".kittify" / "missions"
    if missions_src.exists() and not missions_dest.exists():
        shutil.copytree(missions_src, missions_dest)

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

    (repo / "README.md").write_text("# Test Repo\n", encoding="utf-8")
    (repo / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    subprocess.run(["git", "branch", "2.x"], cwd=repo, check=True, capture_output=True)

    metadata_file = repo / ".kittify" / "metadata.yaml"
    if metadata_file.exists():
        with open(metadata_file, encoding="utf-8") as f:
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

    return repo
