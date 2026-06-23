"""Artifact-home contract for mission runtime consumers.

This module is internal to :mod:`mission_runtime`; callers import the public
symbols from the package root.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

from mission_runtime.context import (
    CommitTarget,
    MissionTopology,
    routes_through_coordination,
)
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
    # Planning SOURCE docs (/spec-kitty.specify + /spec-kitty.plan outputs).
    # Under coordination topology these are committed to the coordination branch
    # exactly like the finalized artifacts above, so a stale primary copy is
    # coordination residue (not a dirty-tree blocker).
    SPEC = "spec"
    DATA_MODEL = "data_model"
    RESEARCH = "research"
    CHECKLIST = "checklist"


@dataclass(frozen=True)
class MissionArtifactHome:
    """Resolved read/write/commit home for one mission artifact kind."""

    kind: MissionArtifactKind
    read_surface: ArtifactSurface
    write_surface: ArtifactSurface
    commit_target: CommitTarget | None
    ignores_primary_coord_residue: bool


def kind_is_coordination_residue(
    kind: MissionArtifactKind,
    topology: MissionTopology,
) -> bool:
    """Is ``kind`` coordination residue under ``topology`` (stored-topology projection)?

    The #2090-clean residue authority: coord-routing is derived from the **stored**
    :class:`MissionTopology` via the SINGLE :func:`routes_through_coordination`
    predicate over ``COORD`` / ``LANES_WITH_COORD`` — NEVER from a fabricated
    ``CommitTarget`` ``.kind`` shim. A placement-kind artifact whose home ignores
    primary residue is residue iff the mission routes through coordination; the two
    coord-less cells (``SINGLE_BRANCH`` / ``LANES``) have no primary↔coordination
    split, so nothing is residue there (the flat→False cell). The placement ref the
    home carries is irrelevant to the routing decision — only the kind's
    ``ignores_primary_coord_residue`` classification and the stored topology matter.
    """
    if not routes_through_coordination(topology):
        return False
    return kind in _PLACEMENT_ARTIFACT_KINDS


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
        MissionArtifactKind.SPEC,
        MissionArtifactKind.DATA_MODEL,
        MissionArtifactKind.RESEARCH,
        MissionArtifactKind.CHECKLIST,
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
    "spec.md": MissionArtifactKind.SPEC,
    "data-model.md": MissionArtifactKind.DATA_MODEL,
    "research.md": MissionArtifactKind.RESEARCH,
}

_COORD_RESIDUE_DIRS: dict[str, MissionArtifactKind] = {
    "tasks": MissionArtifactKind.WORK_PACKAGE_TASK,
    "checklists": MissionArtifactKind.CHECKLIST,
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

    The predicate is path-specific: planning SOURCE docs (``spec.md`` /
    ``data-model.md`` / ``research.md`` / ``checklists/``) and finalized
    planning/status artifacts are all committed to the coordination branch under
    coordination topology, so their stale primary copies are ignored. Unknown
    mission files and another mission's artifacts still block dirty-tree gates.
    """
    artifact_kind = _artifact_kind_for_path(path, mission_slug=mission_slug)
    if artifact_kind is None:
        return False
    # #2090-clean: derive coord-routing from the STORED topology via the SINGLE
    # routing predicate, NOT a fabricated ``CommitTarget(kind=COORDINATION)`` shim.
    # This predicate is the coordination-residue question, so it projects the
    # ``COORD`` topology cell; the coord-less cells return False (no residue).
    return kind_is_coordination_residue(artifact_kind, MissionTopology.COORD)


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
