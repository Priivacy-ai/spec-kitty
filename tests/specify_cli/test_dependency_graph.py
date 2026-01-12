"""Tests for dependency graph utilities (WP01)."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.core.dependency_graph import (
    build_dependency_graph,
    detect_cycles,
    get_dependents,
    parse_wp_dependencies,
    validate_dependencies,
)


# T001: Tests for dependency parsing
class TestParseWpDependencies:
    """Test parse_wp_dependencies() function."""

    def test_parse_no_dependencies(self, tmp_path: Path):
        """Test parsing WP with no dependencies (empty list)."""
        wp_content = """---
work_package_id: "WP01"
dependencies: []
---
# Content
"""
        wp_file = tmp_path / "WP01.md"
        wp_file.write_text(wp_content)

        deps = parse_wp_dependencies(wp_file)
        assert deps == []

    def test_parse_single_dependency(self, tmp_path: Path):
        """Test parsing WP with single dependency."""
        wp_content = """---
work_package_id: "WP02"
dependencies: ["WP01"]
---
# Content
"""
        wp_file = tmp_path / "WP02.md"
        wp_file.write_text(wp_content)

        deps = parse_wp_dependencies(wp_file)
        assert deps == ["WP01"]

    def test_parse_multiple_dependencies(self, tmp_path: Path):
        """Test parsing WP with multiple dependencies."""
        wp_content = """---
work_package_id: "WP04"
dependencies:
  - "WP01"
  - "WP02"
  - "WP03"
---
# Content
"""
        wp_file = tmp_path / "WP04.md"
        wp_file.write_text(wp_content)

        deps = parse_wp_dependencies(wp_file)
        assert deps == ["WP01", "WP02", "WP03"]

    def test_parse_missing_dependencies_field(self, tmp_path: Path):
        """Test parsing WP without dependencies field (defaults to [])."""
        wp_content = """---
work_package_id: "WP01"
title: "Legacy WP"
lane: "planned"
---
# Content
"""
        wp_file = tmp_path / "WP01.md"
        wp_file.write_text(wp_content)

        deps = parse_wp_dependencies(wp_file)
        assert deps == []  # Defaults to empty list

    def test_parse_invalid_frontmatter(self, tmp_path: Path):
        """Test parsing file with invalid/missing frontmatter."""
        # No frontmatter
        wp_file = tmp_path / "WP01.md"
        wp_file.write_text("# Just content, no frontmatter")

        deps = parse_wp_dependencies(wp_file)
        assert deps == []  # Returns empty on error

        # Malformed frontmatter
        wp_file.write_text("---\ninvalid yaml: [unclosed\n---\n")
        deps = parse_wp_dependencies(wp_file)
        assert deps == []  # Returns empty on parse error


# T002: Tests for graph building
class TestBuildDependencyGraph:
    """Test build_dependency_graph() function."""

    def test_build_graph_empty_feature(self, tmp_path: Path):
        """Test graph building with no WPs."""
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        graph = build_dependency_graph(feature_dir)
        assert graph == {}

    def test_build_graph_single_wp(self, tmp_path: Path):
        """Test graph building with single WP."""
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        (tasks_dir / "WP01.md").write_text("---\nwork_package_id: WP01\ndependencies: []\n---")

        graph = build_dependency_graph(feature_dir)
        assert graph == {"WP01": []}

    def test_build_graph_raises_on_mismatched_wp_id(self, tmp_path: Path):
        """Mismatched filename WP ID vs frontmatter should raise."""
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        (tasks_dir / "WP02-mismatch.md").write_text(
            "---\nwork_package_id: WP03\ndependencies: []\n---"
        )

        with pytest.raises(ValueError, match="WP ID mismatch"):
            build_dependency_graph(feature_dir)

    def test_build_graph_linear_chain(self, tmp_path: Path):
        """Test graph building with linear dependency chain."""
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        (tasks_dir / "WP01.md").write_text("---\nwork_package_id: WP01\ndependencies: []\n---")
        (tasks_dir / "WP02.md").write_text("---\nwork_package_id: WP02\ndependencies: [WP01]\n---")
        (tasks_dir / "WP03.md").write_text("---\nwork_package_id: WP03\ndependencies: [WP02]\n---")

        graph = build_dependency_graph(feature_dir)
        assert graph == {"WP01": [], "WP02": ["WP01"], "WP03": ["WP02"]}

    def test_build_graph_fan_out(self, tmp_path: Path):
        """Test graph building with fan-out pattern (multiple WPs depend on one)."""
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        (tasks_dir / "WP01.md").write_text("---\nwork_package_id: WP01\ndependencies: []\n---")
        (tasks_dir / "WP02.md").write_text("---\nwork_package_id: WP02\ndependencies: [WP01]\n---")
        (tasks_dir / "WP03.md").write_text("---\nwork_package_id: WP03\ndependencies: [WP01]\n---")
        (tasks_dir / "WP04.md").write_text("---\nwork_package_id: WP04\ndependencies: [WP01]\n---")

        graph = build_dependency_graph(feature_dir)
        assert graph == {
            "WP01": [],
            "WP02": ["WP01"],
            "WP03": ["WP01"],
            "WP04": ["WP01"]
        }

    def test_build_graph_complex_dag(self, tmp_path: Path):
        """Test graph building with complex DAG (diamond pattern)."""
        feature_dir = tmp_path / "kitty-specs" / "010-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        (tasks_dir / "WP01.md").write_text("---\nwork_package_id: WP01\ndependencies: []\n---")
        (tasks_dir / "WP02.md").write_text("---\nwork_package_id: WP02\ndependencies: [WP01]\n---")
        (tasks_dir / "WP03.md").write_text("---\nwork_package_id: WP03\ndependencies: [WP01]\n---")
        (tasks_dir / "WP04.md").write_text("---\nwork_package_id: WP04\ndependencies: [WP02, WP03]\n---")

        graph = build_dependency_graph(feature_dir)
        assert graph == {
            "WP01": [],
            "WP02": ["WP01"],
            "WP03": ["WP01"],
            "WP04": ["WP02", "WP03"]
        }


# T003: Tests for cycle detection
class TestDetectCycles:
    """Test detect_cycles() function."""

    def test_detect_cycles_none(self):
        """Test acyclic graph returns None."""
        graph = {"WP01": [], "WP02": ["WP01"], "WP03": ["WP01"]}
        cycles = detect_cycles(graph)
        assert cycles is None

    def test_detect_cycles_simple(self):
        """Test detection of simple circular dependency."""
        graph = {"WP01": ["WP02"], "WP02": ["WP01"]}
        cycles = detect_cycles(graph)

        assert cycles is not None
        assert len(cycles) == 1
        # Cycle should contain both WP01 and WP02
        assert "WP01" in cycles[0] and "WP02" in cycles[0]

    def test_detect_cycles_self_dependency(self):
        """Test detection of self-dependency (WP01 → WP01)."""
        graph = {"WP01": ["WP01"]}
        cycles = detect_cycles(graph)

        assert cycles is not None
        assert len(cycles) == 1
        assert "WP01" in cycles[0]

    def test_detect_cycles_complex(self):
        """Test detection of complex cycle (WP01 → WP02 → WP03 → WP01)."""
        graph = {
            "WP01": ["WP02"],
            "WP02": ["WP03"],
            "WP03": ["WP01"]
        }
        cycles = detect_cycles(graph)

        assert cycles is not None
        assert len(cycles) == 1
        # Cycle should include all three WPs
        cycle = cycles[0]
        assert "WP01" in cycle and "WP02" in cycle and "WP03" in cycle

    def test_detect_cycles_complex_dag_no_cycles(self):
        """Test complex DAG (diamond) has no cycles."""
        graph = {
            "WP01": [],
            "WP02": ["WP01"],
            "WP03": ["WP01"],
            "WP04": ["WP02", "WP03"]
        }
        cycles = detect_cycles(graph)
        assert cycles is None


# T004: Tests for dependency validation
class TestValidateDependencies:
    """Test validate_dependencies() function."""

    def test_validate_dependencies_valid(self):
        """Test validation passes for valid dependencies."""
        graph = {"WP01": [], "WP02": ["WP01"], "WP03": ["WP01"]}
        is_valid, errors = validate_dependencies("WP02", ["WP01"], graph)

        assert is_valid is True
        assert errors == []

    def test_validate_dependencies_missing(self):
        """Test validation catches missing dependencies."""
        graph = {"WP01": [], "WP02": ["WP01"]}
        is_valid, errors = validate_dependencies("WP03", ["WP99"], graph)

        assert is_valid is False
        assert len(errors) > 0
        assert any("WP99" in err for err in errors)

    def test_validate_dependencies_self_dependency(self):
        """Test validation catches self-dependency."""
        graph = {"WP01": ["WP01"]}
        is_valid, errors = validate_dependencies("WP01", ["WP01"], graph)

        assert is_valid is False
        assert any("self" in err.lower() for err in errors)

    def test_validate_dependencies_circular(self):
        """Test validation catches circular dependencies."""
        graph = {"WP01": ["WP02"], "WP02": ["WP01"]}
        is_valid, errors = validate_dependencies("WP01", ["WP02"], graph)

        assert is_valid is False
        assert any("circular" in err.lower() or "cycle" in err.lower() for err in errors)

    def test_validate_dependencies_invalid_format(self):
        """Test validation catches invalid WP ID format."""
        graph = {"WP01": []}
        is_valid, errors = validate_dependencies("WP02", ["WP1"], graph)  # Invalid: WP1 not WP01

        assert is_valid is False
        assert any("format" in err.lower() or "invalid" in err.lower() for err in errors)


# T005: Tests for dependent lookup
class TestGetDependents:
    """Test get_dependents() function."""

    def test_get_dependents_none(self):
        """Test WP with no dependents returns empty list."""
        graph = {"WP01": [], "WP02": []}
        dependents = get_dependents("WP01", graph)
        assert dependents == []

    def test_get_dependents_single(self):
        """Test WP with single dependent."""
        graph = {"WP01": [], "WP02": ["WP01"]}
        dependents = get_dependents("WP01", graph)
        assert dependents == ["WP02"]

    def test_get_dependents_fan_out(self):
        """Test finding dependents in fan-out pattern."""
        graph = {
            "WP01": [],
            "WP02": ["WP01"],
            "WP03": ["WP01"],
            "WP04": ["WP01"]
        }
        dependents = get_dependents("WP01", graph)
        assert set(dependents) == {"WP02", "WP03", "WP04"}

    def test_get_dependents_nonexistent_wp(self):
        """Test querying non-existent WP returns empty list."""
        graph = {"WP01": [], "WP02": ["WP01"]}
        dependents = get_dependents("WP99", graph)
        assert dependents == []

    def test_get_dependents_transitive(self):
        """Test get_dependents only returns direct dependents (not transitive)."""
        graph = {
            "WP01": [],
            "WP02": ["WP01"],
            "WP03": ["WP02"]  # WP03 depends on WP02, not directly on WP01
        }
        dependents = get_dependents("WP01", graph)
        assert dependents == ["WP02"]  # Only direct dependent
        assert "WP03" not in dependents  # Transitive, not direct
