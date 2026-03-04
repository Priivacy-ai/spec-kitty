"""Mutation testing suite for dependency_graph.py.

This test suite is designed to eliminate mutants identified in the mutation testing campaign.
Each test targets specific mutation patterns discovered during analysis.

Iteration 1 Target Patterns:
1. None assignment mutations (graph = {}, errors = [], etc.)
2. Boolean condition negations (if not X → if X)
3. Default parameter mutations (.get(key, []) → .get(key, None))
4. Graph coloring/state mutations (color[node] = BLACK → None)
5. Parameter removal/wrong arguments (missing args, wrong values)
"""

from pathlib import Path


from specify_cli.core.dependency_graph import (
    build_dependency_graph,
    detect_cycles,
    extract_wp_id_from_filename,
    get_dependents,
    parse_wp_dependencies,
    topological_sort,
    validate_dependencies,
)


class TestBuildDependencyGraph:
    """Tests for build_dependency_graph() - targets None assignments, path checks."""

    def test_build_graph_returns_dict_not_none(self, tmp_path: Path) -> None:
        """Verify function returns dict (not None) even with empty directory.

        Targets: Mutation where `graph = {}` → `graph = None`
        Expected: Function returns empty dict, not None
        """
        # Create empty feature directory with tasks/
        feature_dir = tmp_path / "001-test-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        result = build_dependency_graph(feature_dir)

        # Kill mutation: graph = {} → graph = None
        assert result is not None
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_build_graph_with_valid_wps(self, tmp_path: Path) -> None:
        """Verify graph building with multiple valid WP files.

        Targets: Core graph building logic, frontmatter parsing
        Expected: Returns dict mapping WP IDs to their dependencies
        """
        # Setup feature with multiple WPs
        feature_dir = tmp_path / "002-feature"
        tasks_dir = feature_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        # WP01 with no dependencies
        wp01 = tasks_dir / "WP01-setup.md"
        wp01.write_text("---\nwork_package_id: WP01\ndependencies: []\n---\n# Setup")

        # WP02 depends on WP01
        wp02 = tasks_dir / "WP02-core.md"
        wp02.write_text("---\nwork_package_id: WP02\ndependencies: [WP01]\n---\n# Core")

        # WP03 depends on WP01 and WP02
        wp03 = tasks_dir / "WP03-final.md"
        wp03.write_text("---\nwork_package_id: WP03\ndependencies: [WP01, WP02]\n---\n# Final")

        result = build_dependency_graph(feature_dir)

        # Verify correct graph structure
        assert isinstance(result, dict)
        assert len(result) == 3
        assert result["WP01"] == []
        assert result["WP02"] == ["WP01"]
        assert set(result["WP03"]) == {"WP01", "WP02"}

    def test_build_graph_missing_tasks_dir_returns_empty(self, tmp_path: Path) -> None:
        """Verify returns empty dict when tasks/ directory does not exist.

        Targets: Boolean condition `if not tasks_dir.exists():` → `if tasks_dir.exists():`
        Expected: Empty dict returned when directory missing
        """
        # Create feature directory WITHOUT tasks/ subdirectory
        feature_dir = tmp_path / "003-missing-tasks"
        feature_dir.mkdir()

        result = build_dependency_graph(feature_dir)

        # Kill mutation: if not exists() → if exists()
        assert isinstance(result, dict)
        assert len(result) == 0


class TestParseDependencies:
    """Tests for parse_wp_dependencies() - targets default parameters, None handling."""

    def test_parse_dependencies_no_field_returns_empty_list(self, tmp_path: Path) -> None:
        """Verify returns empty list (not None) when dependencies field missing.

        Targets: Mutation `.get("dependencies", [])` → `.get("dependencies", None)`
        Expected: Empty list returned, not None
        """
        # Create WP file WITHOUT dependencies field
        wp_file = tmp_path / "WP01-test.md"
        wp_file.write_text("---\nwork_package_id: WP01\ntitle: Test\n---\n# Content")

        result = parse_wp_dependencies(wp_file)

        # Kill mutation: .get("dependencies", []) → .get("dependencies", None)
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 0

    def test_parse_dependencies_with_deps(self, tmp_path: Path) -> None:
        """Verify correctly parses dependencies from frontmatter.

        Targets: Core parsing logic
        Expected: Returns list of dependency WP IDs
        """
        # Create WP file WITH dependencies
        wp_file = tmp_path / "WP02-test.md"
        wp_file.write_text("---\nwork_package_id: WP02\ndependencies: [WP01]\n---\n# Content")

        result = parse_wp_dependencies(wp_file)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == "WP01"


class TestExtractWpId:
    """Tests for extract_wp_id_from_filename() - targets regex matching, None handling."""

    def test_extract_wp_id_valid_filename(self) -> None:
        """Verify extracts WP ID from valid filename.

        Targets: Regex matching logic, parameter removal mutations
        Expected: Returns 'WP01' from 'WP01-title.md'
        """
        # Test various valid formats
        assert extract_wp_id_from_filename("WP01-setup.md") == "WP01"
        assert extract_wp_id_from_filename("WP02.md") == "WP02"
        assert extract_wp_id_from_filename("WP99-final-task.md") == "WP99"

        # Kill parameter removal mutations (re.match needs filename arg)
        result = extract_wp_id_from_filename("WP03-test.md")
        assert result is not None
        assert result == "WP03"

    def test_extract_wp_id_invalid_filename_returns_none(self) -> None:
        """Verify returns None for invalid filename format.

        Targets: None return path
        Expected: None returned for non-WP filenames
        """
        # Kill mutation: match = re.match(...) → match = None
        assert extract_wp_id_from_filename("invalid.md") is None
        assert extract_wp_id_from_filename("readme.md") is None
        assert extract_wp_id_from_filename("WP1.md") is None  # Wrong format (single digit)
        assert extract_wp_id_from_filename("") is None


class TestDetectCycles:
    """Tests for detect_cycles() - targets DFS algorithm, coloring mutations."""

    def test_detect_cycles_simple_cycle(self) -> None:
        """Verify detects simple two-node cycle.

        Targets: DFS coloring logic, GRAY state detection
        Expected: Cycle detected in WP01→WP02→WP01
        """
        # Create simple cycle: WP01 → WP02 → WP01
        graph = {"WP01": ["WP02"], "WP02": ["WP01"]}

        cycles = detect_cycles(graph)

        # Kill mutations in cycle detection (color[node] = BLACK → None, etc.)
        assert cycles is not None
        assert isinstance(cycles, list)
        assert len(cycles) > 0

        # Verify cycle contains both nodes
        cycle = cycles[0]
        assert "WP01" in cycle
        assert "WP02" in cycle

    def test_detect_cycles_acyclic_returns_none(self) -> None:
        """Verify returns None for acyclic graph.

        Targets: Absence of cycles, color state transitions
        Expected: None returned (no cycles)
        """
        # Create acyclic graph: WP01 → WP02 → WP03
        graph = {"WP01": [], "WP02": ["WP01"], "WP03": ["WP02"]}

        cycles = detect_cycles(graph)

        # Kill mutation: default parameter .get(neighbor, WHITE) → .get(neighbor, None)
        assert cycles is None

    def test_detect_cycles_multi_node_cycle(self) -> None:
        """Verify detects cycles with more than 2 nodes.

        Targets: Complex cycle detection
        Expected: Cycle detected in WP01→WP02→WP03→WP01
        """
        # Create 3-node cycle
        graph = {"WP01": ["WP02"], "WP02": ["WP03"], "WP03": ["WP01"]}

        cycles = detect_cycles(graph)

        # Kill mutations: WHITE, GRAY, BLACK = 0, 1, 2 → None
        assert cycles is not None
        assert isinstance(cycles, list)
        assert len(cycles) > 0

        # Verify all three nodes in cycle
        cycle = cycles[0]
        assert "WP01" in cycle
        assert "WP02" in cycle
        assert "WP03" in cycle


class TestValidateDependencies:
    """Tests for validate_dependencies() - targets validation logic, error handling."""

    def test_validate_self_dependency_fails(self) -> None:
        """Verify validation fails when WP depends on itself.

        Targets: Boolean condition `if dep == wp_id:` → `if dep != wp_id:`
        Expected: Validation fails with self-dependency error
        """
        graph = {"WP01": [], "WP02": []}

        # Try to make WP01 depend on itself
        is_valid, errors = validate_dependencies("WP01", ["WP01"], graph)

        # Kill mutation: if dep == wp_id → if dep != wp_id
        assert is_valid is False
        assert len(errors) > 0
        assert any("self" in err.lower() for err in errors)

    def test_validate_nonexistent_dependency_fails(self) -> None:
        """Verify validation fails when dependency not in graph.

        Targets: Dependency existence check
        Expected: Validation fails with 'not found' error
        """
        graph = {"WP01": [], "WP02": []}

        # Try to depend on non-existent WP99
        is_valid, errors = validate_dependencies("WP02", ["WP99"], graph)

        # Kill mutation: errors = [] → errors = None
        assert is_valid is False
        assert errors is not None
        assert isinstance(errors, list)
        assert len(errors) > 0
        assert any("not found" in err.lower() for err in errors)

    def test_validate_valid_dependencies_passes(self) -> None:
        """Verify validation passes for valid dependencies.

        Targets: Happy path validation
        Expected: Returns (True, []) for valid dependencies
        """
        graph = {"WP01": [], "WP02": ["WP01"], "WP03": ["WP01", "WP02"]}

        # Validate WP03's dependencies
        is_valid, errors = validate_dependencies("WP03", ["WP01", "WP02"], graph)

        assert is_valid is True
        assert isinstance(errors, list)
        assert len(errors) == 0


class TestTopologicalSort:
    """Tests for topological_sort() - targets Kahn's algorithm, ordering logic."""

    def test_topological_sort_basic_ordering(self) -> None:
        """Verify correct dependency ordering.

        Targets: Core sorting logic, in-degree calculations
        Expected: WP01 before WP02 when WP02 depends on WP01
        """
        graph = {"WP01": [], "WP02": ["WP01"]}

        result = topological_sort(graph)

        # Kill mutation: in_degree = {...} → in_degree = None
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 2

        # WP01 must come before WP02
        wp01_idx = result.index("WP01")
        wp02_idx = result.index("WP02")
        assert wp01_idx < wp02_idx

    def test_topological_sort_complex_graph(self) -> None:
        """Verify correct ordering with multiple dependencies.

        Targets: Complex dependency resolution
        Expected: Dependencies always before dependents
        """
        # Diamond dependency: WP01 <- WP02, WP03 <- WP04
        #     WP01
        #    /    \
        #  WP02  WP03
        #    \    /
        #     WP04
        graph = {"WP01": [], "WP02": ["WP01"], "WP03": ["WP01"], "WP04": ["WP02", "WP03"]}

        result = topological_sort(graph)

        # Kill mutation: sorted(None) → parameter removal
        assert isinstance(result, list)
        assert len(result) == 4

        # Verify ordering constraints
        wp01_idx = result.index("WP01")
        wp02_idx = result.index("WP02")
        wp03_idx = result.index("WP03")
        wp04_idx = result.index("WP04")

        # WP01 must be first
        assert wp01_idx < wp02_idx
        assert wp01_idx < wp03_idx
        assert wp01_idx < wp04_idx

        # WP02 and WP03 must come before WP04
        assert wp02_idx < wp04_idx
        assert wp03_idx < wp04_idx


class TestGetDependents:
    """Tests for get_dependents() - targets inverse graph construction."""

    def test_get_dependents_basic(self) -> None:
        """Verify finds direct dependents.

        Targets: Inverse graph construction logic
        Expected: Returns WPs that depend on given WP
        """
        # Graph where WP02 and WP03 depend on WP01
        graph = {"WP01": [], "WP02": ["WP01"], "WP03": ["WP01"]}

        result = get_dependents("WP01", graph)

        # Kill mutation: inverse_graph = {...} → inverse_graph = None
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 2
        assert "WP02" in result
        assert "WP03" in result

    def test_get_dependents_no_dependents_returns_empty(self) -> None:
        """Verify returns empty list when no dependents.

        Targets: Empty result path
        Expected: Empty list for WP with no dependents
        """
        # Graph where WP03 has no dependents
        graph = {"WP01": [], "WP02": ["WP01"], "WP03": ["WP01", "WP02"]}

        result = get_dependents("WP03", graph)

        # Kill mutation: inverse_graph.get(None, []) → wrong argument
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 0
