"""Lamport clock reconciliation (T039).

Originally the emit → queue → **batch sync** → server integration suite. #3167
retired the queue-backed drain, so the 7 nodes that drove `batch_sync` went with
it; what survives here is the `sync.clock` coverage, which never touched the
drain. Per-node disposition:
`kitty-specs/chain-b-consent-bypass-3167-01KZ63HK/contracts/deletion-manifest.md`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

from specify_cli.sync.clock import LamportClock


class TestLamportClockReconciliation:
    """Test clock reconciliation across different scenarios."""

    def test_clock_receive_updates_from_remote(self, tmp_path: Path):
        """Clock reconciles when remote value is higher."""
        clock = LamportClock(value=5, node_id="local", _storage_path=tmp_path / "c.json")
        new_value = clock.receive(100)
        assert new_value == 101
        assert clock.value == 101

    def test_clock_persists_after_reconciliation(self, tmp_path: Path):
        """Clock state is persisted after receive()."""
        path = tmp_path / "c.json"
        clock = LamportClock(value=5, node_id="local", _storage_path=path)
        clock.receive(100)

        # Reload and verify
        reloaded = LamportClock.load(path)
        assert reloaded.value == 101
