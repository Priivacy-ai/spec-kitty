"""WP01/T001 — pin the lane-planning data-loss regression (FR-001).

This file holds two layers of regression pins:

1. ``TestMergeIncludesPlanningLane`` — the **bookkeeping** assertion: every WP
   from every lane (planning + code) must appear in ``MergeState.wp_order``
   and reach the per-WP ``_mark_wp_merged_done`` pass. This layer mocks out
   ``merge_lane_to_mission`` / ``merge_mission_to_target`` so the merge plan
   can be inspected without a real on-disk merge.

2. ``TestPlanningArtifactReachesTarget`` — the **load-bearing** assertion:
   the planning-artifact file MUST be present on the target branch (``main``)
   after ``_run_lane_based_merge`` returns. This layer drives the **real**
   ``merge_lane_to_mission`` / ``merge_mission_to_target`` / ``_merge_branch_into``
   functions against a real on-disk git repository. It mocks ONLY the side
   effects that touch state outside git (status emit, dossier sync, SaaS
   emit, stale-assertion check, sparse-checkout preflight, merge gates,
   post-merge invariants) — the merge itself runs through real ``git merge``.

   The negative case in the same class proves the documented design boundary
   from research.md D4: planning artifacts that live on a phantom
   ``kitty/mission-<slug>-lane-planning`` branch (instead of on the
   ``planning_base_branch`` as the design requires) do **not** reach the
   target branch.  This is by design — ``lane_branch_name("lane-planning",
   planning_base_branch="main")`` returns ``"main"``, so the merge never
   visits a separate planning lane branch.
"""

from __future__ import annotations

import contextlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.cli.commands.merge import _run_lane_based_merge
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import write_lanes_json
from specify_cli.merge.config import MergeStrategy


pytestmark = [pytest.mark.git_repo, pytest.mark.non_sandbox]


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_git_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-qb", "main", str(repo)])
    _run(["git", "-C", str(repo), "config", "user.email", "test@test.com"])
    _run(["git", "-C", str(repo), "config", "user.name", "Test"])
    _run(["git", "-C", str(repo), "config", "commit.gpgsign", "false"])
    (repo / "README.md").write_text("init\n")
    _run(["git", "-C", str(repo), "add", "."])
    _run(["git", "-C", str(repo), "commit", "-m", "init"])


def _make_manifest_with_planning_and_code(slug: str) -> MagicMock:
    """Build a fake LanesManifest with three code WPs and one planning-artifact WP."""
    manifest = MagicMock()
    manifest.target_branch = "main"
    manifest.mission_branch = f"kitty/mission-{slug}"

    lane_a = MagicMock()
    lane_a.lane_id = "lane-a"
    lane_a.wp_ids = ["WP01", "WP02", "WP03"]

    lane_planning = MagicMock()
    lane_planning.lane_id = "lane-planning"
    lane_planning.wp_ids = ["WP04"]

    manifest.lanes = [lane_a, lane_planning]
    return manifest


# ---------------------------------------------------------------------------
# Layer 1 — bookkeeping (mocked merge functions)
# ---------------------------------------------------------------------------


class TestMergeIncludesPlanningLane:
    """FR-001 bookkeeping: planning-lane WPs MUST appear in MergeState wp_order
    and must reach the per-WP mark-done pass.

    This layer mocks ``merge_lane_to_mission`` and ``merge_mission_to_target``
    so we can inspect the plan without driving real git.  It is the
    fast-feedback regression pin for the lane-iteration / WP-iteration loops.
    """

    def test_merge_state_wp_order_includes_planning_lane_wps(self, tmp_path: Path) -> None:
        slug = "test-planning-data-loss"
        _init_git_repo(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / slug
        feature_dir.mkdir(parents=True)

        manifest = _make_manifest_with_planning_and_code(slug)

        captured_states: list[list[str]] = []

        def fake_save_state(state, repo_root):  # noqa: ANN001
            # Capture wp_order on every save so we can assert what was committed.
            captured_states.append(list(state.wp_order))

        lane_result = MagicMock()
        lane_result.success = True
        lane_result.errors = []

        mission_result = MagicMock()
        mission_result.success = True
        mission_result.commit = "abc1234"
        mission_result.errors = []

        completed_wps_seen: list[str] = []

        def fake_mark_wp_merged_done(repo_root, mission_slug, wp_id, target_branch):  # noqa: ANN001
            completed_wps_seen.append(wp_id)

        def fake_run_command(cmd, *args, **kwargs):  # noqa: ANN001
            if "merge-base" in cmd:
                return (0, "abc123\n", "")
            return (0, "", "")

        patches = [
            patch("specify_cli.cli.commands.merge.require_lanes_json", return_value=manifest),
            patch("specify_cli.cli.commands.merge.load_state", return_value=None),
            patch("specify_cli.cli.commands.merge.save_state", side_effect=fake_save_state),
            patch("specify_cli.cli.commands.merge.get_main_repo_root", return_value=tmp_path),
            patch("specify_cli.cli.commands.merge.require_no_sparse_checkout"),
            patch("specify_cli.lanes.merge.merge_lane_to_mission", return_value=lane_result),
            patch("specify_cli.lanes.merge.merge_mission_to_target", return_value=mission_result),
            patch("specify_cli.cli.commands.merge._mark_wp_merged_done", side_effect=fake_mark_wp_merged_done),
            patch("specify_cli.cli.commands.merge.safe_commit"),
            patch("specify_cli.cli.commands.merge._assert_merged_wps_reached_done"),
            patch("specify_cli.post_merge.stale_assertions.run_check"),
            patch("specify_cli.policy.merge_gates.evaluate_merge_gates"),
            patch("specify_cli.policy.config.load_policy_config"),
            patch("specify_cli.cli.commands.merge.run_command", side_effect=fake_run_command),
            patch("specify_cli.cli.commands.merge.has_remote", return_value=False),
            patch("specify_cli.cli.commands.merge.cleanup_merge_workspace"),
            patch("specify_cli.cli.commands.merge.clear_state"),
            patch("specify_cli.cli.commands.merge._bake_mission_number_into_mission_branch"),
            patch("specify_cli.cli.commands.merge.trigger_feature_dossier_sync_if_enabled"),
            patch("specify_cli.cli.commands.merge.emit_mission_closed"),
            patch("specify_cli.cli.commands.merge._emit_merge_diff_summary"),
        ]
        with contextlib.ExitStack() as stack:
            mocks = [stack.enter_context(p) for p in patches]
            mock_run_check = mocks[10]
            mock_gates = mocks[11]
            mock_policy = mocks[12]

            stale_report = MagicMock()
            stale_report.findings = []
            mock_run_check.return_value = stale_report

            gate_eval = MagicMock()
            gate_eval.overall_pass = True
            gate_eval.gates = []
            mock_gates.return_value = gate_eval

            policy = MagicMock()
            policy.merge_gates = []
            mock_policy.return_value = policy

            _run_lane_based_merge(
                repo_root=tmp_path,
                mission_slug=slug,
                push=False,
                delete_branch=False,
                remove_worktree=False,
                strategy=MergeStrategy.SQUASH,
            )

        # FR-001 assertion 1: every initial save must include all WPs from
        # both code AND planning lanes.
        assert captured_states, "save_state was never called — merge state never persisted"
        first_state = captured_states[0]
        assert set(first_state) == {"WP01", "WP02", "WP03", "WP04"}, (
            f"FR-001 regression: MergeState.wp_order does not contain every WP "
            f"from every lane. Got {first_state!r}, expected all of WP01..WP04 "
            f"(WP04 is in lane-planning and must NOT be silently dropped)."
        )

        # FR-001 assertion 2: the planning-lane WP must reach the per-WP
        # mark-done loop.
        assert "WP04" in completed_wps_seen, (
            f"FR-001 regression: WP04 (lane-planning) was not marked done. "
            f"Marked WPs: {completed_wps_seen!r}. The planning lane was either "
            "skipped in the lane iteration or its WPs were filtered out of the "
            "completion pass."
        )

        # And the code-lane WPs were all marked too.
        for wp in ("WP01", "WP02", "WP03"):
            assert wp in completed_wps_seen, f"{wp} was dropped from the merge"


# ---------------------------------------------------------------------------
# Layer 2 — real merge against real git (no mocks of merge_lane_to_mission /
# merge_mission_to_target / _merge_branch_into).
# ---------------------------------------------------------------------------


def _write_meta(feature_dir: Path, slug: str) -> None:
    """Write a minimal meta.json for a mission directory."""
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "mission_slug": slug,
        "mission_number": None,
        "mission_type": "software-dev",
        "target_branch": "main",
        "purpose_tldr": "data-loss regression pin",
        "purpose_context": "real-merge planning-artifact reach-target test",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_lanes_manifest(
    feature_dir: Path,
    slug: str,
    *,
    code_wp_ids: list[str],
    planning_wp_ids: list[str],
    target_branch: str = "main",
    mission_branch: str | None = None,
) -> LanesManifest:
    """Build a real LanesManifest with a code lane and a planning lane and write it to disk."""
    if mission_branch is None:
        mission_branch = f"kitty/mission-{slug}"
    lanes: list[ExecutionLane] = [
        ExecutionLane(
            lane_id="lane-a",
            wp_ids=tuple(code_wp_ids),
            write_scope=("src/foo.py",),
            predicted_surfaces=("code",),
            depends_on_lanes=(),
            parallel_group=0,
        )
    ]
    if planning_wp_ids:
        lanes.append(
            ExecutionLane(
                lane_id="lane-planning",
                wp_ids=tuple(planning_wp_ids),
                write_scope=(),
                predicted_surfaces=("planning",),
                depends_on_lanes=(),
                parallel_group=0,
            )
        )
    manifest = LanesManifest(
        version=1,
        mission_slug=slug,
        mission_id=slug,  # legacy form: mission_id == mission_slug
        mission_branch=mission_branch,
        target_branch=target_branch,
        lanes=lanes,
        computed_at=datetime.now(UTC).isoformat(),
        computed_from="test-fixture",
    )
    write_lanes_json(feature_dir, manifest)
    return manifest


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return _run(["git", "-C", str(repo), *args])


def _commit_file(
    repo: Path,
    *,
    branch: str,
    relpath: str,
    content: str,
    message: str,
) -> str:
    """Check out *branch*, write *relpath* with *content*, commit, return the commit SHA."""
    _git(repo, "checkout", branch)
    target = repo / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    _git(repo, "add", relpath)
    _git(repo, "commit", "-m", message)
    sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    return sha


def _file_on_branch(repo: Path, branch: str, relpath: str) -> bool:
    """Return True iff *relpath* exists on *branch* (via ``git ls-tree``)."""
    result = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "--name-only", "-r", branch, "--", relpath],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and relpath in result.stdout.splitlines()


@contextlib.contextmanager
def _real_merge_external_mocks(repo_root: Path):
    """Mock only the side effects that touch state OUTSIDE git.

    The real merge_lane_to_mission, merge_mission_to_target, and
    _merge_branch_into are NOT mocked — they execute real ``git merge``.
    """
    patches = [
        # External side effects (status emit, dossier, SaaS, stale-assertion check)
        patch("specify_cli.cli.commands.merge._mark_wp_merged_done"),
        patch("specify_cli.cli.commands.merge._assert_merged_wps_reached_done"),
        patch("specify_cli.cli.commands.merge.safe_commit"),
        patch("specify_cli.cli.commands.merge.trigger_feature_dossier_sync_if_enabled"),
        patch("specify_cli.cli.commands.merge.emit_mission_closed"),
        patch("specify_cli.cli.commands.merge._emit_merge_diff_summary"),
        patch("specify_cli.post_merge.stale_assertions.run_check"),
        patch("specify_cli.cli.commands.merge.run_check"),
        # Preflight / gates / policy / sparse-checkout — out of scope for
        # this data-loss regression
        patch("specify_cli.cli.commands.merge.require_no_sparse_checkout"),
        patch("specify_cli.cli.commands.merge._enforce_git_preflight"),
        patch("specify_cli.policy.merge_gates.evaluate_merge_gates"),
        patch("specify_cli.policy.config.load_policy_config"),
        # mission_number assignment scans kitty-specs/ and rewrites meta.json on
        # the mission branch via a temp worktree — not the focus of the
        # data-loss regression.  Keep it out of the way.
        patch("specify_cli.cli.commands.merge._bake_mission_number_into_mission_branch", return_value=None),
        # Post-merge invariant fires on `git status --porcelain` output that
        # includes the test-only files — short-circuit it for this test.
        # The merge has already run through real git by the time this would
        # raise.
        patch("specify_cli.cli.commands.merge._classify_porcelain_lines", return_value=([], 0)),
    ]
    with contextlib.ExitStack() as stack:
        ms = [stack.enter_context(p) for p in patches]
        gate_eval = MagicMock()
        gate_eval.overall_pass = True
        gate_eval.gates = []
        ms[10].return_value = gate_eval
        policy = MagicMock()
        policy.merge_gates = []
        ms[11].return_value = policy
        stale_report = MagicMock()
        stale_report.findings = []
        ms[6].return_value = stale_report
        ms[7].return_value = stale_report
        yield


class TestPlanningArtifactReachesTarget:
    """FR-001 load-bearing: planning-artifact files MUST end up on the target
    branch after ``_run_lane_based_merge`` runs against real git.

    These tests do NOT mock merge_lane_to_mission, merge_mission_to_target,
    or _merge_branch_into — they exercise real ``git merge``, real branch
    refs, and real worktrees.  They mock only the side effects that touch
    state outside git (status emit, dossier sync, SaaS emit, etc.).
    """

    def test_planning_artifact_on_main_reaches_target_after_merge(self, tmp_path: Path) -> None:
        """Design-correct case: planning artifact lives on planning_base (main).

        Per research.md D4, planning_artifact WPs "execute in the canonical
        repo with workspace_path: null" — so the artifact lives on the
        planning_base branch (typically main) and ``lane_branch_name(
        "lane-planning", planning_base_branch="main")`` returns ``"main"``
        so that ``merge_lane_to_mission`` for ``lane-planning`` brings any
        new commits from main into the mission branch (so the mission→main
        merge sees them).

        This test proves that:

        1. A code commit on lane-a reaches main.
        2. A planning-artifact commit committed on main BEFORE the merge
           survives the merge and is still on main afterward.
        """
        slug = "real-merge-planning-design-correct"
        _init_git_repo(tmp_path)

        feature_dir = tmp_path / "kitty-specs" / slug
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks").mkdir(parents=True)
        _write_meta(feature_dir, slug)

        # Commit the lanes.json on main so it is visible to require_lanes_json.
        _write_lanes_manifest(
            feature_dir,
            slug,
            code_wp_ids=["WP01"],
            planning_wp_ids=["WP02"],
        )
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", f"chore({slug}): bootstrap mission fixture")

        # Commit a real planning artifact on main BEFORE the merge starts.
        # Per D4, this is the design-correct location for planning artifacts.
        planning_relpath = f"kitty-specs/{slug}/research/decision-A.md"
        _commit_file(
            tmp_path,
            branch="main",
            relpath=planning_relpath,
            content="# Decision A\n\nPlanning artifact body.\n",
            message=f"plan({slug}): commit planning artifact on planning_base",
        )

        # Create the mission branch from main.
        mission_branch = f"kitty/mission-{slug}"
        _git(tmp_path, "branch", mission_branch, "main")

        # Create the lane-a branch from main and add a real code commit.
        lane_a_branch = f"kitty/mission-{slug}-lane-a"
        _git(tmp_path, "branch", lane_a_branch, "main")
        code_relpath = "src/foo.py"
        _commit_file(
            tmp_path,
            branch=lane_a_branch,
            relpath=code_relpath,
            content="def foo():\n    return 1\n",
            message=f"feat({slug}): add foo function (WP01)",
        )

        # Return to main so the merge command does not run from a feature branch.
        _git(tmp_path, "checkout", "main")

        # Drive the real merge.  No mocks of merge_lane_to_mission /
        # merge_mission_to_target / _merge_branch_into.
        with _real_merge_external_mocks(tmp_path):
            _run_lane_based_merge(
                repo_root=tmp_path,
                mission_slug=slug,
                push=False,
                delete_branch=False,
                remove_worktree=False,
                strategy=MergeStrategy.SQUASH,
                allow_sparse_checkout=True,  # bypass preflight (already mocked)
            )

        # The actual data-loss check.  Both files must be on main after merge.
        assert _file_on_branch(tmp_path, "main", code_relpath), (
            f"FR-001 regression: code file {code_relpath} did not reach main after merge.  ``git ls-tree main -- {code_relpath}`` returned empty."
        )
        assert _file_on_branch(tmp_path, "main", planning_relpath), (
            f"FR-001 regression (load-bearing): planning artifact "
            f"{planning_relpath} was DROPPED from main during the merge.  "
            f"It was committed to main before the merge, but it is not "
            f"present on main afterward.  This is the silent-data-loss case "
            f"FR-001 forbids."
        )

    def test_planning_artifact_on_phantom_lane_branch_is_NOT_reached(self, tmp_path: Path) -> None:
        """Design-boundary negative case (research.md D4).

        Per ``lane_branch_name``, ``lane-planning`` resolves to the
        ``planning_base_branch`` (typically ``main``), NOT to a separate
        ``kitty/mission-<slug>-lane-planning`` branch.  Operators who
        accidentally commit planning artifacts to such a phantom branch
        will lose them at merge time — the merge never visits that branch.

        This test pins that boundary as a known limitation: planning
        artifacts MUST live on ``planning_base`` (main), not on a phantom
        lane-planning branch.
        """
        slug = "real-merge-planning-phantom-branch"
        _init_git_repo(tmp_path)

        feature_dir = tmp_path / "kitty-specs" / slug
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks").mkdir(parents=True)
        _write_meta(feature_dir, slug)

        _write_lanes_manifest(
            feature_dir,
            slug,
            code_wp_ids=["WP01"],
            planning_wp_ids=["WP02"],
        )
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", f"chore({slug}): bootstrap mission fixture")

        # Mission branch from main.
        mission_branch = f"kitty/mission-{slug}"
        _git(tmp_path, "branch", mission_branch, "main")

        # Code lane: real code commit.
        lane_a_branch = f"kitty/mission-{slug}-lane-a"
        _git(tmp_path, "branch", lane_a_branch, "main")
        code_relpath = "src/foo.py"
        _commit_file(
            tmp_path,
            branch=lane_a_branch,
            relpath=code_relpath,
            content="def foo():\n    return 1\n",
            message=f"feat({slug}): add foo function (WP01)",
        )

        # PHANTOM lane-planning branch — this is the misuse case.
        # The planning artifact lives ONLY here, not on main.
        phantom_planning_branch = f"kitty/mission-{slug}-lane-planning"
        _git(tmp_path, "branch", phantom_planning_branch, "main")
        orphan_relpath = f"kitty-specs/{slug}/research/orphaned-decision.md"
        _commit_file(
            tmp_path,
            branch=phantom_planning_branch,
            relpath=orphan_relpath,
            content="# Orphaned\n\nThis file lives on the phantom branch.\n",
            message=f"plan({slug}): commit planning artifact on PHANTOM branch (anti-pattern)",
        )

        _git(tmp_path, "checkout", "main")

        with _real_merge_external_mocks(tmp_path):
            _run_lane_based_merge(
                repo_root=tmp_path,
                mission_slug=slug,
                push=False,
                delete_branch=False,
                remove_worktree=False,
                strategy=MergeStrategy.SQUASH,
                allow_sparse_checkout=True,
            )

        # Code file did reach main.
        assert _file_on_branch(tmp_path, "main", code_relpath), "Sanity: code file from lane-a should still reach main."

        # Phantom planning artifact did NOT reach main — by design.
        # ``lane_branch_name("lane-planning", planning_base_branch="main")``
        # returns ``"main"``, so the merge never visits the phantom branch.
        # This is the documented design limitation we are pinning.
        assert not _file_on_branch(tmp_path, "main", orphan_relpath), (
            "Design-boundary regression: a planning artifact committed only "
            f"on the phantom branch {phantom_planning_branch} unexpectedly "
            f"reached main.  Per research.md D4, planning artifacts must "
            f"live on planning_base (main), and the merge does not visit a "
            f"separate ``kitty/mission-<slug>-lane-planning`` branch.  If "
            f"this assertion starts failing, the design has changed and the "
            f"D4 documentation must be updated."
        )
