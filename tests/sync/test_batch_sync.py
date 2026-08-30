"""Surviving coverage for the retained `sync/batch.py` surface.

#3167 retired the queue-backed drain (`batch_sync`, `sync_all_queued_events` and
their callee tree), and with it 37 of this module's original 40 test nodes -- the
tests whose only subject was the deleted sender. See
`kitty-specs/chain-b-consent-bypass-3167-01KZ63HK/contracts/deletion-manifest.md`
for the per-node disposition; every retired node names a surviving node id or the
argument that its requirement died with the drain.

What is left covers surface that is still production-alive:

* `BatchSyncResult` -- consumed by `sync/background.py`.
* `categorize_error` -- consumed by `sync/diagnose.py`.

The class names are deliberately unchanged: they carry the node ids the mission's
survivor check greps for. `TestBatchSyncSuccess` now holds a single
`categorize_error` unit test rather than a batch-sync scenario, which reads oddly
in isolation and is the accepted cost of keeping that node id stable.
"""

import pytest

from specify_cli.sync.batch import BatchSyncResult, categorize_error

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


class TestBatchSyncResult:
    """Test BatchSyncResult class"""

    def test_initial_state(self):
        """Test BatchSyncResult initializes with zeros"""
        result = BatchSyncResult()
        assert result.total_events == 0
        assert result.synced_count == 0
        assert result.duplicate_count == 0
        assert result.error_count == 0
        assert result.synced_ids == []
        assert result.failed_ids == []
        assert result.error_messages == []

    def test_success_count(self):
        """Test success_count includes synced and duplicates"""
        result = BatchSyncResult()
        result.synced_count = 10
        result.duplicate_count = 5
        assert result.success_count == 15


class TestBatchSyncSuccess:
    """Test successful batch sync operations"""
    def test_oversized_batch_error_classifies_without_unknown(self):
        assert categorize_error("Batch payload exceeds decompressed byte limit") == "oversized_batch"
