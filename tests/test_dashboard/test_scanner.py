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


# --- Regression tests for canonical lane name mismatch (issue: in_progress vs doing) ---


def _create_flat_feature(tmp_path: Path, slug: str = "047-test-feature") -> Path:
    """Create a flat-format feature (new layout: WPs in tasks/, lane in frontmatter)."""
    feature_dir = tmp_path / "kitty-specs" / slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
    return feature_dir


def _wp_file(tasks_dir: Path, wp_id: str, lane: str) -> None:
    """Write a minimal WP prompt file with the given lane in frontmatter."""
    content = f"""---
work_package_id: {wp_id}
lane: {lane}
subtasks:
- T001
---
# Work Package Prompt: {wp_id}

Body text.
"""
    (tasks_dir / f"{wp_id}-test.md").write_text(content, encoding="utf-8")


def test_scan_feature_kanban_canonical_in_progress_appears_in_doing_lane(tmp_path):
    """Regression: WPs with lane=in_progress (canonical) must appear in 'doing' kanban column.

    The status model writes canonical 'in_progress' to WP frontmatter when the user
    runs `move-task --to doing`. The scanner's 'doing' lane key must include these WPs;
    previously they silently fell back to 'planned'.
    """
    feature_dir = _create_flat_feature(tmp_path)
    _wp_file(feature_dir / "tasks", "WP01", "in_progress")

    lanes = scanner.scan_feature_kanban(tmp_path, feature_dir.name)

    assert lanes["doing"], (
        "WP with lane='in_progress' should appear in 'doing' kanban column, "
        f"but got: planned={[t['id'] for t in lanes['planned']]}, "
        f"doing={[t['id'] for t in lanes['doing']]}"
    )
    assert lanes["doing"][0]["id"] == "WP01"
    assert not lanes["planned"], "WP should NOT fall back to 'planned'"


def test_scan_feature_kanban_doing_alias_still_works(tmp_path):
    """Regression: WPs with lane=doing (legacy alias) must still appear in 'doing' column."""
    feature_dir = _create_flat_feature(tmp_path)
    _wp_file(feature_dir / "tasks", "WP01", "doing")

    lanes = scanner.scan_feature_kanban(tmp_path, feature_dir.name)

    assert lanes["doing"], "WP with lane='doing' should appear in 'doing' kanban column"
    assert lanes["doing"][0]["id"] == "WP01"


def test_scan_feature_kanban_all_canonical_lanes_mapped(tmp_path):
    """Regression: verify all canonical status lane values land in the correct kanban column.

    Canonical lanes: planned, in_progress, for_review, done.
    Alias: doing -> in_progress.
    """
    feature_dir = _create_flat_feature(tmp_path)
    tasks_dir = feature_dir / "tasks"
    _wp_file(tasks_dir, "WP01", "planned")
    _wp_file(tasks_dir, "WP02", "in_progress")
    _wp_file(tasks_dir, "WP03", "for_review")
    _wp_file(tasks_dir, "WP04", "done")

    lanes = scanner.scan_feature_kanban(tmp_path, feature_dir.name)

    assert [t["id"] for t in lanes["planned"]] == ["WP01"], "planned lane"
    assert [t["id"] for t in lanes["doing"]] == ["WP02"], "doing/in_progress lane"
    assert [t["id"] for t in lanes["for_review"]] == ["WP03"], "for_review lane"
    assert [t["id"] for t in lanes["done"]] == ["WP04"], "done lane"
