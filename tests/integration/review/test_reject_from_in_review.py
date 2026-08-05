from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import tasks as tasks_module
from specify_cli.cli.commands.agent.tasks import app as tasks_app
from specify_cli.review.artifacts import ReviewCycleArtifact
from specify_cli.status.models import (
    InnerStateChanged,
    Lane,
    ReviewOverride,
    StatusEvent,
    WPInnerStateDelta,
)
from specify_cli.status.reducer import materialize_snapshot
from specify_cli.status.store import (
    append_annotations_atomic_verified,
    append_event,
    read_events,
)
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


@patch("specify_cli.cli.commands.agent.tasks.get_mission_type", return_value="software-dev")
def test_move_task_reject_threads_declared_reviewer_into_artifact(
    _mock_mission: Mock,
    in_review_repo: tuple[Path, str, Path],
) -> None:
    """The ``--reviewer`` option must be threaded into the rejected review-cycle
    artifact's ``reviewer_agent`` frontmatter.

    ``--agent`` names the WP *actor* driving the CLI invocation (which may be
    the reviewer's own tooling identity, an orchestrator, or a bot); it is not
    the same fact as the reviewer's declared identity. Declaring a distinct
    ``--reviewer`` must win over both ``--agent`` and the ``"unknown"``
    fallback in ``create_rejected_review_cycle``.
    """
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
            "orchestrator-bot",
            "--reviewer",
            "reviewer-renata",
            "--json",
            "--no-auto-commit",
        ],
    )

    assert result.exit_code == 0, result.stdout
    artifact_path = feature_dir / "tasks" / "WP01-core" / "review-cycle-1.md"
    assert artifact_path.is_file()
    artifact = ReviewCycleArtifact.from_file(artifact_path)
    assert artifact.reviewer_agent == "reviewer-renata", (
        "expected the rejected review-cycle artifact to record the declared "
        f"--reviewer identity 'reviewer-renata', got {artifact.reviewer_agent!r}. "
        f"CLI stdout:\n{result.stdout}"
    )


@patch("specify_cli.cli.commands.agent.tasks.get_mission_type", return_value="software-dev")
def test_rollback_to_planned_supersedes_stale_review_override_slot(
    _mock_mission: Mock,
    in_review_repo: tuple[Path, str, Path],
) -> None:
    """A ``--to planned`` rejection rollback must supersede a stale ``review``
    override slot in the materialized snapshot.

    The ``review`` runtime slot is written by ``_persist_review_artifact_override``
    when an operator overrides (approves past) a rejected review-cycle -- it is
    durable evidence that a REJECTED verdict was superseded by an approval. Once
    a *fresh* real rejection lands (``move-task --to planned`` with a new
    ``--review-feedback-file``), that prior "superseded by approval" note is
    itself stale: the WP is back in ``planned`` with a brand-new rejection, not
    an approved-override state. A reader of ``status.json`` must not see the
    withdrawn approval evidence survive onto the rolled-back WP.
    """
    repo, mission_slug, feature_dir = in_review_repo

    # Seed a stale "review override" annotation as if an earlier cycle's
    # rejection had been approved past via an operator override.
    append_annotations_atomic_verified(
        feature_dir,
        [
            InnerStateChanged(
                event_id="01KZ80AAAAAAAAAAAAAAAAAAAA",
                wp_id="WP01",
                at="2026-01-01T00:00:06+00:00",
                actor="operator",
                delta=WPInnerStateDelta(
                    review=ReviewOverride(
                        at="2026-01-01T00:00:06Z",
                        actor="operator",
                        wp_id="WP01",
                        reason="approved despite rejected review-cycle-1",
                    )
                ),
            )
        ],
    )
    before_snapshot = materialize_snapshot(feature_dir)
    before_review = before_snapshot.work_packages["WP01"].get("review")
    assert before_review is not None, "fixture setup did not seed the stale review override"

    feedback = repo / "feedback.md"
    feedback.write_text("**Issue**: A fresh rejection after the override.\n", encoding="utf-8")

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

    status_json_path = feature_dir / "status.json"
    assert status_json_path.is_file()
    status_payload = json.loads(status_json_path.read_text(encoding="utf-8"))
    wp_state = status_payload["work_packages"]["WP01"]
    assert wp_state.get("lane") == "planned"
    assert wp_state.get("review") is None, (
        "expected the stale approval-override 'review' slot to be superseded by "
        f"the fresh rejection, but status.json still reports {wp_state.get('review')!r}"
    )
