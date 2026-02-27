"""Regression tests for workflow review lane gating."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import workflow
from specify_cli.frontmatter import write_frontmatter
from specify_cli.tasks_support import extract_scalar, split_frontmatter


def _write_wp_file(path: Path, wp_id: str, lane: str) -> None:
    frontmatter = {
        "work_package_id": wp_id,
        "subtasks": ["T001"],
        "title": f"{wp_id} Test",
        "phase": "Phase 0",
        "lane": lane,
        "assignee": "",
        "agent": "",
        "shell_pid": "",
        "review_status": "",
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
    repo_root = tmp_path
    (repo_root / ".kittify").mkdir()
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo_root))
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.workflow._ensure_target_branch_checked_out",
        lambda repo_root, feature_slug: (repo_root, "main"),
    )
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.workflow.safe_commit",
        lambda **kwargs: True,
    )
    return repo_root


def test_workflow_review_rejects_planned_lane(workflow_repo: Path) -> None:
    feature_slug = "001-test-feature"
    tasks_dir = workflow_repo / "kitty-specs" / feature_slug / "tasks"
    tasks_dir.mkdir(parents=True)
    wp_path = tasks_dir / "WP01-test.md"
    _write_wp_file(wp_path, "WP01", lane="planned")

    result = CliRunner().invoke(
        workflow.app,
        ["review", "WP01", "--feature", feature_slug, "--agent", "test-reviewer"],
    )

    assert result.exit_code == 1
    assert "not 'for_review'" in result.stdout
    frontmatter, _, _ = split_frontmatter(wp_path.read_text(encoding="utf-8"))
    assert extract_scalar(frontmatter, "lane") == "planned"


def test_workflow_review_accepts_for_review_lane(workflow_repo: Path) -> None:
    feature_slug = "001-test-feature"
    tasks_dir = workflow_repo / "kitty-specs" / feature_slug / "tasks"
    tasks_dir.mkdir(parents=True)
    wp_path = tasks_dir / "WP01-test.md"
    _write_wp_file(wp_path, "WP01", lane="for_review")

    result = CliRunner().invoke(
        workflow.app,
        ["review", "WP01", "--feature", feature_slug, "--agent", "test-reviewer"],
    )

    assert result.exit_code == 0
    frontmatter, _, _ = split_frontmatter(wp_path.read_text(encoding="utf-8"))
    assert extract_scalar(frontmatter, "lane") == "doing"
