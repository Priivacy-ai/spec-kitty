"""Tests for body queue diagnostics and upload result logging."""

from __future__ import annotations

import pytest
import logging
from pathlib import Path
from io import StringIO

from specify_cli.sync.body_queue import BodyQueueStats, OfflineBodyUploadQueue
from specify_cli.sync.diagnose import diagnose_body_queue, print_body_queue_summary
from specify_cli.sync.body_upload import log_upload_outcomes
from specify_cli.sync.namespace import NamespaceRef, UploadOutcome, UploadStatus

pytestmark = pytest.mark.fast

def _ns() -> NamespaceRef:
    return NamespaceRef(
        project_uuid="uuid-1",
        mission_slug="047-feat",
        target_branch="main",
        mission_type="software-dev",
        manifest_version="1",
    )


def _enqueue(queue: OfflineBodyUploadQueue, path: str = "spec.md") -> None:
    queue.enqueue(
        namespace=_ns(),
        artifact_path=path,
        content_hash="abc123",
        content_body="# Spec\n",
        size_bytes=8,
    )


# --- diagnose_body_queue ---


class TestDiagnoseBodyQueue:
    def test_empty_queue(self, tmp_path: Path) -> None:
        queue = OfflineBodyUploadQueue(db_path=tmp_path / "q.db")
        result = diagnose_body_queue(queue)

        assert result["body_queue"]["total_tasks"] == 0
        assert result["body_queue"]["ready_to_send"] == 0
        assert result["body_queue"]["in_backoff"] == 0
        assert result["body_queue"]["max_retry_count"] == 0
        assert result["body_queue"]["oldest_task_age_seconds"] is None
        assert result["body_queue"]["retry_distribution"] == {}
        assert result["body_queue"]["recorded_failure_count"] == 0
        assert result["body_queue"]["recent_failures"] == []

    def test_populated_queue(self, tmp_path: Path) -> None:
        queue = OfflineBodyUploadQueue(db_path=tmp_path / "q.db")
        _enqueue(queue, "spec.md")
        _enqueue(queue, "plan.md")

        result = diagnose_body_queue(queue)

        assert result["body_queue"]["total_tasks"] == 2
        assert result["body_queue"]["ready_to_send"] == 2
        assert result["body_queue"]["in_backoff"] == 0
        assert result["body_queue"]["oldest_task_age_seconds"] is not None
        assert result["body_queue"]["oldest_task_age_seconds"] >= 0

    def test_with_retried_tasks(self, tmp_path: Path) -> None:
        queue = OfflineBodyUploadQueue(db_path=tmp_path / "q.db")
        _enqueue(queue, "spec.md")

        # Mark as failed retryable to increment retry count
        tasks = queue.drain(limit=10)
        queue.mark_failed_retryable(tasks[0].row_id, "connection_error")

        result = diagnose_body_queue(queue)

        assert result["body_queue"]["total_tasks"] == 1
        assert result["body_queue"]["max_retry_count"] == 1
        assert result["body_queue"]["in_backoff"] == 1
        assert 1 in result["body_queue"]["retry_distribution"]

    def test_returns_dict_structure(self, tmp_path: Path) -> None:
        queue = OfflineBodyUploadQueue(db_path=tmp_path / "q.db")
        result = diagnose_body_queue(queue)

        assert "body_queue" in result
        expected_keys = {
            "total_tasks", "ready_to_send", "in_backoff",
            "max_retry_count", "oldest_task_age_seconds",
            "retry_distribution", "recorded_failure_count",
            "recent_failures",
        }
        assert set(result["body_queue"].keys()) == expected_keys

    def test_recent_failures_included(self, tmp_path: Path) -> None:
        queue = OfflineBodyUploadQueue(db_path=tmp_path / "q.db")
        _enqueue(queue, "spec.md")
        task = queue.drain(limit=1)[0]
        queue.record_permanent_failure(task, "bad_request: content_body: This field may not be blank.")
        queue.mark_failed_permanent(task.row_id, "bad_request: content_body: This field may not be blank.")

        result = diagnose_body_queue(queue)

        assert result["body_queue"]["recorded_failure_count"] == 1
        assert len(result["body_queue"]["recent_failures"]) == 1
        assert result["body_queue"]["recent_failures"][0]["artifact_path"] == "spec.md"


# --- print_body_queue_summary ---


class TestPrintBodyQueueSummary:
    def test_empty_queue_output(self) -> None:
        stats = BodyQueueStats(
            total_count=0, ready_count=0, backoff_count=0,
            oldest_created_at=None, newest_created_at=None,
            max_retry_count=0, retry_histogram={},
        )
        # Should not raise
        print_body_queue_summary(stats)

    def test_populated_queue_output(self) -> None:
        stats = BodyQueueStats(
            total_count=5, ready_count=3, backoff_count=2,
            oldest_created_at=1000.0, newest_created_at=2000.0,
            max_retry_count=3, retry_histogram={0: 3, 1: 1, 3: 1},
        )
        # Should not raise
        print_body_queue_summary(stats)

    def test_no_retries_skips_max_line(self, capsys) -> None:
        stats = BodyQueueStats(
            total_count=1, ready_count=1, backoff_count=0,
            oldest_created_at=1000.0, newest_created_at=1000.0,
            max_retry_count=0, retry_histogram={0: 1},
        )
        print_body_queue_summary(stats)
        captured = capsys.readouterr()
        assert "Max retries" not in captured.out


# --- log_upload_outcomes ---


class TestLogUploadOutcomes:
    def test_logs_info_summary(self) -> None:
        log = logging.getLogger("test_log_outcomes")
        log.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(StringIO())
        handler.setLevel(logging.INFO)
        log.addHandler(handler)

        outcomes = [
            UploadOutcome("spec.md", UploadStatus.QUEUED, "enqueued"),
            UploadOutcome("plan.md", UploadStatus.QUEUED, "enqueued"),
            UploadOutcome("image.png", UploadStatus.SKIPPED, "unsupported_format"),
        ]

        log_upload_outcomes(outcomes, "047-feat", log)

        output = handler.stream.getvalue()
        assert "047-feat" in output
        assert "queued=2" in output
        assert "skipped=1" in output

    def test_logs_debug_per_artifact(self) -> None:
        log = logging.getLogger("test_log_debug")
        log.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(StringIO())
        handler.setLevel(logging.DEBUG)
        log.addHandler(handler)

        outcomes = [
            UploadOutcome("spec.md", UploadStatus.UPLOADED, "stored"),
            UploadOutcome("plan.md", UploadStatus.ALREADY_EXISTS, "already_exists"),
        ]

        log_upload_outcomes(outcomes, "047-feat", log)

        output = handler.stream.getvalue()
        assert "spec.md" in output
        assert "plan.md" in output

    def test_empty_outcomes(self) -> None:
        log = logging.getLogger("test_log_empty")
        log.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(StringIO())
        handler.setLevel(logging.INFO)
        log.addHandler(handler)

        log_upload_outcomes([], "047-feat", log)

        output = handler.stream.getvalue()
        assert "047-feat" in output

    def test_all_five_status_types(self) -> None:
        log = logging.getLogger("test_log_all_statuses")
        log.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(StringIO())
        handler.setLevel(logging.INFO)
        log.addHandler(handler)

        outcomes = [
            UploadOutcome("a.md", UploadStatus.UPLOADED, "stored"),
            UploadOutcome("b.md", UploadStatus.ALREADY_EXISTS, "already_exists"),
            UploadOutcome("c.md", UploadStatus.QUEUED, "enqueued"),
            UploadOutcome("d.md", UploadStatus.SKIPPED, "unsupported"),
            UploadOutcome("e.md", UploadStatus.FAILED, "connection_error"),
        ]

        log_upload_outcomes(outcomes, "047-feat", log)

        output = handler.stream.getvalue()
        assert "uploaded=1" in output
        assert "already_exists=1" in output
        assert "queued=1" in output
        assert "skipped=1" in output
        assert "failed=1" in output

    def test_default_logger(self) -> None:
        outcomes = [
            UploadOutcome("spec.md", UploadStatus.QUEUED, "enqueued"),
        ]
        # Should not raise when using default logger
        log_upload_outcomes(outcomes, "047-feat")
