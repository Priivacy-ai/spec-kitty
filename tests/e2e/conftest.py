"""Shared fixtures for end-to-end CLI smoke tests.

These tests exercise the full spec-kitty workflow via subprocess calls
against a temporary git repository, verifying that the CLI commands
compose correctly end-to-end.
"""

from __future__ import annotations

import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tests.test_isolation_helpers import get_installed_version, run_cli_subprocess
from specify_cli.migration.schema_version import MAX_SUPPORTED_SCHEMA, SCHEMA_CAPABILITIES

REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Source-checkout pollution-guard helpers (T002)
# ---------------------------------------------------------------------------
#
# These helpers exist so the WP02 golden-path E2E test can verify that running
# the public spec-kitty CLI inside a temp project never writes back into the
# source checkout (REPO_ROOT). They capture both git-visible state and a
# direct on-disk inventory of pollution-prone roots so .gitignore-masked
# writes are also caught (FR-017, FR-018).
#
# Helpers are defined at module level (not bound to a fixture) so they can be
# imported by sibling test modules: `from tests.e2e.conftest import ...`.


_WATCHED_ROOTS: tuple[str, ...] = ("kitty-specs", ".kittify", ".worktrees", "docs")


@dataclass(frozen=True)
class SourcePollutionBaseline:
    """Snapshot of the source checkout's pollution-relevant state.

    Layer 1 (`git_status_short`): output of `git status --short` in the
    source checkout. Catches anything visible to git.

    Layer 2 (`inventory`): mapping of watched root -> {relative_path: (size,
    mtime_ns)}. Watched roots include each of `_WATCHED_ROOTS` plus a
    synthetic `**/profile-invocations` bucket aggregating every
    `profile-invocations` directory anywhere under the repo. This catches
    writes that a top-level `.gitignore` entry would mask from `git status`.
    """

    git_status_short: str
    inventory: dict[str, dict[str, tuple[int, int]]]


def _walk_inventory(
    root: Path,
    *,
    anchor: Path | None = None,
) -> dict[str, tuple[int, int]]:
    """Return a {relative_path: (size, mtime_ns)} map for every file under root.

    `anchor` controls the relative-path base. When omitted, paths are made
    relative to `root` itself; when supplied, paths are made relative to
    `anchor`. The latter is used for the aggregated `profile-invocations`
    bucket so paths from different subtrees stay disambiguated.
    """
    inv: dict[str, tuple[int, int]] = {}
    base = anchor if anchor is not None else root
    for path in root.rglob("*"):
        if path.is_file():
            st = path.stat()
            inv[str(path.relative_to(base))] = (st.st_size, st.st_mtime_ns)
    return inv


def capture_source_pollution_baseline(repo_root: Path) -> SourcePollutionBaseline:
    """Snapshot the source checkout's pollution-relevant state.

    Assumes `repo_root` is a git repo (the WP02 contract is that it is only
    ever called against `REPO_ROOT`). Returns a `SourcePollutionBaseline`
    suitable for later comparison via `assert_no_source_pollution`.
    """
    status = subprocess.run(
        ["git", "status", "--short"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    inventory: dict[str, dict[str, tuple[int, int]]] = {}
    for root_name in _WATCHED_ROOTS:
        root = repo_root / root_name
        inventory[root_name] = _walk_inventory(root) if root.exists() else {}

    # Aggregate every `profile-invocations` directory anywhere under repo_root.
    pi_inventory: dict[str, tuple[int, int]] = {}
    for path in repo_root.rglob("profile-invocations"):
        if path.is_dir():
            pi_inventory.update(_walk_inventory(path, anchor=repo_root))
    inventory["**/profile-invocations"] = pi_inventory

    return SourcePollutionBaseline(git_status_short=status, inventory=inventory)


def assert_no_source_pollution(baseline: SourcePollutionBaseline, repo_root: Path) -> None:
    """Compare current source-checkout state against `baseline`; raise on drift.

    Two-layer guard:
      * Layer 1 (FR-017): `git status --short` must be byte-identical to the
        baseline.
      * Layer 2 (FR-018): per-watched-root inventory must be byte-identical;
        any added / removed / modified file raises AssertionError with a
        diagnostic listing the diff.
    """
    current = capture_source_pollution_baseline(repo_root)

    if current.git_status_short != baseline.git_status_short:
        raise AssertionError(
            f"Source-checkout polluted (FR-017 / git status drift):\n  before: {baseline.git_status_short!r}\n  after:  {current.git_status_short!r}"
        )

    for watched, before in baseline.inventory.items():
        after = current.inventory.get(watched, {})
        added = sorted(set(after) - set(before))
        removed = sorted(set(before) - set(after))
        modified = sorted(p for p in set(before) & set(after) if before[p] != after[p])
        if added or removed or modified:
            raise AssertionError(f"Source-checkout polluted (FR-018 / {watched} drift):\n  added:    {added}\n  removed:  {removed}\n  modified: {modified}")


# ---------------------------------------------------------------------------
# Subprocess-failure diagnostic helper (T003)
# ---------------------------------------------------------------------------


def format_subprocess_failure(
    *,
    command: list[str] | tuple[str, ...],
    cwd: Path,
    completed: subprocess.CompletedProcess[str],
) -> str:
    """Produce a multi-line diagnostic for a failed subprocess (FR-019, NFR-004).

    The golden-path E2E test must surface command, cwd, return code, stdout,
    and stderr in any failed-subprocess assertion message so a single failed
    run is diagnosable without rerunning under a debugger.
    """
    return (
        "Subprocess failed.\n"
        f"  command: {list(command)!r}\n"
        f"  cwd:     {cwd}\n"
        f"  rc:      {completed.returncode}\n"
        f"  stdout:  {completed.stdout!r}\n"
        f"  stderr:  {completed.stderr!r}"
    )


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
        cwd=project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "E2E Test"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial project"],
        cwd=project,
        check=True,
        capture_output=True,
    )

    # Align metadata version with source to avoid version mismatch errors
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
        metadata["spec_kitty"]["schema_version"] = MAX_SUPPORTED_SCHEMA
        metadata["spec_kitty"]["schema_capabilities"] = SCHEMA_CAPABILITIES[MAX_SUPPORTED_SCHEMA]

        with open(metadata_file, "w", encoding="utf-8") as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)

        # Commit the version update
        subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Align metadata version", "--allow-empty"],
            cwd=project,
            check=True,
            capture_output=True,
        )

    # Create a minimal source directory for realism
    src_dir = project / "src"
    src_dir.mkdir()
    (src_dir / "__init__.py").write_text("", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add source skeleton"],
        cwd=project,
        check=True,
        capture_output=True,
    )

    return project


# ---------------------------------------------------------------------------
# Fresh-project fixture (T001)
# ---------------------------------------------------------------------------


@pytest.fixture()
def fresh_e2e_project(tmp_path: Path) -> Path:
    """Create a temp Spec Kitty project from scratch via public CLI.

    Unlike `e2e_project`, this fixture does NOT copy `.kittify` from the
    source checkout. It runs `spec-kitty init` against a brand-new git
    repo so the test exercises the operator path from a truly clean
    starting state (FR-003, FR-020).
    """
    project = tmp_path / "fresh-e2e-project"
    project.mkdir()

    # Step 1: bare git init + config (spec-kitty init does NOT do this).
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "fresh-e2e@example.com"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Fresh E2E Test"],
        cwd=project,
        check=True,
        capture_output=True,
    )

    # Step 2: drive `spec-kitty init` via the same isolated invocation
    # path used by the `run_cli` fixture (PYTHONPATH -> source `src/`,
    # SPEC_KITTY_TEMPLATE_ROOT -> REPO_ROOT, SPEC_KITTY_TEST_MODE=1).
    result = run_cli_subprocess(
        project,
        "init",
        ".",
        "--ai",
        "codex",
        "--non-interactive",
    )
    if result.returncode != 0:
        raise AssertionError(f"spec-kitty init failed for fresh fixture:\n  rc={result.returncode}\n  stdout: {result.stdout}\n  stderr: {result.stderr}")

    # Step 3: commit the freshly seeded project state so subsequent
    # CLI commands see a clean working tree.
    subprocess.run(
        ["git", "add", "."],
        cwd=project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial spec-kitty init"],
        cwd=project,
        check=True,
        capture_output=True,
    )

    return project
