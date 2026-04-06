"""Lane computation algorithm.

Groups work packages into execution lanes using a union-find structure.
Two WPs are placed in the same lane when:

1. One depends on the other (any dependency → same lane).
2. They have overlapping owned_files globs (write-scope conflict).
3. They share predicted surface tags.

After grouping, WPs within each lane are topologically sorted,
and lane-level dependencies and parallel groups are computed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import combinations

from specify_cli.core.dependency_graph import topological_sort
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.ownership.models import ExecutionMode, OwnershipManifest
from specify_cli.ownership.validation import _globs_overlap

# Surface taxonomy for conflict detection.
# If two WPs predict the same surface, they are presumed to overlap.
SURFACE_TAXONOMY: tuple[str, ...] = (
    "dashboard",
    "workspace",
    "app-shell",
    "legacy-cleanup",
    "tests",
    "tracker-integration",
    "artifact-rendering",
    "api",
)

# Keywords that map to surface tags (case-insensitive substring match).
_SURFACE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "dashboard": ("dashboard", "landing page", "landing-page"),
    "workspace": ("workspace", "mission workspace"),
    "app-shell": ("app shell", "app-shell", "navigation", "sidebar", "layout"),
    "legacy-cleanup": ("legacy", "cleanup", "deprecat", "remov"),
    "tests": ("test suite", "test infrastructure", "e2e test", "integration test"),
    "tracker-integration": ("tracker", "saas", "sync"),
    "artifact-rendering": ("artifact", "render", "template"),
    "api": ("api", "endpoint", "route", "view"),
}


# ---------------------------------------------------------------------------
# Union-Find
# ---------------------------------------------------------------------------

class _UnionFind:
    """Disjoint-set data structure with union-by-rank and path compression."""

    def __init__(self, elements: list[str]) -> None:
        self._parent: dict[str, str] = {e: e for e in elements}
        self._rank: dict[str, int] = {e: 0 for e in elements}

    def find(self, x: str) -> str:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self._rank[ra] < self._rank[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        if self._rank[ra] == self._rank[rb]:
            self._rank[ra] += 1

    def groups(self) -> dict[str, list[str]]:
        """Return mapping of root → list of members."""
        result: dict[str, list[str]] = {}
        for element in self._parent:
            root = self.find(element)
            result.setdefault(root, []).append(element)
        return result


# ---------------------------------------------------------------------------
# Surface inference
# ---------------------------------------------------------------------------

def infer_surfaces(wp_body: str) -> list[str]:
    """Infer surface tags from WP body text using keyword matching.

    Args:
        wp_body: The markdown body of a work package.

    Returns:
        List of matched surface taxonomy tags.
    """
    body_lower = wp_body.lower()
    matched: list[str] = []
    for surface, keywords in _SURFACE_KEYWORDS.items():
        if any(kw in body_lower for kw in keywords):
            matched.append(surface)
    return matched


# ---------------------------------------------------------------------------
# Overlap pair detection
# ---------------------------------------------------------------------------

def find_overlap_pairs(
    manifests: dict[str, OwnershipManifest],
) -> list[tuple[str, str]]:
    """Return pairs of WP IDs whose owned_files globs overlap.

    Args:
        manifests: Mapping of WP ID to OwnershipManifest.

    Returns:
        List of (wp_a, wp_b) tuples with overlapping write scopes.
    """
    pairs: list[tuple[str, str]] = []
    wp_ids = sorted(manifests.keys())
    for wp_a, wp_b in combinations(wp_ids, 2):
        for glob_a in manifests[wp_a].owned_files:
            for glob_b in manifests[wp_b].owned_files:
                if _globs_overlap(glob_a, glob_b):
                    pairs.append((wp_a, wp_b))
                    break
            else:
                continue
            break
    return pairs


# ---------------------------------------------------------------------------
# Main computation
# ---------------------------------------------------------------------------

def compute_lanes(
    dependency_graph: dict[str, list[str]],
    ownership_manifests: dict[str, OwnershipManifest],
    mission_slug: str,
    target_branch: str = "main",
    wp_bodies: dict[str, str] | None = None,
    mission_id: str | None = None,
) -> LanesManifest:
    """Compute execution lanes from dependency graph and ownership manifests.

    Algorithm:
    1. Filter out planning_artifact WPs (they run on main repo, not in lanes).
    2. Union WPs that depend on each other (rule 1).
    3. Union WPs with overlapping owned_files (rule 2).
    4. Union WPs sharing predicted surfaces (rule 3).
    5. Build ExecutionLane per disjoint set, sorted internally by topo order.
    6. Compute lane-level dependencies and parallel groups.

    Args:
        dependency_graph: WP ID → list of dependency WP IDs.
        ownership_manifests: WP ID → OwnershipManifest.
        mission_slug: Feature identifier.
        target_branch: Branch the mission merges into.
        wp_bodies: Optional WP ID → body text for surface inference.

    Returns:
        A LanesManifest ready for persistence.
    """
    resolved_mission_id = mission_id or mission_slug

    # Collect all WP IDs from the graph.
    all_wp_ids = sorted(dependency_graph.keys())
    if not all_wp_ids:
        return _empty_manifest(mission_slug, target_branch, resolved_mission_id)

    # Separate planning artifacts — they don't get lanes.
    code_wp_ids: list[str] = []
    for wp_id in all_wp_ids:
        manifest = ownership_manifests.get(wp_id)
        if manifest and manifest.execution_mode == ExecutionMode.PLANNING_ARTIFACT:
            continue
        code_wp_ids.append(wp_id)

    if not code_wp_ids:
        return _empty_manifest(mission_slug, target_branch, resolved_mission_id)

    # Build union-find over code WPs.
    uf = _UnionFind(code_wp_ids)

    # Rule 1: Dependencies → same lane.
    for wp_id in code_wp_ids:
        for dep in dependency_graph.get(wp_id, []):
            if dep in uf._parent:
                uf.union(wp_id, dep)

    # Rule 2: Overlapping write scopes → same lane.
    code_manifests = {
        wp: ownership_manifests[wp]
        for wp in code_wp_ids
        if wp in ownership_manifests
    }
    for wp_a, wp_b in find_overlap_pairs(code_manifests):
        uf.union(wp_a, wp_b)

    # Rule 3: Shared predicted surfaces → same lane.
    if wp_bodies:
        wp_surfaces: dict[str, list[str]] = {}
        for wp_id in code_wp_ids:
            body = wp_bodies.get(wp_id, "")
            wp_surfaces[wp_id] = infer_surfaces(body)

        # For each pair sharing a surface, union them.
        for wp_a, wp_b in combinations(code_wp_ids, 2):
            surfaces_a = set(wp_surfaces.get(wp_a, []))
            surfaces_b = set(wp_surfaces.get(wp_b, []))
            if surfaces_a & surfaces_b:
                uf.union(wp_a, wp_b)

    # Build lane groups from union-find.
    raw_groups = uf.groups()

    # Order WPs within each lane by topological sort.
    lanes: list[ExecutionLane] = []
    lane_letter = ord("a")

    # Sort groups deterministically by lowest WP ID in each group.
    sorted_groups = sorted(raw_groups.values(), key=lambda g: min(g))

    # Build a sub-graph for each group to topologically sort within it.
    for group_wps in sorted_groups:
        group_set = set(group_wps)
        sub_graph = {
            wp: [d for d in dependency_graph.get(wp, []) if d in group_set]
            for wp in group_wps
        }
        ordered_wps = topological_sort(sub_graph)

        # Collect write scopes and surfaces for the lane.
        lane_write_scope: set[str] = set()
        lane_surfaces: set[str] = set()
        for wp_id in ordered_wps:
            m = ownership_manifests.get(wp_id)
            if m:
                lane_write_scope.update(m.owned_files)
            if wp_bodies:
                lane_surfaces.update(infer_surfaces(wp_bodies.get(wp_id, "")))

        lane_id = f"lane-{chr(lane_letter)}"
        lane_letter += 1

        lanes.append(
            ExecutionLane(
                lane_id=lane_id,
                wp_ids=tuple(ordered_wps),
                write_scope=tuple(sorted(lane_write_scope)),
                predicted_surfaces=tuple(sorted(lane_surfaces)),
                depends_on_lanes=(),  # Filled in below.
                parallel_group=0,  # Filled in below.
            )
        )

    # Compute lane-level dependencies.
    # Lane B depends on lane A if any WP in B depends on any WP in A
    # (and they are in different lanes — which only happens via write-scope grouping).
    wp_to_lane: dict[str, str] = {}
    for lane in lanes:
        for wp_id in lane.wp_ids:
            wp_to_lane[wp_id] = lane.lane_id

    lane_deps: dict[str, set[str]] = {lane.lane_id: set() for lane in lanes}
    for wp_id in code_wp_ids:
        my_lane = wp_to_lane.get(wp_id)
        if not my_lane:
            continue
        for dep in dependency_graph.get(wp_id, []):
            dep_lane = wp_to_lane.get(dep)
            if dep_lane and dep_lane != my_lane:
                lane_deps[my_lane].add(dep_lane)

    # Assign parallel groups via topological sort of lane DAG.
    # Lanes at the same depth in the DAG can run in parallel.
    lane_depth = _compute_lane_depths(lanes, lane_deps)

    # Rebuild lanes with depends_on_lanes and parallel_group.
    final_lanes: list[ExecutionLane] = []
    for lane in lanes:
        final_lanes.append(
            ExecutionLane(
                lane_id=lane.lane_id,
                wp_ids=lane.wp_ids,
                write_scope=lane.write_scope,
                predicted_surfaces=lane.predicted_surfaces,
                depends_on_lanes=tuple(sorted(lane_deps[lane.lane_id])),
                parallel_group=lane_depth[lane.lane_id],
            )
        )

    mission_branch = f"kitty/mission-{mission_slug}"

    return LanesManifest(
        version=1,
        mission_slug=mission_slug,
        mission_id=resolved_mission_id,
        mission_branch=mission_branch,
        target_branch=target_branch,
        lanes=final_lanes,
        computed_at=datetime.now(timezone.utc).isoformat(),
        computed_from="dependency_graph+ownership",
    )


def _compute_lane_depths(
    lanes: list[ExecutionLane],
    lane_deps: dict[str, set[str]],
) -> dict[str, int]:
    """Compute the depth (parallel group) of each lane in the lane DAG.

    Lanes with no dependencies get depth 0. A lane's depth is one plus
    the maximum depth of its dependencies.
    """
    depths: dict[str, int] = {}

    def _depth(lane_id: str) -> int:
        if lane_id in depths:
            return depths[lane_id]
        deps = lane_deps.get(lane_id, set())
        if not deps:
            depths[lane_id] = 0
        else:
            depths[lane_id] = 1 + max(_depth(d) for d in deps)
        return depths[lane_id]

    for lane in lanes:
        _depth(lane.lane_id)

    return depths


def _empty_manifest(
    mission_slug: str, target_branch: str, mission_id: str,
) -> LanesManifest:
    """Return an empty LanesManifest (no code WPs to lane)."""
    return LanesManifest(
        version=1,
        mission_slug=mission_slug,
        mission_id=mission_id,
        mission_branch=f"kitty/mission-{mission_slug}",
        target_branch=target_branch,
        lanes=[],
        computed_at=datetime.now(timezone.utc).isoformat(),
        computed_from="dependency_graph+ownership",
    )
