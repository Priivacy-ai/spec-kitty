"""Regression tests for mission artifact commit handling."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.cli.commands.agent.mission import _commit_to_branch

pytestmark = pytest.mark.git_repo


def _run_git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _init_repo(repo: Path) -> None:
    _run_git(repo, "init")
    _run_git(repo, "config", "user.email", "test@example.com")
    _run_git(repo, "config", "user.name", "Test User")
    (repo / "plan.md").write_text("# Plan\n")
    _run_git(repo, "add", "plan.md")
    _run_git(repo, "commit", "-m", "Initial plan")
    _run_git(repo, "checkout", "-b", "mission/work")


def test_commit_to_branch_treats_empty_safe_commit_as_benign(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    plan_file = tmp_path / "plan.md"
    head_before = _run_git(tmp_path, "rev-parse", "HEAD")

    _commit_to_branch(
        plan_file,
        "001-demo",
        "plan",
        tmp_path,
        "mission/work",
        json_output=True,
    )

    assert _run_git(tmp_path, "rev-parse", "HEAD") == head_before


def test_commit_to_branch_still_commits_changed_artifact(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Plan\n\nUpdated.\n")

    _commit_to_branch(
        plan_file,
        "001-demo",
        "plan",
        tmp_path,
        "mission/work",
        json_output=True,
    )

    assert _run_git(tmp_path, "log", "-1", "--pretty=%s") == "Add plan for feature 001-demo"


def test_commit_to_branch_reraises_empty_safe_commit_shape_when_artifact_is_dirty(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Plan\n\nUpdated.\n")

    hook = tmp_path / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)

    with pytest.raises(RuntimeError, match="safe_commit: git commit failed"):
        _commit_to_branch(
            plan_file,
            "001-demo",
            "plan",
            tmp_path,
            "mission/work",
            json_output=True,
        )

    assert _run_git(tmp_path, "status", "--porcelain", "--", "plan.md") == "M plan.md"
