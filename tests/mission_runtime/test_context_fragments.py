"""Unit tests for the doc-09 context fragments (WP03 / 01KTPKST).

These cover the fragment value objects + single-derivation invariants in
isolation (the dual-CWD parity behaviour is covered by
``tests/architectural/test_execution_context_parity.py``). Fast, hermetic,
no git / no filesystem.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.fast]

from mission_runtime import (
    ArtifactPlacementFragment,
    BranchRefFragment,
    CommitTarget,
    IdentityFragment,
    MissionExecutionContext,
    StatusSurfaceFragment,
    WorkspaceFragment,
)
from pathlib import Path


_MISSION_ID = "01KTPKST0000000000000000XY"


# ---------------------------------------------------------------------------
# T009 — single-derivation invariants
# ---------------------------------------------------------------------------


def test_identity_fragment_derives_mid8_once() -> None:
    """``IdentityFragment.derive`` computes ``mid8`` as ``mission_id[:8]``."""
    frag = IdentityFragment.derive(mission_id=_MISSION_ID, mission_slug="demo")
    assert frag.mid8 == _MISSION_ID[:8]
    assert frag.mission_id == _MISSION_ID
    assert frag.mission_slug == "demo"


def test_identity_fragment_rejects_inconsistent_mid8() -> None:
    """Constructing with a ``mid8`` that is not ``mission_id[:8]`` is rejected."""
    with pytest.raises(ValueError, match="mission_id\\[:8\\]"):
        IdentityFragment(mission_id=_MISSION_ID, mid8="WRONG000", mission_slug="demo")


def test_identity_fragment_is_frozen() -> None:
    frag = IdentityFragment.derive(mission_id=_MISSION_ID, mission_slug="demo")
    with pytest.raises((AttributeError, TypeError)):
        frag.mid8 = "tampered"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CommitTarget (ADR-2026-06-03-2)
# ---------------------------------------------------------------------------


def test_commit_target_is_ref_only() -> None:
    """``CommitTarget`` is a ref-only carrier (C-007 / FR-001b): no ``kind`` field.

    The retired per-ref topology enum is gone — routing is decided from the stored
    ``MissionTopology`` via ``routes_through_coordination``, never a ref-local enum.
    This pins the ref-only shape so a reintroduced ``kind`` field fails here.
    """
    target = CommitTarget(ref="kitty/mission-demo-01KTPKST")
    assert target.ref == "kitty/mission-demo-01KTPKST"
    assert set(CommitTarget.__dataclass_fields__) == {"ref"}


# ---------------------------------------------------------------------------
# BranchRefFragment + flattened topology
# ---------------------------------------------------------------------------


def test_branchref_fragment_flattened_has_no_coordination_branch() -> None:
    target = CommitTarget(ref="fixups/code-engine-stabilization")
    frag = BranchRefFragment(
        target_branch="fixups/code-engine-stabilization",
        coordination_branch=None,
        destination_ref=target,
    )
    assert frag.coordination_branch is None
    assert frag.destination_ref.ref == "fixups/code-engine-stabilization"


# ---------------------------------------------------------------------------
# StatusSurfaceFragment collapse
# ---------------------------------------------------------------------------


def test_status_surface_collapses_when_flattened() -> None:
    surface = Path("/repo/kitty-specs/demo-01KTPKST")
    frag = StatusSurfaceFragment(status_read_dir=surface, status_write_dir=surface)
    assert frag.status_read_dir == frag.status_write_dir


# ---------------------------------------------------------------------------
# T008 — op-composite assembly + substrate compatibility (C-004 / NFR-001)
# ---------------------------------------------------------------------------


def test_execution_context_default_fragments_are_none() -> None:
    """A bare substrate context (not-yet-converted consumer) has no fragments."""
    ctx = MissionExecutionContext(
        action="tasks",
        mission_slug="demo",
        feature_dir="/repo/kitty-specs/demo",
        target_branch="main",
        detection_method="explicit",
    )
    assert ctx.identity is None
    assert ctx.branch_ref is None
    assert ctx.workspace is None
    assert ctx.status_surface is None
    assert ctx.artifact_placement is None


def test_to_dict_excludes_fragments_preserving_substrate_shape() -> None:
    """``to_dict`` returns the historical flat shape (NFR-001) — no fragments."""
    surface = Path("/repo/kitty-specs/demo-01KTPKST")
    ctx = MissionExecutionContext(
        action="tasks",
        mission_slug="demo",
        feature_dir="/repo/kitty-specs/demo",
        target_branch="main",
        detection_method="explicit",
        identity=IdentityFragment.derive(mission_id=_MISSION_ID, mission_slug="demo"),
        branch_ref=BranchRefFragment(
            target_branch="main",
            coordination_branch=None,
            destination_ref=CommitTarget(ref="main"),
        ),
        status_surface=StatusSurfaceFragment(
            status_read_dir=surface, status_write_dir=surface
        ),
    )
    data = ctx.to_dict()
    for fragment_field in (
        "identity",
        "branch_ref",
        "workspace",
        "status_surface",
        "artifact_placement",
        "_FRAGMENT_FIELDS",
    ):
        assert fragment_field not in data, f"{fragment_field} leaked into to_dict()"
    # The historical substrate fields are present and intact.
    assert data["action"] == "tasks"
    assert data["mission_slug"] == "demo"
    assert data["target_branch"] == "main"
    assert data["dependencies"] == []
    assert data["commands"] == {}


def test_optional_fragments_can_be_attached() -> None:
    """Workspace/ArtifactPlacement fields exist for WP04/05/06."""
    ws = WorkspaceFragment(
        primary_root=Path("/repo"),
        current_cwd=Path("/repo/.worktrees/demo-lane-a"),
        coord_worktree=None,
        execution_workspace=Path("/repo/.worktrees/demo-lane-a"),
        allowed_command_cwd=Path("/repo"),
    )
    placement = ArtifactPlacementFragment(
        placement_ref=CommitTarget(ref="main")
    )
    ctx = MissionExecutionContext(
        action="implement",
        mission_slug="demo",
        feature_dir="/repo/kitty-specs/demo",
        target_branch="main",
        detection_method="explicit",
        workspace=ws,
        artifact_placement=placement,
    )
    assert ctx.workspace is ws
    assert ctx.artifact_placement is placement
    assert ctx.workspace.primary_root == Path("/repo")
