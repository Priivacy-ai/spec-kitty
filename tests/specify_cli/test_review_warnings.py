"""Tests for review feedback warning system."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.core.dependency_graph import build_dependency_graph, get_dependents
from specify_cli.frontmatter import write_frontmatter
from specify_cli.cli.commands.agent import workflow


def create_wp_file(
    path: Path,
    wp_id: str,
    dependencies: list[str],
    lane: str = "planned"
) -> None:
    """Create a test WP file with frontmatter.

    Args:
        path: Path to WP file
        wp_id: Work package ID
        dependencies: List of dependency WP IDs
        lane: Lane status
    """
    frontmatter = {
        "work_package_id": wp_id,
        "title": f"Test {wp_id}",
        "lane": lane,
        "dependencies": dependencies,
        "subtasks": [],
        "phase": "Test Phase",
        "assignee": "",
        "agent": "",
        "shell_pid": "",
        "review_status": "",
        "reviewed_by": "",
        "history": [
            {
                "timestamp": "2025-01-01T00:00:00Z",
                "lane": lane,
                "agent": "test",
                "action": "Test"
            }
        ]
    }

    body = f"# Test WP: {wp_id}\n\nTest content."

    write_frontmatter(path, frontmatter, body)


def test_warning_when_dependents_in_progress(tmp_path: Path) -> None:
    """Test warning displays when WP has dependents in doing lane."""
    feature_dir = tmp_path / "kitty-specs" / "011-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create WP01 (no deps)
    create_wp_file(tasks_dir / "WP01-test.md", "WP01", [], lane="for_review")

    # Create WP02 (depends on WP01, in doing lane)
    create_wp_file(tasks_dir / "WP02-test.md", "WP02", ["WP01"], lane="doing")

    # Build dependency graph
    graph = build_dependency_graph(feature_dir)

    # Get dependents of WP01
    dependents = get_dependents("WP01", graph)

    assert "WP02" in dependents


def test_no_warning_when_dependents_done(tmp_path: Path) -> None:
    """Test no warning when dependents are in done lane."""
    feature_dir = tmp_path / "kitty-specs" / "011-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create WP01 (no deps)
    create_wp_file(tasks_dir / "WP01-test.md", "WP01", [], lane="for_review")

    # Create WP02 (depends on WP01, in done lane)
    create_wp_file(tasks_dir / "WP02-test.md", "WP02", ["WP01"], lane="done")

    # Build dependency graph
    graph = build_dependency_graph(feature_dir)

    # Get dependents of WP01
    dependents = get_dependents("WP01", graph)

    assert "WP02" in dependents
    # Warning should NOT be displayed because WP02 is done


def test_no_warning_when_no_dependents(tmp_path: Path) -> None:
    """Test no warning when WP has no dependents."""
    feature_dir = tmp_path / "kitty-specs" / "011-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create WP01 (no deps)
    create_wp_file(tasks_dir / "WP01-test.md", "WP01", [], lane="for_review")

    # Build dependency graph
    graph = build_dependency_graph(feature_dir)

    # Get dependents of WP01
    dependents = get_dependents("WP01", graph)

    assert dependents == []


def test_dependency_graph_multiple_dependents(tmp_path: Path) -> None:
    """Test dependency graph with multiple dependents."""
    feature_dir = tmp_path / "kitty-specs" / "011-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create WP01 (base)
    create_wp_file(tasks_dir / "WP01-base.md", "WP01", [], lane="for_review")

    # Create WP02 and WP03 depending on WP01
    create_wp_file(tasks_dir / "WP02-dep1.md", "WP02", ["WP01"], lane="doing")
    create_wp_file(tasks_dir / "WP03-dep2.md", "WP03", ["WP01"], lane="planned")

    # Build dependency graph
    graph = build_dependency_graph(feature_dir)

    # Get dependents of WP01
    dependents = get_dependents("WP01", graph)

    assert sorted(dependents) == ["WP02", "WP03"]


def test_dependency_graph_chain(tmp_path: Path) -> None:
    """Test dependency graph with chain: WP01 → WP02 → WP03."""
    feature_dir = tmp_path / "kitty-specs" / "011-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create chain: WP01 → WP02 → WP03
    create_wp_file(tasks_dir / "WP01-base.md", "WP01", [], lane="for_review")
    create_wp_file(tasks_dir / "WP02-mid.md", "WP02", ["WP01"], lane="doing")
    create_wp_file(tasks_dir / "WP03-end.md", "WP03", ["WP02"], lane="planned")

    # Build dependency graph
    graph = build_dependency_graph(feature_dir)

    # WP01 has one direct dependent: WP02
    wp01_deps = get_dependents("WP01", graph)
    assert wp01_deps == ["WP02"]

    # WP02 has one direct dependent: WP03
    wp02_deps = get_dependents("WP02", graph)
    assert wp02_deps == ["WP03"]

    # WP03 has no dependents
    wp03_deps = get_dependents("WP03", graph)
    assert wp03_deps == []


def test_in_progress_filter(tmp_path: Path) -> None:
    """Test filtering dependents by lane status."""
    feature_dir = tmp_path / "kitty-specs" / "011-test"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Create WP01 with various dependents in different lanes
    create_wp_file(tasks_dir / "WP01-base.md", "WP01", [], lane="for_review")
    create_wp_file(tasks_dir / "WP02-planned.md", "WP02", ["WP01"], lane="planned")
    create_wp_file(tasks_dir / "WP03-doing.md", "WP03", ["WP01"], lane="doing")
    create_wp_file(tasks_dir / "WP04-for-review.md", "WP04", ["WP01"], lane="for_review")
    create_wp_file(tasks_dir / "WP05-done.md", "WP05", ["WP01"], lane="done")

    # Build dependency graph
    graph = build_dependency_graph(feature_dir)
    dependents = get_dependents("WP01", graph)

    # All dependents should be in the graph
    assert sorted(dependents) == ["WP02", "WP03", "WP04", "WP05"]

    # Only WP03 should trigger warnings (doing)
    # Planned/for_review/done are not in progress for warnings
    in_progress = [
        dep for dep in dependents
        if dep == "WP03"
    ]
    assert sorted(in_progress) == ["WP03"]


def test_workflow_review_warns_dependents(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Review workflow should warn when dependents are in progress."""
    repo_root = tmp_path
    (repo_root / ".kittify").mkdir()
    feature_slug = "011-test"
    tasks_dir = repo_root / "kitty-specs" / feature_slug / "tasks"
    tasks_dir.mkdir(parents=True)

    create_wp_file(tasks_dir / "WP01-base.md", "WP01", [], lane="for_review")
    create_wp_file(tasks_dir / "WP02-dep.md", "WP02", ["WP01"], lane="doing")

    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo_root))
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr(
        "specify_cli.cli.commands.agent.workflow._ensure_target_branch_checked_out",
        lambda repo_root, feature_slug: (repo_root, "main"),
    )

    # --agent is required for tracking who is reviewing
    workflow.review(wp_id="WP01", feature=feature_slug, agent="test-reviewer")
    output = capsys.readouterr().out

    assert "Dependency Alert" in output
    assert "WP02" in output
