"""Scope: git_repo integration tests for create() branch recording — real git repos."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.core.git_ops import run_command

pytestmark = pytest.mark.git_repo


@pytest.fixture(name="_git_identity")
def git_identity_fixture(monkeypatch):
    """Ensure git commands can commit even if the user has no global config."""
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Spec Kitty")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "spec@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Spec Kitty")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "spec@example.com")


def _init_repo(tmp_path: Path, branch_name: str) -> Path:
    """Create a git repo with a commit on the given branch."""
    repo = tmp_path / "repo"
    repo.mkdir()
    run_command(["git", "init", f"--initial-branch={branch_name}"], cwd=repo)
    (repo / "README.md").write_text("init", encoding="utf-8")
    run_command(["git", "add", "."], cwd=repo)
    run_command(["git", "commit", "-m", "Initial"], cwd=repo)
    return repo


def _setup_kittify(repo: Path) -> None:
    """Create minimal .kittify structure required by create()."""
    kittify = repo / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text(
        "agents:\n  available:\n    - claude\nmission_type_activations:\n  - software-dev\n",
        encoding="utf-8",
    )
    (kittify / "charter.md").write_text("# Charter\n", encoding="utf-8")
    # Create kitty-specs dir
    (repo / "kitty-specs").mkdir(exist_ok=True)


def _read_meta(repo: Path, mission_slug: str) -> dict:
    """Read and return meta.json for a mission."""
    meta_file = repo / "kitty-specs" / mission_slug / "meta.json"
    return json.loads(meta_file.read_text(encoding="utf-8"))


def _get_mission_slugs(repo: Path) -> list[str]:
    """Get list of mission directory names from kitty-specs/."""
    kitty_specs = repo / "kitty-specs"
    return sorted(d.name for d in kitty_specs.iterdir() if d.is_dir() and not d.name.startswith("."))


# ============================================================================
# create records current branch as target
# ============================================================================


@pytest.mark.usefixtures("_git_identity")
def test_create_feature_on_2x_records_target_branch(tmp_path, monkeypatch):
    """create on 2.x records target_branch='2.x' in meta.json."""
    # Arrange
    from typer.testing import CliRunner
    from specify_cli.cli.commands.agent.mission import app

    repo = _init_repo(tmp_path, "2.x")
    _setup_kittify(repo)
    monkeypatch.chdir(repo)
    # Assumption check
    assert (repo / ".kittify" / "config.yaml").exists()
    # Act
    runner = CliRunner()
    result = runner.invoke(app, ["create", "test-feature", "--json"])
    # Assert
    assert result.exit_code == 0, f"Command failed: {result.output}"
    slugs = _get_mission_slugs(repo)
    assert len(slugs) == 1
    meta = _read_meta(repo, slugs[0])
    assert meta["target_branch"] == "2.x"


@pytest.mark.usefixtures("_git_identity")
def test_create_feature_on_2x_with_main_also_existing(tmp_path, monkeypatch):
    """create on 2.x records target_branch='2.x' even when main exists.

    THIS IS THE CRITICAL REGRESSION TEST.
    """
    # Arrange
    from typer.testing import CliRunner
    from specify_cli.cli.commands.agent.mission import app

    repo = _init_repo(tmp_path, "main")
    _setup_kittify(repo)
    run_command(["git", "branch", "2.x"], cwd=repo)
    run_command(["git", "checkout", "2.x"], cwd=repo)
    monkeypatch.chdir(repo)
    # Assumption check
    assert (repo / ".kittify" / "config.yaml").exists()
    # Act
    runner = CliRunner()
    result = runner.invoke(app, ["create", "test-feature", "--json"])
    # Assert
    assert result.exit_code == 0, f"Command failed: {result.output}"
    slugs = _get_mission_slugs(repo)
    assert len(slugs) == 1
    meta = _read_meta(repo, slugs[0])
    assert meta["target_branch"] == "2.x"


def _head_commit_subject(repo: Path) -> str:
    """Return the subject line of the current HEAD commit."""
    return run_command(["git", "log", "-1", "--format=%s"], cwd=repo, capture=True)[1].strip()


def _assert_protected_branch_refusal(result, repo: Path, protected_branch: str) -> None:
    """Assert a structured protected-branch refusal that names the --start-branch remedy.

    The coord-primary-partition-lock guard refuses to land planning artifacts on
    a protected primary branch; the sanctioned flow is ``--start-branch``. This
    helper keeps the two primary-branch cases (main/master) asserting the same
    shipped contract without duplicating the literal error substrings. It also
    confirms the guard blocked the commit (HEAD is unchanged) — the load-bearing
    invariant, distinct from whether the untracked scaffold is swept from disk.
    """
    assert result.exit_code != 0, f"Create on protected '{protected_branch}' must be refused: {result.output}"
    payload = json.loads(result.output)
    error = payload["error"]
    assert "protected branch" in error, error
    assert protected_branch in error, error
    assert "--start-branch" in error, error
    # The guard blocked the meta.json commit: no mission commit lands on the branch.
    assert _head_commit_subject(repo) == "Initial", _head_commit_subject(repo)


@pytest.mark.usefixtures("_git_identity")
def test_create_feature_on_main_refused_by_protected_branch_guard(tmp_path, monkeypatch):
    """create on the protected primary branch 'main' is refused (must use --start-branch).

    The coord-primary-partition-lock guard (see mission_creation.py WP02) forbids
    landing planning artifacts on a protected branch. Recording ``main`` as the
    target by committing meta.json onto ``main`` was the pre-guard behavior; the
    shipped contract now refuses it and points at the ``--start-branch`` flow.
    """
    # Arrange
    from typer.testing import CliRunner
    from specify_cli.cli.commands.agent.mission import app

    repo = _init_repo(tmp_path, "main")
    _setup_kittify(repo)
    monkeypatch.chdir(repo)
    # Assumption check
    assert (repo / ".kittify").exists()
    # Act
    runner = CliRunner()
    result = runner.invoke(app, ["create", "test-feature", "--json"])
    # Assert
    _assert_protected_branch_refusal(result, repo, "main")


@pytest.mark.usefixtures("_git_identity")
def test_create_feature_on_master_refused_by_protected_branch_guard(tmp_path, monkeypatch):
    """create on the protected primary branch 'master' is refused (must use --start-branch)."""
    # Arrange
    from typer.testing import CliRunner
    from specify_cli.cli.commands.agent.mission import app

    repo = _init_repo(tmp_path, "master")
    _setup_kittify(repo)
    monkeypatch.chdir(repo)
    # Assumption check
    assert (repo / ".kittify").exists()
    # Act
    runner = CliRunner()
    result = runner.invoke(app, ["create", "test-feature", "--json"])
    # Assert
    _assert_protected_branch_refusal(result, repo, "master")


@pytest.mark.usefixtures("_git_identity")
def test_create_feature_on_custom_branch_records_target_branch(tmp_path, monkeypatch):
    """create on v3-next records target_branch='v3-next'."""
    # Arrange
    from typer.testing import CliRunner
    from specify_cli.cli.commands.agent.mission import app

    repo = _init_repo(tmp_path, "v3-next")
    _setup_kittify(repo)
    monkeypatch.chdir(repo)
    # Assumption check
    assert (repo / ".kittify").exists()
    # Act
    runner = CliRunner()
    result = runner.invoke(app, ["create", "test-feature", "--json"])
    # Assert
    assert result.exit_code == 0, f"Command failed: {result.output}"
    slugs = _get_mission_slugs(repo)
    assert len(slugs) == 1
    meta = _read_meta(repo, slugs[0])
    assert meta["target_branch"] == "v3-next"


# TODO(conventions): retrofit remaining test bodies


@pytest.mark.usefixtures("_git_identity")
def test_create_feature_target_branch_mismatch_is_refused(tmp_path, monkeypatch):
    """--target-branch pointing away from the checkout is refused (no create-time split-brain).

    Pre-guard, ``--target-branch 2.x`` while parked on another branch recorded
    ``2.x`` yet committed meta.json onto the checkout branch — the create-time
    split-brain the coord-primary-partition-lock WP02 fix closed
    (mission_creation.py:198-209). The shipped contract now refuses the mismatch:
    the meta.json commit must land on the resolved target branch, so the operator
    must be checked out on it.
    """
    from typer.testing import CliRunner
    from specify_cli.cli.commands.agent.mission import app

    repo = _init_repo(tmp_path, "main")
    _setup_kittify(repo)
    # A non-protected feature branch keeps the default topology single_branch, so
    # the refusal is the crisp safe_commit branch-coherence error (no coordination
    # branch is involved) rather than the protected-branch guard.
    run_command(["git", "checkout", "-b", "feat/target-mismatch"], cwd=repo)
    monkeypatch.chdir(repo)

    runner = CliRunner()
    result = runner.invoke(app, ["create", "test-feature", "--json", "--target-branch", "2.x"])

    assert result.exit_code != 0, f"target/checkout mismatch must be refused: {result.output}"
    payload = json.loads(result.output)
    # A structured error is surfaced (the meta.json commit is refused rather than
    # silently landing on the wrong branch); we assert the load-bearing invariant
    # rather than a brittle message substring.
    assert payload["error"], payload
    # The split-brain is closed by construction: the guard blocked the commit, so
    # no mission commit lands on the checkout branch (HEAD unchanged from Initial).
    assert _head_commit_subject(repo) == "Initial", _head_commit_subject(repo)


@pytest.mark.usefixtures("_git_identity")
def test_create_feature_rejects_detached_head(tmp_path, monkeypatch):
    """create fails on detached HEAD."""
    from typer.testing import CliRunner
    from specify_cli.cli.commands.agent.mission import app

    repo = _init_repo(tmp_path, "main")
    _setup_kittify(repo)
    # Detach HEAD
    run_command(["git", "checkout", "--detach"], cwd=repo)
    monkeypatch.chdir(repo)

    runner = CliRunner()
    result = runner.invoke(app, ["create", "test-feature", "--json"])

    assert result.exit_code != 0


@pytest.mark.usefixtures("_git_identity")
def test_create_feature_rejects_worktree(tmp_path, monkeypatch):
    """create fails when run from inside a worktree."""
    from typer.testing import CliRunner
    from specify_cli.cli.commands.agent.mission import app

    repo = _init_repo(tmp_path, "main")
    _setup_kittify(repo)
    # Create a fake worktree directory
    worktree = repo / ".worktrees" / "001-test-lane-a"
    worktree.mkdir(parents=True)
    monkeypatch.chdir(worktree)

    runner = CliRunner()
    result = runner.invoke(app, ["create", "test-feature", "--json"])

    assert result.exit_code != 0
