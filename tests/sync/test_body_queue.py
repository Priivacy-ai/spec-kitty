"""Project-store acceptance tests for the body upload outbox."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest

from kernel.clock import now_epoch
from specify_cli.sync.body_queue import (
    BodyEnqueueResult,
    BodyQueueStats,
    BodyUploadTask,
    DEFAULT_BODY_QUEUE_SIZE,
    OfflineBodyUploadQueue,
)
from specify_cli.sync.namespace import NamespaceRef
from specify_cli.sync.project_store import ProjectSyncStore, ProjectUnitOfWork
from specify_cli.sync.queue import OfflineQueue

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT = "aaaaaaaa-0000-0000-0000-000000000001"


def _ns(
    project_uuid: str = PROJECT,
    mission_slug: str = "047-feat",
    target_branch: str = "main",
    mission_type: str = "software-dev",
    manifest_version: str = "1",
) -> NamespaceRef:
    return NamespaceRef(
        project_uuid=project_uuid,
        mission_slug=mission_slug,
        target_branch=target_branch,
        mission_type=mission_type,
        manifest_version=manifest_version,
    )


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectSyncStore:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    value = ProjectSyncStore(PROJECT)
    authority = value.layout_generation()
    authority.begin_cutover("body-queue-tests")
    authority.publish_project_only("body-queue-tests", verify_exact=lambda: True)
    return value


@pytest.fixture
def unit(store: ProjectSyncStore) -> Iterator[ProjectUnitOfWork]:
    with store.unit_of_work() as value:
        yield value


@pytest.fixture
def queue(unit: ProjectUnitOfWork, store: ProjectSyncStore) -> OfflineBodyUploadQueue:
    return OfflineBodyUploadQueue(unit, store.layout_generation())


def _reference(unit: ProjectUnitOfWork, row_id: str) -> dict[str, object]:
    row = unit.execute(
        "SELECT body_reference FROM body_upload_tasks WHERE project_uuid = ? AND body_task_id = ?",
        (PROJECT, row_id),
    ).fetchone()
    assert row is not None
    value = json.loads(str(row[0]))
    assert isinstance(value, dict)
    return value


def _update_reference(
    unit: ProjectUnitOfWork,
    row_id: str,
    **changes: object,
) -> None:
    value = _reference(unit, row_id)
    value.update(changes)
    unit.execute(
        "UPDATE body_upload_tasks SET body_reference = ? WHERE project_uuid = ? AND body_task_id = ?",
        (json.dumps(value, sort_keys=True), PROJECT, row_id),
    )


class TestSchema:
    def test_table_created(self, unit: ProjectUnitOfWork) -> None:
        row = unit.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='body_upload_tasks'").fetchone()
        assert row is not None

    def test_indexes_created(self, unit: ProjectUnitOfWork) -> None:
        indexes = list(unit.execute("PRAGMA index_list(body_upload_tasks)"))
        assert sum(bool(row[2]) for row in indexes) >= 1

    def test_schema_idempotent(
        self,
        unit: ProjectUnitOfWork,
        store: ProjectSyncStore,
    ) -> None:
        first = OfflineBodyUploadQueue(unit, store.layout_generation())
        second = OfflineBodyUploadQueue(unit, store.layout_generation())
        assert first.size() == second.size() == 0


class TestSchemaInOfflineQueue:
    def test_body_queue_table_created_by_offline_queue(
        self,
        unit: ProjectUnitOfWork,
        store: ProjectSyncStore,
    ) -> None:
        OfflineQueue(unit, store.layout_generation())
        assert unit.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='body_upload_tasks'").fetchone() is not None


class TestEnqueue:
    def test_new_task_returns_true(self, queue: OfflineBodyUploadQueue) -> None:
        result = queue.enqueue(_ns(), "spec.md", "sha256abc", "# Spec", 6)
        assert result is BodyEnqueueResult.ENQUEUED

    def test_duplicate_returns_false(self, queue: OfflineBodyUploadQueue) -> None:
        queue.enqueue(_ns(), "spec.md", "sha256abc", "# Spec", 6)
        assert queue.enqueue(_ns(), "spec.md", "sha256abc", "# Spec", 6) is BodyEnqueueResult.ALREADY_EXISTS

    def test_different_hash_creates_new_task(self, queue: OfflineBodyUploadQueue) -> None:
        assert queue.enqueue(_ns(), "spec.md", "hash1", "v1", 2) is BodyEnqueueResult.ENQUEUED
        assert queue.enqueue(_ns(), "spec.md", "hash2", "v2", 2) is BodyEnqueueResult.ENQUEUED

    def test_different_namespace_creates_new_task(self, queue: OfflineBodyUploadQueue) -> None:
        assert queue.enqueue(_ns(mission_slug="feat-a"), "spec.md", "hash1", "body", 4) is BodyEnqueueResult.ENQUEUED
        assert queue.enqueue(_ns(mission_slug="feat-b"), "spec.md", "hash1", "body", 4) is BodyEnqueueResult.ENQUEUED

    def test_default_capacity_matches_event_queue_default(
        self,
        queue: OfflineBodyUploadQueue,
    ) -> None:
        assert queue.max_queue_size == DEFAULT_BODY_QUEUE_SIZE

    def test_capacity_limit(
        self,
        unit: ProjectUnitOfWork,
        store: ProjectSyncStore,
    ) -> None:
        queue = OfflineBodyUploadQueue(unit, store.layout_generation(), max_queue_size=2)
        queue.enqueue(_ns(), "a.md", "hash-a", "body", 4)
        queue.enqueue(_ns(), "b.md", "hash-b", "body", 4)
        assert queue.enqueue(_ns(), "extra.md", "new-hash", "body", 4) is BodyEnqueueResult.QUEUE_FULL

    def test_capacity_limit_is_silent(
        self,
        unit: ProjectUnitOfWork,
        store: ProjectSyncStore,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        queue = OfflineBodyUploadQueue(unit, store.layout_generation(), max_queue_size=1)
        queue.enqueue(_ns(), "spec.md", "hash-a", "body", 4)
        with caplog.at_level(logging.WARNING):
            result = queue.enqueue(_ns(), "plan.md", "hash-b", "body", 4)
        assert result is BodyEnqueueResult.QUEUE_FULL
        assert caplog.records == []


class TestDrain:
    def test_returns_fifo_order(self, queue: OfflineBodyUploadQueue) -> None:
        with patch("specify_cli.sync.body_queue.now_epoch") as mock_now_epoch:
            mock_now_epoch.return_value = 100.0
            queue.enqueue(_ns(), "a.md", "h1", "body-a", 6)
            mock_now_epoch.return_value = 200.0
            queue.enqueue(_ns(), "b.md", "h2", "body-b", 6)
            mock_now_epoch.return_value = 300.0
            tasks = queue.drain()
        assert [task.artifact_path for task in tasks] == ["a.md", "b.md"]

    def test_returns_fifo_order_when_timestamps_tie(
        self,
        queue: OfflineBodyUploadQueue,
    ) -> None:
        with patch("specify_cli.sync.body_queue.now_epoch") as mock_now_epoch:
            mock_now_epoch.return_value = 100.0
            queue.enqueue(_ns(), "a.md", "h1", "body-a", 6)
            queue.enqueue(_ns(), "b.md", "h2", "body-b", 6)
            tasks = queue.drain()
        assert [task.artifact_path for task in tasks] == ["a.md", "b.md"]

    def test_respects_backoff(self, queue: OfflineBodyUploadQueue) -> None:
        queue.enqueue(_ns(), "a.md", "h1", "body", 4)
        task = queue.drain()[0]
        queue.mark_failed_retryable(task.row_id, "wait")
        assert queue.drain() == []

    def test_respects_limit(self, queue: OfflineBodyUploadQueue) -> None:
        for index in range(5):
            queue.enqueue(_ns(), f"file{index}.md", f"h{index}", "body", 4)
        assert len(queue.drain(limit=2)) == 2

    def test_returns_body_upload_task(self, queue: OfflineBodyUploadQueue) -> None:
        queue.enqueue(_ns(), "spec.md", "sha256abc", "# Spec", 6)
        task = queue.drain()[0]
        assert isinstance(task, BodyUploadTask)
        assert task.project_uuid == PROJECT
        assert task.mission_slug == "047-feat"
        assert task.target_branch == "main"
        assert task.mission_type == "software-dev"
        assert task.manifest_version == "1"
        assert task.artifact_path == "spec.md"
        assert task.content_hash == "sha256abc"
        assert task.content_body == "# Spec"
        assert task.size_bytes == 6
        assert task.retry_count == 0
        assert task.last_error is None


class TestMarkUploaded:
    def test_removes_from_queue(self, queue: OfflineBodyUploadQueue) -> None:
        queue.enqueue(_ns(), "spec.md", "h1", "body", 4)
        queue.mark_uploaded(queue.drain()[0].row_id)
        assert queue.drain() == []


class TestMarkAlreadyExists:
    def test_removes_from_queue(self, queue: OfflineBodyUploadQueue) -> None:
        queue.enqueue(_ns(), "spec.md", "h1", "body", 4)
        queue.mark_already_exists(queue.drain()[0].row_id)
        assert queue.drain() == []


class TestMarkFailedRetryable:
    def test_increments_retry_count(
        self,
        queue: OfflineBodyUploadQueue,
        unit: ProjectUnitOfWork,
    ) -> None:
        queue.enqueue(_ns(), "spec.md", "h1", "body", 4)
        task = queue.drain()[0]
        queue.mark_failed_retryable(task.row_id, "timeout")
        reference = _reference(unit, task.row_id)
        assert reference["retry_count"] == 1
        assert reference["last_error"] == "timeout"

    def test_sets_future_next_attempt(
        self,
        queue: OfflineBodyUploadQueue,
        unit: ProjectUnitOfWork,
    ) -> None:
        with patch("specify_cli.sync.body_queue.now_epoch") as mock_now_epoch:
            mock_now_epoch.return_value = 100.0
            queue.enqueue(_ns(), "spec.md", "h1", "body", 4)
            task = queue.drain()[0]
            queue.mark_failed_retryable(task.row_id, "err")
            mock_now_epoch.return_value = 100.5
            stats = queue.get_stats()
        reference = _reference(unit, task.row_id)
        assert reference["next_attempt_at"] == 101.0
        assert stats.backoff_count == 1
        assert stats.newest_created_at == 100.0

    def test_task_hidden_during_backoff(self, queue: OfflineBodyUploadQueue) -> None:
        queue.enqueue(_ns(), "spec.md", "h1", "body", 4)
        task = queue.drain()[0]
        queue.mark_failed_retryable(task.row_id, "err")
        assert queue.drain() == []


class TestMarkFailedPermanent:
    def test_removes_from_queue(self, queue: OfflineBodyUploadQueue) -> None:
        queue.enqueue(_ns(), "spec.md", "h1", "body", 4)
        queue.mark_failed_permanent(queue.drain()[0].row_id, "namespace_not_found")
        assert queue.drain() == []
        assert queue.failure_count() == 1


class TestBackoffProgression:
    def test_exponential_backoff_capped_at_300(
        self,
        queue: OfflineBodyUploadQueue,
        unit: ProjectUnitOfWork,
    ) -> None:
        queue.enqueue(_ns(), "spec.md", "h1", "body", 4)
        row_id = queue.drain()[0].row_id
        expected_delays = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0, 300.0]
        for index, expected in enumerate(expected_delays):
            _update_reference(unit, row_id, next_attempt_at=0.0)
            now = now_epoch()
            with patch("specify_cli.sync.body_queue.now_epoch") as mock_now_epoch:
                mock_now_epoch.return_value = now
                queue.mark_failed_retryable(row_id, f"error {index}")
            reference = _reference(unit, row_id)
            next_attempt = reference["next_attempt_at"]
            assert isinstance(next_attempt, (int, float))
            assert abs(float(next_attempt) - now - expected) < 0.01


class TestRemoveStale:
    def test_removes_tasks_beyond_max_retries(
        self,
        queue: OfflineBodyUploadQueue,
        unit: ProjectUnitOfWork,
    ) -> None:
        queue.enqueue(_ns(), "spec.md", "h1", "body", 4)
        row_id = queue.drain()[0].row_id
        _update_reference(unit, row_id, retry_count=25)
        assert queue.remove_stale(max_retry_count=20) == 1

    def test_keeps_tasks_under_max_retries(self, queue: OfflineBodyUploadQueue) -> None:
        queue.enqueue(_ns(), "spec.md", "h1", "body", 4)
        assert queue.remove_stale(max_retry_count=20) == 0


class TestStats:
    def test_empty_queue(self, queue: OfflineBodyUploadQueue) -> None:
        stats = queue.get_stats()
        assert isinstance(stats, BodyQueueStats)
        assert stats == BodyQueueStats(0, 0, 0, None, None, 0, {})

    def test_populated_queue(self, queue: OfflineBodyUploadQueue) -> None:
        queue.enqueue(_ns(), "a.md", "h1", "body-a", 6)
        queue.enqueue(_ns(), "b.md", "h2", "body-b", 6)
        stats = queue.get_stats()
        assert stats.total_count == stats.ready_count == 2
        assert stats.backoff_count == 0
        assert stats.oldest_created_at is not None
        assert stats.newest_created_at is not None

    def test_retry_histogram(
        self,
        queue: OfflineBodyUploadQueue,
        unit: ProjectUnitOfWork,
    ) -> None:
        queue.enqueue(_ns(), "a.md", "h1", "body", 4)
        queue.enqueue(_ns(), "b.md", "h2", "body", 4)
        task = next(task for task in queue.drain() if task.artifact_path == "b.md")
        _update_reference(unit, task.row_id, retry_count=3)
        assert queue.get_stats().retry_histogram == {0: 1, 3: 1}

    def test_backoff_count(self, queue: OfflineBodyUploadQueue) -> None:
        queue.enqueue(_ns(), "a.md", "h1", "body", 4)
        queue.enqueue(_ns(), "b.md", "h2", "body", 4)
        task = next(task for task in queue.drain() if task.artifact_path == "b.md")
        queue.mark_failed_retryable(task.row_id, "wait")
        stats = queue.get_stats()
        assert stats.ready_count == 1
        assert stats.backoff_count == 1


class TestProcessRestart:
    def test_data_persists_across_reopen(self, store: ProjectSyncStore) -> None:
        with store.unit_of_work() as unit:
            OfflineBodyUploadQueue(unit, store.layout_generation()).enqueue(_ns(), "spec.md", "h1", "body", 4)
        with store.unit_of_work() as unit:
            tasks = OfflineBodyUploadQueue(unit, store.layout_generation()).drain()
        assert len(tasks) == 1
        assert tasks[0].artifact_path == "spec.md"
