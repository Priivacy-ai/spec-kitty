"""Behavioural contract for the Gate Execution Context (WP03).

Discharges ``contracts/gate-execution-context.md`` C1–C7 and data-model
``GateExecutionContext`` GEC-1..GEC-5 / ``LifecyclePhase`` PH-1. Every assertion is
behavioural on realistic fixtures (NFR-008) — there is **no** single-construction-site
source scan and **no** code-shape assertion. The integration cases drive the REAL WP02
resolver (:func:`mission_runtime.resolve_artifact_surface`) on un-patched git fixtures;
the pure cases exercise the value object's outcomes directly.

Prior art reused rather than reinvented (contract C1): the decoy-marker idiom in
``tests/integration/coord_topology_fixture.py`` (a distinct answer seeded on the primary
copy so a wrong-leg read returns a wrong *value*, not merely a wrong path), and the
cwd-independence discipline of
``test_placement_partition_golden_path.py::test_cwd_independence_resolves_identical_authority``
(run the gate from a directory sharing no ancestry with the repo).

C-006 gate-coverage registration: this new file shells out to git (the integration
cases), so it carries the ``integration`` + ``git_repo`` markers deliberately.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mission_runtime import MissionArtifactKind, TopologySurface
from specify_cli.acceptance.execution_context import (
    CannotEvaluate,
    CannotEvaluateReason,
    GateExecutionContext,
    GateSurfaceRefMismatch,
    LifecyclePhase,
    build_gate_execution_context,
    declared_home_surface,
)
from specify_cli.acceptance.gates_core import (
    AcceptanceCheckDiagnostic,
    _acceptance_gate_context,
    _evaluate_acceptance_matrix,
)
from specify_cli.acceptance.matrix import (
    AcceptanceCriterion,
    AcceptanceMatrix,
    write_acceptance_matrix,
)
from tests.integration import coord_topology_fixture as ctf

# The ``coord_topology_mission`` / ``flat_topology_mission`` fixtures are injected
# by name via ``tests/acceptance/conftest.py`` (re-exported there to avoid the
# import-shadows-parameter F811), so they are NOT imported into this module.

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


# ===========================================================================
# Helpers — realistic acceptance matrices + the create-window fixtures
# ===========================================================================


def _seed_matrix(feature_dir: Path, *, verdict: str, marker: str) -> None:
    """Write a realistic acceptance-matrix.json whose overall_verdict is ``verdict``.

    ``marker`` becomes the single criterion's id so a wrong-leg read returns a
    distinguishable *value* (the decoy-marker idiom), not merely a wrong path.
    """
    pass_fail = "fail" if verdict == "fail" else "pass"
    matrix = AcceptanceMatrix(
        mission_slug=feature_dir.name,
        criteria=[
            AcceptanceCriterion(
                criterion_id=marker,
                description=f"seeded {verdict} criterion",
                proof_type="code_review",
                evidence="seeded",
                pass_fail=pass_fail,
                verified_by="pedro",
                verified_at="2026-07-24T00:00:00+00:00",
            )
        ],
    )
    write_acceptance_matrix(feature_dir, matrix)


def _plain_context(
    *,
    surface: Path,
    surface_kind: TopologySurface,
    phase: LifecyclePhase = LifecyclePhase.ACCEPT,
    ref: str = "main",
) -> GateExecutionContext:
    return GateExecutionContext(
        surface=surface,
        surface_kind=surface_kind,
        ref=ref,
        phase=phase,
        mission_slug="mission-under-test",
    )


def _build_create_window_coord(
    tmp_path: Path, *, coord_branch_exists: bool
) -> tuple[Path, str, Path]:
    """Materialise a coord-routing mission whose coord worktree is NOT created.

    ``coord_branch_exists=True`` → UNMATERIALIZED (branch present, no worktree — the
    #1718 create window). ``coord_branch_exists=False`` → DELETED (branch absent).
    No ``.worktrees/<slug>-coord`` is ever created, so ``probe_coord_state`` sees the
    coord root absent and splits the two states on the branch's git existence. No
    resolver is patched. Returns ``(repo_root, slug, primary_feature_dir)``.
    """
    subdir = "unmat" if coord_branch_exists else "deleted"
    repo = ctf._make_git_repo(tmp_path / subdir)
    mission_id = "01KY72GQ0000000000000000A1"
    mid8 = mission_id[:8]
    slug = f"create-window-{mid8}"
    coord_branch = f"kitty/mission-{slug}"
    if coord_branch_exists:
        ctf._git(repo, "branch", coord_branch)

    feature_dir = repo / "kitty-specs" / slug
    feature_dir.mkdir(parents=True)
    ctf._write_meta(
        feature_dir,
        slug=slug,
        mission_id=mission_id,
        topology="coord",
        coordination_branch=coord_branch,
    )
    ctf._write_lanes_json(feature_dir, slug=slug, mission_id=mission_id)
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    ctf._write_wp_task(tasks_dir, "WP01")
    ctf._git(repo, "add", ".")
    ctf._git(repo, "commit", "-m", "feat: primary planning, coord worktree not materialised")
    return repo, slug, feature_dir


# ===========================================================================
# LifecyclePhase + PH-1 (T015)
# ===========================================================================


def test_lifecycle_phase_is_ordered() -> None:
    """PH-1 ordering: REVIEW < ACCEPT < POST_CONSOLIDATION."""
    assert LifecyclePhase.REVIEW < LifecyclePhase.ACCEPT < LifecyclePhase.POST_CONSOLIDATION


def test_implement_is_not_a_lifecycle_phase() -> None:
    """IC-01 finding: IMPLEMENT is not represented (no gate declares that floor)."""
    assert "IMPLEMENT" not in LifecyclePhase.__members__


def test_below_minimum_phase_returns_not_applicable() -> None:
    """PH-1: a gate invoked below its declared floor returns NOT_APPLICABLE_IN_PHASE.

    Not a pass and not a fail — a distinguishable cannot-evaluate naming its surface.
    """
    ctx = _plain_context(surface=Path("/x"), surface_kind=TopologySurface.PRIMARY,
                         phase=LifecyclePhase.REVIEW)
    outcome = ctx.not_applicable_below(LifecyclePhase.ACCEPT)
    assert isinstance(outcome, CannotEvaluate)
    assert outcome.reason is CannotEvaluateReason.BELOW_MINIMUM_PHASE
    assert outcome.reason.value == "NOT_APPLICABLE_IN_PHASE"
    assert outcome.surface_kind is TopologySurface.PRIMARY and outcome.ref == "main"


@pytest.mark.parametrize("phase", [LifecyclePhase.ACCEPT, LifecyclePhase.POST_CONSOLIDATION])
def test_at_or_above_minimum_phase_is_evaluable(phase: LifecyclePhase) -> None:
    """A gate at or above its declared floor is not short-circuited (returns None)."""
    ctx = _plain_context(surface=Path("/x"), surface_kind=TopologySurface.COORD, phase=phase)
    assert ctx.not_applicable_below(LifecyclePhase.ACCEPT) is None


# ===========================================================================
# Cannot-evaluate + GEC-5 (T016) — a stamp is not permission
# ===========================================================================


def test_gec5_coord_home_on_primary_stamp_cannot_evaluate() -> None:
    """GEC-5 / C2: a COORD-homed kind judged on a PRIMARY-stamped surface refuses.

    This is the create-window substitution: the outcome is cannot-evaluate (naming
    the reason + surface + ref), NOT a verdict — the #2885 pass-by-default fix.
    """
    ctx = _plain_context(surface=Path("/primary"), surface_kind=TopologySurface.PRIMARY)
    outcome = ctx.surface_cannot_hold(TopologySurface.COORD)
    assert isinstance(outcome, CannotEvaluate)
    assert outcome.reason is CannotEvaluateReason.SURFACE_CANNOT_HOLD_FACT
    # C6: the refusal names a resolvable surface + ref.
    assert outcome.surface_kind is TopologySurface.PRIMARY and outcome.ref == "main"


def test_gec5_flat_primary_home_can_hold() -> None:
    """C7 neutrality: a PRIMARY-homed kind on a PRIMARY surface is judgeable (None).

    Flat / SINGLE_BRANCH / LANES resolve primary as their DECLARED home (AH-2) — the
    stamp is genuine, not a substitution, so the gate proceeds to a verdict.
    """
    ctx = _plain_context(surface=Path("/primary"), surface_kind=TopologySurface.PRIMARY)
    assert ctx.surface_cannot_hold(TopologySurface.PRIMARY) is None


def test_gec5_materialized_coord_home_can_hold() -> None:
    """A COORD-homed kind on a materialised COORD surface is judgeable (None)."""
    ctx = _plain_context(surface=Path("/coord"), surface_kind=TopologySurface.COORD)
    assert ctx.surface_cannot_hold(TopologySurface.COORD) is None


def test_cannot_evaluate_is_a_distinct_outcome_type() -> None:
    """C2: cannot-evaluate is a distinguishable type, not a pass/fail string."""
    outcome = _plain_context(
        surface=Path("/p"), surface_kind=TopologySurface.PRIMARY
    ).surface_cannot_hold(TopologySurface.COORD)
    assert isinstance(outcome, CannotEvaluate)
    assert outcome.reason.value not in {"pass", "fail", "pending"}


def test_gate_execution_context_is_immutable() -> None:
    """GEC-1 shape: the value object a gate is handed is frozen — no in-place patch."""
    ctx = _plain_context(surface=Path("/p"), surface_kind=TopologySurface.PRIMARY)
    with pytest.raises((AttributeError, TypeError)):
        ctx.surface = Path("/elsewhere")  # type: ignore[misc]


# ===========================================================================
# GEC-2 / C5 — ref agreement (injected head resolver, no real git needed)
# ===========================================================================


def test_assert_at_ref_raises_when_surface_drifted() -> None:
    """C5: a surface not at its ref makes the gate refuse rather than judge."""
    ctx = _plain_context(surface=Path("/p"), surface_kind=TopologySurface.COORD, ref="expected-sha")
    with pytest.raises(GateSurfaceRefMismatch) as excinfo:
        ctx.assert_at_ref(head_of=lambda _s: "different-sha")
    assert excinfo.value.error_code == "GATE_SURFACE_REF_MISMATCH"
    assert excinfo.value.expected_ref == "expected-sha"
    assert excinfo.value.actual_ref == "different-sha"


def test_assert_at_ref_passes_on_agreement() -> None:
    """C5: when the surface is at its ref, the gate proceeds (no raise)."""
    ctx = _plain_context(surface=Path("/p"), surface_kind=TopologySurface.COORD, ref="sha-abc")
    ctx.assert_at_ref(head_of=lambda _s: "sha-abc")  # must not raise


# ===========================================================================
# Total resolution over the four CoordState answers (T017 / C3) — real resolver
# ===========================================================================


def test_build_context_materialized_coord_stamps_coord(
    coord_topology_mission: ctf.CoordTopologyContext,
) -> None:
    """C3 MATERIALIZED: a materialised coord worktree resolves + stamps COORD."""
    ctx = build_gate_execution_context(
        coord_topology_mission.repo,
        coord_topology_mission.slug,
        MissionArtifactKind.ACCEPTANCE_MATRIX,
        phase=LifecyclePhase.ACCEPT,
        ref="main",
    )
    assert ctx.surface_kind is TopologySurface.COORD
    assert ctx.surface == coord_topology_mission.coord_feature_dir


def test_build_context_flat_stamps_primary(
    flat_topology_mission: ctf.FlatTopologyContext,
) -> None:
    """C3 / AH-2: a flat mission resolves primary AFFIRMATIVELY, stamped PRIMARY."""
    ctx = build_gate_execution_context(
        flat_topology_mission.repo,
        flat_topology_mission.slug,
        MissionArtifactKind.ACCEPTANCE_MATRIX,
        phase=LifecyclePhase.ACCEPT,
        ref="main",
    )
    assert ctx.surface_kind is TopologySurface.PRIMARY
    assert ctx.surface == flat_topology_mission.primary_feature_dir


def test_build_context_unmaterialized_stamps_primary_without_raising(tmp_path: Path) -> None:
    """C3 UNMATERIALIZED: the create-window resolves primary + stamps PRIMARY.

    A DECLARED answer for that state, not a degradation — it does NOT raise.
    """
    repo, slug, primary_feature_dir = _build_create_window_coord(
        tmp_path, coord_branch_exists=True
    )
    ctx = build_gate_execution_context(
        repo, slug, MissionArtifactKind.ACCEPTANCE_MATRIX,
        phase=LifecyclePhase.ACCEPT, ref="main",
    )
    assert ctx.surface_kind is TopologySurface.PRIMARY
    assert ctx.surface == primary_feature_dir


def test_build_context_deleted_coord_branch_raises(tmp_path: Path) -> None:
    """C3 DELETED: a declared coord branch absent from git raises, does NOT read primary."""
    from specify_cli.coordination.surface_resolver import CoordinationBranchDeleted

    repo, slug, _primary = _build_create_window_coord(tmp_path, coord_branch_exists=False)
    with pytest.raises(CoordinationBranchDeleted) as excinfo:
        build_gate_execution_context(
            repo, slug, MissionArtifactKind.ACCEPTANCE_MATRIX,
            phase=LifecyclePhase.ACCEPT, ref="main",
        )
    assert excinfo.value.error_code == "COORDINATION_BRANCH_DELETED"


def test_declared_home_surface_coord_vs_flat(
    coord_topology_mission: ctf.CoordTopologyContext,
    flat_topology_mission: ctf.FlatTopologyContext,
) -> None:
    """The kind's declared home is COORD under coord topology, PRIMARY under flat."""
    assert (
        declared_home_surface(
            coord_topology_mission.repo,
            coord_topology_mission.slug,
            MissionArtifactKind.ACCEPTANCE_MATRIX,
        )
        is TopologySurface.COORD
    )
    assert (
        declared_home_surface(
            flat_topology_mission.repo,
            flat_topology_mission.slug,
            MissionArtifactKind.ACCEPTANCE_MATRIX,
        )
        is TopologySurface.PRIMARY
    )


# ===========================================================================
# C1 — a gate judges the surface it was handed, not an ambient one (behavioural)
# ===========================================================================


def test_c1_gate_judges_handed_surface_not_ambient(
    coord_topology_mission: ctf.CoordTopologyContext,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """C1: the acceptance-matrix verdict reflects the answer at ``context.surface``.

    The surface (the materialised COORD dir) is distinct from BOTH ``repo_root``
    (the primary checkout) and the process cwd (an unrelated dir sharing no
    ancestry). All three hold DIFFERENT seeded answers: COORD carries a FAIL
    matrix, the primary decoy carries a PASS matrix (silent if read), the cwd carries
    a third decoy. The gate reads coord → the verdict is FAIL. Reverting the read to
    the ambient primary/cwd surface would flip it to a silent pass — the mutant dies
    on a wrong *value*, not merely a wrong path.
    """
    ctx = coord_topology_mission
    # Seed three DIFFERENT answers at the three locations.
    _seed_matrix(ctx.coord_feature_dir, verdict="fail", marker="COORD-AUTHORITY")
    _seed_matrix(ctx.primary_feature_dir, verdict="pass", marker="PRIMARY-DECOY")
    unrelated_cwd = tmp_path_factory.mktemp("unrelated-cwd")
    assert not str(unrelated_cwd).startswith(str(ctx.repo))
    _seed_matrix(unrelated_cwd, verdict="pass", marker="CWD-DECOY")

    # Pre-flight: the gate is genuinely handed the COORD surface (non-vacuity).
    handed = _acceptance_gate_context(ctx.repo, ctx.primary_feature_dir)
    assert handed.surface_kind is TopologySurface.COORD
    assert handed.surface == ctx.coord_feature_dir

    monkeypatch.chdir(unrelated_cwd)
    activity_issues: list[str] = []
    skipped: list[AcceptanceCheckDiagnostic] = []
    blocked: list[AcceptanceCheckDiagnostic] = []
    _evaluate_acceptance_matrix(
        ctx.repo, ctx.primary_feature_dir, activity_issues, skipped, blocked,
        mutate_matrix=False,
    )

    # The verdict follows context.surface (COORD → fail), not the ambient decoys.
    assert any("verdict is 'fail'" in issue for issue in activity_issues), activity_issues
    assert not any(c.check == "acceptance_matrix_cannot_evaluate" for c in blocked)


# ===========================================================================
# GEC-5 through the real gate — create-window refuses instead of passing (#2885)
# ===========================================================================


def test_gec5_create_window_gate_refuses_instead_of_passing(tmp_path: Path) -> None:
    """GEC-5 end to end: the create window records cannot-evaluate, not a pass.

    On the UNMATERIALIZED coord create window the surface resolves PRIMARY. A PASS
    matrix is seeded on that primary surface — WITHOUT GEC-5 the gate would read it
    and pass by default (#2885). GEC-5 refuses: a distinguishable cannot-evaluate
    naming its reason + surface, and NO silent pass.
    """
    repo, slug, primary_feature_dir = _build_create_window_coord(
        tmp_path, coord_branch_exists=True
    )
    _seed_matrix(primary_feature_dir, verdict="pass", marker="PRIMARY-EMPTY-STAND-IN")

    activity_issues: list[str] = []
    skipped: list[AcceptanceCheckDiagnostic] = []
    blocked: list[AcceptanceCheckDiagnostic] = []
    _evaluate_acceptance_matrix(
        repo, primary_feature_dir, activity_issues, skipped, blocked,
        mutate_matrix=False,
    )

    assert any(c.check == "acceptance_matrix_cannot_evaluate" for c in blocked), blocked
    assert any(
        CannotEvaluateReason.SURFACE_CANNOT_HOLD_FACT.value in issue
        for issue in activity_issues
    ), activity_issues
    # It is NOT a verdict — no pass/fail verdict issue was recorded.
    assert not any("verdict is" in issue for issue in activity_issues)


def test_gec2_primary_ref_drift_gate_refuses_instead_of_passing(
    flat_topology_mission: ctf.FlatTopologyContext,
) -> None:
    """GEC-2 / C5 end to end: a drifted PRIMARY surface refuses, not judges.

    The real gate resolves ``ref`` from the caller-observed currently-checked-out
    ``branch`` (:func:`_acceptance_gate_context`). A PASS matrix is seeded on the
    genuine primary surface, but the caller asserts a ``branch`` that does NOT match
    what is actually checked out (simulating drift between when ``branch`` was
    captured and when this gate runs — WITHOUT GEC-2 the gate would read the seeded
    PASS matrix and judge it, silently ignoring the drift). GEC-2 refuses: a
    ``GATE_SURFACE_REF_MISMATCH`` cannot-evaluate naming the surface + expected/actual
    ref, and NO pass/fail verdict.
    """
    ctx = flat_topology_mission
    _seed_matrix(ctx.primary_feature_dir, verdict="pass", marker="DRIFTED-REF-PASS")

    activity_issues: list[str] = []
    skipped: list[AcceptanceCheckDiagnostic] = []
    blocked: list[AcceptanceCheckDiagnostic] = []
    _evaluate_acceptance_matrix(
        ctx.repo, ctx.primary_feature_dir, activity_issues, skipped, blocked,
        mutate_matrix=False, branch="stale-observed-branch",
    )

    assert any(c.check == "acceptance_matrix_cannot_evaluate" for c in blocked), blocked
    assert any("GATE_SURFACE_REF_MISMATCH" in issue for issue in activity_issues), activity_issues
    # It is NOT a verdict — no pass/fail verdict issue was recorded.
    assert not any("verdict is" in issue for issue in activity_issues)


def test_gec2_primary_ref_agreement_still_judges(
    flat_topology_mission: ctf.FlatTopologyContext,
) -> None:
    """GEC-2 happy path: a PRIMARY surface genuinely at its ref still judges (C5).

    The caller-observed ``branch`` matches what is actually checked out (the
    ordinary, undrifted case) — ref-agreement holds, so the gate proceeds to a real
    verdict instead of refusing.
    """
    ctx = flat_topology_mission
    _seed_matrix(ctx.primary_feature_dir, verdict="fail", marker="AT-REF-FAIL")

    activity_issues: list[str] = []
    skipped: list[AcceptanceCheckDiagnostic] = []
    blocked: list[AcceptanceCheckDiagnostic] = []
    _evaluate_acceptance_matrix(
        ctx.repo, ctx.primary_feature_dir, activity_issues, skipped, blocked,
        mutate_matrix=False, branch="main",
    )

    assert not any(c.check == "acceptance_matrix_cannot_evaluate" for c in blocked), blocked
    assert any("verdict is 'fail'" in issue for issue in activity_issues), activity_issues


# ===========================================================================
# C7 — topology neutrality: identical defect → identical outcome (coord and flat)
# ===========================================================================


def test_c7_identical_defect_identical_outcome_coord_and_flat(
    coord_topology_mission: ctf.CoordTopologyContext,
    flat_topology_mission: ctf.FlatTopologyContext,
) -> None:
    """C7 / C-004: the same FAIL defect on coord and flat yields the same outcome.

    The gate is neither named nor shaped around coordination topology and reads no
    ``flattened`` flag: a FAIL matrix seeded at each mission's GENUINE home (coord's
    materialised worktree, flat's primary dir) produces the identical
    ``verdict is 'fail'`` outcome. A decoy PASS matrix on the coord mission's primary
    leg proves the coord case really read coord, not its own primary.
    """
    # Coord: defect at the materialised coord home; decoy pass on the primary leg.
    _seed_matrix(coord_topology_mission.coord_feature_dir, verdict="fail", marker="COORD-DEFECT")
    _seed_matrix(coord_topology_mission.primary_feature_dir, verdict="pass", marker="COORD-PRIMARY-DECOY")
    # Flat: defect at its declared (primary) home.
    _seed_matrix(flat_topology_mission.primary_feature_dir, verdict="fail", marker="FLAT-DEFECT")

    coord_issues: list[str] = []
    flat_issues: list[str] = []
    _evaluate_acceptance_matrix(
        coord_topology_mission.repo, coord_topology_mission.primary_feature_dir,
        coord_issues, [], [], mutate_matrix=False,
    )
    _evaluate_acceptance_matrix(
        flat_topology_mission.repo, flat_topology_mission.primary_feature_dir,
        flat_issues, [], [], mutate_matrix=False,
    )

    coord_fail = any("verdict is 'fail'" in i for i in coord_issues)
    flat_fail = any("verdict is 'fail'" in i for i in flat_issues)
    assert coord_fail and flat_fail, (coord_issues, flat_issues)
    assert coord_fail == flat_fail  # identical outcome, identical defect


# ===========================================================================
# C6 — every recorded judgement names its surface + ref
# ===========================================================================


def test_c6_recorded_judgement_names_surface_and_ref(
    coord_topology_mission: ctf.CoordTopologyContext,
) -> None:
    """C6 / NFR-003: the cannot-evaluate outcome carries a resolvable surface + ref.

    Built through the real gate-context door so the ``ref`` is the mission's own
    target branch (a resolvable identifier), not a synthetic literal.
    """
    ctx = _acceptance_gate_context(
        coord_topology_mission.repo, coord_topology_mission.primary_feature_dir
    )
    # The context (and thus any verdict/refusal derived from it) names its surface+ref.
    assert ctx.surface_kind is TopologySurface.COORD
    assert ctx.ref == "main"  # the mission's recorded target_branch
    outcome = ctx.not_applicable_below(LifecyclePhase.POST_CONSOLIDATION)
    assert isinstance(outcome, CannotEvaluate)
    assert outcome.surface_kind is TopologySurface.COORD and outcome.ref == "main"


def test_fixture_smoke_no_resolver_patched(
    coord_topology_mission: ctf.CoordTopologyContext,
) -> None:
    """Non-vacuity: the coord fixture is real git state (a coord worktree exists)."""
    assert coord_topology_mission.coord_feature_dir.exists()
    assert (coord_topology_mission.repo / ".worktrees").exists()
    # meta.json on primary declares coord topology (drives the real resolver).
    meta = json.loads(
        (coord_topology_mission.primary_feature_dir / "meta.json").read_text(encoding="utf-8")
    )
    assert meta["topology"] == "coord"
