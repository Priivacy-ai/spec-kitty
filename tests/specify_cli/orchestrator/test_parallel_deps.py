"""Parallel execution and dependency tests for orchestrator.

These tests verify the orchestrator correctly handles WP dependencies
and parallel execution. Tests use checkpoint fixtures with various
dependency patterns.

Marks:
    - @pytest.mark.slow: Tests may take >30 seconds
    - @pytest.mark.orchestrator_parallel: Parallel execution tests
    - @pytest.mark.core_agent: Requires core tier agent

Note: These tests focus on dependency graph logic and do NOT require
actual agents to be available. They use fixture data directly.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest


# =============================================================================
# Test Fixture Path Helper
# =============================================================================

# Fixture checkpoint directory (relative to tests/fixtures/orchestrator/)
FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "orchestrator"


def get_checkpoint_path(checkpoint_name: str) -> Path:
    """Get path to a checkpoint fixture directory.

    Args:
        checkpoint_name: Name of checkpoint (e.g., 'wp_created')

    Returns:
        Absolute path to checkpoint directory
    """
    return FIXTURES_DIR / f"checkpoint_{checkpoint_name}"


# =============================================================================
# T041: Independent WPs Parallel Test
# =============================================================================


@pytest.mark.orchestrator_parallel
class TestIndependentWPsParallel:
    """Tests for parallel execution of independent WPs."""

    def test_independent_wps_have_no_dependency_conflict(self):
        """Independent WPs should be schedulable concurrently."""
        from specify_cli.core.dependency_graph import (
            build_dependency_graph,
            detect_cycles,
        )

        checkpoint_path = get_checkpoint_path("wp_created")
        if not checkpoint_path.exists():
            pytest.skip("Checkpoint fixture not found: wp_created")

        # Get the tasks directory
        tasks_dir = checkpoint_path / "feature" / "tasks"

        if not tasks_dir.exists():
            pytest.skip("No tasks directory in fixture")

        # Build dependency graph
        graph = build_dependency_graph(tasks_dir)

        if len(graph) < 2:
            pytest.skip("Need at least 2 WPs for parallel test")

        # Find WPs with no dependencies (independent)
        independent_wps = [
            wp_id for wp_id, deps in graph.items()
            if not deps
        ]

        # Verify no cycles
        cycles = detect_cycles(graph)
        assert cycles is None, f"Unexpected cycles in fixture: {cycles}"

        # Independent WPs should exist (WP01 typically has no deps)
        assert len(independent_wps) >= 1, "Expected at least one independent WP"

    def test_dependency_graph_is_dag(self):
        """Dependency graph should be a DAG (no cycles)."""
        from specify_cli.core.dependency_graph import (
            build_dependency_graph,
            detect_cycles,
        )

        checkpoint_path = get_checkpoint_path("wp_created")
        if not checkpoint_path.exists():
            pytest.skip("Checkpoint fixture not found: wp_created")

        tasks_dir = checkpoint_path / "feature" / "tasks"

        if not tasks_dir.exists():
            pytest.skip("No tasks directory")

        graph = build_dependency_graph(tasks_dir)

        # Should be acyclic
        cycles = detect_cycles(graph)
        assert cycles is None, f"Graph should be acyclic, found: {cycles}"


# =============================================================================
# T042: Dependency Blocking Test
# =============================================================================


@pytest.mark.orchestrator_parallel
class TestDependencyBlocking:
    """Tests for dependency blocking behavior."""

    def test_dependent_wp_recorded_in_graph(self):
        """WP dependencies should be correctly recorded in graph."""
        from specify_cli.core.dependency_graph import build_dependency_graph

        checkpoint_path = get_checkpoint_path("wp_created")
        if not checkpoint_path.exists():
            pytest.skip("Checkpoint fixture not found: wp_created")

        tasks_dir = checkpoint_path / "feature" / "tasks"

        if not tasks_dir.exists():
            pytest.skip("No tasks directory")

        graph = build_dependency_graph(tasks_dir)

        # In our fixture, WP02 depends on WP01
        if "WP02" in graph and "WP01" in graph:
            deps = graph.get("WP02", [])
            assert "WP01" in deps, (
                f"WP02 should depend on WP01, got deps: {deps}"
            )

    def test_blocked_wp_cannot_run_before_dependency(self):
        """WP waiting for dependency should not be schedulable."""
        from specify_cli.core.dependency_graph import (
            build_dependency_graph,
            topological_sort,
        )

        checkpoint_path = get_checkpoint_path("wp_created")
        if not checkpoint_path.exists():
            pytest.skip("Checkpoint fixture not found: wp_created")

        tasks_dir = checkpoint_path / "feature" / "tasks"

        if not tasks_dir.exists():
            pytest.skip("No tasks directory")

        graph = build_dependency_graph(tasks_dir)

        # Topological sort should put dependencies first
        order = topological_sort(graph)

        if "WP01" in order and "WP02" in order:
            wp01_idx = order.index("WP01")
            wp02_idx = order.index("WP02")

            # WP01 should come before WP02
            assert wp01_idx < wp02_idx, (
                f"WP01 should be scheduled before WP02 in topological order: {order}"
            )

    def test_dependency_chain_order_preserved(self):
        """Dependency chain A->B should result in A before B in schedule."""
        from specify_cli.core.dependency_graph import (
            build_dependency_graph,
            topological_sort,
        )

        checkpoint_path = get_checkpoint_path("wp_created")
        if not checkpoint_path.exists():
            pytest.skip("Checkpoint fixture not found: wp_created")

        tasks_dir = checkpoint_path / "feature" / "tasks"

        if not tasks_dir.exists():
            pytest.skip("No tasks directory")

        graph = build_dependency_graph(tasks_dir)
        order = topological_sort(graph)

        # For each WP, all its dependencies should appear earlier
        for wp_id in order:
            deps = graph.get(wp_id, [])
            wp_idx = order.index(wp_id)

            for dep in deps:
                if dep in order:
                    dep_idx = order.index(dep)
                    assert dep_idx < wp_idx, (
                        f"Dependency {dep} should appear before {wp_id} "
                        f"in order: {order}"
                    )


# =============================================================================
# T043: Circular Dependency Detection Test
# =============================================================================


@pytest.mark.orchestrator_parallel
class TestCircularDependencyDetection:
    """Tests for circular dependency detection."""

    def _create_circular_dep_fixture(self, base_checkpoint_path: Path) -> Path:
        r"""Create a fixture with circular dependency.

        Creates WP01 -> WP02 -> WP01 cycle.
        """
        temp_dir = Path(tempfile.mkdtemp(prefix="circular_dep_test_"))

        # Copy base fixture
        src_feature = base_checkpoint_path / "feature"
        dst_feature = temp_dir / "feature"
        shutil.copytree(src_feature, dst_feature)

        tasks_dir = dst_feature / "tasks"

        # Modify WP01 to depend on WP02 (creates cycle)
        wp01_path = tasks_dir / "WP01.md"
        if wp01_path.exists():
            content = wp01_path.read_text()
            # Add WP02 as dependency to WP01
            if 'dependencies: []' in content:
                content = content.replace(
                    'dependencies: []',
                    'dependencies: ["WP02"]'
                )
                wp01_path.write_text(content)
            elif 'dependencies:' in content:
                # Try to append WP02
                content = content.replace(
                    'dependencies:',
                    'dependencies: ["WP02"]  #'
                )
                wp01_path.write_text(content)

        return temp_dir

    def test_circular_dependency_detected(self):
        """Circular dependency should be detected by detect_cycles."""
        from specify_cli.core.dependency_graph import (
            build_dependency_graph,
            detect_cycles,
        )

        checkpoint_path = get_checkpoint_path("wp_created")
        if not checkpoint_path.exists():
            pytest.skip("Checkpoint fixture not found: wp_created")

        temp_dir = self._create_circular_dep_fixture(checkpoint_path)

        try:
            tasks_dir = temp_dir / "feature" / "tasks"
            graph = build_dependency_graph(tasks_dir)

            # Should detect the cycle
            cycles = detect_cycles(graph)
            assert cycles is not None, "Expected cycle to be detected"
            assert len(cycles) > 0, "Expected at least one cycle"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_circular_dependency_identifies_wps(self):
        """Cycle detection should identify the involved WPs."""
        from specify_cli.core.dependency_graph import (
            build_dependency_graph,
            detect_cycles,
        )

        checkpoint_path = get_checkpoint_path("wp_created")
        if not checkpoint_path.exists():
            pytest.skip("Checkpoint fixture not found: wp_created")

        temp_dir = self._create_circular_dep_fixture(checkpoint_path)

        try:
            tasks_dir = temp_dir / "feature" / "tasks"
            graph = build_dependency_graph(tasks_dir)

            cycles = detect_cycles(graph)

            if cycles:
                # At least one cycle should involve WP01 or WP02
                all_wps_in_cycles = set()
                for cycle in cycles:
                    all_wps_in_cycles.update(cycle)

                # The cycle we created involves WP01 and WP02
                assert "WP01" in all_wps_in_cycles or "WP02" in all_wps_in_cycles, (
                    f"Expected WP01 or WP02 in cycle, got: {all_wps_in_cycles}"
                )

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_acyclic_graph_passes_validation(self):
        """Acyclic graph should pass cycle detection."""
        from specify_cli.core.dependency_graph import (
            build_dependency_graph,
            detect_cycles,
        )

        checkpoint_path = get_checkpoint_path("wp_created")
        if not checkpoint_path.exists():
            pytest.skip("Checkpoint fixture not found: wp_created")

        tasks_dir = checkpoint_path / "feature" / "tasks"

        if not tasks_dir.exists():
            pytest.skip("No tasks directory")

        graph = build_dependency_graph(tasks_dir)
        cycles = detect_cycles(graph)

        # Original fixture should be acyclic
        assert cycles is None, f"Expected no cycles in base fixture, got: {cycles}"


# =============================================================================
# T044: Diamond Dependency Pattern Test
# =============================================================================


@pytest.mark.orchestrator_parallel
class TestDiamondDependency:
    r"""Tests for diamond dependency pattern: A->B,C->D where B,C->D."""

    def _create_diamond_fixture(self, base_checkpoint_path: Path) -> Path:
        r"""Create fixture with diamond pattern.

        Pattern::

                WP01
               /    \
            WP02    WP03
               \    /
                WP04
        """
        temp_dir = Path(tempfile.mkdtemp(prefix="diamond_dep_test_"))

        src_feature = base_checkpoint_path / "feature"
        dst_feature = temp_dir / "feature"
        shutil.copytree(src_feature, dst_feature)

        tasks_dir = dst_feature / "tasks"

        # Create WP03.md (depends on WP01)
        wp03_content = '''---
work_package_id: "WP03"
title: "Third Task"
lane: "planned"
dependencies: ["WP01"]
subtasks: ["T003"]
---

# Work Package: WP03 - Third Task

## Objective

Third task in diamond pattern.
'''
        (tasks_dir / "WP03.md").write_text(wp03_content)

        # Create WP04.md (depends on both WP02 and WP03)
        wp04_content = '''---
work_package_id: "WP04"
title: "Fourth Task"
lane: "planned"
dependencies: ["WP02", "WP03"]
subtasks: ["T004"]
---

# Work Package: WP04 - Fourth Task

## Objective

Fourth task - depends on both WP02 and WP03 (diamond merge).
'''
        (tasks_dir / "WP04.md").write_text(wp04_content)

        return temp_dir

    def test_diamond_pattern_is_acyclic(self):
        """Diamond pattern should not create cycles."""
        from specify_cli.core.dependency_graph import (
            build_dependency_graph,
            detect_cycles,
        )

        checkpoint_path = get_checkpoint_path("wp_created")
        if not checkpoint_path.exists():
            pytest.skip("Checkpoint fixture not found: wp_created")

        temp_dir = self._create_diamond_fixture(checkpoint_path)

        try:
            tasks_dir = temp_dir / "feature" / "tasks"
            graph = build_dependency_graph(tasks_dir)

            cycles = detect_cycles(graph)
            assert cycles is None, f"Diamond should be acyclic, got: {cycles}"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_diamond_has_correct_structure(self):
        """Diamond pattern should have correct dependency structure."""
        from specify_cli.core.dependency_graph import build_dependency_graph

        checkpoint_path = get_checkpoint_path("wp_created")
        if not checkpoint_path.exists():
            pytest.skip("Checkpoint fixture not found: wp_created")

        temp_dir = self._create_diamond_fixture(checkpoint_path)

        try:
            tasks_dir = temp_dir / "feature" / "tasks"
            graph = build_dependency_graph(tasks_dir)

            # WP01 has no dependencies
            assert graph.get("WP01", []) == [], "WP01 should have no deps"

            # WP02 depends on WP01
            assert "WP01" in graph.get("WP02", []), "WP02 should depend on WP01"

            # WP03 depends on WP01
            assert "WP01" in graph.get("WP03", []), "WP03 should depend on WP01"

            # WP04 depends on both WP02 and WP03
            wp04_deps = graph.get("WP04", [])
            assert "WP02" in wp04_deps, "WP04 should depend on WP02"
            assert "WP03" in wp04_deps, "WP04 should depend on WP03"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_diamond_topological_order(self):
        """Diamond should have valid topological order."""
        from specify_cli.core.dependency_graph import (
            build_dependency_graph,
            topological_sort,
        )

        checkpoint_path = get_checkpoint_path("wp_created")
        if not checkpoint_path.exists():
            pytest.skip("Checkpoint fixture not found: wp_created")

        temp_dir = self._create_diamond_fixture(checkpoint_path)

        try:
            tasks_dir = temp_dir / "feature" / "tasks"
            graph = build_dependency_graph(tasks_dir)
            order = topological_sort(graph)

            # WP01 should be first
            assert order.index("WP01") == 0, "WP01 should be first"

            # WP04 should be last
            assert order.index("WP04") == len(order) - 1, "WP04 should be last"

            # WP02 and WP03 should be between WP01 and WP04
            assert order.index("WP02") > order.index("WP01")
            assert order.index("WP02") < order.index("WP04")
            assert order.index("WP03") > order.index("WP01")
            assert order.index("WP03") < order.index("WP04")

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# T045: Linear Chain Test
# =============================================================================


@pytest.mark.orchestrator_parallel
class TestLinearChain:
    """Tests for linear dependency chain: WP01->WP02."""

    def test_linear_chain_in_fixture(self):
        """Fixture should have linear chain WP01->WP02."""
        from specify_cli.core.dependency_graph import build_dependency_graph

        checkpoint_path = get_checkpoint_path("wp_created")
        if not checkpoint_path.exists():
            pytest.skip("Checkpoint fixture not found: wp_created")

        tasks_dir = checkpoint_path / "feature" / "tasks"

        if not tasks_dir.exists():
            pytest.skip("No tasks directory")

        graph = build_dependency_graph(tasks_dir)

        if "WP01" in graph and "WP02" in graph:
            # WP02 should depend on WP01
            assert "WP01" in graph.get("WP02", []), (
                "WP02 should depend on WP01 in linear chain"
            )
        else:
            pytest.skip("Fixture doesn't have WP01 and WP02")

    def test_linear_chain_topological_order(self):
        """Linear chain should have A before B in topological order."""
        from specify_cli.core.dependency_graph import (
            build_dependency_graph,
            topological_sort,
        )

        checkpoint_path = get_checkpoint_path("wp_created")
        if not checkpoint_path.exists():
            pytest.skip("Checkpoint fixture not found: wp_created")

        tasks_dir = checkpoint_path / "feature" / "tasks"

        if not tasks_dir.exists():
            pytest.skip("No tasks directory")

        graph = build_dependency_graph(tasks_dir)
        order = topological_sort(graph)

        if "WP01" in order and "WP02" in order:
            assert order.index("WP01") < order.index("WP02"), (
                "WP01 should come before WP02 in linear chain"
            )

    def test_chain_failure_blocks_downstream_by_structure(self):
        """Dependency structure should reflect blocking relationship."""
        from specify_cli.core.dependency_graph import build_dependency_graph

        checkpoint_path = get_checkpoint_path("wp_created")
        if not checkpoint_path.exists():
            pytest.skip("Checkpoint fixture not found: wp_created")

        tasks_dir = checkpoint_path / "feature" / "tasks"

        if not tasks_dir.exists():
            pytest.skip("No tasks directory")

        graph = build_dependency_graph(tasks_dir)

        # Verify dependency is recorded
        if "WP02" in graph:
            deps = graph.get("WP02", [])
            assert "WP01" in deps, "WP02 should depend on WP01"


# =============================================================================
# T046: Fan-out Pattern Test
# =============================================================================


@pytest.mark.orchestrator_parallel
class TestFanOutPattern:
    """Tests for fan-out dependency pattern: WP01->WP02, WP01->WP03."""

    def _create_fanout_fixture(self, base_checkpoint_path: Path) -> Path:
        r"""Create fixture with fan-out pattern.

        Pattern::

                WP01
               /    \
            WP02    WP03
        """
        temp_dir = Path(tempfile.mkdtemp(prefix="fanout_dep_test_"))

        src_feature = base_checkpoint_path / "feature"
        dst_feature = temp_dir / "feature"
        shutil.copytree(src_feature, dst_feature)

        tasks_dir = dst_feature / "tasks"

        # Create WP03.md (depends on WP01, parallel to WP02)
        wp03_content = '''---
work_package_id: "WP03"
title: "Third Task (Parallel)"
lane: "planned"
dependencies: ["WP01"]
subtasks: ["T003"]
---

# Work Package: WP03 - Third Task

## Objective

Third task - parallel to WP02, both depend on WP01.
'''
        (tasks_dir / "WP03.md").write_text(wp03_content)

        return temp_dir

    def test_fanout_pattern_is_acyclic(self):
        """Fan-out pattern should not create cycles."""
        from specify_cli.core.dependency_graph import (
            build_dependency_graph,
            detect_cycles,
        )

        checkpoint_path = get_checkpoint_path("wp_created")
        if not checkpoint_path.exists():
            pytest.skip("Checkpoint fixture not found: wp_created")

        temp_dir = self._create_fanout_fixture(checkpoint_path)

        try:
            tasks_dir = temp_dir / "feature" / "tasks"
            graph = build_dependency_graph(tasks_dir)

            cycles = detect_cycles(graph)
            assert cycles is None, f"Fan-out should be acyclic, got: {cycles}"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_fanout_has_correct_structure(self):
        """Fan-out pattern should have WP02 and WP03 depending on WP01."""
        from specify_cli.core.dependency_graph import build_dependency_graph

        checkpoint_path = get_checkpoint_path("wp_created")
        if not checkpoint_path.exists():
            pytest.skip("Checkpoint fixture not found: wp_created")

        temp_dir = self._create_fanout_fixture(checkpoint_path)

        try:
            tasks_dir = temp_dir / "feature" / "tasks"
            graph = build_dependency_graph(tasks_dir)

            # WP01 has no dependencies
            assert graph.get("WP01", []) == [], "WP01 should have no deps"

            # Both WP02 and WP03 depend on WP01
            assert "WP01" in graph.get("WP02", []), "WP02 should depend on WP01"
            assert "WP01" in graph.get("WP03", []), "WP03 should depend on WP01"

            # WP02 and WP03 don't depend on each other
            assert "WP03" not in graph.get("WP02", []), "WP02 should not depend on WP03"
            assert "WP02" not in graph.get("WP03", []), "WP03 should not depend on WP02"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_fanout_children_can_run_parallel(self):
        """Fan-out children should be schedulable in parallel (same level)."""
        from specify_cli.core.dependency_graph import (
            build_dependency_graph,
            topological_sort,
        )

        checkpoint_path = get_checkpoint_path("wp_created")
        if not checkpoint_path.exists():
            pytest.skip("Checkpoint fixture not found: wp_created")

        temp_dir = self._create_fanout_fixture(checkpoint_path)

        try:
            tasks_dir = temp_dir / "feature" / "tasks"
            graph = build_dependency_graph(tasks_dir)
            order = topological_sort(graph)

            # WP01 should be first
            assert order.index("WP01") == 0, "WP01 should be first"

            # WP02 and WP03 should both come after WP01
            assert order.index("WP02") > order.index("WP01")
            assert order.index("WP03") > order.index("WP01")

            # WP02 and WP03 can be at the same level (both after WP01)
            # The topological sort might put them in any relative order
            # but they're both valid second-level WPs

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_fanout_parent_must_complete_first(self):
        """In fan-out, parent WP must be scheduled before all children."""
        from specify_cli.core.dependency_graph import (
            build_dependency_graph,
            topological_sort,
        )

        checkpoint_path = get_checkpoint_path("wp_created")
        if not checkpoint_path.exists():
            pytest.skip("Checkpoint fixture not found: wp_created")

        temp_dir = self._create_fanout_fixture(checkpoint_path)

        try:
            tasks_dir = temp_dir / "feature" / "tasks"
            graph = build_dependency_graph(tasks_dir)
            order = topological_sort(graph)

            wp01_idx = order.index("WP01")

            # All children must come after parent
            for wp_id in ["WP02", "WP03"]:
                if wp_id in order:
                    assert order.index(wp_id) > wp01_idx, (
                        f"{wp_id} should come after WP01"
                    )

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
