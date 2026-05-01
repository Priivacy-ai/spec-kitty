"""Merge ordering based on WP dependencies.

Implements FR-008 through FR-011: determining merge order via topological
sort of the dependency graph.
"""

from __future__ import annotations

import logging
from pathlib import Path

from specify_cli.core.dependency_graph import (
    build_dependency_graph,
    detect_cycles,
    topological_sort,
)

__all__ = [
    "get_merge_order",
    "MergeOrderError",
    "has_dependency_info",
    "display_merge_order",
    "assign_next_mission_number",
]

logger = logging.getLogger(__name__)


class MergeOrderError(Exception):
    """Error determining merge order."""

    pass


def has_dependency_info(graph: dict[str, list[str]]) -> bool:
    """Check if any WP has declared dependencies.

    Args:
        graph: Dependency graph mapping WP ID to list of dependencies

    Returns:
        True if at least one WP has non-empty dependencies
    """
    return any(deps for deps in graph.values())


def get_merge_order(
    wp_workspaces: list[tuple[Path, str, str]],
    feature_dir: Path,
) -> list[tuple[Path, str, str]]:
    """Return WPs in dependency order (topological sort).

    Determines the optimal merge order based on WP dependencies declared
    in frontmatter. WPs with dependencies will be merged after their
    dependencies.

    Args:
        wp_workspaces: List of (worktree_path, wp_id, branch_name) tuples
        feature_dir: Path to feature directory containing tasks/

    Returns:
        Same tuples reordered by dependency (dependencies first)

    Raises:
        MergeOrderError: If circular dependency detected
    """
    if not wp_workspaces:
        return []

    # Build WP ID → workspace mapping
    wp_map = {wp_id: (path, wp_id, branch) for path, wp_id, branch in wp_workspaces}

    # Build dependency graph from task frontmatter
    graph = build_dependency_graph(feature_dir)

    # Check for missing WPs in graph (may have no frontmatter)
    for wp_id in wp_map:
        if wp_id not in graph:
            graph[wp_id] = []  # No dependencies

    # Check if we have any dependency info
    if not has_dependency_info(graph):
        # No dependency info - fall back to numerical order with warning
        logger.warning("No dependency information found in WP frontmatter. Falling back to numerical order (WP01, WP02, ...).")
        return sorted(wp_workspaces, key=lambda x: x[1])  # Sort by wp_id

    # Detect cycles - show full cycle path in error
    cycles = detect_cycles(graph)
    if cycles:
        # Format the cycle path clearly: WP01 → WP02 → WP03 → WP01
        cycle = cycles[0]
        cycle_str = " → ".join(cycle)
        raise MergeOrderError(f"Circular dependency detected: {cycle_str}\nFix the dependencies in the WP frontmatter to remove this cycle.")

    # Topological sort
    try:
        ordered_ids = topological_sort(graph)
    except ValueError as e:
        raise MergeOrderError(str(e)) from e

    # Filter to only WPs we have workspaces for, maintaining order
    result = []
    for wp_id in ordered_ids:
        if wp_id in wp_map:
            result.append(wp_map[wp_id])

    return result


def assign_next_mission_number(target_branch_path: Path, kitty_specs_dir: Path) -> int:
    """Compute the next dense integer ``mission_number`` for the target branch.

    Walks ``kitty_specs_dir`` (which should reflect the checked-out target
    branch's ``kitty-specs/`` view), reads every mission's ``meta.json`` via
    the canonical metadata loader, collects all non-null integer
    ``mission_number`` values, and returns ``max(collected) + 1`` -- or ``1``
    if no missions on the target branch have an integer assigned yet.

    **Locking invariant (FR-044, WP10/T052/T055):** This helper does **not**
    acquire any lock.  It assumes the caller is already holding the
    merge-state lock for the mission being merged, which provides
    single-writer semantics against the target branch.  Calling this without
    the lock is a race-condition bug.

    Args:
        target_branch_path: Path to the checked-out target branch worktree
            (e.g. the merge worktree at
            ``.kittify/runtime/merge/<mission_id>/workspace/``). Currently
            unused for I/O -- present in the signature so callers explicitly
            document which branch's view they are reading.  ``kitty_specs_dir``
            must be a child of (or otherwise consistent with) this path.
        kitty_specs_dir: Path to the ``kitty-specs/`` directory on the
            target branch worktree.  Each immediate subdirectory containing a
            ``meta.json`` is treated as a mission.

    Returns:
        The next available integer ``mission_number`` (>= 1).

    Notes:
        - Pre-merge missions (``mission_number: null``) are excluded from the
          max computation by virtue of being ``None`` after coercion.
        - Legacy string forms (``"042"``) are coerced to ``int`` by
          :func:`specify_cli.mission_metadata.resolve_mission_identity` and
          participate in the max.
        - Missions whose ``meta.json`` is missing or unreadable are skipped.
    """
    # Lazy import to keep merge.ordering import-cheap and avoid any
    # mission_metadata <-> merge cycles.
    from specify_cli.mission_metadata import resolve_mission_identity

    del target_branch_path  # Documentation only -- see docstring.

    if not kitty_specs_dir.exists() or not kitty_specs_dir.is_dir():
        return 1

    collected: list[int] = []
    for child in sorted(kitty_specs_dir.iterdir()):
        if not child.is_dir():
            continue
        if not (child / "meta.json").exists():
            continue
        try:
            identity = resolve_mission_identity(child)
        except (ValueError, TypeError):
            # Malformed mission_number — skip rather than crash the merge.
            logger.warning(
                "Skipping mission %s during number assignment scan: malformed mission_number",
                child.name,
            )
            continue
        if identity.mission_number is not None:
            collected.append(identity.mission_number)

    if not collected:
        return 1
    return max(collected) + 1


def display_merge_order(
    ordered_workspaces: list[tuple[Path, str, str]],
    console,
) -> None:
    """Display the merge order to the user.

    Args:
        ordered_workspaces: Ordered list of (path, wp_id, branch) tuples
        console: Rich Console for output
    """
    if not ordered_workspaces:
        return

    console.print("\n[bold]Merge Order[/bold] (dependency-based):\n")
    for i, (_, wp_id, branch) in enumerate(ordered_workspaces, 1):
        console.print(f"  {i}. {wp_id} ({branch})")
    console.print()
