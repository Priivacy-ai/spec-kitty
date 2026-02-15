from pathlib import Path

from specify_cli.dashboard import scanner
from specify_cli.core.feature_detection import FeatureContext


def _create_feature(tmp_path: Path) -> Path:
    feature_dir = tmp_path / "kitty-specs" / "001-demo-feature"
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
