"""``mission_runtime`` — the canonical execution-state surface.

This umbrella package is the single, screaming home for execution-state
resolution: given a mission (and optional work package), it produces a fully
resolved, CWD-invariant :class:`MissionExecutionContext`. Consumers import **only** from
this package root; internal submodules (``context``, ``resolution``) are
import-forbidden from outside the package and enforced by
``tests/architectural/test_mission_runtime_surface.py`` (FR-005).

The public API is expressed over context objects, never over path fragments —
callers receive a resolved context and never reconstruct the mission-spec
directory from ``main_repo_root`` + the specs dir name + ``mission_slug``
themselves (FR-009).

WP02 stood up the package empty-but-registered (lean ``__all__`` over stub
symbols + layer-guard registration); WP03 relocated the hardened resolver here
and removed the old ``specify_cli.core.execution_context`` module outright (all
callers were migrated to this package root). A few historical command-oriented
names remain as compatibility attributes for first-party callers, but they are
not part of the public ``__all__`` surface.

See ADR ``docs/adr/3.x/2026-06-07-1-execution-state-canonical-surface.md``.
"""
from __future__ import annotations

from typing import Any

from mission_runtime.context import (
    ArtifactPlacementFragment,
    BranchRefFragment,
    CommitTarget,
    ExecutionMode,
    IdentityFragment,
    MissionArtifactContext,
    MissionContext,
    MissionExecutionContext,
    MissionTopology,
    StatusSurfaceFragment,
    WorkspaceFragment,
    classify_topology,
    routes_through_coordination,
)
from mission_runtime.artifacts import (
    MissionArtifactHome,
    MissionArtifactKind,
    TopologySurface,
    artifact_home_for,
    is_primary_artifact_kind,
    kind_for_mission_file,
    kind_is_coordination_residue,
)
from mission_runtime.identity import mid8_from_slug, resolve_mid8
from mission_runtime.resolution import (
    ActionContextError,
    PlacementSeam,
    ResolvedSurface,
    SurfaceLocations,
    coord_read_dir_for,
    mission_context_for,
    placement_seam,
    resolve_action_context,
    resolve_artifact_surface,
    resolve_placement_only,
    resolve_topology,
    translate_surface,
)
from mission_runtime.mission_resolver_port import MissionResolver

__all__ = [
    "ActionContextError",
    "ArtifactPlacementFragment",
    "BranchRefFragment",
    "CommitTarget",
    "ExecutionMode",
    "IdentityFragment",
    "MissionArtifactContext",
    "MissionArtifactHome",
    "MissionArtifactKind",
    "MissionContext",
    "MissionExecutionContext",
    "MissionResolver",
    "MissionTopology",
    "PlacementSeam",
    "ResolvedSurface",
    "StatusSurfaceFragment",
    "SurfaceLocations",
    "TopologySurface",
    "WorkspaceFragment",
    "artifact_home_for",
    "classify_topology",
    "coord_read_dir_for",
    "is_primary_artifact_kind",
    "kind_for_mission_file",
    "kind_is_coordination_residue",
    "mid8_from_slug",
    "mission_context_for",
    "placement_seam",
    "resolve_action_context",
    "resolve_artifact_surface",
    "resolve_mid8",
    "resolve_placement_only",
    "resolve_topology",
    "routes_through_coordination",
    "translate_surface",
]

_COMPAT_ATTRS = frozenset(
    {
        "ActionContext",
        "ActionName",
        "ACTION_NAMES",
        "_resolve_mission_slug",
    }
)


def __getattr__(name: str) -> Any:
    """Resolve historical first-party names without widening ``__all__``."""
    if name not in _COMPAT_ATTRS:
        raise AttributeError(name)
    if name == "ActionContext":
        from mission_runtime.context import ActionContext

        return ActionContext
    from mission_runtime import resolution

    return getattr(resolution, name)
