"""Shared fixtures for tests/integration suite."""

from __future__ import annotations

import pytest

# Register the coord-topology test fixture + asserters so they are available
# to every test in the tests/integration/ subtree without a per-file import.
# See tests/integration/conftest_coord_topology.py for the registration facade
# and tests/integration/coord_topology_fixture.py for the implementation.
from tests.integration.conftest_coord_topology import (  # noqa: F401
    coord_topology_mission,
    coord_topology_mission_sentinel_meta,
    coord_topology_mission_tasks_husk,
    flat_topology_mission,
)


@pytest.fixture(autouse=True)
def _disable_saas_sync_for_integration_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable the SaaS sync boundary preflight for integration tests.

    The root conftest enables SPEC_KITTY_ENABLE_SAAS_SYNC=1 to keep legacy
    sync/auth tests live, but the planning/commit-boundary integration tests
    invoke ``setup-plan`` which gates on the boundary preflight with
    ``require_auth=True``. Tests run without hosted auth credentials, so the
    gate refuses with SAAS_SYNC_UNAUTHENTICATED before the actual behavior
    being tested can run. These tests don't intentionally test the boundary
    preflight, so we disable the gate here.
    """
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
