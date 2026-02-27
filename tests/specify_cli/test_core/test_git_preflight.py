"""Tests for deterministic git preflight checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from unittest.mock import patch

from specify_cli.core.git_preflight import (
    build_git_preflight_failure_payload,
    run_git_preflight,
)


def _init_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True, capture_output=True)
    (path / "README.md").write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True)


def test_run_git_preflight_blocks_non_repo(tmp_path: Path) -> None:
    result = run_git_preflight(tmp_path)
    assert not result.passed
    assert result.first_error is not None
    assert result.first_error.code == "NOT_A_GIT_REPOSITORY"
    assert "git status" in (result.first_error.command or "")


def test_run_git_preflight_missing_origin_is_warning(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)

    result = run_git_preflight(repo)

    assert result.passed
    assert any(issue.code == "MISSING_ORIGIN_REMOTE" for issue in result.warnings)


@dataclass
class _FakeCmdResult:
    returncode: int
    stdout: str
    stderr: str


def test_run_git_preflight_detects_dubious_ownership(tmp_path: Path) -> None:
    dubious = _FakeCmdResult(
        returncode=128,
        stdout="",
        stderr="fatal: detected dubious ownership in repository at '/tmp/repo'",
    )
    with patch("specify_cli.core.git_preflight._run_git", return_value=dubious):
        result = run_git_preflight(tmp_path)

    assert not result.passed
    assert result.first_error is not None
    assert result.first_error.code == "UNTRUSTED_REPOSITORY"
    assert "safe.directory" in (result.first_error.command or "")


def test_run_git_preflight_detects_worktree_listing_failure(tmp_path: Path) -> None:
    responses = iter(
        [
            _FakeCmdResult(returncode=0, stdout="true\n", stderr=""),
            _FakeCmdResult(returncode=1, stdout="", stderr="fatal: could not list worktrees"),
        ]
    )
    with patch("specify_cli.core.git_preflight._run_git", side_effect=lambda *_args, **_kwargs: next(responses)):
        result = run_git_preflight(tmp_path, check_worktree_list=True)

    assert not result.passed
    assert result.first_error is not None
    assert result.first_error.code == "WORKTREE_LIST_FAILED"


def test_build_git_preflight_failure_payload_contains_remediation(tmp_path: Path) -> None:
    result = run_git_preflight(tmp_path)
    payload = build_git_preflight_failure_payload(result, command_name="spec-kitty merge")

    assert payload["error_code"] == "GIT_PREFLIGHT_FAILED"
    assert payload["command"] == "spec-kitty merge"
    assert isinstance(payload["remediation"], list)
