"""Regression for #2993: a fresh lane worktree does not descend from the
mission's own planning artifacts (spec.md/tasks.md/meta.json).

Root cause (traced against ``main`` @ upstream/main, WP03 read-side-seam
mission): ``_ensure_planning_artifacts_committed_git``
(``src/specify_cli/cli/commands/implement.py:626-714``) decides what to
auto-commit onto the coordination branch via
``resolve_planning_artifact_staging`` (``implement_cores.py:544-609``). When
the planning artifacts are *already* committed on the planning/primary
branch (the normal spec -> plan -> tasks authoring flow, NOT a dirty
uncommitted edit), ``git status --porcelain`` is clean, so
``_status_paths_for_commit`` contributes nothing. The only other source is
``extra_file_paths`` (a plain filesystem walk of every file currently under
the mission dir), which is then filtered by
``_files_changed_vs_precondition_ref`` -> ``resolve_precondition_ref``
(``implement_cores.py:299-327``). ``resolve_precondition_ref`` classifies
``spec.md`` / ``tasks.md`` / ``meta.json`` as PRIMARY-kind (not
``is_coord_residue_churn``), so they are diffed against ``HEAD`` -- the
planning branch itself, where they are already committed and therefore
byte-identical. They are silently dropped from ``files_to_commit``, which
becomes empty, and the function no-ops (``implement.py:691-692``). The
coordination branch's tip is left exactly where ``ensure_coordination_branch``
minted it -- BEFORE the planning artifacts ever existed. When
``allocate_lane_worktree`` later branches the lane off that coordination
branch (``worktree_allocator.py:213-216``, ``_ensure_branch_exists`` is a
no-op because the branch already exists, ``_create_lane_worktree`` runs
``git worktree add -b <lane> <path> <coordination_branch>``), the resulting
lane branch never contains the planning artifacts at all.

This test drives the four real production entry points named in the mission
ticket, in the exact order that reproduces the defect:

1. ``ensure_coordination_branch`` -- mint the coord branch BEFORE the
   planning artifacts exist.
2. A normal ``git commit`` of ``kitty-specs/<slug>/{spec.md,tasks.md,
   meta.json}`` onto the planning branch (captures the sha).
3. ``_ensure_planning_artifacts_committed_git`` -- the auto-commit helper,
   called exactly as the legacy (``placement_ref=None``) fallback path in
   ``implement.py:1706`` invokes it when context resolution fails
   (``_resolve_placement_ref`` returns ``None`` on ``ActionContextError``,
   ``implement_cores.py:617-637``).
4. ``allocate_lane_worktree`` -- the real WP04 lane allocator.

Related existing coverage this test does NOT contradict:
``tests/specify_cli/cli/commands/test_implement.py:471-545``
(``TestPlanningArtifactAutoCommit.test_auto_commit_uses_coordination_worktree_paths``)
pins a *different* precondition: there the planning artifact is written to
disk but never committed on the planning branch, so it IS picked up by
``git status --porcelain`` and correctly lands on the coordination branch.
That assertion is not disturbed here -- this test's planning artifacts are
committed BEFORE the auto-commit helper runs, which is the gap the existing
test does not cover. Whoever fixes #2993 should re-adjudicate that test only
if the fix changes what counts as "already committed" for the idempotency
filter.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.cli.commands.implement import _ensure_planning_artifacts_committed_git
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.worktree_allocator import allocate_lane_worktree
from specify_cli.missions._create import ensure_coordination_branch

pytestmark = [pytest.mark.regression, pytest.mark.git_repo]

MISSION_SLUG = "annoying-bugs-sweep-01KYHQ9F"
MISSION_ID = "01KYHQ9FTN3W7C5J4K2M6R8QDS"
MID8 = MISSION_ID[:8]
WP_ID = "WP03"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "seed")


def _write_meta(feature_dir: Path, *, coordination_branch: str) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "mission_id": MISSION_ID,
        "mission_slug": MISSION_SLUG,
        "mid8": MID8,
        "mission_type": "software-dev",
        "target_branch": "main",
        "created_at": "2026-07-28T00:00:00+00:00",
        "friendly_name": "Annoying bugs sweep",
        "coordination_branch": coordination_branch,
    }
    (feature_dir / "meta.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def _make_manifest(coordination_branch: str) -> LanesManifest:
    return LanesManifest(
        version=1,
        mission_slug=MISSION_SLUG,
        mission_id=MISSION_ID,
        mission_branch=coordination_branch,
        target_branch="main",
        lanes=[
            ExecutionLane(
                lane_id="lane-a",
                wp_ids=(WP_ID,),
                write_scope=("src/**",),
                predicted_surfaces=("core",),
                depends_on_lanes=(),
                parallel_group=0,
            )
        ],
        computed_at="2026-07-28T10:00:00Z",
        computed_from="test",
    )


def test_lane_worktree_does_not_descend_from_planning_artifacts(
    tmp_path: Path,
) -> None:
    """Pin #2993: the lane branch must contain the mission's own planning
    artifacts. Today it does not."""
    repo = tmp_path / "repo"
    _init_repo(repo)

    # Step 1: mint the coordination branch BEFORE the planning artifacts exist.
    coord_result = ensure_coordination_branch(
        repo_root=repo,
        mission_slug=MISSION_SLUG,
        mission_id=MISSION_ID,
        target_branch="main",
    )
    assert coord_result.created
    coord_branch = coord_result.branch_name

    # Step 2: commit the planning artifacts on the planning (primary) branch
    # -- a normal, already-committed spec/tasks authoring commit, not a dirty
    # uncommitted edit.
    feature_dir = repo / "kitty-specs" / MISSION_SLUG
    (feature_dir).mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec.md").write_text("# Annoying bugs sweep\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "## WP03 Ledger grammar and census\n\n- [ ] T001 Draft grammar\n",
        encoding="utf-8",
    )
    _write_meta(feature_dir, coordination_branch=coord_branch)
    _git(repo, "add", "kitty-specs")
    _git(repo, "commit", "-q", "-m", f"docs: spec+tasks for {MISSION_SLUG}")
    planning_artifact_sha = _git(repo, "rev-parse", "HEAD")

    # Step 3: run the real auto-commit helper, legacy (placement_ref=None)
    # fallback path -- exactly as implement.py falls back to when
    # _resolve_placement_ref's context resolution fails.
    _ensure_planning_artifacts_committed_git(
        repo_root=repo,
        feature_dir=feature_dir,
        mission_slug=MISSION_SLUG,
        wp_id=WP_ID,
        planning_branch="main",
        auto_commit=True,
    )

    # Step 4: allocate the lane worktree -- the real WP04 lane allocator.
    manifest = _make_manifest(coord_branch)
    worktree_path, lane_branch = allocate_lane_worktree(
        repo_root=repo,
        mission_slug=MISSION_SLUG,
        wp_id=WP_ID,
        lanes_manifest=manifest,
    )
    assert worktree_path.exists()

    # Assert A -- ancestry: the lane branch must descend from the commit that
    # introduced the planning artifacts.
    ancestry = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "merge-base",
            "--is-ancestor",
            planning_artifact_sha,
            lane_branch,
        ],
        capture_output=True,
        text=True,
    )
    assert ancestry.returncode == 0, (
        f"lane branch {lane_branch!r} should descend from the planning-artifact "
        f"commit {planning_artifact_sha}, but `git merge-base --is-ancestor` "
        f"returned {ancestry.returncode} (stderr: {ancestry.stderr!r}). This is "
        "the #2993 defect: the coordination branch tip was never advanced past "
        "its pre-artifact mint point before the lane branched off it."
    )

    # Assert B -- silent-revert half: amend tasks.md on the planning branch
    # AFTER the lane exists, then union-merge the two branches. A healthy
    # lane (containing the original tasks.md as an ancestor state) merges
    # cleanly and picks up the amendment. Today the lane's tree has no
    # tasks.md at all, so the merge fabricates a stale/absent result instead
    # of the amended text.
    (feature_dir / "tasks.md").write_text(
        "## WP03 Ledger grammar and census (amended)\n\n"
        "- [ ] T001 Draft grammar\n- [ ] T002 Census sweep\n",
        encoding="utf-8",
    )
    _git(repo, "add", "kitty-specs")
    _git(repo, "commit", "-q", "-m", "docs: amend tasks.md for WP03")

    merge_tree = subprocess.run(
        ["git", "-C", str(repo), "merge-tree", "--write-tree", lane_branch, "main"],
        capture_output=True,
        text=True,
    )
    assert merge_tree.returncode == 0, (
        "expected a clean union-merge between the lane branch and the amended "
        f"planning branch under kitty-specs/, got a conflict:\n{merge_tree.stdout}"
        f"\n{merge_tree.stderr}"
    )
    merged_tree_sha = merge_tree.stdout.strip().splitlines()[0]

    show = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "show",
            f"{merged_tree_sha}:kitty-specs/{MISSION_SLUG}/tasks.md",
        ],
        capture_output=True,
        text=True,
    )
    assert show.returncode == 0, (
        f"tasks.md missing from the union-merge tree entirely: {show.stderr!r}"
    )
    assert show.stdout == (
        "## WP03 Ledger grammar and census (amended)\n\n"
        "- [ ] T001 Draft grammar\n- [ ] T002 Census sweep\n"
    ), (
        "the union-merge should carry forward the amended tasks.md; instead it "
        f"kept the lane's stale copy:\n{show.stdout!r}"
    )
