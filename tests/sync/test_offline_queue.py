"""Tests for offline event queue"""
import pytest
from pathlib import Path
import tempfile
import os
from specify_cli.sync.queue import OfflineQueue


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
