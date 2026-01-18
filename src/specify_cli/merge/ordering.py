"""Merge ordering based on WP dependencies.

Implements FR-008 through FR-011: determining merge order via topological
sort of the dependency graph.
"""

from __future__ import annotations

__all__: list[str] = []
