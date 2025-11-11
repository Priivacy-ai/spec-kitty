from pathlib import Path

from specify_cli.dashboard import scanner


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
