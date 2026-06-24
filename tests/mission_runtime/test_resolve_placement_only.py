"""Unit tests for the WP-less placement projection (WP05, T018).

Mission ``tooling-stability-guard-coherence-01KTRC04`` (FR-003, C-GUARD-3a).

``resolve_placement_only(repo_root, mission_slug)`` is the planning-phase
placement projection: the planning lifecycle (specify / plan / tasks /
finalize-tasks) has no ``wp_id``, so the full :func:`resolve_action_context`
cannot be driven for an :class:`ArtifactPlacementFragment`. These tests pin the
single-authority invariant the catch-22 fix depends on: the projection's
``CommitTarget`` is **byte-identical** to the one the full resolver assembles
for the same mission across all three topologies — flattened (non-protected
target), coordination (declared coordination branch), and protected-main
(target == protected branch).

If the projection ever re-derived a destination independently of the resolver,
this parity would drift — which is exactly the #1784 split-brain it kills.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from mission_runtime import (
    ActionContextError,
    CommitTarget,
    MissionArtifactKind,
    resolve_action_context,
    resolve_placement_only,
    resolve_topology,
    routes_through_coordination,
)

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

# These parity tests assert the TOPOLOGY-routed destination is byte-identical to
# the full resolver's ``destination_ref``. ``STATUS_STATE`` is a coordination
# (topology-routed) kind, so it keeps that destination across all topologies —
# the parity invariant these tests pin (WP01 made ``kind`` required; the
# kind-aware primary partition is covered in ``test_artifact_partition.py``).
_TOPOLOGY_ROUTED_KIND = MissionArtifactKind.STATUS_STATE

_MISSION_SLUG = "wp05-placement-mission"
_MISSION_ID = "01WP05PLACEMENTPARITY00001"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _build_mission(
    repo_root: Path,
    *,
    target_branch: str,
    coordination_branch: str | None = None,
) -> None:
    feature_dir = repo_root / "kitty-specs" / _MISSION_SLUG
    feature_dir.mkdir(parents=True)
    meta: dict[str, object] = {
        "mission_id": _MISSION_ID,
        "mission_slug": _MISSION_SLUG,
        "mission_type": "software-dev",
        "target_branch": target_branch,
        "friendly_name": "WP05 placement mission",
    }
    if coordination_branch is not None:
        meta["coordination_branch"] = coordination_branch
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (feature_dir / "tasks").mkdir()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@example.com")
    _git(r, "config", "user.name", "Test")
    _git(r, "config", "commit.gpgsign", "false")
    (r / ".kittify").mkdir()
    (r / ".kittify" / "config.yaml").write_text(
        "agents:\n  available:\n    - claude\n", encoding="utf-8"
    )
    return r


def _commit_fixture(repo: Path) -> None:
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "fixture")


def _full_resolver_placement(repo: Path) -> CommitTarget:
    ctx = resolve_action_context(repo, action="tasks", feature=_MISSION_SLUG)
    assert ctx.artifact_placement is not None
    return ctx.artifact_placement.placement_ref


# ---------------------------------------------------------------------------
# Topology parity — the projection equals the full resolver's destination_ref
# ---------------------------------------------------------------------------


def test_flattened_topology_parity(repo: Path) -> None:
    """No coordination branch + non-protected target → FLATTENED, parity holds."""
    _build_mission(repo, target_branch="feat/some-non-protected-branch")
    _commit_fixture(repo)

    placement = resolve_placement_only(repo, _MISSION_SLUG, kind=_TOPOLOGY_ROUTED_KIND)

    assert placement == _full_resolver_placement(repo)
    # FR-001b: routing is decided from the STORED topology, not a per-ref enum —
    # a flattened mission does NOT route through coordination.
    assert routes_through_coordination(resolve_topology(repo, _MISSION_SLUG)) is False
    assert placement.ref == "feat/some-non-protected-branch"


def test_coordination_topology_parity(repo: Path) -> None:
    """A declared coordination branch → COORDINATION, parity holds."""
    coord = "kitty/mission-wp05-placement-mission-01WP05PLA"
    _build_mission(
        repo,
        target_branch="feat/some-non-protected-branch",
        coordination_branch=coord,
    )
    _commit_fixture(repo)
    # WP03 R3 authority: a declared coordination branch must actually EXIST in
    # git for the COORDINATION (R2) path to resolve; a declared-but-absent
    # branch now correctly raises CoordinationBranchDeleted (R3). Materialize
    # the real coordination ref so the registry-based topology authority
    # ("name proposes, authority disposes") resolves COORDINATION.
    _git(repo, "branch", coord)

    placement = resolve_placement_only(repo, _MISSION_SLUG, kind=_TOPOLOGY_ROUTED_KIND)

    assert placement == _full_resolver_placement(repo)
    # A declared+materialized coordination branch routes through coordination
    # (FR-001b: decision reads the stored topology, never a per-ref enum).
    assert routes_through_coordination(resolve_topology(repo, _MISSION_SLUG)) is True
    assert placement.ref == coord


def test_protected_main_with_coordination_branch_parity(repo: Path) -> None:
    """Protected-main mission carrying a coordination branch (the #1784 shape).

    On a protected-target repo ``mission create`` materializes a coordination
    branch; the resolved placement is that NON-protected coordination ref, NOT
    the protected ``main`` target. This is the literal catch-22 killer.
    """
    coord = "kitty/mission-wp05-placement-mission-01WP05PLA"
    _build_mission(repo, target_branch="main", coordination_branch=coord)
    _commit_fixture(repo)
    # WP03 R3 authority: materialize the real coordination branch so the
    # protected-main + coordination shape resolves COORDINATION (R2) rather
    # than raising CoordinationBranchDeleted (R3) on an absent ref.
    _git(repo, "branch", coord)

    placement = resolve_placement_only(repo, _MISSION_SLUG, kind=_TOPOLOGY_ROUTED_KIND)

    assert placement == _full_resolver_placement(repo)
    assert routes_through_coordination(resolve_topology(repo, _MISSION_SLUG)) is True
    assert placement.ref == coord
    # The protected target is NEVER the resolved placement here.
    assert placement.ref != "main"


def test_protected_main_flattened_returns_protected_ref(repo: Path) -> None:
    """A protected-main mission with NO coordination branch resolves to ``main``.

    The projection does not invent a safe branch: under genuine flattened
    topology it surfaces the protected ref (kind FLATTENED). The guard — not the
    resolver — decides legitimacy. Parity with the full resolver still holds.
    """
    _build_mission(repo, target_branch="main")
    _commit_fixture(repo)

    placement = resolve_placement_only(repo, _MISSION_SLUG, kind=_TOPOLOGY_ROUTED_KIND)

    assert placement == _full_resolver_placement(repo)
    assert routes_through_coordination(resolve_topology(repo, _MISSION_SLUG)) is False
    assert placement.ref == "main"


# ---------------------------------------------------------------------------
# No silent fallback (mirrors resolve_action_context)
# ---------------------------------------------------------------------------


def test_empty_mission_slug_raises(repo: Path) -> None:
    with pytest.raises(ActionContextError):
        resolve_placement_only(repo, "", kind=_TOPOLOGY_ROUTED_KIND)


def test_whitespace_mission_slug_raises(repo: Path) -> None:
    with pytest.raises(ActionContextError):
        resolve_placement_only(repo, "   ", kind=_TOPOLOGY_ROUTED_KIND)
