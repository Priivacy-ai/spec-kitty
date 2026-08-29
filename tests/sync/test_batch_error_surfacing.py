"""Error surfacing and diagnostics on the retained `sync/batch.py` surface.

#3167 retired the queue-backed drain, and with it the 26 nodes here whose subject
was a private parser reached only through it (`_parse_event_results`,
`_parse_error_response`) or `batch_sync` itself. Per-node disposition, each naming
a surviving node id or the argument that the requirement died with the drain:
`kitty-specs/chain-b-consent-bypass-3167-01KZ63HK/contracts/deletion-manifest.md`.

The 28 surviving nodes all cover production-alive surface:

- T006: Error categorisation (`categorize_error`, consumed by `sync/diagnose.py`)
- T007: Actionable summary formatting (`format_sync_summary`, lazy-map exported)
- T008: Selective queue removal via `OfflineQueue.process_batch_results`
- T009: `--report` flag JSON failure dump (`generate_failure_report`,
  `write_failure_report`, both lazy-map exported)
- `BatchSyncResult` / `BatchEventResult` properties, consumed by
  `sync/background.py`

The HTTP response-mapping equivalents of the retired parser tests now live on the
live delivery path at `tests/delivery/test_receivers.py::map_batch_response`.
"""

import json
from collections.abc import Iterator
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

from specify_cli.sync.batch import (
    BatchEventResult,
    BatchSyncResult,
    categorize_error,
    format_sync_summary,
    generate_failure_report,
    write_failure_report,
    ERROR_CATEGORIES,
    CATEGORY_ACTIONS,
)
from specify_cli.sync._team import CATEGORY_MISSING_PRIVATE_TEAM
from specify_cli.sync.queue import OfflineQueue
from specify_cli.sync.project_store import ProjectSyncStore


PROJECT = "aaaaaaaa-0000-0000-0000-000000000001"


# ────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────


@pytest.fixture
def temp_queue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[OfflineQueue]:
    """Create a project-owned queue inside its outer unit of work."""
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT)
    authority = store.layout_generation()
    authority.begin_cutover("batch-error-surfacing-tests")
    authority.publish_project_only("batch-error-surfacing-tests", verify_exact=lambda: True)
    with store.unit_of_work() as unit:
        yield OfflineQueue(unit, authority)


@pytest.fixture
def small_queue(temp_queue):
    """Queue with 5 events for smaller tests."""
    for i in range(5):
        temp_queue.queue_event(
            {
                "event_id": f"evt-{i:04d}",
                "event_type": "TestEvent",
                "project_uuid": PROJECT,
                "payload": {"index": i},
            }
        )
    return temp_queue


# ────────────────────────────────────────────────────────────────
# T006: Error categorisation
# ────────────────────────────────────────────────────────────────


class TestCategorizeError:
    """Test the categorize_error function (T006)."""

    def test_known_keywords_map_to_their_category(self):
        """Every live diagnostic keyword maps to its owning category."""
        mismatches = {
            (category, keyword): categorize_error(f"Sync failed: {keyword}")
            for category in (
                "schema_mismatch",
                "auth_expired",
                "server_error",
                "retryable_transport",
            )
            for keyword in ERROR_CATEGORIES[category]
            if categorize_error(f"Sync failed: {keyword}") != category
        }
        assert mismatches == {}

    def test_unknown_for_unrecognised(self):
        """Strings with no matching keywords yield 'unknown'."""
        assert categorize_error("Something completely different happened") == "unknown"

    def test_empty_string_returns_unknown(self):
        assert categorize_error("") == "unknown"

    def test_case_insensitive(self):
        """Matching is case-insensitive."""
        assert categorize_error("SCHEMA violation detected") == "schema_mismatch"
        assert categorize_error("TOKEN EXPIRED at midnight") == "auth_expired"
        assert categorize_error("INTERNAL server meltdown") == "server_error"
        assert categorize_error("REQUEST TIMEOUT at midnight") == "retryable_transport"

    def test_first_match_wins(self):
        """When multiple categories match, first in dict order wins."""
        # "invalid" matches schema_mismatch, "timeout" matches server_error
        # schema_mismatch is first in ERROR_CATEGORIES
        result = categorize_error("invalid timeout detected")
        assert result == "schema_mismatch"


# ────────────────────────────────────────────────────────────────
# T007: Actionable summary
# ────────────────────────────────────────────────────────────────


class TestFormatSyncSummary:
    """Test format_sync_summary (T007)."""

    def test_all_success(self):
        """No failures produces clean summary."""
        result = BatchSyncResult()
        result.synced_count = 42
        result.duplicate_count = 3

        summary = format_sync_summary(result)
        assert "Synced: 42" in summary
        assert "Duplicates: 3" in summary
        assert "Failed: 0" in summary
        # No category breakdown
        assert "schema_mismatch" not in summary

    def test_with_failures(self):
        """Failures produce category breakdown with actions."""
        result = BatchSyncResult()
        result.synced_count = 10
        result.error_count = 5
        result.event_results = [
            BatchEventResult("e1", "rejected", "Invalid schema", "schema_mismatch"),
            BatchEventResult("e2", "rejected", "Invalid schema", "schema_mismatch"),
            BatchEventResult("e3", "rejected", "Invalid schema", "schema_mismatch"),
            BatchEventResult("e4", "rejected", "Token expired", "auth_expired"),
            BatchEventResult("e5", "rejected", "Strange thing", "unknown"),
        ]

        summary = format_sync_summary(result)
        assert "Failed: 5" in summary
        assert "schema_mismatch: 3" in summary
        assert "auth_expired: 1" in summary
        assert "unknown: 1" in summary
        assert "spec-kitty sync diagnose" in summary
        assert "spec-kitty auth login" in summary

    def test_category_actions_present(self):
        """Each known category has an action string."""
        assert "schema_mismatch" in CATEGORY_ACTIONS
        assert "auth_expired" in CATEGORY_ACTIONS
        assert "unauthenticated" in CATEGORY_ACTIONS
        assert CATEGORY_MISSING_PRIVATE_TEAM in CATEGORY_ACTIONS
        assert "retryable_transport" in CATEGORY_ACTIONS
        assert "server_error" in CATEGORY_ACTIONS
        assert "unknown" in CATEGORY_ACTIONS

    def test_pending_segment_when_nonzero(self):
        """``Pending: N`` segment surfaces when pending_count > 0
        (Priivacy-ai/spec-kitty#1182)."""
        result = BatchSyncResult()
        result.synced_count = 5
        result.duplicate_count = 1
        result.pending_count = 3
        result.error_count = 0

        summary = format_sync_summary(result)
        assert "Synced: 5" in summary
        assert "Duplicates: 1" in summary
        assert "Pending: 3" in summary
        assert "Failed: 0" in summary

    def test_no_pending_segment_when_zero(self):
        """``Pending`` segment is omitted when pending_count == 0
        (preserves the historical summary shape for the common case)."""
        result = BatchSyncResult()
        result.synced_count = 5
        result.duplicate_count = 1
        result.error_count = 2

        summary = format_sync_summary(result)
        assert "Pending" not in summary
        assert "Synced: 5" in summary
        assert "Duplicates: 1" in summary
        assert "Failed: 2" in summary


# ────────────────────────────────────────────────────────────────
# T009: Failure report generation
# ────────────────────────────────────────────────────────────────


class TestFailureReport:
    """Test generate_failure_report and write_failure_report (T009)."""

    def test_generate_report_structure(self):
        """Report has required top-level keys."""
        result = BatchSyncResult()
        result.total_events = 10
        result.synced_count = 7
        result.duplicate_count = 1
        result.error_count = 2
        result.event_results = [
            BatchEventResult("e1", "rejected", "Invalid field", "schema_mismatch"),
            BatchEventResult("e2", "rejected", "Timeout occurred", "server_error"),
        ]

        report = generate_failure_report(result)

        assert "generated_at" in report
        assert "summary" in report
        assert "failures" in report

        assert report["summary"]["total_events"] == 10
        assert report["summary"]["synced"] == 7
        assert report["summary"]["duplicates"] == 1
        assert report["summary"]["pending"] == 0
        assert report["summary"]["failed"] == 2
        assert report["summary"]["categories"] == {
            "schema_mismatch": 1,
            "server_error": 1,
        }

        assert len(report["failures"]) == 2
        assert report["failures"][0]["event_id"] == "e1"
        assert report["failures"][0]["error"] == "Invalid field"
        assert report["failures"][0]["category"] == "schema_mismatch"

    def test_generate_report_empty_failures(self):
        """Report with no failures has empty failures list."""
        result = BatchSyncResult()
        result.total_events = 5
        result.synced_count = 5

        report = generate_failure_report(result)
        assert report["failures"] == []

    def test_write_failure_report_creates_file(self, tmp_path):
        """write_failure_report writes valid JSON to disk."""
        result = BatchSyncResult()
        result.total_events = 3
        result.error_count = 1
        result.event_results = [
            BatchEventResult("e1", "rejected", "Schema error", "schema_mismatch"),
        ]

        report_path = tmp_path / "failures.json"
        write_failure_report(report_path, result)

        assert report_path.exists()
        data = json.loads(report_path.read_text())
        assert len(data["failures"]) == 1
        assert data["failures"][0]["event_id"] == "e1"

    def test_write_failure_report_no_failures(self, tmp_path):
        """Report file is still created even with no failures (metadata only)."""
        result = BatchSyncResult()
        result.total_events = 5
        result.synced_count = 5

        report_path = tmp_path / "empty_report.json"
        write_failure_report(report_path, result)

        assert report_path.exists()
        data = json.loads(report_path.read_text())
        assert data["failures"] == []
        assert data["summary"]["synced"] == 5


# ────────────────────────────────────────────────────────────────
# T008: Selective queue removal via process_batch_results
# ────────────────────────────────────────────────────────────────


class TestProcessBatchResults:
    """Test OfflineQueue.process_batch_results (T008)."""

    def test_mixed_results(self, small_queue):
        """Synced/duplicate removed, rejected retained with bumped retry."""
        results = [
            BatchEventResult("evt-0000", "success"),
            BatchEventResult("evt-0001", "duplicate"),
            BatchEventResult("evt-0002", "rejected", "Schema error", "schema_mismatch"),
            BatchEventResult("evt-0003", "success"),
            BatchEventResult("evt-0004", "rejected", "Timeout", "server_error"),
        ]

        small_queue.process_batch_results(results)

        # 3 removed (success + duplicate), 2 remain (rejected)
        assert small_queue.size() == 2

        remaining = small_queue.drain_queue()
        remaining_ids = {task.event_id for task in remaining}
        assert remaining_ids == {"evt-0002", "evt-0004"}

    def test_all_success(self, small_queue):
        """All events synced -> queue empty."""
        results = [BatchEventResult(f"evt-{i:04d}", "success") for i in range(5)]
        small_queue.process_batch_results(results)
        assert small_queue.size() == 0

    def test_all_rejected(self, small_queue):
        """All events rejected -> all stay, retry incremented."""
        results = [BatchEventResult(f"evt-{i:04d}", "rejected", "Error", "unknown") for i in range(5)]
        small_queue.process_batch_results(results)
        assert small_queue.size() == 5

        # Verify retry count was incremented
        events_with_retries = small_queue.get_events_by_retry_count(max_retries=1)
        assert len(events_with_retries) == 5

        events_below_two = small_queue.get_events_by_retry_count(max_retries=2)
        assert len(events_below_two) == 5  # all at retry_count=1, threshold is <2

    def test_empty_results(self, small_queue):
        """Empty results list is a no-op."""
        small_queue.process_batch_results([])
        assert small_queue.size() == 5

    def test_atomicity_on_valid_input(self, small_queue):
        """Both operations (delete + update) happen in one transaction."""
        results = [
            BatchEventResult("evt-0000", "success"),
            BatchEventResult("evt-0001", "rejected", "Error", "unknown"),
        ]

        small_queue.process_batch_results(results)

        # 1 removed, 4 remain
        assert small_queue.size() == 4


# ────────────────────────────────────────────────────────────────
# BatchSyncResult new properties
# ────────────────────────────────────────────────────────────────


class TestBatchSyncResultProperties:
    """Test new properties on BatchSyncResult."""

    def test_failed_results_filters_rejected(self):
        result = BatchSyncResult()
        result.event_results = [
            BatchEventResult("e1", "success"),
            BatchEventResult("e2", "duplicate"),
            BatchEventResult("e3", "rejected", "err", "unknown"),
            BatchEventResult("e4", "rejected", "err2", "schema_mismatch"),
        ]

        failed = result.failed_results
        assert len(failed) == 2
        assert failed[0].event_id == "e3"
        assert failed[1].event_id == "e4"

    def test_category_counts_empty(self):
        result = BatchSyncResult()
        assert result.category_counts == {}

    def test_event_results_list_initialised_empty(self):
        result = BatchSyncResult()
        assert result.event_results == []


# ────────────────────────────────────────────────────────────────
# BatchEventResult dataclass
# ────────────────────────────────────────────────────────────────


class TestBatchEventResult:
    """Test the BatchEventResult dataclass."""

    def test_success_result(self):
        r = BatchEventResult(event_id="e1", status="success")
        assert r.error is None
        assert r.error_category is None

    def test_rejected_result(self):
        r = BatchEventResult(
            event_id="e1",
            status="rejected",
            error="Schema mismatch",
            error_category="schema_mismatch",
        )
        assert r.event_id == "e1"
        assert r.status == "rejected"
        assert r.error == "Schema mismatch"
        assert r.error_category == "schema_mismatch"
