"""2.x tests for review feedback pointer persistence and resolution."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.branch_contract import IS_2X_BRANCH
from specify_cli.cli.commands.agent.tasks import _persist_review_feedback
from specify_cli.cli.commands.agent.workflow import _resolve_review_feedback_pointer

pytestmark = pytest.mark.skipif(not IS_2X_BRANCH, reason="2.x-only review feedback pointer contract")


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True)
    return repo


def _git_common_dir(repo: Path) -> Path:
    raw_value = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    common_dir = Path(raw_value)
    if not common_dir.is_absolute():
        common_dir = (repo / common_dir).resolve()
    return common_dir


def test_persist_feedback_uses_git_common_dir_and_pointer(git_repo: Path, tmp_path: Path):
    source = tmp_path / "feedback.md"
    source.write_text("**Issue**: Add test coverage\n", encoding="utf-8")

    persisted_path, pointer = _persist_review_feedback(
        main_repo_root=git_repo,
        feature_slug="001-test-feature",
        task_id="WP01",
        feedback_source=source,
    )

    common_dir = _git_common_dir(git_repo)
    assert pointer.startswith("feedback://001-test-feature/WP01/")
    assert persisted_path.parent == common_dir / "spec-kitty" / "feedback" / "001-test-feature" / "WP01"
    assert persisted_path.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")


def test_resolve_feedback_pointer_from_common_dir(git_repo: Path, tmp_path: Path):
    source = tmp_path / "feedback.md"
    source.write_text("**Issue**: Fix edge case\n", encoding="utf-8")

    persisted_path, pointer = _persist_review_feedback(
        main_repo_root=git_repo,
        feature_slug="001-test-feature",
        task_id="WP02",
        feedback_source=source,
    )

    resolved = _resolve_review_feedback_pointer(git_repo, pointer)
    assert resolved == persisted_path.resolve()


def test_resolve_feedback_pointer_rejects_invalid_shape(git_repo: Path):
    assert _resolve_review_feedback_pointer(git_repo, "feedback://bad-shape") is None

