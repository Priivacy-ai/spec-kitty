"""Coordination-branch-aware behaviour of :mod:`worktree_allocator`.

Covers the WP04 contract (#1348):

* New-topology missions (``meta.json`` has ``coordination_branch``):
  lane branches are parented on the coordination branch, and lane
  worktrees receive the status-files sparse-checkout exclusion.
* Legacy missions (no ``coordination_branch``): allocator falls back to
  the manifest's ``mission_branch`` and skips sparse-checkout, matching
  the pre-WP04 behaviour.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.worktree_allocator import allocate_lane_worktree

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


HUMAN_SLUG = "demo-feature"
# Post-WP03 mission_slug carries the mid8 suffix verbatim. Mirrors
# mission_creation.py's mission_slug_formatted construction.
MISSION_SLUG = "demo-feature-01J6XW9K"
MISSION_ID = "01J6XW9KABCDEFGHJKMNPQRSTV"  # full ULID, mid8 = "01J6XW9K"
MID8 = "01J6XW9K"
# Mission directory equals mission_slug (which itself already carries
# the mid8 suffix in the post-WP03 format).
COORD_BRANCH = f"kitty/mission-{MISSION_SLUG}"
LEGACY_MISSION_SLUG = HUMAN_SLUG
LEGACY_MISSION_BRANCH = f"kitty/mission-{LEGACY_MISSION_SLUG}"
MISSION_DIR_NEW = MISSION_SLUG


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _make_manifest(
    *,
    mission_branch: str,
    mission_id: str,
    lane_id: str = "lane-a",
    wp_ids: tuple[str, ...] = ("WP01",),
) -> LanesManifest:
    return LanesManifest(
        version=1,
        mission_slug=MISSION_SLUG,
        mission_id=mission_id,
        mission_branch=mission_branch,
        target_branch="main",
        lanes=[ExecutionLane(
            lane_id=lane_id,
            wp_ids=wp_ids,
            write_scope=(),
            predicted_surfaces=(),
            depends_on_lanes=(),
            parallel_group=0,
        )],
        computed_at=datetime.now(timezone.utc).isoformat(),
        computed_from="test",
    )


@pytest.fixture
def new_topology_repo(tmp_path: Path) -> Path:
    """Tmp repo with coordination branch + meta.json carrying it.

    Mimics post-WP03 mission state on disk.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")

    spec_dir = repo / "kitty-specs" / MISSION_DIR_NEW
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text("# spec\n")
    (spec_dir / "status.events.jsonl").write_text(
        '{"actor":"test","wp_id":"WP01"}\n'
    )
    (spec_dir / "status.json").write_text("{}\n")
    (spec_dir / "meta.json").write_text(json.dumps({
        "mission_id": MISSION_ID,
        "mission_slug": MISSION_SLUG,
        "coordination_branch": COORD_BRANCH,
    }))
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "seed")
    _git(repo, "branch", COORD_BRANCH)
    return repo


@pytest.fixture
def legacy_repo(tmp_path: Path) -> Path:
    """Tmp repo with no ``coordination_branch`` field — legacy topology."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")

    # Legacy spec dir uses the bare slug (no mid8).
    spec_dir = repo / "kitty-specs" / LEGACY_MISSION_SLUG
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text("# spec\n")
    # NB: no coordination_branch field, mirroring pre-WP03 missions.
    (spec_dir / "meta.json").write_text(json.dumps({
        "mission_slug": LEGACY_MISSION_SLUG,
    }))
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "seed")
    return repo


def test_new_topology_parents_on_coordination_branch(
    new_topology_repo: Path,
) -> None:
    manifest = _make_manifest(
        mission_branch=COORD_BRANCH, mission_id=MISSION_ID,
    )
    worktree_path, branch = allocate_lane_worktree(
        repo_root=new_topology_repo,
        mission_slug=MISSION_SLUG,
        wp_id="WP01",
        lanes_manifest=manifest,
    )
    assert worktree_path.exists()
    assert branch == f"kitty/mission-{MISSION_SLUG}-lane-a"

    # The lane branch must be reachable from the coordination branch.
    result = subprocess.run(
        ["git", "-C", str(new_topology_repo), "merge-base",
         "--is-ancestor", COORD_BRANCH, branch],
        capture_output=True,
    )
    assert result.returncode == 0, (
        f"lane branch {branch} should descend from {COORD_BRANCH}"
    )


def test_new_topology_applies_sparse_checkout(
    new_topology_repo: Path,
) -> None:
    manifest = _make_manifest(
        mission_branch=COORD_BRANCH, mission_id=MISSION_ID,
    )
    worktree_path, _ = allocate_lane_worktree(
        repo_root=new_topology_repo,
        mission_slug=MISSION_SLUG,
        wp_id="WP01",
        lanes_manifest=manifest,
    )

    lane_spec_dir = worktree_path / "kitty-specs" / MISSION_DIR_NEW
    assert (lane_spec_dir / "spec.md").exists()
    assert not (lane_spec_dir / "status.events.jsonl").exists()
    assert not (lane_spec_dir / "status.json").exists()


def test_legacy_topology_skips_sparse_checkout(
    legacy_repo: Path,
) -> None:
    """No ``coordination_branch`` => parent on mission_branch, no sparse-checkout."""
    manifest = _make_manifest(
        mission_branch=LEGACY_MISSION_BRANCH,
        mission_id="legacy",  # too short for mid8(); irrelevant on legacy path
    )
    worktree_path, branch = allocate_lane_worktree(
        repo_root=legacy_repo,
        mission_slug=LEGACY_MISSION_SLUG,
        wp_id="WP01",
        lanes_manifest=manifest,
    )
    assert worktree_path.exists()
    assert branch == f"kitty/mission-{LEGACY_MISSION_SLUG}-lane-a"

    # No sparse-checkout was applied — legacy mission_dir was bare, no
    # status files to exclude, and `core.sparseCheckout` should remain unset.
    result = subprocess.run(
        ["git", "-C", str(worktree_path), "config",
         "--get", "core.sparseCheckout"],
        capture_output=True, text=True,
    )
    # config --get returns 1 when unset.
    assert result.returncode != 0 or result.stdout.strip() != "true"
