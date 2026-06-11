"""Feature directory resolver backed by the canonical action context.

C-004 / C-005 strangler note: ``candidate_feature_dir_for_mission`` no longer
carries its own coord-vs-primary logic. The canonical implementation lives in
:mod:`specify_cli.missions._read_path_resolver` (the ONE read primitive). This
module re-exports it so the 30+ historical import sites keep working unchanged
until each is converted to consume the resolved context directly (later WPs).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

# Re-export the canonical read primitive (C-005: one resolver). Folding the
# duplicate here into ``_read_path_resolver`` means a ``--mission <mid8>`` handle
# now resolves identically to the full slug for every caller (F-001/F-003/F-004).
from specify_cli.missions._read_path_resolver import (
    candidate_feature_dir_for_mission as candidate_feature_dir_for_mission,
)


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
