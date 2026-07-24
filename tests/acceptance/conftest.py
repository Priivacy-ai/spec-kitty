"""Fixture wiring for the acceptance behavioural-contract suite.

Re-exports the un-patched coordination/flat topology fixtures so tests in this
directory receive them by pytest fixture injection (parameter name) rather than a
module-level import that shadows the parameter (F811). No resolver is patched by
these fixtures — topology routing uses real git + filesystem state.
"""

from __future__ import annotations

from tests.integration.coord_topology_fixture import (  # noqa: F401 — pytest fixture re-exports
    coord_topology_mission,
    flat_topology_mission,
)
