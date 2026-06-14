"""Tests for the templated bare-repo fixture (WP06 / A3 / PP-03)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests._support.git_template import (
    _template_repo,
    clone_template,
    templated_repo,  # noqa: F401  (re-exported so consumers import it from here)
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _git_out(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_template_is_bare_with_single_commit() -> None:
    """The cached template is a bare repo carrying exactly one initial commit."""
    template = _template_repo()
    assert template.name.endswith(".git")
    is_bare = _git_out("rev-parse", "--is-bare-repository", cwd=template)
    assert is_bare == "true"
    log = _git_out("log", "--oneline", cwd=template)
    assert log.count("\n") == 0  # exactly one commit
    assert "Initial commit" in log


def test_template_is_cached_per_process() -> None:
    """Repeated calls return the same template path (build-once semantics)."""
    assert _template_repo() == _template_repo()


def test_clone_template_yields_clean_working_repo(tmp_path: Path) -> None:
    """A clone is a non-bare working tree on ``main`` with a clean status."""
    repo = clone_template(tmp_path / "checkout")
    assert repo.is_dir()
    assert (repo / "README.md").is_file()
    assert _git_out("rev-parse", "--is-bare-repository", cwd=repo) == "false"
    assert _git_out("rev-parse", "--abbrev-ref", "HEAD", cwd=repo) == "main"
    assert _git_out("status", "--porcelain", cwd=repo) == ""


def test_clone_template_allows_immediate_commit(tmp_path: Path) -> None:
    """The clone has an identity configured so ``git commit`` works at once."""
    repo = clone_template(tmp_path / "checkout")
    (repo / "new.txt").write_text("work\n", encoding="utf-8")
    subprocess.run(["git", "add", "new.txt"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add file"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    log = _git_out("log", "--oneline", cwd=repo)
    assert "add file" in log


def test_templated_repo_fixture(templated_repo: Path) -> None:  # noqa: F811
    """The fixture yields a ready-to-use working repo under ``tmp_path``."""
    assert templated_repo.is_dir()
    assert (templated_repo / "README.md").is_file()
    assert _git_out("status", "--porcelain", cwd=templated_repo) == ""
