"""Issue #3784 (FIXED) — permanent guard: a ``.worktrees/`` coord-surface path
(``tasks.md``) must never reach a PRIMARY-surface ``safe_commit`` bundle on a
coord-topology mission.

WHAT WAS REPORTED (now fixed)
-----------------------------
On a coord-topology mission (``meta.json`` ``topology: "coord"``,
``"flattened": false``, coordination worktree at ``.worktrees/<slug>-coord/``),
a lane transition's own auto-commit of the WP prompt file was refused with::

    safe_commit: refusing to stage path under .worktrees/:
    .worktrees/<slug>-coord/kitty-specs/<slug>/tasks.md.
    Planning artifacts must be committed from the coordination worktree,
    not the primary repo root.

The lane transition itself succeeded (the status event landed on the coordination
branch); only the primary-surface auto-commit was lost, leaving a dirty tree —
violating the "the tool drives the commits" contract.

ROOT CAUSE (fixed on this branch)
---------------------------------
``_collect_status_artifacts(feature_dir)``
(``src/specify_cli/cli/commands/agent/tasks_materialization.py``) returns THREE
existing artifacts: ``status.events.jsonl``, ``status.json``, AND ``tasks.md``.
On coord topology ``feature_dir`` is the coordination worktree
(``.worktrees/<slug>-coord/kitty-specs/<slug>/``), so ``tasks.md`` is a
``.worktrees/`` path.

The primary-surface claim-commit caller,
``src/specify_cli/cli/commands/implement.py`` (``_commit_wp_claim_status``),
bundles those artifacts for a ``safe_commit`` executed with
``worktree_root = repo_root``. It used to drop only the coord-owned STATUS_STATE
files with ``is_status_state_path`` (matching EXACTLY ``status.events.jsonl`` /
``status.json``) and NOT ``tasks.md`` (a ``TASKS_INDEX`` kind) — so ``tasks.md``
survived the filter into the bundle and tripped ``SafeCommitPathPolicyError``.

THE FIX
-------
``implement._primary_surface_status_paths`` now drops ANY ``.worktrees/``-nested
path on coord topology (``is_status_state_path(path) or
is_under_worktrees_segment(path)``), keeping the #2155 invariant whole: NO
``.worktrees/``-nested path may enter a primary-root ``safe_commit`` bundle.
Dropping the coord-worktree ``tasks.md`` from the CLAIM commit is correct — at
claim time it is unchanged and the primary copy was already committed at finalize.

This guard drives the REAL ``_do_move_task`` entry point (the #2939 coord-topology
harness) and the REAL ``_collect_status_artifacts`` / product
``_primary_surface_status_paths`` filter / ``safe_commit`` production surfaces —
no stubbed router, no patched resolver. GREEN today (defect fixed); it fails again
only if the coord ``.worktrees/`` exclusion regresses.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from mission_runtime import CommitTarget

from specify_cli.cli.commands.agent.tasks import (
    _collect_status_artifacts,
    _do_move_task,
    _MoveTaskArgs,
)
from specify_cli.cli.commands.implement import _primary_surface_status_paths
from specify_cli.git import safe_commit
from specify_cli.git.commit_helpers import (
    SafeCommitError,
    SafeCommitPathPolicyError,
)
from specify_cli.status import materialize as _materialize
from tests.integration.coord_topology_fixture import (
    CoordTopologyContext,
    _build_coord_topology,
)
from tests.integration.test_review_durability_matrix import (
    _REVIEW_GATE_BYPASS,
    _coord_cell_ports,
    _disable_branch_protection_for_coord_cell,
)
from tests.mocked_env import setup_mocked_env
from tests.specify_cli.cli.commands.agent.test_move_task_durability import (
    _FaultInjectableCoordRouter,
    _seed_wp_event,
)

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_WP_ID = "WP01"


def _run_move(
    ctx: CoordTopologyContext,
    router: _FaultInjectableCoordRouter,
    *,
    to: str,
    note: str | None = None,
) -> None:
    """Drive the REAL ``_do_move_task`` on the coord fixture (mirrors #2939)."""
    with setup_mocked_env(
        ctx.repo,
        mission_slug=ctx.slug,
        target_branch="main",
        extra_patches=dict(_REVIEW_GATE_BYPASS),
    ):
        _do_move_task(
            _MoveTaskArgs(
                task_id=_WP_ID,
                to=to,
                mission=ctx.slug,
                agent=None,
                assignee=None,
                shell_pid=None,
                note=note,
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


def _is_under_worktrees(path: Path, repo_root: Path) -> bool:
    """True iff *path* lives under ``<repo_root>/.worktrees/`` (a coord surface)."""
    try:
        rel = path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return False
    return bool(rel.parts) and rel.parts[0] == ".worktrees"


@pytest.mark.integration
@pytest.mark.git_repo
def test_coord_surface_tasks_md_never_reaches_primary_safe_commit_bundle(
    tmp_path: Path,
) -> None:
    """#3784 (fixed) — a coord-surface ``tasks.md`` must never survive into a
    primary-surface ``safe_commit`` bundle.

    ``_collect_status_artifacts`` returns the coord-worktree ``tasks.md`` next to
    the two status files; the product ``_primary_surface_status_paths`` filter (as
    ``implement.py``'s claim-commit applies it) now drops ANY ``.worktrees/``-nested
    path on coord topology, so ``tasks.md`` never reaches the bundle and the real
    ``safe_commit`` raises no ``SafeCommitPathPolicyError``.
    """
    # --- Realistic coord-topology mission (real coord worktree, no stubs). ---
    ctx = _build_coord_topology(tmp_path, write_husk_meta=False)
    _disable_branch_protection_for_coord_cell(ctx.repo)

    # Seed WP01 in_progress on the authoritative coord status log.
    ctx.status_events_path.unlink()
    _seed_wp_event(ctx.coord_feature_dir, _WP_ID, "in_progress", seq=0)

    # ``tasks-finalize`` leaves a ``tasks.md`` in the coordination worktree's
    # mission dir (step 3 of the issue's reproduction). Create it there so the
    # coord surface matches a real post-finalize mission.
    coord_tasks_md = ctx.coord_feature_dir / "tasks.md"
    coord_tasks_md.write_text("# Tasks\n\n- [ ] WP01\n", encoding="utf-8")

    # --- Drive the REAL move-task lane transition (the entry point the issue
    # names). It succeeds and — post the IC-04 event-only cutover — leaves the
    # primary WP file untouched: a precondition, NOT the assertion. ---
    router = _FaultInjectableCoordRouter(write_dir=ctx.coord_feature_dir)
    _run_move(ctx, router, to="for_review", note="Ready for review.")

    primary_wp_file = ctx.primary_feature_dir / "tasks" / f"{_WP_ID}.md"
    assert primary_wp_file.exists(), (
        "precondition: the primary WP prompt file must exist for the claim-commit "
        "bundle"
    )

    # --- Rebuild the PRIMARY-surface bundle EXACTLY as the live coord claim-commit
    # caller does (implement._commit_wp_claim_status): collect status artifacts from
    # the (coord) feature_dir and run the PRODUCT ``_primary_surface_status_paths``
    # filter with ``routes_through_coord=True`` (this mission's genuine topology). ---
    _materialize(ctx.coord_feature_dir)  # status.json now exists alongside the log
    collected = _collect_status_artifacts(ctx.coord_feature_dir)
    assert coord_tasks_md.resolve() in {p.resolve() for p in collected}, (
        "precondition: _collect_status_artifacts must return the coord tasks.md "
        f"(returned {[p.name for p in collected]})"
    )
    status_paths = _primary_surface_status_paths(collected, routes_through_coord=True)
    # Make the primary WP file dirty so, with the coord tasks.md correctly
    # dropped, there is a legitimate primary change to commit.
    primary_wp_file.write_text(
        primary_wp_file.read_text(encoding="utf-8") + "\n<!-- #3784 -->\n",
        encoding="utf-8",
    )
    bundle = [primary_wp_file.resolve(), *status_paths]

    # (a) Deterministic invariant: no coord (.worktrees/) path may reach the
    #     primary-surface bundle.
    offending = [str(p) for p in bundle if _is_under_worktrees(p, ctx.repo)]
    assert not offending, (
        "#3784: a coord-surface .worktrees/ path (tasks.md) survived the "
        "_primary_surface_status_paths filter into the PRIMARY-surface safe_commit "
        "bundle. The coord-topology exclusion must drop ANY .worktrees/-nested path "
        "(status.events.jsonl / status.json AND tasks.md). Offending path(s):\n  "
        + "\n  ".join(offending)
    )

    # (b) The documented symptom, through the real production surface: driving
    #     safe_commit with worktree_root=repo_root must NOT refuse a path under
    #     .worktrees/. Any OTHER safe_commit refusal (e.g. the protected-branch
    #     check that runs AFTER the path-policy check) is unrelated to this bug
    #     and is not treated as the failure.
    path_policy_refusal: SafeCommitPathPolicyError | None = None
    try:
        safe_commit(
            repo_root=ctx.repo,
            worktree_root=ctx.repo,
            target=CommitTarget(ref="main"),
            message="chore: Move WP01 to for_review (primary WP-file commit)",
            paths=tuple(bundle),
        )
    except SafeCommitPathPolicyError as exc:
        path_policy_refusal = exc
    except SafeCommitError:
        # A different, later safe_commit refusal (e.g. protected-branch): the
        # path-policy check already passed, so this bug is fixed for this bundle.
        pass

    assert path_policy_refusal is None, (
        "#3784: safe_commit refused the primary-surface bundle for a path under "
        f".worktrees/ — the documented coord-topology refusal:\n{path_policy_refusal}"
    )
