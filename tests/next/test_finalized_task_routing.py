from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.next.decision import DecisionKind
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event
from tests.lane_test_utils import write_single_lane_manifest

pytestmark = pytest.mark.git_repo


def _init_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True)


def _scaffold(repo: Path, wps: dict[str, Lane]) -> tuple[Path, str]:
    _init_repo(repo)
    (repo / ".kittify").mkdir()
    mission_slug = "001-finalized-routing"
    feature_dir = repo / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(json.dumps({"mission_type": "software-dev"}), encoding="utf-8")
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
    write_single_lane_manifest(feature_dir, wp_ids=tuple(wps.keys()))
    for wp_id, lane in wps.items():
        (tasks_dir / f"{wp_id}.md").write_text(
            f"---\nwork_package_id: {wp_id}\ndependencies: []\ntitle: {wp_id}\n---\n# {wp_id}\n",
            encoding="utf-8",
        )
        append_event(
            feature_dir,
            StatusEvent(
                event_id=f"seed-{wp_id}-{lane}",
                mission_slug=mission_slug,
                wp_id=wp_id,
                from_lane=Lane.PLANNED,
                to_lane=lane,
                at="2026-01-01T00:00:00+00:00",
                actor="fixture",
                force=True,
                execution_mode="worktree",
            ),
        )
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed finalized routing"], cwd=repo, check=True, capture_output=True)
    return feature_dir, mission_slug


def test_query_prefers_finalized_planned_wps_over_discovery(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _, mission_slug = _scaffold(repo, {"WP01": Lane.PLANNED})

    from specify_cli.next.runtime_bridge import query_current_state

    decision = query_current_state("codex", mission_slug, repo)

    assert decision.kind == DecisionKind.query
    assert decision.mission_state == "implement"
    assert decision.preview_step == "implement"


def test_query_routes_finalized_for_review_wps_to_review(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _, mission_slug = _scaffold(repo, {"WP01": Lane.FOR_REVIEW})

    from specify_cli.next.runtime_bridge import query_current_state

    decision = query_current_state("codex", mission_slug, repo)

    assert decision.kind == DecisionKind.query
    assert decision.mission_state == "review"
    assert decision.preview_step == "review"


def test_query_blocks_finalized_in_review_wps_without_discovery(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _, mission_slug = _scaffold(repo, {"WP01": Lane.IN_REVIEW})

    from specify_cli.next.runtime_bridge import query_current_state

    decision = query_current_state("codex", mission_slug, repo)

    assert decision.kind == DecisionKind.query
    assert decision.mission_state == "blocked"
    assert decision.preview_step is None
    assert decision.reason == "review in progress"


def test_query_marks_all_done_finalized_wps_terminal_without_discovery(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _, mission_slug = _scaffold(repo, {"WP01": Lane.DONE, "WP02": Lane.DONE})

    from specify_cli.next.runtime_bridge import query_current_state

    decision = query_current_state("codex", mission_slug, repo)

    assert decision.kind == DecisionKind.query
    assert decision.mission_state == "done"
    assert decision.preview_step is None
    assert decision.reason == "All work packages are done"


def test_finalized_for_review_routes_to_review(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    feature_dir, _ = _scaffold(repo, {"WP01": Lane.FOR_REVIEW})

    from specify_cli.next.runtime_bridge import _finalized_task_board_override_step
    from specify_cli.next.decision import _compute_wp_progress

    assert _finalized_task_board_override_step(feature_dir, _compute_wp_progress(feature_dir)) == "review"


def test_finalized_done_is_terminal(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    feature_dir, _ = _scaffold(repo, {"WP01": Lane.DONE, "WP02": Lane.DONE})

    from specify_cli.next.runtime_bridge import _finalized_task_board_override_step
    from specify_cli.next.decision import _compute_wp_progress

    assert _finalized_task_board_override_step(feature_dir, _compute_wp_progress(feature_dir)) == "done"


def test_finalized_in_review_is_blocked_not_discovery(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    feature_dir, _ = _scaffold(repo, {"WP01": Lane.IN_REVIEW})

    from specify_cli.next.runtime_bridge import _finalized_task_board_override_step
    from specify_cli.next.decision import _compute_wp_progress

    assert _finalized_task_board_override_step(feature_dir, _compute_wp_progress(feature_dir)) == "blocked:review_in_progress"
