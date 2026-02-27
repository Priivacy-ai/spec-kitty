"""2.x tests for workflow implement review feedback pointer guidance."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from tests.branch_contract import IS_2X_BRANCH
from specify_cli.cli.commands.agent import workflow
from specify_cli.frontmatter import write_frontmatter

pytestmark = pytest.mark.skipif(not IS_2X_BRANCH, reason="2.x-only review feedback pointer contract")


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


def _wp_path(repo: Path) -> Path:
    return repo / "kitty-specs" / "001-test-feature" / "tasks" / "WP01-test-task.md"


def _write_wp(
    wp_path: Path,
    *,
    lane: str,
    review_status: str,
    review_feedback: str,
    reviewed_by: str = "reviewer",
) -> None:
    wp_frontmatter = {
        "work_package_id": "WP01",
        "subtasks": ["T001"],
        "title": "Test Task",
        "phase": "Phase 1",
        "lane": lane,
        "dependencies": [],
        "assignee": "",
        "agent": "test-agent",
        "shell_pid": "",
        "review_status": review_status,
        "reviewed_by": reviewed_by,
        "review_feedback": review_feedback,
        "history": [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "lane": lane,
                "agent": "system",
                "shell_pid": "",
                "action": "Prompt created",
            }
        ],
    }
    wp_body = (
        "# WP01 Prompt\n\n## Activity Log\n"
        f"- 2026-01-01T00:00:00Z – system – lane={lane} – Prompt created.\n"
    )
    write_frontmatter(wp_path, wp_frontmatter, wp_body)


@pytest.fixture()
def workflow_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True)

    (repo / ".kittify").mkdir()

    feature_slug = "001-test-feature"
    feature_dir = repo / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "tasks.md").write_text("## WP01 Test\n\n- [x] T001 Placeholder task\n", encoding="utf-8")

    feedback_rel = "001-test-feature/WP01/20260227T120000Z-ab12cd34.md"
    feedback_pointer = f"feedback://{feedback_rel}"
    feedback_file = _git_common_dir(repo) / "spec-kitty" / "feedback" / feedback_rel
    feedback_file.parent.mkdir(parents=True, exist_ok=True)
    feedback_file.write_text("**Issue**: Fix retry handling\n", encoding="utf-8")

    _write_wp(
        _wp_path(repo),
        lane="in_progress",
        review_status="has_feedback",
        review_feedback=feedback_pointer,
    )

    workspace = repo / ".worktrees" / f"{feature_slug}-WP01"
    workspace.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed workflow fixture"], cwd=repo, check=True, capture_output=True)

    monkeypatch.chdir(repo)
    return repo, feedback_pointer, feedback_file


def test_implement_prompt_uses_feedback_pointer(workflow_repo: tuple[Path, str, Path]):
    _repo, feedback_pointer, feedback_file = workflow_repo
    runner = CliRunner()

    result = runner.invoke(
        workflow.app,
        ["implement", "WP01", "--feature", "001-test-feature", "--agent", "test-agent"],
    )

    assert result.exit_code == 0, result.stdout
    assert f"Has review feedback - read reference: {feedback_pointer}" in result.stdout

    prompt_file = Path(tempfile.gettempdir()) / "spec-kitty-implement-WP01.md"
    assert prompt_file.exists(), f"Prompt file not found: {prompt_file}"
    prompt_content = prompt_file.read_text(encoding="utf-8")
    assert f"Canonical feedback reference: {feedback_pointer}" in prompt_content
    assert f'Read it first: cat "{feedback_file}"' in prompt_content


@pytest.mark.parametrize(
    "error",
    [
        subprocess.CalledProcessError(1, ["git", "rev-parse", "--git-common-dir"]),
        FileNotFoundError("git"),
    ],
)
def test_resolve_git_common_dir_returns_none_on_subprocess_errors(error: Exception):
    with patch("specify_cli.cli.commands.agent.workflow.subprocess.run", side_effect=error):
        assert workflow._resolve_git_common_dir(Path("/tmp/repo")) is None


def test_resolve_git_common_dir_returns_none_for_blank_output():
    completed = subprocess.CompletedProcess(args=["git"], returncode=0, stdout="\n", stderr="")
    with patch("specify_cli.cli.commands.agent.workflow.subprocess.run", return_value=completed):
        assert workflow._resolve_git_common_dir(Path("/tmp/repo")) is None


def test_resolve_feedback_pointer_handles_blank_and_legacy_missing(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()

    assert workflow._resolve_review_feedback_pointer(repo, "   ") is None

    with patch.object(workflow, "_resolve_git_common_dir", return_value=None):
        assert workflow._resolve_review_feedback_pointer(
            repo,
            "feedback://001-test-feature/WP01/file.md",
        ) is None

    assert workflow._resolve_review_feedback_pointer(repo, "relative/path/that/does-not-exist.md") is None


def test_implement_prompt_warns_when_feedback_pointer_artifact_is_missing(
    workflow_repo: tuple[Path, str, Path]
):
    repo, feedback_pointer, feedback_file = workflow_repo
    _write_wp(
        _wp_path(repo),
        lane="doing",
        review_status="has_feedback",
        review_feedback=feedback_pointer,
    )
    feedback_file.unlink()

    runner = CliRunner()
    result = runner.invoke(workflow.app, ["implement", "WP01", "--feature", "001-test-feature"])

    assert result.exit_code == 0, result.stdout
    prompt_file = Path(tempfile.gettempdir()) / "spec-kitty-implement-WP01.md"
    prompt_content = prompt_file.read_text(encoding="utf-8")
    assert "WARNING: review feedback reference is set, but the artifact is missing/unreadable." in prompt_content
    assert "Ask reviewer to re-run move-task with --review-feedback-file." in prompt_content


def test_implement_prompt_warns_when_review_status_has_feedback_without_reference(
    workflow_repo: tuple[Path, str, Path]
):
    repo, _feedback_pointer, _feedback_file = workflow_repo
    _write_wp(
        _wp_path(repo),
        lane="doing",
        review_status="has_feedback",
        review_feedback="",
    )

    runner = CliRunner()
    result = runner.invoke(workflow.app, ["implement", "WP01", "--feature", "001-test-feature"])

    assert result.exit_code == 0, result.stdout
    assert "Has review feedback - but no review_feedback reference is set" in result.stdout

    prompt_file = Path(tempfile.gettempdir()) / "spec-kitty-implement-WP01.md"
    prompt_content = prompt_file.read_text(encoding="utf-8")
    assert "WARNING: review_status=has_feedback but no review_feedback reference is set." in prompt_content
    assert "Ask reviewer to re-run move-task with --review-feedback-file." in prompt_content


def test_review_prompt_mentions_shared_git_common_dir_feedback_storage(
    workflow_repo: tuple[Path, str, Path]
):
    repo, feedback_pointer, _feedback_file = workflow_repo
    _write_wp(
        _wp_path(repo),
        lane="doing",
        review_status="has_feedback",
        review_feedback=feedback_pointer,
    )

    runner = CliRunner()
    result = runner.invoke(workflow.app, ["review", "WP01", "--feature", "001-test-feature"])

    assert result.exit_code == 0, result.stdout
    prompt_file = Path(tempfile.gettempdir()) / "spec-kitty-review-WP01.md"
    prompt_content = prompt_file.read_text(encoding="utf-8")
    assert (
        "move-task stores feedback in shared git common-dir and writes frontmatter review_feedback pointer"
        in prompt_content
    )
