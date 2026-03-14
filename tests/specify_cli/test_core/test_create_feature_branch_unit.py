"""Unit tests for create_feature() — no real git repo required.

These tests verify the target_branch recording logic and guard conditions
in create_feature() by mocking out all git I/O at the responsibility
boundary:
  - locate_project_root  → returns a tmp_path
  - is_git_repo          → returns True
  - is_worktree_context  → returns False (unless testing the guard)
  - get_current_branch   → returns a controlled branch name
  - get_next_feature_number → returns a fixed number (1)

The CliRunner is used for in-process invocation with no subprocess overhead.
Tests run in < 50 ms each.

Scope statement: validates that create_feature writes target_branch correctly
and enforces worktree/detached-HEAD guards, while stubbing all git operations.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner
from click.testing import Result

from specify_cli.cli.commands.agent.feature import app

pytestmark = pytest.mark.fast

_FEATURE_MODULE = "specify_cli.cli.commands.agent.feature"

runner = CliRunner()


def _setup_kittify(repo: Path) -> None:
    """Create minimal .kittify structure required by create_feature()."""
    kittify = repo / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text("agents:\n  available:\n    - claude\n", encoding="utf-8")
    (kittify / "constitution.md").write_text("# Constitution\n", encoding="utf-8")
    (repo / "kitty-specs").mkdir(exist_ok=True)


def _run_create_feature(
    repo: Path, slug: str, current_branch: str, extra_args: list[str] | None = None
) -> tuple[Result, dict[str, object] | None]:
    """Invoke create-feature with mocked git layer and return (result, meta)."""
    args = ["create-feature", slug, "--json"] + (extra_args or [])
    with (
        patch(f"{_FEATURE_MODULE}.locate_project_root", return_value=repo),
        patch(f"{_FEATURE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_FEATURE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_FEATURE_MODULE}.get_current_branch", return_value=current_branch),
        patch(f"{_FEATURE_MODULE}.get_next_feature_number", return_value=1),
        patch(f"{_FEATURE_MODULE}.safe_commit", return_value=True),
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


def test_create_feature_records_current_branch_2x(tmp_path: Path) -> None:
    """create_feature records target_branch='2.x' when current branch is '2.x'."""
    _setup_kittify(tmp_path)
    result, meta = _run_create_feature(tmp_path, "test-feature", "2.x")
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert meta is not None
    assert meta["target_branch"] == "2.x"


def test_create_feature_records_current_branch_main(tmp_path: Path) -> None:
    """create_feature records target_branch='main' when current branch is 'main'."""
    _setup_kittify(tmp_path)
    result, meta = _run_create_feature(tmp_path, "test-feature", "main")
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert meta is not None
    assert meta["target_branch"] == "main"


def test_create_feature_records_current_branch_master(tmp_path: Path) -> None:
    """create_feature records target_branch='master' when current branch is 'master'."""
    _setup_kittify(tmp_path)
    result, meta = _run_create_feature(tmp_path, "test-feature", "master")
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert meta is not None
    assert meta["target_branch"] == "master"


def test_create_feature_records_custom_branch(tmp_path: Path) -> None:
    """create_feature records target_branch='v3-next' when current branch is 'v3-next'."""
    _setup_kittify(tmp_path)
    result, meta = _run_create_feature(tmp_path, "test-feature", "v3-next")
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert meta is not None
    assert meta["target_branch"] == "v3-next"


def test_create_feature_explicit_target_branch_flag_overrides_current(tmp_path: Path) -> None:
    """--target-branch flag overrides the current branch."""
    _setup_kittify(tmp_path)
    result, meta = _run_create_feature(tmp_path, "test-feature", "main", extra_args=["--target-branch", "2.x"])
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert meta is not None
    assert meta["target_branch"] == "2.x"


def test_create_feature_2x_wins_even_when_main_coexists(tmp_path: Path) -> None:
    """The critical regression test: on 2.x, target_branch is '2.x' not 'main'."""
    _setup_kittify(tmp_path)
    # Simulate being on 2.x while main also exists (branch detection is mocked)
    result, meta = _run_create_feature(tmp_path, "test-feature", "2.x")
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert meta is not None
    assert meta["target_branch"] == "2.x"


# ============================================================================
# Guard conditions
# ============================================================================


def test_create_feature_rejects_worktree_context(tmp_path: Path) -> None:
    """create_feature exits non-zero when run from inside a worktree."""
    _setup_kittify(tmp_path)
    with (
        patch(f"{_FEATURE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_FEATURE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_FEATURE_MODULE}.is_worktree_context", return_value=True),
        patch(f"{_FEATURE_MODULE}.get_current_branch", return_value="main"),
    ):
        result = runner.invoke(app, ["create-feature", "test-feature", "--json"])

    assert result.exit_code != 0


def test_create_feature_rejects_detached_head(tmp_path: Path) -> None:
    """create_feature exits non-zero when get_current_branch returns None (detached HEAD)."""
    _setup_kittify(tmp_path)
    with (
        patch(f"{_FEATURE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_FEATURE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_FEATURE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_FEATURE_MODULE}.get_current_branch", return_value=None),
    ):
        result = runner.invoke(app, ["create-feature", "test-feature", "--json"])

    assert result.exit_code != 0


def test_create_feature_rejects_invalid_slug(tmp_path: Path) -> None:
    """create_feature exits non-zero for non-kebab-case slugs."""
    _setup_kittify(tmp_path)
    with (
        patch(f"{_FEATURE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_FEATURE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_FEATURE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_FEATURE_MODULE}.get_current_branch", return_value="main"),
    ):
        result = runner.invoke(app, ["create-feature", "Invalid_Slug", "--json"])

    assert result.exit_code != 0
