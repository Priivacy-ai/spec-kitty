import json
from pathlib import Path

from specify_cli.dashboard import scanner
from specify_cli.dashboard.constitution_path import resolve_project_constitution_path
from specify_cli.core.feature_detection import FeatureContext


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


def test_resolve_active_feature_uses_core_detector(tmp_path, monkeypatch):
    features = [
        {"id": "009-old-feature"},
        {"id": "010-new-feature"},
    ]

    def _fake_detect_feature(*_args, **_kwargs):
        return FeatureContext(
            slug="010-new-feature",
            number="010",
            name="new-feature",
            directory=tmp_path / "kitty-specs" / "010-new-feature",
            detection_method="fallback_latest_incomplete",
        )

    monkeypatch.setattr(scanner, "detect_feature", _fake_detect_feature)

    resolved = scanner.resolve_active_feature(tmp_path, features)
    assert resolved is not None
    assert resolved["id"] == "010-new-feature"


def test_resolve_active_feature_falls_back_to_first(tmp_path, monkeypatch):
    features = [
        {"id": "009-old-feature"},
        {"id": "010-new-feature"},
    ]

    monkeypatch.setattr(scanner, "detect_feature", lambda *_args, **_kwargs: None)
    resolved = scanner.resolve_active_feature(tmp_path, features)
    assert resolved is not None
    assert resolved["id"] == "009-old-feature"


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


def test_scan_feature_kanban_approved_lane(tmp_path):
    """WPs with lane: approved should land in the approved column, not planned."""
    feature_dir = tmp_path / "kitty-specs" / "001-demo"
    (feature_dir / "tasks").mkdir(parents=True)
    (feature_dir / "tasks" / "WP01.md").write_text(
        "---\nwork_package_id: WP01\nlane: approved\n---\n# Work Package Prompt: WP01\n",
        encoding="utf-8",
    )
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
            f"---\nwork_package_id: {wp_id}\nlane: {lane}\n---\n# Work Package Prompt: {wp_id}\n",
            encoding="utf-8",
        )
    lanes = scanner.scan_feature_kanban(tmp_path, "001-demo")
    assert len(lanes["planned"]) == 1  # claimed -> planned
    assert len(lanes["doing"]) == 1  # in_progress -> doing
