"""WP03 / T018 — pure ``resolve_context_for_mission`` projection (NFR-005, SC-002).

The functional-core tripwire (FR-004): :func:`resolve_context_for_mission` is a
PURE projection over the construction door ``build_execution_context``. It takes
``(mission_id, topology)`` + shell-assembled fragments and returns an
``MissionExecutionContext`` whose placement reflects the STORED topology — with **zero**
filesystem / git fixtures. If this test ever needs a ``tmp_path`` meta.json, a
repo init, or a ``load_meta`` monkeypatch, the resolver has regressed to impurity
— fix the RESOLVER, not the test.

All four ``MissionTopology`` cells are exercised so the coord-vs-flattened
placement projection is covered end-to-end, plus the T016 optional
input-assertion (supplied-vs-signal mismatch fails closed). The ``mission_id`` is
a production-shaped 26-char ULID (NFR-002 / realistic-test-data) — never a short
stand-in.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.fast]

from mission_runtime import (
    ActionContextError,
    BranchRefFragment,
    CommitTarget,
    IdentityFragment,
    MissionExecutionContext,
    MissionTopology,
    StatusSurfaceFragment,
    routes_through_coordination,
)
from mission_runtime.resolution import resolve_context_for_mission

# Production-shaped 26-char ULID (NFR-002): never a fabricated short id.
_MISSION_ID = "01KVPR000000000000000000ZZ"
_MISSION_SLUG = "single-planning-surface-authority-01KVPR00"
_TARGET_BRANCH = "feat/single-planning-surface-authority"
_COORD_BRANCH = "kitty/mission-single-planning-surface-authority-01KVPR00-coord"
_FEATURE_DIR = f"kitty-specs/{_MISSION_SLUG}"

# DoD-(a) absolute per-topology surface pin (FR-001b): COORD/LANES_WITH_COORD route
# through coordination, the two coord-less cells do NOT. A HARDCODED literal table,
# NOT ``routes_through_coordination(topology)`` (asserting the predicate against
# itself is a tautology). The 2×2 grid is small and stable, so the expectation is
# spelled out independently — the over-collapse "everything→PRIMARY" mutant-killer.
_EXPECTED_ROUTES_COORD = {
    MissionTopology.SINGLE_BRANCH: False,
    MissionTopology.LANES: False,
    MissionTopology.COORD: True,
    MissionTopology.LANES_WITH_COORD: True,
}


def _identity() -> IdentityFragment:
    return IdentityFragment.derive(mission_id=_MISSION_ID, mission_slug=_MISSION_SLUG)


def _branch_ref(coordination_branch: str | None) -> BranchRefFragment:
    # The shell pre-assembles this ref-only CommitTarget (C-007); the resolver
    # carries destination_ref through unchanged and routes from the stored topology.
    return BranchRefFragment(
        target_branch=_TARGET_BRANCH,
        coordination_branch=coordination_branch,
        destination_ref=CommitTarget(ref=coordination_branch or _TARGET_BRANCH),
    )


def _resolve(topology: MissionTopology, **kwargs: object) -> MissionExecutionContext:
    coordination_branch = (
        _COORD_BRANCH
        if topology in (MissionTopology.COORD, MissionTopology.LANES_WITH_COORD)
        else None
    )
    return resolve_context_for_mission(
        _MISSION_ID,
        topology,
        action="specify",
        mission_slug=_MISSION_SLUG,
        feature_dir=_FEATURE_DIR,
        target_branch=_TARGET_BRANCH,
        identity=_identity(),
        branch_ref=_branch_ref(coordination_branch),
        **kwargs,  # type: ignore[arg-type]
    )


_COORD_CELLS = (MissionTopology.COORD, MissionTopology.LANES_WITH_COORD)
_FLAT_CELLS = (MissionTopology.SINGLE_BRANCH, MissionTopology.LANES)


@pytest.mark.parametrize("topology", list(MissionTopology))
def test_projects_context_for_every_topology(topology: MissionTopology) -> None:
    """All four cells project a context with a topology-correct placement."""
    context = _resolve(topology)

    assert context.mission_slug == _MISSION_SLUG
    assert context.target_branch == _TARGET_BRANCH
    assert context.identity is not None
    assert context.identity.mission_id == _MISSION_ID
    assert context.identity.mid8 == _MISSION_ID[:8]

    assert context.branch_ref is not None
    assert context.artifact_placement is not None
    # DoD-(a): the absolute per-topology routing pin (FR-001b) — the over-collapse
    # mutant-killer that a leg-vs-leg differential cannot catch.
    assert (
        routes_through_coordination(topology) is _EXPECTED_ROUTES_COORD[topology]
    )
    # One CommitTarget shared by branch_ref + artifact_placement (C-PLACE-1).
    assert (
        context.artifact_placement.placement_ref
        is context.branch_ref.destination_ref
    )


@pytest.mark.parametrize("topology", _COORD_CELLS)
def test_coord_cells_route_through_coordination(topology: MissionTopology) -> None:
    """COORD / LANES_WITH_COORD route through coordination on the coord ref."""
    context = _resolve(topology)
    assert context.branch_ref is not None
    assert routes_through_coordination(topology) is True
    assert context.branch_ref.destination_ref.ref == _COORD_BRANCH


@pytest.mark.parametrize("topology", _FLAT_CELLS)
def test_flat_cells_project_flattened(topology: MissionTopology) -> None:
    """SINGLE_BRANCH / LANES do NOT route through coordination — target ref."""
    context = _resolve(topology)
    assert context.branch_ref is not None
    assert routes_through_coordination(topology) is False
    assert context.branch_ref.destination_ref.ref == _TARGET_BRANCH


def test_status_surface_fragment_carried_through() -> None:
    """A supplied status-surface fragment is projected onto the context verbatim."""
    surface = StatusSurfaceFragment(
        status_read_dir=Path(_FEATURE_DIR),
        status_write_dir=Path(_FEATURE_DIR),
    )
    context = _resolve(MissionTopology.LANES, status_surface=surface)
    assert context.status_surface is surface


def test_input_assertion_skipped_without_signals() -> None:
    """No corroborating signals supplied ⇒ the optional T016 guard is a no-op."""
    # COORD topology with NO has_lanes_signal: the guard is skipped, no raise.
    context = _resolve(MissionTopology.COORD)
    assert context.branch_ref is not None
    assert routes_through_coordination(MissionTopology.COORD) is True


def test_input_assertion_passes_when_signals_corroborate() -> None:
    """Supplying matching signals corroborates the topology (no raise)."""
    context = _resolve(
        MissionTopology.COORD,
        coordination_branch_signal=_COORD_BRANCH,
        has_lanes_signal=False,
    )
    assert context.branch_ref is not None
    assert routes_through_coordination(MissionTopology.COORD) is True


def test_input_assertion_fails_closed_on_mismatch() -> None:
    """Supplied topology disagreeing with the signals fails closed (T016)."""
    with pytest.raises(ActionContextError) as excinfo:
        # Claim COORD, but the signals imply SINGLE_BRANCH (no coord branch, no lanes).
        _resolve(
            MissionTopology.COORD,
            coordination_branch_signal=None,
            has_lanes_signal=False,
        )
    assert excinfo.value.code == "TOPOLOGY_INPUT_MISMATCH"
    message = str(excinfo.value)
    # Both topologies named (operator-debuggable).
    assert MissionTopology.COORD.value in message
    assert MissionTopology.SINGLE_BRANCH.value in message


def test_input_assertion_fails_closed_on_lanes_mismatch() -> None:
    """has_lanes signal flips the implied cell and is caught against the claim."""
    with pytest.raises(ActionContextError) as excinfo:
        # Claim SINGLE_BRANCH, but has_lanes=True implies LANES.
        _resolve(
            MissionTopology.SINGLE_BRANCH,
            coordination_branch_signal=None,
            has_lanes_signal=True,
        )
    assert excinfo.value.code == "TOPOLOGY_INPUT_MISMATCH"
    assert MissionTopology.LANES.value in str(excinfo.value)


def test_identity_mismatch_fails_closed() -> None:
    """A mission_id that disagrees with the identity fragment fails closed."""
    with pytest.raises(ActionContextError) as excinfo:
        resolve_context_for_mission(
            "01KOTHER0000000000000000ZZ",  # disagrees with the fragment's id
            MissionTopology.LANES,
            action="specify",
            mission_slug=_MISSION_SLUG,
            feature_dir=_FEATURE_DIR,
            target_branch=_TARGET_BRANCH,
            identity=_identity(),
            branch_ref=_branch_ref(None),
        )
    assert excinfo.value.code == "TOPOLOGY_INPUT_MISMATCH"
