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


@pytest.mark.usefixtures("_git_identity")
def test_create_feature_on_main_records_target_branch(tmp_path, monkeypatch):
    """create on main records target_branch='main'."""
    # Arrange
    from typer.testing import CliRunner
    from specify_cli.cli.commands.agent.mission import app

    repo = _init_repo(tmp_path, "main")
    _setup_kittify(repo)
    monkeypatch.chdir(repo)
    # Creating on a protected ``main`` branch commits meta.json to it; the
    # documented operator escape hatch is the ONE sanctioned waiver (the test
    # repo IS the solo operator who owns main). Without it, safe_commit rightly
    # refuses the protected-branch commit (#3673 made this refusal fail loud
    # instead of the pre-fix contextlib.suppress that let it silently succeed).
    monkeypatch.setenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", "1")
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
    assert meta["target_branch"] == "main"


@pytest.mark.usefixtures("_git_identity")
def test_create_feature_on_master_records_target_branch(tmp_path, monkeypatch):
    """create on master records target_branch='master'."""
    # Arrange
    from typer.testing import CliRunner
    from specify_cli.cli.commands.agent.mission import app

    repo = _init_repo(tmp_path, "master")
    _setup_kittify(repo)
    monkeypatch.chdir(repo)
    # ``master`` is a protected branch too; same operator-owned-repo waiver as
    # the ``main`` case above (see that test for the #3673 rationale).
    monkeypatch.setenv("SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS", "1")
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
    assert meta["target_branch"] == "master"


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
def test_create_feature_target_branch_not_checked_out_fails_loud(tmp_path, monkeypatch):
    """``--target-branch X`` requires the invoking checkout to be on X — fail-loud otherwise.

    ``--target-branch`` names where planning artifacts land (``planning_branch =
    target_branch`` in ``mission_creation.py``), not merely a merge-target label.
    On ``main`` with ``--target-branch 2.x`` the placement seam routes the
    ``meta.json`` commit to ``2.x`` and ``safe_commit`` refuses because HEAD is
    still ``main`` — surfacing the actionable "checkout 2.x first" remedy. The
    modern way to create a mission on a different branch is ``--start-branch``
    (switch first), not this flag.

    Regression guard for #3673: pre-fix, this commit was wrapped in
    ``contextlib.suppress(Exception)``, so the refusal was swallowed and create
    "succeeded" (exit 0) with ``target_branch=2.x`` written to disk but never
    committed. This test used to assert that silent success; #3673 made the
    refusal fail loud, and this guard now pins the loud behavior.
    """
    from typer.testing import CliRunner
    from specify_cli.cli.commands.agent.mission import app

    repo = _init_repo(tmp_path, "main")
    _setup_kittify(repo)
    # ``2.x`` exists as a real branch so the refusal is the actionable
    # "checkout 2.x first" message — not the topology-mint error you get when the
    # target branch does not exist at all (a distinct, message-quality concern).
    run_command(["git", "branch", "2.x"], cwd=repo)
    monkeypatch.chdir(repo)

    runner = CliRunner()
    result = runner.invoke(app, ["create", "test-feature", "--json", "--target-branch", "2.x"])

    assert result.exit_code != 0, f"Expected fail-loud refusal, got success: {result.output}"
    assert "expected '2.x'" in result.output, result.output


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
