"""Atomicity regression for the allocator's multi-dependency lane merge (#1915).

When a dependent lane declares two or more dependency lanes, the allocator's
``_merge_dependency_lane_tips`` merges each dependency tip in turn. The #1915
defect: if an earlier dependency merges cleanly and a *later* dependency
conflicts, ``git merge --abort`` only undoes the conflicting merge — the
earlier clean dependency-merge commit SURVIVES on the lane worktree, leaving a
partially-propagated state the operator never asked for.

This module reproduces that surviving-commit bug RED-FIRST and locks the fix:
the whole dependency-merge loop is atomic — on ANY conflict the lane is reset
hard to the exact pre-loop ref, so no partial dependency merge survives.

It also asserts (T012) that the allocator routes the worktree path through the
WP01 ``worktree_path`` seam and emits a name byte-identical to the legacy
``f"{slug}-{lane}"`` grammar, asserted against the shared golden-value table.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.lanes.branch_naming import lane_branch_name, worktree_path
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.worktree_allocator import (
    DependencyLaneMergeConflictError,
    _merge_dependency_lane_tips,
    allocate_lane_worktree,
)
from tests.lanes.test_branch_naming_seam import GOLDEN_ROWS

pytestmark = pytest.mark.git_repo

MISSION_SLUG = "010-feat"
TARGET_BRANCH = "main"
SHARED_FILE = "shared.txt"


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=check,
    )


def _make_git_repo(path: Path) -> None:
    """Create a minimal git repo with an initial commit on ``main``."""
    _git(path, "init")
    _git(path, "config", "user.email", "test@test.com")
    _git(path, "config", "user.name", "Test")
    (path / "README.md").write_text("init\n")
    _git(path, "add", ".")
    _git(path, "commit", "-m", "init")
    _git(path, "branch", "-M", "main")


def _commit_on_branch(repo: Path, branch: str, base: str, filename: str, content: str) -> str:
    """Create ``branch`` off ``base`` with one commit writing ``filename``; return its SHA."""
    _git(repo, "branch", branch, base)
    _git(repo, "checkout", branch)
    (repo / filename).write_text(content)
    _git(repo, "add", filename)
    _git(repo, "commit", "-m", f"{branch}: write {filename}")
    sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _git(repo, "checkout", "main")
    return sha


def _lane(lane_id: str, *, depends: tuple[str, ...] = (), group: int = 0) -> ExecutionLane:
    return ExecutionLane(
        lane_id=lane_id,
        wp_ids=(f"WP-{lane_id}",),
        write_scope=("src/**",),
        predicted_surfaces=(),
        depends_on_lanes=depends,
        parallel_group=group,
    )


def _manifest(lanes: list[ExecutionLane]) -> LanesManifest:
    return LanesManifest(
        version=1,
        mission_slug=MISSION_SLUG,
        mission_id=MISSION_SLUG,
        mission_branch=f"kitty/mission-{MISSION_SLUG}",
        target_branch=TARGET_BRANCH,
        lanes=lanes,
        computed_at="2026-06-15T12:00:00+00:00",
        computed_from="test",
    )


# ---------------------------------------------------------------------------
# T012 — allocator routes through the WP01 worktree_path seam (byte-identical).
# ---------------------------------------------------------------------------


def test_allocator_routes_through_worktree_path_seam(tmp_path: Path) -> None:
    """The allocated path equals ``worktree_path(...)`` and the golden legacy row.

    The old call site composed ``repo_root/".worktrees"/f"{slug}-{lane}"`` (no
    mid8). Routing through ``worktree_path(repo_root, slug, mission_id=None,
    lane_id=...)`` must reproduce that EXACT name — proven against the shared
    golden-value table's legacy row, not a self-authored expectation.
    """
    legacy_row = next(r for r in GOLDEN_ROWS if r.mission_id is None)

    repo = tmp_path / "repo"
    repo.mkdir()
    _make_git_repo(repo)

    manifest = _manifest([_lane("lane-a")])
    wt_path, _branch = allocate_lane_worktree(
        repo, MISSION_SLUG, "WP-lane-a", manifest
    )

    # Routed name is byte-identical to the WP01 seam with mission_id=None …
    assert wt_path == worktree_path(
        repo, MISSION_SLUG, mission_id=None, lane_id="lane-a"
    )
    # … and to the legacy f-string the old call site composed (no mid8) …
    assert wt_path == repo / ".worktrees" / f"{MISSION_SLUG}-lane-a"
    # … which the shared golden table fixes for an embedded slug (no churn).
    assert (
        worktree_path(
            repo,
            legacy_row.mission_slug,
            mission_id=None,
            lane_id=legacy_row.lane_id,
        ).name
        == legacy_row.worktree_dir
    )


# ---------------------------------------------------------------------------
# T013/T014 — #1915 atomic multi-dependency merge.
# ---------------------------------------------------------------------------


def _setup_two_dep_conflict(repo: Path) -> tuple[Path, LanesManifest, ExecutionLane, str]:
    """Build a dependent lane with a clean-then-conflicting pair of dep lanes.

    Layout:
      * ``lane-a`` (dep, group 0): adds a *new* file → merges cleanly.
      * ``lane-b`` (dep, group 1): writes ``SHARED_FILE`` with one content.
      * ``lane-c`` (dependent): its worktree already wrote ``SHARED_FILE`` with
        *different* content, so merging ``lane-b`` conflicts.

    Returns ``(lane_c_worktree, manifest, lane_c, pre_loop_head)``.
    """
    dep_a = _lane("lane-a", group=0)
    dep_b = _lane("lane-b", group=1)
    lane_c = _lane("lane-c", depends=("lane-a", "lane-b"), group=2)
    manifest = _manifest([dep_a, dep_b, lane_c])

    # Dependency lane-a: a clean, non-overlapping addition.
    _commit_on_branch(
        repo,
        lane_branch_name(MISSION_SLUG, "lane-a"),
        "main",
        "from_lane_a.txt",
        "lane-a content\n",
    )
    # Dependency lane-b: writes the shared file (will conflict with lane-c).
    _commit_on_branch(
        repo,
        lane_branch_name(MISSION_SLUG, "lane-b"),
        "main",
        SHARED_FILE,
        "lane-b version\n",
    )

    # Dependent lane-c worktree: branch off main, write the shared file with a
    # DIFFERENT content so the later lane-b merge conflicts.
    lane_c_branch = lane_branch_name(MISSION_SLUG, "lane-c")
    lane_c_wt = repo / ".worktrees" / f"{MISSION_SLUG}-lane-c"
    lane_c_wt.parent.mkdir(parents=True, exist_ok=True)
    _git(repo, "worktree", "add", "-b", lane_c_branch, str(lane_c_wt), "main")
    (lane_c_wt / SHARED_FILE).write_text("lane-c version\n")
    _git(lane_c_wt, "add", SHARED_FILE)
    _git(lane_c_wt, "commit", "-m", "lane-c: write shared file")

    pre_loop_head = _git(lane_c_wt, "rev-parse", "HEAD").stdout.strip()
    return lane_c_wt, manifest, lane_c, pre_loop_head


def test_1915_later_dep_conflict_rolls_back_earlier_dep_merge(tmp_path: Path) -> None:
    """RED-FIRST #1915: a later-dep conflict must NOT leave the earlier dep merged.

    Before the fix, ``git merge --abort`` only undid the conflicting lane-b
    merge while the clean lane-a merge commit survived — the dependent lane's
    HEAD advanced past its pre-loop ref and ``from_lane_a.txt`` lingered. The
    atomic fix resets the lane hard to the recorded pre-loop ref on ANY
    conflict, so HEAD is unchanged and no partial dep merge survives.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _make_git_repo(repo)

    lane_c_wt, manifest, lane_c, pre_loop_head = _setup_two_dep_conflict(repo)

    with pytest.raises(DependencyLaneMergeConflictError) as exc:
        _merge_dependency_lane_tips(repo, lane_c_wt, MISSION_SLUG, lane_c, manifest)

    # The conflict is reported for the genuinely-conflicting later dep (lane-b).
    assert exc.value.dep_lane_id == "lane-b"

    # Atomicity: HEAD is exactly the pre-loop ref — the earlier clean lane-a
    # merge was rolled back, not orphaned on the lane.
    head_after = _git(lane_c_wt, "rev-parse", "HEAD").stdout.strip()
    assert head_after == pre_loop_head, (
        "lane worktree HEAD advanced past its pre-loop ref — the earlier clean "
        "dependency merge survived a later-dep conflict (#1915)."
    )
    # The earlier dep's file must NOT linger in the working tree.
    assert not (lane_c_wt / "from_lane_a.txt").exists()
    # The worktree is clean (no half-merge residue, conflict markers gone).
    assert _git(lane_c_wt, "status", "--porcelain").stdout.strip() == ""


def test_1915_all_clean_deps_still_merge(tmp_path: Path) -> None:
    """Success path preserved: when every dep merges cleanly, all tips land."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _make_git_repo(repo)

    dep_a = _lane("lane-a", group=0)
    dep_b = _lane("lane-b", group=1)
    lane_c = _lane("lane-c", depends=("lane-a", "lane-b"), group=2)
    manifest = _manifest([dep_a, dep_b, lane_c])

    _commit_on_branch(
        repo, lane_branch_name(MISSION_SLUG, "lane-a"), "main", "a.txt", "a\n"
    )
    _commit_on_branch(
        repo, lane_branch_name(MISSION_SLUG, "lane-b"), "main", "b.txt", "b\n"
    )

    lane_c_branch = lane_branch_name(MISSION_SLUG, "lane-c")
    lane_c_wt = repo / ".worktrees" / f"{MISSION_SLUG}-lane-c"
    lane_c_wt.parent.mkdir(parents=True, exist_ok=True)
    _git(repo, "worktree", "add", "-b", lane_c_branch, str(lane_c_wt), "main")

    _merge_dependency_lane_tips(repo, lane_c_wt, MISSION_SLUG, lane_c, manifest)

    # Both dependency tips propagated into the dependent lane worktree.
    assert (lane_c_wt / "a.txt").exists()
    assert (lane_c_wt / "b.txt").exists()
    assert _git(lane_c_wt, "status", "--porcelain").stdout.strip() == ""
