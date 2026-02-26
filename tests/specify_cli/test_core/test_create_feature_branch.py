"""Tests for create_feature() branch handling — current branch IS the target branch.

All tests use real git repos. No mocks.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.core.git_ops import run_command


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
    """Create minimal .kittify structure required by create_feature()."""
    kittify = repo / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text("agents:\n  available:\n    - claude\n", encoding="utf-8")
    (kittify / "constitution.md").write_text("# Constitution\n", encoding="utf-8")
    # Create kitty-specs dir
    (repo / "kitty-specs").mkdir(exist_ok=True)


def _read_meta(repo: Path, feature_slug: str) -> dict:
    """Read and return meta.json for a feature."""
    meta_file = repo / "kitty-specs" / feature_slug / "meta.json"
    return json.loads(meta_file.read_text(encoding="utf-8"))


def _get_feature_slugs(repo: Path) -> list[str]:
    """Get list of feature directory names from kitty-specs/."""
    kitty_specs = repo / "kitty-specs"
    return sorted(
        d.name for d in kitty_specs.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


# ============================================================================
# create_feature records current branch as target
# ============================================================================


@pytest.mark.usefixtures("_git_identity")
def test_create_feature_on_2x_records_target_branch(tmp_path, monkeypatch):
    """create_feature on 2.x records target_branch='2.x' in meta.json."""
    from typer.testing import CliRunner
    from specify_cli.cli.commands.agent.feature import app

    repo = _init_repo(tmp_path, "2.x")
    _setup_kittify(repo)
    monkeypatch.chdir(repo)

    runner = CliRunner()
    result = runner.invoke(app, ["create-feature", "test-feature", "--json"])

    assert result.exit_code == 0, f"Command failed: {result.output}"
    slugs = _get_feature_slugs(repo)
    assert len(slugs) == 1
    meta = _read_meta(repo, slugs[0])
    assert meta["target_branch"] == "2.x"


@pytest.mark.usefixtures("_git_identity")
def test_create_feature_on_2x_with_main_also_existing(tmp_path, monkeypatch):
    """create_feature on 2.x records target_branch='2.x' even when main exists.

    THIS IS THE CRITICAL REGRESSION TEST.
    """
    from typer.testing import CliRunner
    from specify_cli.cli.commands.agent.feature import app

    repo = _init_repo(tmp_path, "main")
    _setup_kittify(repo)
    # Create 2.x branch and switch to it
    run_command(["git", "branch", "2.x"], cwd=repo)
    run_command(["git", "checkout", "2.x"], cwd=repo)
    monkeypatch.chdir(repo)

    runner = CliRunner()
    result = runner.invoke(app, ["create-feature", "test-feature", "--json"])

    assert result.exit_code == 0, f"Command failed: {result.output}"
    slugs = _get_feature_slugs(repo)
    assert len(slugs) == 1
    meta = _read_meta(repo, slugs[0])
    assert meta["target_branch"] == "2.x"


@pytest.mark.usefixtures("_git_identity")
def test_create_feature_on_main_records_target_branch(tmp_path, monkeypatch):
    """create_feature on main records target_branch='main'."""
    from typer.testing import CliRunner
    from specify_cli.cli.commands.agent.feature import app

    repo = _init_repo(tmp_path, "main")
    _setup_kittify(repo)
    monkeypatch.chdir(repo)

    runner = CliRunner()
    result = runner.invoke(app, ["create-feature", "test-feature", "--json"])

    assert result.exit_code == 0, f"Command failed: {result.output}"
    slugs = _get_feature_slugs(repo)
    assert len(slugs) == 1
    meta = _read_meta(repo, slugs[0])
    assert meta["target_branch"] == "main"


@pytest.mark.usefixtures("_git_identity")
def test_create_feature_on_master_records_target_branch(tmp_path, monkeypatch):
    """create_feature on master records target_branch='master'."""
    from typer.testing import CliRunner
    from specify_cli.cli.commands.agent.feature import app

    repo = _init_repo(tmp_path, "master")
    _setup_kittify(repo)
    monkeypatch.chdir(repo)

    runner = CliRunner()
    result = runner.invoke(app, ["create-feature", "test-feature", "--json"])

    assert result.exit_code == 0, f"Command failed: {result.output}"
    slugs = _get_feature_slugs(repo)
    assert len(slugs) == 1
    meta = _read_meta(repo, slugs[0])
    assert meta["target_branch"] == "master"


@pytest.mark.usefixtures("_git_identity")
def test_create_feature_on_custom_branch_records_target_branch(tmp_path, monkeypatch):
    """create_feature on v3-next records target_branch='v3-next'."""
    from typer.testing import CliRunner
    from specify_cli.cli.commands.agent.feature import app

    repo = _init_repo(tmp_path, "v3-next")
    _setup_kittify(repo)
    monkeypatch.chdir(repo)

    runner = CliRunner()
    result = runner.invoke(app, ["create-feature", "test-feature", "--json"])

    assert result.exit_code == 0, f"Command failed: {result.output}"
    slugs = _get_feature_slugs(repo)
    assert len(slugs) == 1
    meta = _read_meta(repo, slugs[0])
    assert meta["target_branch"] == "v3-next"


@pytest.mark.usefixtures("_git_identity")
def test_create_feature_with_explicit_target_branch_flag(tmp_path, monkeypatch):
    """--target-branch flag overrides current branch."""
    from typer.testing import CliRunner
    from specify_cli.cli.commands.agent.feature import app

    repo = _init_repo(tmp_path, "main")
    _setup_kittify(repo)
    monkeypatch.chdir(repo)

    runner = CliRunner()
    result = runner.invoke(app, ["create-feature", "test-feature", "--json", "--target-branch", "2.x"])

    assert result.exit_code == 0, f"Command failed: {result.output}"
    slugs = _get_feature_slugs(repo)
    assert len(slugs) == 1
    meta = _read_meta(repo, slugs[0])
    assert meta["target_branch"] == "2.x"


@pytest.mark.usefixtures("_git_identity")
def test_create_feature_rejects_detached_head(tmp_path, monkeypatch):
    """create_feature fails on detached HEAD."""
    from typer.testing import CliRunner
    from specify_cli.cli.commands.agent.feature import app

    repo = _init_repo(tmp_path, "main")
    _setup_kittify(repo)
    # Detach HEAD
    run_command(["git", "checkout", "--detach"], cwd=repo)
    monkeypatch.chdir(repo)

    runner = CliRunner()
    result = runner.invoke(app, ["create-feature", "test-feature", "--json"])

    assert result.exit_code != 0


@pytest.mark.usefixtures("_git_identity")
def test_create_feature_rejects_worktree(tmp_path, monkeypatch):
    """create_feature fails when run from inside a worktree."""
    from typer.testing import CliRunner
    from specify_cli.cli.commands.agent.feature import app

    repo = _init_repo(tmp_path, "main")
    _setup_kittify(repo)
    # Create a fake worktree directory
    worktree = repo / ".worktrees" / "001-test-WP01"
    worktree.mkdir(parents=True)
    monkeypatch.chdir(worktree)

    runner = CliRunner()
    result = runner.invoke(app, ["create-feature", "test-feature", "--json"])

    assert result.exit_code != 0
