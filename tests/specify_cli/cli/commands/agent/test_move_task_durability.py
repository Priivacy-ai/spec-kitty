"""WP11 (T047-T050): transition ordering and the durability signal.

T047 originally reproduced, red-first, the committed-orphan hazard FR-002/
SC-003 exist to close: a transition-emit failure left a COMMITTED
``verdict: approved`` review-cycle artifact on disk for a WP whose lane never
actually moved. T048's revert-compensator (``tasks_verdict_persistence.
revert_committed_verdict_write``, wired at the ``_mt_execute`` call site via
``_mt_execute_with_verdict_revert`` in ``tasks_move_task.py``) now closes that
hazard, so both tests below assert the GREEN post-fix outcome: no readable
committed verdict survives a failed transition, and the retry -- with its
OWN, genuine ``--approval-ref`` -- records the real approval, not a stale one
left over from the reverted failed attempt.

``exit_code == 0``/``typer.Exit`` is asserted as necessary but never
sufficient in either test: every assertion also queries recorded state
directly (``latest_review_artifact_verdict`` -- the same reader the census's
"reader" category exercises -- git HEAD content, and the transactional lane),
never mere file-listing or exit-code alone.

Both drive the REAL ``_do_move_task`` orchestrator against a REAL
git-fixture repo with the REAL ``RealCoordCommitRouter.commit_artifact`` (so
"committed"/"reverted" is proven via ``git log``/``git status``/HEAD content,
never mere file existence) while the transition-emit leg (``commit_status``)
is fault-injected via a constructor-supplied stand-in, mirroring the
``RealCoordCommitRouter(emit_fn=...)`` injection seam already established in
``tests/review/test_cycle.py``.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import typer

from specify_cli.agent_tasks_ports import (
    CommitArtifactResult,
    CommitStatusResult,
    MissionHandle,
    RealCoordCommitRouter,
    TasksPorts,
)
from specify_cli.cli.commands.agent import tasks_move_task as _tmt
from specify_cli.cli.commands.agent import tasks_verdict_persistence as _tvp
from specify_cli.cli.commands.agent.tasks import _do_move_task, _MoveTaskArgs
from specify_cli.cli.commands.agent.tasks_finalize_validation import (
    _read_transactional_wp_lane,
)
from specify_cli.core.commit_guard import GuardCapability
from specify_cli.git.protection_policy import ProtectionPolicy
from specify_cli.review.artifacts import latest_review_artifact_verdict
from specify_cli.review.cycle import ReviewCycleError, create_rejected_review_cycle
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event
from specify_cli.status import TransitionRequest
from tests.mocked_env import setup_mocked_env
from tests.specify_cli.cli.commands.agent.test_tasks_ports import (
    FakeFsReader,
    FakeGitOps,
    FakeRender,
)

pytestmark = pytest.mark.fast

_MISSION = "wp11-durability"
_WP_ID = "WP01"


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )


def _unprotect_main(repo: Path) -> None:
    """Disable branch protection so a real commit lands on ``main``.

    Mirrors ``tests/review/test_cycle.py``'s ``_unprotect_main``.
    """
    kittify_dir = repo / ".kittify"
    kittify_dir.mkdir(parents=True, exist_ok=True)
    (kittify_dir / "config.yaml").write_text(
        "protection:\n  protected_branches: []\n", encoding="utf-8"
    )
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "test: unprotect main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )


_MISSION_ID = "01HQZZZZZZZZZZZZZZZZZZZZZZ"


def _build_wp_file(repo: Path, mission_slug: str, wp_id: str) -> tuple[Path, Path]:
    feature_dir = repo / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    # A real, non-coord SINGLE_BRANCH mission still needs a resolvable
    # ``meta.json`` -- ``read_events_transactional`` (a REAL git repo takes the
    # non-fallback path _transaction_topology_available walks) treats an
    # ABSENT meta.json as "maybe still-coord, go check CoordinationWorkspace",
    # which then hard-fails on an empty ``mid8``. Any valid meta dict makes
    # ``meta_exists`` True, short-circuiting to the (false) coord-transaction
    # check instead -- this mission has no coordination_branch/lanes.json, so
    # it is genuinely SINGLE_BRANCH.
    import json as _json

    (feature_dir / "meta.json").write_text(
        _json.dumps({"mission_id": _MISSION_ID, "mission_slug": mission_slug}),
        encoding="utf-8",
    )
    wp_file = tasks_dir / f"{wp_id}-test.md"
    wp_file.write_text(
        f"---\n"
        f"work_package_id: {wp_id}\n"
        f"title: Test {wp_id}\n"
        f"execution_mode: code_change\n"
        f"agent: testbot\n"
        f"subtasks: [T001, T002, T003]\n"
        f"owned_files:\n  - src/{wp_id.lower()}/**\n"
        f"authoritative_surface: src/{wp_id.lower()}/\n"
        f"---\n\n# {wp_id}\n\n## Activity Log\n",
        encoding="utf-8",
    )
    return feature_dir, wp_file


def _seed_wp_event(feature_dir: Path, wp_id: str, to_lane: str, *, seq: int) -> None:
    append_event(
        feature_dir,
        StatusEvent(
            event_id=f"test-{wp_id}-{to_lane}-{seq}",
            mission_slug=feature_dir.name,
            wp_id=wp_id,
            from_lane=Lane.PLANNED,
            to_lane=Lane(to_lane),
            at="2026-01-01T00:00:00+00:00",
            actor="test",
            force=True,
            execution_mode="worktree",
        ),
    )


@dataclass
class _FaultInjectableCoordRouter:
    """A ``CoordCommitRouter`` whose ``commit_artifact`` is the REAL
    ``RealCoordCommitRouter`` (so the review-cycle write is a genuine,
    verifiable git commit) while ``commit_status`` -- the transition-emit
    leg -- is independently fault-injectable per call.

    ``feature_write_dir`` returns a fixed, test-controlled directory (this
    test does not exercise the coord-worktree resolution seam, only the
    verdict-write / transition-emit ordering) -- the same pattern
    ``FakeCoordCommitRouter`` uses in ``test_tasks_ports.py``.
    """

    write_dir: Path
    real_router: RealCoordCommitRouter = field(default_factory=RealCoordCommitRouter)
    emit_should_fail: bool = False
    status_calls: list[TransitionRequest] = field(default_factory=list)

    def feature_write_dir(self, mission: MissionHandle) -> Path:
        return self.write_dir

    def commit_status(
        self, request: TransitionRequest, *, capability: GuardCapability
    ) -> CommitStatusResult:
        self.status_calls.append(request)
        if self.emit_should_fail:
            raise RuntimeError("T047: simulated transition-emit failure")
        return self.real_router.commit_status(request, capability=capability)

    def commit_artifact(
        self,
        mission: MissionHandle,
        paths: Sequence[Path],
        message: str,
        *,
        kind: object,
        policy: ProtectionPolicy,
    ) -> CommitArtifactResult:
        return self.real_router.commit_artifact(
            mission, paths, message, kind=kind, policy=policy
        )


def _fake_ports(feature_dir: Path, coord: _FaultInjectableCoordRouter) -> TasksPorts:
    return TasksPorts(
        fs=FakeFsReader(default_planning_dir=feature_dir),
        coord=coord,
        git=FakeGitOps(),
        render=FakeRender(),
    )


def _run_move(
    repo: Path,
    *,
    ports: TasksPorts,
    note: str | None = None,
    approval_ref: str | None = None,
    auto_commit: bool = True,
) -> None:
    with setup_mocked_env(
        repo,
        mission_slug=_MISSION,
        target_branch="main",
        extra_patches={
            "_validate_ready_for_review": (True, []),
            "_check_unchecked_subtasks": [],
        },
    ):
        _do_move_task(
            _MoveTaskArgs(
                task_id=_WP_ID,
                to="approved",
                mission=_MISSION,
                agent=None,
                assignee=None,
                shell_pid=None,
                note=note,
                review_feedback_file=None,
                approval_ref=approval_ref,
                reviewer=None,
                self_review_fallback=False,
                intended_reviewer=None,
                reviewer_failure_reason=None,
                done_override_reason=None,
                force=False,
                tracker_ref=None,
                skip_review_artifact_check=False,
                auto_commit=auto_commit,
                json_output=True,
            ),
            ports=ports,
        )


def _wp_dir(repo: Path) -> Path:
    return repo / "kitty-specs" / _MISSION / "tasks" / f"{_WP_ID}-test"


def _git_status(repo: Path) -> str:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _git_head_has_file(repo: Path, relpath: str) -> bool:
    """True iff *relpath* is reachable in ``HEAD``'s tree (``git cat-file -e``).

    Distinct from "was it ever committed" (``_git_log_files`` -- history keeps
    the OLD commit forever) and from "does it exist on disk" (a checkout
    reflects only the CURRENT tree). This is the read T048's revert-commit
    must flip to ``False``: a readable, checked-out-from-HEAD verdict.
    """
    result = subprocess.run(
        ["git", "cat-file", "-e", f"HEAD:{relpath}"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _git_log_files(repo: Path) -> str:
    result = subprocess.run(
        ["git", "log", "--name-only", "--pretty=format:--COMMIT--"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _setup_fixture(repo: Path) -> Path:
    """Real git repo with WP01 currently ``in_review`` and a rejected
    review-cycle-1.md already committed (the guard's "prior cycle" precondition).
    """
    _init_repo(repo)
    feature_dir, _ = _build_wp_file(repo, _MISSION, _WP_ID)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=repo, check=True, capture_output=True)
    _unprotect_main(repo)

    _seed_wp_event(feature_dir, _WP_ID, "in_review", seq=0)

    # Seed cycle 1 (rejected) via the real writer + real commit, exactly like
    # production would have left it after an earlier rejection.
    create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug=_MISSION,
        wp_id=_WP_ID,
        wp_slug=f"{_WP_ID}-test",
        body="Needs another pass.\n",
        reviewer_agent="reviewer-renata",
        verdict="rejected",
        commit_router=RealCoordCommitRouter(),
    )
    return feature_dir


def test_failed_transition_emit_is_reverted_leaving_no_committed_verdict(
    tmp_path: Path,
) -> None:
    """T047/T048 GREEN: a transition-emit failure no longer leaves a committed
    orphan -- ``_mt_execute_with_verdict_revert`` catches the failure and
    ``revert_committed_verdict_write`` undoes the already-committed write
    before ``_do_move_task`` returns its error.

    ``exit_code`` (via ``typer.Exit``) is necessary but NOT sufficient: every
    assertion below queries RECORDED STATE directly.
    """
    repo = tmp_path
    feature_dir = _setup_fixture(repo)
    wp_dir = _wp_dir(repo)
    relpath = f"kitty-specs/{_MISSION}/tasks/{_WP_ID}-test/review-cycle-2.md"

    coord = _FaultInjectableCoordRouter(write_dir=feature_dir, emit_should_fail=True)
    ports = _fake_ports(feature_dir, coord)

    with pytest.raises(typer.Exit) as exc_info:
        _run_move(repo, ports=ports, note="Review passed")
    assert exc_info.value.exit_code == 1  # necessary, never sufficient (see below)

    # (a) No readable committed verdict for this WP -- queried the way the
    # census's "reader" category would (latest_review_artifact_verdict), not
    # raw file listing. The reverted write must not be the latest: cycle 1
    # (rejected, seeded by the fixture) is still the true latest.
    latest = latest_review_artifact_verdict(wp_dir)
    assert latest is not None and latest.verdict == "rejected", (
        f"expected the pre-existing rejected cycle 1 to still be the reader-"
        f"visible latest verdict after the revert, got {latest}"
    )

    # (b) The orphan file itself is gone from disk...
    artifact = wp_dir / "review-cycle-2.md"
    assert not artifact.exists(), (
        "the reverted verdict write is still present on disk -- the "
        "compensator did not delete it"
    )
    # ...AND not merely deleted-but-uncommitted (that would be a NEW,
    # partially-reverted orphan shape) -- HEAD's tree must not contain it,
    # and the working tree must be clean (the deletion itself was committed).
    assert not _git_head_has_file(repo, relpath), (
        "review-cycle-2.md is still reachable at HEAD -- the deletion was "
        "never committed (partially-reverted state)"
    )
    # Scoped to the WP's own tasks dir (not repo-wide): the fixture's own
    # ``status.events.jsonl`` is deliberately left untracked by ``_setup_
    # fixture`` (a different, unrelated concern from the verdict artifact)
    # and would otherwise be a false positive here.
    tasks_status = subprocess.run(
        ["git", "status", "--porcelain", "--", f"kitty-specs/{_MISSION}/tasks"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert tasks_status == "", (
        f"the WP's tasks dir is not clean after the revert-commit -- a "
        f"partially-reverted state (deleted but not committed, or vice "
        f"versa) must never occur:\n{tasks_status}"
    )
    # The OLD commit that introduced review-cycle-2.md still exists in
    # history (a revert-commit, not a rewrite) -- this is the correct,
    # honest shape: "no readable committed verdict AT HEAD", not "no trace
    # in history ever".
    log = _git_log_files(repo)
    assert "review-cycle-2.md" in log, (
        "the revert should be a NEW commit undoing the write, not a history "
        f"rewrite -- the original commit should still appear in git log:\n{log}"
    )

    # (c) The WP's lane is STILL in_review -- the transition never completed.
    lane = _read_transactional_wp_lane(
        feature_dir=feature_dir, mission_slug=_MISSION, wp_id=_WP_ID, repo_root=repo
    )
    assert lane == Lane.IN_REVIEW, (
        f"expected the lane to still be in_review after the failed transition emit, got {lane}"
    )


def test_retry_after_reverted_orphan_records_the_genuine_approval(
    tmp_path: Path,
) -> None:
    """T047/T048 GREEN, the SC-003 half: once the failed attempt's orphan is
    actually reverted (no longer merely tolerated), the retry is a genuine
    write again -- not a no-op guard short-circuit backed by stale data.

    This is the corrected form of the WP prompt's Objective-section claim
    (empirically disproven pre-fix, see the prior commit's Activity Log):
    the retry now records the RETRY's OWN ``--approval-ref``, because there
    is no orphan left for the no-op guard to treat as "already approved".
    ``exit_code == 0`` is asserted as necessary but never sufficient.
    """
    repo = tmp_path
    feature_dir = _setup_fixture(repo)
    wp_dir = _wp_dir(repo)

    failing_coord = _FaultInjectableCoordRouter(write_dir=feature_dir, emit_should_fail=True)
    with pytest.raises(typer.Exit):
        _run_move(
            repo,
            ports=_fake_ports(feature_dir, failing_coord),
            note="Review passed",
            approval_ref="approval:first-failed-attempt",
        )
    # Precondition: the failed attempt's write was actually reverted (proven
    # in detail by the sibling test) -- confirm no orphan survives to retry
    # against, so this test's own assertions mean what they claim to.
    assert not (wp_dir / "review-cycle-2.md").exists()
    latest_before_retry = latest_review_artifact_verdict(wp_dir)
    assert latest_before_retry is not None and latest_before_retry.verdict == "rejected"

    # Retry: SAME command, its OWN genuine approval_ref, failure removed.
    # Reaching the line after this call (no exception) is "exit 0" --
    # necessary, but per this test's own docstring, never sufficient on its
    # own; every assertion below queries what was actually recorded.
    retry_coord = _FaultInjectableCoordRouter(write_dir=feature_dir, emit_should_fail=False)
    _run_move(
        repo,
        ports=_fake_ports(feature_dir, retry_coord),
        note="Review passed",
        approval_ref="approval:genuine-retry",
    )

    # A GENUINE new write happened this time (cycle 2 again -- the deleted slot is free).
    assert len(retry_coord.status_calls) >= 1, (
        "the retry never even attempted the transition emit -- this test is "
        "not exercising the described retry path"
    )
    artifact = wp_dir / "review-cycle-2.md"
    assert artifact.exists(), (
        "the retry did not write a new verdict artifact -- with the orphan "
        "actually reverted, the no-op guard must not fire this time"
    )
    artifact_text = artifact.read_text(encoding="utf-8")
    assert "approval:genuine-retry" in artifact_text, (
        "the retry's OWN approval_ref did not make it into the recorded "
        "artifact -- 'records the correct verdict' (SC-003) is failing"
    )
    assert "approval:first-failed-attempt" not in artifact_text, (
        "the artifact still carries the FIRST FAILED attempt's stale "
        "reference -- the revert did not actually clear the prior write"
    )
    latest_after_retry = latest_review_artifact_verdict(wp_dir)
    assert latest_after_retry is not None and latest_after_retry.verdict == "approved"

    status = _git_status(repo)
    assert "review-cycle-2.md" not in status, (
        f"the retry's write is not committed:\n{status}"
    )
    relpath = f"kitty-specs/{_MISSION}/tasks/{_WP_ID}-test/review-cycle-2.md"
    assert _git_head_has_file(repo, relpath), (
        "the retry's genuine write is not reachable at HEAD"
    )

    lane_after_retry = _read_transactional_wp_lane(
        feature_dir=feature_dir, mission_slug=_MISSION, wp_id=_WP_ID, repo_root=repo
    )
    assert lane_after_retry == Lane.APPROVED, (
        f"expected the retry's transition emit to succeed and move the lane "
        f"to approved, got {lane_after_retry}"
    )


# ---------------------------------------------------------------------------
# T050: skip_target_branch_commit threaded to the review-cycle-artifact writer
# ---------------------------------------------------------------------------


@dataclass
class _ProtectedBranchRefusingCommitRouter:
    """Stub ``CoordCommitRouter`` whose ``commit_artifact`` simulates the real
    ``ProtectedBranchRefused`` outcome ``commit_for_mission`` returns for a
    protected target branch -- modeled on ``tests/review/test_cycle.py``'s
    ``_FailingCommitRouter``. ``commit_status``/``feature_write_dir`` assert
    if called: this stub exists to prove whether ``commit_artifact`` is even
    ATTEMPTED, not to exercise the transition-emit leg.
    """

    artifact_calls: list[Path] = field(default_factory=list)

    def feature_write_dir(self, mission: MissionHandle) -> Path:
        raise AssertionError("feature_write_dir is not used by this reproduction")

    def commit_status(
        self, request: object, *, capability: GuardCapability
    ) -> CommitStatusResult:
        raise AssertionError("commit_status is not used by this reproduction")

    def commit_artifact(
        self,
        mission: MissionHandle,
        paths: Sequence[Path],
        message: str,
        *,
        kind: object,
        policy: ProtectionPolicy,
    ) -> CommitArtifactResult:
        self.artifact_calls.extend(paths)
        return CommitArtifactResult(
            status="error",
            placement_ref=str(paths[0]) if paths else "",
            diagnostic="simulated ProtectedBranchRefused: destination branch is protected",
        )


def _minimal_state(
    repo: Path,
    *,
    task_id: str = _WP_ID,
    mission_slug: str = _MISSION,
    resolved_auto_commit: bool,
    skip_target_branch_commit: bool,
    json_output: bool = False,
    approval_ref: str | None = None,
    note: str | None = None,
    resolved_feedback_source: Path | None = None,
) -> _tmt._MoveTaskState:
    st = _tmt._MoveTaskState(
        task_id=task_id,
        to="approved",
        mission=mission_slug,
        agent="testbot",
        assignee=None,
        shell_pid=None,
        note=note,
        review_feedback_file=None,
        approval_ref=approval_ref,
        reviewer="reviewer-renata",
        self_review_fallback=False,
        intended_reviewer=None,
        reviewer_failure_reason=None,
        done_override_reason=None,
        force=False,
        tracker_ref=None,
        skip_review_artifact_check=False,
        auto_commit=resolved_auto_commit,
        json_output=json_output,
    )
    st.main_repo_root = repo
    st.mission_slug = mission_slug
    st.resolved_auto_commit = resolved_auto_commit
    st.skip_target_branch_commit = skip_target_branch_commit
    st.note_text = note
    st.resolved_feedback_source = resolved_feedback_source
    return st


def _seed_rejected_cycle_1(repo: Path, mission_slug: str, wp_id: str) -> None:
    """A prior rejected cycle on disk, UNCOMMITTED -- sufficient for the
    no-op guard's precondition; this reproduction is not about that guard.
    """
    create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug=mission_slug,
        wp_id=wp_id,
        wp_slug=f"{wp_id}-test",
        body="Needs another pass.\n",
        reviewer_agent="reviewer-renata",
        verdict="rejected",
    )


def test_pre_fix_naive_commit_router_gating_crashes_on_protected_target_branch(
    tmp_path: Path,
) -> None:
    """T050 red-first: reproduces the PRE-FIX defect this WP's Objective
    section describes -- gating the review-cycle-artifact ``commit_router``
    on ``resolved_auto_commit`` ALONE (ignoring ``skip_target_branch_commit``,
    the naive expression this WP replaces) raises ``ReviewCycleError``
    uncaught on a protected-primary-coord topology, where
    ``resolved_auto_commit=True`` but ``skip_target_branch_commit=True``.

    This does not call ``_persist_approved_review_cycle`` itself (that
    function is ALREADY fixed in this diff) -- it inlines the exact
    pre-fix expression (``ports.coord if st.resolved_auto_commit else
    None``) verbatim to prove, in isolation, that the naive gate is what
    crashes -- per the rule against reverting tracked files to observe
    pre-fix behaviour.
    """
    repo = tmp_path
    _init_repo(repo)
    _build_wp_file(repo, _MISSION, _WP_ID)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=repo, check=True, capture_output=True)
    _seed_rejected_cycle_1(repo, _MISSION, _WP_ID)

    st = _minimal_state(
        repo, resolved_auto_commit=True, skip_target_branch_commit=True
    )
    router = _ProtectedBranchRefusingCommitRouter()

    # The naive, pre-fix expression this WP replaces (tasks_verdict_
    # persistence.py's two call sites used to read exactly this).
    naive_commit_router = router if st.resolved_auto_commit else None

    with pytest.raises(ReviewCycleError, match="ProtectedBranchRefused|protected"):
        create_rejected_review_cycle(
            main_repo_root=st.main_repo_root,
            mission_slug=st.mission_slug,
            wp_id=st.task_id,
            wp_slug=f"{_WP_ID}-test",
            body="Approved by reviewer-renata: approval:WP01\n",
            reviewer_agent="reviewer-renata",
            verdict="approved",
            commit_router=naive_commit_router,
        )


def test_protected_target_branch_completes_without_raising_after_fix(
    tmp_path: Path,
) -> None:
    """T050 green: the FIXED ``_persist_approved_review_cycle`` (this diff)
    consults ``skip_target_branch_commit`` and passes ``commit_router=None``
    instead of attempting -- and crashing on -- the protected-branch commit.
    Both the approval and rejection call sites are exercised.
    """
    repo = tmp_path
    _init_repo(repo)
    _build_wp_file(repo, _MISSION, _WP_ID)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=repo, check=True, capture_output=True)
    _seed_rejected_cycle_1(repo, _MISSION, _WP_ID)

    st = _minimal_state(
        repo,
        resolved_auto_commit=True,
        skip_target_branch_commit=True,
        approval_ref="approval:WP01",
    )
    router = _ProtectedBranchRefusingCommitRouter()
    ports = TasksPorts(
        fs=FakeFsReader(default_planning_dir=repo / "kitty-specs" / _MISSION),
        coord=router,
        git=FakeGitOps(),
        render=FakeRender(),
    )

    signal = _tvp._persist_approved_review_cycle(st, ports)

    assert router.artifact_calls == [], (
        "commit_artifact was invoked despite skip_target_branch_commit=True -- "
        "the protected-branch attempt should never happen"
    )
    assert signal is not None
    assert signal.durably_persisted is False
    assert signal.skip_reason == _tvp._DURABILITY_REASON_PROTECTED_TARGET_BRANCH

    wp_dir = _wp_dir(repo)
    artifact = wp_dir / "review-cycle-2.md"
    assert artifact.exists()
    assert "verdict: approved" in artifact.read_text(encoding="utf-8")

    # Rejection call site: same gating, exercised via a fresh rollback state.
    st2 = _minimal_state(
        repo,
        resolved_auto_commit=True,
        skip_target_branch_commit=True,
        resolved_feedback_source=None,
    )
    feedback = tmp_path / "feedback.md"
    feedback.write_text("**Issue**: needs another look.\n", encoding="utf-8")
    st2.resolved_feedback_source = feedback
    router2 = _ProtectedBranchRefusingCommitRouter()
    ports2 = TasksPorts(
        fs=FakeFsReader(default_planning_dir=repo / "kitty-specs" / _MISSION),
        coord=router2,
        git=FakeGitOps(),
        render=FakeRender(),
    )
    signal2 = _tvp.persist_rejected_review_cycle_for_rollback(st2, ports2)
    assert router2.artifact_calls == []
    assert signal2.durably_persisted is False
    assert signal2.skip_reason == _tvp._DURABILITY_REASON_PROTECTED_TARGET_BRANCH


# ---------------------------------------------------------------------------
# T049: the --no-auto-commit durability signal (console notice half)
# ---------------------------------------------------------------------------


def test_no_auto_commit_announces_the_non_durable_write_on_console(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T049: ``--no-auto-commit`` is FR-013's ONE sanctioned non-durable path.
    The console notice (this module's owned half of the durability signal --
    the ``--json`` key requires ``_mt_output``/``_MoveTaskState`` in
    ``tasks_move_task.py``, outside this WP's ``owned_files``; see the
    module docstring and the WP11 report) must actually print, and the
    returned :class:`VerdictDurabilitySignal` must name the reason.
    """
    repo = tmp_path
    _init_repo(repo)
    _build_wp_file(repo, _MISSION, _WP_ID)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=repo, check=True, capture_output=True)
    _seed_rejected_cycle_1(repo, _MISSION, _WP_ID)

    st = _minimal_state(
        repo,
        resolved_auto_commit=False,
        skip_target_branch_commit=False,
        approval_ref="approval:WP01",
        json_output=False,
    )
    router = _ProtectedBranchRefusingCommitRouter()  # asserts if commit_artifact is ever called
    ports = TasksPorts(
        fs=FakeFsReader(default_planning_dir=repo / "kitty-specs" / _MISSION),
        coord=router,
        git=FakeGitOps(),
        render=FakeRender(),
    )

    signal = _tvp._persist_approved_review_cycle(st, ports)

    assert router.artifact_calls == [], "no commit should be attempted at all"
    assert signal is not None
    assert signal.durably_persisted is False
    assert signal.skip_reason == _tvp._DURABILITY_REASON_NO_AUTO_COMMIT

    captured = capsys.readouterr()
    assert "written but NOT committed" in captured.out
    assert "--no-auto-commit" in captured.out

    latest = latest_review_artifact_verdict(_wp_dir(repo))
    assert latest is not None
    assert latest.verdict == "approved"


def test_json_output_suppresses_the_durability_console_notice(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The console notice must stay silent under ``--json`` (matching this
    module's established ``if not json_output:`` pattern) -- a machine
    consumer is expected to read the (currently unwired) ``--json`` key
    instead, never a Rich-formatted console line.
    """
    repo = tmp_path
    _init_repo(repo)
    _build_wp_file(repo, _MISSION, _WP_ID)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=repo, check=True, capture_output=True)
    _seed_rejected_cycle_1(repo, _MISSION, _WP_ID)

    st = _minimal_state(
        repo,
        resolved_auto_commit=False,
        skip_target_branch_commit=False,
        approval_ref="approval:WP01",
        json_output=True,
    )
    router = _ProtectedBranchRefusingCommitRouter()
    ports = TasksPorts(
        fs=FakeFsReader(default_planning_dir=repo / "kitty-specs" / _MISSION),
        coord=router,
        git=FakeGitOps(),
        render=FakeRender(),
    )

    signal = _tvp._persist_approved_review_cycle(st, ports)
    assert signal is not None
    assert signal.skip_reason == _tvp._DURABILITY_REASON_NO_AUTO_COMMIT

    captured = capsys.readouterr()
    assert captured.out == ""


def test_ordinary_auto_commit_path_reports_durably_persisted_true(
    tmp_path: Path,
) -> None:
    """The normal (auto-commit, not protected) path must report
    ``durably_persisted=True, skip_reason=None`` -- the DoD requirement that
    the key is present/true (not merely absent) on every other path.
    """
    repo = tmp_path
    _init_repo(repo)
    _build_wp_file(repo, _MISSION, _WP_ID)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=repo, check=True, capture_output=True)
    _unprotect_main(repo)
    _seed_rejected_cycle_1(repo, _MISSION, _WP_ID)

    st = _minimal_state(
        repo,
        resolved_auto_commit=True,
        skip_target_branch_commit=False,
        approval_ref="approval:WP01",
    )
    ports = TasksPorts(
        fs=FakeFsReader(default_planning_dir=repo / "kitty-specs" / _MISSION),
        coord=RealCoordCommitRouter(),
        git=FakeGitOps(),
        render=FakeRender(),
    )

    signal = _tvp._persist_approved_review_cycle(st, ports)

    assert signal is not None
    assert signal.durably_persisted is True
    assert signal.skip_reason is None
    status = _git_status(repo)
    assert "review-cycle-2.md" not in status, f"expected a real commit:\n{status}"


# ---------------------------------------------------------------------------
# T048: the in-line _mt_execute/revert wrap inside _do_move_task
# ---------------------------------------------------------------------------
#
# Note (report-worthy): T048's compensator is wrapped IN-LINE inside
# ``_do_move_task`` rather than factored into a new named top-level helper.
# A new native top-level symbol in ``tasks_move_task.py`` would ALSO need a
# row in ``test_tasks_compat_surface.py``'s consolidated re-export guard
# (``test_guard_keyset_is_superset_of_all_six_seams_native_defs``) plus an
# identity re-export on ``tasks.py`` to satisfy Guard 1 there -- both files
# outside this WP's two named widened purposes. Keeping the wrap inline
# avoids that third file entirely, matching "keep the diff minimal and
# surgical". These tests exercise it end-to-end through ``_do_move_task``
# instead of unit-testing a standalone function.


def _raising_mt_execute(_st: object, _ports: object) -> None:
    raise RuntimeError("simulated unrelated execute failure")


def test_execute_failure_without_pending_write_reports_the_original_error_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """No verdict write happened this invocation (``_mt_finalize_plan``
    stubbed to a no-op, so ``pending_verdict_write`` stays ``None`` -- mirrors
    a plain claim/for_review transition with no review-cycle involved). A
    transition-emit failure must surface UNCHANGED: no revert attempted
    (nothing to revert), and the reported error is the ORIGINAL message only
    -- no compensator text.
    """
    repo = tmp_path
    feature_dir = _setup_fixture(repo)
    monkeypatch.setattr(_tmt, "_mt_finalize_plan", lambda st, ports: None)
    monkeypatch.setattr(_tmt, "_mt_execute", _raising_mt_execute)
    revert_calls: list[object] = []
    monkeypatch.setattr(
        _tmt, "revert_committed_verdict_write", lambda *a: revert_calls.append(a)
    )
    ports = _fake_ports(feature_dir, _FaultInjectableCoordRouter(write_dir=feature_dir))

    with pytest.raises(typer.Exit) as exc_info:
        _run_move(repo, ports=ports, note="Review passed")
    assert exc_info.value.exit_code == 1
    assert revert_calls == [], "the compensator ran with nothing to revert"

    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["error"] == "simulated unrelated execute failure"


def test_execute_failure_with_failed_revert_surfaces_a_compound_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A durable write DID happen (real ``_mt_finalize_plan``); the compensator
    itself then fails to undo it (stubbed ``VerdictRevertError``). This is a
    COMPOUNDED failure and must NOT be silently swallowed into the original
    error -- both messages must be visible to the operator.
    """
    repo = tmp_path
    feature_dir = _setup_fixture(repo)
    monkeypatch.setattr(_tmt, "_mt_execute", _raising_mt_execute)

    def _failing_revert(_st: object, _signal: object) -> None:
        raise _tvp.VerdictRevertError("simulated revert-commit failure")

    monkeypatch.setattr(_tmt, "revert_committed_verdict_write", _failing_revert)
    ports = _fake_ports(feature_dir, _FaultInjectableCoordRouter(write_dir=feature_dir))

    with pytest.raises(typer.Exit) as exc_info:
        _run_move(repo, ports=ports, note="Review passed", approval_ref="approval:WP01")
    assert exc_info.value.exit_code == 1

    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert "simulated unrelated execute failure" in payload["error"]
    assert "simulated revert-commit failure" in payload["error"]


# ---------------------------------------------------------------------------
# T049/T050: end-to-end --json wiring (_mt_output, tasks_move_task.py)
# ---------------------------------------------------------------------------


def test_json_output_surfaces_durably_persisted_true_end_to_end(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The durability signal computed in ``tasks_verdict_persistence.py``
    actually reaches the ``--json`` envelope ``_mt_output`` builds in
    ``tasks_move_task.py`` -- the ownership-widening wiring this WP was
    escalated for, not just the unit-level signal computation.
    """
    repo = tmp_path
    feature_dir = _setup_fixture(repo)
    coord = _FaultInjectableCoordRouter(write_dir=feature_dir, emit_should_fail=False)
    _run_move(repo, ports=_fake_ports(feature_dir, coord), note="Review passed")

    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["verdict_durably_persisted"] is True
    assert "verdict_durability_skip_reason" not in payload


def test_json_output_surfaces_skip_reason_end_to_end_for_no_auto_commit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--no-auto-commit`` end-to-end: the ``--json`` envelope carries both
    keys (explicit ``false``, plus the distinguishing reason) -- never a bare
    missing key for a machine consumer to infer non-durability from.
    """
    repo = tmp_path
    feature_dir = _setup_fixture(repo)
    coord = _FaultInjectableCoordRouter(write_dir=feature_dir, emit_should_fail=False)
    _run_move(
        repo, ports=_fake_ports(feature_dir, coord), note="Review passed", auto_commit=False
    )

    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["verdict_durably_persisted"] is False
    assert payload["verdict_durability_skip_reason"] == "no_auto_commit"
