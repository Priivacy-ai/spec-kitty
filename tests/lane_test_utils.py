"""Helpers for lane-only test fixtures."""

from __future__ import annotations

from pathlib import Path

from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import write_lanes_json


def write_single_lane_manifest(
    feature_dir: Path,
    *,
    wp_ids: tuple[str, ...] = ("WP01",),
    lane_id: str = "lane-a",
    target_branch: str = "main",
    mission_id: str | None = None,
    write_scope: tuple[str, ...] = ("src/**",),
    predicted_surfaces: tuple[str, ...] = ("test",),
    depends_on_lanes: tuple[str, ...] = (),
    parallel_group: int = 0,
) -> Path:
    """Persist a minimal valid lanes.json for tests."""
    return write_lanes_json(
        feature_dir,
        LanesManifest(
            version=1,
            mission_slug=feature_dir.name,
            mission_id=mission_id or feature_dir.name,
            mission_branch=f"kitty/mission-{feature_dir.name}",
            target_branch=target_branch,
            lanes=[
                ExecutionLane(
                    lane_id=lane_id,
                    wp_ids=wp_ids,
                    write_scope=write_scope,
                    predicted_surfaces=predicted_surfaces,
                    depends_on_lanes=depends_on_lanes,
                    parallel_group=parallel_group,
                )
            ],
            computed_at="2026-04-05T12:00:00Z",
            computed_from="test",
        ),
    )


def lane_worktree_path(repo_root: Path, mission_slug: str, lane_id: str = "lane-a") -> Path:
    """Return the lane worktree path for a feature."""
    return repo_root / ".worktrees" / f"{mission_slug}-{lane_id}"


def lane_branch_name(mission_slug: str, lane_id: str = "lane-a") -> str:
    """Return the lane branch name for a feature."""
    return f"kitty/mission-{mission_slug}-{lane_id}"
