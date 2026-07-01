"""Seam-foundation tests for the MissionTopology SSOT (WP01 / #2069).

Pins three orthogonal contracts that WP02/WP03/WP04 depend on:

* FR-001 — the ``MissionTopology`` enum names the 2×2 coordination × lanes grid
  as four cells and excludes ``FLATTENED`` (a provenance flag, not a shape).
* FR-001 — ``classify_topology`` is the single authority mapping
  ``(coordination_branch, has_lanes)`` to a topology cell; ``FLATTENED`` is
  never produced.
* FR-005 — ``routes_through_coordination`` is the single per-ref routing
  predicate; it returns ``True`` only for a ``COORDINATION`` target.

The serialized ``.value`` strings are asserted so WP02 (meta.json minting) and
WP03 (resolver) agree on the wire form — any later drift fails this test rather
than silently breaking the round-trip.
"""

from __future__ import annotations

import pytest

from mission_runtime import (
    MissionTopology,
    classify_topology,
    routes_through_coordination,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# Production-shaped coordination branch ref (kitty/mission-<slug>-<mid8>-coord),
# so the "branch present" classifier signal is exercised with a real-format
# value rather than a bare placeholder.
COORD_BRANCH_REF = "kitty/mission-single-planning-surface-authority-01KVPR00-coord"
PRIMARY_BRANCH_REF = "kitty/mission-single-planning-surface-authority-01KVPR00"


def test_mission_topology_has_exactly_the_four_shape_cells() -> None:
    """FR-001: the enum names exactly the 2×2 grid — no more, no fewer."""
    assert {member.name for member in MissionTopology} == {
        "SINGLE_BRANCH",
        "LANES",
        "COORD",
        "LANES_WITH_COORD",
    }


def test_mission_topology_excludes_flattened_member() -> None:
    """FR-001: FLATTENED is a provenance flag, never a shape value."""
    assert not hasattr(MissionTopology, "FLATTENED")


@pytest.mark.parametrize(
    ("member", "expected_value"),
    [
        (MissionTopology.SINGLE_BRANCH, "single_branch"),
        (MissionTopology.LANES, "lanes"),
        (MissionTopology.COORD, "coord"),
        (MissionTopology.LANES_WITH_COORD, "lanes_with_coord"),
    ],
)
def test_mission_topology_serialized_values_are_pinned(
    member: MissionTopology, expected_value: str
) -> None:
    """FR-001 / R4: the wire form WP02/WP03 round-trip against is fixed."""
    assert member.value == expected_value


@pytest.mark.parametrize(
    ("topology", "expected"),
    [
        (MissionTopology.COORD, True),
        (MissionTopology.LANES_WITH_COORD, True),
        (MissionTopology.SINGLE_BRANCH, False),
        (MissionTopology.LANES, False),
    ],
)
def test_routes_through_coordination_topology_truth_table(
    topology: MissionTopology, expected: bool
) -> None:
    """FR-005 / FR-001b: the predicate routes from the STORED topology.

    True only for the two coord-routing cells (COORD / LANES_WITH_COORD); the two
    coord-less cells return False. The retired per-ref ``CommitTarget`` arm is gone
    — there is no ref-local enum to consult. Exhaustive over the 2×2 grid so a
    new member would force this table to stay complete.
    """
    assert set(MissionTopology) == {
        MissionTopology.COORD,
        MissionTopology.LANES_WITH_COORD,
        MissionTopology.SINGLE_BRANCH,
        MissionTopology.LANES,
    }
    assert routes_through_coordination(topology) is expected


@pytest.mark.parametrize(
    ("coordination_branch", "has_lanes", "expected"),
    [
        (None, False, MissionTopology.SINGLE_BRANCH),
        (None, True, MissionTopology.LANES),
        (COORD_BRANCH_REF, False, MissionTopology.COORD),
        (COORD_BRANCH_REF, True, MissionTopology.LANES_WITH_COORD),
    ],
)
def test_classify_topology_full_2x2_truth_table(
    coordination_branch: str | None,
    has_lanes: bool,
    expected: MissionTopology,
) -> None:
    """FR-001: classify_topology maps every (coord, lanes) cell to one shape."""
    assert classify_topology(coordination_branch, has_lanes) is expected


def test_classify_topology_never_returns_flattened() -> None:
    """FR-001: a flattened mission classifies as a shape + provenance flag.

    classify_topology has no flattened input or output; exhausting the 2×2 grid
    must only ever yield the four shape cells.
    """
    results = {
        classify_topology(coordination_branch, has_lanes)
        for coordination_branch in (None, COORD_BRANCH_REF)
        for has_lanes in (False, True)
    }
    assert results == {
        MissionTopology.SINGLE_BRANCH,
        MissionTopology.LANES,
        MissionTopology.COORD,
        MissionTopology.LANES_WITH_COORD,
    }


def test_public_surface_exports_all_three_symbols() -> None:
    """T007: WP02/WP03/WP04 import these from the package root."""
    import mission_runtime

    for symbol in ("MissionTopology", "classify_topology", "routes_through_coordination"):
        assert symbol in mission_runtime.__all__
        assert hasattr(mission_runtime, symbol)
