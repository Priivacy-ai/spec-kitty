"""Fixture wiring for ``tests/specify_cli/``.

Re-exports the un-patched flat-topology mission fixture so tests in this
directory receive it by pytest fixture injection (parameter name) rather
than a module-level import that shadows the parameter (F811). No resolver is
patched by this fixture -- topology routing uses real git + filesystem
state. Mirrors ``tests/acceptance/conftest.py``'s rationale for the same
shared fixture.
"""

from __future__ import annotations

from tests.integration.coord_topology_fixture import (  # noqa: F401 — pytest fixture re-export
    flat_topology_mission,
)
