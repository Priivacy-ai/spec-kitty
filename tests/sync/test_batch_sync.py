"""Tests for batch sync functionality"""

import gzip
import json
import logging
import tempfile
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import httpx
import pytest
import respx

from specify_cli.auth.secure_storage import SecureStorage
from specify_cli.auth.session import StoredSession, Team
from specify_cli.auth.token_manager import TokenManager
from specify_cli.sync.queue import OfflineQueue
from specify_cli.sync.batch import (
    DEFAULT_MAX_DECOMPRESSED_BYTES_PER_BATCH,
    BatchSyncResult,
    batch_sync,
    categorize_error,
    sync_all_queued_events,
)
from specify_cli.sync.feature_flags import SAAS_SYNC_ENV_VAR

pytestmark = pytest.mark.fast

_INGRESS_SAAS_BASE_URL = "https://saas.example"


@pytest.fixture(autouse=True)
def _default_private_team_token_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default TokenManager fixture exposing a Private Teamspace.

    WP04 (private-teamspace-ingress-safeguards) makes Private Teamspace a hard
    precondition for direct ingress. Pre-existing batch tests in this module
    don't bother with TokenManager state — they rely on ``requests.post`` being
    patched. To preserve their semantics without changing each one, install an
    autouse default that surfaces a Private Teamspace. Individual tests that
    need a different session re-patch ``get_token_manager`` themselves; the
    later monkeypatch wins.
    """
    now = datetime.now(UTC)
    fake_session = StoredSession(
        user_id="user-default",
        email="default@example.com",
        name="Default User",
        teams=[
            Team(
                id="default-private-team",
                name="Default Private",
                role="owner",
                is_private_teamspace=True,
            )
        ],
        default_team_id="default-private-team",
        access_token="default-access",
        refresh_token="default-refresh",
        session_id="default-sess",
        issued_at=now,
        access_token_expires_at=now + timedelta(hours=1),
        refresh_token_expires_at=now + timedelta(days=30),
        scope="offline_access",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )
    fake_tm = Mock()
    fake_tm.get_current_session.return_value = fake_session
    fake_tm.is_authenticated = True
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: fake_tm)


@pytest.fixture
def temp_queue():
    """Create a queue with a temporary database"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_queue.db"
        queue = OfflineQueue(db_path)
        yield queue


@pytest.fixture
def populated_queue(temp_queue):
    """Create a queue with 100 test events"""
    for i in range(100):
        temp_queue.queue_event(
            {
                "event_id": f"evt-{i:04d}",
                "event_type": "WPStatusChanged",
                "aggregate_id": f"WP{i % 10:02d}",
                "lamport_clock": i,
                "node_id": "test-node",
                "payload": {"index": i},
            }
        )
    return temp_queue


@pytest.fixture
def mock_successful_response():
    """Mock a successful batch sync response"""

    def create_response(events):
        return {"results": [{"event_id": e["event_id"], "status": "success"} for e in events]}

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
        result = batch_sync(queue=temp_queue, auth_token="test-token", server_url="http://localhost:8000", show_progress=False)

        assert result.total_events == 0
        assert result.synced_count == 0


class TestSaasFeatureFlag:
    """Feature-flag behavior for SaaS upload."""

    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_skips_network_when_disabled(self, mock_post, populated_queue, monkeypatch):
        """No HTTP upload should occur when SaaS sync feature is disabled."""
        monkeypatch.delenv(SAAS_SYNC_ENV_VAR, raising=False)
        initial_size = populated_queue.size()

        result = batch_sync(
            queue=populated_queue,
            auth_token="test-token",
            server_url="http://localhost:8000",
            show_progress=False,
        )

        assert populated_queue.size() == initial_size
        assert result.total_events == 0
        assert any("not enabled" in msg.lower() for msg in result.error_messages)
        mock_post.assert_not_called()


class TestBatchSyncSuccess:
    """Test successful batch sync operations"""

    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_success(self, mock_post, populated_queue):
        """Test successful batch sync removes events from queue"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"event_id": f"evt-{i:04d}", "status": "success"} for i in range(100)]}
        mock_post.return_value = mock_response

        result = batch_sync(queue=populated_queue, auth_token="test-token", server_url="http://localhost:8000", show_progress=False)

        assert result.total_events == 100
        assert result.synced_count == 100
        assert result.error_count == 0
        assert populated_queue.size() == 0  # Queue should be empty

    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_with_duplicates(self, mock_post, populated_queue):
        """Test batch sync handles duplicate events"""
        # Mock response with some duplicates
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"event_id": f"evt-{i:04d}", "status": "success" if i % 2 == 0 else "duplicate"} for i in range(100)]}
        mock_post.return_value = mock_response

        result = batch_sync(queue=populated_queue, auth_token="test-token", server_url="http://localhost:8000", show_progress=False)

        assert result.synced_count == 50  # Even indices
        assert result.duplicate_count == 50  # Odd indices
        assert result.success_count == 100  # All successful
        assert populated_queue.size() == 0  # All removed from queue

    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_gzip_compression(self, mock_post, populated_queue):
        """Test batch sync sends gzip compressed data"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"event_id": f"evt-{i:04d}", "status": "success"} for i in range(100)]}
        mock_post.return_value = mock_response

        batch_sync(queue=populated_queue, auth_token="test-token", server_url="http://localhost:8000", show_progress=False)

        # Verify request was made with gzip headers
        call_args = mock_post.call_args
        headers = call_args.kwargs["headers"]
        assert headers["Content-Encoding"] == "gzip"
        assert headers["Content-Type"] == "application/json"

        # Verify data is actually gzip compressed
        compressed_data = call_args.kwargs["data"]
        decompressed = gzip.decompress(compressed_data)
        payload = json.loads(decompressed)
        assert "events" in payload
        assert len(payload["events"]) == 100

    @patch("specify_cli.sync.batch.requests.get")
    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_consumes_advertised_max_events_per_batch(
        self,
        mock_post,
        mock_get,
        populated_queue,
    ):
        """Live SaaS limits should cap the number of events sent per request."""
        health_response = Mock()
        health_response.status_code = 200
        health_response.json.return_value = {
            "sync_ingress": {
                "contract_version": "sync-ingress-limits.v1",
                "limits": {
                    "max_events_per_batch": 25,
                    "max_decompressed_bytes_per_batch": 1_000_000,
                    "retry_after_min_seconds": 5,
                    "retry_after_max_seconds": 60,
                },
            }
        }
        mock_get.return_value = health_response

        post_response = Mock()
        post_response.status_code = 200
        post_response.json.return_value = {"results": [{"event_id": f"evt-{i:04d}", "status": "success"} for i in range(25)]}
        mock_post.return_value = post_response

        result = batch_sync(
            queue=populated_queue,
            auth_token="token",
            server_url="https://spec-kitty-dev.fly.dev",
            limit=1000,
            show_progress=False,
        )

        assert result.total_events == 25
        call_args = mock_post.call_args
        payload = json.loads(gzip.decompress(call_args.kwargs["data"]))
        assert len(payload["events"]) == 25
        assert mock_get.call_args.args[0] == "https://spec-kitty-dev.fly.dev/api/v1/sync/health/"

    @patch("specify_cli.sync.batch.requests.get")
    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_shrinks_batch_to_advertised_decompressed_bytes(
        self,
        mock_post,
        mock_get,
        temp_queue,
    ):
        """The CLI should split oversized batches before sending to SaaS."""
        for i in range(8):
            temp_queue.queue_event(
                {
                    "event_id": f"large-evt-{i:04d}",
                    "event_type": "WPStatusChanged",
                    "aggregate_id": "WP01",
                    "lamport_clock": i,
                    "node_id": "test-node",
                    "payload": {"body": "x" * 200},
                }
            )

        health_response = Mock()
        health_response.status_code = 200
        health_response.json.return_value = {
            "sync_ingress": {
                "limits": {
                    "max_events_per_batch": 8,
                    "max_decompressed_bytes_per_batch": 900,
                }
            }
        }
        mock_get.return_value = health_response

        post_response = Mock()
        post_response.status_code = 200

        def _post_response(*args, **kwargs):
            sent = json.loads(gzip.decompress(kwargs["data"]))["events"]
            post_response.json.return_value = {"results": [{"event_id": event["event_id"], "status": "success"} for event in sent]}
            return post_response

        mock_post.side_effect = _post_response

        result = batch_sync(
            queue=temp_queue,
            auth_token="token",
            server_url="https://spec-kitty-dev.fly.dev",
            limit=8,
            show_progress=False,
        )

        sent_payload = gzip.decompress(mock_post.call_args.kwargs["data"])
        sent_events = json.loads(sent_payload)["events"]
        assert 0 < len(sent_events) < 8
        assert len(sent_payload) <= int(900 * 0.90)
        assert result.total_events == len(sent_events)

    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_uses_fallback_decompressed_byte_limit(self, mock_post, temp_queue):
        """When health limits are unavailable, the CLI should still avoid huge batches."""
        for i in range(2):
            temp_queue.queue_event(
                {
                    "event_id": f"fallback-large-{i}",
                    "event_type": "WPStatusChanged",
                    "aggregate_id": "WP01",
                    "lamport_clock": i,
                    "node_id": "test-node",
                    "payload": {"body": "x" * (DEFAULT_MAX_DECOMPRESSED_BYTES_PER_BATCH // 2)},
                }
            )

        post_response = Mock()
        post_response.status_code = 200

        def _post_response(*args, **kwargs):
            sent = json.loads(gzip.decompress(kwargs["data"]))["events"]
            post_response.json.return_value = {"results": [{"event_id": event["event_id"], "status": "success"} for event in sent]}
            return post_response

        mock_post.side_effect = _post_response

        result = batch_sync(
            queue=temp_queue,
            auth_token="token",
            server_url="http://localhost:8000",
            limit=2,
            show_progress=False,
        )

        sent_payload = gzip.decompress(mock_post.call_args.kwargs["data"])
        assert len(sent_payload) <= DEFAULT_MAX_DECOMPRESSED_BYTES_PER_BATCH
        assert result.synced_count == 1
        assert temp_queue.size() == 1

    @patch("specify_cli.sync.batch.requests.get")
    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_retries_smaller_batch_after_server_size_rejection(
        self,
        mock_post,
        mock_get,
        temp_queue,
    ):
        """Server decompressed-size rejections should shrink, retry, and avoid unknown errors."""
        for i in range(4):
            temp_queue.queue_event(
                {
                    "event_id": f"retry-large-{i}",
                    "event_type": "WPStatusChanged",
                    "aggregate_id": "WP01",
                    "lamport_clock": i,
                    "node_id": "test-node",
                    "payload": {"body": "x" * 100},
                }
            )

        health_response = Mock()
        health_response.status_code = 200
        health_response.json.return_value = {
            "sync_ingress": {
                "limits": {
                    "max_events_per_batch": 4,
                    "max_decompressed_bytes_per_batch": 100_000,
                }
            }
        }
        mock_get.return_value = health_response

        rejected = Mock()
        rejected.status_code = 413
        rejected.json.return_value = {
            "error": "Batch payload exceeds decompressed byte limit",
            "error_code": "sync_batch_too_large",
            "category": "request_too_large",
            "limits": {
                "max_events_per_batch": 4,
                "max_decompressed_bytes_per_batch": 900,
            },
        }

        accepted = Mock()
        accepted.status_code = 200

        calls = {"count": 0}

        def _post_response(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                return rejected
            sent = json.loads(gzip.decompress(kwargs["data"]))["events"]
            accepted.json.return_value = {"results": [{"event_id": event["event_id"], "status": "success"} for event in sent]}
            return accepted

        mock_post.side_effect = _post_response

        result = batch_sync(
            queue=temp_queue,
            auth_token="token",
            server_url="https://spec-kitty-dev.fly.dev",
            limit=4,
            show_progress=False,
        )

        assert mock_post.call_count == 2
        retried_payload = json.loads(gzip.decompress(mock_post.call_args.kwargs["data"]))
        assert 0 < len(retried_payload["events"]) < 4
        assert result.error_count == 0
        assert result.synced_count == len(retried_payload["events"])

    @patch("specify_cli.sync.batch.requests.get")
    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_reports_single_oversized_event_without_posting(
        self,
        mock_post,
        mock_get,
        temp_queue,
    ):
        """A single event that cannot fit the advertised limit is isolated in the report."""
        temp_queue.queue_event(
            {
                "event_id": "too-large-one",
                "event_type": "WPStatusChanged",
                "aggregate_id": "WP01",
                "lamport_clock": 1,
                "node_id": "test-node",
                "payload": {"body": "x" * 500},
            }
        )

        health_response = Mock()
        health_response.status_code = 200
        health_response.json.return_value = {
            "sync_ingress": {
                "limits": {
                    "max_events_per_batch": 10,
                    "max_decompressed_bytes_per_batch": 100,
                }
            }
        }
        mock_get.return_value = health_response

        result = batch_sync(
            queue=temp_queue,
            auth_token="token",
            server_url="https://spec-kitty-dev.fly.dev",
            limit=10,
            show_progress=False,
        )

        mock_post.assert_not_called()
        assert result.error_count == 1
        assert result.failed_results[0].error_category == "oversized_event"
        assert "unknown" not in result.category_counts

    def test_oversized_batch_error_classifies_without_unknown(self):
        assert categorize_error("Batch payload exceeds decompressed byte limit") == "oversized_batch"

    @patch("specify_cli.sync.batch.requests.get")
    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_server_413_on_single_event_classifies_as_oversized_event(
        self,
        mock_post,
        mock_get,
        temp_queue,
    ):
        """Server-side 413 after shrinking to 1 event uses failed_permanent, not rejected."""
        temp_queue.queue_event(
            {
                "event_id": "single-server-413",
                "event_type": "WPStatusChanged",
                "aggregate_id": "WP01",
                "lamport_clock": 1,
                "node_id": "test-node",
                "payload": {"body": "x" * 50},
            }
        )

        health_response = Mock()
        health_response.status_code = 200
        health_response.json.return_value = {
            "sync_ingress": {"limits": {"max_events_per_batch": 10, "max_decompressed_bytes_per_batch": 100_000}}
        }
        mock_get.return_value = health_response

        rejected_413 = Mock()
        rejected_413.status_code = 413
        rejected_413.json.return_value = {"error": "Batch payload exceeds decompressed byte limit"}
        mock_post.return_value = rejected_413

        result = batch_sync(
            queue=temp_queue,
            auth_token="token",
            server_url="https://spec-kitty-dev.fly.dev",
            limit=10,
            show_progress=False,
        )

        assert mock_post.call_count == 1
        assert result.error_count == 1
        assert result.failed_results[0].error_category == "oversized_event"
        assert result.failed_results[0].status == "failed_permanent"
        assert temp_queue.size() == 0

    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_throttled_category_on_429(self, mock_post, temp_queue):
        """HTTP 429 should classify as 'throttled', not 'retryable_transport'."""
        temp_queue.queue_event(
            {"event_id": "evt-429", "event_type": "WPStatusChanged", "payload": {}}
        )

        throttled = Mock()
        throttled.status_code = 429
        throttled.json.return_value = {"error": "Too many requests"}
        mock_post.return_value = throttled

        result = batch_sync(
            queue=temp_queue,
            auth_token="token",
            server_url="http://localhost:8000",
            limit=10,
            show_progress=False,
        )

        assert result.category_counts.get("throttled", 0) == 1
        assert "retryable_transport" not in result.category_counts

    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_auth_header(self, mock_post, populated_queue):
        """Test batch sync sends authorization header"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_post.return_value = mock_response

        batch_sync(queue=populated_queue, auth_token="my-secret-token", server_url="http://localhost:8000", show_progress=False)

        call_args = mock_post.call_args
        headers = call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer my-secret-token"

    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_sends_private_team_slug_header(self, mock_post, populated_queue, monkeypatch):
        """Batch sync should target Private Teamspace for ingress when available."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_post.return_value = mock_response

        now = datetime.now(UTC)
        fake_tm = Mock()
        fake_tm.get_current_session.return_value = StoredSession(
            user_id="user-1",
            email="robert@example.com",
            name="Robert",
            teams=[
                Team(id="private-team", name="Robert Private Teamspace", role="owner", is_private_teamspace=True),
                Team(id="product-team", name="Product Team", role="member"),
            ],
            default_team_id="private-team",
            access_token="access",
            refresh_token="refresh",
            session_id="sess-1",
            issued_at=now,
            access_token_expires_at=now + timedelta(hours=1),
            refresh_token_expires_at=now + timedelta(days=30),
            scope="offline_access",
            storage_backend="file",
            last_used_at=now,
            auth_method="authorization_code",
        )
        monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: fake_tm)

        batch_sync(
            queue=populated_queue,
            auth_token="my-secret-token",
            server_url="http://localhost:8000",
            show_progress=False,
        )

        call_args = mock_post.call_args
        headers = call_args.kwargs["headers"]
        assert headers["X-Team-Slug"] == "private-team"

    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_prefers_private_team_over_shared_default(self, mock_post, populated_queue, monkeypatch):
        """Ingress must keep routing to Private Teamspace even if session default drifts."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_post.return_value = mock_response

        now = datetime.now(UTC)
        fake_tm = Mock()
        fake_tm.get_current_session.return_value = StoredSession(
            user_id="user-1",
            email="robert@example.com",
            name="Robert",
            teams=[
                Team(id="product-team", name="Product Team", role="member"),
                Team(id="private-team", name="Robert Private Teamspace", role="owner", is_private_teamspace=True),
            ],
            default_team_id="product-team",
            access_token="access",
            refresh_token="refresh",
            session_id="sess-1",
            issued_at=now,
            access_token_expires_at=now + timedelta(hours=1),
            refresh_token_expires_at=now + timedelta(days=30),
            scope="offline_access",
            storage_backend="file",
            last_used_at=now,
            auth_method="authorization_code",
        )
        monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: fake_tm)

        batch_sync(
            queue=populated_queue,
            auth_token="my-secret-token",
            server_url="http://localhost:8000",
            show_progress=False,
        )

        call_args = mock_post.call_args
        headers = call_args.kwargs["headers"]
        assert headers["X-Team-Slug"] == "private-team"

    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_url_construction(self, mock_post, populated_queue):
        """Test batch sync constructs correct URL"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_post.return_value = mock_response

        # Test with trailing slash
        batch_sync(queue=populated_queue, auth_token="token", server_url="http://localhost:8000/", show_progress=False)

        call_args = mock_post.call_args
        assert call_args.args[0] == "http://localhost:8000/api/v1/events/batch/"


class TestBatchSyncErrors:
    """Test batch sync error handling"""

    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_auth_failure(self, mock_post, populated_queue):
        """Test batch sync handles 401 authentication failure"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        initial_size = populated_queue.size()

        result = batch_sync(queue=populated_queue, auth_token="invalid-token", server_url="http://localhost:8000", show_progress=False)

        assert result.error_count == 100
        assert "Authentication failed" in result.error_messages
        assert populated_queue.size() == initial_size  # Events not removed

    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_bad_request(self, mock_post, populated_queue):
        """Test batch sync handles 400 bad request"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Max 1000 events per batch"}
        mock_post.return_value = mock_response

        result = batch_sync(queue=populated_queue, auth_token="token", server_url="http://localhost:8000", show_progress=False)

        assert result.error_count == 100
        assert "Max 1000 events per batch" in result.error_messages

    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_server_error(self, mock_post, populated_queue):
        """Test batch sync handles 500 server error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        result = batch_sync(queue=populated_queue, auth_token="token", server_url="http://localhost:8000", show_progress=False)

        assert result.error_count == 100
        assert "HTTP 500" in result.error_messages[0]

    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_timeout(self, mock_post, populated_queue):
        """Test batch sync handles request timeout"""
        import requests

        mock_post.side_effect = requests.exceptions.Timeout()

        result = batch_sync(queue=populated_queue, auth_token="token", server_url="http://localhost:8000", show_progress=False)

        assert result.error_count == 100
        assert "Request timeout" in result.error_messages

    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_connection_error(self, mock_post, populated_queue):
        """Test batch sync handles connection error"""
        import requests

        mock_post.side_effect = requests.exceptions.ConnectionError("Network unreachable")

        result = batch_sync(queue=populated_queue, auth_token="token", server_url="http://localhost:8000", show_progress=False)

        assert result.error_count == 100
        assert "Connection error" in result.error_messages[0]

    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_partial_failure(self, mock_post, populated_queue):
        """Test batch sync handles partial event failures"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"event_id": f"evt-{i:04d}", "status": "success" if i < 90 else "error", "error_message": "DB error"} for i in range(100)]
        }
        mock_post.return_value = mock_response

        result = batch_sync(queue=populated_queue, auth_token="token", server_url="http://localhost:8000", show_progress=False)

        assert result.synced_count == 90
        assert result.error_count == 10
        assert len(result.synced_ids) == 90
        assert len(result.failed_ids) == 10
        # Failed events stay in queue, successful ones removed
        assert populated_queue.size() == 10


class TestBatchSyncLimit:
    """Test batch sync with limit parameter"""

    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_respects_limit(self, mock_post, temp_queue):
        """Test batch sync only syncs up to limit events"""
        # Queue 200 events
        for i in range(200):
            temp_queue.queue_event({"event_id": f"evt-{i:04d}", "event_type": "Test", "payload": {}})

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"event_id": f"evt-{i:04d}", "status": "success"} for i in range(50)]}
        mock_post.return_value = mock_response

        result = batch_sync(queue=temp_queue, auth_token="token", server_url="http://localhost:8000", limit=50, show_progress=False)

        assert result.total_events == 50
        assert temp_queue.size() == 150  # 150 events remain


class TestBatchSync1000Events:
    """Test batch sync with a representative large batch."""

    @patch("specify_cli.sync.batch.requests.post")
    def test_batch_sync_1000_events(self, mock_post, temp_queue):
        """Test batch sync handles a large compressed payload."""
        event_count = 200

        # Queue a representative large batch
        for i in range(event_count):
            temp_queue.queue_event(
                {
                    "event_id": f"evt-{i:04d}",
                    "event_type": "WPStatusChanged",
                    "aggregate_id": f"WP{i % 100:02d}",
                    "lamport_clock": i,
                    "node_id": "test-node",
                    "payload": {"index": i},
                }
            )

        assert temp_queue.size() == event_count

        # Mock successful response for all queued events
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"event_id": f"evt-{i:04d}", "status": "success"} for i in range(event_count)]}
        mock_post.return_value = mock_response

        result = batch_sync(
            queue=temp_queue,
            auth_token="token",
            server_url="http://localhost:8000",
            limit=event_count,
            show_progress=False,
        )

        assert result.total_events == event_count
        assert result.synced_count == event_count
        assert result.error_count == 0
        assert temp_queue.size() == 0  # Queue should be empty

        # Verify gzip payload contains all queued events
        call_args = mock_post.call_args
        compressed_data = call_args.kwargs["data"]
        decompressed = gzip.decompress(compressed_data)
        payload = json.loads(decompressed)
        assert len(payload["events"]) == event_count


class TestSyncAllQueuedEvents:
    """Test sync_all_queued_events function"""

    @patch("specify_cli.sync.batch.requests.post")
    def test_sync_all_in_batches(self, mock_post, temp_queue):
        """Test syncing more events than batch size"""
        # Queue 250 events
        for i in range(250):
            temp_queue.queue_event({"event_id": f"evt-{i:04d}", "event_type": "Test", "payload": {}})

        def mock_response_fn(*args, **kwargs):
            # Parse the request to determine which events
            compressed = kwargs["data"]
            decompressed = gzip.decompress(compressed)
            payload = json.loads(decompressed)
            events = payload["events"]

            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"results": [{"event_id": e["event_id"], "status": "success"} for e in events]}
            return mock_resp

        mock_post.side_effect = mock_response_fn

        result = sync_all_queued_events(
            queue=temp_queue,
            auth_token="token",
            server_url="http://localhost:8000",
            batch_size=100,
            show_progress=False,
        )

        assert result.total_events == 250
        assert result.synced_count == 250
        assert temp_queue.size() == 0
        assert mock_post.call_count == 3  # 100 + 100 + 50

    @patch("specify_cli.sync.batch.requests.post")
    def test_sync_all_progress_output_is_log_readable(self, mock_post, temp_queue, capsys):
        """Manual drains should expose counts without relying on an interactive progress bar."""
        for i in range(3):
            temp_queue.queue_event({"event_id": f"evt-{i:04d}", "event_type": "Test", "payload": {}})

        def mock_response_fn(*args, **kwargs):
            events = json.loads(gzip.decompress(kwargs["data"]))["events"]
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"results": [{"event_id": e["event_id"], "status": "success"} for e in events]}
            return mock_resp

        mock_post.side_effect = mock_response_fn

        sync_all_queued_events(
            queue=temp_queue,
            auth_token="token",
            server_url="http://localhost:8000",
            batch_size=2,
            show_progress=True,
        )

        out = capsys.readouterr().out
        assert "Initial queued events: 3" in out
        assert "requested_batch_size=2" in out
        assert "Sync batch: events=" in out
        assert "Progress: accepted=" in out
        assert "remaining=0" in out

    @patch("specify_cli.sync.batch.requests.post")
    def test_sync_all_stops_on_all_errors(self, mock_post, populated_queue):
        """Test sync_all stops if all events in a batch fail"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        result = sync_all_queued_events(queue=populated_queue, auth_token="token", server_url="http://localhost:8000", show_progress=False)

        # Should have tried once and stopped
        assert mock_post.call_count == 1
        assert result.error_count == 100

    @patch("specify_cli.sync.batch.requests.get")
    @patch("specify_cli.sync.batch.requests.post")
    def test_sync_all_continues_past_oversized_event(self, mock_post, mock_get, temp_queue):
        """An oversized event at queue head must not permanently stall subsequent events."""
        temp_queue.queue_event(
            {
                "event_id": "oversized-head",
                "event_type": "WPStatusChanged",
                "aggregate_id": "WP01",
                "lamport_clock": 1,
                "node_id": "test-node",
                "payload": {"body": "x" * 500},
            }
        )
        for i in range(3):
            temp_queue.queue_event(
                {"event_id": f"good-{i}", "event_type": "WPStatusChanged", "payload": {}}
            )

        health_response = Mock()
        health_response.status_code = 200
        health_response.json.return_value = {
            "sync_ingress": {"limits": {"max_events_per_batch": 10, "max_decompressed_bytes_per_batch": 100}}
        }
        mock_get.return_value = health_response

        def _post_response(*args, **kwargs):
            events = json.loads(gzip.decompress(kwargs["data"]))["events"]
            resp = Mock()
            resp.status_code = 200
            resp.json.return_value = {"results": [{"event_id": e["event_id"], "status": "success"} for e in events]}
            return resp

        mock_post.side_effect = _post_response

        # Use a non-localhost URL so _should_probe_advertised_limits returns True
        # and the mocked health limits (100 bytes) take effect.
        result = sync_all_queued_events(
            queue=temp_queue,
            auth_token="token",
            server_url="https://spec-kitty-dev.fly.dev",
            batch_size=10,
            show_progress=False,
        )

        assert temp_queue.size() == 0
        assert result.synced_count == 3
        assert result.error_count == 1
        assert result.category_counts.get("oversized_event", 0) == 1


# ---------------------------------------------------------------------------
# WP04 — Direct-ingress shared helper coverage (T018)
#
# These tests are sync (no @pytest.mark.asyncio); ``batch_sync`` is sync.
# ``respx.mock`` intercepts the sync ``httpx.Client`` GET issued by the
# rehydrate path; ``unittest.mock.patch`` intercepts the ``requests.post``
# used by the actual batch ingress POST.
# ---------------------------------------------------------------------------


class _IngressFakeStorage(SecureStorage):  # type: ignore[misc]
    """Minimal in-memory ``SecureStorage`` for WP04 ingress fixtures."""

    def __init__(self) -> None:
        self._session: StoredSession | None = None

    def read(self) -> StoredSession | None:
        return self._session

    def write(self, session: StoredSession) -> None:
        self._session = session

    def delete(self) -> None:
        self._session = None

    @property
    def backend_name(self) -> str:
        return "file"


def _build_ingress_session(*, teams: list[Team]) -> StoredSession:
    """Build a ``StoredSession`` carrying the supplied team list."""
    now = datetime.now(UTC)
    return StoredSession(
        user_id="user-1",
        email="u@example.com",
        name="U",
        teams=teams,
        default_team_id=teams[0].id if teams else "",
        access_token="access-v1",
        refresh_token="refresh-v1",
        session_id="sess",
        issued_at=now,
        access_token_expires_at=now + timedelta(seconds=900),
        refresh_token_expires_at=None,
        scope="openid",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )


@pytest.fixture
def token_manager_with_shared_only_session() -> TokenManager:
    """A ``TokenManager`` whose loaded session has only a shared (non-private) team."""
    storage = _IngressFakeStorage()
    tm = TokenManager(storage, saas_base_url=_INGRESS_SAAS_BASE_URL)
    tm._session = _build_ingress_session(
        teams=[
            Team(
                id="t-shared",
                name="Shared",
                role="member",
                is_private_teamspace=False,
            )
        ]
    )
    return tm


@pytest.fixture
def token_manager_with_private_session() -> TokenManager:
    """A ``TokenManager`` whose loaded session already has a Private Teamspace."""
    storage = _IngressFakeStorage()
    tm = TokenManager(storage, saas_base_url=_INGRESS_SAAS_BASE_URL)
    tm._session = _build_ingress_session(
        teams=[
            Team(
                id="t-private",
                name="Private",
                role="owner",
                is_private_teamspace=True,
            )
        ]
    )
    return tm


def flush_some_events(token_manager: TokenManager, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Drive ``batch_sync`` against a small fixture queue using ``token_manager``.

    Mocks ``requests.post`` so any successful ingress call is recorded but does
    not hit the network. Returns the mock so assertions can inspect it.
    """
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: token_manager)
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "wp04_queue.db"
        queue = OfflineQueue(db_path)
        for i in range(3):
            queue.queue_event(
                {
                    "event_id": f"wp04-evt-{i:04d}",
                    "event_type": "WPStatusChanged",
                    "aggregate_id": "WP04",
                    "lamport_clock": i,
                    "node_id": "test-node",
                    "payload": {"index": i},
                }
            )

        with patch("specify_cli.sync.batch.requests.post") as mock_post:
            response = Mock()
            response.status_code = 200
            response.json.return_value = {"results": [{"event_id": f"wp04-evt-{i:04d}", "status": "success"} for i in range(3)]}
            mock_post.return_value = response
            batch_sync(
                queue=queue,
                auth_token="test-token",
                server_url=_INGRESS_SAAS_BASE_URL,
                show_progress=False,
            )
            return mock_post


@respx.mock
def test_batch_shared_only_session_triggers_one_me_rehydrate(
    token_manager_with_shared_only_session: TokenManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-002: shared-only session triggers exactly one /api/v1/me rehydrate then sends batch."""
    me_route = respx.get(f"{_INGRESS_SAAS_BASE_URL}/api/v1/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "email": "u@example.com",
                "teams": [
                    {
                        "id": "t-private",
                        "name": "Private",
                        "role": "owner",
                        "is_private_teamspace": True,
                    }
                ],
            },
        )
    )

    mock_post = flush_some_events(token_manager_with_shared_only_session, monkeypatch)

    assert me_route.call_count == 1
    assert mock_post.call_count == 1
    headers = mock_post.call_args.kwargs["headers"]
    assert headers["X-Team-Slug"] == "t-private"


@respx.mock
def test_batch_skips_ingress_when_rehydrate_yields_no_private(
    token_manager_with_shared_only_session: TokenManager,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC-001 + AC-004: shared-only session, rehydrate returns no private => no batch POST."""
    respx.get(f"{_INGRESS_SAAS_BASE_URL}/api/v1/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "email": "u@example.com",
                "teams": [
                    {
                        "id": "t-shared",
                        "name": "Shared",
                        "role": "member",
                        "is_private_teamspace": False,
                    }
                ],
            },
        )
    )

    with caplog.at_level(logging.WARNING, logger="specify_cli.sync._team"):
        mock_post = flush_some_events(token_manager_with_shared_only_session, monkeypatch)

    assert mock_post.call_count == 0
    assert any("direct_ingress_missing_private_team" in record.getMessage() for record in caplog.records)


@respx.mock
def test_batch_negative_cache_honored_across_calls(
    token_manager_with_shared_only_session: TokenManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NFR-001: at most one /api/v1/me GET per process for a shared-only session."""
    me_route = respx.get(f"{_INGRESS_SAAS_BASE_URL}/api/v1/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "email": "u@example.com",
                "teams": [
                    {
                        "id": "t-shared",
                        "name": "Shared",
                        "role": "member",
                        "is_private_teamspace": False,
                    }
                ],
            },
        )
    )

    flush_some_events(token_manager_with_shared_only_session, monkeypatch)
    flush_some_events(token_manager_with_shared_only_session, monkeypatch)
    flush_some_events(token_manager_with_shared_only_session, monkeypatch)

    assert me_route.call_count == 1


@respx.mock
def test_batch_healthy_session_no_rehydrate(
    token_manager_with_private_session: TokenManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario 1 regression: session with private team => no /api/v1/me call; batch goes through."""
    me_route = respx.get(f"{_INGRESS_SAAS_BASE_URL}/api/v1/me").mock(return_value=httpx.Response(200, json={}))

    mock_post = flush_some_events(token_manager_with_private_session, monkeypatch)

    assert me_route.call_count == 0
    assert mock_post.call_count == 1
    headers = mock_post.call_args.kwargs["headers"]
    assert headers["X-Team-Slug"] == "t-private"


@respx.mock
def test_sync_all_queued_events_terminates_on_no_private_team(
    token_manager_with_shared_only_session: TokenManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post-merge regression: sync_all_queued_events MUST NOT spin forever
    when the strict resolver returns None for every batch.

    Before the fix, batch_sync's skip path returned a result with
    success_count=0 and error_count=0, while leaving events in the queue.
    sync_all_queued_events looped while ``queue.size() > 0`` and only broke
    on ``error_count > 0``, so a shared-only session caused an infinite
    loop in ``spec-kitty sync now`` / ``_perform_full_sync``.

    The fix: batch_sync appends a sentinel error message on the skip path,
    and sync_all_queued_events breaks when ``success_count == 0`` regardless
    of error_count. This test pins both behaviours.
    """
    # /api/v1/me returns shared-only — strict resolver returns None.
    respx.get(f"{_INGRESS_SAAS_BASE_URL}/api/v1/me").mock(
        return_value=httpx.Response(
            200,
            json={
                "email": "u@example.com",
                "teams": [
                    {
                        "id": "t-shared",
                        "name": "Shared",
                        "role": "member",
                        "is_private_teamspace": False,
                    }
                ],
            },
        )
    )
    monkeypatch.setattr(
        "specify_cli.auth.get_token_manager",
        lambda: token_manager_with_shared_only_session,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "p1_regression_queue.db"
        queue = OfflineQueue(db_path)
        # Pre-fill the queue. If the loop spins forever, this many rows would
        # never drain (skip path leaves them in place).
        for i in range(5):
            queue.queue_event(
                {
                    "event_id": f"p1-evt-{i:04d}",
                    "event_type": "WPStatusChanged",
                    "aggregate_id": "WP",
                    "lamport_clock": i,
                    "node_id": "test-node",
                    "payload": {"index": i},
                }
            )

        with patch("specify_cli.sync.batch.requests.post") as mock_post:
            # If the loop did spin, mock_post would never fire (skip path
            # never sends an HTTP POST), and the test would hang on the
            # `while queue.size() > 0` loop. The fix terminates the loop
            # after the first batch's no-progress signal.
            result = sync_all_queued_events(
                queue=queue,
                auth_token="test-token",
                server_url="http://test.example.com",
                show_progress=False,
            )

        # Loop terminated — events stayed queued for a future drain after
        # the SaaS provisions a Private Teamspace.
        assert queue.size() == 5, "events must stay queued (no destructive skip)"
        # The skip path issued no batch POST.
        assert mock_post.call_count == 0
        # The skip-path sentinel surfaces on the result for operator-visible
        # diagnostics (also goes to stderr via the helper's structured
        # logger.warning, but operators reading the result get a hint too).
        assert any("Private Teamspace" in m for m in result.error_messages), f"expected skip-sentinel in error_messages, got {result.error_messages!r}"
