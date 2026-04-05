import json
from pathlib import Path

import pytest

from specify_cli.dashboard import scanner
from specify_cli.dashboard.charter_path import resolve_project_charter_path
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.reducer import materialize
from specify_cli.status.store import append_event

pytestmark = pytest.mark.fast


def _set_wp_lane(feature_dir: Path, wp_id: str, lane: str) -> None:
    append_event(
        feature_dir,
        StatusEvent(
            event_id=f"TEST{wp_id}{lane.upper()}0000000000000000"[:26],
            feature_slug=feature_dir.name,
            wp_id=wp_id,
            from_lane=Lane.PLANNED,
            to_lane=Lane(lane),
            at="2026-03-31T09:00:00+00:00",
            actor="test",
            force=True,
            execution_mode="direct_repo",
        ),
    )
    materialize(feature_dir)


def _create_feature(tmp_path: Path, slug: str = "001-demo-feature", *, lane: str = "planned") -> Path:
    feature_dir = tmp_path / "kitty-specs" / slug
    (feature_dir / "tasks").mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")

    prompt = """---
work_package_id: WP01
subtasks: ["T1"]
agent: codex
---
# Work Package Prompt: Demo

Body
"""
    (feature_dir / "tasks" / "WP01-demo.md").write_text(prompt, encoding="utf-8")
    _set_wp_lane(feature_dir, "WP01", lane)
    return feature_dir


def test_scan_all_features_detects_feature(tmp_path):
    feature_dir = _create_feature(tmp_path)
    features = scanner.scan_all_features(tmp_path)
    assert features, "Expected at least one feature"
    assert features[0]["id"] == feature_dir.name
    assert features[0]["artifacts"]["spec"]


def test_scan_all_features_tolerates_unreadable_event_log(tmp_path):
    feature_dir = tmp_path / "kitty-specs" / "001-demo-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (tasks_dir / "WP01-demo.md").write_text(
        """---
work_package_id: WP01
---
# Work Package Prompt: Demo
""",
        encoding="utf-8",
    )
    (feature_dir / "status.events.jsonl").write_text(
        json.dumps(
            {
                "event_id": "TESTBAD00000000000000000000",
                "mission_slug": feature_dir.name,
                "wp_id": "WP01",
                "from_lane": "planned",
                "to_lane": "doing",
                "at": "2026-04-05T12:00:00+00:00",
                "actor": "test-agent",
                "force": False,
                "execution_mode": "worktree",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    features = scanner.scan_all_features(tmp_path)

    assert len(features) == 1
    assert features[0]["id"] == feature_dir.name
    assert features[0]["kanban_stats"]["total"] == 0
    assert "Event log unreadable" in features[0]["kanban_stats"]["error"]


def test_scan_all_features_builds_switcher_display_name(tmp_path):
    feature_dir = _create_feature(tmp_path)
    (feature_dir / "meta.json").write_text(
        json.dumps({"friendly_name": "Demo Feature"}),
        encoding="utf-8",
    )

    features = scanner.scan_all_features(tmp_path)

    assert features[0]["name"] == "Demo Feature"
    assert features[0]["display_name"] == "001 - Demo Feature"


def test_scan_all_features_display_name_avoids_duplicate_prefix(tmp_path):
    feature_dir = _create_feature(tmp_path)
    (feature_dir / "meta.json").write_text(
        json.dumps({"friendly_name": "001 - Demo Feature"}),
        encoding="utf-8",
    )

    features = scanner.scan_all_features(tmp_path)

    assert features[0]["display_name"] == "001 - Demo Feature"


def test_scan_feature_kanban_returns_prompt(tmp_path):
    feature_dir = _create_feature(tmp_path)
    lanes = scanner.scan_feature_kanban(tmp_path, feature_dir.name)
    assert "planned" in lanes
    assert lanes["planned"], "planned lane should contain prompt data"
    task = lanes["planned"][0]
    assert task["id"] == "WP01"
    assert "prompt_markdown" in task


def test_resolve_active_feature_requires_explicit_selection(tmp_path):
    """resolve_active_feature returns None — auto-detection was removed.

    Since feature_detection was deleted (WP02), the dashboard no longer
    auto-detects the active feature.  Callers must provide an explicit
    --feature flag.  This test confirms the contract: without heuristics,
    resolve_active_feature always returns None.
    """
    resolved = scanner.resolve_active_feature(tmp_path)
    assert resolved is None, (
        "resolve_active_feature must return None after removal of auto-detection"
    )


def test_project_charter_propagates_to_all_features(tmp_path):
    _create_feature(tmp_path, "001-demo-feature")
    _create_feature(tmp_path, "002-another-feature")
    charter = tmp_path / ".kittify" / "charter" / "charter.md"
    charter.parent.mkdir(parents=True)
    charter.write_text("# Project Charter\n", encoding="utf-8")

    features = scanner.scan_all_features(tmp_path)
    assert len(features) == 2
    assert all(feature["artifacts"]["charter"]["exists"] for feature in features)


def test_feature_local_charter_is_ignored_without_project_charter(tmp_path):
    first = _create_feature(tmp_path, "001-demo-feature")
    _create_feature(tmp_path, "002-another-feature")
    (first / "charter.md").write_text("# Legacy Feature Charter\n", encoding="utf-8")

    features = scanner.scan_all_features(tmp_path)
    assert len(features) == 2
    assert all(not feature["artifacts"]["charter"]["exists"] for feature in features)


def test_legacy_memory_path_not_resolved(tmp_path):
    """Legacy .kittify/memory/ path is NOT resolved — user must run spec-kitty upgrade."""
    _create_feature(tmp_path, "001-demo-feature")
    _create_feature(tmp_path, "002-another-feature")
    legacy = tmp_path / ".kittify" / "memory" / "charter.md"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("# Legacy Project Charter\n", encoding="utf-8")

    features = scanner.scan_all_features(tmp_path)
    assert len(features) == 2
    assert all(not feature["artifacts"]["charter"]["exists"] for feature in features)


def test_only_canonical_path_resolved(tmp_path):
    """Only .kittify/charter/charter.md is resolved."""
    _create_feature(tmp_path)
    new_path = tmp_path / ".kittify" / "charter" / "charter.md"
    new_path.parent.mkdir(parents=True)
    new_path.write_text("canonical", encoding="utf-8")

    resolved = resolve_project_charter_path(tmp_path)
    assert resolved == new_path


def test_scan_feature_kanban_approved_lane(tmp_path):
    """WPs with canonical lane approved should land in the approved column."""
    _create_feature(tmp_path, "001-demo", lane="approved")
    lanes = scanner.scan_feature_kanban(tmp_path, "001-demo")
    assert len(lanes["approved"]) == 1
    assert len(lanes["planned"]) == 0
    assert lanes["approved"][0]["id"] == "WP01"


def test_scan_feature_kanban_lane_mapping(tmp_path):
    """claimed maps to planned, in_progress maps to doing."""
    feature_dir = tmp_path / "kitty-specs" / "001-demo"
    (feature_dir / "tasks").mkdir(parents=True)
    for wp_id, lane in [("WP01", "claimed"), ("WP02", "in_progress")]:
        (feature_dir / "tasks" / f"{wp_id}.md").write_text(
            f"---\nwork_package_id: {wp_id}\n---\n# Work Package Prompt: {wp_id}\n",
            encoding="utf-8",
        )
        _set_wp_lane(feature_dir, wp_id, lane)
    lanes = scanner.scan_feature_kanban(tmp_path, "001-demo")
    assert len(lanes["planned"]) == 1  # claimed -> planned
    assert len(lanes["doing"]) == 1  # in_progress -> doing


@pytest.mark.fast
def test_scan_feature_kanban_structured_agent_metadata(tmp_path):
    feature_dir = tmp_path / "kitty-specs" / "001-demo"
    (feature_dir / "tasks").mkdir(parents=True)
    (feature_dir / "tasks" / "WP01-agent.md").write_text(
        """---
work_package_id: WP01
agent:
  tool: codex
  model: gpt-5.4
---
# Work Package Prompt: Agent Metadata
""",
        encoding="utf-8",
    )
    _set_wp_lane(feature_dir, "WP01", "planned")

    lanes = scanner.scan_feature_kanban(tmp_path, "001-demo")

    task = lanes["planned"][0]
    assert task["agent"] == "codex"
    assert task["model"] == "gpt-5.4"
