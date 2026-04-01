import json
from pathlib import Path

from specify_cli.dashboard import scanner
from specify_cli.dashboard.constitution_path import resolve_project_constitution_path


def _create_feature(tmp_path: Path, slug: str = "001-demo-feature") -> Path:
    feature_dir = tmp_path / "kitty-specs" / slug
    (feature_dir / "tasks" / "planned").mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")

    prompt = """---
work_package_id: WP01
lane: planned
subtasks: ["T1"]
agent: codex
---
# Work Package Prompt: Demo

Body
"""
    (feature_dir / "tasks" / "planned" / "WP01-demo.md").write_text(prompt, encoding="utf-8")
    return feature_dir


def test_scan_all_features_detects_feature(tmp_path):
    feature_dir = _create_feature(tmp_path)
    features = scanner.scan_all_features(tmp_path)
    assert features, "Expected at least one feature"
    assert features[0]["id"] == feature_dir.name
    assert features[0]["artifacts"]["spec"]


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
    features = [
        {"id": "009-old-feature"},
        {"id": "010-new-feature"},
    ]

    resolved = scanner.resolve_active_feature(tmp_path, features)
    assert resolved is None, (
        "resolve_active_feature must return None after removal of auto-detection"
    )


def test_project_constitution_propagates_to_all_features(tmp_path):
    _create_feature(tmp_path, "001-demo-feature")
    _create_feature(tmp_path, "002-another-feature")
    constitution = tmp_path / ".kittify" / "constitution" / "constitution.md"
    constitution.parent.mkdir(parents=True)
    constitution.write_text("# Project Constitution\n", encoding="utf-8")

    features = scanner.scan_all_features(tmp_path)
    assert len(features) == 2
    assert all(feature["artifacts"]["constitution"]["exists"] for feature in features)


def test_feature_local_constitution_is_ignored_without_project_constitution(tmp_path):
    first = _create_feature(tmp_path, "001-demo-feature")
    _create_feature(tmp_path, "002-another-feature")
    (first / "constitution.md").write_text("# Legacy Feature Constitution\n", encoding="utf-8")

    features = scanner.scan_all_features(tmp_path)
    assert len(features) == 2
    assert all(not feature["artifacts"]["constitution"]["exists"] for feature in features)


def test_legacy_constitution_path_supported(tmp_path):
    _create_feature(tmp_path, "001-demo-feature")
    _create_feature(tmp_path, "002-another-feature")
    legacy = tmp_path / ".kittify" / "memory" / "constitution.md"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("# Legacy Project Constitution\n", encoding="utf-8")

    features = scanner.scan_all_features(tmp_path)
    assert len(features) == 2
    assert all(feature["artifacts"]["constitution"]["exists"] for feature in features)


def test_new_path_preferred_when_both_exist(tmp_path):
    _create_feature(tmp_path)
    new_path = tmp_path / ".kittify" / "constitution" / "constitution.md"
    legacy_path = tmp_path / ".kittify" / "memory" / "constitution.md"
    new_path.parent.mkdir(parents=True)
    legacy_path.parent.mkdir(parents=True)
    new_path.write_text("new", encoding="utf-8")
    legacy_path.write_text("legacy", encoding="utf-8")

    resolved = resolve_project_constitution_path(tmp_path)
    assert resolved == new_path


def _write_status_event(feature_dir, wp_id, to_lane, from_lane="planned"):
    """Write a status event to the feature's event log."""
    import json
    from datetime import datetime, UTC

    event = {
        "event_id": f"01TEST{wp_id}{to_lane.upper()[:4]}",
        "feature_slug": feature_dir.name,
        "wp_id": wp_id,
        "from_lane": from_lane,
        "to_lane": to_lane,
        "actor": "test",
        "at": datetime.now(UTC).isoformat(),
        "force": False,
        "reason": None,
        "evidence": None,
        "review_ref": None,
        "execution_mode": "worktree",
    }
    events_path = feature_dir / "status.events.jsonl"
    with events_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")


def test_scan_feature_kanban_approved_lane(tmp_path):
    """WPs with approved status in event log should land in the approved column."""
    feature_dir = tmp_path / "kitty-specs" / "001-demo"
    (feature_dir / "tasks").mkdir(parents=True)
    (feature_dir / "tasks" / "WP01.md").write_text(
        "---\nwork_package_id: WP01\n---\n# Work Package Prompt: WP01\n",
        encoding="utf-8",
    )
    _write_status_event(feature_dir, "WP01", "planned", from_lane="planned")
    _write_status_event(feature_dir, "WP01", "approved", from_lane="for_review")
    lanes = scanner.scan_feature_kanban(tmp_path, "001-demo")
    assert len(lanes["approved"]) == 1
    assert len(lanes["planned"]) == 0
    assert lanes["approved"][0]["id"] == "WP01"


def test_scan_feature_kanban_lane_mapping(tmp_path):
    """claimed maps to planned, in_progress maps to doing."""
    feature_dir = tmp_path / "kitty-specs" / "001-demo"
    (feature_dir / "tasks").mkdir(parents=True)
    for wp_id in ["WP01", "WP02"]:
        (feature_dir / "tasks" / f"{wp_id}.md").write_text(
            f"---\nwork_package_id: {wp_id}\n---\n# Work Package Prompt: {wp_id}\n",
            encoding="utf-8",
        )
    _write_status_event(feature_dir, "WP01", "claimed", from_lane="planned")
    _write_status_event(feature_dir, "WP02", "in_progress", from_lane="claimed")
    lanes = scanner.scan_feature_kanban(tmp_path, "001-demo")
    assert len(lanes["planned"]) == 1  # claimed -> planned
    assert len(lanes["doing"]) == 1  # in_progress -> doing
