"""Tests for WP02: batch error surfacing and diagnostics.

Covers:
- T004: Per-event result parsing from HTTP 200 responses
- T005: Details field parsing from HTTP 400 responses
- T006: Error categorisation
- T007: Actionable summary formatting
- T008: Selective queue removal via process_batch_results
- T009: --report flag JSON failure dump
- T010: Integration / regression checks
"""
import gzip
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from specify_cli.sync.batch import (
    BatchEventResult,
    BatchSyncResult,
    categorize_error,
    format_sync_summary,
    generate_failure_report,
    write_failure_report,
    batch_sync,
    _parse_event_results,
    _parse_error_response,
    ERROR_CATEGORIES,
    CATEGORY_ACTIONS,
)
from specify_cli.sync.queue import OfflineQueue


# ────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────

@pytest.fixture
def temp_queue():
    """Create a queue with a temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_queue.db"
        queue = OfflineQueue(db_path)
        yield queue


@pytest.fixture
def populated_queue(temp_queue):
    """Queue with 100 test events."""
    for i in range(100):
        temp_queue.queue_event({
            "event_id": f"evt-{i:04d}",
            "event_type": "WPStatusChanged",
            "aggregate_id": f"WP{i % 10:02d}",
            "lamport_clock": i,
            "node_id": "test-node",
            "payload": {"index": i},
        })
    return temp_queue


@pytest.fixture
def small_queue(temp_queue):
    """Queue with 5 events for smaller tests."""
    for i in range(5):
        temp_queue.queue_event({
            "event_id": f"evt-{i:04d}",
            "event_type": "TestEvent",
            "payload": {"index": i},
        })
    return temp_queue


# ────────────────────────────────────────────────────────────────
# T006: Error categorisation
# ────────────────────────────────────────────────────────────────

class TestCategorizeError:
    """Test the categorize_error function (T006)."""

    def test_schema_mismatch_keywords(self):
        """Each schema_mismatch keyword is detected."""
        for kw in ERROR_CATEGORIES["schema_mismatch"]:
            assert categorize_error(f"Event has {kw} problem") == "schema_mismatch"

    def test_auth_expired_keywords(self):
        """Each auth_expired keyword is detected."""
        for kw in ERROR_CATEGORIES["auth_expired"]:
            assert categorize_error(f"Request {kw} error") == "auth_expired"

    def test_server_error_keywords(self):
        """Each server_error keyword is detected."""
        for kw in ERROR_CATEGORIES["server_error"]:
            assert categorize_error(f"Server {kw} issue") == "server_error"

    def test_unknown_for_unrecognised(self):
        """Strings with no matching keywords yield 'unknown'."""
        assert categorize_error("Something completely different happened") == "unknown"

    def test_empty_string_returns_unknown(self):
        assert categorize_error("") == "unknown"

    def test_none_like_returns_unknown(self):
        """None-ish empty string."""
        assert categorize_error("") == "unknown"

    def test_case_insensitive(self):
        """Matching is case-insensitive."""
        assert categorize_error("SCHEMA violation detected") == "schema_mismatch"
        assert categorize_error("TOKEN EXPIRED at midnight") == "auth_expired"
        assert categorize_error("INTERNAL server meltdown") == "server_error"

    def test_first_match_wins(self):
        """When multiple categories match, first in dict order wins."""
        # "invalid" matches schema_mismatch, "timeout" matches server_error
        # schema_mismatch is first in ERROR_CATEGORIES
        result = categorize_error("invalid timeout detected")
        assert result == "schema_mismatch"


# ────────────────────────────────────────────────────────────────
# T004: Per-event result parsing (HTTP 200)
# ────────────────────────────────────────────────────────────────

class TestParseEventResults:
    """Test _parse_event_results helper (T004)."""

    def test_all_success(self):
        """All events returned as success."""
        result = BatchSyncResult()
        raw = [
            {"event_id": "e1", "status": "success"},
            {"event_id": "e2", "status": "success"},
        ]
        _parse_event_results(raw, result)

        assert result.synced_count == 2
        assert result.duplicate_count == 0
        assert result.error_count == 0
        assert len(result.event_results) == 2
        assert all(r.status == "success" for r in result.event_results)

    def test_mixed_results(self):
        """Mix of success, duplicate, and rejected events."""
        result = BatchSyncResult()
        raw = [
            {"event_id": "e1", "status": "success"},
            {"event_id": "e2", "status": "duplicate"},
            {"event_id": "e3", "status": "rejected", "error_message": "Invalid schema"},
            {"event_id": "e4", "status": "error", "error": "Token expired"},
        ]
        _parse_event_results(raw, result)

        assert result.synced_count == 1
        assert result.duplicate_count == 1
        assert result.error_count == 2
        assert result.synced_ids == ["e1", "e2"]
        assert result.failed_ids == ["e3", "e4"]

        # Check categorisation
        rejected = result.failed_results
        assert len(rejected) == 2
        assert rejected[0].error_category == "schema_mismatch"
        assert rejected[1].error_category == "auth_expired"

    def test_terminal_success_like_statuses(self):
        """accepted/warning/skipped are terminal non-error outcomes."""
        result = BatchSyncResult()
        raw = [
            {"event_id": "e1", "status": "accepted"},
            {"event_id": "e2", "status": "warning"},
            {"event_id": "e3", "status": "skipped"},
        ]

        _parse_event_results(raw, result)

        assert result.synced_count == 3
        assert result.duplicate_count == 0
        assert result.error_count == 0
        assert result.synced_ids == ["e1", "e2", "e3"]
        assert [r.status for r in result.event_results] == ["accepted", "warning", "skipped"]
        assert result.failed_results == []

    def test_empty_results_array(self):
        """Empty results array (edge case for empty batch)."""
        result = BatchSyncResult()
        _parse_event_results([], result)

        assert result.synced_count == 0
        assert result.error_count == 0
        assert result.event_results == []

    def test_rejected_with_no_error_message(self):
        """Rejected event without error_message gets 'Unknown error'."""
        result = BatchSyncResult()
        raw = [{"event_id": "e1", "status": "rejected"}]
        _parse_event_results(raw, result)

        assert result.error_count == 1
        rejected = result.failed_results
        assert rejected[0].error == "Unknown error"
        assert rejected[0].error_category == "unknown"

    def test_error_field_fallback(self):
        """'error' field used when 'error_message' is absent."""
        result = BatchSyncResult()
        raw = [{"event_id": "e1", "status": "rejected", "error": "Missing field X"}]
        _parse_event_results(raw, result)

        assert result.failed_results[0].error == "Missing field X"
        assert result.failed_results[0].error_category == "schema_mismatch"


# ────────────────────────────────────────────────────────────────
# T005: HTTP 400 details parsing
# ────────────────────────────────────────────────────────────────

class TestParseErrorResponse:
    """Test _parse_error_response for HTTP 400 bodies (T005)."""

    def test_error_only_no_details(self):
        """400 with only 'error' field, no 'details'."""
        result = BatchSyncResult()
        events = [{"event_id": f"e{i}"} for i in range(3)]
        body = {"error": "Max 1000 events per batch"}

        _parse_error_response(body, events, result)

        assert result.error_count == 3
        assert "Max 1000 events per batch" in result.error_messages[0]
        assert len(result.event_results) == 3

    def test_error_with_plain_text_details(self):
        """400 with 'error' + plain string 'details'."""
        result = BatchSyncResult()
        events = [{"event_id": "e1"}, {"event_id": "e2"}]
        body = {
            "error": "Validation failed",
            "details": "Events contained invalid schemas",
        }

        _parse_error_response(body, events, result)

        assert result.error_count == 2
        assert "Validation failed" in result.error_messages[0]
        assert "Details: Events contained invalid schemas" in result.error_messages[0]

    def test_error_with_structured_json_details_string(self):
        """400 with 'details' as a JSON string containing per-event reasons."""
        result = BatchSyncResult()
        events = [{"event_id": "e1"}, {"event_id": "e2"}, {"event_id": "e3"}]
        per_event = [
            {"event_id": "e1", "error": "Invalid schema for field X"},
            {"event_id": "e2", "reason": "Token expired"},
        ]
        body = {
            "error": "Partial failure",
            "details": json.dumps(per_event),
        }

        _parse_error_response(body, events, result)

        # 2 from details + 1 remaining event
        assert result.error_count == 3
        assert len(result.event_results) == 3

        # First two have per-event details
        assert result.event_results[0].error == "Invalid schema for field X"
        assert result.event_results[0].error_category == "schema_mismatch"
        assert result.event_results[1].error == "Token expired"
        assert result.event_results[1].error_category == "auth_expired"

        # Third falls back to top-level error
        assert result.event_results[2].error == "Partial failure"

    def test_error_with_details_as_list(self):
        """400 with 'details' already a list (not JSON string)."""
        result = BatchSyncResult()
        events = [{"event_id": "e1"}]
        body = {
            "error": "Batch rejected",
            "details": [
                {"event_id": "e1", "error": "Internal server error 500"},
            ],
        }

        _parse_error_response(body, events, result)

        assert result.error_count == 1
        assert result.event_results[0].error_category == "server_error"

    def test_details_invalid_json_treated_as_text(self):
        """Invalid JSON in 'details' treated as plain text."""
        result = BatchSyncResult()
        events = [{"event_id": "e1"}]
        body = {
            "error": "Bad request",
            "details": "not valid {json",
        }

        _parse_error_response(body, events, result)

        assert result.error_count == 1
        assert "Details: not valid {json" in result.error_messages[0]


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
        assert "server_error" in CATEGORY_ACTIONS
        assert "unknown" in CATEGORY_ACTIONS


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
        remaining_ids = {e["event_id"] for e in remaining}
        assert remaining_ids == {"evt-0002", "evt-0004"}

    def test_terminal_success_like_results_removed(self, small_queue):
        """accepted/warning/skipped are terminal and removed from queue."""
        results = [
            BatchEventResult("evt-0000", "accepted"),
            BatchEventResult("evt-0001", "warning"),
            BatchEventResult("evt-0002", "skipped"),
            BatchEventResult("evt-0003", "error", "Server error", "server_error"),
            BatchEventResult("evt-0004", "rejected", "Schema", "schema_mismatch"),
        ]

        small_queue.process_batch_results(results)

        remaining = small_queue.drain_queue()
        remaining_ids = {e["event_id"] for e in remaining}
        assert remaining_ids == {"evt-0003", "evt-0004"}

    def test_all_success(self, small_queue):
        """All events synced -> queue empty."""
        results = [
            BatchEventResult(f"evt-{i:04d}", "success") for i in range(5)
        ]
        small_queue.process_batch_results(results)
        assert small_queue.size() == 0

    def test_all_rejected(self, small_queue):
        """All events rejected -> all stay, retry incremented."""
        results = [
            BatchEventResult(f"evt-{i:04d}", "rejected", "Error", "unknown")
            for i in range(5)
        ]
        small_queue.process_batch_results(results)
        assert small_queue.size() == 5

        # Verify retry count was incremented
        events_with_retries = small_queue.get_events_by_retry_count(max_retries=1)
        assert len(events_with_retries) == 0  # all at retry_count=1, threshold is <1

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
# Integration: batch_sync with per-event results
# ────────────────────────────────────────────────────────────────

class TestBatchSyncEventResults:
    """Integration tests: batch_sync populates event_results."""

    @patch("specify_cli.sync.batch.requests.post")
    def test_http_200_mixed_populates_event_results(self, mock_post, populated_queue):
        """HTTP 200 with mixed statuses populates event_results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"event_id": f"evt-{i:04d}", "status": "success"}
                if i < 90
                else {"event_id": f"evt-{i:04d}", "status": "rejected", "error_message": "Invalid schema"}
                for i in range(100)
            ]
        }
        mock_post.return_value = mock_response

        result = batch_sync(
            queue=populated_queue,
            auth_token="token",
            server_url="http://localhost:8000",
            show_progress=False,
        )

        # Verify event_results populated
        assert len(result.event_results) == 100
        assert result.synced_count == 90
        assert result.error_count == 10

        # Check categorisation applied
        rejected = result.failed_results
        assert len(rejected) == 10
        assert all(r.error_category == "schema_mismatch" for r in rejected)

    @patch("specify_cli.sync.batch.requests.post")
    def test_http_400_with_details(self, mock_post, populated_queue):
        """HTTP 400 with details field surfaces per-event errors."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "Validation failed",
            "details": "Events have invalid format",
        }
        mock_post.return_value = mock_response

        result = batch_sync(
            queue=populated_queue,
            auth_token="token",
            server_url="http://localhost:8000",
            show_progress=False,
        )

        assert result.error_count == 100
        assert len(result.event_results) == 100
        # All should mention the details
        assert "Details: Events have invalid format" in result.error_messages[0]

    @patch("specify_cli.sync.batch.requests.post")
    def test_http_400_with_structured_details(self, mock_post, small_queue):
        """HTTP 400 with JSON details array parses per-event reasons."""
        per_event = [
            {"event_id": "evt-0000", "error": "Missing required field"},
            {"event_id": "evt-0001", "error": "Token expired"},
        ]
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "Partial failure",
            "details": json.dumps(per_event),
        }
        mock_post.return_value = mock_response

        result = batch_sync(
            queue=small_queue,
            auth_token="token",
            server_url="http://localhost:8000",
            show_progress=False,
        )

        # 2 from details + 3 remaining events
        assert result.error_count == 5
        assert len(result.event_results) == 5

        # First two have specific errors
        assert result.event_results[0].error == "Missing required field"
        assert result.event_results[0].error_category == "schema_mismatch"
        assert result.event_results[1].error == "Token expired"
        assert result.event_results[1].error_category == "auth_expired"

    @patch("specify_cli.sync.batch.requests.post")
    def test_http_401_populates_auth_expired_category(self, mock_post, small_queue):
        """HTTP 401 creates event_results with auth_expired category."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        result = batch_sync(
            queue=small_queue,
            auth_token="bad-token",
            server_url="http://localhost:8000",
            show_progress=False,
        )

        assert result.error_count == 5
        assert len(result.event_results) == 5
        assert all(r.error_category == "auth_expired" for r in result.event_results)

    @patch("specify_cli.sync.batch.requests.post")
    def test_http_500_populates_server_error_category(self, mock_post, small_queue):
        """HTTP 500 creates event_results with server_error category."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        result = batch_sync(
            queue=small_queue,
            auth_token="token",
            server_url="http://localhost:8000",
            show_progress=False,
        )

        assert result.error_count == 5
        assert len(result.event_results) == 5
        assert all(r.error_category == "server_error" for r in result.event_results)

    @patch("specify_cli.sync.batch.requests.post")
    def test_timeout_populates_server_error_category(self, mock_post, small_queue):
        """Request timeout creates event_results with server_error category."""
        import requests as req
        mock_post.side_effect = req.exceptions.Timeout()

        result = batch_sync(
            queue=small_queue,
            auth_token="token",
            server_url="http://localhost:8000",
            show_progress=False,
        )

        assert result.error_count == 5
        assert all(r.error_category == "server_error" for r in result.event_results)

    @patch("specify_cli.sync.batch.requests.post")
    def test_connection_error_populates_event_results(self, mock_post, small_queue):
        """Connection error creates event_results with server_error category."""
        import requests as req
        mock_post.side_effect = req.exceptions.ConnectionError("Network unreachable")

        result = batch_sync(
            queue=small_queue,
            auth_token="token",
            server_url="http://localhost:8000",
            show_progress=False,
        )

        assert result.error_count == 5
        assert all(r.error_category == "server_error" for r in result.event_results)

    @patch("specify_cli.sync.batch.requests.post")
    def test_category_counts_property(self, mock_post, small_queue):
        """category_counts aggregates correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"event_id": "evt-0000", "status": "success"},
                {"event_id": "evt-0001", "status": "rejected", "error_message": "Invalid schema"},
                {"event_id": "evt-0002", "status": "rejected", "error_message": "Token expired"},
                {"event_id": "evt-0003", "status": "rejected", "error_message": "Invalid field type"},
                {"event_id": "evt-0004", "status": "duplicate"},
            ]
        }
        mock_post.return_value = mock_response

        result = batch_sync(
            queue=small_queue,
            auth_token="token",
            server_url="http://localhost:8000",
            show_progress=False,
        )

        counts = result.category_counts
        assert counts["schema_mismatch"] == 2
        assert counts["auth_expired"] == 1


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
