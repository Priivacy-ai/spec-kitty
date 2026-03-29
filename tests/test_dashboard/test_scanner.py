import json
from pathlib import Path

from specify_cli.dashboard import scanner
from specify_cli.dashboard.constitution_path import resolve_project_constitution_path
from specify_cli.core.mission_detection import MissionContext
import pytest
pytestmark = pytest.mark.fast



def _create_mission(tmp_path: Path, slug: str = "001-demo-mission") -> Path:
    mission_dir = tmp_path / "kitty-specs" / slug
    (mission_dir / "tasks" / "planned").mkdir(parents=True)
    (mission_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (mission_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (mission_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")

    prompt = """---
work_package_id: WP01
lane: planned
subtasks: ["T1"]
agent: codex
---
# Work Package Prompt: Demo

Body
"""
    (mission_dir / "tasks" / "planned" / "WP01-demo.md").write_text(prompt, encoding="utf-8")
    return mission_dir


def test_scan_all_missions_detects_mission(tmp_path):
    mission_dir = _create_mission(tmp_path)
    missions = scanner.scan_all_missions(tmp_path)
    assert missions, "Expected at least one mission"
    assert missions[0]["id"] == mission_dir.name
    assert missions[0]["artifacts"]["spec"]


def test_scan_all_missions_builds_switcher_display_name(tmp_path):
    mission_dir = _create_mission(tmp_path)
    (mission_dir / "meta.json").write_text(
        json.dumps({"friendly_name": "Demo Mission"}),
        encoding="utf-8",
    )

    missions = scanner.scan_all_missions(tmp_path)

    assert missions[0]["name"] == "Demo Mission"
    assert missions[0]["display_name"] == "001 - Demo Mission"


def test_scan_all_missions_display_name_avoids_duplicate_prefix(tmp_path):
    mission_dir = _create_mission(tmp_path)
    (mission_dir / "meta.json").write_text(
        json.dumps({"friendly_name": "001 - Demo Mission"}),
        encoding="utf-8",
    )

    missions = scanner.scan_all_missions(tmp_path)

    assert missions[0]["display_name"] == "001 - Demo Mission"


def test_scan_mission_kanban_returns_prompt(tmp_path):
    mission_dir = _create_mission(tmp_path)
    lanes = scanner.scan_mission_kanban(tmp_path, mission_dir.name)
    assert "planned" in lanes
    assert lanes["planned"], "planned lane should contain prompt data"
    task = lanes["planned"][0]
    assert task["id"] == "WP01"
    assert "prompt_markdown" in task


def test_resolve_active_mission_uses_core_detector(tmp_path, monkeypatch):
    missions = [
        {"id": "009-old-mission"},
        {"id": "010-new-mission"},
    ]

    def _fake_detect_mission(*_args, **_kwargs):
        return MissionContext(
            slug="010-new-mission",
            number="010",
            name="new-mission",
            directory=tmp_path / "kitty-specs" / "010-new-mission",
            detection_method="single_auto",
        )

    monkeypatch.setattr(scanner, "detect_mission", _fake_detect_mission)

    resolved = scanner.resolve_active_mission(tmp_path, missions)
    assert resolved is not None
    assert resolved["id"] == "010-new-mission"


def test_resolve_active_mission_falls_back_to_first(tmp_path, monkeypatch):
    missions = [
        {"id": "009-old-mission"},
        {"id": "010-new-mission"},
    ]

    monkeypatch.setattr(scanner, "detect_mission", lambda *_args, **_kwargs: None)
    resolved = scanner.resolve_active_mission(tmp_path, missions)
    assert resolved is not None
    assert resolved["id"] == "009-old-mission"


def test_project_constitution_propagates_to_all_missions(tmp_path):
    _create_mission(tmp_path, "001-demo-mission")
    _create_mission(tmp_path, "002-another-mission")
    constitution = tmp_path / ".kittify" / "constitution" / "constitution.md"
    constitution.parent.mkdir(parents=True)
    constitution.write_text("# Project Constitution\n", encoding="utf-8")

    missions = scanner.scan_all_missions(tmp_path)
    assert len(missions) == 2
    assert all(mission["artifacts"]["constitution"]["exists"] for mission in missions)


def test_mission_local_constitution_is_ignored_without_project_constitution(tmp_path):
    first = _create_mission(tmp_path, "001-demo-mission")
    _create_mission(tmp_path, "002-another-mission")
    (first / "constitution.md").write_text("# Legacy Mission Constitution\n", encoding="utf-8")

    missions = scanner.scan_all_missions(tmp_path)
    assert len(missions) == 2
    assert all(not mission["artifacts"]["constitution"]["exists"] for mission in missions)


def test_legacy_constitution_path_supported(tmp_path):
    _create_mission(tmp_path, "001-demo-mission")
    _create_mission(tmp_path, "002-another-mission")
    legacy = tmp_path / ".kittify" / "memory" / "constitution.md"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("# Legacy Project Constitution\n", encoding="utf-8")

    missions = scanner.scan_all_missions(tmp_path)
    assert len(missions) == 2
    assert all(mission["artifacts"]["constitution"]["exists"] for mission in missions)


def test_new_path_preferred_when_both_exist(tmp_path):
    _create_mission(tmp_path)
    new_path = tmp_path / ".kittify" / "constitution" / "constitution.md"
    legacy_path = tmp_path / ".kittify" / "memory" / "constitution.md"
    new_path.parent.mkdir(parents=True)
    legacy_path.parent.mkdir(parents=True)
    new_path.write_text("new", encoding="utf-8")
    legacy_path.write_text("legacy", encoding="utf-8")

    resolved = resolve_project_constitution_path(tmp_path)
    assert resolved == new_path


def test_scan_mission_kanban_approved_lane(tmp_path):
    """WPs with lane: approved should land in the approved column, not planned."""
    mission_dir = tmp_path / "kitty-specs" / "001-demo"
    (mission_dir / "tasks").mkdir(parents=True)
    (mission_dir / "tasks" / "WP01.md").write_text(
        "---\nwork_package_id: WP01\nlane: approved\n---\n# Work Package Prompt: WP01\n",
        encoding="utf-8",
    )
    lanes = scanner.scan_mission_kanban(tmp_path, "001-demo")
    assert len(lanes["approved"]) == 1
    assert len(lanes["planned"]) == 0
    assert lanes["approved"][0]["id"] == "WP01"


def test_scan_mission_kanban_lane_mapping(tmp_path):
    """claimed maps to planned, in_progress maps to doing."""
    mission_dir = tmp_path / "kitty-specs" / "001-demo"
    (mission_dir / "tasks").mkdir(parents=True)
    for wp_id, lane in [("WP01", "claimed"), ("WP02", "in_progress")]:
        (mission_dir / "tasks" / f"{wp_id}.md").write_text(
            f"---\nwork_package_id: {wp_id}\nlane: {lane}\n---\n# Work Package Prompt: {wp_id}\n",
            encoding="utf-8",
        )
    lanes = scanner.scan_mission_kanban(tmp_path, "001-demo")
    assert len(lanes["planned"]) == 1  # claimed -> planned
    assert len(lanes["doing"]) == 1  # in_progress -> doing
