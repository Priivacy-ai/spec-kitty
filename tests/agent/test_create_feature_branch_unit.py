"""Scope: mock-boundary unit tests for create_mission() target_branch logic — no real git."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner
from click.testing import Result

from specify_cli.cli.commands.agent.mission import app

pytestmark = pytest.mark.fast

_MISSION_MODULE = "specify_cli.cli.commands.agent.mission"

runner = CliRunner()


def _setup_kittify(repo: Path) -> None:
    """Create minimal .kittify structure required by create_mission()."""
    kittify = repo / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text("agents:\n  available:\n    - claude\n", encoding="utf-8")
    (kittify / "constitution.md").write_text("# Constitution\n", encoding="utf-8")
    (repo / "kitty-specs").mkdir(exist_ok=True)


def _run_create_mission(
    repo: Path, slug: str, current_branch: str, extra_args: list[str] | None = None
) -> tuple[Result, dict[str, object] | None]:
    """Invoke create-mission with mocked git layer and return (result, meta)."""
    args = ["create-mission", slug, "--json"] + (extra_args or [])
    with (
        patch(f"{_MISSION_MODULE}.locate_project_root", return_value=repo),
        patch(f"{_MISSION_MODULE}.is_git_repo", return_value=True),
        patch(f"{_MISSION_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_MISSION_MODULE}.get_current_branch", return_value=current_branch),
        patch(f"{_MISSION_MODULE}.get_next_mission_number", return_value=1),
        patch(f"{_MISSION_MODULE}.safe_commit", return_value=True),
    ):
        result = runner.invoke(app, args)

    # Find written meta.json
    meta = None
    kitty_specs = repo / "kitty-specs"
    if kitty_specs.exists():
        for d in kitty_specs.iterdir():
            meta_file = d / "meta.json"
            if meta_file.exists():
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                break

    return result, meta


# ============================================================================
# target_branch recording
# ============================================================================


def test_create_mission_records_current_branch_2x(tmp_path: Path) -> None:
    """create_mission records target_branch='2.x' when current branch is '2.x'."""
    # Arrange
    _setup_kittify(tmp_path)
    # Assumption check
    assert (tmp_path / ".kittify" / "config.yaml").exists()
    # Act
    result, meta = _run_create_mission(tmp_path, "test-mission", "2.x")
    # Assert
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert meta is not None
    assert meta["target_branch"] == "2.x"


def test_create_mission_records_current_branch_main(tmp_path: Path) -> None:
    """create_mission records target_branch='main' when current branch is 'main'."""
    # Arrange
    _setup_kittify(tmp_path)
    # Assumption check
    assert (tmp_path / ".kittify").exists()
    # Act
    result, meta = _run_create_mission(tmp_path, "test-mission", "main")
    # Assert
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert meta is not None
    assert meta["target_branch"] == "main"


def test_create_mission_records_current_branch_master(tmp_path: Path) -> None:
    """create_mission records target_branch='master' when current branch is 'master'."""
    # Arrange
    _setup_kittify(tmp_path)
    # Assumption check
    assert (tmp_path / ".kittify").exists()
    # Act
    result, meta = _run_create_mission(tmp_path, "test-mission", "master")
    # Assert
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert meta is not None
    assert meta["target_branch"] == "master"


def test_create_mission_records_custom_branch(tmp_path: Path) -> None:
    """create_mission records target_branch='v3-next' when current branch is 'v3-next'."""
    # Arrange
    _setup_kittify(tmp_path)
    # Assumption check
    assert (tmp_path / ".kittify").exists()
    # Act
    result, meta = _run_create_mission(tmp_path, "test-mission", "v3-next")
    # Assert
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert meta is not None
    assert meta["target_branch"] == "v3-next"


def test_create_mission_explicit_target_branch_flag_overrides_current(tmp_path: Path) -> None:
    """--target-branch flag overrides the current branch."""
    # Arrange
    _setup_kittify(tmp_path)
    # Assumption check
    assert (tmp_path / ".kittify").exists()
    # Act
    result, meta = _run_create_mission(tmp_path, "test-mission", "main", extra_args=["--target-branch", "2.x"])
    # Assert
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert meta is not None
    assert meta["target_branch"] == "2.x"


# TODO(conventions): retrofit remaining test bodies


def test_create_mission_2x_wins_even_when_main_coexists(tmp_path: Path) -> None:
    """The critical regression test: on 2.x, target_branch is '2.x' not 'main'."""
    _setup_kittify(tmp_path)
    # Simulate being on 2.x while main also exists (branch detection is mocked)
    result, meta = _run_create_mission(tmp_path, "test-mission", "2.x")
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert meta is not None
    assert meta["target_branch"] == "2.x"


# ============================================================================
# Guard conditions
# ============================================================================


def test_create_mission_rejects_worktree_context(tmp_path: Path) -> None:
    """create_mission exits non-zero when run from inside a worktree."""
    _setup_kittify(tmp_path)
    with (
        patch(f"{_MISSION_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_MISSION_MODULE}.is_git_repo", return_value=True),
        patch(f"{_MISSION_MODULE}.is_worktree_context", return_value=True),
        patch(f"{_MISSION_MODULE}.get_current_branch", return_value="main"),
    ):
        result = runner.invoke(app, ["create-mission", "test-mission", "--json"])

    assert result.exit_code != 0


def test_create_mission_rejects_detached_head(tmp_path: Path) -> None:
    """create_mission exits non-zero when get_current_branch returns None (detached HEAD)."""
    _setup_kittify(tmp_path)
    with (
        patch(f"{_MISSION_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_MISSION_MODULE}.is_git_repo", return_value=True),
        patch(f"{_MISSION_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_MISSION_MODULE}.get_current_branch", return_value=None),
    ):
        result = runner.invoke(app, ["create-mission", "test-mission", "--json"])

    assert result.exit_code != 0


def test_create_mission_rejects_invalid_slug(tmp_path: Path) -> None:
    """create_mission exits non-zero for non-kebab-case slugs."""
    _setup_kittify(tmp_path)
    with (
        patch(f"{_MISSION_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_MISSION_MODULE}.is_git_repo", return_value=True),
        patch(f"{_MISSION_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_MISSION_MODULE}.get_current_branch", return_value="main"),
    ):
        result = runner.invoke(app, ["create-mission", "Invalid_Slug", "--json"])

    assert result.exit_code != 0
