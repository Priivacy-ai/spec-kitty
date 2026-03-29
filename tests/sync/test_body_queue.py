"""Tests for specify_cli.sync.body_queue module."""

from __future__ import annotations

import pytest
import sqlite3
import time
from unittest.mock import patch


from specify_cli.sync.body_queue import (
    BodyQueueStats,
    BodyUploadTask,
    OfflineBodyUploadQueue,
)
from specify_cli.sync.namespace import NamespaceRef

pytestmark = pytest.mark.fast

def _ns(
    project_uuid: str = "uuid-1",
    mission_slug: str = "047-feat",
    target_branch: str = "main",
    mission_key: str = "software-dev",
    manifest_version: str = "1",
) -> NamespaceRef:
    return NamespaceRef(
        project_uuid=project_uuid,
        mission_slug=mission_slug,
        target_branch=target_branch,
        mission_key=mission_key,
        manifest_version=manifest_version,
    )


# --- Schema ---


class TestSchema:
    def test_table_created(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        OfflineBodyUploadQueue(db_path=db)
        conn = sqlite3.connect(db)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='body_upload_queue'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_indexes_created(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        OfflineBodyUploadQueue(db_path=db)
        conn = sqlite3.connect(db)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        index_names = {row[0] for row in cursor}
        assert "idx_body_queue_next_attempt" in index_names
        assert "idx_body_queue_namespace" in index_names
        conn.close()

    def test_schema_idempotent(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        OfflineBodyUploadQueue(db_path=db)
        OfflineBodyUploadQueue(db_path=db)  # Second init should not fail


class TestSchemaInOfflineQueue:
    def test_body_queue_table_created_by_offline_queue(self, tmp_path: object) -> None:
        from pathlib import Path

        from specify_cli.sync.queue import OfflineQueue

        db = Path(str(tmp_path)) / "test.db"
        OfflineQueue(db_path=db)
        conn = sqlite3.connect(db)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='body_upload_queue'")
        assert cursor.fetchone() is not None
        conn.close()


# --- Enqueue ---


class TestEnqueue:
    def test_new_task_returns_true(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        result = q.enqueue(
            namespace=_ns(),
            artifact_path="spec.md",
            content_hash="sha256abc",
            content_body="# Spec",
            size_bytes=6,
        )
        assert result is True

    def test_duplicate_returns_false(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        ns = _ns()
        q.enqueue(ns, "spec.md", "sha256abc", "# Spec", 6)
        result = q.enqueue(ns, "spec.md", "sha256abc", "# Spec", 6)
        assert result is False

    def test_different_hash_creates_new_task(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        ns = _ns()
        assert q.enqueue(ns, "spec.md", "hash1", "v1", 2) is True
        assert q.enqueue(ns, "spec.md", "hash2", "v2", 2) is True

    def test_different_namespace_creates_new_task(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        ns1 = _ns(mission_slug="feat-a")
        ns2 = _ns(mission_slug="feat-b")
        assert q.enqueue(ns1, "spec.md", "hash1", "body", 4) is True
        assert q.enqueue(ns2, "spec.md", "hash1", "body", 4) is True

    def test_capacity_limit(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        # Insert MAX tasks directly
        conn = sqlite3.connect(db)
        for i in range(10_000):
            conn.execute(
                """INSERT INTO body_upload_queue
                   (project_uuid, mission_slug, target_branch, mission_key,
                    manifest_version, artifact_path, content_hash, hash_algorithm,
                    content_body, size_bytes, retry_count, next_attempt_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0.0, ?)""",
                ("u", "f", "b", "m", "v", f"file{i}.md", f"h{i}", "sha256", "x", 1, time.time()),
            )
        conn.commit()
        conn.close()
        result = q.enqueue(_ns(), "extra.md", "new-hash", "body", 4)
        assert result is False


# --- Drain ---


class TestDrain:
    def test_returns_fifo_order(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        with patch("specify_cli.sync.body_queue.time") as mock_time:
            mock_time.time.return_value = 100.0
            q.enqueue(_ns(), "a.md", "h1", "body-a", 6)
            mock_time.time.return_value = 200.0
            q.enqueue(_ns(), "b.md", "h2", "body-b", 6)
            mock_time.time.return_value = 300.0
            tasks = q.drain()
        assert len(tasks) == 2
        assert tasks[0].artifact_path == "a.md"
        assert tasks[1].artifact_path == "b.md"

    def test_respects_backoff(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        q.enqueue(_ns(), "a.md", "h1", "body", 4)
        # Set next_attempt_at far in the future
        conn = sqlite3.connect(db)
        conn.execute("UPDATE body_upload_queue SET next_attempt_at = ?", (time.time() + 9999,))
        conn.commit()
        conn.close()
        tasks = q.drain()
        assert len(tasks) == 0

    def test_respects_limit(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        for i in range(5):
            q.enqueue(_ns(), f"file{i}.md", f"h{i}", "body", 4)
        tasks = q.drain(limit=2)
        assert len(tasks) == 2

    def test_returns_body_upload_task(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        q.enqueue(_ns(), "spec.md", "sha256abc", "# Spec", 6)
        tasks = q.drain()
        assert len(tasks) == 1
        task = tasks[0]
        assert isinstance(task, BodyUploadTask)
        assert task.project_uuid == "uuid-1"
        assert task.mission_slug == "047-feat"
        assert task.target_branch == "main"
        assert task.mission_key == "software-dev"
        assert task.manifest_version == "1"
        assert task.artifact_path == "spec.md"
        assert task.content_hash == "sha256abc"
        assert task.content_body == "# Spec"
        assert task.size_bytes == 6
        assert task.retry_count == 0
        assert task.last_error is None


# --- Lifecycle ---


class TestMarkUploaded:
    def test_removes_from_queue(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        q.enqueue(_ns(), "spec.md", "h1", "body", 4)
        tasks = q.drain()
        q.mark_uploaded(tasks[0].row_id)
        assert len(q.drain()) == 0


class TestMarkAlreadyExists:
    def test_removes_from_queue(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        q.enqueue(_ns(), "spec.md", "h1", "body", 4)
        tasks = q.drain()
        q.mark_already_exists(tasks[0].row_id)
        assert len(q.drain()) == 0


class TestMarkFailedRetryable:
    def test_increments_retry_count(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        q.enqueue(_ns(), "spec.md", "h1", "body", 4)
        tasks = q.drain()
        q.mark_failed_retryable(tasks[0].row_id, "timeout")
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT retry_count, last_error FROM body_upload_queue WHERE id = ?",
            (tasks[0].row_id,),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 1
        assert row[1] == "timeout"

    def test_sets_future_next_attempt(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        q.enqueue(_ns(), "spec.md", "h1", "body", 4)
        tasks = q.drain()
        now = time.time()
        q.mark_failed_retryable(tasks[0].row_id, "err")
        conn = sqlite3.connect(db)
        row = conn.execute("SELECT next_attempt_at FROM body_upload_queue WHERE id = ?", (tasks[0].row_id,)).fetchone()
        conn.close()
        assert row is not None
        assert row[0] > now  # next_attempt_at is in the future

    def test_task_hidden_during_backoff(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        q.enqueue(_ns(), "spec.md", "h1", "body", 4)
        tasks = q.drain()
        q.mark_failed_retryable(tasks[0].row_id, "err")
        # Immediately after failing, task should be in backoff
        assert len(q.drain()) == 0


class TestMarkFailedPermanent:
    def test_removes_from_queue(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        q.enqueue(_ns(), "spec.md", "h1", "body", 4)
        tasks = q.drain()
        q.mark_failed_permanent(tasks[0].row_id, "namespace_not_found")
        assert len(q.drain()) == 0


class TestBackoffProgression:
    def test_exponential_backoff_capped_at_300(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        q.enqueue(_ns(), "spec.md", "h1", "body", 4)

        expected_delays = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0, 300.0]
        for i, expected in enumerate(expected_delays):
            now = time.time()
            # Make task eligible by setting next_attempt_at to past
            conn = sqlite3.connect(db)
            conn.execute("UPDATE body_upload_queue SET next_attempt_at = 0.0")
            conn.commit()
            conn.close()

            tasks = q.drain()
            assert len(tasks) == 1, f"Iteration {i}: expected 1 task, got {len(tasks)}"
            with patch("specify_cli.sync.body_queue.time") as mock_time:
                mock_time.time.return_value = now
                q.mark_failed_retryable(tasks[0].row_id, f"error {i}")

            conn = sqlite3.connect(db)
            row = conn.execute("SELECT next_attempt_at, retry_count FROM body_upload_queue").fetchone()
            conn.close()
            assert row is not None
            actual_delay = row[0] - now
            assert abs(actual_delay - expected) < 0.01, (
                f"Retry {i}: expected delay {expected}s, got {actual_delay:.2f}s"
            )


class TestRemoveStale:
    def test_removes_tasks_beyond_max_retries(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        q.enqueue(_ns(), "spec.md", "h1", "body", 4)
        # Set retry count above threshold
        conn = sqlite3.connect(db)
        conn.execute("UPDATE body_upload_queue SET retry_count = 25")
        conn.commit()
        conn.close()
        removed = q.remove_stale(max_retry_count=20)
        assert removed == 1

    def test_keeps_tasks_under_max_retries(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        q.enqueue(_ns(), "spec.md", "h1", "body", 4)
        removed = q.remove_stale(max_retry_count=20)
        assert removed == 0


# --- Stats ---


class TestStats:
    def test_empty_queue(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        stats = q.get_stats()
        assert isinstance(stats, BodyQueueStats)
        assert stats.total_count == 0
        assert stats.ready_count == 0
        assert stats.backoff_count == 0
        assert stats.oldest_created_at is None
        assert stats.newest_created_at is None
        assert stats.max_retry_count == 0
        assert stats.retry_histogram == {}

    def test_populated_queue(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        q.enqueue(_ns(), "a.md", "h1", "body-a", 6)
        q.enqueue(_ns(), "b.md", "h2", "body-b", 6)
        stats = q.get_stats()
        assert stats.total_count == 2
        assert stats.ready_count == 2
        assert stats.backoff_count == 0
        assert stats.oldest_created_at is not None
        assert stats.newest_created_at is not None
        assert stats.max_retry_count == 0

    def test_retry_histogram(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        q.enqueue(_ns(), "a.md", "h1", "body", 4)
        q.enqueue(_ns(), "b.md", "h2", "body", 4)
        # Set one to retry_count=3
        conn = sqlite3.connect(db)
        conn.execute("UPDATE body_upload_queue SET retry_count = 3 WHERE artifact_path = 'b.md'")
        conn.commit()
        conn.close()
        stats = q.get_stats()
        assert stats.retry_histogram == {0: 1, 3: 1}

    def test_backoff_count(self, tmp_path: object) -> None:
        from pathlib import Path

        db = Path(str(tmp_path)) / "test.db"
        q = OfflineBodyUploadQueue(db_path=db)
        q.enqueue(_ns(), "a.md", "h1", "body", 4)
        q.enqueue(_ns(), "b.md", "h2", "body", 4)
        # Put one in backoff
        conn = sqlite3.connect(db)
        conn.execute(
            "UPDATE body_upload_queue SET next_attempt_at = ? WHERE artifact_path = 'b.md'",
            (time.time() + 9999,),
        )
        conn.commit()
        conn.close()
        stats = q.get_stats()
        assert stats.ready_count == 1
        assert stats.backoff_count == 1


# --- Process restart ---


class TestProcessRestart:
    def test_data_persists_across_reopen(self, tmp_path: object) -> None:
        from pathlib import Path


        db = Path(str(tmp_path)) / "test.db"
        q1 = OfflineBodyUploadQueue(db_path=db)
        q1.enqueue(_ns(), "spec.md", "h1", "body", 4)
        del q1
        q2 = OfflineBodyUploadQueue(db_path=db)
        tasks = q2.drain()
        assert len(tasks) == 1
        assert tasks[0].artifact_path == "spec.md"
