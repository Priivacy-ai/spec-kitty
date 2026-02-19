"""End-to-end integration tests for offline queue replay workflow.

Tests the complete offline workflow:
1. Queue events while offline
2. Reconnection triggers batch sync
3. Batch sync performance (<30s for 1000 events)
4. Idempotency (duplicate event_ids)
5. Queue size limits
6. 100% event recovery
"""
import gzip
import json
import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile

from specify_cli.sync.queue import OfflineQueue
from specify_cli.sync.batch import batch_sync, sync_all_queued_events


@pytest.fixture
def temp_queue():
    """Create a queue with a temporary database"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / 'test_queue.db'
        queue = OfflineQueue(db_path)
        yield queue


def create_test_event(index: int, node_id: str = 'test-node') -> dict:
    """Create a test event with all required fields"""
    return {
        'event_id': f'evt-{index:06d}',
        'event_type': 'WPStatusChanged',
        'aggregate_id': f'WP{index % 100:02d}',
        'aggregate_type': 'WorkPackage',
        'lamport_clock': index,
        'node_id': node_id,
        'causation_id': f'evt-{index-1:06d}' if index > 0 else None,
        'payload': {
            'wp_id': f'WP{index % 100:02d}',
            'from_lane': 'planned',
            'to_lane': 'in_progress',
            'index': index
        }
    }


class TestQueueEventsOffline:
    """Test T129: Queue 100 events offline"""

    def test_queue_100_events_offline(self, temp_queue):
        """Queue 100 events while offline and verify queue state"""
        # Queue 100 events
        for i in range(100):
            event = create_test_event(i)
            result = temp_queue.queue_event(event)
            assert result is True, f"Failed to queue event {i}"

        # Verify queue size
        assert temp_queue.size() == 100

        # Verify FIFO ordering preserved
        events = temp_queue.drain_queue(limit=100)
        assert len(events) == 100
        for i, event in enumerate(events):
            assert event['event_id'] == f'evt-{i:06d}'
            assert event['payload']['index'] == i

    def test_queue_events_with_complex_payloads(self, temp_queue):
        """Queue events with complex nested payloads"""
        for i in range(50):
            event = {
                'event_id': f'complex-{i}',
                'event_type': 'ComplexEvent',
                'aggregate_id': 'WP01',
                'lamport_clock': i,
                'node_id': 'test',
                'payload': {
                    'nested': {
                        'deep': {
                            'value': i,
                            'list': [1, 2, 3],
                            'string': f'data-{i}'
                        }
                    },
                    'tags': ['tag1', 'tag2', 'tag3'],
                    'metadata': {'key': 'value'}
                }
            }
            temp_queue.queue_event(event)

        assert temp_queue.size() == 50

        # Verify complex payload preserved
        events = temp_queue.drain_queue()
        assert events[25]['payload']['nested']['deep']['value'] == 25


class TestReconnectionTriggersBatchSync:
    """Test T130: Reconnection triggers batch sync"""

    @patch('specify_cli.sync.batch.requests.post')
    def test_reconnection_triggers_batch_sync(self, mock_post, temp_queue):
        """Simulate disconnect, queue events, reconnect, verify batch sync"""
        # Phase 1: Simulate offline - queue events
        for i in range(50):
            temp_queue.queue_event(create_test_event(i))

        assert temp_queue.size() == 50

        # Phase 2: Simulate reconnection - batch sync
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'event_id': f'evt-{i:06d}', 'status': 'success'}
                for i in range(50)
            ]
        }
        mock_post.return_value = mock_response

        # This would be called by reconnection handler
        result = batch_sync(
            queue=temp_queue,
            auth_token='reconnect-token',
            server_url='http://localhost:8000',
            show_progress=False
        )

        # Verify batch sync was triggered and succeeded
        assert result.total_events == 50
        assert result.synced_count == 50
        assert temp_queue.size() == 0  # Queue emptied after sync

    @patch('specify_cli.sync.batch.requests.post')
    def test_multiple_reconnection_cycles(self, mock_post, temp_queue):
        """Test multiple offline/online cycles"""
        def mock_batch_response(*args, **kwargs):
            compressed = kwargs['data']
            decompressed = gzip.decompress(compressed)
            payload = json.loads(decompressed)
            events = payload['events']

            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                'results': [
                    {'event_id': e['event_id'], 'status': 'success'}
                    for e in events
                ]
            }
            return mock_resp

        mock_post.side_effect = mock_batch_response

        total_synced = 0

        # Cycle 1: Queue 30, sync
        for i in range(30):
            temp_queue.queue_event(create_test_event(i, node_id='cycle1'))
        result = batch_sync(temp_queue, 'token', 'http://localhost:8000', show_progress=False)
        total_synced += result.synced_count
        assert temp_queue.size() == 0

        # Cycle 2: Queue 50, sync
        for i in range(50):
            temp_queue.queue_event(create_test_event(100 + i, node_id='cycle2'))
        result = batch_sync(temp_queue, 'token', 'http://localhost:8000', show_progress=False)
        total_synced += result.synced_count
        assert temp_queue.size() == 0

        # Cycle 3: Queue 20, sync
        for i in range(20):
            temp_queue.queue_event(create_test_event(200 + i, node_id='cycle3'))
        result = batch_sync(temp_queue, 'token', 'http://localhost:8000', show_progress=False)
        total_synced += result.synced_count
        assert temp_queue.size() == 0

        assert total_synced == 100


class TestBatchSyncThroughput:
    """Test T131: Batch sync <30s for 1000 events"""

    @patch('specify_cli.sync.batch.requests.post')
    def test_batch_sync_throughput_1000_events(self, mock_post, temp_queue):
        """1000 events should sync in <30s (mocked network)"""
        # Queue 1000 events
        for i in range(1000):
            temp_queue.queue_event(create_test_event(i))

        assert temp_queue.size() == 1000

        # Mock successful response for all events
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'event_id': f'evt-{i:06d}', 'status': 'success'}
                for i in range(1000)
            ]
        }
        mock_post.return_value = mock_response

        # Measure sync time
        start = time.time()
        result = batch_sync(
            queue=temp_queue,
            auth_token='token',
            server_url='http://localhost:8000',
            limit=1000,
            show_progress=False
        )
        duration = time.time() - start

        # Verify throughput
        assert result.total_events == 1000
        assert result.synced_count == 1000
        assert temp_queue.size() == 0
        assert duration < 30, f"Batch sync took {duration:.2f}s, expected <30s"

        # Verify gzip compression was used
        call_args = mock_post.call_args
        headers = call_args.kwargs['headers']
        assert headers['Content-Encoding'] == 'gzip'

    @patch('specify_cli.sync.batch.requests.post')
    def test_batch_sync_throughput_multiple_batches(self, mock_post, temp_queue):
        """Sync 2500 events in multiple batches <30s"""
        # Queue 2500 events
        for i in range(2500):
            temp_queue.queue_event(create_test_event(i))

        def mock_batch_response(*args, **kwargs):
            compressed = kwargs['data']
            decompressed = gzip.decompress(compressed)
            payload = json.loads(decompressed)
            events = payload['events']

            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                'results': [
                    {'event_id': e['event_id'], 'status': 'success'}
                    for e in events
                ]
            }
            return mock_resp

        mock_post.side_effect = mock_batch_response

        start = time.time()
        result = sync_all_queued_events(
            queue=temp_queue,
            auth_token='token',
            server_url='http://localhost:8000',
            batch_size=1000,
            show_progress=False
        )
        duration = time.time() - start

        assert result.total_events == 2500
        assert result.synced_count == 2500
        assert temp_queue.size() == 0
        assert duration < 30, f"Multi-batch sync took {duration:.2f}s, expected <30s"
        assert mock_post.call_count == 3  # 1000 + 1000 + 500


class TestIdempotency:
    """Test T132: Idempotency via event_id"""

    @patch('specify_cli.sync.batch.requests.post')
    def test_idempotency_duplicate_events(self, mock_post, temp_queue):
        """Send same event_id twice, second should return 'duplicate'"""
        # Queue unique events
        for i in range(10):
            temp_queue.queue_event(create_test_event(i))

        # First sync - all success
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            'results': [
                {'event_id': f'evt-{i:06d}', 'status': 'success'}
                for i in range(10)
            ]
        }
        mock_post.return_value = mock_response1

        result1 = batch_sync(temp_queue, 'token', 'http://localhost:8000', show_progress=False)
        assert result1.synced_count == 10
        assert result1.duplicate_count == 0

        # Queue same events again (simulating retry scenario)
        for i in range(10):
            temp_queue.queue_event(create_test_event(i))

        # Second sync - all duplicates
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            'results': [
                {'event_id': f'evt-{i:06d}', 'status': 'duplicate'}
                for i in range(10)
            ]
        }
        mock_post.return_value = mock_response2

        result2 = batch_sync(temp_queue, 'token', 'http://localhost:8000', show_progress=False)
        assert result2.synced_count == 0
        assert result2.duplicate_count == 10
        assert result2.success_count == 10  # Duplicates count as success
        assert temp_queue.size() == 0  # Duplicates removed from queue

    @patch('specify_cli.sync.batch.requests.post')
    def test_idempotency_mixed_results(self, mock_post, temp_queue):
        """Mixed new and duplicate events in same batch"""
        # Queue 20 events
        for i in range(20):
            temp_queue.queue_event(create_test_event(i))

        # Mock: first 10 are duplicates, next 10 are new
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'event_id': f'evt-{i:06d}', 'status': 'duplicate' if i < 10 else 'success'}
                for i in range(20)
            ]
        }
        mock_post.return_value = mock_response

        result = batch_sync(temp_queue, 'token', 'http://localhost:8000', show_progress=False)

        assert result.synced_count == 10
        assert result.duplicate_count == 10
        assert result.success_count == 20
        assert temp_queue.size() == 0


class TestQueueSizeLimit:
    """Test T133: Queue size limit warning"""

    def test_queue_size_limit_enforced(self, temp_queue):
        """Queue should reject events at MAX_QUEUE_SIZE (10,000)"""
        # Fill queue to limit
        for i in range(OfflineQueue.MAX_QUEUE_SIZE):
            result = temp_queue.queue_event({
                'event_id': f'evt-{i}',
                'event_type': 'Test',
                'payload': {}
            })
            assert result is True

        assert temp_queue.size() == OfflineQueue.MAX_QUEUE_SIZE

        # 10,001st event should fail
        result = temp_queue.queue_event({
            'event_id': 'evt-overflow',
            'event_type': 'Test',
            'payload': {}
        })
        assert result is False
        assert temp_queue.size() == OfflineQueue.MAX_QUEUE_SIZE

    def test_queue_accepts_after_sync(self, temp_queue):
        """Queue accepts new events after sync makes room"""
        # Fill to limit
        for i in range(OfflineQueue.MAX_QUEUE_SIZE):
            temp_queue.queue_event({
                'event_id': f'evt-{i}',
                'event_type': 'Test',
                'payload': {}
            })

        # Drain some events (simulating sync)
        events = temp_queue.drain_queue(limit=1000)
        temp_queue.mark_synced([e['event_id'] for e in events])

        assert temp_queue.size() == OfflineQueue.MAX_QUEUE_SIZE - 1000

        # Should accept new events now
        result = temp_queue.queue_event({
            'event_id': 'evt-new',
            'event_type': 'Test',
            'payload': {}
        })
        assert result is True


class TestEventRecovery:
    """Test T134-T136: 100% event recovery"""

    @patch('specify_cli.sync.batch.requests.post')
    def test_100_percent_event_recovery(self, mock_post, temp_queue):
        """Queue 500 events, verify all 500 recovered after sync"""
        # Queue 500 events
        for i in range(500):
            temp_queue.queue_event(create_test_event(i, node_id='recovery-test'))

        assert temp_queue.size() == 500

        # Track which events were sent
        sent_event_ids = set()

        def mock_batch_response(*args, **kwargs):
            compressed = kwargs['data']
            decompressed = gzip.decompress(compressed)
            payload = json.loads(decompressed)
            events = payload['events']

            # Track sent events
            for e in events:
                sent_event_ids.add(e['event_id'])

            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                'results': [
                    {'event_id': e['event_id'], 'status': 'success'}
                    for e in events
                ]
            }
            return mock_resp

        mock_post.side_effect = mock_batch_response

        result = batch_sync(
            queue=temp_queue,
            auth_token='token',
            server_url='http://localhost:8000',
            limit=1000,
            show_progress=False
        )

        # Verify 100% recovery
        assert result.synced_count == 500
        assert result.error_count == 0
        assert temp_queue.size() == 0
        assert len(sent_event_ids) == 500

        # Verify all event IDs were sent
        expected_ids = {f'evt-{i:06d}' for i in range(500)}
        assert sent_event_ids == expected_ids

    @patch('specify_cli.sync.batch.requests.post')
    def test_partial_failure_recovery(self, mock_post, temp_queue):
        """Partial failures should retry and eventually recover"""
        # Queue 100 events
        for i in range(100):
            temp_queue.queue_event(create_test_event(i))

        # First attempt: 80 succeed, 20 fail
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            'results': [
                {'event_id': f'evt-{i:06d}', 'status': 'success' if i < 80 else 'error', 'error_message': 'Temp failure'}
                for i in range(100)
            ]
        }
        mock_post.return_value = mock_response1

        result1 = batch_sync(temp_queue, 'token', 'http://localhost:8000', show_progress=False)
        assert result1.synced_count == 80
        assert result1.error_count == 20
        assert temp_queue.size() == 20  # Failed events remain

        # Second attempt: remaining 20 succeed
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            'results': [
                {'event_id': f'evt-{i:06d}', 'status': 'success'}
                for i in range(80, 100)
            ]
        }
        mock_post.return_value = mock_response2

        result2 = batch_sync(temp_queue, 'token', 'http://localhost:8000', show_progress=False)
        assert result2.synced_count == 20
        assert result2.error_count == 0
        assert temp_queue.size() == 0

        # Total recovery: 100%
        total_synced = result1.synced_count + result2.synced_count
        assert total_synced == 100

    @patch('specify_cli.sync.batch.requests.post')
    def test_event_order_preserved(self, mock_post, temp_queue):
        """Verify events are sent in FIFO order"""
        # Queue events with specific ordering
        for i in range(100):
            temp_queue.queue_event(create_test_event(i))

        received_order = []

        def mock_batch_response(*args, **kwargs):
            compressed = kwargs['data']
            decompressed = gzip.decompress(compressed)
            payload = json.loads(decompressed)
            events = payload['events']

            # Record order received
            received_order.extend([e['event_id'] for e in events])

            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                'results': [
                    {'event_id': e['event_id'], 'status': 'success'}
                    for e in events
                ]
            }
            return mock_resp

        mock_post.side_effect = mock_batch_response

        batch_sync(temp_queue, 'token', 'http://localhost:8000', show_progress=False)

        # Verify FIFO order
        expected_order = [f'evt-{i:06d}' for i in range(100)]
        assert received_order == expected_order


class TestOfflineWorkflowEndToEnd:
    """Full end-to-end workflow tests"""

    @patch('specify_cli.sync.batch.requests.post')
    def test_complete_offline_workflow(self, mock_post, temp_queue):
        """
        Complete offline workflow:
        1. Start online
        2. Go offline, queue events
        3. Reconnect, batch sync
        4. Verify all events synced
        """
        # Phase 1: Online (nothing to queue)
        assert temp_queue.size() == 0

        # Phase 2: Go offline, queue events
        for i in range(200):
            temp_queue.queue_event(create_test_event(i))
        assert temp_queue.size() == 200

        # Phase 3: Reconnect, batch sync
        def mock_batch_response(*args, **kwargs):
            compressed = kwargs['data']
            decompressed = gzip.decompress(compressed)
            payload = json.loads(decompressed)
            events = payload['events']

            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                'results': [
                    {'event_id': e['event_id'], 'status': 'success'}
                    for e in events
                ]
            }
            return mock_resp

        mock_post.side_effect = mock_batch_response

        result = batch_sync(
            queue=temp_queue,
            auth_token='token',
            server_url='http://localhost:8000',
            show_progress=False
        )

        # Phase 4: Verify all synced
        assert result.synced_count == 200
        assert result.error_count == 0
        assert temp_queue.size() == 0

    @patch('specify_cli.sync.batch.requests.post')
    def test_intermittent_connectivity(self, mock_post, temp_queue):
        """Test workflow with intermittent connectivity"""
        call_count = [0]

        def mock_intermittent(*args, **kwargs):
            call_count[0] += 1
            compressed = kwargs['data']
            decompressed = gzip.decompress(compressed)
            payload = json.loads(decompressed)
            events = payload['events']

            mock_resp = Mock()

            # First call fails, second succeeds
            if call_count[0] == 1:
                mock_resp.status_code = 503  # Service unavailable
            else:
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    'results': [
                        {'event_id': e['event_id'], 'status': 'success'}
                        for e in events
                    ]
                }

            return mock_resp

        mock_post.side_effect = mock_intermittent

        # Queue events
        for i in range(50):
            temp_queue.queue_event(create_test_event(i))

        # First sync attempt fails
        result1 = batch_sync(temp_queue, 'token', 'http://localhost:8000', show_progress=False)
        assert result1.error_count == 50
        assert temp_queue.size() == 50  # Events still in queue

        # Second sync attempt succeeds
        result2 = batch_sync(temp_queue, 'token', 'http://localhost:8000', show_progress=False)
        assert result2.synced_count == 50
        assert temp_queue.size() == 0
