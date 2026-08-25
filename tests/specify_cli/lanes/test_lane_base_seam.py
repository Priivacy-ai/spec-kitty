"""M8 WP02 — the shared lane-allocation seam ``resolve_lane_base_or_refuse``.

M1 (#3571) landed two flat helpers on ``worktree_allocator`` —
``_guard_base_honorable`` (the refusal path) and ``_resolve_lane_parent`` (the
positive parent chooser) — and called them directly, in pairs, at the four
allocation routes. M8 folds them into ONE seam so no route can compute a parent
ref inline (FR-001/002/003, NFR-001).

Red-first anchor (INV-0): the seam is the SOLE parent-computer — the two
helpers are no longer called from ``allocate_lane_worktree`` directly, and no
inline topology parent-choice survives. That assertion is genuinely red on
pre-refactor ``main`` (both helpers are called there); it drives this WP.

The seam symbols (``resolve_lane_base_or_refuse``, ``LaneAllocationRoute``,
``LaneBaseDecision``, ``LaneTopology``) do NOT exist pre-refactor, so they are
imported LOCALLY inside each test that needs them — this keeps the module
collectible against unfixed ``main`` and lets INV-0 fail on its structural
assertion (symptom-red) rather than a collection-time ImportError (false-red).
``allocate_lane_worktree`` and ``UnhonorableBaseError`` predate this WP (M1) and
are imported at module scope.
"""

from __future__ import annotations

import inspect
import json
import subprocess
from pathlib import Path

import pytest
from kernel.clock import now_utc_iso

from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.worktree_allocator import (
    UnhonorableBaseError,
    allocate_lane_worktree,
)

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

MISSION_SLUG = "lane-base-seam-demo"
MISSION_ID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
COORD_BRANCH = f"kitty/mission-{MISSION_SLUG}-coord"
MISSION_BRANCH = f"kitty/mission-{MISSION_SLUG}"
LEGACY_MISSION_SLUG = "lane-base-seam-legacy"
LEGACY_MISSION_BRANCH = f"kitty/mission-{LEGACY_MISSION_SLUG}"
WP_ID = "WP06"
EXPLICIT_BASE_BRANCH = "explicit-base"
LANE_A = "lane-a"


# ---------------------------------------------------------------------------
# Shared git helpers
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _git_out(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def _is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo, capture_output=True,
    )
    return result.returncode == 0


def _branch_missing(repo: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", branch], cwd=repo, capture_output=True,
    )
    return result.returncode != 0


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")


def _make_manifest(
    *,
    mission_slug: str = MISSION_SLUG,
    mission_branch: str,
    depends_on_lanes: tuple[str, ...] = (),
    planning_commit_sha: str | None = None,
) -> LanesManifest:
    return LanesManifest(
        version=1,
        mission_slug=mission_slug,
        mission_id=MISSION_ID,
        mission_branch=mission_branch,
        target_branch="main",
        lanes=[ExecutionLane(
            lane_id=LANE_A,
            wp_ids=(WP_ID,),
            write_scope=(),
            predicted_surfaces=(),
            depends_on_lanes=depends_on_lanes,
            parallel_group=0,
        )],
        computed_at=now_utc_iso(),
        computed_from="test",
        planning_commit_sha=planning_commit_sha,
    )


def _write_meta(
    feature_dir: Path, *, mission_slug: str, coordination_branch: str | None,
) -> None:
    meta: dict[str, object] = {
        "mission_id": MISSION_ID,
        "mission_slug": mission_slug,
        "target_branch": "main",
    }
    if coordination_branch is not None:
        meta["coordination_branch"] = coordination_branch
    (feature_dir / "meta.json").write_text(json.dumps(meta))


def _lane(depends_on_lanes: tuple[str, ...] = ()) -> ExecutionLane:
    return ExecutionLane(
        lane_id=LANE_A, wp_ids=(WP_ID,), write_scope=(),
        predicted_surfaces=(), depends_on_lanes=depends_on_lanes, parallel_group=0,
    )


# ---------------------------------------------------------------------------
# INV-0 — the seam is the SOLE parent-computer (RED on pre-refactor main)
# ---------------------------------------------------------------------------


def test_inv0_seam_is_sole_parent_computer() -> None:
    """After WP02, ``allocate_lane_worktree`` computes no parent inline: it
    calls the seam and never ``_guard_base_honorable`` / ``_resolve_lane_parent``
    directly, and no ``coordination_branch if … else mission_branch`` survives.

    This is the genuinely-red-on-main cell — pre-refactor both helpers are
    called directly and there is no seam.
    """
    src = inspect.getsource(allocate_lane_worktree)

    assert "resolve_lane_base_or_refuse(" in src, (
        "allocate_lane_worktree must route through the seam"
    )
    assert "_guard_base_honorable(" not in src, (
        "the refusal guard must be called ONLY from inside the seam"
    )
    assert "_resolve_lane_parent(" not in src, (
        "the parent chooser must be called ONLY from inside the seam"
    )
    # No inline topology parent-choice composition survives outside the seam.
    assert "coordination_branch if" not in src
    assert "else mission_branch" not in src
    assert "else lanes_manifest.mission_branch" not in src


# ---------------------------------------------------------------------------
# INV-1 — base=None on each of the four routes → topology parent, no refusal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "route_name,coord,mission_branch,expected_parent,expected_topology_name",
    [
        ("FRESH_COORD", COORD_BRANCH, MISSION_BRANCH, COORD_BRANCH, "COORD"),
        ("FRESH_LEGACY", None, MISSION_BRANCH, MISSION_BRANCH, "LEGACY"),
        ("REUSE", None, MISSION_BRANCH, MISSION_BRANCH, "LEGACY"),
        ("CRASH_RECOVERY", COORD_BRANCH, MISSION_BRANCH, COORD_BRANCH, "COORD"),
    ],
)
def test_inv1_base_none_returns_topology_parent(
    route_name: str,
    coord: str | None,
    mission_branch: str,
    expected_parent: str,
    expected_topology_name: str,
) -> None:
    """``base=None`` on every route returns the pre-M8 topology-derived parent
    (``coordination_branch`` if set, else ``mission_branch``), ``base_honored``
    False, and no refusal (NFR-001)."""
    from specify_cli.lanes.worktree_allocator import (
        LaneAllocationRoute,
        LaneBaseDecision,
        LaneTopology,
        resolve_lane_base_or_refuse,
    )

    route = LaneAllocationRoute[route_name]
    decision = resolve_lane_base_or_refuse(
        base=None,
        route=route,
        coordination_branch=coord,
        mission_branch=mission_branch,
        wp_id=WP_ID,
        lane=_lane(),
    )
    assert isinstance(decision, LaneBaseDecision)
    assert decision.parent_ref == expected_parent
    assert decision.base_honored is False
    assert decision.route is route
    assert decision.topology is LaneTopology[expected_topology_name]


def test_inv1_fresh_coord_base_none_descends_coordination_branch(
    coord_repo: Path,
) -> None:
    """Integration parity: a fresh coord lane with ``base=None`` descends from
    the ``coordination_branch``, byte-identical to pre-M8."""
    manifest = _make_manifest(mission_branch=MISSION_BRANCH)
    worktree_path, branch = allocate_lane_worktree(
        repo_root=coord_repo, mission_slug=MISSION_SLUG, wp_id=WP_ID,
        lanes_manifest=manifest,
    )
    assert worktree_path.exists()
    assert _is_ancestor(coord_repo, COORD_BRANCH, branch)


def test_inv1_fresh_legacy_base_none_descends_mission_branch(
    legacy_repo: Path,
) -> None:
    """Integration parity: a fresh legacy lane with ``base=None`` descends from
    the ``mission_branch`` field, byte-identical to pre-M8."""
    manifest = _make_manifest(
        mission_slug=LEGACY_MISSION_SLUG, mission_branch=LEGACY_MISSION_BRANCH,
    )
    worktree_path, branch = allocate_lane_worktree(
        repo_root=legacy_repo, mission_slug=LEGACY_MISSION_SLUG, wp_id=WP_ID,
        lanes_manifest=manifest,
    )
    assert worktree_path.exists()
    assert _is_ancestor(legacy_repo, LEGACY_MISSION_BRANCH, branch)


# ---------------------------------------------------------------------------
# Honored-base parity (standing #3571 / INV-3 companion at the seam)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "route_name,coord", [("FRESH_COORD", COORD_BRANCH), ("FRESH_LEGACY", None)],
)
def test_honored_base_replaces_topology_parent(
    route_name: str, coord: str | None,
) -> None:
    """A base on an honorable fresh route fully REPLACES the topology parent."""
    from specify_cli.lanes.worktree_allocator import (
        LaneAllocationRoute,
        resolve_lane_base_or_refuse,
    )

    decision = resolve_lane_base_or_refuse(
        base=EXPLICIT_BASE_BRANCH,
        route=LaneAllocationRoute[route_name],
        coordination_branch=coord,
        mission_branch=MISSION_BRANCH,
        wp_id=WP_ID,
        lane=_lane(),
    )
    assert decision.parent_ref == EXPLICIT_BASE_BRANCH
    assert decision.base_honored is True


# ---------------------------------------------------------------------------
# INV-2 — base on reuse / crash_recovery → UnhonorableBaseError naming route
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "route_name,trigger",
    [("REUSE", "reuse"), ("CRASH_RECOVERY", "crash_recovery")],
)
def test_inv2_base_on_already_created_route_refuses(
    route_name: str, trigger: str,
) -> None:
    """An already-created lane (reuse / crash-recovery) cannot be re-parented —
    a supplied base raises ``UnhonorableBaseError`` naming the route (FR-003),
    never returning a degraded parent."""
    from specify_cli.lanes.worktree_allocator import (
        LaneAllocationRoute,
        resolve_lane_base_or_refuse,
    )

    with pytest.raises(UnhonorableBaseError) as exc_info:
        resolve_lane_base_or_refuse(
            base=EXPLICIT_BASE_BRANCH,
            route=LaneAllocationRoute[route_name],
            coordination_branch=COORD_BRANCH,
            mission_branch=MISSION_BRANCH,
            wp_id=WP_ID,
        )
    assert exc_info.value.route == trigger
    assert exc_info.value.wp_id == WP_ID
    assert exc_info.value.base == EXPLICIT_BASE_BRANCH


def test_inv2_dependency_lane_base_refuses() -> None:
    """A dependency-bearing fresh lane refuses a base (D2/FR-009), naming the
    ``dependency_lane`` trigger — no ``git`` needed (the guard inspects
    ``lane.depends_on_lanes``)."""
    from specify_cli.lanes.worktree_allocator import (
        LaneAllocationRoute,
        resolve_lane_base_or_refuse,
    )

    with pytest.raises(UnhonorableBaseError) as exc_info:
        resolve_lane_base_or_refuse(
            base=EXPLICIT_BASE_BRANCH,
            route=LaneAllocationRoute.FRESH_COORD,
            coordination_branch=COORD_BRANCH,
            mission_branch=MISSION_BRANCH,
            wp_id=WP_ID,
            lane=_lane(depends_on_lanes=("lane-b",)),
        )
    assert exc_info.value.route == "dependency_lane"


# ---------------------------------------------------------------------------
# INV-7 — atomicity: a refusal on any route leaves no half-created lane
# ---------------------------------------------------------------------------


def test_inv7_dependency_lane_refusal_leaves_no_residual(coord_repo: Path) -> None:
    """A dependency-lane refusal through ``allocate_lane_worktree`` leaves no
    lane worktree or branch (the seam runs before creation)."""
    manifest = _make_manifest(
        mission_branch=MISSION_BRANCH, depends_on_lanes=("lane-b",),
    )
    with pytest.raises(UnhonorableBaseError) as exc_info:
        allocate_lane_worktree(
            repo_root=coord_repo, mission_slug=MISSION_SLUG, wp_id=WP_ID,
            lanes_manifest=manifest, base=EXPLICIT_BASE_BRANCH,
        )
    assert exc_info.value.route == "dependency_lane"

    worktree_path = coord_repo / ".worktrees" / f"{MISSION_SLUG}-{LANE_A}"
    lane_branch = f"kitty/mission-{MISSION_SLUG}-{LANE_A}"
    assert not worktree_path.exists(), "no residual worktree after a refusal"
    assert _branch_missing(coord_repo, lane_branch), "no residual branch after a refusal"


def test_inv7_detached_base_refusal_leaves_no_residual(coord_repo: Path) -> None:
    """A detached base (no common ancestor with the recorded planning commit)
    refuses BEFORE creation — no lane worktree/branch residual (FR-010)."""
    repo = coord_repo
    # An orphan-root base shares NO history with the seed lineage.
    _git(repo, "checkout", "-q", "--orphan", "detached-root")
    (repo / "detached.txt").write_text("detached root\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "detached root commit")
    detached_sha = _git_out(repo, "rev-parse", "HEAD")
    _git(repo, "branch", "-f", EXPLICIT_BASE_BRANCH, detached_sha)
    _git(repo, "checkout", "-q", "main")

    # Planning commit lives on the seed lineage — unrelated to the detached base.
    seed_sha = _git_out(repo, "rev-parse", "main")
    _git(repo, "checkout", "-q", "-b", "planning-tmp", seed_sha)
    (repo / "planning.txt").write_text("planning artifact\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "planning commit")
    planning_sha = _git_out(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "main")
    _git(repo, "branch", "-D", "planning-tmp")

    manifest = _make_manifest(
        mission_branch=MISSION_BRANCH, planning_commit_sha=planning_sha,
    )
    with pytest.raises(UnhonorableBaseError) as exc_info:
        allocate_lane_worktree(
            repo_root=repo, mission_slug=MISSION_SLUG, wp_id=WP_ID,
            lanes_manifest=manifest, base=EXPLICIT_BASE_BRANCH,
        )
    assert exc_info.value.route == "detached_base"

    worktree_path = repo / ".worktrees" / f"{MISSION_SLUG}-{LANE_A}"
    lane_branch = f"kitty/mission-{MISSION_SLUG}-{LANE_A}"
    assert not worktree_path.exists(), "no residual worktree after a pre-create refusal"
    assert _branch_missing(repo, lane_branch), "no residual branch after a pre-create refusal"


def test_inv7_reuse_refusal_does_not_disturb_existing_lane(coord_repo: Path) -> None:
    """A reuse refusal is raised BEFORE any reuse side effect; the pre-existing
    lane worktree and branch survive untouched (atomicity for the reuse route)."""
    manifest = _make_manifest(mission_branch=MISSION_BRANCH)
    # First allocation (no base) creates the lane worktree + branch.
    worktree_path, lane_branch = allocate_lane_worktree(
        repo_root=coord_repo, mission_slug=MISSION_SLUG, wp_id=WP_ID,
        lanes_manifest=manifest,
    )
    head_before = _git_out(worktree_path, "rev-parse", "HEAD")

    with pytest.raises(UnhonorableBaseError) as exc_info:
        allocate_lane_worktree(
            repo_root=coord_repo, mission_slug=MISSION_SLUG, wp_id=WP_ID,
            lanes_manifest=manifest, base=EXPLICIT_BASE_BRANCH,
        )
    assert exc_info.value.route == "reuse"
    # The existing lane is untouched — same worktree, same HEAD.
    assert worktree_path.exists()
    assert _git_out(worktree_path, "rev-parse", "HEAD") == head_before
    assert not _branch_missing(coord_repo, lane_branch)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def coord_repo(tmp_path: Path) -> Path:
    """Coord-topology repo: a distinct ``coordination_branch`` and an
    ``explicit-base`` branch, both descending from the seed."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    feature_dir = repo / "kitty-specs" / MISSION_SLUG
    feature_dir.mkdir(parents=True)
    _write_meta(feature_dir, mission_slug=MISSION_SLUG, coordination_branch=COORD_BRANCH)
    (repo / "README.md").write_text("seed\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "seed")
    seed_sha = _git_out(repo, "rev-parse", "HEAD")

    # coordination_branch descends from the seed (distinct from mission_branch).
    _git(repo, "branch", COORD_BRANCH, seed_sha)

    # explicit-base shares the seed as a common ancestor with the planning line.
    _git(repo, "branch", EXPLICIT_BASE_BRANCH, seed_sha)
    _git(repo, "checkout", "-q", EXPLICIT_BASE_BRANCH)
    (repo / "base.txt").write_text("explicit base work\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "explicit base work")
    _git(repo, "checkout", "-q", "main")
    return repo


@pytest.fixture
def legacy_repo(tmp_path: Path) -> Path:
    """No ``coordination_branch`` — legacy topology."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    feature_dir = repo / "kitty-specs" / LEGACY_MISSION_SLUG
    feature_dir.mkdir(parents=True)
    _write_meta(feature_dir, mission_slug=LEGACY_MISSION_SLUG, coordination_branch=None)
    (feature_dir / "spec.md").write_text("# spec\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "seed")
    return repo
