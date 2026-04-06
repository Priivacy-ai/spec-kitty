"""Tests for core/mission_creation.py — the programmatic feature-creation API."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.core.mission_creation import (
    FeatureCreationError,
    FeatureCreationResult,
    create_feature_core,
)

pytestmark = pytest.mark.fast

_CORE_MODULE = "specify_cli.core.mission_creation"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_git_repo(repo: Path) -> None:
    """Initialise a minimal git repo with .kittify and kitty-specs."""
    (repo / ".kittify").mkdir(exist_ok=True)
    (repo / "kitty-specs").mkdir(exist_ok=True)
    subprocess.run(
        ["git", "init"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "init", "--allow-empty"],
        cwd=repo,
        capture_output=True,
        check=True,
    )


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


def test_happy_path_creates_directory_and_returns_result(tmp_path: Path) -> None:
    """create_feature_core creates the feature dir, meta.json, spec.md and returns FeatureCreationResult."""
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}.get_next_feature_number", return_value=1),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        result = create_feature_core(tmp_path, "test-feature")

    assert isinstance(result, FeatureCreationResult)
    assert result.mission_slug == "001-test-feature"
    assert result.mission_number == "001"
    assert result.target_branch == "main"
    assert result.current_branch == "main"
    assert result.feature_dir == tmp_path / "kitty-specs" / "001-test-feature"
    assert result.feature_dir.is_dir()

    # meta.json exists and has correct content
    meta_file = result.feature_dir / "meta.json"
    assert meta_file.exists()
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    assert meta["mission_slug"] == "001-test-feature"
    assert meta["target_branch"] == "main"
    assert meta["mission_type"] == "software-dev"

    # spec.md exists
    assert (result.feature_dir / "spec.md").exists()

    # Subdirectories exist
    assert (result.feature_dir / "tasks").is_dir()
    assert (result.feature_dir / "checklists").is_dir()
    assert (result.feature_dir / "research").is_dir()

    # status.events.jsonl exists
    assert (result.feature_dir / "status.events.jsonl").exists()


def test_result_created_files_populated(tmp_path: Path) -> None:
    """FeatureCreationResult.created_files lists the key files."""
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}.get_next_feature_number", return_value=5),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        result = create_feature_core(tmp_path, "my-feature")

    assert len(result.created_files) == 3
    names = [f.name for f in result.created_files]
    assert "spec.md" in names
    assert "meta.json" in names
    assert "README.md" in names


# ---------------------------------------------------------------------------
# Validation error tests
# ---------------------------------------------------------------------------


def test_invalid_slug_raises(tmp_path: Path) -> None:
    """Non-kebab-case slug raises FeatureCreationError."""
    _init_git_repo(tmp_path)

    with pytest.raises(FeatureCreationError, match="Invalid feature slug"):
        create_feature_core(tmp_path, "Invalid_Slug")


def test_slug_starting_with_number_raises(tmp_path: Path) -> None:
    """Slug starting with a digit raises FeatureCreationError."""
    _init_git_repo(tmp_path)

    with pytest.raises(FeatureCreationError, match="Invalid feature slug"):
        create_feature_core(tmp_path, "123-fix")


def test_uppercase_slug_raises(tmp_path: Path) -> None:
    """Uppercase slug raises FeatureCreationError."""
    _init_git_repo(tmp_path)

    with pytest.raises(FeatureCreationError, match="Invalid feature slug"):
        create_feature_core(tmp_path, "User-Auth")


# ---------------------------------------------------------------------------
# Context guard tests
# ---------------------------------------------------------------------------


def test_worktree_context_raises(tmp_path: Path) -> None:
    """Running from inside a worktree raises FeatureCreationError."""
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=True),
        pytest.raises(FeatureCreationError, match="worktree"),
    ):
        create_feature_core(tmp_path, "test-feature")


def test_not_git_repo_raises(tmp_path: Path) -> None:
    """Not being in a git repo raises FeatureCreationError."""
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=False),
        pytest.raises(FeatureCreationError, match="git repository"),
    ):
        create_feature_core(tmp_path, "test-feature")


def test_detached_head_raises(tmp_path: Path) -> None:
    """Detached HEAD raises FeatureCreationError."""
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value=None),
        pytest.raises(FeatureCreationError, match="branch"),
    ):
        create_feature_core(tmp_path, "test-feature")


# ---------------------------------------------------------------------------
# Target branch tests
# ---------------------------------------------------------------------------


def test_explicit_target_branch(tmp_path: Path) -> None:
    """Explicit target_branch overrides the current branch."""
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}.get_next_feature_number", return_value=1),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        result = create_feature_core(tmp_path, "test-feature", target_branch="2.x")

    assert result.target_branch == "2.x"
    assert result.current_branch == "main"
    meta = json.loads((result.feature_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["target_branch"] == "2.x"


def test_target_branch_defaults_to_current(tmp_path: Path) -> None:
    """When no target_branch provided, uses the current branch."""
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="develop"),
        patch(f"{_CORE_MODULE}.get_next_feature_number", return_value=2),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        result = create_feature_core(tmp_path, "my-feature")

    assert result.target_branch == "develop"
    meta = json.loads((result.feature_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["target_branch"] == "develop"


# ---------------------------------------------------------------------------
# Mission tests
# ---------------------------------------------------------------------------


def test_documentation_mission_sets_doc_state(tmp_path: Path) -> None:
    """mission='documentation' initializes documentation_state in meta.json."""
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}.get_next_feature_number", return_value=3),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        result = create_feature_core(tmp_path, "docs-feature", mission="documentation")

    meta = json.loads((result.feature_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["mission_type"] == "documentation"
    assert "documentation_state" in meta
    assert meta["documentation_state"]["iteration_mode"] == "initial"


def test_default_mission_is_software_dev(tmp_path: Path) -> None:
    """When mission is None, defaults to 'software-dev'."""
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}.get_next_feature_number", return_value=1),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        result = create_feature_core(tmp_path, "basic-feature")

    assert result.meta["mission_type"] == "software-dev"


# ---------------------------------------------------------------------------
# Feature number / slug formatting tests
# ---------------------------------------------------------------------------


def test_feature_number_zero_padded(tmp_path: Path) -> None:
    """Feature number is zero-padded to 3 digits."""
    _init_git_repo(tmp_path)

    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}.get_next_feature_number", return_value=42),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        result = create_feature_core(tmp_path, "padded-test")

    assert result.mission_number == "042"
    assert result.mission_slug == "042-padded-test"
