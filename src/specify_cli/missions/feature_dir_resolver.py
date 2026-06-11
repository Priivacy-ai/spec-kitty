"""Feature directory resolver backed by the canonical action context."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from specify_cli.core.constants import KITTY_SPECS_DIR


def candidate_feature_dir_for_mission(repo_root: Path, mission_slug: str) -> Path:
    """Return the topology-aware mission-dir candidate without requiring it to exist."""
    from specify_cli.coordination.workspace import CoordinationWorkspace
    from specify_cli.lanes.branch_naming import mid8_from_slug
    from specify_cli.missions._read_path_resolver import _compose_mission_dir

    mid8 = mid8_from_slug(mission_slug)
    mission_dir_name: str = _compose_mission_dir(mission_slug, mid8)
    primary_candidate: Path = repo_root / KITTY_SPECS_DIR / mission_dir_name
    coord_candidate: Path | None = None
    if mid8:
        coord_root: Path = CoordinationWorkspace.worktree_path(repo_root, mission_slug, mid8)
        coord_candidate = coord_root / KITTY_SPECS_DIR / mission_dir_name
        if coord_candidate.exists() and (coord_candidate / "meta.json").exists():
            return coord_candidate
    if primary_candidate.exists():
        return primary_candidate
    if coord_candidate is not None and coord_candidate.exists():
        return coord_candidate
    return primary_candidate


def primary_feature_dir_for_mission(repo_root: Path, mission_slug: str) -> Path:
    """Return the mission dir in the primary checkout, never a coordination worktree."""
    from specify_cli.missions._read_path_resolver import compose_meta_json_path

    return compose_meta_json_path(repo_root, mission_slug).parent


def resolve_feature_dir_for_slug(repo_root: Path, mission_slug: str) -> Path:
    """Resolve a mission directory **without** asserting it exists.

    This is the canonical, topology-aware, dir-only resolver for callers that
    already hold a mission slug and only need the read-side directory path —
    never raises on a missing directory (unlike
    :func:`resolve_feature_dir_for_mission`). It delegates to the single
    coord-aware path primitive (``resolve_mission_read_path``), so coordination
    topology is honoured exactly once.

    Late imports keep ``import specify_cli.missions.feature_dir_resolver`` from
    pulling in heavier modules during cold ``spec-kitty next`` startup.
    """
    from specify_cli.lanes.branch_naming import mid8_from_slug
    from specify_cli.missions._read_path_resolver import resolve_mission_read_path

    feature_dir: Path = resolve_mission_read_path(repo_root, mission_slug, mid8_from_slug(mission_slug))
    return feature_dir


def resolve_feature_dir_for_mission(
    repo_root: Path,
    mission_slug: str,
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Resolve a mission directory through ``resolve_action_context``."""
    from mission_runtime import resolve_action_context

    context = resolve_action_context(
        repo_root=repo_root,
        action="tasks",
        feature=mission_slug,
        cwd=cwd,
        env=env,
    )
    return Path(context.feature_dir)


__all__ = [
    "candidate_feature_dir_for_mission",
    "primary_feature_dir_for_mission",
    "resolve_feature_dir_for_slug",
    "resolve_feature_dir_for_mission",
]
