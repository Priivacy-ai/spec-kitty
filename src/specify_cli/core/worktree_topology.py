"""Lane worktree topology analysis.

Agents need a deterministic view of which work packages share a lane worktree,
which lane branch they are on, and what the diff base is. This module renders
that lane topology as structured JSON for prompt injection and as simple text
for diagnostics.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from specify_cli.core.dependency_graph import build_dependency_graph, topological_sort
from specify_cli.core.paths import get_main_repo_root, get_feature_target_branch
from specify_cli.mission_metadata import mission_identity_fields, resolve_mission_identity
from specify_cli.status.lane_reader import CanonicalStatusNotFoundError, get_wp_lane
from specify_cli.workspace_context import resolve_workspace_for_wp


@dataclass
class WPTopologyEntry:
    """Per-WP lane topology information."""

    wp_id: str
    lane_id: str
    lane_wp_ids: list[str]
    branch_name: str
    base_branch: str
    dependencies: list[str] = field(default_factory=list)
    lane: str = "planned"
    worktree_exists: bool = False
    commits_ahead_of_base: int = 0


@dataclass
class FeatureTopology:
    """Lane topology for a feature."""

    mission_slug: str
    target_branch: str
    mission_branch: str
    mission_number: str = ""
    mission_type: str = "software-dev"
    entries: list[WPTopologyEntry] = field(default_factory=list)

    @property
    def has_stacking(self) -> bool:
        """Compatibility shim: true when the lane topology is worth injecting."""
        lane_ids = {entry.lane_id for entry in self.entries}
        return len(lane_ids) > 1 or any(len(entry.lane_wp_ids) > 1 for entry in self.entries)

    def get_entry(self, wp_id: str) -> WPTopologyEntry | None:
        for entry in self.entries:
            if entry.wp_id == wp_id:
                return entry
        return None

    def get_actual_base_for_wp(self, wp_id: str) -> str:
        entry = self.get_entry(wp_id)
        if entry is not None:
            return entry.base_branch
        return self.mission_branch


def _read_canonical_lane_or_default(feature_dir: Path, wp_id: str) -> str:
    try:
        lane = get_wp_lane(feature_dir, wp_id)
    except CanonicalStatusNotFoundError:
        return "planned"
    except Exception:
        return "planned"
    if lane == "uninitialized":
        return "planned"
    return lane


def _count_commits_ahead(worktree_path: Path, base_branch: str) -> int:
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


def materialize_worktree_topology(repo_root: Path, mission_slug: str) -> FeatureTopology:
    """Gather the full lane worktree topology for a feature."""
    from specify_cli.lanes.branch_naming import lane_branch_name
    from specify_cli.lanes.persistence import require_lanes_json

    main_repo_root = get_main_repo_root(repo_root)
    target_branch = get_feature_target_branch(main_repo_root, mission_slug)
    feature_dir = main_repo_root / "kitty-specs" / mission_slug
    identity = resolve_mission_identity(feature_dir)
    lanes_manifest = require_lanes_json(feature_dir)
    graph = build_dependency_graph(feature_dir)

    try:
        topo_order = topological_sort(graph)
    except ValueError:
        topo_order = sorted(graph.keys())

    entries: list[WPTopologyEntry] = []
    for wp_id in topo_order:
        lane_entry = lanes_manifest.lane_for_wp(wp_id)
        if lane_entry is None:
            raise ValueError(f"{wp_id} is not assigned to any lane in lanes.json")

        workspace = resolve_workspace_for_wp(main_repo_root, mission_slug, wp_id)
        worktree_exists = workspace.exists
        commits_ahead = 0
        if worktree_exists:
            commits_ahead = _count_commits_ahead(workspace.worktree_path, lanes_manifest.mission_branch)

        entries.append(
            WPTopologyEntry(
                wp_id=wp_id,
                lane_id=lane_entry.lane_id,
                lane_wp_ids=list(lane_entry.wp_ids),
                branch_name=lane_branch_name(mission_slug, lane_entry.lane_id),
                base_branch=lanes_manifest.mission_branch,
                dependencies=graph.get(wp_id, []),
                lane=_read_canonical_lane_or_default(feature_dir, wp_id),
                worktree_exists=worktree_exists,
                commits_ahead_of_base=commits_ahead,
            )
        )

    return FeatureTopology(
        mission_slug=identity.mission_slug,
        mission_number=identity.mission_number,
        mission_type=identity.mission_type,
        target_branch=target_branch,
        mission_branch=lanes_manifest.mission_branch,
        entries=entries,
    )


def render_topology_json(topology: FeatureTopology, current_wp_id: str) -> list[str]:
    """Render lane topology as structured JSON for prompt injection."""
    current_entry = topology.get_entry(current_wp_id)
    diff_base = topology.get_actual_base_for_wp(current_wp_id)
    identity = mission_identity_fields(
        topology.mission_slug,
        topology.mission_number,
        topology.mission_type,
    )

    entries_json = []
    for entry in topology.entries:
        entry_data: dict[str, object] = {
            "wp": entry.wp_id,
            "status": entry.lane,
            "lane_id": entry.lane_id,
            "lane_wp_ids": entry.lane_wp_ids,
            "branch": entry.branch_name,
            "base": entry.base_branch,
        }
        if entry.worktree_exists:
            entry_data["commits_ahead"] = entry.commits_ahead_of_base
        if entry.dependencies:
            entry_data["dependencies"] = entry.dependencies
        entries_json.append(entry_data)

    payload = {
        "mission_slug": identity["mission_slug"],
        "mission_number": identity["mission_number"],
        "mission_type": identity["mission_type"],
        "target_branch": topology.target_branch,
        "mission_branch": topology.mission_branch,
        "current_wp": current_wp_id,
        "diff_command": f"git diff {diff_base}..HEAD",
        "shared_lane": bool(current_entry and len(current_entry.lane_wp_ids) > 1),
        "note": (
            f"{current_wp_id} shares lane {current_entry.lane_id} with {', '.join(current_entry.lane_wp_ids)}. "
            "Sequential WPs in the same lane reuse one worktree."
            if current_entry and len(current_entry.lane_wp_ids) > 1
            else f"{current_wp_id} owns lane {current_entry.lane_id} alone."
            if current_entry
            else f"{current_wp_id} is not in the computed topology."
        ),
        "entries": entries_json,
    }

    return [
        "<!-- WORKTREE_TOPOLOGY -->",
        json.dumps(payload, indent=2),
        "<!-- /WORKTREE_TOPOLOGY -->",
    ]


def render_topology_text(topology: FeatureTopology, current_wp_id: str) -> list[str]:
    """Render lane topology as human-readable text."""
    lines = []
    lines.append("╔" + "═" * 78 + "╗")
    lines.append("║  LANE WORKTREE TOPOLOGY" + " " * 54 + "║")
    lines.append("╠" + "═" * 78 + "╣")
    lines.append(f"║  Feature: {topology.mission_slug:<66} ║")
    lines.append(f"║  Target:  {topology.target_branch:<66} ║")
    lines.append(f"║  Mission: {topology.mission_branch:<66} ║")
    lines.append("║" + " " * 78 + "║")

    for entry in topology.entries:
        marker = "→" if entry.wp_id == current_wp_id else " "
        lane_members = ",".join(entry.lane_wp_ids)
        line_text = (
            f"{marker} {entry.wp_id} [{entry.lane}] lane={entry.lane_id} "
            f"members={lane_members} branch={entry.branch_name}"
        )
        if entry.worktree_exists and entry.commits_ahead_of_base > 0:
            line_text += f" (+{entry.commits_ahead_of_base})"
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
