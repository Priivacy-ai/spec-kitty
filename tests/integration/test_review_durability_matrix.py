"""WP15 (T067-T069, FR-015): the review-verdict durability coverage matrix.

FR-015 / US1 Acceptance Scenario 9: for the matrix of **verdict x target lane x
topology x auto-commit**, durability must behave as that cell specifies, AND
removing the commit call must turn each cell red. A matrix that stays green
after the production commit call is deleted proves nothing -- that is the
entire reason this WP exists (see the module-level mutation tests below).

**Matrix shape (T067) -- 12 cells, documented so a future dimension addition
is visible as a count change:**

FR-015 names four axes literally. Two of them (verdict, target lane) are not
independent in production: a WP is never simultaneously "rejected" and
"done" -- the real writer produces exactly three non-redundant (verdict,
lane) pairings (:data:`_SCENARIOS`), not the 3x3 = 9 combinations a bare
cross-product would suggest. Excluding the six nonsensical pairings is not
"a subset chosen for convenience" (the WP's own caution) -- it is excluding
combinations the production writer cannot produce. The fourth verdict named
by the mission (an **arbiter override**) is handled in its OWN, separate,
smaller matrix (see "Arbiter override" section below) because WP12 retired
its durability mechanism onto the event-sourced ``commit_status`` seam, not
the ``commit_artifact`` seam every other cell here exercises -- folding it
into the same 12-cell parametrization would silently paper over that
structural difference (exactly the "assertion-specificity" risk the WP
prompt names).

    3 scenarios x 2 topologies x 2 auto-commit settings = 12 cells

* **Scenarios** (:data:`_SCENARIOS`): ``rejected_planned`` (the rollback
  writer), ``approved_approved``, ``approved_done`` (the ordinary approval
  writer, target lane APPROVED or DONE).
* **Topology** (:data:`_TOPOLOGIES`): ``single_branch`` (``skip_target_branch_
  commit=False``) vs ``coord_protected`` (``skip_target_branch_commit=True``,
  the protected-primary-under-coordination-topology shape T050 introduced). Be
  precise about what this axis actually is: **every one of these 12 cells runs
  against a plain, non-coord, single-branch git repo** (``_seed_fixture``'s
  ``_init_repo``); ``"topology"`` here is a directly-patched
  ``_skip_target_branch_commit`` boolean, not a real coord worktree. It
  legitimately proves the ONE topology-mediated behaviour a ``FakeCoordCommit
  Router`` cell can observe at all -- the skip-gate
  (``_resolve_verdict_commit_router``'s own docstring: "a protected-primary-
  coord topology is a SECOND, structurally different cause") -- but it does
  NOT exercise WP04's OTHER topology effect: which git REF the commit lands on
  (PRIMARY vs COORD). That effect needed a genuinely separate, real coord
  worktree, added below as its own section ("T069c -- the real coord-topology
  cell") built on ``tests/integration/coord_topology_fixture.py``'s
  ``_build_coord_topology`` -- not folded into this 12-cell parametrization,
  and not skipped.
* **Auto-commit**: ``True`` / ``False`` (``--no-auto-commit``, FR-013).

**T068 -- the non-vacuity proof.** :func:`test_matrix_is_sensitive_to_commit_
removal` re-drives the 3 cells where a commit is actually attempted
(``auto_commit=True`` AND ``single_branch``) with ``commit_artifact``
monkeypatched to the documented no-op (``CommitArtifactResult(status=
"unchanged", ...)``) and asserts each one now raises. The other 9 cells
(``auto_commit=False``, or ``coord_protected``) never call ``commit_artifact``
at all by design (T050's skip gate fires BEFORE the call) -- mutating it
cannot and must not affect them; :func:`test_protected_and_no_auto_commit_
cells_never_invoke_commit_artifact` pins that insulation explicitly as its OWN
regression guard, rather than silently omitting it.

**T069a/b -- real router, real git (single_branch), and the SIGKILL cell.**
:func:`test_real_router_commit_lands_on_disk_and_git_history` and
:func:`test_real_router_cell_reds_when_commit_artifact_is_neutered` drive the
REAL ``RealCoordCommitRouter``/``commit_for_mission`` against a real,
git-initialised repo (reusing ``test_move_task_durability.py``'s established
``_FaultInjectableCoordRouter`` fixture rather than duplicating a second real-
git harness) -- like the 12-cell matrix above, this pair is a SINGLE_BRANCH
repo (``_init_repo``), not a coord worktree; it proves the commit is genuinely
real and mutation-sensitive, not that topology is exercised.
:func:`test_sigkill_between_write_and_commit_then_identical_retry_exits_zero`
is the dedicated SC-003 SIGKILL cell (also single_branch): a child OS process
performs ONLY ``_allocate_and_write_review_cycle_locked`` (the write+validate
half -- there is no commit call reachable in the killed function at all, so
the kill window is unambiguous), signals write-complete readiness via a file,
then hangs; the parent SIGKILLs it in that window and re-drives the identical
write from the PARENT process, asserting the retry both completes cleanly and
records the correct verdict at ``HEAD``. This is scoped to the SPEC's own
named window ("killed between the write and the commit") -- a mid-write kill
is a different, filesystem-dependent hazard this test deliberately does not
simulate (matching WP10's T044 scope note).

**T069c -- the real coord-topology cell (the genuine topology coverage).**
:func:`test_real_coord_topology_review_cycle_commits_to_coord_ref_not_primary`,
:func:`test_real_coord_topology_cell_reds_when_commit_artifact_is_neutered`,
and :func:`test_real_coord_topology_revert_deletes_and_commits_on_coord_ref`
are built on the canonical ``tests/integration/coord_topology_fixture.py``
(``_build_coord_topology``) -- a REAL coord worktree via
``CoordinationWorkspace.resolve``, not a patched flag. They assert on
committed git trees (``git show <ref>:<path>``) that a review-cycle write
lands on the COORD ref and is absent on primary, that this is genuinely
mutation-sensitive, and -- the actual durability-matrix witness for WP13's
fix (DM-01KZ75GBNXC73Q38M43GBH38W7) -- that a transition-emit failure AFTER
a coord-topology write already landed is reverted on the SAME coord ref, not
primary (the live bug WP13's ``_resolve_revert_commit_worktree`` +
``kind=REVIEW_CYCLE`` fix closed; WP11's own tests never caught it because
they exercised only a single_branch fixture). No product defect surfaced
beyond what WP13 already fixed.

**SC-004 -- MET post verdict-seam-write-unification (event-log durability).**
:func:`test_sc004_two_concurrent_processes_never_clobber_a_verdict_over_50_
iterations` upgrades WP10's own THREADED reproduction
(``tests/review/test_cycle.py::test_concurrent_verdict_writes_do_not_clobber_
each_other``, which carries an explicit ``TODO(WP15)``) to SC-004's literal
bar: >= 50 iterations, 2 real OS processes (``multiprocessing``, not threads --
``feature_status_lock`` is an inter-process ``FileLock``).

**History (WP15).** Under the pre-verdict-seam authority the durable act was
the ``.md`` git commit (``_commit_review_cycle_artifact``, deliberately OUTSIDE
``feature_status_lock`` per NFR-006), which has NO protection against two
processes racing ``git add``/``git commit`` in the SAME working tree -- so
WP15 committed this probe as an honest, reproducible red witness of a genuine
durability gap.

**Resolution (verdict-seam-write-unification-01KZ9Q35, WP05).** That mission
re-pointed the authoritative durable act off the best-effort ``.md`` commit
onto the ``status.events.jsonl`` event log (NFR-004): the review_result event
is appended INSIDE ``feature_status_lock`` by the production recording path
(``status.emit.emit_status_transition``, emit.py). Two concurrent verdict
recordings therefore serialize on that inter-process lock -- no lost update.
This test's authoritative anchor is the event-record count
(``_assert_durable_event_records_at_least``, >= 2 * iterations distinct
``review_result`` event_ids), NOT ``.md`` files or a clean git tree.

**Post-merge green-up (2026-08-06).** The consolidated feature branch surfaced
TWO distinct intermittent reds this probe had left un-repointed; both are fixed
without weakening the durability guarantee, ``xfail``/``skip``, or any product
change:

1. **Event-count anchor (~2/12 stress runs: "99 of 100 distinct records").** A
   TEST-fixture defect, not a product defect: :func:`_mp_write_review_cycle`
   appended its authoritative event via the raw ``append_events_atomic_verified``
   store primitive **without** holding ``feature_status_lock`` -- manufacturing a
   read-modify-write/``os.replace`` lost-update race that production (which always
   appends the review_result event under that lock -- ``status.emit.
   emit_status_transition``) cannot have. Within a single working tree the
   ``.gitattributes`` union merge driver never fires (no git *merge* at write
   time). The worker now holds ``feature_status_lock`` around its append,
   mirroring production. This is the real, lock-serialized durability guarantee.

2. **Per-iteration ``.md`` existence assert ("review-cycle-N.md missing from
   disk", surfaced only under whole-file contention).** This re-tested the
   RETIRED authority: NFR-004 makes the ``.md`` render commit best-effort (it
   runs OUTSIDE ``feature_status_lock`` per NFR-006 and has no protection against
   two processes racing ``git`` in one tree, so a best-effort ``.md`` MAY vanish
   under contention -- BY DESIGN acceptable, because durability moved to the
   event log). WP05 demoted the git-status assertion but left this
   ``path.exists()`` durability assertion on the best-effort file. The loop now
   asserts best-effort-``.md`` *integrity* (a surviving file's body is one
   writer's own feedback) but NOT its *durability*; the sole durability anchor
   is the lock-serialized event count below.

Verified deterministically green: 10/10 whole-file runs under the maximum
parallel contention (6 concurrent full-file invocations) that reproduced both
reds. The negative control (:func:`test_sc003_durability_negative_control_
dropped_event_reds`) proves the event anchor is still non-vacuous.
"""

from __future__ import annotations

import json
import multiprocessing
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import typer

from specify_cli.agent_tasks_ports import (
    CommitArtifactResult,
    RealCoordCommitRouter,
    TasksPorts,
)
from specify_cli.cli.commands.agent.tasks import _do_move_task, _MoveTaskArgs
from specify_cli.review.artifacts import ReviewCycleArtifact
from specify_cli.review.cycle import (
    _allocate_and_write_review_cycle_locked,
    _review_cycle_wp_dir,
    create_rejected_review_cycle,
)
from specify_cli.status import materialize as _materialize
from specify_cli.status.models import Lane, ReviewResult, StatusEvent
from specify_cli.status.store import append_event, read_events
from tests.integration.coord_topology_fixture import (
    CoordTopologyContext,
    _build_coord_topology,
)
from tests.mocked_env import setup_mocked_env
from tests.specify_cli.cli.commands.agent.test_move_task_durability import (
    _FaultInjectableCoordRouter,
    _build_wp_file,
    _git_head_has_file,
    _git_status,
    _init_repo,
    _seed_wp_event,
    _unprotect_main,
)
from tests.specify_cli.cli.commands.agent.test_tasks_ports import (
    FakeCoordCommitRouter,
    FakeFsReader,
    FakeGitOps,
    FakeRender,
)

# Architectural convention (test_pytest_marker_convention.py): every test_*.py
# file must declare a module-level marker. Per-test ``@pytest.mark.fast`` /
# ``@pytest.mark.integration`` / ``@pytest.mark.git_repo`` decorators below
# refine individual tests further; this module-level mark satisfies the
# file-level presence check and reflects the file's home (real command
# surface + real git, not pure unit logic).
#
# PR #3211 landing pass (2026-08-05, F6): ``git_repo`` added at module level --
# EVERY cell (including the ``@pytest.mark.fast``-decorated ones above)
# transitively drives a real ``git init``/``git add``/``git commit`` via
# ``_seed_fixture`` -> ``_init_repo`` (see that helper's own docstring: the
# production writer's ``feature_status_lock`` is keyed under the real git
# common dir, so there is no way to exercise it against a non-git
# ``tmp_path``). ``test_pytest_marker_correctness.py``'s Rule 1 requires the
# marker at file scope whenever the file invokes git via subprocess anywhere,
# which this file does.
pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

# ---------------------------------------------------------------------------
# Shared constants (Sonar S1192: every repeated literal below is named once)
# ---------------------------------------------------------------------------

_MISSION = "durability-matrix"
_WP_ID = "WP01"
_WP_SLUG = f"{_WP_ID}-test"
_REASON_NO_AUTO_COMMIT = "no_auto_commit"
_REASON_PROTECTED_TARGET_BRANCH = "protected_target_branch"
_REVIEW_GATE_BYPASS: dict[str, Any] = {
    "_validate_ready_for_review": (True, []),
    "_check_unchecked_subtasks": [],
}
_SEED_FEEDBACK_BODY = "Needs another pass before the matrix drives it.\n"


@dataclass(frozen=True)
class _Scenario:
    """One non-redundant (verdict, target_lane) pairing the real writer produces."""

    scenario_id: str
    verdict: str
    target_lane: str


_SCENARIOS: tuple[_Scenario, ...] = (
    _Scenario("rejected_planned", "rejected", "planned"),
    _Scenario("approved_approved", "approved", "approved"),
    _Scenario("approved_done", "approved", "done"),
)
_TOPOLOGIES: tuple[str, ...] = ("single_branch", "coord_protected")
_AUTO_COMMIT_SETTINGS: tuple[bool, ...] = (True, False)

_MatrixCell = tuple[_Scenario, str, bool]

_MATRIX_CELLS: tuple[_MatrixCell, ...] = tuple(
    (scenario, topology, auto_commit)
    for scenario in _SCENARIOS
    for topology in _TOPOLOGIES
    for auto_commit in _AUTO_COMMIT_SETTINGS
)
# Pinned per the T067 validation checklist: the count is the DOCUMENTED
# product of the dimension sizes above, so an added scenario/topology/
# auto-commit value changes this number visibly rather than silently.
assert len(_MATRIX_CELLS) == 3 * 2 * 2 == 12  # golden-count: cardinality-is-contract

_DURABLE_CELLS: tuple[_MatrixCell, ...] = tuple(
    cell for cell in _MATRIX_CELLS if cell[1] == "single_branch" and cell[2] is True
)
assert len(_DURABLE_CELLS) == 3  # golden-count: cardinality-is-contract

_INSULATED_CELLS: tuple[_MatrixCell, ...] = tuple(
    cell for cell in _MATRIX_CELLS if cell not in _DURABLE_CELLS
)
assert len(_INSULATED_CELLS) == 9  # golden-count: cardinality-is-contract


def _cell_id(cell: _MatrixCell) -> str:
    scenario, topology, auto_commit = cell
    ac = "auto_commit" if auto_commit else "no_auto_commit"
    return f"{scenario.scenario_id}-{topology}-{ac}"


# ---------------------------------------------------------------------------
# Shared fixture + driver helpers
# ---------------------------------------------------------------------------


def _seed_fixture(
    repo: Path,
    mission: str,
    wp_id: str,
    *,
    old_lane: str,
    seed_rejected_cycle: bool,
) -> Path:
    """Real git repo + WP + status-event seed shared by every matrix cell.

    EVERY cell needs a real ``git init`` regardless of Fake/Real router: the
    production writer (``_allocate_and_write_review_cycle_locked``) always
    acquires ``feature_status_lock``, an inter-process ``FileLock`` keyed
    under the real git common dir (``status/locking.py``) -- there is no way
    to exercise that seam against a non-git ``tmp_path``. This matches the
    house pattern already established in ``test_move_task_durability.py``
    (whose helpers this module reuses below rather than duplicating).
    """
    _init_repo(repo)
    feature_dir, _wp_file = _build_wp_file(repo, mission, wp_id)
    _write_lanes_json(feature_dir, mission, wp_id)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "seed"], cwd=repo, check=True, capture_output=True
    )
    _unprotect_main(repo)
    if seed_rejected_cycle:
        created = create_rejected_review_cycle(
            main_repo_root=repo,
            mission_slug=mission,
            wp_id=wp_id,
            wp_slug=f"{wp_id}-test",
            body=_SEED_FEEDBACK_BODY,
            reviewer_agent="reviewer-matrix",
            verdict="rejected",
            commit_router=None,  # uncommitted seed -- the production "prior rejection" shape
        )
        # WP05 (verdict-seam-write-unification-01KZ9Q35, T023): the writer's
        # own "is the current verdict a rejection" probe
        # (``_persist_approved_review_cycle``) is now event-sourced -- seed
        # the SAME ``review_result`` the real writer produces as a durable
        # event, not just the on-disk artifact above. Appended BEFORE the
        # ``old_lane`` seed event below (never after): ``_mt_current_event_
        # lane`` picks the LAST event IN FILE ORDER for wp_id as "current" --
        # this must stay the historical rejection's PREDECESSOR, not its
        # successor, or production code reads the WP's current lane as
        # ``in_progress`` (this event's own to_lane) instead of ``old_lane``.
        append_event(
            feature_dir,
            StatusEvent(
                event_id=f"test-{wp_id}-seed-rejection-event",
                mission_slug=mission,
                wp_id=wp_id,
                from_lane=Lane.IN_REVIEW,
                to_lane=Lane.IN_PROGRESS,
                at="2025-12-31T00:00:00+00:00",
                actor="reviewer-matrix",
                force=False,
                execution_mode="worktree",
                review_result=created.review_result,
            ),
        )
    _seed_wp_event(feature_dir, wp_id, old_lane, seq=0)
    return feature_dir


#: ``_build_wp_file`` (imported from ``test_move_task_durability.py``) always
#: seeds this fixed mission_id into ``meta.json`` -- reused here so
#: ``lanes.json`` names the SAME identity, matching the production shape
#: ``mission_finalize`` would have written.
_FIXTURE_MISSION_ID = "01HQZZZZZZZZZZZZZZZZZZZZZZ"


def _write_lanes_json(feature_dir: Path, mission: str, wp_id: str) -> None:
    """Minimal, schema-valid ``lanes.json`` (mirrors ``coord_topology_
    fixture._write_lanes_json``'s shape) -- required for the ``done`` target
    lane: ``_mt_done_ancestry_facts`` calls ``resolve_workspace_for_wp``,
    which raises the (uncaught-by-design) ``MissingLanesError`` when no
    ``lanes.json`` exists at all (distinct from the caught ``FileNotFoundError``
    a present-but-nonexistent-worktree resolution raises)."""
    payload = {
        "version": 1,
        "mission_slug": mission,
        "mission_id": _FIXTURE_MISSION_ID,
        "mission_branch": f"kitty/mission-{mission}",
        "target_branch": "main",
        "lanes": [
            {
                "lane_id": "lane-a",
                "wp_ids": [wp_id],
                "write_scope": [],
                "predicted_surfaces": [],
                "depends_on_lanes": [],
                "parallel_group": 0,
            }
        ],
        "computed_at": "2026-01-01T00:00:00+00:00",
        "computed_from": "durability-matrix-fixture",
        "planning_artifact_wps": [],
    }
    (feature_dir / "lanes.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _wp_dir(repo: Path, mission: str, wp_id: str) -> Path:
    return repo / "kitty-specs" / mission / "tasks" / f"{wp_id}-test"


def _assert_body_matches_scenario_verdict(body: str, verdict: str, *, cell: str) -> None:
    """Assert *body* is shaped the way the write path for *verdict* produces
    it (WP06 successor for a removed ``.verdict`` check -- see callers'
    comments for why neither the artifact field nor an event-sourced read is
    available at these particular call sites). ``"approved"`` bodies always
    start with ``"Approved by "`` (:func:`_persist_approved_review_cycle`'s
    own synthesized body); a rejection's body is real reviewer prose and
    never starts that way.
    """
    if verdict == "approved":
        assert body.startswith("Approved by "), (
            f"cell {cell}: expected an 'Approved by ...' body for verdict={verdict!r}, "
            f"got: {body!r}"
        )
    else:
        assert not body.startswith("Approved by "), (
            f"cell {cell}: expected reviewer-prose body for verdict={verdict!r}, "
            f"got an approval-shaped body: {body!r}"
        )


def _assert_committed_frontmatter_has_no_verdict_key(frontmatter_and_body: str) -> None:
    """SC-007 (WP06, FR-003): the REAL committed ``.md`` blob carries no
    ``verdict:`` frontmatter key. Several sites in this file used to assert
    the OPPOSITE (``"verdict: approved"``/``"verdict: rejected"`` present in
    the committed blob) as circumstantial evidence the write landed with the
    expected content -- that assertion is now categorically wrong (the field
    no longer exists), so every one of those sites now asserts its structural
    absence instead, on the SAME real committed git blob."""
    frontmatter = frontmatter_and_body.split("---", 2)[1]
    keys = {
        line.split(":", 1)[0].strip()
        for line in frontmatter.splitlines()
        if line and not line.startswith((" ", "\t", "-"))
    }
    assert "verdict" not in keys, (
        f"committed review-cycle blob must carry no verdict key, found keys "
        f"{sorted(keys)} in:\n{frontmatter_and_body}"
    )


def _run_cell(
    repo: Path,
    *,
    mission: str,
    wp_id: str,
    to: str,
    router: FakeCoordCommitRouter,
    auto_commit: bool,
    skip_target_branch_commit: bool,
    review_feedback_file: Path | None = None,
    note: str | None = None,
    done_override_reason: str | None = None,
    force: bool = False,
) -> None:
    """Drive the REAL ``_do_move_task`` orchestrator (the same entry point
    ``test_move_task_approval_body_collision.py`` and ``test_move_task_
    durability.py`` already establish as the house "real command surface"
    drive), never a hand-assembled call to an internal writer directly.
    """
    ports = TasksPorts(
        fs=FakeFsReader(default_planning_dir=repo / "kitty-specs" / mission),
        coord=router,
        git=FakeGitOps(),
        render=FakeRender(),
    )
    extra_patches = dict(_REVIEW_GATE_BYPASS)
    extra_patches["_skip_target_branch_commit"] = skip_target_branch_commit
    with setup_mocked_env(
        repo,
        mission_slug=mission,
        target_branch="main",
        extra_patches=extra_patches,
    ):
        _do_move_task(
            _MoveTaskArgs(
                task_id=wp_id,
                to=to,
                mission=mission,
                agent=None,
                assignee=None,
                shell_pid=None,
                note=note,
                review_feedback_file=review_feedback_file,
                approval_ref=None,
                reviewer=None,
                self_review_fallback=False,
                intended_reviewer=None,
                reviewer_failure_reason=None,
                done_override_reason=done_override_reason,
                force=force,
                tracker_ref=None,
                skip_review_artifact_check=False,
                auto_commit=auto_commit,
                json_output=True,
            ),
            ports=ports,
        )


def _last_json_payload(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    out = capsys.readouterr().out.strip()
    last_line = out.splitlines()[-1]
    payload: dict[str, Any] = json.loads(last_line)
    return payload


def _drive_scenario(
    repo: Path,
    *,
    mission: str,
    wp_id: str,
    scenario: _Scenario,
    router: FakeCoordCommitRouter,
    auto_commit: bool,
    skip_target_branch_commit: bool,
) -> None:
    """Build the scenario-specific ``_run_cell`` call (the feedback file for a
    rollback, the done-override-reason for a DONE target)."""
    if scenario.target_lane == "planned":
        feedback = repo / "feedback.md"
        feedback.write_text(
            "**Issue**: the matrix's rejection feedback.\n", encoding="utf-8"
        )
        _run_cell(
            repo,
            mission=mission,
            wp_id=wp_id,
            to="planned",
            router=router,
            auto_commit=auto_commit,
            skip_target_branch_commit=skip_target_branch_commit,
            review_feedback_file=feedback,
        )
        return
    done_override = (
        "matrix cell: bypass merge-ancestry check" if scenario.target_lane == "done" else None
    )
    # ``_guard_unsupported_skip_metadata`` refuses a coord-protected commit
    # that ALSO carries a ``note`` (frontmatter activity-log write, which the
    # skip arm cannot land) -- omit it under that topology and rely on
    # ``_mt_approval_facts``'s own ``auto-approval:<wp>:<date>`` default
    # reference instead of reproducing that guard's refusal here.
    note = None if skip_target_branch_commit else "Review passed"
    _run_cell(
        repo,
        mission=mission,
        wp_id=wp_id,
        to=scenario.target_lane,
        router=router,
        auto_commit=auto_commit,
        skip_target_branch_commit=skip_target_branch_commit,
        note=note,
        done_override_reason=done_override,
    )


# ---------------------------------------------------------------------------
# T067 -- the 12-cell matrix through the real command surface
# ---------------------------------------------------------------------------


@pytest.mark.fast
@pytest.mark.parametrize("cell", _MATRIX_CELLS, ids=[_cell_id(c) for c in _MATRIX_CELLS])
def test_durability_matrix_cell(
    tmp_path: Path, cell: _MatrixCell, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every one of the 12 documented cells: durability behaves as specified,
    and every assertion is specific to what THAT cell's own dimensions imply
    (never a shared "no exception raised" catch-all)."""
    scenario, topology, auto_commit = cell
    repo = tmp_path
    seed_rejected = scenario.verdict == "approved"
    feature_dir = _seed_fixture(
        repo, _MISSION, _WP_ID, old_lane="in_review", seed_rejected_cycle=seed_rejected
    )
    wp_dir = _wp_dir(repo, _MISSION, _WP_ID)
    router = FakeCoordCommitRouter(write_dir=feature_dir)
    skip_target_branch_commit = topology == "coord_protected"
    expected_durable = auto_commit and not skip_target_branch_commit

    _drive_scenario(
        repo,
        mission=_MISSION,
        wp_id=_WP_ID,
        scenario=scenario,
        router=router,
        auto_commit=auto_commit,
        skip_target_branch_commit=skip_target_branch_commit,
    )

    payload = _last_json_payload(capsys)
    assert payload["verdict_durably_persisted"] is expected_durable, payload
    if expected_durable:
        assert "verdict_durability_skip_reason" not in payload, payload
    else:
        expected_reason = (
            _REASON_NO_AUTO_COMMIT if not auto_commit else _REASON_PROTECTED_TARGET_BRANCH
        )
        assert payload["verdict_durability_skip_reason"] == expected_reason, payload

    latest = ReviewCycleArtifact.latest(wp_dir)
    assert latest is not None, f"cell {_cell_id(cell)}: expected a written review-cycle artifact"
    # WP06 (FR-003/SC-007): ``ReviewCycleArtifact`` no longer carries a
    # ``verdict`` field, and this cell's own mocked harness (``setup_mocked_
    # env``/``_REVIEW_GATE_BYPASS``) deliberately does not append a review_
    # result event for this hop either (it isolates the review-cycle
    # WRITER's own behaviour, not the full transition-emit machinery -- see
    # ``test_uncommitted_rejection_is_visible_to_the_immediately_following_
    # approval``'s own comment for the identical, already-documented
    # limitation) -- so neither successor authority is populated here. The
    # BODY content the two write paths produce is genuinely distinct
    # (``_persist_approved_review_cycle`` always starts with "Approved by ",
    # the rejection path never does), so it is the correct, still-checkable
    # proxy for "which scenario actually wrote this".
    _assert_body_matches_scenario_verdict(latest.body, scenario.verdict, cell=_cell_id(cell))

    if expected_durable:
        assert len(router.artifact_calls) == 1, (
            f"cell {_cell_id(cell)}: expected exactly one commit_artifact call, "
            f"got {router.artifact_calls}"
        )
    else:
        assert router.artifact_calls == [], (
            f"cell {_cell_id(cell)}: durability signal reported non-durable "
            f"but commit_artifact was still invoked ({router.artifact_calls}) -- "
            "the skip must prevent the ATTEMPT, not merely mis-report it"
        )


# ---------------------------------------------------------------------------
# T068 -- the committed, automated mutation (non-vacuity) proof
# ---------------------------------------------------------------------------


@pytest.mark.fast
@pytest.mark.parametrize("cell", _DURABLE_CELLS, ids=[_cell_id(c) for c in _DURABLE_CELLS])
def test_matrix_is_sensitive_to_commit_removal(
    tmp_path: Path, cell: _MatrixCell, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    """WP05 (verdict-seam-write-unification-01KZ9Q35, T026/D-PLAN-11)
    INVERTS this test's former premise: before WP05, neutering
    ``commit_artifact`` turned the cell red (a hard ``ReviewCycleError``) --
    that was FR-015's own non-vacuity proof for the THEN-authoritative
    ``.md`` commit. T026 DEMOTES that commit to best-effort: the SAME
    mutation must now leave the command SUCCEEDING (exit 0) with a logged
    WARNING, never a hard failure -- the authoritative durable act is the
    event-sourced ``review_result`` append (``emit_status_transition``),
    which this neutered router does not touch at all. A cell that still
    fails here would mean the demote did not actually land."""
    scenario, topology, auto_commit = cell
    assert topology == "single_branch" and auto_commit is True  # documents the subset

    repo = tmp_path
    seed_rejected = scenario.verdict == "approved"
    feature_dir = _seed_fixture(
        repo, _MISSION, _WP_ID, old_lane="in_review", seed_rejected_cycle=seed_rejected
    )

    router = FakeCoordCommitRouter(write_dir=feature_dir)
    # The documented no-op mutation -- ``commit_artifact`` neutered to report
    # "unchanged" without ever performing a commit.
    router.commit_artifact = (  # type: ignore[method-assign]
        lambda *args, **kwargs: CommitArtifactResult(
            status="unchanged", placement_ref="primary"
        )
    )

    with caplog.at_level("WARNING", logger="specify_cli.review.cycle"):
        _drive_scenario(
            repo,
            mission=_MISSION,
            wp_id=_WP_ID,
            scenario=scenario,
            router=router,
            auto_commit=True,
            skip_target_branch_commit=False,
        )

    payload = _last_json_payload(capsys)
    assert payload.get("result") == "success", (
        f"cell {_cell_id(cell)}: a neutered (best-effort) commit_artifact "
        f"must not fail the command post-demote, got {payload}"
    )
    # The best-effort failure is still LOGGED (never silently swallowed) --
    # ``review/cycle.py::_commit_review_cycle_artifact``'s own
    # ``logger.warning`` call (T026).
    assert any("Failed to commit review-cycle" in r.message for r in caplog.records), (
        f"cell {_cell_id(cell)}: a best-effort commit failure must still be "
        f"logged as a WARNING, never silently dropped; records={caplog.records}"
    )


@pytest.mark.fast
@pytest.mark.parametrize("cell", _INSULATED_CELLS, ids=[_cell_id(c) for c in _INSULATED_CELLS])
def test_protected_and_no_auto_commit_cells_never_invoke_commit_artifact(
    tmp_path: Path, cell: _MatrixCell, capsys: pytest.CaptureFixture[str]
) -> None:
    """The other half of T068's edge case: for the 9 cells where
    ``auto_commit=False`` or the topology is ``coord_protected``, the skip
    gate (``_resolve_verdict_commit_router``) must prevent ``commit_artifact``
    from EVER being called -- so mutating it cannot and must not flip these
    cells (they are already non-durable BY DESIGN, not by a working commit
    that happens to succeed). Pinned here as an explicit regression guard
    rather than left as an unstated assumption, per the WP prompt's own edge
    case: "confirm the monkeypatch does not accidentally make an unrelated
    auto_commit=False cell's assertion fail too"."""
    scenario, topology, auto_commit = cell
    repo = tmp_path
    seed_rejected = scenario.verdict == "approved"
    feature_dir = _seed_fixture(
        repo, _MISSION, _WP_ID, old_lane="in_review", seed_rejected_cycle=seed_rejected
    )
    router = FakeCoordCommitRouter(write_dir=feature_dir)
    router.commit_artifact = (  # type: ignore[method-assign]
        lambda *args, **kwargs: CommitArtifactResult(
            status="unchanged", placement_ref="primary"
        )
    )
    skip_target_branch_commit = topology == "coord_protected"

    _drive_scenario(
        repo,
        mission=_MISSION,
        wp_id=_WP_ID,
        scenario=scenario,
        router=router,
        auto_commit=auto_commit,
        skip_target_branch_commit=skip_target_branch_commit,
    )

    payload = _last_json_payload(capsys)
    assert payload["verdict_durably_persisted"] is False, payload
    assert router.artifact_calls == [], (
        f"cell {_cell_id(cell)}: commit_artifact was invoked even though this "
        "cell is supposed to skip the attempt entirely -- the mutation should "
        "be irrelevant to (and must not have altered) this outcome"
    )


# ---------------------------------------------------------------------------
# Edge case (T067): an uncommitted --no-auto-commit rejection must still be
# the "latest verdict" the very next approval attempt on the same WP reads.
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_uncommitted_rejection_is_visible_to_the_immediately_following_approval(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = tmp_path
    feature_dir = _seed_fixture(
        repo, _MISSION, _WP_ID, old_lane="in_review", seed_rejected_cycle=False
    )
    wp_dir = _wp_dir(repo, _MISSION, _WP_ID)

    feedback = repo / "feedback.md"
    feedback.write_text("**Issue**: needs work, --no-auto-commit.\n", encoding="utf-8")
    router1 = FakeCoordCommitRouter(write_dir=feature_dir)
    _run_cell(
        repo,
        mission=_MISSION,
        wp_id=_WP_ID,
        to="planned",
        router=router1,
        auto_commit=False,
        skip_target_branch_commit=False,
        review_feedback_file=feedback,
    )
    payload1 = _last_json_payload(capsys)
    assert payload1["verdict_durably_persisted"] is False
    assert payload1["verdict_durability_skip_reason"] == _REASON_NO_AUTO_COMMIT
    latest_after_reject = ReviewCycleArtifact.latest(wp_dir)
    # No event-sourced review_result exists yet at this point (the comment
    # below explains why -- the mocked harness bypasses the real emit layer
    # for this rejection hop), so the WP06-successor check cannot be the
    # event authority here (unlike every other site in this file). The
    # artifact itself no longer carries a ``verdict`` field either (FR-003/
    # SC-007) -- the genuinely-checkable property at this point is that the
    # WRITE actually happened and carries the reviewer's real feedback body,
    # not a fabricated/wrong one.
    assert latest_after_reject is not None
    assert "needs work" in latest_after_reject.body
    # Genuinely uncommitted -- not merely "reported" as such (the WP's own
    # ``tasks/<wp>/`` dir is untracked-as-a-whole, so ``git status`` collapses
    # it to a single directory line rather than naming the file -- assert on
    # HEAD readability instead, the same idiom WP11's own durability tests use).
    rel = f"kitty-specs/{_MISSION}/tasks/{_WP_ID}-test/review-cycle-1.md"
    assert not _git_head_has_file(repo, rel), "the rejection must NOT be committed at HEAD"

    # Immediately re-open for review and approve -- the ordinary reject->approve
    # flow the rejection's own uncommitted state must not break.
    #
    # WP05 (verdict-seam-write-unification-01KZ9Q35, T023): the writer's own
    # "is the current verdict a rejection" probe is now event-sourced. This
    # test's mocked harness (``setup_mocked_env``'s ``_REVIEW_GATE_BYPASS``)
    # deliberately stubs out the transactional emit layer to isolate the
    # review-cycle WRITER's own behaviour, so step 1's rejection above never
    # appended a real ``review_result`` event (confirmed: only the seed event
    # exists on disk afterward) -- seed it explicitly here, mirroring what the
    # UNMOCKED production ``_mt_hop_review_result`` wiring records for a real
    # ``in_review -> planned`` rejection hop.
    append_event(
        feature_dir,
        StatusEvent(
            event_id=f"test-{_WP_ID}-rejection-review-result",
            mission_slug=_MISSION,
            wp_id=_WP_ID,
            from_lane=Lane.IN_REVIEW,
            to_lane=Lane.PLANNED,
            at="2026-01-01T00:00:30+00:00",
            actor="test",
            force=False,
            execution_mode="worktree",
            review_result=ReviewResult(
                reviewer="test",
                verdict="changes_requested",
                reference=f"review-cycle://{_MISSION}/{_WP_ID}-test/review-cycle-1.md",
            ),
        ),
    )
    _seed_wp_event(feature_dir, _WP_ID, "in_review", seq=1)
    router2 = FakeCoordCommitRouter(write_dir=feature_dir)
    _run_cell(
        repo,
        mission=_MISSION,
        wp_id=_WP_ID,
        to="approved",
        router=router2,
        auto_commit=True,
        skip_target_branch_commit=False,
        note="Review passed",
    )
    payload2 = _last_json_payload(capsys)
    assert payload2["verdict_durably_persisted"] is True
    latest_after_approve = ReviewCycleArtifact.latest(wp_dir)
    assert latest_after_approve is not None
    assert latest_after_approve.body.startswith("Approved by "), (
        f"expected an 'Approved by ...' body after the approval hop, "
        f"got: {latest_after_approve.body!r}"
    )


# ---------------------------------------------------------------------------
# Arbiter override -- a SEPARATE, smaller matrix (event-sourced durability,
# not commit_artifact-based; see the module docstring for why it is not
# folded into the 12-cell parametrization above).
# ---------------------------------------------------------------------------


def _seed_arbiter_fixture(repo: Path, mission: str, wp_id: str) -> Path:
    """A WP that went for_review -> planned via an explicit, on-disk rejected
    review-cycle-1.md (uncommitted) -- the precondition an arbiter override
    supersedes. Mirrors ``test_tasks_cli_contract_coord.py``'s
    ``arbiter_override_to_approved`` scenario recipe (the established house
    pattern for this exact shape) rather than inventing a second one."""
    _init_repo(repo)
    feature_dir, _wp_file = _build_wp_file(repo, mission, wp_id)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "seed"], cwd=repo, check=True, capture_output=True
    )
    _unprotect_main(repo)
    chain: Sequence[tuple[str, str]] = (
        ("planned", "claimed"),
        ("claimed", "in_progress"),
        ("in_progress", "for_review"),
    )
    for seq, (from_lane, to_lane) in enumerate(chain, start=1):
        append_event(
            feature_dir,
            StatusEvent(
                event_id=f"arb-matrix-{seq}",
                mission_slug=mission,
                wp_id=wp_id,
                from_lane=Lane(from_lane),
                to_lane=Lane(to_lane),
                at=f"2026-01-01T00:00:0{seq}+00:00",
                actor="test",
                force=True,
                execution_mode="worktree",
            ),
        )
    append_event(
        feature_dir,
        StatusEvent(
            event_id="arb-matrix-4",
            mission_slug=mission,
            wp_id=wp_id,
            from_lane=Lane.FOR_REVIEW,
            to_lane=Lane.PLANNED,
            at="2026-01-01T00:00:04+00:00",
            actor="test",
            force=True,
            execution_mode="worktree",
            review_ref=f"feedback://arbiter/{wp_id}/review-cycle-1.md",
        ),
    )
    create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug=mission,
        wp_id=wp_id,
        wp_slug=f"{wp_id}-test",
        body=_SEED_FEEDBACK_BODY,
        reviewer_agent="reviewer-matrix",
        verdict="rejected",
        commit_router=None,
    )
    return feature_dir


@pytest.mark.fast
@pytest.mark.parametrize("auto_commit", _AUTO_COMMIT_SETTINGS, ids=["auto_commit", "no_auto_commit"])
def test_arbiter_override_cell_suppresses_fabricated_approval(
    tmp_path: Path, auto_commit: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    """T055/FR-011 (WP12) re-verified through THIS WP's own matrix harness:
    an arbiter override targeting ``approved`` must record the ``ReviewOverride``
    (event-sourced) and must NOT also fabricate a fresh ``verdict: approved``
    review-cycle artifact. Durability here rides on ``commit_status`` (the
    status-transition commit), not ``commit_artifact`` -- so this cell
    correctly reports NEITHER of the ``verdict_durably_persisted``/
    ``verdict_durability_skip_reason`` keys at all (there is no review-cycle
    write for `_mt_output` to describe)."""
    repo = tmp_path
    mission = "arbiter-matrix"
    feature_dir = _seed_arbiter_fixture(repo, mission, _WP_ID)
    router = FakeCoordCommitRouter(write_dir=feature_dir)

    _run_cell(
        repo,
        mission=mission,
        wp_id=_WP_ID,
        to="approved",
        router=router,
        auto_commit=auto_commit,
        skip_target_branch_commit=False,
        note="arbiter release: matrix override",
        force=True,
    )
    payload = _last_json_payload(capsys)
    assert "verdict_durably_persisted" not in payload, payload
    assert "verdict_durability_skip_reason" not in payload, payload

    wp_dir = _wp_dir(repo, mission, _WP_ID)
    cycle_artifacts = sorted(p.name for p in wp_dir.glob("review-cycle-*.md"))
    assert cycle_artifacts == ["review-cycle-1.md"], (
        "an arbiter override must not ALSO write a fresh approved review-cycle "
        f"artifact; got {cycle_artifacts}"
    )

    snapshot = _materialize(feature_dir)
    override = snapshot.work_packages.get(_WP_ID, {}).get("review") or {}
    assert override.get("wp_id") == _WP_ID
    assert override.get("actor"), "override must carry a non-empty actor"
    assert "matrix override" in override.get("reason", "")


@pytest.mark.fast
def test_arbiter_override_is_sensitive_to_its_own_commit_removal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T068's mutation proof, scoped correctly to the arbiter cell's OWN
    durability mechanism (``persist_arbiter_decision``, not ``commit_
    artifact`` -- see this module's docstring). Neutering the persist call to
    a no-op that performs no write must leave the review-override slot
    genuinely empty -- proving the assertion above (not merely "no exception")
    is what would catch the commit call being deleted.

    Patched at the POINT OF USE (``tasks_move_task``'s own module-scope
    ``from ... import persist_arbiter_override_decision``), not at
    ``tasks_verdict_persistence`` (the origin module) -- a ``from X import
    name`` binds the name in the IMPORTING module's namespace at import time,
    so patching the origin module's attribute afterwards would not intercept
    the call ``_run_arbiter_override`` actually makes (research.md D1/D7's
    documented seam-bridge convention this codebase uses throughout)."""
    from specify_cli.cli.commands.agent import tasks_move_task as _tmt

    repo = tmp_path
    mission = "arbiter-matrix-mutation"
    feature_dir = _seed_arbiter_fixture(repo, mission, _WP_ID)
    router = FakeCoordCommitRouter(write_dir=feature_dir)

    def _neutered(**kwargs: object) -> None:
        # The documented no-op shape: skip straight past the real
        # ``persist_arbiter_decision`` call this function would otherwise
        # make -- simulating the commit call having been deleted from
        # production code. Performs NO event append/commit at all.
        del kwargs

    monkeypatch.setattr(_tmt, "persist_arbiter_override_decision", _neutered)
    _run_cell(
        repo,
        mission=mission,
        wp_id=_WP_ID,
        to="approved",
        router=router,
        auto_commit=True,
        skip_target_branch_commit=False,
        note="arbiter release: matrix override",
        force=True,
    )

    snapshot = _materialize(feature_dir)
    override = snapshot.work_packages.get(_WP_ID, {}).get("review") or {}
    assert override == {}, (
        "expected the review-override slot to be EMPTY once the persist call "
        f"is neutered (proving the assertion catches a deleted commit call); "
        f"got {override!r}"
    )


# ---------------------------------------------------------------------------
# T069a -- real CoordCommitRouter, real git: the non-fakeable durability proof
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.git_repo
def test_real_router_commit_lands_on_disk_and_git_history(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T069: at least one cell runs the REAL ``CoordCommitRouter``
    (``RealCoordCommitRouter``, wrapped by ``test_move_task_durability.py``'s
    established ``_FaultInjectableCoordRouter`` so the transition-emit leg
    stays independently controllable) against a real, git-initialised repo,
    and asserts on ACTUAL git state -- never a fake's in-memory call log
    dressed up to look real."""
    repo = tmp_path
    feature_dir = _seed_fixture(
        repo, _MISSION, _WP_ID, old_lane="in_review", seed_rejected_cycle=True
    )
    router = _FaultInjectableCoordRouter(write_dir=feature_dir)
    ports = TasksPorts(
        fs=FakeFsReader(default_planning_dir=repo / "kitty-specs" / _MISSION),
        coord=router,
        git=FakeGitOps(),
        render=FakeRender(),
    )
    extra_patches = dict(_REVIEW_GATE_BYPASS)
    extra_patches["_skip_target_branch_commit"] = False
    with setup_mocked_env(
        repo, mission_slug=_MISSION, target_branch="main", extra_patches=extra_patches
    ):
        _do_move_task(
            _MoveTaskArgs(
                task_id=_WP_ID,
                to="approved",
                mission=_MISSION,
                agent=None,
                assignee=None,
                shell_pid=None,
                note="Review passed",
                review_feedback_file=None,
                approval_ref=None,
                reviewer=None,
                self_review_fallback=False,
                intended_reviewer=None,
                reviewer_failure_reason=None,
                done_override_reason=None,
                force=False,
                tracker_ref=None,
                skip_review_artifact_check=False,
                auto_commit=True,
                json_output=True,
            ),
            ports=ports,
        )

    payload = _last_json_payload(capsys)
    assert payload["verdict_durably_persisted"] is True

    rel = f"kitty-specs/{_MISSION}/tasks/{_WP_ID}-test/review-cycle-2.md"
    assert _git_head_has_file(repo, rel), "the real commit never reached HEAD"
    status = _git_status(repo)
    assert "review-cycle-2.md" not in status, f"expected a clean tree after a real commit:\n{status}"

    show = subprocess.run(
        ["git", "show", f"HEAD:{rel}"], cwd=repo, capture_output=True, text=True
    )
    assert show.returncode == 0
    assert "Approved by" in show.stdout  # sanity: real body/content landed
    _assert_committed_frontmatter_has_no_verdict_key(show.stdout)


@pytest.mark.integration
@pytest.mark.git_repo
def test_real_router_cell_reds_when_commit_artifact_is_neutered(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    """WP05 (verdict-seam-write-unification-01KZ9Q35, T026/D-PLAN-11)
    INVERTS this test's former premise (see ``test_matrix_is_sensitive_to_
    commit_removal`` for the identical rationale): the ``.md`` commit is now
    best-effort, so a neutered ``commit_artifact`` no longer fails the
    command against the REAL router either -- it succeeds, warns, and the
    event-sourced transition (this router's ``commit_status`` leg, left
    UNCHANGED here) still lands normally."""
    repo = tmp_path
    feature_dir = _seed_fixture(
        repo, _MISSION, _WP_ID, old_lane="in_review", seed_rejected_cycle=True
    )

    router = _FaultInjectableCoordRouter(write_dir=feature_dir)
    router.commit_artifact = (  # type: ignore[method-assign]
        lambda *args, **kwargs: CommitArtifactResult(
            status="unchanged", placement_ref="primary"
        )
    )
    ports = TasksPorts(
        fs=FakeFsReader(default_planning_dir=repo / "kitty-specs" / _MISSION),
        coord=router,
        git=FakeGitOps(),
        render=FakeRender(),
    )
    extra_patches = dict(_REVIEW_GATE_BYPASS)
    extra_patches["_skip_target_branch_commit"] = False
    with (
        setup_mocked_env(
            repo, mission_slug=_MISSION, target_branch="main", extra_patches=extra_patches
        ),
        caplog.at_level("WARNING", logger="specify_cli.review.cycle"),
    ):
        _do_move_task(
            _MoveTaskArgs(
                task_id=_WP_ID,
                to="approved",
                mission=_MISSION,
                agent=None,
                assignee=None,
                shell_pid=None,
                note="Review passed",
                review_feedback_file=None,
                approval_ref=None,
                reviewer=None,
                self_review_fallback=False,
                intended_reviewer=None,
                reviewer_failure_reason=None,
                done_override_reason=None,
                force=False,
                tracker_ref=None,
                skip_review_artifact_check=False,
                auto_commit=True,
                json_output=True,
            ),
            ports=ports,
        )

    payload = _last_json_payload(capsys)
    assert payload.get("result") == "success", (
        f"a neutered (best-effort) commit_artifact must not fail the real-router "
        f"cell post-demote, got {payload}"
    )
    assert any("Failed to commit review-cycle" in r.message for r in caplog.records), (
        "best-effort commit failure must still be logged, never silently dropped"
    )


# ---------------------------------------------------------------------------
# T069c -- the REAL coord-topology cell (adversarial-review finding: the
# "topology" axis in the 12-cell matrix above is a directly-patched
# ``_skip_target_branch_commit`` boolean, not a real coord worktree -- every
# one of those 12 cells is a SINGLE_BRANCH repo under the hood. WP04's
# ``REVIEW_CYCLE`` routing makes topology load-bearing for durability (it
# changes which git REF the commit lands on, not merely whether a commit is
# attempted), so that dimension needs its OWN genuine coverage, not a second
# coat of the skip-gate proof above. Built on the canonical, un-stubbed
# ``coord_topology_fixture.py`` (``_build_coord_topology``) -- NOT a
# hand-rolled second coord fixture, per the reviewer's explicit instruction.
# ---------------------------------------------------------------------------


def _seed_coord_wp_in_review(ctx: CoordTopologyContext, wp_id: str) -> None:
    """Replace the base fixture's own seed event (a resolver-smoke marker
    event, not meant to be read by the real reducer -- see ``coord_topology_
    fixture.py``'s module docstring) with a single, real, force-seeded
    ``in_review`` event on the COORD husk -- the same single-event seed shape
    every other cell in this file uses (``_seed_wp_event``), just written to
    the coord husk's event log instead of a flat mission's."""
    ctx.status_events_path.unlink()
    _seed_wp_event(ctx.coord_feature_dir, wp_id, "in_review", seq=0)


def _disable_branch_protection_for_coord_cell(repo: Path) -> None:
    """Unprotect ``main`` so the ordinary (non-skip-arm) commit path runs --
    mirrors ``tests/coordination/test_analysis_report_rehome.py``'s
    ``_disable_branch_protection`` (a few lines, reproduced rather than
    cross-imported from a `tests/coordination/` module this file has no other
    dependency on)."""
    config = repo / ".kittify" / "config.yaml"
    config.write_text("protection:\n  protected_branches: []\n", encoding="utf-8")
    subprocess.run(["git", "add", ".kittify/config.yaml"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "test: unprotect main for the coord durability cell"],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _coord_cell_ports(ctx: CoordTopologyContext, router: _FaultInjectableCoordRouter) -> TasksPorts:
    return TasksPorts(
        fs=FakeFsReader(default_planning_dir=ctx.primary_feature_dir),
        coord=router,
        git=FakeGitOps(),
        render=FakeRender(),
    )


def _run_coord_cell_approval(
    ctx: CoordTopologyContext, *, wp_id: str, router: _FaultInjectableCoordRouter
) -> None:
    """Drive the REAL ``_do_move_task`` against the real coord fixture.

    Deliberately does NOT patch ``_skip_target_branch_commit`` (unlike every
    other cell in this file) -- this cell's entire point is to let the REAL
    resolver see the REAL coord worktree ``_build_coord_topology`` created, so
    the topology dimension is genuine, not simulated.
    """
    with setup_mocked_env(
        ctx.repo,
        mission_slug=ctx.slug,
        target_branch="main",
        extra_patches=dict(_REVIEW_GATE_BYPASS),
    ):
        _do_move_task(
            _MoveTaskArgs(
                task_id=wp_id,
                to="approved",
                mission=ctx.slug,
                agent=None,
                assignee=None,
                shell_pid=None,
                note="Review passed",
                review_feedback_file=None,
                approval_ref=None,
                reviewer=None,
                self_review_fallback=False,
                intended_reviewer=None,
                reviewer_failure_reason=None,
                done_override_reason=None,
                force=False,
                tracker_ref=None,
                skip_review_artifact_check=False,
                auto_commit=True,
                json_output=True,
            ),
            ports=_coord_cell_ports(ctx, router),
        )


def _seed_coord_rejected_cycle(ctx: CoordTopologyContext, wp_id: str) -> None:
    created = create_rejected_review_cycle(
        main_repo_root=ctx.repo,
        mission_slug=ctx.slug,
        wp_id=wp_id,
        wp_slug=wp_id,  # the fixture's WP file is literally ``tasks/WP01.md``
        body=_SEED_FEEDBACK_BODY,
        reviewer_agent="reviewer-matrix",
        verdict="rejected",
        commit_router=None,  # uncommitted seed, matching every other cell's precondition
    )
    # WP05 (verdict-seam-write-unification-01KZ9Q35, T023): seed the
    # event-sourced rejection the writer's probe now reads (see
    # ``_seed_fixture``'s identical rationale). Re-issues the ``in_review``
    # seed event AFTER this one so the LAST event in file order stays
    # ``in_review`` (``_mt_current_event_lane`` picks the last one) --
    # this function runs AFTER ``_seed_coord_wp_in_review`` at every call
    # site, so without the re-seed this rejection event would wrongly
    # become "current".
    append_event(
        ctx.coord_feature_dir,
        StatusEvent(
            event_id=f"test-{wp_id}-seed-rejection-event",
            mission_slug=ctx.slug,
            wp_id=wp_id,
            from_lane=Lane.IN_REVIEW,
            to_lane=Lane.IN_PROGRESS,
            at="2025-12-31T00:00:00+00:00",
            actor="reviewer-matrix",
            force=False,
            execution_mode="worktree",
            review_result=created.review_result,
        ),
    )
    _seed_wp_event(ctx.coord_feature_dir, wp_id, "in_review", seq=1)


def _coord_review_cycle_rel(ctx: CoordTopologyContext, wp_id: str, cycle: int) -> str:
    return f"kitty-specs/{ctx.slug}/tasks/{wp_id}/review-cycle-{cycle}.md"


def _git_show(repo: Path, ref: str, rel: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "show", f"{ref}:{rel}"], cwd=repo, capture_output=True, text=True
    )


@pytest.mark.integration
@pytest.mark.git_repo
def test_real_coord_topology_review_cycle_commits_to_coord_ref_not_primary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The genuine topology-dimension cell: a real coord worktree (not a
    patched ``skip_target_branch_commit`` boolean), driven through the real
    ``_do_move_task`` orchestrator with the REAL ``CoordCommitRouter``.
    Asserts on committed git TREES (``git show <ref>:<path>``), mirroring
    ``tests/coordination/test_analysis_report_rehome.py``'s placement idiom --
    the artifact must be reachable on the COORD ref and ABSENT on primary."""
    ctx = _build_coord_topology(tmp_path, write_husk_meta=False)
    _disable_branch_protection_for_coord_cell(ctx.repo)
    _seed_coord_wp_in_review(ctx, "WP01")
    _seed_coord_rejected_cycle(ctx, "WP01")

    router = _FaultInjectableCoordRouter(write_dir=ctx.coord_feature_dir)
    _run_coord_cell_approval(ctx, wp_id="WP01", router=router)

    payload = _last_json_payload(capsys)
    assert payload["verdict_durably_persisted"] is True

    rel = _coord_review_cycle_rel(ctx, "WP01", 2)
    coord_show = _git_show(ctx.repo, ctx.coord_branch, rel)
    assert coord_show.returncode == 0, (
        f"review-cycle-2.md is NOT on the coordination ref {ctx.coord_branch!r}: "
        f"{coord_show.stderr}"
    )
    _assert_committed_frontmatter_has_no_verdict_key(coord_show.stdout)

    primary_show = _git_show(ctx.repo, "main", rel)
    assert primary_show.returncode != 0, (
        "review-cycle-2.md WAS committed to the primary ref 'main' -- a stale "
        f"PRIMARY copy was left behind:\n{primary_show.stdout}"
    )


@pytest.mark.integration
@pytest.mark.git_repo
def test_real_coord_topology_cell_reds_when_commit_artifact_is_neutered(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    """WP05 (verdict-seam-write-unification-01KZ9Q35, T026/D-PLAN-11)
    INVERTS this test's former premise (see ``test_matrix_is_sensitive_to_
    commit_removal`` for the identical rationale), proven for the coord
    cell too: the ``.md`` commit is now best-effort, so a neutered
    ``commit_artifact`` no longer reds this cell -- it succeeds, warns, and
    the event-sourced transition (unaffected by this mutation) still lands
    on the coord ref normally."""
    ctx = _build_coord_topology(tmp_path, write_husk_meta=False)
    _disable_branch_protection_for_coord_cell(ctx.repo)
    _seed_coord_wp_in_review(ctx, "WP01")
    _seed_coord_rejected_cycle(ctx, "WP01")

    router = _FaultInjectableCoordRouter(write_dir=ctx.coord_feature_dir)
    router.commit_artifact = (  # type: ignore[method-assign]
        lambda *args, **kwargs: CommitArtifactResult(status="unchanged", placement_ref="primary")
    )
    with caplog.at_level("WARNING", logger="specify_cli.review.cycle"):
        _run_coord_cell_approval(ctx, wp_id="WP01", router=router)

    payload = _last_json_payload(capsys)
    assert payload.get("result") == "success", (
        f"a neutered (best-effort) commit_artifact must not fail the real "
        f"coord-topology cell post-demote, got {payload}"
    )
    assert any("Failed to commit review-cycle" in r.message for r in caplog.records), (
        "best-effort commit failure must still be logged, never silently dropped"
    )


@pytest.mark.integration
@pytest.mark.git_repo
def test_real_coord_topology_revert_deletes_and_commits_on_coord_ref(
    tmp_path: Path,
) -> None:
    """WP13's durability-matrix witness (DM-01KZ75GBNXC73Q38M43GBH38W7): a
    transition-emit failure AFTER a coord-topology verdict write already
    landed must be reverted on the SAME ref the original commit used (COORD),
    not primary -- the exact live bug WP13 fixed
    (``_resolve_revert_commit_worktree`` + ``kind=REVIEW_CYCLE`` in
    ``revert_committed_verdict_write``). Before WP13, this compensator tried
    to commit the deletion onto PRIMARY while the orphan verdict stayed
    fully readable on COORD -- this cell is the regression pin."""
    ctx = _build_coord_topology(tmp_path, write_husk_meta=False)
    _disable_branch_protection_for_coord_cell(ctx.repo)
    _seed_coord_wp_in_review(ctx, "WP01")
    _seed_coord_rejected_cycle(ctx, "WP01")

    rel = _coord_review_cycle_rel(ctx, "WP01", 2)
    router = _FaultInjectableCoordRouter(write_dir=ctx.coord_feature_dir, emit_should_fail=True)

    with pytest.raises(typer.Exit):
        _run_coord_cell_approval(ctx, wp_id="WP01", router=router)

    # The revert must undo the COORD commit -- no readable verdict at the
    # CURRENT tip of the coord ref.
    coord_show_after = _git_show(ctx.repo, ctx.coord_branch, rel)
    assert coord_show_after.returncode != 0, (
        f"review-cycle-2.md is STILL reachable at the coord ref {ctx.coord_branch!r} "
        f"tip after a reverted transition-emit failure -- WP13's revert-worktree "
        f"fix did not take effect:\n{coord_show_after.stdout}"
    )
    # It was never left on primary either (the original write never commits there).
    assert _git_show(ctx.repo, "main", rel).returncode != 0

    # The ORIGINAL commit still exists in history (a revert commit, not a
    # rewrite) -- mirrors test_move_task_durability.py's own idiom.
    log = subprocess.run(
        ["git", "-C", str(ctx.repo), "log", "--all", "--name-only", "--pretty=format:--COMMIT--"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "review-cycle-2.md" in log, (
        "the revert should be a NEW commit undoing the write, not a history "
        f"rewrite -- the original commit should still appear in git log:\n{log}"
    )

    # No readable committed verdict for this WP -- the reverted cycle-2 must
    # not be the reader-visible latest; the pre-existing rejected cycle-1 is.
    # (WP06, FR-003/SC-007: the artifact no longer carries a ``verdict``
    # field to read directly -- ``cycle_number`` is the checkable proxy for
    # "which write is the reader-visible latest", which is exactly what this
    # assertion is about: cycle-2's revert must not promote it over cycle-1.)
    latest = ReviewCycleArtifact.latest(ctx.primary_feature_dir / "tasks" / "WP01")
    assert latest is not None and latest.cycle_number == 1, (
        f"expected the pre-existing rejected cycle 1 to still be the reader-"
        f"visible latest after the coord-ref revert, got {latest!r}"
    )

    # Coord worktree's tasks/ dir is clean after the revert-commit (no
    # partially-reverted state) -- scoped to that subtree, not repo-wide: the
    # fixture's own ``status.events.jsonl`` under the coord husk is
    # deliberately left untracked by the builder (a different, unrelated
    # concern -- see ``_build_coord_topology``'s own docstring) and would
    # otherwise be a false positive here, mirroring ``test_move_task_
    # durability.py``'s identical scoping choice for the single_branch case.
    coord_tasks_rel = f"kitty-specs/{ctx.slug}/tasks"
    coord_status = subprocess.run(
        ["git", "status", "--porcelain", "--", coord_tasks_rel],
        cwd=ctx.coord_feature_dir.parents[1],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert coord_status == "", (
        f"coord worktree's tasks/ dir is not clean after the revert-commit:\n{coord_status}"
    )


# ---------------------------------------------------------------------------
# T069b -- the SIGKILL cell (SC-003 / US1 AC4)
# ---------------------------------------------------------------------------


def _mp_child_write_then_hang(
    repo: str,
    mission: str,
    wp_id: str,
    sub_artifact_dir: str,
    ready_path: str,
    body: str,
) -> None:
    """Multiprocessing worker target: perform ONLY the write+validate half of
    the writer (``_allocate_and_write_review_cycle_locked`` -- there is no
    commit call reachable inside this function AT ALL), signal readiness, then
    hang. The parent's SIGKILL therefore always lands cleanly between a
    COMPLETED write and a NOT-YET-STARTED commit -- the exact window SC-003
    names, never a mid-write kill (a different, filesystem-dependent hazard
    this test does not simulate, matching WP10's T044 scope note)."""
    artifact_path: Path
    _artifact, artifact_path, _filename = _allocate_and_write_review_cycle_locked(
        main_repo_root=Path(repo),
        mission_slug=mission,
        wp_id=wp_id,
        sub_artifact_dir=Path(sub_artifact_dir),
        reviewer_agent="reviewer-sigkill",
        affected_files=[],
        body=body,
    )
    Path(ready_path).write_text(str(artifact_path), encoding="utf-8")
    time.sleep(3600)  # the parent SIGKILLs us long before this could return


@pytest.mark.integration
@pytest.mark.git_repo
@pytest.mark.skipif(
    sys.platform == "win32",
    reason="SIGKILL has no direct Windows equivalent (T069 documented edge case)",
)
def test_sigkill_between_write_and_commit_then_identical_retry_exits_zero(
    tmp_path: Path,
) -> None:
    """SC-003 / US1 AC4, exercised end to end: after a SIGKILL strictly
    between a completed write and a not-yet-started commit, the identical
    retry both completes cleanly AND records the correct verdict, with zero
    manual cleanup -- the literal acceptance criterion.

    Scope note: this drives ``create_rejected_review_cycle`` (the writer WP10's
    own T044 reproduction and this WP's prompt both license as the "real
    move-task writer path" substitute for the full CLI surface) rather than
    the full ``_do_move_task``/CLI stack, to keep the multiprocessing child a
    minimal, single-purpose target. "Exits zero" is therefore the direct-call
    analogue (no exception escapes the retry) rather than a literal process
    exit code -- the git-state assertions below are what actually prove the
    SC-003 guarantee, independent of that framing choice.
    """
    repo = tmp_path
    mission = "sigkill-matrix"
    _init_repo(repo)
    feature_dir, _wp_file = _build_wp_file(repo, mission, _WP_ID)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "seed"], cwd=repo, check=True, capture_output=True
    )
    _unprotect_main(repo)
    sub_dir = _review_cycle_wp_dir(repo, mission, _WP_SLUG)
    ready_path = tmp_path / "ready.txt"
    body = "Killed mid-flight, before any commit was attempted.\n"

    ctx = multiprocessing.get_context("fork")
    proc = ctx.Process(
        target=_mp_child_write_then_hang,
        args=(str(repo), mission, _WP_ID, str(sub_dir), str(ready_path), body),
    )
    proc.start()
    deadline = time.monotonic() + 10.0
    while not ready_path.exists():
        if time.monotonic() > deadline:
            proc.kill()
            proc.join(timeout=5)
            pytest.fail("child never signaled write-complete readiness within 10s")
        time.sleep(0.02)

    artifact_path = Path(ready_path.read_text(encoding="utf-8").strip())
    assert artifact_path.exists(), "the child's write never landed before the readiness signal"

    # The SIGKILL itself -- sent only once the write is provably complete and
    # the commit has provably not started (there is no commit call reachable
    # in the child target at all).
    proc.kill()
    proc.join(timeout=10)
    assert not proc.is_alive(), "the child process was not reaped after SIGKILL"
    assert proc.exitcode != 0, f"expected a killed child, got exitcode={proc.exitcode}"

    rel = artifact_path.relative_to(repo)
    status_before_retry = subprocess.run(
        ["git", "status", "--porcelain", "--", str(rel)],
        cwd=repo,
        capture_output=True,
        text=True,
    ).stdout
    assert artifact_path.name in status_before_retry, (
        f"expected the orphan {artifact_path.name} to be untracked after the kill:\n"
        f"{status_before_retry}"
    )

    # The identical retry, from the PARENT process -- exactly as an operator's
    # re-invocation would perform it.
    retried = create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug=mission,
        wp_id=_WP_ID,
        wp_slug=_WP_SLUG,
        body=body,
        reviewer_agent="reviewer-sigkill",
        verdict="rejected",
        commit_router=RealCoordCommitRouter(),
    )
    assert retried.artifact_path != artifact_path, (
        "the retry collided with the orphan instead of allocating the next cycle"
    )
    retried_rel = retried.artifact_path.relative_to(repo)
    show = subprocess.run(
        ["git", "show", f"HEAD:{retried_rel}"], cwd=repo, capture_output=True, text=True
    )
    assert show.returncode == 0, f"retry's write is not committed at HEAD: {show.stderr}"
    _assert_committed_frontmatter_has_no_verdict_key(show.stdout)
    assert body.strip() in show.stdout

    wp_dir = feature_dir / "tasks" / _WP_SLUG
    latest = ReviewCycleArtifact.latest(wp_dir)
    assert latest is not None and latest.cycle_number == retried.artifact.cycle_number, (
        f"expected the retry ({retried.artifact.cycle_number}) to be the "
        f"reader-visible latest, got {latest!r}"
    )


# ---------------------------------------------------------------------------
# SC-004 -- real multi-process concurrency bar (>= 50 iterations, 2 processes)
# ---------------------------------------------------------------------------


def _mp_write_review_cycle(
    repo: str,
    mission: str,
    wp_id: str,
    wp_slug: str,
    body: str,
    reviewer: str,
    result_queue: multiprocessing.Queue[tuple[str, str]],
    event_id: str | None = None,
) -> None:
    """SC-004 worker target: the REAL writer, in a genuinely separate OS
    process, real git commit included; reports its outcome back through a
    Queue rather than raising across the process boundary.

    WP05 (verdict-seam-write-unification-01KZ9Q35, T028/D-PLAN-13): when
    ``event_id`` is supplied, ALSO durably appends the corresponding
    ``review_result`` event -- the authoritative durable act this test's
    re-pointed anchors count (the ``.md`` write is now best-effort).

    Concurrency discipline (post-merge green-up, 2026-08-06): the append MUST
    hold ``feature_status_lock`` -- exactly as the production recording path
    (``status.emit.emit_status_transition`` appends its ``review_result`` event
    INSIDE ``with feature_status_lock(...)``, emit.py). The low-level
    ``append_events_atomic_verified`` store primitive is documented as *crash*-
    atomic only (read-modify-write + ``os.replace``); it is NOT concurrency-safe
    on its own -- two unlocked processes each read N lines and each ``os.replace``
    an N+1 line file, so the later rename silently clobbers the earlier append
    (observed here as "99 of 100 distinct records"). Within a single working tree
    the ``.gitattributes`` union merge driver never fires (there is no git *merge*
    at write time -- that guard is for cross-worktree/branch appends reconciled at
    merge). Serialization comes from ``feature_status_lock``, which production
    always holds and this worker previously (incorrectly) omitted -- manufacturing
    a race production cannot have. Holding the lock here restores fidelity to the
    real recording path without weakening the probe (still two real OS processes,
    still real ``.md`` git commits, still ``>= 2 * iterations`` distinct records
    asserted).
    """
    try:
        created = create_rejected_review_cycle(
            main_repo_root=Path(repo),
            mission_slug=mission,
            wp_id=wp_id,
            wp_slug=wp_slug,
            body=body,
            reviewer_agent=reviewer,
            verdict="rejected",
            commit_router=RealCoordCommitRouter(),
        )
        if event_id is not None:
            from specify_cli.status.locking import feature_status_lock
            from specify_cli.status.models import ReviewResult
            from specify_cli.status.store import append_events_atomic_verified
            from specify_cli.workspace.root_resolver import resolve_status_lock_root

            feature_dir = Path(repo) / "kitty-specs" / mission
            lock_root = resolve_status_lock_root(feature_dir, None)
            with feature_status_lock(lock_root, mission):
                append_events_atomic_verified(
                    feature_dir,
                    [
                        StatusEvent(
                            event_id=event_id,
                            mission_slug=mission,
                            wp_id=wp_id,
                            from_lane=Lane.IN_REVIEW,
                            to_lane=Lane.IN_PROGRESS,
                            at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            actor=reviewer,
                            force=False,
                            execution_mode="worktree",
                            review_result=ReviewResult(
                                reviewer=reviewer, verdict="changes_requested", reference=created.pointer
                            ),
                        )
                    ],
                )
        result_queue.put(("ok", str(created.artifact_path)))
    except Exception as exc:  # noqa: BLE001 -- report to the parent; never crash silently
        result_queue.put(("error", repr(exc)))


@pytest.mark.integration
@pytest.mark.git_repo
def test_sc004_two_concurrent_processes_never_clobber_a_verdict_over_50_iterations(
    tmp_path: Path,
) -> None:
    """SC-004's real probe -- MET via event-log durability (see module
    docstring): >= 50 iterations, 2 REAL OS processes (``multiprocessing``,
    not threads -- ``feature_status_lock`` is an inter-process ``FileLock``).
    Upgrades ``tests/review/test_cycle.py``'s own threaded reproduction
    (``test_concurrent_verdict_writes_do_not_clobber_each_other``, which
    carries an explicit ``TODO(WP15)`` pointing here) to the literal bar.
    Every iteration must end with either two distinct, correctly-recorded
    verdicts, or an explicit, reported refusal for one side -- NEVER a silent
    clobber (both report success but one durable record vanishes). Post
    verdict-seam-write-unification the authoritative record is the
    ``review_result`` event appended under ``feature_status_lock`` (the anchor
    is ``_assert_durable_event_records_at_least`` below); the ``.md`` render
    commit is best-effort (NFR-004). The worker append holds that same lock
    (see :func:`_mp_write_review_cycle`), so the probe is deterministic --
    verified green under the heavy parallel contention that previously
    reproduced an unlocked-append lost-update red."""
    repo = tmp_path
    mission = "sc004-concurrency"
    _init_repo(repo)
    feature_dir, _wp_file = _build_wp_file(repo, mission, _WP_ID)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "seed"], cwd=repo, check=True, capture_output=True
    )
    _unprotect_main(repo)

    ctx = multiprocessing.get_context("fork")
    iterations = 50
    for i in range(iterations):
        text_a = f"Reviewer A's feedback, iteration {i}.\n"
        text_b = f"Reviewer B's feedback, iteration {i}.\n"
        queue: multiprocessing.Queue[tuple[str, str]] = ctx.Queue()
        proc_a = ctx.Process(
            target=_mp_write_review_cycle,
            args=(str(repo), mission, _WP_ID, _WP_SLUG, text_a, "reviewer-a", queue, f"01SC004A{i:018d}"),
        )
        proc_b = ctx.Process(
            target=_mp_write_review_cycle,
            args=(str(repo), mission, _WP_ID, _WP_SLUG, text_b, "reviewer-b", queue, f"01SC004B{i:018d}"),
        )
        proc_a.start()
        proc_b.start()
        results = [queue.get(timeout=30) for _ in range(2)]
        proc_a.join(timeout=30)
        proc_b.join(timeout=30)
        assert proc_a.exitcode == 0, f"iteration {i}: worker A crashed (exitcode={proc_a.exitcode})"
        assert proc_b.exitcode == 0, f"iteration {i}: worker B crashed (exitcode={proc_b.exitcode})"

        errors = [r[1] for r in results if r[0] == "error"]
        oks = [r[1] for r in results if r[0] == "ok"]
        assert oks, (
            f"iteration {i}: neither writer succeeded (errors={errors}) -- SC-004 "
            "requires at least one side to succeed"
        )
        assert len(set(oks)) == len(oks), (
            f"iteration {i}: two 'ok' results collapsed onto the same allocation "
            f"{oks} -- the lock-protected cycle allocator must hand two concurrent "
            "successes DISTINCT review-cycle slots, never the same one"
        )
        # The returned ``.md`` path is a best-effort render, not a durability
        # authority. Under the intentionally unlocked commit phase it can be
        # absent or contain an earlier render for the same allocated cycle.
        # Per-record integrity and cardinality live in the locked event log and
        # are asserted once, comprehensively, below.

    _assert_durable_event_records_at_least(repo, mission, _WP_ID, minimum=2 * iterations)


def _assert_durable_event_records_at_least(repo: Path, mission: str, wp_id: str, *, minimum: int) -> None:
    """SC-003/NFR-004 (WP05, T028, D-PLAN-13) re-pointed anchor: assert AT
    LEAST ``minimum`` distinct, durably-committed ``review_result`` event
    records exist for *wp_id* -- the authoritative durability count
    (``emit_status_transition``/``append_events_atomic_verified`` appends),
    never a count of best-effort ``review-cycle-N.md`` files or a clean git
    working tree (the property WP05's demote retires). Counts DISTINCT
    ``event_id``s carrying a ``review_result`` for this WP, read straight
    from the on-disk event log (not the reducer's collapsed per-WP slot,
    which only ever keeps the LATEST) so a dropped/missing append is
    detectable even when a later one overwrites the reducer's view.
    """
    feature_dir = repo / "kitty-specs" / mission
    events = read_events(feature_dir)
    durable_ids = {
        event.event_id
        for event in events
        if event.wp_id == wp_id and event.review_result is not None
    }
    assert len(durable_ids) >= minimum, (
        f"expected >= {minimum} distinct durable review_result event records "
        f"for {wp_id}, found {len(durable_ids)} -- the event log (not the "
        "best-effort .md commit) is this mission's sole durability authority "
        "post-WP05 (NFR-004)"
    )


def test_sc003_durability_negative_control_dropped_event_reds(tmp_path: Path) -> None:
    """SC-003 non-vacuity (T028, squad #4): the re-pointed durability
    assertion above is not vacuously greenable -- deliberately DROP one
    durable event (write only one of two expected records) and assert
    :func:`_assert_durable_event_records_at_least` correctly goes RED. A
    naive re-point that always passes regardless of what actually landed
    would silently defeat SC-003; this proves it does not."""
    from specify_cli.status.models import ReviewResult
    from specify_cli.status.store import append_events_atomic_verified

    repo = tmp_path
    mission = "sc003-negative-control"
    feature_dir = repo / "kitty-specs" / mission
    feature_dir.mkdir(parents=True)

    # Only ONE durable event lands (the second write is simulated as
    # "dropped" -- e.g. a crash between write and event-append).
    append_events_atomic_verified(
        feature_dir,
        [
            StatusEvent(
                event_id="01SC003NEGATIVECONTROL001",
                mission_slug=mission,
                wp_id=_WP_ID,
                from_lane=Lane.IN_REVIEW,
                to_lane=Lane.IN_PROGRESS,
                at="2026-01-01T00:00:00Z",
                actor="reviewer-a",
                force=False,
                execution_mode="worktree",
                review_result=ReviewResult(reviewer="reviewer-a", verdict="changes_requested", reference="x"),
            )
        ],
    )

    with pytest.raises(AssertionError, match="expected >= 2 distinct durable review_result"):
        _assert_durable_event_records_at_least(repo, mission, _WP_ID, minimum=2)

    # Non-vacuity control: the SAME assertion is green when both records land.
    append_events_atomic_verified(
        feature_dir,
        [
            StatusEvent(
                event_id="01SC003NEGATIVECONTROL002",
                mission_slug=mission,
                wp_id=_WP_ID,
                from_lane=Lane.IN_REVIEW,
                to_lane=Lane.APPROVED,
                at="2026-01-01T00:01:00Z",
                actor="reviewer-b",
                force=False,
                execution_mode="worktree",
                review_result=ReviewResult(reviewer="reviewer-b", verdict="approved", reference="y"),
            )
        ],
    )
    _assert_durable_event_records_at_least(repo, mission, _WP_ID, minimum=2)
