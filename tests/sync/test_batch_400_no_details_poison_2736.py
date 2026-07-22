"""Regression tests for Priivacy-ai/spec-kitty#2736 (WP04 / T015-T016).

A whole-batch HTTP 400 whose body carries a top-level ``error`` but **no
per-event ``details``** means the server rejected the *request* without
adjudicating individual events. In that case the offline queue MUST NOT
mark every drained event ``rejected`` (which bumps ``retry_count`` on every
innocent event via ``process_batch_results``). Such a batch-level 400 is a
transient failure -- mirror the sibling 401/403/5xx branches, which record
``failed_transient`` and leave ``retry_count`` untouched (issue #889).

The complementary path -- a 400 **with** structured per-event ``details`` --
is a genuine server-adjudicated per-event rejection and MUST stay intact:
the named events are rejected with their per-event reasons and their
``retry_count`` is bumped.
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
from specify_cli.sync.batch import batch_sync
from specify_cli.sync.queue import OfflineQueue

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Fixtures (mirrors test_batch_retry_hygiene.py so the pre-flight succeeds)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _default_private_team_token_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default TokenManager exposing a Private Teamspace for the pre-flight."""
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
def mixed_queue():
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
# T015: the live whole-batch-400 no-details poison
# ---------------------------------------------------------------------------


class TestWholeBatch400NoDetailsIsTransient:
    """#2736: a batch-level 400 with no per-event details is transient."""

    @patch("specify_cli.sync.batch.requests.post")
    def test_no_details_400_does_not_reject_or_bump_innocents(
        self, mock_post: Mock, mixed_queue: OfflineQueue
    ) -> None:
        """400 with only a top-level ``error`` -> no ``rejected``, no retry bump."""
        before = _read_retry_counts(mixed_queue)
        assert all(rc == 0 for rc in before.values())

        # Whole-batch 400: the server refused the request without naming
        # any individual event (no ``details`` key at all).
        mock_post.return_value = _build_response(
            400, {"error": "Bad request payload"}
        )

        result = batch_sync(
            queue=mixed_queue,
            auth_token="ok-token",
            server_url="http://localhost:8000",
            show_progress=False,
        )

        # No innocent event may be stamped ``rejected``.
        assert not any(r.status == "rejected" for r in result.event_results), (
            "a no-details batch-level 400 must not reject any event"
        )
        assert all(r.status == "failed_transient" for r in result.event_results)

        # retry_count must be untouched for every drained row.
        after = _read_retry_counts(mixed_queue)
        assert after == before, (
            "no-details batch-level 400 must not bump retry_count for any event"
        )

        # The operator-facing error summary is still surfaced.
        assert result.error_messages
        assert any("Bad request payload" in m for m in result.error_messages)


# ---------------------------------------------------------------------------
# T015 second assertion: the adjudicated per-event details path stays intact
# ---------------------------------------------------------------------------


class TestWholeBatch400WithDetailsStillRejects:
    """Regression guard: server-adjudicated per-event 400 is unchanged."""

    @patch("specify_cli.sync.batch.requests.post")
    def test_details_400_rejects_named_events_and_bumps_retry(
        self, mock_post: Mock, mixed_queue: OfflineQueue
    ) -> None:
        """400 with per-event ``details`` -> named events rejected + retry bumped."""
        before = _read_retry_counts(mixed_queue)

        # Server adjudicated every event and returned per-event reasons. Each
        # event is named with its own detail so the adjudicated path surfaces
        # per-event reasons rather than collapsing to the outer error.
        reasons = {
            "evt-0000": "schema validation failed",
            "evt-0001": "aggregate_id missing",
            "evt-0002": "lamport_clock out of range",
            "evt-0003": "unknown event_type",
            "evt-0004": "payload too large",
        }
        details = [
            {"event_id": eid, "detail": reason} for eid, reason in reasons.items()
        ]
        mock_post.return_value = _build_response(
            400, {"error": "Bad request", "details": details}
        )

        result = batch_sync(
            queue=mixed_queue,
            auth_token="ok-token",
            server_url="http://localhost:8000",
            show_progress=False,
        )

        by_id = {r.event_id: r for r in result.event_results}

        # Exactly the named events are rejected with their per-event reasons
        # (the adjudicated ``details`` path at batch.py:923-966 is intact).
        assert set(by_id) == set(reasons)
        for eid, reason in reasons.items():
            assert by_id[eid].status == "rejected"
            assert by_id[eid].error == reason

        # Every rejected row survives with retry_count bumped to 1.
        after = _read_retry_counts(mixed_queue)
        assert set(after) == set(reasons), "rejected rows must not be deleted"
        for eid in reasons:
            assert after[eid] == before[eid] + 1
