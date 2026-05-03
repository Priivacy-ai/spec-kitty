from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import tasks as tasks_module
from specify_cli.cli.commands.agent.tasks import app as tasks_app
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event, read_events
from tests.lane_test_utils import write_single_lane_manifest

pytestmark = pytest.mark.git_repo


def _json_payload(output: str) -> dict:
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("{"):
            return json.loads(stripped)
    raise AssertionError(f"No JSON payload found in output:\n{output}")


@pytest.fixture
def in_review_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True)
    (repo / ".kittify").mkdir()
    (repo / ".kittify" / "config.yaml").write_text("auto_commit: false\n", encoding="utf-8")

    mission_slug = "001-reject-from-in-review"
    feature_dir = repo / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    write_single_lane_manifest(feature_dir, wp_ids=("WP01",))
    (feature_dir / "tasks.md").write_text(
        "### WP01 - Core\n\n- [x] T001 Done\n",
        encoding="utf-8",
    )
    (tasks_dir / "WP01-core.md").write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Core\n"
        "agent: reviewer\n"
        "shell_pid: ''\n"
        "subtasks:\n"
        "- T001\n"
        "dependencies: []\n"
        "---\n\n# WP01\n",
        encoding="utf-8",
    )
    for idx, lane in enumerate(
        [Lane.PLANNED, Lane.CLAIMED, Lane.IN_PROGRESS, Lane.FOR_REVIEW, Lane.IN_REVIEW],
        start=1,
    ):
        from_lane = Lane.PLANNED if idx == 1 else [
            Lane.PLANNED,
            Lane.CLAIMED,
            Lane.IN_PROGRESS,
            Lane.FOR_REVIEW,
        ][idx - 2]
        append_event(
            feature_dir,
            StatusEvent(
                event_id=f"seed-{idx}",
                mission_slug=mission_slug,
                wp_id="WP01",
                from_lane=from_lane,
                to_lane=lane,
                at=f"2026-01-01T00:00:0{idx}+00:00",
                actor="fixture",
                force=True,
                execution_mode="worktree",
            ),
        )

    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed in_review fixture"], cwd=repo, check=True, capture_output=True)
    monkeypatch.chdir(repo)
    monkeypatch.setattr(tasks_module, "locate_project_root", lambda: repo)
    monkeypatch.setattr(tasks_module, "_validate_ready_for_review", lambda *_args, **_kwargs: (True, []))
    return repo, mission_slug, feature_dir


@patch("specify_cli.cli.commands.agent.tasks.get_mission_type", return_value="software-dev")
def test_move_task_rejects_from_in_review_with_canonical_review_result(
    _mock_mission: Mock,
    in_review_repo: tuple[Path, str, Path],
) -> None:
    repo, mission_slug, feature_dir = in_review_repo
    feedback = repo / "feedback.md"
    feedback.write_text("**Issue**: The reviewer rejected this WP.\n", encoding="utf-8")

    result = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "planned",
            "--mission",
            mission_slug,
            "--review-feedback-file",
            str(feedback),
            "--agent",
            "reviewer",
            "--json",
            "--no-auto-commit",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = _json_payload(result.stdout)
    pointer = payload["review_feedback"]
    assert pointer == "review-cycle://001-reject-from-in-review/WP01-core/review-cycle-1.md"
    events = read_events(feature_dir)
    assert events[-1].from_lane == Lane.IN_REVIEW
    assert events[-1].to_lane == Lane.PLANNED
    assert events[-1].review_ref == pointer
    assert (feature_dir / "tasks" / "WP01-core" / "review-cycle-1.md").is_file()


@patch("specify_cli.cli.commands.agent.tasks.get_mission_type", return_value="software-dev")
def test_empty_feedback_fails_before_status_mutation(
    _mock_mission: Mock,
    in_review_repo: tuple[Path, str, Path],
) -> None:
    repo, mission_slug, feature_dir = in_review_repo
    feedback = repo / "feedback.md"
    feedback.write_text(" \n", encoding="utf-8")
    before = len(read_events(feature_dir))

    result = CliRunner().invoke(
        tasks_app,
        [
            "move-task",
            "WP01",
            "--to",
            "planned",
            "--mission",
            mission_slug,
            "--review-feedback-file",
            str(feedback),
            "--agent",
            "reviewer",
            "--json",
            "--no-auto-commit",
        ],
    )

    assert result.exit_code == 1
    assert "Review feedback file is empty" in _json_payload(result.stdout)["error"]
    assert len(read_events(feature_dir)) == before
    assert not (feature_dir / "tasks" / "WP01-core" / "review-cycle-1.md").exists()
