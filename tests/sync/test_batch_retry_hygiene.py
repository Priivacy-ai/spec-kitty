"""Regression tests for Mission 5 / issue Priivacy-ai/spec-kitty#889.

When a batch POST fails at the batch level (HTTP 401, 403, 5xx, transport
timeout/connection error) or the pre-flight skips because no Private
Teamspace is available, ``OfflineQueue.process_batch_results`` MUST NOT
increment ``retry_count`` for the drained queue rows. The server never
adjudicated those events individually, so a per-event retry attribution is
wrong and eventually poisons the queue.

Per-event 200-response content rejections still bump ``retry_count`` --
that path is unchanged.
"""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from specify_cli.auth.session import StoredSession, Team
from specify_cli.sync._team import CATEGORY_MISSING_PRIVATE_TEAM
from specify_cli.sync.batch import batch_sync
from specify_cli.sync.queue import OfflineQueue

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _default_private_team_token_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default TokenManager exposing a Private Teamspace.

    Mirrors the fixture in ``test_batch_sync.py`` so the pre-flight
    ``_current_team_slug`` resolution succeeds for the tests that exercise
    the network path. Tests that need the no-private-team scenario re-patch
    ``get_token_manager`` themselves.
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


@pytest.fixture(autouse=True)
def _enable_saas_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the SaaS-sync feature flag on for every test in this module."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")


@pytest.fixture
def small_queue():
    """OfflineQueue with 5 events, all retry_count=0."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "queue.db"
        queue = OfflineQueue(db_path)
        for i in range(5):
            queue.queue_event(
                {
                    "event_id": f"evt-{i:04d}",
                    "event_type": "WPStatusChanged",
                    "aggregate_id": f"WP{i:02d}",
                    "lamport_clock": i,
                    "node_id": "test-node",
                    "payload": {"index": i},
                }
            )
        yield queue


def _read_retry_counts(queue: OfflineQueue) -> dict[str, int]:
    """Read raw retry_count for every queue row keyed by event_id."""
    conn = sqlite3.connect(queue.db_path)
    try:
        cursor = conn.execute("SELECT event_id, retry_count FROM queue")
        return {row[0]: int(row[1]) for row in cursor}
    finally:
        conn.close()


def _build_response(status_code: int, body: dict[str, Any]) -> Mock:
    """Build a mock ``requests.Response`` with the given status + JSON body."""
    response = Mock()
    response.status_code = status_code
    response.json = Mock(return_value=body)
    response.text = ""
    return response


# ---------------------------------------------------------------------------
# Batch-level transient failures: retry_count MUST NOT advance
# ---------------------------------------------------------------------------


class TestRetryCountStableOnBatchLevelFailures:
    """Issue #889 regression suite."""

    @patch("specify_cli.sync.batch.requests.post")
    def test_http_401_does_not_bump_retry_count(
        self, mock_post: Mock, small_queue: OfflineQueue
    ) -> None:
        """Batch POST returns 401 -> retry_count stays at 0 for every event."""
        before = _read_retry_counts(small_queue)
        assert all(rc == 0 for rc in before.values())

        mock_post.return_value = _build_response(401, {"detail": "Unauthorized"})

        result = batch_sync(
            queue=small_queue,
            auth_token="bad-token",
            server_url="http://localhost:8000",
            show_progress=False,
        )

        after = _read_retry_counts(small_queue)
        assert after == before, "401 must not bump retry_count for any event"
        assert all(r.error_category == "auth_expired" for r in result.event_results)
        assert all(r.status == "failed_transient" for r in result.event_results)

    @patch("specify_cli.sync.batch.requests.post")
    def test_http_403_private_team_does_not_bump_retry_count(
        self, mock_post: Mock, small_queue: OfflineQueue
    ) -> None:
        """403 + private-team body -> retry_count untouched, category preserved."""
        before = _read_retry_counts(small_queue)

        mock_post.return_value = _build_response(
            403,
            {
                "category": CATEGORY_MISSING_PRIVATE_TEAM,
                "detail": "private teamspace required for direct ingress",
            },
        )

        result = batch_sync(
            queue=small_queue,
            auth_token="ok-token",
            server_url="http://localhost:8000",
            show_progress=False,
        )

        after = _read_retry_counts(small_queue)
        assert after == before
        assert all(
            r.error_category == CATEGORY_MISSING_PRIVATE_TEAM
            for r in result.event_results
        )
        assert all(r.status == "failed_transient" for r in result.event_results)

    @patch("specify_cli.sync.batch.requests.post")
    def test_http_403_generic_unauthorized_does_not_bump_retry_count(
        self, mock_post: Mock, small_queue: OfflineQueue
    ) -> None:
        """403 with generic forbidden body -> 'unauthorized' category, retry_count steady."""
        before = _read_retry_counts(small_queue)

        mock_post.return_value = _build_response(
            403, {"detail": "you do not have permission"}
        )

        result = batch_sync(
            queue=small_queue,
            auth_token="ok-token",
            server_url="http://localhost:8000",
            show_progress=False,
        )

        after = _read_retry_counts(small_queue)
        assert after == before
        assert all(r.error_category == "unauthorized" for r in result.event_results)
        assert all(r.status == "failed_transient" for r in result.event_results)

    @patch("specify_cli.sync.batch.requests.post")
    def test_http_500_does_not_bump_retry_count(
        self, mock_post: Mock, small_queue: OfflineQueue
    ) -> None:
        """5xx -> 'server_error' category, retry_count unchanged."""
        before = _read_retry_counts(small_queue)

        mock_post.return_value = _build_response(500, {"detail": "boom"})

        result = batch_sync(
            queue=small_queue,
            auth_token="ok-token",
            server_url="http://localhost:8000",
            show_progress=False,
        )

        after = _read_retry_counts(small_queue)
        assert after == before
        assert all(r.error_category == "server_error" for r in result.event_results)
        assert all(r.status == "failed_transient" for r in result.event_results)

    def test_preflight_no_private_team_does_not_bump_retry_count(
        self, small_queue: OfflineQueue, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Pre-flight: _current_team_slug returns None -> retry_count untouched."""
        before = _read_retry_counts(small_queue)

        # Force the pre-flight skip path explicitly. We patch the strict
        # private-team resolver inside ``_current_team_slug``.
        monkeypatch.setattr(
            "specify_cli.sync.batch.resolve_private_team_id_for_ingress",
            lambda *args, **kwargs: None,
        )

        result = batch_sync(
            queue=small_queue,
            auth_token="ok-token",
            server_url="http://localhost:8000",
            show_progress=False,
        )

        after = _read_retry_counts(small_queue)
        assert after == before, "pre-flight skip must not mutate retry_count"
        assert all(
            r.error_category == CATEGORY_MISSING_PRIVATE_TEAM
            for r in result.event_results
        )
        assert all(r.status == "failed_transient" for r in result.event_results)


# ---------------------------------------------------------------------------
# Per-event content rejection: retry_count still bumps (regression guard)
# ---------------------------------------------------------------------------


class TestRetryCountStillBumpsOnPerEventRejection:
    """Sanity: the 200-response per-event rejection path is unchanged."""

    @patch("specify_cli.sync.batch.requests.post")
    def test_per_event_rejection_still_bumps_retry_count(
        self, mock_post: Mock, small_queue: OfflineQueue
    ) -> None:
        """200 OK with one event marked rejected -> just that row gets retry_count=1."""
        before = _read_retry_counts(small_queue)
        # One event will be rejected by the server. Others succeed.
        target_event_id = "evt-0002"
        all_ids = sorted(before.keys())

        results_payload = []
        for event_id in all_ids:
            if event_id == target_event_id:
                results_payload.append(
                    {
                        "event_id": event_id,
                        "status": "rejected",
                        "error_message": "schema validation failed",
                    }
                )
            else:
                results_payload.append({"event_id": event_id, "status": "success"})

        mock_post.return_value = _build_response(200, {"results": results_payload})

        result = batch_sync(
            queue=small_queue,
            auth_token="ok-token",
            server_url="http://localhost:8000",
            show_progress=False,
        )

        # The successful events are deleted from the queue; only the rejected
        # row survives, with retry_count incremented to 1.
        after = _read_retry_counts(small_queue)
        assert target_event_id in after, "rejected row should still be present"
        assert after[target_event_id] == 1, (
            f"per-event rejection MUST bump retry_count; got {after[target_event_id]}"
        )
        # All other events were removed (synced).
        assert set(after.keys()) == {target_event_id}

        rejected_results = [r for r in result.event_results if r.status == "rejected"]
        assert len(rejected_results) == 1
        assert rejected_results[0].event_id == target_event_id
