"""Integration tests for ticket-first mission origin binding (WP06).

Unlike the unit tests in ``test_origin.py`` which mock the entire
``SaaSTrackerClient``, these tests mock ONLY at the ``httpx.Client``
boundary.  Real config loading, real metadata writes, real event
emission, and the real ``SaaSTrackerClient`` transport are exercised.

Covers:
- T031: End-to-end search -> confirm -> bind flow
- T032: start_mission_from_ticket full flow
- T033: Error propagation across layers
- T034: SaaS-first write ordering invariant (MOST CRITICAL)
- T035: Offline event queuing
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from specify_cli.tracker.origin import (
    OriginBindingError,
    bind_mission_origin,
    search_origin_candidates,
    start_mission_from_ticket,
)
from specify_cli.tracker.origin_models import (
    MissionFromTicketResult,
    OriginCandidate,
)
from specify_cli.tracker.saas_client import SaaSTrackerClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(
    status_code: int = 200,
    json_body: dict[str, Any] | None = None,
    *,
    text: str = "",
) -> httpx.Response:
    """Build a fake httpx.Response with the given status and JSON body."""
    resp = httpx.Response(
        status_code=status_code,
        request=httpx.Request("GET", "https://example.com"),
    )
    if json_body is not None:
        resp._content = json.dumps(json_body).encode()
        resp.headers["content-type"] = "application/json"
    elif text:
        resp._content = text.encode()
    else:
        resp._content = b""
    return resp


def _make_candidate(
    *,
    key: str = "WEB-123",
    issue_id: str = "issue-uuid-1",
    title: str = "Add Clerk auth",
    status: str = "In Progress",
    url: str = "https://linear.app/acme/issue/WEB-123/add-clerk-auth",
    match_type: str = "text",
) -> OriginCandidate:
    return OriginCandidate(
        external_issue_id=issue_id,
        external_issue_key=key,
        title=title,
        status=status,
        url=url,
        match_type=match_type,
    )


def _setup_mock_http(mock_http_cls: MagicMock) -> MagicMock:
    """Wire up the context-manager protocol on the mock httpx.Client class."""
    mock_http = MagicMock()
    mock_http_cls.return_value.__enter__ = MagicMock(return_value=mock_http)
    mock_http_cls.return_value.__exit__ = MagicMock(return_value=False)
    return mock_http


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo_with_tracker(tmp_path: Path) -> Path:
    """Create a repo with tracker binding configured."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    config_yaml = kittify / "config.yaml"
    config_yaml.write_text(
        "tracker:\n  provider: linear\n  project_slug: acme-web\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture()
def feature_dir_with_meta(repo_with_tracker: Path) -> Path:
    """Create a feature dir with valid meta.json."""
    feature_dir = repo_with_tracker / "kitty-specs" / "061-test-feature"
    feature_dir.mkdir(parents=True)
    meta: dict[str, Any] = {
        "mission_number": "061",
        "slug": "test-feature",
        "mission_slug": "061-test-feature",
        "mission_id": "01KNRQK0R1ZDS8Z57M1TRXF001",
        "friendly_name": "Test Feature",
        "mission_type": "software-dev",
        "target_branch": "main",
        "created_at": "2026-04-01T00:00:00+00:00",
    }
    (feature_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return feature_dir


@pytest.fixture()
def mock_client() -> SaaSTrackerClient:
    """SaaSTrackerClient with mocked credential store and config."""
    store = MagicMock()
    store.get_access_token.return_value = "test-token"
    store.get_team_slug.return_value = "team-acme"
    config = MagicMock()
    config.get_server_url.return_value = "https://saas.example.com"
    return SaaSTrackerClient(
        credential_store=store,
        sync_config=config,
        timeout=5.0,
    )


# ===========================================================================
# T031: End-to-end search -> confirm -> bind flow
# ===========================================================================


class TestSearchConfirmBindFlow:
    """Integration test wiring real service functions with httpx mock only."""

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_search_returns_candidates(
        self,
        mock_http_cls: MagicMock,
        repo_with_tracker: Path,
        mock_client: SaaSTrackerClient,
    ) -> None:
        """Search via real config loading + real SaaSTrackerClient transport."""
        mock_http = _setup_mock_http(mock_http_cls)
        mock_http.request.return_value = _make_response(
            200,
            {
                "candidates": [
                    {
                        "external_issue_id": "id-1",
                        "external_issue_key": "WEB-123",
                        "title": "Add Clerk auth",
                        "status": "In Progress",
                        "url": "https://linear.app/acme/WEB-123",
                        "match_type": "text",
                    },
                ],
                "resource_type": "linear_team",
                "resource_id": "team-uuid",
            },
        )

        result = search_origin_candidates(
            repo_with_tracker,
            query_text="Clerk auth",
            client=mock_client,
        )

        assert len(result.candidates) == 1
        assert result.candidates[0].external_issue_key == "WEB-123"
        assert result.provider == "linear"
        assert result.resource_type == "linear_team"

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_search_confirm_bind_full_flow(
        self,
        mock_http_cls: MagicMock,
        repo_with_tracker: Path,
        feature_dir_with_meta: Path,
        mock_client: SaaSTrackerClient,
    ) -> None:
        """Full happy path: search -> pick candidate -> bind -> verify meta."""
        mock_http = _setup_mock_http(mock_http_cls)

        # Search returns candidates
        search_response = _make_response(
            200,
            {
                "candidates": [
                    {
                        "external_issue_id": "id-1",
                        "external_issue_key": "WEB-123",
                        "title": "Add Clerk auth",
                        "status": "In Progress",
                        "url": "https://linear.app/acme/WEB-123",
                        "match_type": "text",
                    },
                ],
                "resource_type": "linear_team",
                "resource_id": "team-uuid",
            },
        )

        # Bind returns success
        bind_response = _make_response(
            200,
            {"origin_link_id": "link-1", "bound_at": "2026-04-01T00:00:00Z"},
        )

        # First call is search, second is bind
        mock_http.request.side_effect = [search_response, bind_response]

        # Step 1: Search
        result = search_origin_candidates(
            repo_with_tracker,
            query_text="Clerk auth",
            client=mock_client,
        )
        assert len(result.candidates) == 1
        candidate = result.candidates[0]

        # Step 2: Bind (patch event emission to avoid side effects)
        with patch("specify_cli.sync.events.get_emitter") as mock_get_emitter:
            mock_emitter = MagicMock()
            mock_get_emitter.return_value = mock_emitter

            meta, emitted = bind_mission_origin(
                feature_dir_with_meta,
                candidate,
                "linear",
                "linear_team",
                "team-uuid",
                client=mock_client,
            )

        # Step 3: Verify meta.json was written with all 7 required keys
        assert emitted is True
        assert "origin_ticket" in meta
        ot = meta["origin_ticket"]
        assert ot["provider"] == "linear"
        assert ot["resource_type"] == "linear_team"
        assert ot["resource_id"] == "team-uuid"
        assert ot["external_issue_id"] == "id-1"
        assert ot["external_issue_key"] == "WEB-123"
        assert ot["external_issue_url"] == "https://linear.app/acme/WEB-123"
        assert ot["title"] == "Add Clerk auth"

        # Step 4: Verify meta.json on disk matches
        disk_meta = json.loads(
            (feature_dir_with_meta / "meta.json").read_text(encoding="utf-8"),
        )
        assert disk_meta["origin_ticket"] == ot

        # Step 5: Verify event was emitted
        mock_emitter.emit_mission_origin_bound.assert_called_once()


# ===========================================================================
# T032: start_mission_from_ticket full flow
# ===========================================================================


class TestStartMissionFromTicket:
    """Integration test for the full orchestration function."""

    @patch("specify_cli.core.mission_creation.create_mission_core")
    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_full_flow_returns_result(
        self,
        mock_http_cls: MagicMock,
        mock_create: MagicMock,
        repo_with_tracker: Path,
        feature_dir_with_meta: Path,
        mock_client: SaaSTrackerClient,
    ) -> None:
        """Mock create_mission_core + httpx -> real bind -> result."""
        mock_http = _setup_mock_http(mock_http_cls)

        # create_mission_core returns a result pointing at our feature dir
        mock_create.return_value = MagicMock(
            feature_dir=feature_dir_with_meta,
            mission_slug="061-test-feature",
        )

        # Bind succeeds via httpx
        mock_http.request.return_value = _make_response(
            200,
            {"origin_link_id": "link-1", "bound_at": "2026-04-01T00:00:00Z"},
        )

        candidate = _make_candidate()

        with patch("specify_cli.sync.events.get_emitter") as mock_get_emitter:
            mock_emitter = MagicMock()
            mock_get_emitter.return_value = mock_emitter

            result = start_mission_from_ticket(
                repo_with_tracker,
                candidate,
                "linear",
                "linear_team",
                "team-uuid",
                client=mock_client,
            )

        assert isinstance(result, MissionFromTicketResult)
        assert result.mission_slug == "061-test-feature"
        assert result.event_emitted is True
        assert result.origin_ticket["provider"] == "linear"
        assert result.origin_ticket["external_issue_key"] == "WEB-123"

        # Verify meta.json on disk has origin_ticket
        disk_meta = json.loads(
            (feature_dir_with_meta / "meta.json").read_text(encoding="utf-8"),
        )
        assert "origin_ticket" in disk_meta

        # Verify create_mission_core was called with derived slug
        mock_create.assert_called_once_with(
            repo_with_tracker,
            "web-123",
            mission="software-dev",
            target_branch=None,
        )


# ===========================================================================
# T033: Error propagation across layers
# ===========================================================================


class TestErrorPropagation:
    """Verify errors from httpx propagate as OriginBindingError with
    user-actionable messages (not raw HTTP details)."""

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_401_search_propagates_as_origin_error(
        self,
        mock_http_cls: MagicMock,
        repo_with_tracker: Path,
        mock_client: SaaSTrackerClient,
    ) -> None:
        """HTTP 401 -> SaaSTrackerClientError -> OriginBindingError."""
        mock_http = _setup_mock_http(mock_http_cls)

        # Both attempts return 401 (after refresh)
        mock_http.request.side_effect = [
            _make_response(401, {"message": "Unauthorized"}),
            _make_response(401, {"message": "Unauthorized"}),
        ]

        with (
            patch("specify_cli.tracker.saas_client._force_refresh_sync"),
            pytest.raises(OriginBindingError, match="Session expired|login"),
        ):
            search_origin_candidates(
                repo_with_tracker,
                query_text="test",
                client=mock_client,
            )

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_409_bind_propagates_as_origin_error(
        self,
        mock_http_cls: MagicMock,
        feature_dir_with_meta: Path,
        mock_client: SaaSTrackerClient,
    ) -> None:
        """HTTP 409 -> SaaSTrackerClientError -> OriginBindingError with conflict message."""
        mock_http = _setup_mock_http(mock_http_cls)
        mock_http.request.return_value = _make_response(
            409,
            {
                "message": "Feature already bound to a different issue",
                "code": "origin_conflict",
            },
        )

        candidate = _make_candidate()

        with pytest.raises(
            OriginBindingError,
            match="already bound to a different issue",
        ):
            bind_mission_origin(
                feature_dir_with_meta,
                candidate,
                "linear",
                "linear_team",
                "team-uuid",
                client=mock_client,
            )

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_404_search_propagates_as_origin_error(
        self,
        mock_http_cls: MagicMock,
        repo_with_tracker: Path,
        mock_client: SaaSTrackerClient,
    ) -> None:
        """HTTP 404 -> SaaSTrackerClientError -> OriginBindingError."""
        mock_http = _setup_mock_http(mock_http_cls)
        mock_http.request.return_value = _make_response(
            404,
            {"message": "No mapping found for provider", "code": "no_mapping"},
        )

        with pytest.raises(OriginBindingError, match="No mapping found"):
            search_origin_candidates(
                repo_with_tracker,
                query_text="test",
                client=mock_client,
            )

    @patch("specify_cli.core.mission_creation.create_mission_core")
    def test_creation_failure_propagates(
        self,
        mock_create: MagicMock,
        repo_with_tracker: Path,
    ) -> None:
        """MissionCreationError -> OriginBindingError."""
        from specify_cli.core.mission_creation import MissionCreationError

        mock_create.side_effect = MissionCreationError(
            "Feature slug 'web-123' already exists",
        )
        candidate = _make_candidate()

        with pytest.raises(OriginBindingError, match="already exists"):
            start_mission_from_ticket(
                repo_with_tracker,
                candidate,
                "linear",
                "linear_team",
                "team-uuid",
            )


# ===========================================================================
# T034: SaaS-first write ordering invariant (MOST CRITICAL)
# ===========================================================================


class TestSaaSFirstWriteOrdering:
    """The most critical integration test: verify that local metadata
    is NEVER written when the SaaS bind call fails."""

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_500_does_not_write_local_meta(
        self,
        mock_http_cls: MagicMock,
        feature_dir_with_meta: Path,
        mock_client: SaaSTrackerClient,
    ) -> None:
        """HTTP 500 from SaaS -> meta.json must NOT have origin_ticket."""
        mock_http = _setup_mock_http(mock_http_cls)
        mock_http.request.return_value = _make_response(
            500,
            {"message": "Internal server error"},
        )

        candidate = _make_candidate()

        with pytest.raises(OriginBindingError):
            bind_mission_origin(
                feature_dir_with_meta,
                candidate,
                "linear",
                "linear_team",
                "team-uuid",
                client=mock_client,
            )

        # THE INVARIANT: meta.json must NOT have origin_ticket
        meta = json.loads(
            (feature_dir_with_meta / "meta.json").read_text(encoding="utf-8"),
        )
        assert "origin_ticket" not in meta

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_409_does_not_write_local_meta(
        self,
        mock_http_cls: MagicMock,
        feature_dir_with_meta: Path,
        mock_client: SaaSTrackerClient,
    ) -> None:
        """HTTP 409 conflict -> meta.json must NOT have origin_ticket."""
        mock_http = _setup_mock_http(mock_http_cls)
        mock_http.request.return_value = _make_response(
            409,
            {"message": "Feature already bound to a different issue"},
        )

        candidate = _make_candidate()

        with pytest.raises(OriginBindingError):
            bind_mission_origin(
                feature_dir_with_meta,
                candidate,
                "linear",
                "linear_team",
                "team-uuid",
                client=mock_client,
            )

        meta = json.loads(
            (feature_dir_with_meta / "meta.json").read_text(encoding="utf-8"),
        )
        assert "origin_ticket" not in meta

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_401_does_not_write_local_meta(
        self,
        mock_http_cls: MagicMock,
        feature_dir_with_meta: Path,
        mock_client: SaaSTrackerClient,
    ) -> None:
        """HTTP 401 expired session -> meta.json must NOT have origin_ticket."""
        mock_http = _setup_mock_http(mock_http_cls)
        # Both attempts return 401 (initial + after refresh)
        mock_http.request.side_effect = [
            _make_response(401, {"message": "Unauthorized"}),
            _make_response(401, {"message": "Unauthorized"}),
        ]

        candidate = _make_candidate()

        with (
            patch("specify_cli.tracker.saas_client._force_refresh_sync"),
            pytest.raises(OriginBindingError),
        ):
            bind_mission_origin(
                feature_dir_with_meta,
                candidate,
                "linear",
                "linear_team",
                "team-uuid",
                client=mock_client,
            )

        meta = json.loads(
            (feature_dir_with_meta / "meta.json").read_text(encoding="utf-8"),
        )
        assert "origin_ticket" not in meta

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_403_does_not_write_local_meta(
        self,
        mock_http_cls: MagicMock,
        feature_dir_with_meta: Path,
        mock_client: SaaSTrackerClient,
    ) -> None:
        """HTTP 403 forbidden -> meta.json must NOT have origin_ticket."""
        mock_http = _setup_mock_http(mock_http_cls)
        mock_http.request.return_value = _make_response(
            403,
            {"message": "Forbidden: insufficient permissions"},
        )

        candidate = _make_candidate()

        with pytest.raises(OriginBindingError):
            bind_mission_origin(
                feature_dir_with_meta,
                candidate,
                "linear",
                "linear_team",
                "team-uuid",
                client=mock_client,
            )

        meta = json.loads(
            (feature_dir_with_meta / "meta.json").read_text(encoding="utf-8"),
        )
        assert "origin_ticket" not in meta

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_422_does_not_write_local_meta(
        self,
        mock_http_cls: MagicMock,
        feature_dir_with_meta: Path,
        mock_client: SaaSTrackerClient,
    ) -> None:
        """HTTP 422 validation error -> meta.json must NOT have origin_ticket."""
        mock_http = _setup_mock_http(mock_http_cls)
        mock_http.request.return_value = _make_response(
            422,
            {"message": "Invalid payload", "code": "validation_error"},
        )

        candidate = _make_candidate()

        with pytest.raises(OriginBindingError):
            bind_mission_origin(
                feature_dir_with_meta,
                candidate,
                "linear",
                "linear_team",
                "team-uuid",
                client=mock_client,
            )

        meta = json.loads(
            (feature_dir_with_meta / "meta.json").read_text(encoding="utf-8"),
        )
        assert "origin_ticket" not in meta

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_meta_unchanged_byte_for_byte(
        self,
        mock_http_cls: MagicMock,
        feature_dir_with_meta: Path,
        mock_client: SaaSTrackerClient,
    ) -> None:
        """On SaaS failure, meta.json content is byte-for-byte identical."""
        meta_path = feature_dir_with_meta / "meta.json"
        original_bytes = meta_path.read_bytes()

        mock_http = _setup_mock_http(mock_http_cls)
        mock_http.request.return_value = _make_response(
            500,
            {"message": "Internal server error"},
        )

        candidate = _make_candidate()

        with pytest.raises(OriginBindingError):
            bind_mission_origin(
                feature_dir_with_meta,
                candidate,
                "linear",
                "linear_team",
                "team-uuid",
                client=mock_client,
            )

        assert meta_path.read_bytes() == original_bytes


# ===========================================================================
# T035: Offline event queuing
# ===========================================================================


class TestOfflineEventQueuing:
    """Verify MissionOriginBound event reaches the offline queue."""

    @patch("specify_cli.tracker.saas_client.httpx.Client")
    def test_event_queued_when_no_websocket(
        self,
        mock_http_cls: MagicMock,
        feature_dir_with_meta: Path,
        mock_client: SaaSTrackerClient,
        tmp_path: Path,
    ) -> None:
        """Bind succeeds -> MissionOriginBound queued in OfflineQueue."""
        mock_http = _setup_mock_http(mock_http_cls)
        mock_http.request.return_value = _make_response(
            200,
            {"origin_link_id": "link-1", "bound_at": "2026-04-01T00:00:00Z"},
        )

        candidate = _make_candidate()

        # Create an EventEmitter with a real OfflineQueue (temp DB)
        # but no WebSocket (offline mode)
        from specify_cli.sync.emitter import EventEmitter
        from specify_cli.sync.queue import OfflineQueue

        db_path = tmp_path / "test_queue.db"
        queue = OfflineQueue(db_path=db_path)

        emitter = EventEmitter(
            queue=queue,
            ws_client=None,  # No WebSocket = offline mode
        )

        with patch("specify_cli.sync.events.get_emitter", return_value=emitter):
            bind_mission_origin(
                feature_dir_with_meta,
                candidate,
                "linear",
                "linear_team",
                "team-uuid",
                client=mock_client,
            )

        # Drain the queue and check the event
        events = queue.drain_queue(limit=100)
        origin_events = [e for e in events if e.get("event_type") == "MissionOriginBound"]
        assert len(origin_events) >= 1, f"Expected MissionOriginBound event in queue, got: {[e.get('event_type') for e in events]}"

        event = origin_events[0]
        payload = event["payload"]
        assert payload["mission_slug"] == "061-test-feature"
        assert payload["provider"] == "linear"
        assert payload["external_issue_id"] == "issue-uuid-1"
        assert payload["external_issue_key"] == "WEB-123"
        assert payload["external_issue_url"] == ("https://linear.app/acme/issue/WEB-123/add-clerk-auth")
        assert payload["title"] == "Add Clerk auth"
