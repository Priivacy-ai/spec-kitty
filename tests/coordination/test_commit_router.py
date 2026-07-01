"""Tests for commit_router.commit_for_mission (WP02 / T009; write-surface-coherence WP02).

Covers:
- Coordination kind under coord topology → materialises coordination worktree +
  lands on coord branch.
- Primary kind → direct commit (no materialiser called), even under coord topology
  (write-surface-coherence WP02: the planning→coord route is removed).
- Idempotent (unchanged artifact → ``unchanged`` status).
- #1718 preserved: materialisation happens at the commit boundary, not at read time.
- NEGATIVE variant: stubbing the materialiser causes a test failure (proves the
  materialiser is actually called on the coordination path).

``commit_for_mission`` now takes a REQUIRED ``kind`` keyword
(write-surface-coherence WP02): a ``_PRIMARY_ARTIFACT_KINDS`` member resolves to
the primary ``target_branch`` for every topology and NEVER routes through
coordination; a coordination kind keeps the topology-routed placement. The
fixtures stub ``resolve_placement_only`` (the kind-aware placement),
``resolve_topology`` (the routing topology), AND ``_resolve_primary_target_branch``
(the primary ref the router compares the placement against) so the three legs
stay consistent.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from mission_runtime import MissionArtifactKind
from specify_cli.git.protection_policy import ProtectionPolicy

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# A coordination ref vs the primary target branch the router compares against.
_PRIMARY_BRANCH = "main"
_COORD_REF = "kitty/mission-my-slug-ABCD1234"


def _patch_primary_target(ref: str = _PRIMARY_BRANCH) -> object:
    """Patch the router's primary-target-branch read.

    ``commit_for_mission`` derives ``use_coord`` from the kind-aware placement by
    comparing ``placement.ref`` against the mission's primary ``target_branch``
    (write-surface-coherence WP02). Unit fixtures have no real meta.json, so this
    pins the primary ref deterministically.
    """
    return patch(
        "specify_cli.coordination.commit_router._resolve_primary_target_branch",
        return_value=ref,
    )


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

    return CommitTarget(ref=_COORD_REF)


def _make_primary_target() -> object:
    """Return a ref-only CommitTarget for a primary placement."""
    from mission_runtime import CommitTarget

    return CommitTarget(ref=_PRIMARY_BRANCH)


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
        _patch_primary_target(),
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
            kind=MissionArtifactKind.SPEC,
        )

    assert result.status == "committed"
    assert result.placement_ref == _PRIMARY_BRANCH
    # The materialiser must NOT have been called on the unprotected path.
    assert len(materialise_calls) == 0


def test_protected_coord_placement_materialises(tmp_path: Path) -> None:
    """Coordination kind under coord topology → materialiser called; artifact on coord branch.

    A coordination kind (``ANALYSIS_REPORT``) keeps the topology-routed coord
    placement, so the router materialises the coord worktree (C-001) — unchanged
    by write-surface-coherence WP02 (only PRIMARY kinds were re-routed off coord).
    """
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
        _patch_primary_target(),
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
            message="Add analysis report",
            policy=policy,
            kind=MissionArtifactKind.ANALYSIS_REPORT,
        )

    assert result.status == "committed"
    assert result.placement_ref == _COORD_REF
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
        _patch_primary_target(),
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
            kind=MissionArtifactKind.SPEC,
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
            patch.object(_mod, "_resolve_primary_target_branch", return_value=_PRIMARY_BRANCH),
            patch.object(_mod, "_materialise_coord_worktree", side_effect=_fake_materialise),
            patch.object(_mod, "safe_commit", return_value=_FakeCommitResult()),
        ):
            _mod.commit_for_mission(
                repo_root=tmp_path,
                mission_slug="001-x",
                files=(artifact,),
                message="m",
                policy=policy,
                kind=MissionArtifactKind.ANALYSIS_REPORT,
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
        _patch_primary_target(),
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
            kind=MissionArtifactKind.ANALYSIS_REPORT,
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
        _patch_primary_target(),
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
            kind=MissionArtifactKind.ANALYSIS_REPORT,
        )

    assert len(safe_commit_calls) == 1
    correct_surface_root = safe_commit_calls[0]["worktree_root"]
    # The commit MUST land on the coord worktree, not on the primary checkout.
    assert correct_surface_root != tmp_path, (
        "Correct materialiser should route to coord worktree, not primary (tmp_path)."
    )
    assert correct_surface_root == coord_worktree


# ---------------------------------------------------------------------------
# write-surface-coherence WP02 / T011 — RED-FIRST caller-convergence tests
# ---------------------------------------------------------------------------
#
# These pin the FR-003 / C-005 unification: a PRIMARY artifact kind (spec / plan /
# tasks / metadata) committed under COORD topology lands on the PRIMARY target
# branch and NEVER materialises the coordination worktree — the planning→coord
# route is removed. A COORD kind (analysis-report / status) keeps routing to
# coordination (C-001). On PRE-WP02 code, ``commit_for_mission`` routed every
# planning artifact through coordination whenever the topology routed coord, so
# the SPEC-on-coord assertion below goes RED on the unfixed tree (proven by
# revert+restore).


def test_primary_kind_under_coord_topology_does_not_route_to_coord(tmp_path: Path) -> None:
    """RED-FIRST: a SPEC (primary kind) under COORD topology lands on PRIMARY, not coord.

    Pre-WP02 the router routed planning artifacts to coordination whenever the
    stored topology routed coord. WP02 derives routing from the kind-aware
    placement: a primary kind resolves to the primary ``target_branch`` and the
    materialiser is NEVER engaged. The discriminating assertions are:

    * the materialiser was NOT called (no coord worktree),
    * ``safe_commit`` received ``worktree_root == repo_root`` (the primary),
    * ``placement_ref`` is the PRIMARY branch.
    """
    policy = _make_policy(protected=False)
    artifact = tmp_path / "spec.md"
    artifact.write_text("# Spec\n", encoding="utf-8")

    # The kind-aware resolver returns the PRIMARY ref for a primary kind (this is
    # WP01's behavior); the topology still routes coord. The router must trust the
    # placement, not the topology, for a primary kind.
    from mission_runtime import CommitTarget

    primary_placement = CommitTarget(ref=_PRIMARY_BRANCH)

    materialise_calls: list[object] = []
    safe_commit_calls: list[dict] = []

    with (
        _patch_topology(coord=True),  # topology routes coord …
        _patch_primary_target(),  # … but the primary target is "main" …
        patch(
            "specify_cli.coordination.commit_router.resolve_placement_only",
            return_value=primary_placement,  # … and the SPEC placement IS "main".
        ),
        patch(
            "specify_cli.coordination.commit_router._materialise_coord_worktree",
            side_effect=lambda *a, **kw: materialise_calls.append(a) or (tmp_path, (artifact,)),
        ),
        patch(
            "specify_cli.coordination.commit_router.safe_commit",
            side_effect=lambda **kw: safe_commit_calls.append(kw) or _FakeCommitResult(),
        ),
    ):
        from specify_cli.coordination.commit_router import commit_for_mission

        result = commit_for_mission(
            repo_root=tmp_path,
            mission_slug="001-my-mission",
            files=(artifact,),
            message="Add spec",
            policy=policy,
            kind=MissionArtifactKind.SPEC,
        )

    # The materialiser MUST NOT have been called — no planning→coord route.
    assert len(materialise_calls) == 0, (
        "SPEC (primary kind) under coord topology materialised the coordination "
        "worktree — the planning→coord route was not removed (write-surface-coherence WP02)."
    )
    assert len(safe_commit_calls) == 1
    assert safe_commit_calls[0]["worktree_root"] == tmp_path, (
        "SPEC commit did not land on the primary checkout."
    )
    assert result.status == "committed"
    assert result.placement_ref == _PRIMARY_BRANCH


def test_coord_kind_under_coord_topology_still_routes_to_coord(tmp_path: Path) -> None:
    """A COORD kind (ANALYSIS_REPORT) under COORD topology STILL routes to coordination (C-001).

    The bifurcation's other half: WP02 removed the planning→coord route but the
    coordination kinds (analysis-report, status) MUST keep materialising the coord
    worktree. This guards against an over-broad fix that flips every kind primary.
    """
    policy = _make_policy(protected=True)
    coord_target = _make_coord_target()
    artifact = tmp_path / "analysis-report.md"
    artifact.write_text("# Analysis\n", encoding="utf-8")
    coord_artifact = tmp_path / ".worktrees" / "coord" / "analysis-report.md"
    coord_artifact.parent.mkdir(parents=True)
    coord_artifact.write_text("# Analysis\n", encoding="utf-8")

    materialise_calls: list[object] = []

    def _fake_materialise(repo_root, mission_slug, placement, files, **kwargs):
        materialise_calls.append((repo_root, mission_slug, placement))
        return coord_artifact.parent, (coord_artifact,)

    with (
        _patch_topology(coord=True),
        _patch_primary_target(),
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
            mission_slug="001-my-mission",
            files=(artifact,),
            message="Add analysis report",
            policy=policy,
            kind=MissionArtifactKind.ANALYSIS_REPORT,
        )

    # The COORD kind MUST still materialise the coord worktree.
    assert len(materialise_calls) == 1, (
        "ANALYSIS_REPORT (coord kind) did not route to coordination — the fix is "
        "over-broad and broke C-001."
    )
    assert result.status == "committed"
    assert result.placement_ref == _COORD_REF


# ---------------------------------------------------------------------------
# write-surface-coherence WP05 / T023 — DECISION 8 runtime guard
# ---------------------------------------------------------------------------
#
# Once planning no longer transits coord (WP02/WP03), the coord-staging helper is
# reachable ONLY for coordination kinds. A PRIMARY kind arriving at
# ``_materialise_coord_worktree`` means a caller mis-routed a planning artifact
# onto the coordination branch — the RUNTIME guard (DECISION 8) must raise, not
# silently stage. This is the test for the guard added in T020. On pre-WP05 code
# the helper had no guard and would proceed into ``CoordinationWorkspace.resolve``,
# so the ``pytest.raises`` below goes RED (no exception) — proven by revert+restore.


def test_materialise_coord_worktree_rejects_primary_kind(tmp_path: Path) -> None:
    """DECISION 8: a PRIMARY kind reaching ``_materialise_coord_worktree`` raises.

    The guard fires at the staging entry BEFORE any worktree resolution, so a
    planning artifact can never be staged onto the coordination branch. The test
    calls the helper directly (the entry point the guard protects) with a real
    primary kind (``SPEC``) and a realistic coord-worktree-style placement, and
    asserts the typed :class:`PrimaryKindReachedCoordStagingError` is raised.
    """
    from mission_runtime import CommitTarget
    from specify_cli.coordination.commit_router import (
        PrimaryKindReachedCoordStagingError,
        _materialise_coord_worktree,
    )

    artifact = tmp_path / "kitty-specs" / "001-write-surface" / "spec.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("# Spec\n", encoding="utf-8")
    coord_placement = CommitTarget(ref="kitty/mission-write-surface-01KVTVZS3A4B5C6D")

    with pytest.raises(PrimaryKindReachedCoordStagingError):
        _materialise_coord_worktree(
            tmp_path,
            "001-write-surface",
            coord_placement,
            (artifact,),
            kind=MissionArtifactKind.SPEC,
        )


def test_materialise_coord_worktree_allows_coord_kind(tmp_path: Path) -> None:
    """A COORD kind passes the guard (degrades to primary on unresolvable mid8).

    The complement of the guard test: a coordination kind (``ANALYSIS_REPORT``)
    must NOT trip the guard. With no resolvable mid8 in a bare ``tmp_path`` the
    helper degrades to the primary checkout (C-004 safety) — proving the guard
    did not fire and the COORD path proceeded.
    """
    from mission_runtime import CommitTarget
    from specify_cli.coordination.commit_router import _materialise_coord_worktree

    artifact = tmp_path / "kitty-specs" / "001-write-surface" / "analysis-report.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("# Analysis\n", encoding="utf-8")
    coord_placement = CommitTarget(ref="kitty/mission-write-surface-01KVTVZS3A4B5C6D")

    worktree_root, paths = _materialise_coord_worktree(
        tmp_path,
        "001-write-surface",
        coord_placement,
        (artifact,),
        kind=MissionArtifactKind.ANALYSIS_REPORT,
    )
    # No mid8 ⇒ degrades to the primary checkout, but the guard did NOT raise.
    assert worktree_root == tmp_path
    assert paths == (artifact,)
