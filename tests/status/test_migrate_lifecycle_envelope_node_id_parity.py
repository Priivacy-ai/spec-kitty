"""M2 canonical integration: pin ``status.migrate_lifecycle_envelope._generate_node_id``
to ``specify_cli.identity.project.generate_node_id`` byte-for-byte (the CORE module may
not import across the boundary -- tests/architectural/test_integration_boundary.py --
so the derivation is duplicated and this test is what keeps the two from drifting).

(The parity counterpart was originally ``sync.clock.generate_node_id``; the sync
transport died in issue #5 and the canonical derivation now lives in
``specify_cli.identity.project``.)"""

from __future__ import annotations

import pytest

from specify_cli.identity.project import generate_node_id
from specify_cli.status import migrate_lifecycle_envelope as mle

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_status_node_id_matches_identity_generate_node_id() -> None:
    assert mle._generate_node_id() == generate_node_id()
    assert len(mle._generate_node_id()) == 12
