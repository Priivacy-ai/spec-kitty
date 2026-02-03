"""Tests for batch sync functionality"""
import gzip
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

from specify_cli.sync.queue import OfflineQueue
from specify_cli.sync.batch import batch_sync, sync_all_queued_events, BatchSyncResult


@pytest.fixture
def temp_queue():
    """Create a queue with a temporary database"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / 'test_queue.db'
        queue = OfflineQueue(db_path)
        yield queue


@pytest.fixture
def populated_queue(temp_queue):
    """Create a queue with 100 test events"""
    for i in range(100):
        temp_queue.queue_event({
            'event_id': f'evt-{i:04d}',
            'event_type': 'WPStatusChanged',
            'aggregate_id': f'WP{i % 10:02d}',
            'lamport_clock': i,
            'node_id': 'test-node',
            'payload': {'index': i}
        })
    return temp_queue


@pytest.fixture
def mock_successful_response():
    """Mock a successful batch sync response"""
    def create_response(events):
        return {
            'results': [
                {'event_id': e['event_id'], 'status': 'success'}
                for e in events
            ]
        }
    return create_response


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


class TestBatchSyncEmptyQueue:
    """Test batch_sync with empty queue"""

    def test_batch_sync_empty_queue(self, temp_queue):
        """Test batch_sync with no events returns early"""
        result = batch_sync(
            queue=temp_queue,
            auth_token='test-token',
            server_url='http://localhost:8000',
            show_progress=False
        )

        assert result.total_events == 0
        assert result.synced_count == 0


class TestBatchSyncSuccess:
    """Test successful batch sync operations"""

    @patch('specify_cli.sync.batch.requests.post')
    def test_batch_sync_success(self, mock_post, populated_queue):
        """Test successful batch sync removes events from queue"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'event_id': f'evt-{i:04d}', 'status': 'success'}
                for i in range(100)
            ]
        }
        mock_post.return_value = mock_response

        result = batch_sync(
            queue=populated_queue,
            auth_token='test-token',
            server_url='http://localhost:8000',
            show_progress=False
        )

        assert result.total_events == 100
        assert result.synced_count == 100
        assert result.error_count == 0
        assert populated_queue.size() == 0  # Queue should be empty

    @patch('specify_cli.sync.batch.requests.post')
    def test_batch_sync_with_duplicates(self, mock_post, populated_queue):
        """Test batch sync handles duplicate events"""
        # Mock response with some duplicates
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'event_id': f'evt-{i:04d}', 'status': 'success' if i % 2 == 0 else 'duplicate'}
                for i in range(100)
            ]
        }
        mock_post.return_value = mock_response

        result = batch_sync(
            queue=populated_queue,
            auth_token='test-token',
            server_url='http://localhost:8000',
            show_progress=False
        )

        assert result.synced_count == 50  # Even indices
        assert result.duplicate_count == 50  # Odd indices
        assert result.success_count == 100  # All successful
        assert populated_queue.size() == 0  # All removed from queue

    @patch('specify_cli.sync.batch.requests.post')
    def test_batch_sync_gzip_compression(self, mock_post, populated_queue):
        """Test batch sync sends gzip compressed data"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'event_id': f'evt-{i:04d}', 'status': 'success'}
                for i in range(100)
            ]
        }
        mock_post.return_value = mock_response

        batch_sync(
            queue=populated_queue,
            auth_token='test-token',
            server_url='http://localhost:8000',
            show_progress=False
        )

        # Verify request was made with gzip headers
        call_args = mock_post.call_args
        headers = call_args.kwargs['headers']
        assert headers['Content-Encoding'] == 'gzip'
        assert headers['Content-Type'] == 'application/json'

        # Verify data is actually gzip compressed
        compressed_data = call_args.kwargs['data']
        decompressed = gzip.decompress(compressed_data)
        payload = json.loads(decompressed)
        assert 'events' in payload
        assert len(payload['events']) == 100

    @patch('specify_cli.sync.batch.requests.post')
    def test_batch_sync_auth_header(self, mock_post, populated_queue):
        """Test batch sync sends authorization header"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'results': []}
        mock_post.return_value = mock_response

        batch_sync(
            queue=populated_queue,
            auth_token='my-secret-token',
            server_url='http://localhost:8000',
            show_progress=False
        )

        call_args = mock_post.call_args
        headers = call_args.kwargs['headers']
        assert headers['Authorization'] == 'Bearer my-secret-token'

    @patch('specify_cli.sync.batch.requests.post')
    def test_batch_sync_url_construction(self, mock_post, populated_queue):
        """Test batch sync constructs correct URL"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'results': []}
        mock_post.return_value = mock_response

        # Test with trailing slash
        batch_sync(
            queue=populated_queue,
            auth_token='token',
            server_url='http://localhost:8000/',
            show_progress=False
        )

        call_args = mock_post.call_args
        assert call_args.args[0] == 'http://localhost:8000/api/v1/events/batch/'


class TestBatchSyncErrors:
    """Test batch sync error handling"""

    @patch('specify_cli.sync.batch.requests.post')
    def test_batch_sync_auth_failure(self, mock_post, populated_queue):
        """Test batch sync handles 401 authentication failure"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        initial_size = populated_queue.size()

        result = batch_sync(
            queue=populated_queue,
            auth_token='invalid-token',
            server_url='http://localhost:8000',
            show_progress=False
        )

        assert result.error_count == 100
        assert 'Authentication failed' in result.error_messages
        assert populated_queue.size() == initial_size  # Events not removed

    @patch('specify_cli.sync.batch.requests.post')
    def test_batch_sync_bad_request(self, mock_post, populated_queue):
        """Test batch sync handles 400 bad request"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'error': 'Max 1000 events per batch'}
        mock_post.return_value = mock_response

        result = batch_sync(
            queue=populated_queue,
            auth_token='token',
            server_url='http://localhost:8000',
            show_progress=False
        )

        assert result.error_count == 100
        assert 'Max 1000 events per batch' in result.error_messages

    @patch('specify_cli.sync.batch.requests.post')
    def test_batch_sync_server_error(self, mock_post, populated_queue):
        """Test batch sync handles 500 server error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        result = batch_sync(
            queue=populated_queue,
            auth_token='token',
            server_url='http://localhost:8000',
            show_progress=False
        )

        assert result.error_count == 100
        assert 'HTTP 500' in result.error_messages[0]

    @patch('specify_cli.sync.batch.requests.post')
    def test_batch_sync_timeout(self, mock_post, populated_queue):
        """Test batch sync handles request timeout"""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()

        result = batch_sync(
            queue=populated_queue,
            auth_token='token',
            server_url='http://localhost:8000',
            show_progress=False
        )

        assert result.error_count == 100
        assert 'Request timeout' in result.error_messages

    @patch('specify_cli.sync.batch.requests.post')
    def test_batch_sync_connection_error(self, mock_post, populated_queue):
        """Test batch sync handles connection error"""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Network unreachable")

        result = batch_sync(
            queue=populated_queue,
            auth_token='token',
            server_url='http://localhost:8000',
            show_progress=False
        )

        assert result.error_count == 100
        assert 'Connection error' in result.error_messages[0]

    @patch('specify_cli.sync.batch.requests.post')
    def test_batch_sync_partial_failure(self, mock_post, populated_queue):
        """Test batch sync handles partial event failures"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'event_id': f'evt-{i:04d}', 'status': 'success' if i < 90 else 'error', 'error_message': 'DB error'}
                for i in range(100)
            ]
        }
        mock_post.return_value = mock_response

        result = batch_sync(
            queue=populated_queue,
            auth_token='token',
            server_url='http://localhost:8000',
            show_progress=False
        )

        assert result.synced_count == 90
        assert result.error_count == 10
        assert len(result.synced_ids) == 90
        assert len(result.failed_ids) == 10
        # Failed events stay in queue, successful ones removed
        assert populated_queue.size() == 10


class TestBatchSyncLimit:
    """Test batch sync with limit parameter"""

    @patch('specify_cli.sync.batch.requests.post')
    def test_batch_sync_respects_limit(self, mock_post, temp_queue):
        """Test batch sync only syncs up to limit events"""
        # Queue 200 events
        for i in range(200):
            temp_queue.queue_event({
                'event_id': f'evt-{i:04d}',
                'event_type': 'Test',
                'payload': {}
            })

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'event_id': f'evt-{i:04d}', 'status': 'success'}
                for i in range(50)
            ]
        }
        mock_post.return_value = mock_response

        result = batch_sync(
            queue=temp_queue,
            auth_token='token',
            server_url='http://localhost:8000',
            limit=50,
            show_progress=False
        )

        assert result.total_events == 50
        assert temp_queue.size() == 150  # 150 events remain


class TestBatchSync1000Events:
    """Test batch sync with 1000 events as per spec requirement"""

    @patch('specify_cli.sync.batch.requests.post')
    def test_batch_sync_1000_events(self, mock_post, temp_queue):
        """Test batch sync handles 1000 events (spec requirement)"""
        # Queue 1000 events
        for i in range(1000):
            temp_queue.queue_event({
                'event_id': f'evt-{i:04d}',
                'event_type': 'WPStatusChanged',
                'aggregate_id': f'WP{i % 100:02d}',
                'lamport_clock': i,
                'node_id': 'test-node',
                'payload': {'index': i}
            })

        assert temp_queue.size() == 1000

        # Mock successful response for all 1000
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'results': [
                {'event_id': f'evt-{i:04d}', 'status': 'success'}
                for i in range(1000)
            ]
        }
        mock_post.return_value = mock_response

        result = batch_sync(
            queue=temp_queue,
            auth_token='token',
            server_url='http://localhost:8000',
            limit=1000,
            show_progress=False
        )

        assert result.total_events == 1000
        assert result.synced_count == 1000
        assert result.error_count == 0
        assert temp_queue.size() == 0  # Queue should be empty

        # Verify gzip payload contains all 1000 events
        call_args = mock_post.call_args
        compressed_data = call_args.kwargs['data']
        decompressed = gzip.decompress(compressed_data)
        payload = json.loads(decompressed)
        assert len(payload['events']) == 1000


class TestSyncAllQueuedEvents:
    """Test sync_all_queued_events function"""

    @patch('specify_cli.sync.batch.requests.post')
    def test_sync_all_in_batches(self, mock_post, temp_queue):
        """Test syncing more events than batch size"""
        # Queue 250 events
        for i in range(250):
            temp_queue.queue_event({
                'event_id': f'evt-{i:04d}',
                'event_type': 'Test',
                'payload': {}
            })

        def mock_response_fn(*args, **kwargs):
            # Parse the request to determine which events
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

        mock_post.side_effect = mock_response_fn

        result = sync_all_queued_events(
            queue=temp_queue,
            auth_token='token',
            server_url='http://localhost:8000',
            batch_size=100,
            show_progress=False
        )

        assert result.total_events == 250
        assert result.synced_count == 250
        assert temp_queue.size() == 0
        assert mock_post.call_count == 3  # 100 + 100 + 50

    @patch('specify_cli.sync.batch.requests.post')
    def test_sync_all_stops_on_all_errors(self, mock_post, populated_queue):
        """Test sync_all stops if all events in a batch fail"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        result = sync_all_queued_events(
            queue=populated_queue,
            auth_token='token',
            server_url='http://localhost:8000',
            show_progress=False
        )

        # Should have tried once and stopped
        assert mock_post.call_count == 1
        assert result.error_count == 100
