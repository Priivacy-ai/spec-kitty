"""Tests for offline event queue"""
import sqlite3
import pytest
from datetime import timedelta
from io import StringIO
from pathlib import Path
import tempfile
import os
from specify_cli.sync.queue import OfflineQueue, QueueStats


@pytest.fixture
def temp_queue():
    """Create a queue with a temporary database"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / 'test_queue.db'
        queue = OfflineQueue(db_path)
        yield queue


@pytest.fixture
def persistent_db_path():
    """Create a temp path for persistence tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / 'persistent_queue.db'


class TestOfflineQueue:
    """Test OfflineQueue basic operations"""

    def test_queue_initialization(self, temp_queue):
        """Test queue creates database and schema"""
        assert temp_queue.db_path.exists()
        assert temp_queue.size() == 0

    def test_queue_event_success(self, temp_queue):
        """Test queueing a single event"""
        event = {
            'event_id': 'evt-001',
            'event_type': 'WPStatusChanged',
            'payload': {'wp_id': 'WP01', 'status': 'doing'}
        }

        result = temp_queue.queue_event(event)

        assert result is True
        assert temp_queue.size() == 1

    def test_queue_multiple_events(self, temp_queue):
        """Test queueing multiple events"""
        for i in range(5):
            event = {
                'event_id': f'evt-{i:03d}',
                'event_type': 'WPStatusChanged',
                'payload': {'index': i}
            }
            assert temp_queue.queue_event(event) is True

        assert temp_queue.size() == 5

    def test_drain_queue_fifo_order(self, temp_queue):
        """Test drain returns events in FIFO order"""
        for i in range(3):
            event = {
                'event_id': f'evt-{i:03d}',
                'event_type': 'TestEvent',
                'payload': {'index': i}
            }
            temp_queue.queue_event(event)

        events = temp_queue.drain_queue()

        assert len(events) == 3
        assert events[0]['event_id'] == 'evt-000'
        assert events[1]['event_id'] == 'evt-001'
        assert events[2]['event_id'] == 'evt-002'

    def test_drain_queue_with_limit(self, temp_queue):
        """Test drain respects limit parameter"""
        for i in range(10):
            event = {
                'event_id': f'evt-{i:03d}',
                'event_type': 'TestEvent',
                'payload': {}
            }
            temp_queue.queue_event(event)

        events = temp_queue.drain_queue(limit=5)

        assert len(events) == 5
        assert temp_queue.size() == 10  # drain doesn't remove events

    def test_mark_synced_removes_events(self, temp_queue):
        """Test mark_synced removes specified events"""
        for i in range(5):
            event = {
                'event_id': f'evt-{i:03d}',
                'event_type': 'TestEvent',
                'payload': {}
            }
            temp_queue.queue_event(event)

        temp_queue.mark_synced(['evt-000', 'evt-002', 'evt-004'])

        assert temp_queue.size() == 2

        remaining = temp_queue.drain_queue()
        remaining_ids = [e['event_id'] for e in remaining]
        assert remaining_ids == ['evt-001', 'evt-003']

    def test_mark_synced_empty_list(self, temp_queue):
        """Test mark_synced with empty list is safe"""
        temp_queue.queue_event({
            'event_id': 'evt-001',
            'event_type': 'Test',
            'payload': {}
        })

        temp_queue.mark_synced([])

        assert temp_queue.size() == 1

    def test_clear_removes_all_events(self, temp_queue):
        """Test clear removes all events"""
        for i in range(10):
            temp_queue.queue_event({
                'event_id': f'evt-{i}',
                'event_type': 'Test',
                'payload': {}
            })

        temp_queue.clear()

        assert temp_queue.size() == 0

    def test_duplicate_event_id_replaces(self, temp_queue):
        """Test queueing same event_id replaces existing"""
        event1 = {
            'event_id': 'evt-001',
            'event_type': 'Test',
            'payload': {'version': 1}
        }
        event2 = {
            'event_id': 'evt-001',
            'event_type': 'Test',
            'payload': {'version': 2}
        }

        temp_queue.queue_event(event1)
        temp_queue.queue_event(event2)

        assert temp_queue.size() == 1
        events = temp_queue.drain_queue()
        assert events[0]['payload']['version'] == 2


class TestOfflineQueueSizeLimit:
    """Test queue size limit enforcement"""

    def test_queue_size_limit_enforced(self, temp_queue):
        """Test queue rejects events when at capacity"""
        # Queue up to the limit
        for i in range(OfflineQueue.MAX_QUEUE_SIZE):
            event = {
                'event_id': f'evt-{i}',
                'event_type': 'Test',
                'payload': {}
            }
            result = temp_queue.queue_event(event)
            if i < OfflineQueue.MAX_QUEUE_SIZE:
                assert result is True

        assert temp_queue.size() == OfflineQueue.MAX_QUEUE_SIZE

        # One more should fail
        overflow_event = {
            'event_id': 'evt-overflow',
            'event_type': 'Test',
            'payload': {}
        }
        result = temp_queue.queue_event(overflow_event)
        assert result is False
        assert temp_queue.size() == OfflineQueue.MAX_QUEUE_SIZE

    def test_queue_accepts_after_drain_and_sync(self, temp_queue):
        """Test queue accepts events after making room"""
        # Fill to limit
        for i in range(OfflineQueue.MAX_QUEUE_SIZE):
            temp_queue.queue_event({
                'event_id': f'evt-{i}',
                'event_type': 'Test',
                'payload': {}
            })

        # Remove some events
        events = temp_queue.drain_queue(limit=100)
        event_ids = [e['event_id'] for e in events]
        temp_queue.mark_synced(event_ids)

        assert temp_queue.size() == OfflineQueue.MAX_QUEUE_SIZE - 100

        # Should accept new events now
        result = temp_queue.queue_event({
            'event_id': 'evt-new',
            'event_type': 'Test',
            'payload': {}
        })
        assert result is True


class TestOfflineQueuePersistence:
    """Test queue persistence across restarts"""

    def test_queue_persists_across_instances(self, persistent_db_path):
        """Test queue data persists when creating new instance"""
        # Create queue and add event
        queue1 = OfflineQueue(persistent_db_path)
        queue1.queue_event({
            'event_id': 'evt-001',
            'event_type': 'TestEvent',
            'payload': {'data': 'test'}
        })
        del queue1

        # Create new instance pointing to same database
        queue2 = OfflineQueue(persistent_db_path)

        assert queue2.size() == 1
        events = queue2.drain_queue()
        assert len(events) == 1
        assert events[0]['event_id'] == 'evt-001'
        assert events[0]['payload']['data'] == 'test'

    def test_multiple_events_persist(self, persistent_db_path):
        """Test multiple events persist across restarts"""
        queue1 = OfflineQueue(persistent_db_path)
        for i in range(100):
            queue1.queue_event({
                'event_id': f'evt-{i:03d}',
                'event_type': 'Test',
                'payload': {'index': i}
            })
        del queue1

        queue2 = OfflineQueue(persistent_db_path)
        assert queue2.size() == 100

        events = queue2.drain_queue()
        assert len(events) == 100
        # Verify order preserved
        for i, event in enumerate(events):
            assert event['payload']['index'] == i


class TestOfflineQueueRetry:
    """Test retry count functionality"""

    def test_increment_retry(self, temp_queue):
        """Test incrementing retry count"""
        temp_queue.queue_event({
            'event_id': 'evt-001',
            'event_type': 'Test',
            'payload': {}
        })

        temp_queue.increment_retry(['evt-001'])
        temp_queue.increment_retry(['evt-001'])
        temp_queue.increment_retry(['evt-001'])

        # Events should still be in queue
        assert temp_queue.size() == 1

    def test_get_events_by_retry_count(self, temp_queue):
        """Test filtering events by retry count"""
        for i in range(5):
            temp_queue.queue_event({
                'event_id': f'evt-{i}',
                'event_type': 'Test',
                'payload': {}
            })

        # Increment some events past threshold
        temp_queue.increment_retry(['evt-0', 'evt-2'])
        temp_queue.increment_retry(['evt-0', 'evt-2'])
        temp_queue.increment_retry(['evt-0', 'evt-2'])
        temp_queue.increment_retry(['evt-0', 'evt-2'])
        temp_queue.increment_retry(['evt-0', 'evt-2'])
        temp_queue.increment_retry(['evt-0', 'evt-2'])  # Now at 6

        events = temp_queue.get_events_by_retry_count(max_retries=5)
        event_ids = [e['event_id'] for e in events]

        assert len(events) == 3
        assert 'evt-0' not in event_ids
        assert 'evt-2' not in event_ids
        assert 'evt-1' in event_ids
        assert 'evt-3' in event_ids
        assert 'evt-4' in event_ids


class TestOfflineQueueDefaultPath:
    """Test default path behavior"""

    def test_default_path_uses_home_directory(self):
        """Test that default path is ~/.spec-kitty/queue.db"""
        # Don't actually create file, just check path logic
        queue = OfflineQueue.__new__(OfflineQueue)
        queue.db_path = None

        expected_path = Path.home() / '.spec-kitty' / 'queue.db'

        # Verify the default path logic (without fully initializing)
        with tempfile.TemporaryDirectory() as tmpdir:
            test_queue = OfflineQueue(Path(tmpdir) / 'test.db')
            # The real default path check
            default_queue = OfflineQueue()
            assert default_queue.db_path == expected_path
            # Clean up
            if default_queue.db_path.exists():
                default_queue.clear()


class TestQueueStats:
    """Tests for get_queue_stats() aggregate queries (T020, T021, T024)."""

    def test_empty_queue_returns_zero_stats(self, temp_queue):
        """Empty queue should return all-zero QueueStats."""
        stats = temp_queue.get_queue_stats()

        assert stats.total_queued == 0
        assert stats.total_retried == 0
        assert stats.oldest_event_age is None
        assert stats.retry_distribution == {}
        assert stats.top_event_types == []

    def test_single_event_stats(self, temp_queue):
        """Queue with one event should report correct totals."""
        temp_queue.queue_event({
            'event_id': 'evt-001',
            'event_type': 'WPStatusChanged',
            'payload': {}
        })

        stats = temp_queue.get_queue_stats()

        assert stats.total_queued == 1
        assert stats.total_retried == 0
        assert stats.oldest_event_age is not None
        assert stats.oldest_event_age >= timedelta(seconds=0)
        assert stats.retry_distribution == {'0 retries': 1}
        assert stats.top_event_types == [('WPStatusChanged', 1)]

    def test_retried_events_counted(self, temp_queue):
        """Events with retry_count > 0 should be counted in total_retried."""
        for i in range(5):
            temp_queue.queue_event({
                'event_id': f'evt-{i}',
                'event_type': 'Test',
                'payload': {}
            })

        # Retry two events
        temp_queue.increment_retry(['evt-1', 'evt-3'])

        stats = temp_queue.get_queue_stats()

        assert stats.total_queued == 5
        assert stats.total_retried == 2

    def test_retry_distribution_buckets(self, temp_queue):
        """Retry distribution should bucket events as 0, 1-3, 4+."""
        # Create 6 events
        for i in range(6):
            temp_queue.queue_event({
                'event_id': f'evt-{i}',
                'event_type': 'Test',
                'payload': {}
            })

        # evt-0: 0 retries (stays in '0 retries')
        # evt-1: 2 retries (goes to '1-3 retries')
        temp_queue.increment_retry(['evt-1'])
        temp_queue.increment_retry(['evt-1'])
        # evt-2: 3 retries (goes to '1-3 retries')
        temp_queue.increment_retry(['evt-2'])
        temp_queue.increment_retry(['evt-2'])
        temp_queue.increment_retry(['evt-2'])
        # evt-3: 5 retries (goes to '4+ retries')
        for _ in range(5):
            temp_queue.increment_retry(['evt-3'])
        # evt-4: 0 retries
        # evt-5: 1 retry (goes to '1-3 retries')
        temp_queue.increment_retry(['evt-5'])

        stats = temp_queue.get_queue_stats()

        assert stats.retry_distribution['0 retries'] == 2    # evt-0, evt-4
        assert stats.retry_distribution['1-3 retries'] == 3   # evt-1, evt-2, evt-5
        assert stats.retry_distribution['4+ retries'] == 1    # evt-3

    def test_top_event_types_ranking(self, temp_queue):
        """Top event types should be ordered by count descending."""
        # 5 of type A, 3 of type B, 1 of type C
        for i in range(5):
            temp_queue.queue_event({
                'event_id': f'a-{i}',
                'event_type': 'TypeA',
                'payload': {}
            })
        for i in range(3):
            temp_queue.queue_event({
                'event_id': f'b-{i}',
                'event_type': 'TypeB',
                'payload': {}
            })
        temp_queue.queue_event({
            'event_id': 'c-0',
            'event_type': 'TypeC',
            'payload': {}
        })

        stats = temp_queue.get_queue_stats()

        assert len(stats.top_event_types) == 3
        assert stats.top_event_types[0] == ('TypeA', 5)
        assert stats.top_event_types[1] == ('TypeB', 3)
        assert stats.top_event_types[2] == ('TypeC', 1)

    def test_top_event_types_limited_to_five(self, temp_queue):
        """Top event types should return at most 5 entries."""
        for i in range(7):
            temp_queue.queue_event({
                'event_id': f'evt-{i}',
                'event_type': f'Type{i}',
                'payload': {}
            })

        stats = temp_queue.get_queue_stats()

        assert len(stats.top_event_types) <= 5

    def test_oldest_event_age_from_past_timestamp(self, temp_queue):
        """Oldest event age should reflect actual timestamp, not insertion order."""
        # Insert events with specific timestamps using raw SQL
        conn = sqlite3.connect(temp_queue.db_path)
        import json
        import time
        now = int(time.time())
        # Insert an event 3600 seconds (1 hour) ago
        old_ts = now - 3600
        conn.execute(
            'INSERT INTO queue (event_id, event_type, data, timestamp) VALUES (?, ?, ?, ?)',
            ('old-evt', 'TestEvent', json.dumps({'event_id': 'old-evt', 'event_type': 'TestEvent'}), old_ts)
        )
        # Insert a recent event
        conn.execute(
            'INSERT INTO queue (event_id, event_type, data, timestamp) VALUES (?, ?, ?, ?)',
            ('new-evt', 'TestEvent', json.dumps({'event_id': 'new-evt', 'event_type': 'TestEvent'}), now)
        )
        conn.commit()
        conn.close()

        stats = temp_queue.get_queue_stats()

        assert stats.total_queued == 2
        assert stats.oldest_event_age is not None
        # Should be approximately 1 hour (allow some slack)
        age_seconds = stats.oldest_event_age.total_seconds()
        assert 3590 <= age_seconds <= 3700, f"Expected ~3600s, got {age_seconds}s"


class TestHumanizeTimedelta:
    """Tests for humanize_timedelta() formatting helper (T022)."""

    def test_seconds_only(self):
        from specify_cli.cli.commands.sync import humanize_timedelta
        assert humanize_timedelta(timedelta(seconds=0)) == "0s"
        assert humanize_timedelta(timedelta(seconds=45)) == "45s"

    def test_minutes_and_seconds(self):
        from specify_cli.cli.commands.sync import humanize_timedelta
        assert humanize_timedelta(timedelta(minutes=3, seconds=12)) == "3m 12s"
        assert humanize_timedelta(timedelta(minutes=5)) == "5m"

    def test_hours_and_minutes(self):
        from specify_cli.cli.commands.sync import humanize_timedelta
        assert humanize_timedelta(timedelta(hours=2, minutes=5)) == "2h 5m"
        assert humanize_timedelta(timedelta(hours=1)) == "1h"

    def test_days_and_hours(self):
        from specify_cli.cli.commands.sync import humanize_timedelta
        assert humanize_timedelta(timedelta(days=1, hours=4)) == "1d 4h"
        assert humanize_timedelta(timedelta(days=3)) == "3d"

    def test_negative_returns_zero(self):
        from specify_cli.cli.commands.sync import humanize_timedelta
        assert humanize_timedelta(timedelta(seconds=-10)) == "0s"


class TestFormatQueueHealth:
    """Tests for format_queue_health() Rich output (T022)."""

    def test_summary_panel_content(self):
        """Verify summary panel includes queue depth and retried count."""
        from rich.console import Console
        from specify_cli.cli.commands.sync import format_queue_health

        stats = QueueStats(
            total_queued=42,
            total_retried=7,
            oldest_event_age=timedelta(hours=2, minutes=30),
            retry_distribution={'0 retries': 35, '1-3 retries': 5, '4+ retries': 2},
            top_event_types=[('WPStatusChanged', 20), ('FeatureCreated', 12)],
        )

        buf = StringIO()
        test_console = Console(file=buf, force_terminal=False, width=120)
        format_queue_health(stats, test_console)
        output = buf.getvalue()

        # Check semantic content (not exact ANSI formatting)
        assert "Queue Depth" in output
        assert "42" in output
        assert "Retried" in output
        assert "7" in output
        assert "2h 30m ago" in output

    def test_retry_distribution_table(self):
        """Verify retry distribution table rows appear."""
        from rich.console import Console
        from specify_cli.cli.commands.sync import format_queue_health

        stats = QueueStats(
            total_queued=10,
            total_retried=3,
            oldest_event_age=timedelta(minutes=5),
            retry_distribution={'0 retries': 7, '1-3 retries': 2, '4+ retries': 1},
            top_event_types=[('Test', 10)],
        )

        buf = StringIO()
        test_console = Console(file=buf, force_terminal=False, width=120)
        format_queue_health(stats, test_console)
        output = buf.getvalue()

        assert "Retry Distribution" in output
        assert "0 retries" in output
        assert "1-3 retries" in output
        assert "4+ retries" in output

    def test_top_event_types_table(self):
        """Verify top event types table includes event type names."""
        from rich.console import Console
        from specify_cli.cli.commands.sync import format_queue_health

        stats = QueueStats(
            total_queued=15,
            total_retried=0,
            oldest_event_age=timedelta(seconds=30),
            retry_distribution={'0 retries': 15},
            top_event_types=[('WPStatusChanged', 8), ('FeatureCreated', 5), ('SyncPing', 2)],
        )

        buf = StringIO()
        test_console = Console(file=buf, force_terminal=False, width=120)
        format_queue_health(stats, test_console)
        output = buf.getvalue()

        assert "Top Event Types" in output
        assert "WPStatusChanged" in output
        assert "FeatureCreated" in output
        assert "SyncPing" in output
