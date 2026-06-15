"""Artifact-home contract for mission runtime consumers.

This module is internal to :mod:`mission_runtime`; callers import the public
symbols from the package root.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

from mission_runtime.context import CommitTarget, CommitTargetKind
from specify_cli.core.constants import KITTY_SPECS_DIR

ArtifactSurface = Literal["primary", "placement"]


class MissionArtifactKind(enum.Enum):
    """Mission artifact categories whose home can differ by topology."""

    PRIMARY_METADATA = "primary_metadata"
    FINALIZED_EXECUTION_PLAN = "finalized_execution_plan"
    TASKS_INDEX = "tasks_index"
    WORK_PACKAGE_TASK = "work_package_task"
    LANE_STATE = "lane_state"
    ACCEPTANCE_MATRIX = "acceptance_matrix"
    ISSUE_MATRIX = "issue_matrix"
    STATUS_STATE = "status_state"
    ANALYSIS_REPORT = "analysis_report"


@dataclass(frozen=True)
class MissionArtifactHome:
    """Resolved read/write/commit home for one mission artifact kind."""

    kind: MissionArtifactKind
    read_surface: ArtifactSurface
    write_surface: ArtifactSurface
    commit_target: CommitTarget | None
    ignores_primary_coord_residue: bool

    @property
    def is_coordination_owned(self) -> bool:
        """True when stale primary copies should not block coord-topology flows."""
        return (
            self.ignores_primary_coord_residue
            and self.commit_target is not None
            and self.commit_target.kind is CommitTargetKind.COORDINATION
        )


_PLACEMENT_ARTIFACT_KINDS: frozenset[MissionArtifactKind] = frozenset(
    {
        MissionArtifactKind.FINALIZED_EXECUTION_PLAN,
        MissionArtifactKind.TASKS_INDEX,
        MissionArtifactKind.WORK_PACKAGE_TASK,
        MissionArtifactKind.LANE_STATE,
        MissionArtifactKind.ACCEPTANCE_MATRIX,
        MissionArtifactKind.ISSUE_MATRIX,
        MissionArtifactKind.STATUS_STATE,
        MissionArtifactKind.ANALYSIS_REPORT,
    }
)

_COORD_RESIDUE_FILENAMES: dict[str, MissionArtifactKind] = {
    "plan.md": MissionArtifactKind.FINALIZED_EXECUTION_PLAN,
    "tasks.md": MissionArtifactKind.TASKS_INDEX,
    "lanes.json": MissionArtifactKind.LANE_STATE,
    "acceptance-matrix.json": MissionArtifactKind.ACCEPTANCE_MATRIX,
    "issue-matrix.md": MissionArtifactKind.ISSUE_MATRIX,
    "status.events.jsonl": MissionArtifactKind.STATUS_STATE,
    "status.json": MissionArtifactKind.STATUS_STATE,
    "analysis-report.md": MissionArtifactKind.ANALYSIS_REPORT,
}

_COORD_RESIDUE_DIRS: dict[str, MissionArtifactKind] = {
    "tasks": MissionArtifactKind.WORK_PACKAGE_TASK,
}


def artifact_home_for(
    kind: MissionArtifactKind,
    placement_ref: CommitTarget,
) -> MissionArtifactHome:
    """Resolve the artifact-home contract for ``kind`` under ``placement_ref``."""
    if kind is MissionArtifactKind.PRIMARY_METADATA:
        return MissionArtifactHome(
            kind=kind,
            read_surface="primary",
            write_surface="primary",
            commit_target=None,
            ignores_primary_coord_residue=False,
        )

    if kind in _PLACEMENT_ARTIFACT_KINDS:
        return MissionArtifactHome(
            kind=kind,
            read_surface="placement",
            write_surface="placement",
            commit_target=placement_ref,
            ignores_primary_coord_residue=True,
        )

    raise ValueError(f"Unhandled mission artifact kind: {kind!r}")


def is_coordination_artifact_residue_path(
    path: str | Path,
    *,
    mission_slug: str | None = None,
) -> bool:
    """Return True for primary-checkout residue owned by a coord placement.

    The predicate is intentionally path-specific: finalized planning/status
    artifacts are ignored under coordination topology, but ``spec.md`` and
    unknown mission files still block dirty-tree gates.
    """
    artifact_kind = _artifact_kind_for_path(path, mission_slug=mission_slug)
    if artifact_kind is None:
        return False
    coord_ref = CommitTarget(ref="", kind=CommitTargetKind.COORDINATION)
    return artifact_home_for(artifact_kind, coord_ref).is_coordination_owned


def _artifact_kind_for_path(
    path: str | Path,
    *,
    mission_slug: str | None,
) -> MissionArtifactKind | None:
    normalized = str(path).replace("\\", "/").rstrip("/")
    parts = PurePosixPath(normalized).parts
    try:
        specs_index = parts.index(KITTY_SPECS_DIR)
    except ValueError:
        return None

    mission_index = specs_index + 1
    rel_index = mission_index + 1
    if rel_index >= len(parts):
        return None

    path_mission_slug = parts[mission_index]
    if mission_slug is not None and path_mission_slug != mission_slug:
        return None

    mission_rel_parts = parts[rel_index:]
    if len(mission_rel_parts) == 1:
        name = mission_rel_parts[0]
        return _COORD_RESIDUE_FILENAMES.get(name) or _COORD_RESIDUE_DIRS.get(name)

    return _COORD_RESIDUE_DIRS.get(mission_rel_parts[0])
