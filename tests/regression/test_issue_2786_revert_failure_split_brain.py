"""Scope: #2786 — a FAILED coord ``done`` revert during rollback is swallowed (INTENTIONAL red-first P0).

This module is an INTENTIONAL, issue-pinned red-first P0 reproduction for
**#2786**. It is expected to FAIL on ``main`` and stays RED until #2786 is fixed
— per ADR ``docs/adr/3.x/2026-07-17-1`` (a P0 defect must carry an honest,
main-breaking reproduction; it is NOT deselected or xfail-masked).

Defect (#2786)
--------------
The #2711 Option-A rollback reverts the committed coordination ``done`` commit in
lockstep with the working-tree byte restore
(``specify_cli.merge.executor._revert_coord_done_commit``). That revert is
**best-effort**: when the coord-worktree ``git revert`` itself FAILS (a conflict,
a dirty index, a broken worktree), the helper merely runs ``git revert --abort``,
logs a ``warning``, and RETURNS — it neither raises nor writes any durable
reconcile marker (executor.py, the ``if revert.returncode != 0:`` branch).

Consequently the committed coordination ``done`` survives while the working tree
is rolled back to ``approved`` by ``_restore_final_bookkeeping_snapshots`` — the
#2711 split-brain silently RE-OPENS along the revert-failure path that the
Option-A fix did not close. Nothing durable records that the two surfaces
diverged, so a later resume/merge cannot detect the incoherence either.

Reproduction strategy
---------------------
Reuse the proven coord-topology full-merge harness fused in
``test_issue_2711_merge_rollback_resume_coherence`` (itself modeled on the #1772
coord-branch harness the WP02/WP04 work used) and drive the pre-existing entry
point ``_run_lane_based_merge``:

* the mission records the per-WP ``approved -> done`` transition on the
  coordination branch BEFORE the target advance (``done_marked_before_target``);
* the target advance is injected to FAIL (``integrate_mission_into_target``),
  triggering the #2711 rollback path;
* the coord-worktree ``git revert`` is forced to return non-zero — exercising the
  REAL ``if revert.returncode != 0:`` failure branch of ``_revert_coord_done_commit``
  (abort + warning + silent return), the exact swallowed-failure path under test.

The coherence assertion (``committed_lane == working_lane``) then FAILS for the
RIGHT reason: the committed coordination reduction is stranded at ``done`` while
the rolled-back working tree reduces to ``approved`` — the swallowed-revert
split-brain. A non-vacuity witness proves the revert branch was actually hit and
returned non-zero, so the red cannot pass as a setup artefact.

Do NOT fix ``_revert_coord_done_commit`` here — the fix is deferred to #2786; this
module is the honest red that the fix will flip green.
"""

from __future__ import annotations

import contextlib
import subprocess
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the status package before any coordination submodule (mirror the
# production import order; see the #2711 harness module docstring for rationale).
import specify_cli.status  # noqa: F401  # import-order guard

from specify_cli.cli.commands.merge import _run_lane_based_merge
from specify_cli.coordination.status_service import wp_lane_actor_from_events
from specify_cli.merge.config import MergeStrategy
from specify_cli.status import Lane

# Reuse the fused coord-topology harness (never edited in place — WP01/WP02 note).
from tests.regression.test_issue_2711_merge_rollback_resume_coherence import (
    _INJECTED_TARGET_FAILURE,
    WP_ID,
    _assert_pre_target_done_path,
    _bootstrap_coord_mission,
    _committed_coord_events,
    _init_git_repo,
    _merge_external_mocks,
    _working_coord_events,
)

pytestmark = [pytest.mark.regression, pytest.mark.git_repo, pytest.mark.non_sandbox]

MISSION_SLUG = "merge-rollback-2711-01KXRRB7"  # harness slug (isolated per tmp repo)
_INJECTED_REVERT_FAILURE = "injected #2786 coord revert conflict"


@contextlib.contextmanager
def _revert_forced_to_fail() -> Iterator[list[list[str]]]:
    """Force the coord-worktree ``git revert`` to return non-zero.

    Intercepts ONLY the forward ``git revert --no-edit <range>`` subprocess call
    inside ``_revert_coord_done_commit`` and returns a non-zero
    ``CompletedProcess`` — exercising the real ``if revert.returncode != 0:``
    failure branch (abort + warning + silent return). Every other subprocess call
    (``rev-parse HEAD``, the follow-up ``git revert --abort``, and all unrelated
    git plumbing) delegates unchanged to the real ``subprocess.run``, so the merge
    flow is otherwise untouched.

    Yields the list of intercepted revert commands so the caller can assert the
    failure branch was genuinely reached (non-vacuity).
    """
    real_run = subprocess.run
    intercepted: list[list[str]] = []

    # A ``subprocess.run`` shim: fully typing it would mean re-declaring
    # ``run``'s large overload set for a two-line test double — mypy is correct
    # that it is untyped, but a faithful annotation adds no safety here.
    def fake_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(cmd, list) and "revert" in cmd and "--abort" not in cmd:
            intercepted.append(list(cmd))
            return subprocess.CompletedProcess(
                cmd, returncode=1, stdout="", stderr=_INJECTED_REVERT_FAILURE
            )
        return real_run(cmd, *args, **kwargs)

    with patch("specify_cli.merge.executor.subprocess.run", side_effect=fake_run):
        yield intercepted


def _run_merge_with_target_and_revert_failing(
    repo: Path,
) -> tuple[BaseException, list[list[str]]]:
    """Run one merge pass: target advance fails AND the coord revert fails.

    Returns the propagated exception (asserted to be the injected target-advance
    fault) and the intercepted revert commands (asserted non-empty).
    """
    with (
        _merge_external_mocks(),
        patch(
            "specify_cli.lanes.merge.integrate_mission_into_target",
            side_effect=RuntimeError(_INJECTED_TARGET_FAILURE),
        ),
        _revert_forced_to_fail() as intercepted,
    ):
        try:
            _run_lane_based_merge(
                repo_root=repo,
                mission_slug=MISSION_SLUG,
                push=False,
                delete_branch=False,
                remove_worktree=False,
                strategy=MergeStrategy.SQUASH,
                allow_sparse_checkout=True,
            )
        except BaseException as exc:  # noqa: BLE001 — the act under test raises by design
            return exc, intercepted
    raise AssertionError(
        "precondition: injected target-advance failure did not propagate — the "
        "merge unexpectedly succeeded, so the #2711/#2786 rollback path never ran."
    )


def test_swallowed_revert_failure_re_opens_2711_split_brain(tmp_path: Path) -> None:
    """#2786 (RED): a FAILED coord ``done`` revert during rollback is swallowed,
    leaving the committed coordination ``done`` opposed to the rolled-back working
    ``approved`` — the #2711 split-brain re-opened along the revert-failure path.

    RED-for-the-right-reason contract: the committed coordination reduction and the
    working-tree reduction must AGREE after rollback. On ``main`` today they
    disagree because ``_revert_coord_done_commit`` logs a warning and returns on a
    non-zero ``git revert`` without raising or writing a durable reconcile marker.
    The #2786 fix (fail-loud or durable reconcile marker on revert failure) flips
    this GREEN.
    """
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    feature_dir = _bootstrap_coord_mission(repo)

    # Non-vacuity witness A (BEFORE the act): the mission routes status onto the
    # coordination worktree, so a ``done`` is committed pre-target.
    _assert_pre_target_done_path(repo)

    exc, revert_cmds = _run_merge_with_target_and_revert_failing(repo)

    # Non-vacuity witness B: the merge failed via the injected target-advance fault
    # (AFTER the pre-target ``done`` commit), so a ``done`` genuinely landed.
    assert isinstance(exc, RuntimeError) and _INJECTED_TARGET_FAILURE in str(exc), (
        "precondition: the merge must fail via the injected target-advance fault "
        f"(RuntimeError, AFTER the pre-target done commit); got {exc!r}"
    )

    # Non-vacuity witness C: the swallowed-revert branch was genuinely exercised —
    # the coord-worktree ``git revert`` was attempted and forced to return non-zero.
    assert revert_cmds, (
        "precondition: the coord ``done`` revert was never attempted, so the "
        "#2786 revert-failure branch (_revert_coord_done_commit) did not run — "
        "the reproduction would be vacuous."
    )

    committed_events = _committed_coord_events(repo, feature_dir)
    working_events = _working_coord_events(repo)
    committed_lane, _ = wp_lane_actor_from_events(committed_events, WP_ID)
    working_lane, _ = wp_lane_actor_from_events(working_events, WP_ID)

    # Precondition: the working tree DID roll back to ``approved`` (the byte-restore
    # leg still runs after the swallowed revert failure).
    assert working_lane == Lane.APPROVED, (
        "precondition: the rolled-back working tree should reduce to ``approved``; "
        f"got {working_lane}"
    )

    # Coherence CONTRACT (RED on main): a swallowed revert failure must NOT strand
    # the committed coordination ``done`` opposed to the working ``approved``.
    assert committed_lane == working_lane, (
        "#2786 swallowed-revert split-brain: the coord-worktree ``git revert`` "
        "FAILED during rollback and _revert_coord_done_commit swallowed it "
        "(warning + return, no raise, no durable reconcile marker), so the "
        "committed coordination ``done`` was left stranded against the rolled-back "
        "working ``approved``.\n"
        f"  committed coord ref (git-tracked): {committed_lane}\n"
        f"  rolled-back working tree:          {working_lane}\n"
        "The revert-failure path must fail loud or record a durable reconcile "
        "marker so the divergence is never silent (#2786)."
    )
