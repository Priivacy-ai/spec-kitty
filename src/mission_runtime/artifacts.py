"""Artifact-home contract for mission runtime consumers.

This module is internal to :mod:`mission_runtime`; callers import the public
symbols from the package root.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from mission_runtime.context import (
    CommitTarget,
    MissionTopology,
    routes_through_coordination,
)
from specify_cli.core.constants import KITTY_SPECS_DIR


class Surface(enum.StrEnum):
    """The two placement surfaces a mission artifact kind resolves to (S1192).

    Placement-seam campsite (coord-primary-partition-lock WP01): the
    ``"primary"`` / ``"placement"`` literals used to be restated at each
    :func:`artifact_home_for` return arm; this hoists them to one named constant.
    The ``str`` mixin keeps every pre-existing ``== "primary"`` /
    ``== "placement"`` comparison (production and the pinned partition tests)
    working unchanged — a literal-to-constant hoist, not a behavior or wire-shape
    change (C-002).
    """

    PRIMARY = "primary"
    PLACEMENT = "placement"


# Back-compat type alias: historical name for the surface type. ``Surface`` is
# the named constant this campsite hoists to; the alias keeps any external type
# annotation referencing the old name valid (no behavior implication).
ArtifactSurface = Surface


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
    # write-surface-coherence WP01-04: these are PRIMARY-partition kinds (members
    # of ``_PRIMARY_ARTIFACT_KINDS``). They live with their mission on the primary
    # ``target_branch`` for EVERY topology and NEVER transit the coordination
    # branch, so a stale primary copy is a REAL dirty-tree blocker — not residue.
    SPEC = "spec"
    DATA_MODEL = "data_model"
    RESEARCH = "research"
    CHECKLIST = "checklist"
    # Terminal PRIMARY-partition artifact (FR-002): the post-merge retrospective
    # (``retrospective.yaml``) lives with its mission in the durable
    # ``kitty-specs/<slug>/`` home for EVERY topology and never transits the
    # coordination branch.
    RETROSPECTIVE = "retrospective"


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


# FR-004 / data-model.md "The swappable locus (NFR-004)": the single partition
# whose membership routes a kind to the PRIMARY ``target_branch`` for every
# topology shape (read AND write — INV-5 full symmetry). Planning + identity
# artifacts (specify/plan/tasks/finalize/lanes/meta) live with their mission on
# the primary surface; flipping a kind across the two sets is a one-line move,
# never a code change (NFR-004).
_PRIMARY_ARTIFACT_KINDS: frozenset[MissionArtifactKind] = frozenset(
    {
        MissionArtifactKind.SPEC,
        MissionArtifactKind.DATA_MODEL,
        MissionArtifactKind.RESEARCH,
        MissionArtifactKind.CHECKLIST,
        MissionArtifactKind.FINALIZED_EXECUTION_PLAN,
        MissionArtifactKind.TASKS_INDEX,
        MissionArtifactKind.WORK_PACKAGE_TASK,
        # LANE_STATE (lanes.json, finalize output) travels with tasks.md → PRIMARY.
        MissionArtifactKind.LANE_STATE,
        MissionArtifactKind.PRIMARY_METADATA,
        # FR-002: the post-merge retrospective is a terminal PRIMARY-partition
        # artifact — it resolves to the durable mission home for every topology.
        MissionArtifactKind.RETROSPECTIVE,
    }
)

# FR-004: the COORD partition — coordination-owned artifacts that route to the
# coordination branch under coordination topology and whose stale primary copies
# are coordination residue. ACCEPTANCE_MATRIX (accept-time verification) and
# ANALYSIS_REPORT (record-analysis) stay COORD per data-model.md.
_PLACEMENT_ARTIFACT_KINDS: frozenset[MissionArtifactKind] = frozenset(
    {
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
    "spec.md": MissionArtifactKind.SPEC,
    "data-model.md": MissionArtifactKind.DATA_MODEL,
    "research.md": MissionArtifactKind.RESEARCH,
    "retrospective.yaml": MissionArtifactKind.RETROSPECTIVE,
}

_COORD_RESIDUE_DIRS: dict[str, MissionArtifactKind] = {
    "tasks": MissionArtifactKind.WORK_PACKAGE_TASK,
    "checklists": MissionArtifactKind.CHECKLIST,
}

# FR-003 (#2102) / data-model.md "Self-bookkeeping allowlist" / contract G-5:
# spec-kitty's OWN bookkeeping files. These classify ``kind=None`` against the
# mission-artifact partition above, so the record-analysis dirty-tree preflight
# used to treat their churn as "real dirt" and FALSELY block the write. This set
# is DISJOINT from the coord-residue partition (``_COORD_RESIDUE_FILENAMES`` /
# ``_PLACEMENT_ARTIFACT_KINDS``) and from the planning kinds: it contains ONLY
# spec-kitty's own metadata, NEVER a planning artifact. The G-5 invariant — a
# stale primary ``spec.md`` remains non-allowlisted "real dirt" — holds precisely
# because ``spec.md`` is a planning kind and is NOT a member here.
#
# ``meta.json`` matches by bare filename (it can live under any mission dir).
# ``global.jsonl`` is matched by its FULL relative path SUFFIX so an unrelated
# ``global.jsonl`` elsewhere is not over-allowlisted (FR-003 over-allowlist hazard).
_SELF_BOOKKEEPING_FILENAMES: frozenset[str] = frozenset({"meta.json"})
_SELF_BOOKKEEPING_SUFFIXES: tuple[str, ...] = (
    ".kittify/encoding-provenance/global.jsonl",
)

# FR-001 (#2251): ``kitty-ops/<ULID>.jsonl`` Op-record orphans are spec-kitty's
# own invocation audit trail — NOT mission planning artifacts.  A stale record
# left from a previous ``spec-kitty dispatch`` session must not block dirty-tree
# gates.  The match is TIGHT: exactly ``kitty-ops/`` segment + 26-char Crockford
# base32 ULID + ``.jsonl``.  A non-ULID basename (e.g. ``notes.txt``) is NOT
# matched — it remains real dirt (G-5 invariant).  Note: ``ops-index.jsonl``
# is a non-ULID basename too, but as of #2341 it is a gitignored LOCAL_RUNTIME
# cache (``op_invocation_index`` surface), so it never reaches this classifier
# in a correctly-migrated project — it is not "real dirt" here.
# Crockford base32 alphabet: digits 0–9 plus uppercase A–Z MINUS I, L, O, U.
_KITTY_OPS_OP_RECORD_RE: re.Pattern[str] = re.compile(
    r"(?:^|/)kitty-ops/[0-9A-HJKMNP-TV-Z]{26}\.jsonl$"
)


def artifact_home_for(
    kind: MissionArtifactKind,
    placement_ref: CommitTarget,
) -> MissionArtifactHome:
    """Resolve the artifact-home contract for ``kind`` under ``placement_ref``."""
    if kind is MissionArtifactKind.PRIMARY_METADATA:
        return MissionArtifactHome(
            kind=kind,
            read_surface=Surface.PRIMARY,
            write_surface=Surface.PRIMARY,
            commit_target=None,
            ignores_primary_coord_residue=False,
        )

    # FR-002 / FR-004: planning + identity kinds resolve to the PRIMARY surface.
    # This arm runs AFTER the read-anchored ``PRIMARY_METADATA`` arm above (which
    # is also a ``_PRIMARY_ARTIFACT_KINDS`` member) so metadata keeps its
    # never-committed-through-a-ref ``commit_target=None`` contract; the primary
    # planning kinds DO carry the resolved primary ``placement_ref`` as their
    # commit target. The returned shape is unchanged (NFR-004 / G-5).
    if kind in _PRIMARY_ARTIFACT_KINDS:
        return MissionArtifactHome(
            kind=kind,
            read_surface=Surface.PRIMARY,
            write_surface=Surface.PRIMARY,
            commit_target=placement_ref,
            ignores_primary_coord_residue=False,
        )

    if kind in _PLACEMENT_ARTIFACT_KINDS:
        return MissionArtifactHome(
            kind=kind,
            read_surface=Surface.PLACEMENT,
            write_surface=Surface.PLACEMENT,
            commit_target=placement_ref,
            ignores_primary_coord_residue=True,
        )

    raise ValueError(f"Unhandled mission artifact kind: {kind!r}")


def assert_partition_invariant() -> None:
    """Guard P-1: the partition frozensets are disjoint AND jointly exhaustive.

    ``_PRIMARY_ARTIFACT_KINDS`` and ``_PLACEMENT_ARTIFACT_KINDS`` must never
    overlap (no kind double-classified) and their union must cover every
    :class:`MissionArtifactKind` member (no kind left unclassified) —
    data-model.md Invariant P-1. The placement seam (T002,
    coord-primary-partition-lock WP01) asserts this at construction so a future
    kind added to the enum without a partition entry fails LOUD at the seam
    boundary rather than surfacing as a deep ``ValueError: Unhandled mission
    artifact kind`` inside :func:`artifact_home_for`.

    Raises:
        AssertionError: When the partition is not disjoint-and-total.
    """
    overlap = _PRIMARY_ARTIFACT_KINDS & _PLACEMENT_ARTIFACT_KINDS
    if overlap:
        raise AssertionError(
            "P-1 violated: kind(s) classified in BOTH partitions: "
            f"{sorted(kind.value for kind in overlap)}"
        )
    covered = _PRIMARY_ARTIFACT_KINDS | _PLACEMENT_ARTIFACT_KINDS
    all_kinds = frozenset(MissionArtifactKind)
    if covered != all_kinds:
        missing = all_kinds - covered
        raise AssertionError(
            "P-1 violated: kind(s) classified in NEITHER partition: "
            f"{sorted(kind.value for kind in missing)}"
        )


def is_coordination_artifact_residue_path(
    path: str | Path,
    *,
    mission_slug: str | None = None,
) -> bool:
    """Return True for primary-checkout residue owned by a coord placement.

    The predicate is path-specific and partition-aware (write-surface-coherence
    WP01-04): only COORD-partition artifacts (the append-only status log/snapshot,
    ``acceptance-matrix.json`` / ``issue-matrix.md`` / ``analysis-report.md``) are
    committed to the coordination branch under coordination topology, so ONLY
    their stale primary copies are ignored. Planning SOURCE + finalized + identity
    docs (``spec.md`` / ``plan.md`` / ``tasks.md`` / ``tasks/WP*.md`` /
    ``data-model.md`` / ``research.md`` / ``checklists/`` / ``lanes.json``) are now
    PRIMARY-partition kinds that live on ``target_branch`` — their stale primary
    copies are REAL dirt, NOT residue. Unknown mission files and another mission's
    artifacts still block dirty-tree gates.
    """
    artifact_kind = _artifact_kind_for_path(path, mission_slug=mission_slug)
    if artifact_kind is None:
        return False
    # #2090-clean: derive coord-routing from the STORED topology via the SINGLE
    # routing predicate, NOT a fabricated ``CommitTarget(kind=COORDINATION)`` shim.
    # This predicate is the coordination-residue question, so it projects the
    # ``COORD`` topology cell; the coord-less cells return False (no residue).
    return kind_is_coordination_residue(artifact_kind, MissionTopology.COORD)


def is_primary_artifact_kind(kind: MissionArtifactKind) -> bool:
    """Return True if ``kind`` is a PRIMARY-partition kind (lands on target_branch).

    The public predicate over the swappable partition
    (:data:`_PRIMARY_ARTIFACT_KINDS`, NFR-004): a primary kind (planning + identity
    artifacts) resolves to the primary ``target_branch`` for every topology and
    NEVER transits coordination. Consumers outside ``mission_runtime`` query the
    partition through this package-root predicate rather than importing the
    private set (shared-package-boundary).
    """
    return kind in _PRIMARY_ARTIFACT_KINDS


def kind_for_mission_file(
    path: str | Path,
    *,
    mission_slug: str | None = None,
) -> MissionArtifactKind | None:
    """Classify a ``kitty-specs/<slug>/`` file path to its :class:`MissionArtifactKind`.

    The ONE public file→kind classification authority (write-surface-coherence
    WP03 / NFR-004). Write-side callers that hold a *path* (the ``safe-commit``
    command, ``append-history``) consume this helper so the kind partition is
    derived from a single classifier instead of re-deriving it per call site.

    Returns the kind for a recognised mission artifact (``spec.md`` → ``SPEC``,
    ``tasks/WP*.md`` → ``WORK_PACKAGE_TASK``, ``status.events.jsonl`` →
    ``STATUS_STATE``, …) and ``None`` for an unrecognised path or another
    mission's artifact (when ``mission_slug`` is supplied). The returned kind's
    partition membership (:data:`_PRIMARY_ARTIFACT_KINDS`) then selects the
    primary vs topology-routed placement via :func:`resolve_placement_only`.
    """
    return _artifact_kind_for_path(path, mission_slug=mission_slug)


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


def is_self_bookkeeping_path(path: str | Path) -> bool:
    """Return True for spec-kitty's OWN bookkeeping files (FR-003 allowlist).

    The self-bookkeeping allowlist authority (#2102 / data-model.md / contract
    G-5): ``meta.json`` (mission identity metadata), the encoding-provenance
    ``.kittify/encoding-provenance/global.jsonl``, and ``kitty-ops/<ULID>.jsonl``
    Op-record orphans (#2251) are spec-kitty's own bookkeeping, not mission
    planning artifacts. The record-analysis dirty-tree preflight consults this
    predicate to drop their churn from the dirty set so it stops falsely blocking
    — regardless of topology (these are not coord residue).

    This allowlist is DISJOINT from the coord-residue partition and from the
    planning kinds: a stale primary ``spec.md`` is a PRIMARY-partition planning
    artifact, is NOT a member here, and therefore remains "real dirt" that blocks
    (the G-5 invariant). ``meta.json`` matches by bare filename; ``global.jsonl``
    matches by full relative-path SUFFIX; ``kitty-ops/<ULID>.jsonl`` matches by
    the tight ``_KITTY_OPS_OP_RECORD_RE`` pattern (26-char Crockford ULID only —
    a non-ULID ``kitty-ops/notes.txt`` is NOT matched and therefore still blocks).

    This is the SINGLE authority for all four dirty-tree gates (accept, merge,
    review, record-analysis).  See #1914 (no-op-stable gates) for the umbrella
    framing — the full no-op-stable rework is out of scope here.
    """
    normalized = str(path).replace("\\", "/").rstrip("/")
    if PurePosixPath(normalized).name in _SELF_BOOKKEEPING_FILENAMES:
        return True
    if any(normalized.endswith(suffix) for suffix in _SELF_BOOKKEEPING_SUFFIXES):
        return True
    return bool(_KITTY_OPS_OP_RECORD_RE.search(normalized))
