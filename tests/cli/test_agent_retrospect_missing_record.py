from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import app
from specify_cli.context.mission_resolver import ResolvedMission
from specify_cli.doctrine_synthesizer import SynthesisResult
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event
from tests.lane_test_utils import write_single_lane_manifest

pytestmark = pytest.mark.git_repo

runner = CliRunner()
MISSION_ID = "01KQ6YEG000000000000000000"
MISSION_SLUG = "001-retro-missing"


def _resolved(feature_dir: Path) -> ResolvedMission:
    return ResolvedMission(
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
        mid8=MISSION_ID[:8],
        feature_dir=feature_dir,
    )


def _empty_result() -> SynthesisResult:
    return SynthesisResult(
        dry_run=True,
        planned=[],
        applied=[],
        conflicts=[],
        rejected=[],
        events_emitted=[],
    )


def _completed_mission(repo: Path) -> Path:
    feature_dir = repo / "kitty-specs" / MISSION_SLUG
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
    write_single_lane_manifest(feature_dir, wp_ids=("WP01",))
    (tasks_dir / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ndependencies: []\ntitle: WP01\n---\n# WP01\n",
        encoding="utf-8",
    )
    append_event(
        feature_dir,
        StatusEvent(
            event_id="seed-WP01-done",
            mission_slug=MISSION_SLUG,
            wp_id="WP01",
            from_lane=Lane.APPROVED,
            to_lane=Lane.DONE,
            at="2026-01-01T00:00:00+00:00",
            actor="fixture",
            force=True,
            execution_mode="worktree",
        ),
    )
    return feature_dir


def test_missing_record_completed_mission_creates_record_and_returns_json(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".kittify").mkdir()
    feature_dir = _completed_mission(repo)

    with (
        patch("specify_cli.cli.commands.agent_retrospect.locate_project_root", return_value=repo),
        patch("specify_cli.cli.commands.agent_retrospect.resolve_mission_handle", return_value=_resolved(feature_dir)),
        patch("specify_cli.cli.commands.agent_retrospect.apply_proposals", return_value=_empty_result()),
    ):
        result = runner.invoke(app, ["retrospect", "synthesize", "--mission", MISSION_ID[:8], "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["outcome"] == "retrospective_record_created"
    assert payload["result"]["planned"] == []
    assert (repo / ".kittify" / "missions" / MISSION_ID / "retrospective.yaml").is_file()


def test_missing_record_insufficient_artifacts_returns_parseable_json(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".kittify").mkdir()
    feature_dir = repo / "kitty-specs" / MISSION_SLUG
    feature_dir.mkdir(parents=True)

    with (
        patch("specify_cli.cli.commands.agent_retrospect.locate_project_root", return_value=repo),
        patch("specify_cli.cli.commands.agent_retrospect.resolve_mission_handle", return_value=_resolved(feature_dir)),
    ):
        result = runner.invoke(app, ["retrospect", "synthesize", "--mission", MISSION_ID[:8], "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["outcome"] == "insufficient_mission_artifacts"
    assert payload["error"] == "record_not_found"


def test_existing_record_json_includes_synthesized_outcome(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".kittify").mkdir()
    feature_dir = _completed_mission(repo)

    with (
        patch("specify_cli.cli.commands.agent_retrospect.locate_project_root", return_value=repo),
        patch("specify_cli.cli.commands.agent_retrospect.resolve_mission_handle", return_value=_resolved(feature_dir)),
        patch("specify_cli.cli.commands.agent_retrospect.apply_proposals", return_value=_empty_result()),
    ):
        first = runner.invoke(app, ["retrospect", "synthesize", "--mission", MISSION_ID[:8], "--json"])
        second = runner.invoke(app, ["retrospect", "synthesize", "--mission", MISSION_ID[:8], "--json"])

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    payload = json.loads(second.output)
    assert payload["outcome"] == "retrospective_synthesized"
