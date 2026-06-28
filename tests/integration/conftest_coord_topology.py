"""Registration module for the coord-topology test fixture (FR-014, WP01).

Re-exports all fixtures and asserters from
:mod:`tests.integration.coord_topology_fixture` so that the integration
conftest can import them with a single wildcard and make them auto-available
to every test in the ``tests/integration/`` subtree.

Usage (in ``tests/integration/conftest.py``)::

    from tests.integration.conftest_coord_topology import (
        coord_topology_mission,
        flat_topology_mission,
    )

This module intentionally contains NO test functions, NO monkeypatches, and NO
resolver stubs. It is purely a re-export facade.
"""

from tests.integration.coord_topology_fixture import (  # noqa: F401
    CoordTopologyContext,
    FlatTopologyContext,
    assert_both_legs,
    assert_reads_primary,
    assert_status_from_coord,
    coord_topology_mission,
    coord_topology_mission_sentinel_meta,
    coord_topology_mission_tasks_husk,
    flat_topology_mission,
)

__all__ = [
    "CoordTopologyContext",
    "FlatTopologyContext",
    "assert_both_legs",
    "assert_reads_primary",
    "assert_status_from_coord",
    "coord_topology_mission",
    "coord_topology_mission_sentinel_meta",
    "coord_topology_mission_tasks_husk",
    "flat_topology_mission",
]
