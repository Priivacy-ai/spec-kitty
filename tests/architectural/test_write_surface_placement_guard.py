"""Behavioral two-ref write-surface placement guard (write-surface-coherence WP07 / T027).

The mission's headline invariant, asserted BEHAVIORALLY (not structurally) against a
REAL coordination-topology fixture, across EVERY converged write path. The bifurcation:

* PRIMARY-partition kinds (``SPEC`` / ``DATA_MODEL`` / ``RESEARCH`` / ``CHECKLIST`` /
  ``FINALIZED_EXECUTION_PLAN`` / ``TASKS_INDEX`` / ``WORK_PACKAGE_TASK`` /
  ``LANE_STATE`` / ``PRIMARY_METADATA``) resolve to the primary ``target_branch``
  for EVERY topology and NEVER transit coordination.
* COORD-partition kinds (``STATUS_STATE`` / ``ISSUE_MATRIX`` / ``ACCEPTANCE_MATRIX`` /
  ``ANALYSIS_REPORT``) keep the topology-routed coordination ref under coord topology.

Non-vacuity (research D-7 / NFR-002):

* The guard drives the **REAL resolver** (``resolve_placement_only`` /
  ``resolve_topology``) against the real coord-topology fixture — it does NOT stub
  either, unlike ``tests/coordination/test_commit_router.py`` (which stubs both and
  proves nothing about the partition). It exercises the assertion across THREE
  converged write paths: ``commit_for_mission``, the ``safe-commit`` bypass writer
  (``_resolve_commit_target``), and ``_planning_commit_worktree``.
* A MANDATORY anti-mutant negative test forces the PRE-fix partition (puts ``SPEC``
  back into ``_PLACEMENT_ARTIFACT_KINDS``) and asserts the planning-ref assertion
  goes RED — killing the "always-coord-for-coord-topology" mutant. Without it the
  two-ref guard could pass vacuously.

Fixture realism (mandatory): a real 26-char ULID ``mission_id``, real 8-char
``mid8``, a real ``<slug>-<mid8>`` mission dir, a real ``coordination_branch``, and
a NON-protected feature ``target_branch``.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pytest
from ulid import ULID

import mission_runtime.artifacts as artifacts_mod
import mission_runtime.resolution as resolution_mod
from mission_runtime import (
    MissionArtifactKind,
    resolve_placement_only,
    resolve_topology,
    routes_through_coordination,
)

pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]

# Production-shaped identity: a real 26-char ULID + its derived 8-char mid8. The
# on-disk slug carries the mid8 tail (post-WP03 grammar), and ``target_branch`` is
# a NON-protected feature branch so a PRIMARY-kind commit lands cleanly there.
_TARGET_BRANCH = "feat/write-surface-coherence"


@dataclass(frozen=True)
class _CoordMission:
    """A real on-disk coordination-topology mission fixture."""

    repo_root: Path
    mission_slug: str
    feature_dir: Path
    coordination_branch: str
    target_branch: str


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _build_coord_mission(tmp_path: Path) -> _CoordMission:
    """Build a real coord-topology mission whose ``target_branch`` is non-protected.

    The mission stores ``coordination_branch`` + ``topology: coord`` so the REAL
    resolver classifies it COORD (``routes_through_coordination`` is True), and a
    non-protected ``target_branch`` that is HEAD so PRIMARY-kind commits land there.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", _TARGET_BRANCH)
    _git(repo, "config", "user.email", "guard@example.com")
    _git(repo, "config", "user.name", "Guard Suite")
    (repo / ".kittify").mkdir()
    (repo / ".kittify" / "config.yaml").write_text("project: guard-suite\n", encoding="utf-8")

    mission_id = str(ULID())
    mid8 = mission_id[:8].lower()
    slug = f"write-surface-guard-{mid8}"
    coordination_branch = f"kitty/mission-{slug}"

    feature_dir = repo / "kitty-specs" / slug
    (feature_dir / "tasks").mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": mission_id,
                "mid8": mid8,
                "mission_slug": slug,
                "target_branch": _TARGET_BRANCH,
                "coordination_branch": coordination_branch,
                "topology": "coord",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    # A PRIMARY-kind artifact (spec.md) and a COORD-kind artifact (status log).
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "status.events.jsonl").write_text("{}\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed coord mission")
    _git(repo, "branch", coordination_branch)

    return _CoordMission(
        repo_root=repo.resolve(),
        mission_slug=slug,
        feature_dir=feature_dir,
        coordination_branch=coordination_branch,
        target_branch=_TARGET_BRANCH,
    )


@pytest.fixture
def coord_mission(tmp_path: Path) -> _CoordMission:
    mission = _build_coord_mission(tmp_path)
    # Precondition: the REAL resolver classifies this fixture as coord-routing.
    # Without this the two-ref guard is exercising the wrong topology cell.
    assert routes_through_coordination(
        resolve_topology(mission.repo_root, mission.mission_slug)
    ), "fixture precondition violated: mission must route through coordination"
    return mission


# ---------------------------------------------------------------------------
# The two-ref behavioral assertion, parametrized across three write paths.
# ---------------------------------------------------------------------------

# A representative PRIMARY-partition kind and COORD-partition kind. The full
# partition is asserted in ``test_full_partition_resolves_per_membership`` below.
_PRIMARY_KIND = MissionArtifactKind.SPEC
_COORD_KIND = MissionArtifactKind.STATUS_STATE


def _path_commit_for_mission(mission: _CoordMission) -> tuple[str, str]:
    """Write path 1: ``commit_for_mission`` — drives the real resolver internally.

    Returns the (primary_ref, coord_ref) the router lands/resolves each kind on.
    The PRIMARY-kind commit is exercised end-to-end (it must really land on the
    target branch); the COORD-kind commit's resolved placement ref is the
    discriminating signal that it routes to coordination, not the primary.
    """
    from specify_cli.coordination.commit_router import commit_for_mission
    from specify_cli.git.protection_policy import ProtectionPolicy

    policy = ProtectionPolicy(
        protected_branches=frozenset({"main", "master"}), operator_hatch_active=False
    )

    # PRIMARY kind: actually mutate + commit; assert it lands on the target branch.
    spec_path = mission.feature_dir / "spec.md"
    spec_path.write_text("# Spec edited by guard\n", encoding="utf-8")
    primary_result = commit_for_mission(
        mission.repo_root,
        mission.mission_slug,
        (spec_path,),
        "guard: primary kind",
        policy,
        kind=_PRIMARY_KIND,
    )
    assert primary_result.status == "committed", primary_result.diagnostic

    # COORD kind: the resolved placement ref is the routing signal (coord worktree
    # materialisation plumbing is covered by tests/coordination/test_commit_router).
    status_path = mission.feature_dir / "status.events.jsonl"
    status_path.write_text('{"edited": true}\n', encoding="utf-8")
    coord_result = commit_for_mission(
        mission.repo_root,
        mission.mission_slug,
        (status_path,),
        "guard: coord kind",
        policy,
        kind=_COORD_KIND,
    )
    return primary_result.placement_ref, coord_result.placement_ref


def _path_safe_commit_bypass(mission: _CoordMission) -> tuple[str, str]:
    """Write path 2: the ``safe-commit`` bypass writer (``_resolve_commit_target``).

    A planning artifact path (``spec.md``) resolves to the primary target branch;
    a status file path (``status.events.jsonl``) resolves to the coordination ref.
    Drives the real ``resolve_placement_only`` through the CLI's single destination
    resolver — no stub.
    """
    from specify_cli.cli.commands.safe_commit_cmd import _resolve_commit_target

    primary = _resolve_commit_target(
        explicit_to_branch=None,
        repo_root=mission.repo_root,
        files=[mission.feature_dir / "spec.md"],
    )
    coord = _resolve_commit_target(
        explicit_to_branch=None,
        repo_root=mission.repo_root,
        files=[mission.feature_dir / "status.events.jsonl"],
    )
    return primary.ref, coord.ref


def _path_planning_commit_worktree(mission: _CoordMission) -> tuple[str, str]:
    """Write path 3: ``_planning_commit_worktree`` — drives the real resolver.

    A PRIMARY kind returns ``(repo_root, paths)`` (no coord transit). A COORD kind
    routes through coordination — its resolved placement ref (read from the same
    real resolver) is the discriminating signal. We report each path's resolved
    ref by composing the worktree behaviour with the real resolver.
    """
    from specify_cli.cli.commands.agent.mission import _planning_commit_worktree

    spec_path = mission.feature_dir / "spec.md"
    primary_wt, primary_paths = _planning_commit_worktree(
        mission.repo_root, mission.mission_slug, (spec_path,), kind=_PRIMARY_KIND
    )
    # PRIMARY kind never transits coordination: it commits directly from the
    # primary checkout, so the resolved ref is the primary target branch.
    assert primary_wt == mission.repo_root, (
        "PRIMARY kind transited a non-primary worktree (planning→coord route "
        "was not removed)"
    )
    assert primary_paths == (spec_path,)
    primary_ref = resolve_placement_only(
        mission.repo_root, mission.mission_slug, kind=_PRIMARY_KIND
    ).ref

    # COORD kind routes through coordination — its placement ref is the coord ref.
    coord_ref = resolve_placement_only(
        mission.repo_root, mission.mission_slug, kind=_COORD_KIND
    ).ref
    return primary_ref, coord_ref


def _path_workflow_placement_wrapper(mission: _CoordMission) -> tuple[str, str]:
    """Write path 4 (coord-primary-partition-lock WP07 / T033 / T035):
    workflow.py's ``_resolve_workflow_placement`` thin wrapper.

    T033's new checkout-grammar ratchet (``test_no_write_side_rederivation.py``)
    trusts ``_resolve_workflow_placement`` as a sanctioned seam-fold callee
    (a caller assigning from it is treated as seam-derived, not a checkout
    read) WITHOUT re-deriving the placement inline at each of workflow.py's
    write sites. This drives the REAL wrapper (not a stub) against the real
    coord fixture for a representative PRIMARY kind (``WORK_PACKAGE_TASK`` --
    the kind workflow.py actually calls it with for baseline-test capture) and
    the COORD kind (``STATUS_STATE``), proving T033's static "this callee is
    seam-derived" assumption holds behaviorally, not just by AST inspection.
    """
    from specify_cli.cli.commands.agent.workflow import _resolve_workflow_placement

    primary = _resolve_workflow_placement(
        repo_root=mission.repo_root,
        mission_slug=mission.mission_slug,
        kind=MissionArtifactKind.WORK_PACKAGE_TASK,
    )
    coord = _resolve_workflow_placement(
        repo_root=mission.repo_root,
        mission_slug=mission.mission_slug,
        kind=_COORD_KIND,
    )
    return primary.ref, coord.ref


_WRITE_PATHS = {
    "commit_for_mission": _path_commit_for_mission,
    "safe_commit_bypass": _path_safe_commit_bypass,
    "planning_commit_worktree": _path_planning_commit_worktree,
    "workflow_placement_wrapper": _path_workflow_placement_wrapper,
}


@pytest.mark.parametrize("path_name", sorted(_WRITE_PATHS))
def test_two_ref_partition_per_write_path(
    coord_mission: _CoordMission, path_name: str
) -> None:
    """NFR-002 two-ref guard: each converged write path lands the PRIMARY kind on
    the primary ``target_branch`` AND the COORD kind on the ``coordination_branch``.

    A single regression on ANY of the three paths fails its parametrization. The
    real resolver is driven against the real coord fixture — no
    ``resolve_topology`` / ``resolve_placement_only`` stub (D-7).
    """
    resolve_path = _WRITE_PATHS[path_name]
    primary_ref, coord_ref = resolve_path(coord_mission)

    assert primary_ref == coord_mission.target_branch, (
        f"[{path_name}] PRIMARY kind {_PRIMARY_KIND.name} did NOT resolve to the "
        f"primary target branch {coord_mission.target_branch!r}; got {primary_ref!r}"
    )
    assert coord_ref == coord_mission.coordination_branch, (
        f"[{path_name}] COORD kind {_COORD_KIND.name} did NOT resolve to the "
        f"coordination branch {coord_mission.coordination_branch!r}; got {coord_ref!r}"
    )
    # The two refs must DIFFER — a configuration where they collapse to one ref
    # would let a vacuous guard pass.
    assert primary_ref != coord_ref


def test_full_partition_resolves_per_membership(coord_mission: _CoordMission) -> None:
    """Every PRIMARY-partition kind → target_branch; every COORD-partition kind → coord.

    Drives the REAL resolver for the whole partition so a single mis-classified
    kind fails. ``PRIMARY_METADATA`` resolves to the primary surface too (its
    placement is the never-committed-through-a-ref metadata home, asserted via
    ``is_primary_artifact_kind`` rather than a ref equality).
    """
    from mission_runtime import is_primary_artifact_kind

    primary_kinds = {
        MissionArtifactKind.SPEC,
        MissionArtifactKind.DATA_MODEL,
        MissionArtifactKind.RESEARCH,
        MissionArtifactKind.CHECKLIST,
        MissionArtifactKind.FINALIZED_EXECUTION_PLAN,
        MissionArtifactKind.TASKS_INDEX,
        MissionArtifactKind.WORK_PACKAGE_TASK,
        MissionArtifactKind.LANE_STATE,
        MissionArtifactKind.PRIMARY_METADATA,
        MissionArtifactKind.RETROSPECTIVE,
    }
    coord_kinds = {
        MissionArtifactKind.STATUS_STATE,
        MissionArtifactKind.ISSUE_MATRIX,
        MissionArtifactKind.ACCEPTANCE_MATRIX,
        MissionArtifactKind.ANALYSIS_REPORT,
    }
    # Sanity: the two sets partition the whole enum exactly once.
    assert primary_kinds | coord_kinds == set(MissionArtifactKind)
    assert primary_kinds.isdisjoint(coord_kinds)

    for kind in primary_kinds:
        assert is_primary_artifact_kind(kind), kind
        ref = resolve_placement_only(
            coord_mission.repo_root, coord_mission.mission_slug, kind=kind
        ).ref
        assert ref == coord_mission.target_branch, (
            f"PRIMARY kind {kind.name} resolved to {ref!r}, not the target branch"
        )

    for kind in coord_kinds:
        assert not is_primary_artifact_kind(kind), kind
        ref = resolve_placement_only(
            coord_mission.repo_root, coord_mission.mission_slug, kind=kind
        ).ref
        assert ref == coord_mission.coordination_branch, (
            f"COORD kind {kind.name} resolved to {ref!r}, not the coordination branch"
        )


# ---------------------------------------------------------------------------
# MANDATORY anti-mutant negative test (D-7 / DECISION 7).
# ---------------------------------------------------------------------------


def _patch_partition(
    monkeypatch: pytest.MonkeyPatch,
    *,
    primary: frozenset[MissionArtifactKind],
    placement: frozenset[MissionArtifactKind],
) -> None:
    """Patch the live partition frozensets to ``(primary, placement)``.

    ``resolution.py`` imports ``_PRIMARY_ARTIFACT_KINDS`` by reference, so the
    ``artifacts`` AND ``resolution`` module-level bindings are patched together
    (via ``monkeypatch`` so they auto-restore) to keep the write-side projection
    (``resolve_placement_only``) consistent with the mutated partition. The single
    seam every partition-mutation test drives — so the all-kinds anti-mutant
    reuses this machinery rather than re-implementing the three-binding patch.
    """
    monkeypatch.setattr(artifacts_mod, "_PRIMARY_ARTIFACT_KINDS", primary)
    monkeypatch.setattr(artifacts_mod, "_PLACEMENT_ARTIFACT_KINDS", placement)
    monkeypatch.setattr(resolution_mod, "_PRIMARY_ARTIFACT_KINDS", primary)


@pytest.fixture
def _forced_pre_fix_partition(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the PRE-fix partition: move ``SPEC`` into ``_PLACEMENT_ARTIFACT_KINDS``."""
    orig_primary = artifacts_mod._PRIMARY_ARTIFACT_KINDS
    orig_placement = artifacts_mod._PLACEMENT_ARTIFACT_KINDS
    _patch_partition(
        monkeypatch,
        primary=orig_primary - {MissionArtifactKind.SPEC},
        placement=orig_placement | {MissionArtifactKind.SPEC},
    )


def test_anti_mutant_pre_fix_partition_makes_planning_ref_go_red(
    coord_mission: _CoordMission, _forced_pre_fix_partition: None
) -> None:
    """Anti-mutant: with SPEC forced back into the COORD partition, the planning-ref
    assertion the two-ref guard makes goes RED — proving the guard KILLS the
    "always-coord-for-coord-topology" mutant and is not vacuous (DECISION 7).

    The positive guard (``test_two_ref_partition_per_write_path``) asserts
    ``SPEC → target_branch``. Under the mutant SPEC resolves to the coordination
    branch instead, so that assertion would fail. We assert the mutant's effect
    directly (SPEC now resolves to coord) so this test is the explicit
    mutant-catcher paired with the positive guard.
    """
    spec_ref = resolve_placement_only(
        coord_mission.repo_root, coord_mission.mission_slug, kind=MissionArtifactKind.SPEC
    ).ref
    # Under the pre-fix mutant the planning artifact resolves to coordination —
    # exactly the regression the positive guard forbids.
    assert spec_ref == coord_mission.coordination_branch
    assert spec_ref != coord_mission.target_branch, (
        "Anti-mutant test is vacuous: forcing SPEC into the placement partition "
        "did not change its resolved ref — the two-ref guard could pass vacuously."
    )


# ---------------------------------------------------------------------------
# FR-006 (#2198): the machine-read partition-stability rationale map.
#
# A per-kind annotation that pins WHY each artifact kind sits on its partition,
# cross-checked against the LIVE ``_PRIMARY_ARTIFACT_KINDS`` /
# ``_PLACEMENT_ARTIFACT_KINDS`` frozensets so re-homing a kind is a conscious
# CI-red decision (SC-003). NET-NEW only (NFR-005): no ``file:line`` line-pins —
# the map keys on enum MEMBERS (content-anchored, CT7-clean) and reuses the
# ``resolve_placement_only`` machinery the existing tests already drive.
# ---------------------------------------------------------------------------

_Partition = Literal["PRIMARY", "COORD"]

# Each entry: kind → (partition, rationale, load_bearing_consumer). ``partition``
# is the human-facing PRIMARY/COORD label whose membership MUST match the live
# frozenset split (asserted below); ``rationale`` records why the kind sits there;
# ``load_bearing_consumer`` names the surface that breaks if it is re-homed.
PARTITION_RATIONALE: dict[MissionArtifactKind, tuple[_Partition, str, str]] = {
    MissionArtifactKind.SPEC: (
        "PRIMARY",
        "Planning SOURCE doc — lives with its mission on target_branch for every "
        "topology; a stale primary copy is REAL dirt, never coord residue.",
        "/spec-kitty.specify writer + safe-commit planning seam",
    ),
    MissionArtifactKind.DATA_MODEL: (
        "PRIMARY",
        "Planning SOURCE doc (/spec-kitty.plan) — primary-home, never transits "
        "coordination.",
        "/spec-kitty.plan writer",
    ),
    MissionArtifactKind.RESEARCH: (
        "PRIMARY",
        "Planning SOURCE doc (research.md) — primary-home for every topology.",
        "/spec-kitty.research writer",
    ),
    MissionArtifactKind.CHECKLIST: (
        "PRIMARY",
        "Planning SOURCE doc (checklists/) — primary-home; not coordination-owned.",
        "/spec-kitty.checklist writer",
    ),
    MissionArtifactKind.FINALIZED_EXECUTION_PLAN: (
        "PRIMARY",
        "Finalized plan.md travels with its mission on the primary surface.",
        "finalize-tasks / _planning_commit_worktree",
    ),
    MissionArtifactKind.TASKS_INDEX: (
        "PRIMARY",
        "tasks.md index is a planning artifact pinned to the primary surface.",
        "/spec-kitty.tasks writer",
    ),
    MissionArtifactKind.WORK_PACKAGE_TASK: (
        "PRIMARY",
        "tasks/WP*.md are planning artifacts — primary-home, read by implementers.",
        "implement/review WP read-side",
    ),
    MissionArtifactKind.LANE_STATE: (
        "PRIMARY",
        "lanes.json (finalize output) travels with tasks.md → primary-home.",
        "lane allocator / finalize-tasks",
    ),
    MissionArtifactKind.PRIMARY_METADATA: (
        "PRIMARY",
        "meta.json mission identity lives ONLY on the primary checkout for every "
        "topology (the never-committed-through-a-ref metadata home).",
        "identity resolver (mission_id / mid8 reads)",
    ),
    MissionArtifactKind.RETROSPECTIVE: (
        "PRIMARY",
        "FR-002 terminal artifact (retrospective.yaml) resolves to the durable "
        "mission home for every topology; never transits coordination.",
        "post-merge retrospective writer",
    ),
    MissionArtifactKind.ACCEPTANCE_MATRIX: (
        "COORD",
        "accept-time verification artifact — coordination-owned; stale primary "
        "copies are coordination residue under coord topology.",
        "accept gate (acceptance-matrix.json)",
    ),
    MissionArtifactKind.ISSUE_MATRIX: (
        "COORD",
        "issue-matrix.md is coordination-owned; routes to the coordination branch "
        "under coord topology.",
        "coordination issue-matrix writer",
    ),
    MissionArtifactKind.STATUS_STATE: (
        "COORD",
        "Append-only status.events.jsonl is the coordination-branch authority; its "
        "stale primary copy is residue, not real dirt.",
        "status reducer / dashboard (coord worktree)",
    ),
    MissionArtifactKind.ANALYSIS_REPORT: (
        "COORD",
        "record-analysis output (analysis-report.md) stays COORD per data-model.md.",
        "record-analysis writer",
    ),
}


def _placement_ref(mission: _CoordMission, kind: MissionArtifactKind) -> str:
    """Drive the REAL resolver for ``kind`` and return its resolved placement ref.

    The single resolver-driving seam reused by the all-kinds anti-mutant — it does
    NOT clone ``test_full_partition_resolves_per_membership``'s body; it factors the
    one ``resolve_placement_only(...).ref`` call that test already makes.
    """
    return resolve_placement_only(
        mission.repo_root, mission.mission_slug, kind=kind
    ).ref


def _derived_partition_split() -> tuple[
    set[MissionArtifactKind], set[MissionArtifactKind]
]:
    """Project the (PRIMARY, COORD) kind sets out of :data:`PARTITION_RATIONALE`."""
    primary = {k for k, (p, _r, _c) in PARTITION_RATIONALE.items() if p == "PRIMARY"}
    coord = {k for k, (p, _r, _c) in PARTITION_RATIONALE.items() if p == "COORD"}
    return primary, coord


def test_partition_rationale_is_exhaustive() -> None:
    """(a) Every ``MissionArtifactKind`` member has a rationale entry (SC-003).

    A newly-added kind without an entry — or a removed kind — fails here, so the
    map can never silently drift behind the enum.
    """
    assert set(PARTITION_RATIONALE) == set(MissionArtifactKind), (
        "PARTITION_RATIONALE must have exactly one entry per MissionArtifactKind. "
        f"Missing: {set(MissionArtifactKind) - set(PARTITION_RATIONALE)}; "
        f"Extra: {set(PARTITION_RATIONALE) - set(MissionArtifactKind)}"
    )
    for kind, (partition, rationale, consumer) in PARTITION_RATIONALE.items():
        assert partition in ("PRIMARY", "COORD"), (kind, partition)
        assert rationale.strip(), f"{kind.name} has an empty rationale"
        assert consumer.strip(), f"{kind.name} has an empty load_bearing_consumer"


def test_partition_rationale_split_matches_live_frozensets() -> None:
    """(b) The map's derived split EQUALS the live partition frozensets (SC-003).

    Re-homing a kind in ``_PRIMARY_ARTIFACT_KINDS`` / ``_PLACEMENT_ARTIFACT_KINDS``
    without updating its ``PARTITION_RATIONALE`` partition label makes this go RED —
    so a partition move is forced to also restate (and re-justify) the rationale.
    """
    derived_primary, derived_coord = _derived_partition_split()
    assert derived_primary == set(artifacts_mod._PRIMARY_ARTIFACT_KINDS), (
        "PARTITION_RATIONALE PRIMARY split diverged from the live "
        "_PRIMARY_ARTIFACT_KINDS frozenset — a kind was re-homed without updating "
        "its rationale."
    )
    assert derived_coord == set(artifacts_mod._PLACEMENT_ARTIFACT_KINDS), (
        "PARTITION_RATIONALE COORD split diverged from the live "
        "_PLACEMENT_ARTIFACT_KINDS frozenset — a kind was re-homed without updating "
        "its rationale."
    )


def _force_kind_into_opposite_partition(
    monkeypatch: pytest.MonkeyPatch, kind: MissionArtifactKind
) -> None:
    """Move ``kind`` to the OPPOSITE partition (PRIMARY↔COORD) on the live sets."""
    orig_primary = artifacts_mod._PRIMARY_ARTIFACT_KINDS
    orig_placement = artifacts_mod._PLACEMENT_ARTIFACT_KINDS
    if kind in orig_primary:
        _patch_partition(
            monkeypatch,
            primary=orig_primary - {kind},
            placement=orig_placement | {kind},
        )
    else:
        _patch_partition(
            monkeypatch,
            primary=orig_primary | {kind},
            placement=orig_placement - {kind},
        )


_ALL_KINDS_SORTED = sorted(MissionArtifactKind, key=lambda k: k.name)


@pytest.mark.parametrize(
    "kind", _ALL_KINDS_SORTED, ids=[k.name for k in _ALL_KINDS_SORTED]
)
def test_rehome_any_load_bearing_kind_flips_resolved_ref(
    coord_mission: _CoordMission,
    monkeypatch: pytest.MonkeyPatch,
    kind: MissionArtifactKind,
) -> None:
    """(c) All-kinds anti-mutant: re-homing ANY kind flips its resolved ref (SC-003).

    Broadens the single-SPEC ``test_anti_mutant_pre_fix_partition...`` to EVERY
    load-bearing kind. For each kind it drives the REAL resolver
    (``resolve_placement_only`` via ``_placement_ref``) twice — once on the live
    partition, once with the kind forced into the opposite partition — and asserts
    the resolved placement ref FLIPS to the opposite surface. A kind whose ref does
    NOT change on re-home would let the partition guard pass vacuously for it.
    """
    is_primary = kind in artifacts_mod._PRIMARY_ARTIFACT_KINDS
    true_ref = _placement_ref(coord_mission, kind)
    expected_true = (
        coord_mission.target_branch if is_primary else coord_mission.coordination_branch
    )
    assert true_ref == expected_true, (
        f"precondition: live-partition {kind.name} should resolve to "
        f"{expected_true!r}, got {true_ref!r}"
    )

    _force_kind_into_opposite_partition(monkeypatch, kind)

    mutated_ref = _placement_ref(coord_mission, kind)
    expected_opposite = (
        coord_mission.coordination_branch if is_primary else coord_mission.target_branch
    )
    assert mutated_ref == expected_opposite, (
        f"re-homing {kind.name} did not route it to the opposite surface "
        f"{expected_opposite!r}; got {mutated_ref!r}"
    )
    assert mutated_ref != true_ref, (
        f"re-homing {kind.name} left its resolved ref unchanged ({mutated_ref!r}) — "
        "the partition guard would pass vacuously for this kind."
    )
