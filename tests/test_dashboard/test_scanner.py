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




def test_constitution_artifact_checks_project_level_path(tmp_path):
    """Bug: Scanner incorrectly checks per-feature constitution.md instead of project-level .kittify/constitution/constitution.md
    
    Expected: Constitution artifact should check project-level paths:
      - .kittify/constitution/constitution.md (new path, post-migration)
      - .kittify/memory/constitution.md (old path, pre-migration)
    
    Actual: Scanner checks kitty-specs/{feature}/constitution.md (per-feature path)
    
    Context: Feature 011 removed per-mission constitutions. Only ONE project-level
    constitution exists. Dashboard shows "Constitution not created" even when
    constitution exists at .kittify/memory/constitution.md.
    """
    # Setup: Create feature with constitution at PROJECT level (correct location)
    feature_dir = tmp_path / "kitty-specs" / "001-demo-feature"
    feature_dir.mkdir(parents=True)
    
    # Create project-level constitution at new path
    constitution_dir = tmp_path / ".kittify" / "constitution"
    constitution_dir.mkdir(parents=True)
    constitution_path = constitution_dir / "constitution.md"
    constitution_path.write_text("# Project Constitution\n", encoding="utf-8")
    
    # Act: Get feature artifacts
    artifacts = scanner.get_feature_artifacts(feature_dir)
    
    # Assert: Constitution should be detected (project-level, not per-feature)
    # BUG: This assertion will FAIL because scanner checks feature_dir/constitution.md
    assert artifacts["constitution"]["exists"], (
        "Constitution artifact should be detected at project level "
        "(.kittify/constitution/constitution.md), not per-feature "
        "(kitty-specs/001-demo-feature/constitution.md)"
    )


def test_constitution_artifact_checks_legacy_path_fallback(tmp_path):
    """Constitution should also detect old pre-migration path for backward compatibility."""
    # Setup: Create feature with constitution at OLD path (.kittify/memory/)
    feature_dir = tmp_path / "kitty-specs" / "001-demo-feature"
    feature_dir.mkdir(parents=True)
    
    # Create project-level constitution at old path (unmigrated project)
    memory_dir = tmp_path / ".kittify" / "memory"
    memory_dir.mkdir(parents=True)
    old_constitution = memory_dir / "constitution.md"
    old_constitution.write_text("# Project Constitution (old path)\n", encoding="utf-8")
    
    # Act: Get feature artifacts
    artifacts = scanner.get_feature_artifacts(feature_dir)
    
    # Assert: Constitution should be detected at old path
    # BUG: This will also FAIL because scanner doesn't check old path
    assert artifacts["constitution"]["exists"], (
        "Constitution artifact should be detected at legacy path "
        "(.kittify/memory/constitution.md) for unmigrated projects"
    )
