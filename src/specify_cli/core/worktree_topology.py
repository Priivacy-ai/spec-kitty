"""Worktree topology analysis for stacked work package branches.

When WPs branch from other WPs (stacking), agents need visibility into the
dependency stack to understand that being "behind main" is expected behavior.
This module materializes the full worktree topology and renders it as structured
JSON for prompt injection.

Key concepts:
- A WP is "stacked" if its base_branch (from workspace context) points to
  another WP's branch rather than the feature's target branch.
- Topology is only injected into prompts when has_stacking is True.
- JSON output is wrapped in HTML comment markers for reliable agent parsing.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from specify_cli.core.feature_detection import get_feature_target_branch
from specify_cli.core.dependency_graph import build_dependency_graph, topological_sort
from specify_cli.core.paths import get_main_repo_root
from specify_cli.workspace_context import list_contexts
from specify_cli.frontmatter import read_frontmatter


@dataclass
class WPTopologyEntry:
    """Per-WP topology information."""

    wp_id: str
    branch_name: Optional[str]  # None if worktree not yet created
    base_branch: Optional[str]  # None if worktree not yet created
    base_wp: Optional[str]  # WP ID of base, or None if based on target branch
    dependencies: list[str] = field(default_factory=list)
    lane: str = "planned"
    worktree_exists: bool = False
    commits_ahead_of_base: int = 0


@dataclass
class FeatureTopology:
    """Full feature worktree topology."""

    feature_slug: str
    target_branch: str
    entries: list[WPTopologyEntry] = field(default_factory=list)

    @property
    def has_stacking(self) -> bool:
        """True if any WP bases on another WP rather than target branch."""
        return any(e.base_wp is not None for e in self.entries)

    def get_entry(self, wp_id: str) -> Optional[WPTopologyEntry]:
        """Get entry for a specific WP."""
        for entry in self.entries:
            if entry.wp_id == wp_id:
                return entry
        return None

    def get_actual_base_for_wp(self, wp_id: str) -> str:
        """Get the actual base branch for a WP (may be another WP's branch)."""
        entry = self.get_entry(wp_id)
        if entry and entry.base_branch:
            return entry.base_branch
        return self.target_branch


def _resolve_base_wp(
    base_branch: str,
    feature_slug: str,
    wp_branches: dict[str, str],
) -> Optional[str]:
    """Determine if base_branch is another WP's branch.

    Args:
        base_branch: The base branch name from workspace context
        feature_slug: Feature slug for pattern matching
        wp_branches: Map of WP ID -> branch name

    Returns:
        WP ID if base is another WP, None if base is target branch
    """
    for wp_id, branch in wp_branches.items():
        if branch == base_branch:
            return wp_id
    return None


def _count_commits_ahead(
    worktree_path: Path,
    base_branch: str,
) -> int:
    """Count commits ahead of base branch in worktree.

    Returns 0 on any error.
    """
    result = subprocess.run(
        ["git", "rev-list", "--count", f"{base_branch}..HEAD"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        try:
            return int(result.stdout.strip())
        except ValueError:
            pass
    return 0


def materialize_worktree_topology(
    repo_root: Path,
    feature_slug: str,
) -> FeatureTopology:
    """Gather the full worktree topology for a feature.

    Combines workspace contexts, WP frontmatter, dependency graph,
    and git rev-list counts into a complete topology view.

    Args:
        repo_root: Main repository root path
        feature_slug: Feature slug (e.g., "002-event-driven")

    Returns:
        FeatureTopology with all WP entries in topological order
    """
    main_repo_root = get_main_repo_root(repo_root)
    target_branch = get_feature_target_branch(main_repo_root, feature_slug)

    feature_dir = main_repo_root / "kitty-specs" / feature_slug
    graph = build_dependency_graph(feature_dir)

    # Get topological order (dependencies before dependents)
    try:
        topo_order = topological_sort(graph)
    except ValueError:
        # Cycle detected — fall back to sorted keys
        topo_order = sorted(graph.keys())

    # Build WP branch map from workspace contexts
    contexts = list_contexts(main_repo_root)
    feature_contexts = {
        ctx.wp_id: ctx
        for ctx in contexts
        if ctx.feature_slug == feature_slug
    }

    # Map WP ID -> branch name for base resolution
    wp_branches: dict[str, str] = {}
    for wp_id, ctx in feature_contexts.items():
        wp_branches[wp_id] = ctx.branch_name

    # Read lane status from WP frontmatter
    tasks_dir = feature_dir / "tasks"
    wp_lanes: dict[str, str] = {}
    if tasks_dir.exists():
        for wp_file in tasks_dir.glob("WP*.md"):
            try:
                fm, _ = read_frontmatter(wp_file)
                wp_id = fm.get("work_package_id", wp_file.stem.split("-")[0])
                wp_lanes[wp_id] = fm.get("lane", "planned")
            except Exception:
                pass

    # Build topology entries
    entries: list[WPTopologyEntry] = []
    for wp_id in topo_order:
        ctx = feature_contexts.get(wp_id)
        branch_name = ctx.branch_name if ctx else None
        base_branch = ctx.base_branch if ctx else None
        dependencies = graph.get(wp_id, [])
        lane = wp_lanes.get(wp_id, "planned")

        # Determine if base is another WP
        base_wp = None
        if base_branch:
            base_wp = _resolve_base_wp(base_branch, feature_slug, wp_branches)

        # Count commits ahead of base
        commits_ahead = 0
        worktree_path = main_repo_root / ".worktrees" / f"{feature_slug}-{wp_id}"
        worktree_exists = worktree_path.exists()
        if worktree_exists and base_branch:
            commits_ahead = _count_commits_ahead(worktree_path, base_branch)

        entries.append(WPTopologyEntry(
            wp_id=wp_id,
            branch_name=branch_name,
            base_branch=base_branch,
            base_wp=base_wp,
            dependencies=dependencies,
            lane=lane,
            worktree_exists=worktree_exists,
            commits_ahead_of_base=commits_ahead,
        ))

    return FeatureTopology(
        feature_slug=feature_slug,
        target_branch=target_branch,
        entries=entries,
    )


def render_topology_json(
    topology: FeatureTopology,
    current_wp_id: str,
) -> list[str]:
    """Render topology as structured JSON for prompt injection.

    Only call this when topology.has_stacking is True.
    Output is wrapped in HTML comment markers for reliable agent parsing.

    Args:
        topology: Feature topology data
        current_wp_id: The WP being implemented/reviewed

    Returns:
        List of lines to append to prompt
    """
    current_entry = topology.get_entry(current_wp_id)

    # Build base info for current WP
    your_base = None
    if current_entry and current_entry.base_wp:
        your_base = {
            "branch": current_entry.base_branch,
            "wp": current_entry.base_wp,
        }

    # Build diff command
    diff_base = topology.get_actual_base_for_wp(current_wp_id)
    diff_command = f"git diff {diff_base}..HEAD"

    # Build entries list
    entries_json = []
    for entry in topology.entries:
        entry_data: dict = {
            "wp": entry.wp_id,
            "lane": entry.lane,
            "branch": entry.branch_name,
            "base": entry.base_wp if entry.base_wp else topology.target_branch,
        }
        if entry.worktree_exists:
            entry_data["commits_ahead"] = entry.commits_ahead_of_base
        if entry.dependencies and not entry.worktree_exists:
            entry_data["dependencies"] = entry.dependencies
        entries_json.append(entry_data)

    payload = {
        "feature": topology.feature_slug,
        "target_branch": topology.target_branch,
        "current_wp": current_wp_id,
        "your_base": your_base,
        "diff_command": diff_command,
        "stacked": True,
        "note": f"Your branch stacks on {current_entry.base_wp}, NOT {topology.target_branch}. Do not worry about being 'behind {topology.target_branch}'."
            if current_entry and current_entry.base_wp
            else f"Your branch is based on {topology.target_branch}. Other WPs in this feature use stacking.",
        "entries": entries_json,
    }

    lines = [
        "<!-- WORKTREE_TOPOLOGY -->",
        json.dumps(payload, indent=2),
        "<!-- /WORKTREE_TOPOLOGY -->",
    ]
    return lines


def render_topology_text(
    topology: FeatureTopology,
    current_wp_id: str,
) -> list[str]:
    """Render topology as human-readable text for CLI output.

    Utility function for human-facing displays (not used in prompts).

    Args:
        topology: Feature topology data
        current_wp_id: The WP to highlight

    Returns:
        List of lines for console output
    """
    lines = []
    lines.append("╔" + "═" * 78 + "╗")
    lines.append("║  WORKTREE TOPOLOGY" + " " * 59 + "║")
    lines.append("╠" + "═" * 78 + "╣")
    lines.append(f"║  Feature: {topology.feature_slug:<66} ║")
    lines.append(f"║  Target:  {topology.target_branch:<66} ║")
    lines.append("║" + " " * 78 + "║")

    for entry in topology.entries:
        marker = "→" if entry.wp_id == current_wp_id else " "
        base_label = entry.base_wp if entry.base_wp else topology.target_branch
        branch_label = entry.branch_name or "(not created)"
        status = entry.lane

        line_text = f"{marker} {entry.wp_id} [{status}] base={base_label} branch={branch_label}"
        if entry.worktree_exists and entry.commits_ahead_of_base > 0:
            line_text += f" (+{entry.commits_ahead_of_base})"

        # Pad to fit box
        padded = line_text[:76].ljust(76)
        lines.append(f"║  {padded}║")

    lines.append("╚" + "═" * 78 + "╝")
    return lines


__all__ = [
    "WPTopologyEntry",
    "FeatureTopology",
    "materialize_worktree_topology",
    "render_topology_json",
    "render_topology_text",
]
