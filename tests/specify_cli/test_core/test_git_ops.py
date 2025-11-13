import os
import sys
from pathlib import Path

import pytest

from specify_cli.core.git_ops import (
    get_current_branch,
    init_git_repo,
    is_git_repo,
    run_command,
)


def test_run_command_captures_stdout():
    code, stdout, stderr = run_command(
        [sys.executable, "-c", "print('hello world')"],
        capture=True,
    )
    assert code == 0
    assert stdout == "hello world"
    assert stderr == ""


def test_run_command_allows_nonzero_when_not_checking():
    code, stdout, stderr = run_command(
        [sys.executable, "-c", "import sys; sys.exit(3)"],
        check_return=False,
    )
    assert code == 3
    assert stdout == ""
    assert stderr == ""


@pytest.mark.usefixtures("_git_identity")
def test_git_repo_lifecycle(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    project.mkdir()
    (project / "README.md").write_text("hello", encoding="utf-8")

    assert is_git_repo(project) is False
    assert init_git_repo(project, quiet=True) is True
    assert is_git_repo(project) is True

    branch = get_current_branch(project)
    assert branch


@pytest.fixture(name="_git_identity")
def git_identity_fixture(monkeypatch):
    """Ensure git commands can commit even if the user has no global config."""
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Spec Kitty")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "spec@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Spec Kitty")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "spec@example.com")
