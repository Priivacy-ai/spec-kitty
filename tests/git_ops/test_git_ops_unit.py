"""Unit tests for git_ops — no git repo required.

These tests cover:
- run_command() output capture and return-code handling
- get_current_branch() edge cases on non-git directories
- has_remote() / exclude_from_git_index() on non-git directories
- resolve_target_branch() pure decision logic (mocked resolve_primary_branch)
- resolve_primary_branch() branch-priority heuristics (mocked subprocess)

All git I/O is either absent (plain-directory cases) or replaced with
unittest.mock, so every test here runs in < 10 ms with no filesystem setup
beyond tmp_path.

Scope statement: validates pure logic in specify_cli.core.git_ops while
stubbing subprocess.run and get_current_branch where real git repos are
not required to exercise the behaviour under test.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.core.git_ops import (
    exclude_from_git_index,
    get_current_branch,
    has_remote,
    resolve_primary_branch,
    resolve_target_branch,
    run_command,
)

pytestmark = pytest.mark.fast

# ============================================================================
# run_command — pure subprocess wrapper, no git required
# ============================================================================


def test_run_command_captures_stdout() -> None:
    code, stdout, stderr = run_command(
        [sys.executable, "-c", "print('hello world')"],
        capture=True,
    )
    assert code == 0
    assert stdout == "hello world"
    assert stderr == ""


def test_run_command_allows_nonzero_when_not_checking() -> None:
    code, stdout, stderr = run_command(
        [sys.executable, "-c", "import sys; sys.exit(3)"],
        check_return=False,
    )
    assert code == 3
    assert stdout == ""
    assert stderr == ""


# ============================================================================
# get_current_branch — non-git directory (no subprocess needed)
# ============================================================================


def test_get_current_branch_not_git_repo(tmp_path: Path) -> None:
    """get_current_branch returns None for a plain directory."""
    plain_dir = tmp_path / "not-a-repo"
    plain_dir.mkdir()
    assert get_current_branch(plain_dir) is None


# ============================================================================
# has_remote — non-git directory
# ============================================================================


def test_has_remote_nonexistent_repo(tmp_path: Path) -> None:
    """has_remote returns False for a plain (non-git) directory."""
    non_repo = tmp_path / "not-a-repo"
    non_repo.mkdir()
    assert has_remote(non_repo) is False


# ============================================================================
# exclude_from_git_index — non-git directory (should silently no-op)
# ============================================================================


def test_exclude_from_git_index_non_git_repo(tmp_path: Path) -> None:
    """exclude_from_git_index silently skips non-git directories."""
    non_repo = tmp_path / "not-a-repo"
    non_repo.mkdir()
    exclude_from_git_index(non_repo, [".worktrees/"])
    assert not (non_repo / ".git").exists()


# ============================================================================
# resolve_target_branch — pure decision logic, filesystem only (no git calls)
# ============================================================================

# The function reads meta.json from tmp_path and calls resolve_primary_branch.
# We mock resolve_primary_branch to return a controlled value so no git repo
# is required.

_PATCH_PRIMARY = "specify_cli.core.git_ops.resolve_primary_branch"


def _write_meta(repo: Path, mission_slug: str, data: dict[str, str]) -> None:
    feature_dir = repo / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(json.dumps(data), encoding="utf-8")


def test_resolve_target_branch_matches_returns_proceed(tmp_path: Path) -> None:
    """When current == target, action is 'proceed' and should_notify is False."""
    _write_meta(tmp_path, "001-test", {"target_branch": "main"})

    with patch(_PATCH_PRIMARY, return_value="main"):
        resolution = resolve_target_branch("001-test", tmp_path, "main", respect_current=True)

    assert resolution.target == "main"
    assert resolution.current == "main"
    assert resolution.should_notify is False
    assert resolution.action == "proceed"


def test_resolve_target_branch_differs_stays_on_current(tmp_path: Path) -> None:
    """When current != target with respect_current=True, action is 'stay_on_current'."""
    _write_meta(tmp_path, "002-test", {"target_branch": "main"})

    with patch(_PATCH_PRIMARY, return_value="main"):
        resolution = resolve_target_branch("002-test", tmp_path, "develop", respect_current=True)

    assert resolution.target == "main"
    assert resolution.current == "develop"
    assert resolution.should_notify is True
    assert resolution.action == "stay_on_current"


def test_resolve_target_branch_no_respect_current_allows_checkout(tmp_path: Path) -> None:
    """When respect_current=False and branches differ, action is 'checkout_target'."""
    _write_meta(tmp_path, "003-test", {"target_branch": "main"})

    with patch(_PATCH_PRIMARY, return_value="main"):
        resolution = resolve_target_branch("003-test", tmp_path, "develop", respect_current=False)

    assert resolution.action == "checkout_target"
    assert resolution.should_notify is True


def test_resolve_target_branch_no_meta_falls_back_to_primary(tmp_path: Path) -> None:
    """When meta.json is absent, target falls back to resolve_primary_branch result."""
    # Create feature dir WITHOUT meta.json
    (tmp_path / "kitty-specs" / "004-test").mkdir(parents=True)

    with patch(_PATCH_PRIMARY, return_value="master"):
        resolution = resolve_target_branch("004-test", tmp_path, "master", respect_current=True)

    assert resolution.target == "master"
    assert resolution.should_notify is False
    assert resolution.action == "proceed"


def test_resolve_target_branch_invalid_meta_falls_back(tmp_path: Path) -> None:
    """When meta.json is malformed JSON, target falls back to primary branch."""
    feature_dir = tmp_path / "kitty-specs" / "005-test"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text("{ invalid json }", encoding="utf-8")

    with patch(_PATCH_PRIMARY, return_value="main"):
        resolution = resolve_target_branch("005-test", tmp_path, "main", respect_current=True)

    assert resolution.target == "main"
    assert resolution.action == "proceed"


def test_resolve_target_branch_meta_missing_field_falls_back(tmp_path: Path) -> None:
    """When meta.json exists but lacks target_branch, fallback to primary."""
    _write_meta(tmp_path, "006-test", {"feature_id": "006-test"})

    with patch(_PATCH_PRIMARY, return_value="2.x"):
        resolution = resolve_target_branch("006-test", tmp_path, "2.x", respect_current=True)

    assert resolution.target == "2.x"
    assert resolution.action == "proceed"


def test_resolve_target_branch_meta_overrides_primary(tmp_path: Path) -> None:
    """meta.json target_branch wins over the detected primary branch."""
    _write_meta(tmp_path, "007-test", {"target_branch": "2.x"})

    with patch(_PATCH_PRIMARY, return_value="master"):
        resolution = resolve_target_branch("007-test", tmp_path, "master", respect_current=True)

    assert resolution.target == "2.x"  # meta.json wins
    assert resolution.should_notify is True  # master != 2.x


# ============================================================================
# resolve_primary_branch — heuristic priority (mocked subprocess.run)
# ============================================================================

# We mock subprocess.run to return controlled stdout/returncode without
# touching the filesystem. Each test exercises one branch of the priority
# ladder in resolve_primary_branch.

_PATCH_SUBPROCESS = "specify_cli.core.git_ops.subprocess.run"


def _make_proc(returncode: int, stdout: str = "") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    return proc


def test_resolve_primary_branch_prefers_origin_head(tmp_path: Path) -> None:
    """Method 1: origin/HEAD symbolic ref is the highest-priority source."""
    origin_head_proc = _make_proc(0, "refs/remotes/origin/HEAD -> origin/my-trunk\n")
    # symbolic-ref returns the raw ref string
    origin_head_proc.stdout = "refs/remotes/origin/my-trunk\n"

    with patch(_PATCH_SUBPROCESS, return_value=origin_head_proc):
        result = resolve_primary_branch(tmp_path)

    assert result == "my-trunk"


def test_resolve_primary_branch_falls_back_to_current_branch(tmp_path: Path) -> None:
    """Method 2: when origin/HEAD is absent, current branch wins."""
    origin_fail = _make_proc(128, "")  # git symbolic-ref fails

    with (
        patch(_PATCH_SUBPROCESS, return_value=origin_fail),
        patch("specify_cli.core.git_ops.get_current_branch", return_value="feature-x"),
    ):
        result = resolve_primary_branch(tmp_path)

    assert result == "feature-x"


def test_resolve_primary_branch_falls_back_to_main_from_list(tmp_path: Path) -> None:
    """Method 3: when no remote and no current branch, common-branch check wins."""
    _make_proc(128, "")

    # subprocess.run side_effect: first call = symbolic-ref (fail),
    # then rev-parse calls for main (success), master (not reached), develop (not reached)
    def side_effect(cmd: list[str], **_kwargs: object) -> MagicMock:
        if "symbolic-ref" in cmd:
            return _make_proc(128, "")
        if "main" in cmd:
            return _make_proc(0, "")
        return _make_proc(128, "")

    with (
        patch(_PATCH_SUBPROCESS, side_effect=side_effect),
        patch("specify_cli.core.git_ops.get_current_branch", return_value=None),
    ):
        result = resolve_primary_branch(tmp_path)

    assert result == "main"


def test_resolve_primary_branch_falls_back_to_master_when_main_absent(tmp_path: Path) -> None:
    """Method 3: 'master' is returned when main doesn't exist but master does."""

    def side_effect(cmd: list[str], **_kwargs: object) -> MagicMock:
        if "symbolic-ref" in cmd:
            return _make_proc(128, "")
        if "main" in cmd:
            return _make_proc(128, "")  # main absent
        if "master" in cmd:
            return _make_proc(0, "")  # master present
        return _make_proc(128, "")

    with (
        patch(_PATCH_SUBPROCESS, side_effect=side_effect),
        patch("specify_cli.core.git_ops.get_current_branch", return_value=None),
    ):
        result = resolve_primary_branch(tmp_path)

    assert result == "master"


def test_resolve_primary_branch_final_fallback_is_main(tmp_path: Path) -> None:
    """Method 4: when all detection methods fail, 'main' is returned."""

    def side_effect(cmd: list[str], **_kwargs: object) -> MagicMock:
        return _make_proc(128, "")  # everything fails

    with (
        patch(_PATCH_SUBPROCESS, side_effect=side_effect),
        patch("specify_cli.core.git_ops.get_current_branch", return_value=None),
    ):
        result = resolve_primary_branch(tmp_path)

    assert result == "main"
