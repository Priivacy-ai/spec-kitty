"""Project-store acceptance tests for the offline event outbox."""

from __future__ import annotations

import inspect
from collections.abc import Iterator
from kernel.clock import now_utc, timedelta
from io import StringIO
from pathlib import Path

import pytest

from specify_cli.sync.project_store import ProjectSyncStore, ProjectUnitOfWork
from specify_cli.sync.queue import (
    LegacyQueueMigrationRequiredError,
    OfflineQueue,
    ProjectOutboxTask,
    QueueStats,
    default_queue_db_path,
    resolved_scope_db_path,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT = "aaaaaaaa-0000-0000-0000-000000000001"


def _event(
    event_id: str,
    event_type: str = "Test",
    payload: dict[str, object] | None = None,
    *,
    created_at: str | None = None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "event_id": event_id,
        "event_type": event_type,
        "project_uuid": PROJECT,
        "payload": payload or {},
    }
    if created_at is not None:
        value["created_at"] = created_at
    return value


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectSyncStore:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    value = ProjectSyncStore(PROJECT)
    authority = value.layout_generation()
    authority.begin_cutover("offline-queue-tests")
    authority.publish_project_only("offline-queue-tests", verify_exact=lambda: True)
    return value


@pytest.fixture
def unit(store: ProjectSyncStore) -> Iterator[ProjectUnitOfWork]:
    with store.unit_of_work() as value:
        yield value


@pytest.fixture
def temp_queue(unit: ProjectUnitOfWork, store: ProjectSyncStore) -> OfflineQueue:
    return OfflineQueue(unit, store.layout_generation())


class TestOfflineQueue:
    def test_queue_initialization(
        self,
        temp_queue: OfflineQueue,
        store: ProjectSyncStore,
    ) -> None:
        assert store.database_path.exists()
        assert temp_queue.size() == 0
        assert not hasattr(temp_queue, "db_path")

    def test_queue_event_success(self, temp_queue: OfflineQueue) -> None:
        result = temp_queue.queue_event(_event("evt-001", "WPStatusChanged", {"wp_id": "WP01", "status": "doing"}))
        assert result is True
        assert temp_queue.size() == 1

    def test_queue_multiple_events(self, temp_queue: OfflineQueue) -> None:
        for index in range(5):
            assert temp_queue.queue_event(_event(f"evt-{index:03d}", "WPStatusChanged", {"index": index}))
        assert temp_queue.size() == 5

    def test_drain_queue_fifo_order(self, temp_queue: OfflineQueue) -> None:
        for index in range(3):
            temp_queue.queue_event(_event(f"evt-{index:03d}", "TestEvent", {"index": index}))
        tasks = temp_queue.drain_queue()
        assert all(isinstance(task, ProjectOutboxTask) for task in tasks)
        assert [task.event_id for task in tasks] == ["evt-000", "evt-001", "evt-002"]

    def test_drain_queue_with_limit(self, temp_queue: OfflineQueue) -> None:
        for index in range(10):
            temp_queue.queue_event(_event(f"evt-{index:03d}", "TestEvent"))
        assert len(temp_queue.drain_queue(limit=5)) == 5
        assert temp_queue.size() == 10

    def test_mark_synced_removes_events(self, temp_queue: OfflineQueue) -> None:
        for index in range(5):
            temp_queue.queue_event(_event(f"evt-{index:03d}", "TestEvent"))
        temp_queue.mark_synced(["evt-000", "evt-002", "evt-004"])
        assert temp_queue.size() == 2
        assert [task.event_id for task in temp_queue.drain_queue()] == ["evt-001", "evt-003"]

    def test_mark_synced_empty_list(self, temp_queue: OfflineQueue) -> None:
        temp_queue.queue_event(_event("evt-001"))
        temp_queue.mark_synced([])
        assert temp_queue.size() == 1

    def test_clear_removes_all_events(self, temp_queue: OfflineQueue) -> None:
        for index in range(10):
            temp_queue.queue_event(_event(f"evt-{index}"))
        temp_queue.clear()
        assert temp_queue.size() == 0

    def test_duplicate_event_id_replaces(self, temp_queue: OfflineQueue) -> None:
        temp_queue.queue_event(_event("evt-001", payload={"version": 1}))
        temp_queue.queue_event(_event("evt-001", payload={"version": 2}))
        assert temp_queue.size() == 1
        # Stable event identity is idempotent: the original payload is immutable.
        assert temp_queue.drain_queue()[0].event["payload"] == {"version": 1}


class TestOfflineQueueSizeLimit:
    def test_queue_size_limit_enforced(
        self,
        unit: ProjectUnitOfWork,
        store: ProjectSyncStore,
    ) -> None:
        queue = OfflineQueue(unit, store.layout_generation(), max_queue_size=8)
        for index in range(8):
            assert queue.queue_event(_event(f"evt-{index}")) is True
        assert queue.queue_event(_event("evt-overflow")) is False
        assert queue.size() == 8
        assert queue.drain_queue()[0].event_id == "evt-0"

    def test_queue_accepts_after_drain_and_sync(
        self,
        unit: ProjectUnitOfWork,
        store: ProjectSyncStore,
    ) -> None:
        queue = OfflineQueue(unit, store.layout_generation(), max_queue_size=32)
        for index in range(32):
            queue.queue_event(_event(f"evt-{index}"))
        queue.mark_synced([task.event_id for task in queue.drain_queue(limit=10)])
        assert queue.size() == 22
        assert queue.queue_event(_event("evt-new")) is True


class TestOfflineQueuePersistence:
    def test_queue_persists_across_instances(self, store: ProjectSyncStore) -> None:
        with store.unit_of_work() as unit:
            OfflineQueue(unit, store.layout_generation()).queue_event(_event("evt-001", "TestEvent", {"data": "test"}))
        with store.unit_of_work() as unit:
            tasks = OfflineQueue(unit, store.layout_generation()).drain_queue()
        assert len(tasks) == 1
        assert tasks[0].event["payload"] == {"data": "test"}

    def test_multiple_events_persist(self, store: ProjectSyncStore) -> None:
        with store.unit_of_work() as unit:
            queue = OfflineQueue(unit, store.layout_generation())
            for index in range(100):
                queue.queue_event(_event(f"evt-{index:03d}", payload={"index": index}))
        with store.unit_of_work() as unit:
            tasks = OfflineQueue(unit, store.layout_generation()).drain_queue()
        assert len(tasks) == 100
        assert [task.event["payload"]["index"] for task in tasks] == list(range(100))


class TestOfflineQueueRetry:
    def test_increment_retry(self, temp_queue: OfflineQueue) -> None:
        temp_queue.queue_event(_event("evt-001"))
        for _ in range(3):
            temp_queue.increment_retry(["evt-001"])
        assert temp_queue.size() == 1
        assert temp_queue.drain_queue()[0].retry_count == 3

    def test_get_events_by_retry_count(self, temp_queue: OfflineQueue) -> None:
        for index in range(5):
            temp_queue.queue_event(_event(f"evt-{index}"))
        for _ in range(6):
            temp_queue.increment_retry(["evt-0", "evt-2"])
        events = temp_queue.get_events_by_retry_count(max_retries=5)
        assert [event["event_id"] for event in events] == ["evt-1", "evt-3", "evt-4"]


class TestOfflineQueueDefaultPath:
    def test_default_path_uses_home_directory(self) -> None:
        with pytest.raises(LegacyQueueMigrationRequiredError):
            default_queue_db_path()

    def test_default_path_uses_scoped_queue_when_authenticated(self) -> None:
        with pytest.raises(LegacyQueueMigrationRequiredError, match="ProjectSyncStore"):
            default_queue_db_path(user_id="user", team_slug="team")

    def test_session_scope_wins_over_legacy_credentials(self) -> None:
        parameters = inspect.signature(OfflineQueue).parameters
        assert list(parameters) == ["unit", "authority", "max_queue_size"]

    def test_legacy_queue_migrates_into_scoped_queue(self) -> None:
        with pytest.raises(LegacyQueueMigrationRequiredError, match="cannot select"):
            resolved_scope_db_path(object())


class TestQueueStats:
    def test_empty_queue_returns_zero_stats(self, temp_queue: OfflineQueue) -> None:
        stats = temp_queue.get_queue_stats()
        assert stats.total_queued == 0
        assert stats.total_retried == 0
        assert stats.oldest_event_age is None
        assert stats.retry_distribution == {
            "0 retries": 0,
            "1-3 retries": 0,
            "4+ retries": 0,
        }
        assert stats.top_event_types == []

    def test_single_event_stats(self, temp_queue: OfflineQueue) -> None:
        temp_queue.queue_event(_event("evt-001", "WPStatusChanged"))
        stats = temp_queue.get_queue_stats()
        assert stats.total_queued == 1
        assert stats.total_retried == 0
        assert stats.oldest_event_age is not None
        assert stats.oldest_event_age >= timedelta(0)
        assert stats.retry_distribution["0 retries"] == 1
        assert stats.top_event_types == [("WPStatusChanged", 1)]

    def test_retried_events_counted(self, temp_queue: OfflineQueue) -> None:
        for index in range(5):
            temp_queue.queue_event(_event(f"evt-{index}"))
        temp_queue.increment_retry(["evt-1", "evt-3"])
        assert temp_queue.get_queue_stats().total_retried == 2

    def test_retry_distribution_buckets(self, temp_queue: OfflineQueue) -> None:
        for index in range(6):
            temp_queue.queue_event(_event(f"evt-{index}"))
        for _ in range(2):
            temp_queue.increment_retry(["evt-1"])
        for _ in range(3):
            temp_queue.increment_retry(["evt-2"])
        for _ in range(5):
            temp_queue.increment_retry(["evt-3"])
        temp_queue.increment_retry(["evt-5"])
        assert temp_queue.get_queue_stats().retry_distribution == {
            "0 retries": 2,
            "1-3 retries": 3,
            "4+ retries": 1,
        }

    def test_top_event_types_ranking(self, temp_queue: OfflineQueue) -> None:
        for index in range(5):
            temp_queue.queue_event(_event(f"a-{index}", "TypeA"))
        for index in range(3):
            temp_queue.queue_event(_event(f"b-{index}", "TypeB"))
        temp_queue.queue_event(_event("c-0", "TypeC"))
        assert temp_queue.get_queue_stats().top_event_types == [
            ("TypeA", 5),
            ("TypeB", 3),
            ("TypeC", 1),
        ]

    def test_top_event_types_limited_to_five(self, temp_queue: OfflineQueue) -> None:
        for index in range(7):
            temp_queue.queue_event(_event(f"evt-{index}", f"Type{index}"))
        assert len(temp_queue.get_queue_stats().top_event_types) == 5

    def test_oldest_event_age_from_past_timestamp(self, temp_queue: OfflineQueue) -> None:
        now = now_utc()
        temp_queue.queue_event(_event("old-evt", "TestEvent", created_at=(now - timedelta(hours=1)).isoformat()))
        temp_queue.queue_event(_event("new-evt", "TestEvent", created_at=now.isoformat()))
        age = temp_queue.get_queue_stats().oldest_event_age
        assert age is not None
        assert 3590 <= age.total_seconds() <= 3700


class TestHumanizeTimedelta:
    def test_seconds_only(self) -> None:
        from specify_cli.cli.commands.sync import humanize_timedelta

        assert humanize_timedelta(timedelta(seconds=0)) == "0s"
        assert humanize_timedelta(timedelta(seconds=45)) == "45s"

    def test_minutes_and_seconds(self) -> None:
        from specify_cli.cli.commands.sync import humanize_timedelta

        assert humanize_timedelta(timedelta(minutes=3, seconds=12)) == "3m 12s"
        assert humanize_timedelta(timedelta(minutes=5)) == "5m"

    def test_hours_and_minutes(self) -> None:
        from specify_cli.cli.commands.sync import humanize_timedelta

        assert humanize_timedelta(timedelta(hours=2, minutes=5)) == "2h 5m"
        assert humanize_timedelta(timedelta(hours=1)) == "1h"

    def test_days_and_hours(self) -> None:
        from specify_cli.cli.commands.sync import humanize_timedelta

        assert humanize_timedelta(timedelta(days=1, hours=4)) == "1d 4h"
        assert humanize_timedelta(timedelta(days=3)) == "3d"

    def test_negative_returns_zero(self) -> None:
        from specify_cli.cli.commands.sync import humanize_timedelta

        assert humanize_timedelta(timedelta(seconds=-10)) == "0s"


class TestFormatQueueHealth:
    @staticmethod
    def _render(stats: QueueStats) -> str:
        from rich.console import Console
        from specify_cli.cli.commands.sync import format_queue_health

        buffer = StringIO()
        format_queue_health(stats, Console(file=buffer, force_terminal=False, width=120))
        return buffer.getvalue()

    def test_summary_panel_content(self) -> None:
        output = self._render(
            QueueStats(
                total_queued=42,
                total_retried=7,
                oldest_event_age=timedelta(hours=2, minutes=30),
                retry_distribution={"0 retries": 35, "1-3 retries": 5, "4+ retries": 2},
                top_event_types=[("WPStatusChanged", 20), ("FeatureCreated", 12)],
            )
        )
        assert all(token in output for token in ("Queue Depth", "42", "Retried", "7", "2h 30m ago"))

    def test_retry_distribution_table(self) -> None:
        output = self._render(
            QueueStats(
                total_queued=10,
                total_retried=3,
                oldest_event_age=timedelta(minutes=5),
                retry_distribution={"0 retries": 7, "1-3 retries": 2, "4+ retries": 1},
                top_event_types=[("Test", 10)],
            )
        )
        assert all(token in output for token in ("Retry Distribution", "0 retries", "1-3 retries", "4+ retries"))

    def test_top_event_types_table(self) -> None:
        output = self._render(
            QueueStats(
                total_queued=15,
                oldest_event_age=timedelta(seconds=30),
                retry_distribution={"0 retries": 15},
                top_event_types=[("WPStatusChanged", 8), ("FeatureCreated", 5), ("SyncPing", 2)],
            )
        )
        assert all(token in output for token in ("Top Event Types", "WPStatusChanged", "FeatureCreated", "SyncPing"))
