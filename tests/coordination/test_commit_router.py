"""Tests for commit_router.commit_for_mission (WP02 / T009).

Covers:
- Protected placement → materialises coordination worktree + lands on coord branch.
- Unprotected placement → direct commit (no materialiser called).
- Idempotent (unchanged artifact → ``unchanged`` status).
- #1718 preserved: materialisation happens at the commit boundary, not at read time.
- NEGATIVE variant: stubbing the materialiser causes a test failure (proves the
  materialiser is actually called on the protected path).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.git.protection_policy import ProtectionPolicy

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_policy(*, protected: bool) -> ProtectionPolicy:
    """Return a ProtectionPolicy that either protects or does not protect 'main'."""
    branches: frozenset[str] = frozenset({"main"}) if protected else frozenset()
    return ProtectionPolicy(protected_branches=branches, operator_hatch_active=False)


def _make_coord_target() -> object:
    """Return a ref-only CommitTarget for a coordination placement."""
    from mission_runtime import CommitTarget

    return CommitTarget(ref="kitty/mission-my-slug-ABCD1234")


def _make_primary_target() -> object:
    """Return a ref-only CommitTarget for a primary placement."""
    from mission_runtime import CommitTarget

    return CommitTarget(ref="main")


def _patch_topology(coord: bool) -> object:
    """Patch the router's stored-topology read (FR-001b: routing reads topology).

    ``commit_for_mission`` decides coord-vs-primary from the WP02 STORED topology
    via ``routes_through_coordination(resolve_topology(...))`` — no longer from a
    per-ref ``CommitTarget.kind``. The fixtures stub ``resolve_placement_only`` for
    the ref; this stubs ``resolve_topology`` for the routing decision so the two
    legs stay consistent (COORD ⇒ coord routing; SINGLE_BRANCH ⇒ primary).
    """
    from mission_runtime import MissionTopology

    topology = MissionTopology.COORD if coord else MissionTopology.SINGLE_BRANCH
    return patch(
        "specify_cli.coordination.commit_router.resolve_topology",
        return_value=topology,
    )


# ---------------------------------------------------------------------------
# Helper: a minimal CommitResult-like object
# ---------------------------------------------------------------------------


class _FakeCommitResult:
    sha = "abc1234567890"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_unprotected_direct_commit(tmp_path: Path) -> None:
    """Unprotected placement → safe_commit called directly; no materialiser."""
    policy = _make_policy(protected=False)
    primary_target = _make_primary_target()
    mission_slug = "001-my-mission"
    artifact = tmp_path / "spec.md"
    artifact.write_text("# Spec\n", encoding="utf-8")

    materialise_calls: list[object] = []

    with (
        _patch_topology(coord=False),
        patch(
            "specify_cli.coordination.commit_router.resolve_placement_only",
            return_value=primary_target,
        ),
        patch(
            "specify_cli.coordination.commit_router._materialise_coord_worktree",
            side_effect=lambda *a, **kw: materialise_calls.append(a) or (tmp_path, (artifact,)),
        ),
        patch(
            "specify_cli.coordination.commit_router.safe_commit",
            return_value=_FakeCommitResult(),
        ),
    ):
        from specify_cli.coordination.commit_router import commit_for_mission

        result = commit_for_mission(
            repo_root=tmp_path,
            mission_slug=mission_slug,
            files=(artifact,),
            message="Add spec",
            policy=policy,
        )

    assert result.status == "committed"
    assert result.placement_ref == "main"
    # The materialiser must NOT have been called on the unprotected path.
    assert len(materialise_calls) == 0


def test_protected_coord_placement_materialises(tmp_path: Path) -> None:
    """Protected COORDINATION placement → materialiser called; artifact on coord branch."""
    policy = _make_policy(protected=True)
    coord_target = _make_coord_target()
    mission_slug = "001-my-mission"
    artifact = tmp_path / "spec.md"
    artifact.write_text("# Spec\n", encoding="utf-8")

    coord_artifact = tmp_path / ".worktrees" / "coord" / "kitty-specs" / mission_slug / "spec.md"
    coord_artifact.parent.mkdir(parents=True)
    coord_artifact.write_text("# Spec\n", encoding="utf-8")

    materialise_calls: list[object] = []

    def _fake_materialise(repo_root, mission_slug, placement, files, **kwargs):
        materialise_calls.append((repo_root, mission_slug, placement))
        return coord_artifact.parent.parent.parent.parent, (coord_artifact,)

    with (
        _patch_topology(coord=True),
        patch(
            "specify_cli.coordination.commit_router.resolve_placement_only",
            return_value=coord_target,
        ),
        patch(
            "specify_cli.coordination.commit_router._materialise_coord_worktree",
            side_effect=_fake_materialise,
        ),
        patch(
            "specify_cli.coordination.commit_router.safe_commit",
            return_value=_FakeCommitResult(),
        ),
    ):
        from specify_cli.coordination.commit_router import commit_for_mission

        result = commit_for_mission(
            repo_root=tmp_path,
            mission_slug=mission_slug,
            files=(artifact,),
            message="Add spec",
            policy=policy,
        )

    assert result.status == "committed"
    assert result.placement_ref == "kitty/mission-my-slug-ABCD1234"
    # Materialiser MUST have been called.
    assert len(materialise_calls) == 1


def test_idempotent_unchanged(tmp_path: Path) -> None:
    """safe_commit raises 'nothing to commit' → status is 'unchanged'."""
    policy = _make_policy(protected=False)
    from mission_runtime import CommitTarget

    primary_target = CommitTarget(ref="main")
    artifact = tmp_path / "spec.md"
    artifact.write_text("# Spec\n", encoding="utf-8")

    exc = subprocess.CalledProcessError(1, ["git", "commit"])
    exc.stderr = "nothing to commit, working tree clean"

    with (
        _patch_topology(coord=False),
        patch(
            "specify_cli.coordination.commit_router.resolve_placement_only",
            return_value=primary_target,
        ),
        patch(
            "specify_cli.coordination.commit_router.safe_commit",
            side_effect=exc,
        ),
    ):
        from specify_cli.coordination.commit_router import commit_for_mission

        result = commit_for_mission(
            repo_root=tmp_path,
            mission_slug="001-my-mission",
            files=(artifact,),
            message="Add spec",
            policy=policy,
        )

    assert result.status == "unchanged"


def test_1718_no_materialisation_at_read_time(tmp_path: Path) -> None:
    """#1718: the materialiser is NOT called before commit_for_mission is invoked."""
    # This test proves that _materialise_coord_worktree is only called INSIDE
    # commit_for_mission (at the commit boundary), never at import/read time.
    materialise_calls: list[object] = []
    policy = _make_policy(protected=True)

    from mission_runtime import CommitTarget

    coord_target = CommitTarget(ref="kitty/mission-x-ABCD1234")
    artifact = tmp_path / "spec.md"
    artifact.write_text("# Spec\n", encoding="utf-8")
    coord_artifact = tmp_path / "coord-spec.md"
    coord_artifact.write_text("# Spec\n", encoding="utf-8")

    def _fake_materialise(repo_root, mission_slug, placement, files, **kwargs):
        materialise_calls.append("called")
        return tmp_path, (coord_artifact,)

    with patch(
        "specify_cli.coordination.commit_router._materialise_coord_worktree",
        side_effect=_fake_materialise,
    ):
        # Import the module — materialiser should NOT be called just by importing.
        import importlib

        import specify_cli.coordination.commit_router as _mod

        importlib.reload(_mod)
        assert len(materialise_calls) == 0, "Materialiser called at import/read time!"

        # Only called when commit_for_mission is explicitly invoked.
        from mission_runtime import MissionTopology

        with (
            patch.object(_mod, "resolve_topology", return_value=MissionTopology.COORD),
            patch.object(_mod, "resolve_placement_only", return_value=coord_target),
            patch.object(_mod, "_materialise_coord_worktree", side_effect=_fake_materialise),
            patch.object(_mod, "safe_commit", return_value=_FakeCommitResult()),
        ):
            _mod.commit_for_mission(
                repo_root=tmp_path,
                mission_slug="001-x",
                files=(artifact,),
                message="m",
                policy=policy,
            )

    assert len(materialise_calls) == 1


def test_negative_stubbed_materialiser_causes_wrong_result(tmp_path: Path) -> None:
    """NEGATIVE: when materialiser is stubbed to return the PRIMARY path, the router
    must be caught committing to the wrong surface.

    The materialiser's job is to stage artifacts in the COORDINATION worktree, not in
    the primary checkout (``tmp_path``).  This test proves the materialiser is
    load-bearing: when it is replaced by a stub that silently returns the primary path,
    ``safe_commit`` receives ``worktree_root == tmp_path`` (primary), which is the
    wrong surface.  The assertion is:

        worktree_root passed to safe_commit MUST NOT be tmp_path (the primary checkout)

    If the gate inside commit_for_mission that checks placement/surface ever regresses
    (e.g. materialise-then-retry is replaced by a direct primary commit), this test
    goes RED because safe_commit would again receive ``worktree_root == tmp_path``.
    """
    policy = _make_policy(protected=True)
    from mission_runtime import CommitTarget

    coord_target = CommitTarget(ref="kitty/mission-x-ABCD1234")
    artifact = tmp_path / "spec.md"
    artifact.write_text("# Spec\n", encoding="utf-8")

    # A fake coord worktree path — distinct from tmp_path (the primary checkout).
    coord_worktree = tmp_path / ".worktrees" / "coord"
    coord_worktree.mkdir(parents=True)
    coord_artifact = coord_worktree / "spec.md"
    coord_artifact.write_text("# Spec\n", encoding="utf-8")

    # Stub that returns the PRIMARY path — wrong surface.
    def _stub_materialise_primary(*args, **kwargs):
        return tmp_path, (artifact,)

    # Real-ish stub that returns the COORD worktree path — correct surface.
    def _stub_materialise_coord(*args, **kwargs):
        return coord_worktree, (coord_artifact,)

    safe_commit_calls: list[dict] = []

    def _spy_safe_commit(**kwargs):
        safe_commit_calls.append(dict(kwargs))
        return _FakeCommitResult()

    # --- Scenario A: stub returns PRIMARY path (regression / no-op materialiser) ---
    # safe_commit receives worktree_root == tmp_path → wrong surface.
    safe_commit_calls.clear()
    with (
        _patch_topology(coord=True),
        patch(
            "specify_cli.coordination.commit_router.resolve_placement_only",
            return_value=coord_target,
        ),
        patch(
            "specify_cli.coordination.commit_router._materialise_coord_worktree",
            side_effect=_stub_materialise_primary,
        ),
        patch(
            "specify_cli.coordination.commit_router.safe_commit",
            side_effect=_spy_safe_commit,
        ),
    ):
        from specify_cli.coordination.commit_router import commit_for_mission

        commit_for_mission(
            repo_root=tmp_path,
            mission_slug="001-x",
            files=(artifact,),
            message="m",
            policy=policy,
        )

    # Discriminating assertion: when materialiser returns primary, safe_commit lands
    # on the PRIMARY checkout — this is the bug this test must catch.
    assert len(safe_commit_calls) == 1
    wrong_surface_root = safe_commit_calls[0]["worktree_root"]
    assert wrong_surface_root == tmp_path, (
        "Expected stub-materialiser to route to primary (tmp_path); "
        f"got {wrong_surface_root!r} instead."
    )

    # --- Scenario B: materialiser returns COORD path (correct behaviour) ---
    # safe_commit must NOT receive tmp_path as worktree_root.
    safe_commit_calls.clear()
    with (
        _patch_topology(coord=True),
        patch(
            "specify_cli.coordination.commit_router.resolve_placement_only",
            return_value=coord_target,
        ),
        patch(
            "specify_cli.coordination.commit_router._materialise_coord_worktree",
            side_effect=_stub_materialise_coord,
        ),
        patch(
            "specify_cli.coordination.commit_router.safe_commit",
            side_effect=_spy_safe_commit,
        ),
    ):
        commit_for_mission(
            repo_root=tmp_path,
            mission_slug="001-x",
            files=(artifact,),
            message="m",
            policy=policy,
        )

    assert len(safe_commit_calls) == 1
    correct_surface_root = safe_commit_calls[0]["worktree_root"]
    # The commit MUST land on the coord worktree, not on the primary checkout.
    assert correct_surface_root != tmp_path, (
        "Correct materialiser should route to coord worktree, not primary (tmp_path)."
    )
    assert correct_surface_root == coord_worktree
