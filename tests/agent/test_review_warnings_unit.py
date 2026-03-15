"""Unit tests for get_dependents() in dependency_graph — root-node and fanout cases.

Covers the inverse-graph query that returns direct dependents of a given WP ID.
All tests are pure in-memory (no filesystem I/O).
"""

from __future__ import annotations

import pytest

from specify_cli.core.dependency_graph import get_dependents

pytestmark = pytest.mark.fast


class TestGetDependentsRootNode:
    """get_dependents() returns [] for root nodes (no one depends on them)."""

    def test_root_node_empty_graph(self) -> None:
        """A WP in an otherwise empty graph has no dependents."""
        # Arrange
        graph: dict[str, list[str]] = {"WP01": []}

        # Assumption check
        assert "WP01" in graph

        # Act
        result = get_dependents("WP01", graph)

        # Assert
        assert result == []

    def test_root_node_multi_wp_graph(self) -> None:
        """A leaf node that no other WP depends on returns []."""
        # Arrange
        graph = {
            "WP01": [],
            "WP02": ["WP01"],
            "WP03": ["WP02"],
        }

        # Assumption check
        assert "WP03" in graph
        assert graph["WP03"] == ["WP02"]

        # Act
        result = get_dependents("WP03", graph)

        # Assert
        assert result == []

    def test_wp_not_in_graph_returns_empty(self) -> None:
        """A WP ID not present in the graph returns [] (not KeyError)."""
        # Arrange
        graph = {"WP01": [], "WP02": ["WP01"]}

        # Assumption check
        assert "WP99" not in graph

        # Act
        result = get_dependents("WP99", graph)

        # Assert
        assert result == []

    def test_empty_graph_returns_empty(self) -> None:
        """An entirely empty graph returns [] for any WP ID."""
        # Arrange
        graph: dict[str, list[str]] = {}

        # Assumption check
        assert len(graph) == 0

        # Act
        result = get_dependents("WP01", graph)

        # Assert
        assert result == []


class TestGetDependentsFanout:
    """get_dependents() returns correct direct dependents for shared dependencies."""

    def test_single_dependent(self) -> None:
        """A WP depended on by exactly one other WP returns that one WP."""
        # Arrange
        graph = {"WP01": [], "WP02": ["WP01"]}

        # Assumption check
        assert graph["WP02"] == ["WP01"]

        # Act
        result = get_dependents("WP01", graph)

        # Assert
        assert result == ["WP02"]

    def test_multiple_dependents(self) -> None:
        """A WP depended on by two WPs returns both."""
        # Arrange
        graph = {
            "WP01": [],
            "WP02": ["WP01"],
            "WP03": ["WP01"],
        }

        # Assumption check
        assert graph["WP02"] == ["WP01"]
        assert graph["WP03"] == ["WP01"]

        # Act
        result = get_dependents("WP01", graph)

        # Assert
        assert sorted(result) == ["WP02", "WP03"]

    def test_direct_only_not_transitive(self) -> None:
        """get_dependents() returns only direct dependents, not transitive ones."""
        # Arrange
        graph = {
            "WP01": [],
            "WP02": ["WP01"],
            "WP03": ["WP02"],  # WP03 depends on WP02, not WP01 directly
        }

        # Assumption check
        assert "WP01" not in graph["WP03"]

        # Act
        result = get_dependents("WP01", graph)

        # Assert
        assert result == ["WP02"]
        assert "WP03" not in result

    def test_middle_node_dependents(self) -> None:
        """A node in the middle of the chain has correct direct dependents."""
        # Arrange
        graph = {
            "WP01": [],
            "WP02": ["WP01"],
            "WP03": ["WP02"],
            "WP04": ["WP02"],
        }

        # Assumption check
        assert graph["WP03"] == ["WP02"]
        assert graph["WP04"] == ["WP02"]

        # Act
        result = get_dependents("WP02", graph)

        # Assert
        assert sorted(result) == ["WP03", "WP04"]
