"""Tests for workflow auto lane transitions."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import workflow
from specify_cli.frontmatter import write_frontmatter
from specify_cli.tasks_support import extract_scalar, split_frontmatter


def write_tasks_md(feature_dir: Path, wp_id: str, subtasks: list[str], done: bool = True) -> None:
    """Write a minimal tasks.md with checkbox status for a WP."""
    checkbox = "[x]" if done else "[ ]"
    lines = [f"## {wp_id} Test", ""]
    for task_id in subtasks:
        lines.append(f"- {checkbox} {task_id} Placeholder task")
    (feature_dir / "tasks.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_wp_file(path: Path, wp_id: str, lane: str, review_status: str = "") -> None:
    """Create a minimal WP prompt file."""
    frontmatter = {
        "work_package_id": wp_id,
        "subtasks": ["T001"],
        "title": f"{wp_id} Test",
        "phase": "Phase 0",
        "lane": lane,
        "assignee": "",
        "agent": "",
        "shell_pid": "",
        "review_status": review_status,
        "reviewed_by": "",
        "dependencies": [],
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
    body = f"# {wp_id} Prompt\n\n## Activity Log\n- 2026-01-01T00:00:00Z – system – lane={lane} – Prompt created.\n"
    write_frontmatter(path, frontmatter, body)


@pytest.fixture()
def workflow_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a minimal repo root for workflow tests."""
    repo_root = tmp_path
    (repo_root / ".kittify").mkdir()
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo_root))
    monkeypatch.chdir(repo_root)
    return repo_root


def test_workflow_implement_auto_moves_to_for_review(workflow_repo: Path) -> None:
    """Implement workflow should move planned -> doing -> for_review."""
    feature_slug = "001-test-feature"
    feature_dir = workflow_repo / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    write_tasks_md(feature_dir, "WP01", ["T001"], done=True)
    wp_path = tasks_dir / "WP01-test.md"
    write_wp_file(wp_path, "WP01", lane="planned")

    runner = CliRunner()
    result = runner.invoke(workflow.app, ["implement", "WP01", "--feature", feature_slug])
    assert result.exit_code == 0

    content = wp_path.read_text(encoding="utf-8")
    frontmatter, _, _ = split_frontmatter(content)
    assert extract_scalar(frontmatter, "lane") == "for_review"


def test_workflow_review_auto_moves_to_done(workflow_repo: Path) -> None:
    """Review workflow should move for_review -> doing -> done."""
    feature_slug = "001-test-feature"
    feature_dir = workflow_repo / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    write_tasks_md(feature_dir, "WP01", ["T001"], done=True)
    wp_path = tasks_dir / "WP01-test.md"
    write_wp_file(wp_path, "WP01", lane="for_review")

    runner = CliRunner()
    result = runner.invoke(workflow.app, ["review", "WP01", "--feature", feature_slug])
    assert result.exit_code == 0

    content = wp_path.read_text(encoding="utf-8")
    frontmatter, _, _ = split_frontmatter(content)
    assert extract_scalar(frontmatter, "lane") == "done"


def test_workflow_review_moves_to_planned_on_feedback(workflow_repo: Path) -> None:
    """Review workflow should move for_review -> doing -> planned when feedback exists."""
    feature_slug = "001-test-feature"
    feature_dir = workflow_repo / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    write_tasks_md(feature_dir, "WP01", ["T001"], done=True)
    wp_path = tasks_dir / "WP01-test.md"
    write_wp_file(wp_path, "WP01", lane="for_review", review_status="has_feedback")

    runner = CliRunner()
    result = runner.invoke(workflow.app, ["review", "WP01", "--feature", feature_slug])
    assert result.exit_code == 0

    content = wp_path.read_text(encoding="utf-8")
    frontmatter, _, _ = split_frontmatter(content)
    assert extract_scalar(frontmatter, "lane") == "planned"


def test_workflow_review_rejects_non_for_review_lane(workflow_repo: Path) -> None:
    """Review workflow should error when WP is not in for_review lane."""
    feature_slug = "001-test-feature"
    feature_dir = workflow_repo / "kitty-specs" / feature_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    write_tasks_md(feature_dir, "WP01", ["T001"], done=True)
    wp_path = tasks_dir / "WP01-test.md"
    write_wp_file(wp_path, "WP01", lane="planned")

    runner = CliRunner()
    result = runner.invoke(workflow.app, ["review", "WP01", "--feature", feature_slug])
    assert result.exit_code != 0
    assert "Only for_review WPs can be reviewed" in result.output
