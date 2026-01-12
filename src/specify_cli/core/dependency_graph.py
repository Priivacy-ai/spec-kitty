"""Dependency graph utilities for work package relationships.

This module provides functions for parsing, validating, and analyzing
dependency relationships between work packages in Spec Kitty features.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from specify_cli.frontmatter import FrontmatterError, read_frontmatter


def parse_wp_dependencies(wp_file: Path) -> list[str]:
    """Parse dependencies from WP frontmatter.

    Uses FrontmatterManager for consistent parsing across CLI.

    Args:
        wp_file: Path to work package markdown file

    Returns:
        List of WP IDs this WP depends on (e.g., ["WP01", "WP02"])
        Returns empty list if no dependencies or parsing fails

    Examples:
        >>> wp_file = Path("tasks/WP02.md")
        >>> deps = parse_wp_dependencies(wp_file)
        >>> print(deps)  # ["WP01"]
    """
    try:
        # Use FrontmatterManager for consistent parsing
        frontmatter, _ = read_frontmatter(wp_file)

        # Extract dependencies field (FrontmatterManager already defaults to [])
        dependencies = frontmatter.get("dependencies", [])

        # Validate dependencies is a list
        if not isinstance(dependencies, list):
            return []

        return dependencies

    except (FrontmatterError, OSError):
        # Return empty list on any parsing error
        return []


def build_dependency_graph(feature_dir: Path) -> dict[str, list[str]]:
    """Build dependency graph from all WPs in feature.

    Scans tasks/ directory for WP files and parses their dependencies.
    Validates that filename WP ID matches frontmatter work_package_id.

    Args:
        feature_dir: Path to feature directory (contains tasks/ subdirectory)
                    OR path to tasks directory directly

    Returns:
        Adjacency list mapping WP ID to list of dependencies
        Example: {"WP01": [], "WP02": ["WP01"], "WP03": ["WP01"]}

    Examples:
        >>> feature_dir = Path("kitty-specs/010-feature")
        >>> graph = build_dependency_graph(feature_dir)
        >>> print(graph)  # {"WP01": [], "WP02": ["WP01"]}
    """
    graph = {}

    # Support both feature_dir and tasks_dir as input
    if feature_dir.name == "tasks":
        # Already pointing to tasks directory
        tasks_dir = feature_dir
    else:
        # Pointing to feature directory, append tasks/
        tasks_dir = feature_dir / "tasks"

    if not tasks_dir.exists():
        return graph

    # Find all WP markdown files
    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        # Extract WP ID from filename (e.g., WP01-title.md → WP01)
        filename_wp_id = extract_wp_id_from_filename(wp_file.name)
        if not filename_wp_id:
            continue

        # Parse frontmatter to get canonical work_package_id
        try:
            frontmatter, _ = read_frontmatter(wp_file)
            frontmatter_wp_id = frontmatter.get("work_package_id")

            # Verify filename matches frontmatter (catch misnamed files)
            if frontmatter_wp_id and frontmatter_wp_id != filename_wp_id:
                # Log warning but use frontmatter value as canonical
                # (Frontmatter is source of truth, filename may be stale)
                wp_id = frontmatter_wp_id
            else:
                wp_id = frontmatter_wp_id or filename_wp_id

        except (FrontmatterError, OSError):
            # If frontmatter read fails, skip this file
            continue

        # Parse dependencies from frontmatter
        dependencies = parse_wp_dependencies(wp_file)
        graph[wp_id] = dependencies

    return graph


def extract_wp_id_from_filename(filename: str) -> Optional[str]:
    """Extract WP ID from filename.

    Args:
        filename: WP file name (e.g., "WP01-title.md" or "WP02.md")

    Returns:
        WP ID (e.g., "WP01") or None if invalid format

    Examples:
        >>> extract_wp_id_from_filename("WP01-setup.md")
        'WP01'
        >>> extract_wp_id_from_filename("invalid.md")
        None
    """
    match = re.match(r"^(WP\d{2})", filename)
    return match.group(1) if match else None


def detect_cycles(graph: dict[str, list[str]]) -> list[list[str]] | None:
    """Detect circular dependencies using DFS with coloring.

    Uses depth-first search with three-color marking (white/gray/black)
    to detect back edges, which indicate cycles.

    Args:
        graph: Adjacency list mapping WP ID to dependencies

    Returns:
        List of cycles (each cycle is a list of WP IDs) or None if acyclic

    Complexity:
        O(V + E) where V = vertices (WPs), E = edges (dependencies)

    Examples:
        >>> graph = {"WP01": ["WP02"], "WP02": ["WP01"]}
        >>> cycles = detect_cycles(graph)
        >>> print(cycles)  # [["WP01", "WP02", "WP01"]]

        >>> graph = {"WP01": [], "WP02": ["WP01"]}
        >>> cycles = detect_cycles(graph)
        >>> print(cycles)  # None (acyclic)
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {wp: WHITE for wp in graph}
    cycles = []

    def dfs(node: str, path: list[str]) -> None:
        """DFS traversal with cycle detection."""
        color[node] = GRAY
        path.append(node)

        for neighbor in graph.get(node, []):
            neighbor_color = color.get(neighbor, WHITE)

            if neighbor_color == GRAY:
                # Back edge found - cycle detected
                if neighbor in path:
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
            elif neighbor_color == WHITE:
                dfs(neighbor, path)

        path.pop()
        color[node] = BLACK

    # Run DFS from each unvisited node
    for wp in graph:
        if color[wp] == WHITE:
            dfs(wp, [])

    return cycles if cycles else None


def validate_dependencies(
    wp_id: str,
    declared_deps: list[str],
    graph: dict[str, list[str]]
) -> tuple[bool, list[str]]:
    """Validate that WP's dependencies are valid.

    Checks:
    - Dependencies exist in graph
    - No self-dependencies
    - No circular dependencies
    - Valid WP ID format

    Args:
        wp_id: Work package ID being validated
        declared_deps: List of dependency WP IDs
        graph: Complete dependency graph

    Returns:
        Tuple of (is_valid, error_messages)
        - is_valid: True if all validations pass
        - error_messages: List of error descriptions (empty if valid)

    Examples:
        >>> graph = {"WP01": [], "WP02": ["WP01"]}
        >>> is_valid, errors = validate_dependencies("WP02", ["WP01"], graph)
        >>> print(is_valid)  # True

        >>> is_valid, errors = validate_dependencies("WP02", ["WP99"], graph)
        >>> print(is_valid)  # False
        >>> print(errors)  # ["Dependency WP99 not found in graph"]
    """
    errors = []
    wp_pattern = re.compile(r"^WP\d{2}$")

    # Validate each dependency
    for dep in declared_deps:
        # Check format
        if not wp_pattern.match(dep):
            errors.append(f"Invalid WP ID format: {dep} (must be WP## like WP01)")
            continue

        # Check self-dependency
        if dep == wp_id:
            errors.append(f"Cannot depend on self: {wp_id} → {wp_id}")
            continue

        # Check dependency exists in graph
        if dep not in graph:
            errors.append(f"Dependency {dep} not found in graph")

    # Check for circular dependencies
    # Build temporary graph with this WP's dependencies to check for cycles
    test_graph = graph.copy()
    test_graph[wp_id] = declared_deps

    cycles = detect_cycles(test_graph)
    if cycles:
        for cycle in cycles:
            if wp_id in cycle:
                errors.append(f"Circular dependency detected: {' → '.join(cycle)}")
                break

    is_valid = len(errors) == 0
    return is_valid, errors


def get_dependents(wp_id: str, graph: dict[str, list[str]]) -> list[str]:
    """Get list of WPs that depend on this WP (inverse graph query).

    Builds inverse graph and returns direct dependents only (not transitive).

    Args:
        wp_id: Work package ID to query
        graph: Dependency graph (adjacency list)

    Returns:
        List of WP IDs that directly depend on wp_id
        Returns empty list if no dependents or WP not in graph

    Examples:
        >>> graph = {"WP01": [], "WP02": ["WP01"], "WP03": ["WP01"]}
        >>> deps = get_dependents("WP01", graph)
        >>> print(sorted(deps))  # ["WP02", "WP03"]

        >>> deps = get_dependents("WP02", graph)
        >>> print(deps)  # []
    """
    # Build inverse graph: wp -> list of wps that depend on it
    inverse_graph: dict[str, list[str]] = {wp: [] for wp in graph}

    for wp, dependencies in graph.items():
        for dependency in dependencies:
            if dependency not in inverse_graph:
                inverse_graph[dependency] = []
            inverse_graph[dependency].append(wp)

    return inverse_graph.get(wp_id, [])


__all__ = [
    "build_dependency_graph",
    "detect_cycles",
    "get_dependents",
    "parse_wp_dependencies",
    "validate_dependencies",
]
