"""Unit coverage for ``_baseline_artifact_needs_commit`` (#2895).

The baseline-capture commit must be skipped when the artifact is already
committed and unchanged (a resume of an already-captured WP), so a no-op
``git commit`` never raises "nothing to commit" and logs a misleading
best-effort warning on every resume.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.cli.commands.agent.workflow_executor import _baseline_artifact_needs_commit

pytestmark = [pytest.mark.git_repo]


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "T")
    _git(repo, "config", "commit.gpgsign", "false")
    return repo


def test_untracked_artifact_needs_commit(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    artifact = repo / "tasks" / "WP01" / "baseline-tests.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}\n", encoding="utf-8")

    assert _baseline_artifact_needs_commit(repo, artifact) is True


def test_committed_unchanged_artifact_does_not_need_commit(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    artifact = repo / "tasks" / "WP01" / "baseline-tests.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "baseline")

    # The resume case: already committed, no working-tree change -> skip.
    assert _baseline_artifact_needs_commit(repo, artifact) is False


def test_modified_tracked_artifact_needs_commit(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    artifact = repo / "tasks" / "WP01" / "baseline-tests.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "baseline")
    artifact.write_text('{"changed": true}\n', encoding="utf-8")

    assert _baseline_artifact_needs_commit(repo, artifact) is True


def test_non_repo_degrades_to_attempting_commit(tmp_path: Path) -> None:
    # Not a git repo: fall back to attempting the commit (prior behaviour),
    # never crash the best-effort capture path.
    artifact = tmp_path / "baseline-tests.json"
    artifact.write_text("{}\n", encoding="utf-8")

    assert _baseline_artifact_needs_commit(tmp_path, artifact) is True
