"""M2 canonical integration: pin ``status.migrate_lifecycle_envelope._generate_node_id``
to ``sync.clock.generate_node_id`` byte-for-byte (the CORE module may not import the
INTEGRATION one -- tests/architectural/test_integration_boundary.py -- so the derivation is
duplicated and this test is what keeps the two from drifting)."""

from __future__ import annotations

import pytest

from specify_cli.status import migrate_lifecycle_envelope as mle
from specify_cli.sync.clock import generate_node_id

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_status_node_id_matches_sync_clock_generate_node_id() -> None:
    assert mle._generate_node_id() == generate_node_id()
    assert len(mle._generate_node_id()) == 12
