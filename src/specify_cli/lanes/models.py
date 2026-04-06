"""Data models for execution lanes.

An ExecutionLane groups work packages that must share a single
worktree and branch because they are sequentially dependent or
have overlapping write scopes.

A LanesManifest is the complete lane assignment for a feature,
persisted as lanes.json.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExecutionLane:
    """A group of WPs sharing one worktree and branch.

    Attributes:
        lane_id: Identifier like "lane-a", "lane-b".
        wp_ids: WP IDs ordered by execution sequence within the lane.
        write_scope: Union of owned_files globs from all WPs in the lane.
        predicted_surfaces: Surface tags from the surface taxonomy.
        depends_on_lanes: Lane IDs that must complete before this lane starts.
        parallel_group: Lanes with the same group number can run in parallel.
    """

    lane_id: str
    wp_ids: tuple[str, ...]
    write_scope: tuple[str, ...]
    predicted_surfaces: tuple[str, ...]
    depends_on_lanes: tuple[str, ...]
    parallel_group: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane_id": self.lane_id,
            "wp_ids": list(self.wp_ids),
            "write_scope": list(self.write_scope),
            "predicted_surfaces": list(self.predicted_surfaces),
            "depends_on_lanes": list(self.depends_on_lanes),
            "parallel_group": self.parallel_group,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionLane:
        return cls(
            lane_id=data["lane_id"],
            wp_ids=tuple(data["wp_ids"]),
            write_scope=tuple(data.get("write_scope", [])),
            predicted_surfaces=tuple(data.get("predicted_surfaces", [])),
            depends_on_lanes=tuple(data.get("depends_on_lanes", [])),
            parallel_group=data.get("parallel_group", 0),
        )


@dataclass
class LanesManifest:
    """Complete lane assignment for a feature.

    Attributes:
        version: Schema version (currently 1).
        mission_slug: Human-readable slug used in branch names.
        mission_id: Immutable ULID from meta.json. Used for merge locks and
            runtime identity. May equal mission_slug if backfill hasn't run.
        mission_branch: Integration branch name (kitty/mission-{mission_slug}).
        target_branch: Branch the mission merges into (e.g. "main").
        lanes: Ordered list of execution lanes.
        computed_at: ISO 8601 timestamp of computation.
        computed_from: Description of inputs used (e.g. "dependency_graph+ownership").
        planning_artifact_wps: WP IDs excluded from lane assignment because they
            are planning artifacts (execution_mode == planning_artifact).
    """

    version: int
    mission_slug: str
    mission_id: str
    mission_branch: str
    target_branch: str
    lanes: list[ExecutionLane]
    computed_at: str
    computed_from: str
    planning_artifact_wps: list[str] = field(default_factory=list)

    def lane_for_wp(self, wp_id: str) -> ExecutionLane | None:
        """Return the lane containing the given WP, or None."""
        for lane in self.lanes:
            if wp_id in lane.wp_ids:
                return lane
        return None

    def parallel_groups(self) -> dict[int, list[ExecutionLane]]:
        """Group lanes by their parallel_group number."""
        groups: dict[int, list[ExecutionLane]] = {}
        for lane in self.lanes:
            groups.setdefault(lane.parallel_group, []).append(lane)
        return groups

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "mission_slug": self.mission_slug,
            "mission_id": self.mission_id,
            "mission_branch": self.mission_branch,
            "target_branch": self.target_branch,
            "lanes": [lane.to_dict() for lane in self.lanes],
            "computed_at": self.computed_at,
            "computed_from": self.computed_from,
            "planning_artifact_wps": self.planning_artifact_wps,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LanesManifest:
        mission_slug = data["mission_slug"]
        return cls(
            version=data["version"],
            mission_slug=mission_slug,
            mission_id=data.get("mission_id", mission_slug),
            mission_branch=data["mission_branch"],
            target_branch=data["target_branch"],
            lanes=[ExecutionLane.from_dict(lane) for lane in data["lanes"]],
            computed_at=data["computed_at"],
            computed_from=data["computed_from"],
            planning_artifact_wps=data.get("planning_artifact_wps", []),
        )
