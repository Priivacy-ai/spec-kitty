"""Tests for EventEmitter and event builders (T036).

Covers:
- Singleton pattern (get_emitter / reset_emitter)
- All 8 event type builders
- ULID event IDs
- Lamport clock increments
- Validation (payload, envelope)
- team_slug inclusion (SC-010)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast

# Test ULID for mission_id (mandatory parameter on emitter methods).
_TEST_MISSION_ID = "01KNRQK0R1ZDS8Z57M1TRXF001"


from specify_cli.sync.emitter import (
    EventEmitter,
    _ULID_PATTERN,
    _load_contract_schema,
)
from specify_cli.sync.events import (
    get_emitter,
    reset_emitter,
    emit_wp_status_changed,
    emit_wp_created,
    emit_wp_assigned,
    emit_mission_created,
    emit_mission_closed,
    emit_history_added,
    emit_error_logged,
    emit_dependency_resolved,
)


class TestSingleton:
    """Test get_emitter() singleton pattern."""

    def setup_method(self):
        reset_emitter()

    def teardown_method(self):
        reset_emitter()

    @patch("specify_cli.sync.emitter.LamportClock.load")
    @patch("specify_cli.sync.emitter.OfflineQueue")
    @patch("specify_cli.sync.emitter.SyncConfig")
    @patch("specify_cli.sync.runtime.get_runtime")
    def test_get_emitter_returns_same_instance(self, _runtime, _cfg, _queue, _clock):
        """get_emitter() returns same instance on repeated calls."""
        e1 = get_emitter()
        e2 = get_emitter()
        assert e1 is e2

    @patch("specify_cli.sync.emitter.LamportClock.load")
    @patch("specify_cli.sync.emitter.OfflineQueue")
    @patch("specify_cli.sync.emitter.SyncConfig")
    @patch("specify_cli.sync.runtime.get_runtime")
    def test_reset_emitter_clears_singleton(self, _runtime, _cfg, _queue, _clock):
        """reset_emitter() allows new instance creation."""
        e1 = get_emitter()
        reset_emitter()
        e2 = get_emitter()
        assert e1 is not e2

    @patch("specify_cli.sync.emitter.LamportClock.load")
    @patch("specify_cli.sync.emitter.OfflineQueue")
    @patch("specify_cli.sync.emitter.SyncConfig")
    @patch("specify_cli.sync.runtime.get_runtime")
    def test_get_emitter_attaches_runtime(self, mock_get_runtime, _cfg, _queue, _clock):
        """get_emitter() attaches the singleton emitter to the sync runtime."""
        runtime = MagicMock()
        mock_get_runtime.return_value = runtime

        emitter = get_emitter()

        runtime.attach_emitter.assert_called_once_with(emitter)


class TestEventEnvelope:
    """Test common envelope fields across all events."""

    def test_event_id_is_valid_ulid(self, emitter: EventEmitter, temp_queue):
        """Event ID is a 26-character ULID (SC-009 prerequisite)."""
        event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is not None
        assert len(event["event_id"]) == 26
        assert _ULID_PATTERN.match(event["event_id"])

    def test_lamport_clock_increments(self, emitter: EventEmitter, temp_queue):
        """Lamport clock increments on each emit (SC-009)."""
        ev1 = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        ev2 = emitter.emit_wp_status_changed("WP02", "planned", "in_progress")
        assert ev1 is not None and ev2 is not None
        assert ev2["lamport_clock"] > ev1["lamport_clock"]

    def test_lamport_clock_starts_at_one(self, emitter: EventEmitter, temp_queue):
        """First event gets lamport_clock=1 (tick from 0)."""
        event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is not None
        assert event["lamport_clock"] == 1

    def test_node_id_present(self, emitter: EventEmitter, temp_queue):
        """Event includes node_id from clock."""
        event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is not None
        assert event["node_id"] == "test-node-id"

    def test_timestamp_is_iso8601(self, emitter: EventEmitter, temp_queue):
        """Event includes ISO 8601 timestamp."""
        event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is not None
        # Should contain T and timezone info
        assert "T" in event["timestamp"]

    def test_team_slug_from_auth(self, emitter: EventEmitter, temp_queue):
        """Event includes team_slug from AuthClient (SC-010)."""
        event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is not None
        assert event["team_slug"] == "test-team"

    def test_team_slug_defaults_to_local(
        self, temp_queue, temp_clock, mock_config, monkeypatch
    ):
        """team_slug defaults to 'local' when auth is unavailable (SC-010)."""

        def _boom():
            raise RuntimeError("Not authenticated")

        monkeypatch.setattr("specify_cli.auth.get_token_manager", _boom)
        em = EventEmitter(
            clock=temp_clock,
            config=mock_config,
            queue=temp_queue,
            ws_client=None,
        )
        event = em.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is not None
        assert event["team_slug"] == "local"

    def test_causation_id_included_when_provided(self, emitter: EventEmitter, temp_queue):
        """causation_id passed through to event envelope."""
        cid = emitter.generate_causation_id()
        event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress", causation_id=cid)
        assert event is not None
        assert event["causation_id"] == cid

    def test_causation_id_none_by_default(self, emitter: EventEmitter, temp_queue):
        """causation_id is None when not provided."""
        event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is not None
        assert event["causation_id"] is None

    def test_git_branch_present(self, emitter: EventEmitter, temp_queue):
        """Event includes git_branch from resolver."""
        event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is not None
        assert "git_branch" in event
        assert event["git_branch"] == "test-branch"

    def test_head_commit_sha_present(self, emitter: EventEmitter, temp_queue):
        """Event includes head_commit_sha from resolver."""
        event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is not None
        assert "head_commit_sha" in event
        assert event["head_commit_sha"] == "a" * 40

    def test_repo_slug_present(self, emitter: EventEmitter, temp_queue):
        """Event includes repo_slug from resolver."""
        event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is not None
        assert "repo_slug" in event
        assert event["repo_slug"] == "test-org/test-repo"

    def test_git_metadata_present_across_event_types(self, emitter: EventEmitter, temp_queue):
        """All event types include git metadata fields."""
        events = [
            emitter.emit_build_registered(),
            emitter.emit_wp_status_changed("WP01", "planned", "in_progress"),
            emitter.emit_wp_created("WP01", "Test", "033-test"),
            emitter.emit_mission_created("033-test", _TEST_MISSION_ID, 33, "2.x", 1),
        ]
        for event in events:
            assert event is not None
            assert "git_branch" in event
            assert "head_commit_sha" in event
            assert "repo_slug" in event


class TestBuildLifecycle:
    """Test build registration and heartbeat event emission."""

    def test_build_registered_emission(self, emitter: EventEmitter, temp_queue):
        """BuildRegistered includes build/project/git identity in payload."""
        event = emitter.emit_build_registered()
        assert event is not None
        assert event["event_type"] == "BuildRegistered"
        assert event["aggregate_type"] == "Build"
        assert event["aggregate_id"] == "test-build-id-0000-0000-000000000001"
        assert event["payload"]["build_id"] == "test-build-id-0000-0000-000000000001"
        assert event["payload"]["project_slug"] == "test-project"
        assert event["payload"]["project_name"] == "test-project"
        assert event["payload"]["repo_slug"] == "test-org/test-repo"
        assert event["payload"]["branch"] == "test-branch"
        assert event["payload"]["head_commit"] == "a" * 40
        assert event["payload"]["developer_name"] == "Test User"

    def test_build_heartbeat_emission(self, emitter: EventEmitter, temp_queue):
        """BuildHeartbeat carries remote-state deltas when provided."""
        event = emitter.emit_build_heartbeat(
            remote_head="b" * 40,
            ahead_of_remote=2,
            behind_remote=0,
            recent_commits=["c" * 40],
        )
        assert event is not None
        assert event["event_type"] == "BuildHeartbeat"
        assert event["aggregate_type"] == "Build"
        assert event["payload"]["remote_head"] == "b" * 40
        assert event["payload"]["ahead_of_remote"] == 2
        assert event["payload"]["behind_remote"] == 0
        assert event["payload"]["recent_commits"] == ["c" * 40]


class TestWPStatusChanged:
    """Test emit_wp_status_changed (SC-001, SC-002, SC-003)."""

    def test_basic_emission(self, emitter: EventEmitter, temp_queue):
        """WPStatusChanged event has correct structure."""
        event = emitter.emit_wp_status_changed(
            wp_id="WP01",
            from_lane="planned",
            to_lane="in_progress",
        )
        assert event is not None
        assert event["event_type"] == "WPStatusChanged"
        assert event["aggregate_id"] == "WP01"
        assert event["aggregate_type"] == "WorkPackage"
        assert event["from_lane"] == "planned"
        assert event["to_lane"] == "in_progress"
        assert event["actor"] == "user"
        assert event["payload"]["wp_id"] == "WP01"
        assert event["payload"]["from_lane"] == "planned"
        assert event["payload"]["to_lane"] == "in_progress"

    def test_actor_default(self, emitter: EventEmitter, temp_queue):
        """actor defaults to 'user'."""
        event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is not None
        assert event["payload"]["actor"] == "user"

    def test_actor_agent(self, emitter: EventEmitter, temp_queue):
        """actor can be set to agent name."""
        event = emitter.emit_wp_status_changed(
            "WP01",
            "planned",
            "in_progress",
            actor="claude-opus",
        )
        assert event is not None
        assert event["payload"]["actor"] == "claude-opus"

    def test_mission_slug_optional(self, emitter: EventEmitter, temp_queue):
        """mission_slug is optional and nullable."""
        event = emitter.emit_wp_status_changed(
            "WP01",
            "planned",
            "in_progress",
            mission_slug="028-sync",
        )
        assert event is not None
        assert event["payload"]["mission_slug"] == "028-sync"

    def test_queued_in_offline_queue(self, emitter: EventEmitter, temp_queue):
        """Event is queued when no WebSocket connected (SC-006)."""
        emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert temp_queue.size() == 1

    def test_all_valid_status_transitions(self, emitter: EventEmitter, temp_queue):
        """All canonical lane values pass validation."""
        lanes = ["planned", "claimed", "in_progress", "for_review", "approved", "done", "blocked", "canceled"]
        for lane in lanes:
            event = emitter.emit_wp_status_changed("WP01", "planned", lane)
            assert event is not None, f"Failed for to_lane={lane}"


class TestWPCreated:
    """Test emit_wp_created."""

    def test_basic_emission(self, emitter: EventEmitter, temp_queue):
        """WPCreated event has correct structure."""
        event = emitter.emit_wp_created(
            wp_id="WP01",
            title="Implement sync",
            mission_slug="028-sync",
        )
        assert event is not None
        assert event["event_type"] == "WPCreated"
        assert event["aggregate_type"] == "WorkPackage"
        assert event["payload"]["wp_id"] == "WP01"
        assert event["payload"]["title"] == "Implement sync"
        assert event["payload"]["mission_slug"] == "028-sync"

    def test_dependencies_default_empty(self, emitter: EventEmitter, temp_queue):
        """Dependencies defaults to empty list."""
        event = emitter.emit_wp_created("WP01", "Title", "028-sync")
        assert event is not None
        assert event["payload"]["dependencies"] == []

    def test_dependencies_list(self, emitter: EventEmitter, temp_queue):
        """Dependencies can be a list of WP IDs."""
        event = emitter.emit_wp_created(
            "WP02",
            "Title",
            "028-sync",
            dependencies=["WP01"],
        )
        assert event is not None
        assert event["payload"]["dependencies"] == ["WP01"]


class TestWPAssigned:
    """Test emit_wp_assigned (SC-005)."""

    def test_basic_emission(self, emitter: EventEmitter, temp_queue):
        """WPAssigned event has correct structure."""
        event = emitter.emit_wp_assigned(
            wp_id="WP01",
            agent_id="claude-opus",
            phase="implementation",
        )
        assert event is not None
        assert event["event_type"] == "WPAssigned"
        assert event["payload"]["wp_id"] == "WP01"
        assert event["payload"]["agent_id"] == "claude-opus"
        assert event["payload"]["phase"] == "implementation"

    def test_retry_count_default(self, emitter: EventEmitter, temp_queue):
        """retry_count defaults to 0."""
        event = emitter.emit_wp_assigned("WP01", "agent", "implementation")
        assert event is not None
        assert event["payload"]["retry_count"] == 0

    def test_retry_count_custom(self, emitter: EventEmitter, temp_queue):
        """retry_count can be set."""
        event = emitter.emit_wp_assigned("WP01", "agent", "review", retry_count=2)
        assert event is not None
        assert event["payload"]["retry_count"] == 2

    def test_review_phase(self, emitter: EventEmitter, temp_queue):
        """Phase 'review' is valid."""
        event = emitter.emit_wp_assigned("WP01", "agent", "review")
        assert event is not None
        assert event["payload"]["phase"] == "review"


class TestMissionCreated:
    """Test emit_mission_created (SC-004)."""

    def test_basic_emission(self, emitter: EventEmitter, temp_queue):
        """MissionCreated event has correct structure."""
        event = emitter.emit_mission_created(
            mission_slug="028-cli-event-emission-sync",
            mission_id=_TEST_MISSION_ID,
            mission_number=28,  # int, not str (FR-044, WP02)
            target_branch="main",
            wp_count=7,
        )
        assert event is not None
        assert event["event_type"] == "MissionCreated"
        assert event["aggregate_type"] == "Mission"
        assert event["aggregate_id"] == _TEST_MISSION_ID
        assert event["payload"]["wp_count"] == 7

    def test_created_at_optional(self, emitter: EventEmitter, temp_queue):
        """created_at is optional."""
        event = emitter.emit_mission_created(
            "028-sync",
            _TEST_MISSION_ID,
            28,  # int, not str (FR-044, WP02)
            "main",
            5,
            created_at="2026-02-04T12:00:00+00:00",
        )
        assert event is not None
        assert event["payload"]["created_at"] == "2026-02-04T12:00:00+00:00"


class TestMissionClosed:
    """Test emit_mission_closed."""

    def test_basic_emission(self, emitter: EventEmitter, temp_queue):
        """MissionClosed event has correct structure."""
        event = emitter.emit_mission_closed(
            mission_slug="028-sync",
            mission_id=_TEST_MISSION_ID,
            total_wps=7,
        )
        assert event is not None
        assert event["event_type"] == "MissionClosed"
        assert event["aggregate_type"] == "Mission"
        assert event["aggregate_id"] == _TEST_MISSION_ID
        assert event["payload"]["total_wps"] == 7

    def test_optional_fields(self, emitter: EventEmitter, temp_queue):
        """completed_at and total_duration are optional."""
        event = emitter.emit_mission_closed(
            "028-sync",
            _TEST_MISSION_ID,
            7,
            completed_at="2026-02-04T18:00:00+00:00",
            total_duration="6h",
        )
        assert event is not None
        assert event["payload"]["completed_at"] == "2026-02-04T18:00:00+00:00"
        assert event["payload"]["total_duration"] == "6h"


class TestHistoryAdded:
    """Test emit_history_added."""

    def test_basic_emission(self, emitter: EventEmitter, temp_queue):
        """HistoryAdded event has correct structure."""
        event = emitter.emit_history_added(
            wp_id="WP01",
            entry_type="note",
            entry_content="Started implementation",
        )
        assert event is not None
        assert event["event_type"] == "HistoryAdded"
        assert event["payload"]["entry_type"] == "note"
        assert event["payload"]["entry_content"] == "Started implementation"

    def test_author_default(self, emitter: EventEmitter, temp_queue):
        """author defaults to 'user'."""
        event = emitter.emit_history_added("WP01", "note", "content")
        assert event is not None
        assert event["payload"]["author"] == "user"

    def test_all_entry_types(self, emitter: EventEmitter, temp_queue):
        """All entry types pass validation."""
        for entry_type in ["note", "review", "error", "comment"]:
            event = emitter.emit_history_added("WP01", entry_type, "content")
            assert event is not None, f"Failed for entry_type={entry_type}"


class TestErrorLogged:
    """Test emit_error_logged (SC-011)."""

    def test_basic_emission(self, emitter: EventEmitter, temp_queue):
        """ErrorLogged event has correct structure."""
        event = emitter.emit_error_logged(
            error_type="runtime",
            error_message="Something broke",
        )
        assert event is not None
        assert event["event_type"] == "ErrorLogged"
        assert event["payload"]["error_type"] == "runtime"
        assert event["payload"]["error_message"] == "Something broke"

    def test_aggregate_id_uses_wp_id(self, emitter: EventEmitter, temp_queue):
        """aggregate_id is wp_id when provided."""
        event = emitter.emit_error_logged(
            "runtime",
            "error",
            wp_id="WP01",
        )
        assert event is not None
        assert event["aggregate_id"] == "WP01"
        assert event["aggregate_type"] == "WorkPackage"

    def test_aggregate_id_fallback(self, emitter: EventEmitter, temp_queue):
        """aggregate_id is 'error' when no wp_id."""
        event = emitter.emit_error_logged("runtime", "error")
        assert event is not None
        assert event["aggregate_id"] == "error"
        assert event["aggregate_type"] == "Mission"

    def test_optional_fields(self, emitter: EventEmitter, temp_queue):
        """stack_trace and agent_id are optional."""
        event = emitter.emit_error_logged(
            "network",
            "timeout",
            wp_id="WP01",
            stack_trace="Traceback...",
            agent_id="claude",
        )
        assert event is not None
        assert event["payload"]["stack_trace"] == "Traceback..."
        assert event["payload"]["agent_id"] == "claude"

    def test_all_error_types(self, emitter: EventEmitter, temp_queue):
        """All error types pass validation."""
        for error_type in ["validation", "runtime", "network", "auth", "unknown"]:
            event = emitter.emit_error_logged(error_type, "msg")
            assert event is not None, f"Failed for error_type={error_type}"


class TestDependencyResolved:
    """Test emit_dependency_resolved (SC-012)."""

    def test_basic_emission(self, emitter: EventEmitter, temp_queue):
        """DependencyResolved event has correct structure."""
        event = emitter.emit_dependency_resolved(
            wp_id="WP02",
            dependency_wp_id="WP01",
            resolution_type="completed",
        )
        assert event is not None
        assert event["event_type"] == "DependencyResolved"
        assert event["payload"]["wp_id"] == "WP02"
        assert event["payload"]["dependency_wp_id"] == "WP01"
        assert event["payload"]["resolution_type"] == "completed"

    def test_all_resolution_types(self, emitter: EventEmitter, temp_queue):
        """All resolution types pass validation."""
        for rtype in ["completed", "skipped", "merged"]:
            event = emitter.emit_dependency_resolved("WP02", "WP01", rtype)
            assert event is not None, f"Failed for resolution_type={rtype}"


class TestValidation:
    """Test event validation failures."""

    def test_invalid_wp_id_returns_none(self, emitter: EventEmitter, temp_queue):
        """Invalid wp_id format causes validation failure."""
        event = emitter.emit_wp_status_changed("INVALID", "planned", "in_progress")
        assert event is None

    def test_invalid_status_returns_none(self, emitter: EventEmitter, temp_queue):
        """Invalid status value causes validation failure."""
        event = emitter.emit_wp_status_changed("WP01", "planned", "invalid")
        assert event is None

    def test_invalid_phase_returns_none(self, emitter: EventEmitter, temp_queue):
        """Invalid phase value causes validation failure."""
        event = emitter.emit_wp_assigned("WP01", "agent", "invalid_phase")
        assert event is None

    def test_invalid_error_type_returns_none(self, emitter: EventEmitter, temp_queue):
        """Invalid error_type causes validation failure."""
        event = emitter.emit_error_logged("bogus", "message")
        assert event is None

    def test_empty_title_returns_none(self, emitter: EventEmitter, temp_queue):
        """Empty title for WPCreated causes validation failure."""
        event = emitter.emit_wp_created("WP01", "", "028-sync")
        assert event is None

    def test_invalid_mission_slug_returns_none(self, emitter: EventEmitter, temp_queue):
        """Invalid mission_slug format for MissionCreated causes validation failure."""
        event = emitter.emit_mission_created("NoNumbers", _TEST_MISSION_ID, 1, "main", 5)
        assert event is None

    def test_invalid_resolution_type_returns_none(self, emitter: EventEmitter, temp_queue):
        """Invalid resolution_type causes validation failure."""
        event = emitter.emit_dependency_resolved("WP02", "WP01", "invalid")
        assert event is None

    def test_invalid_entry_type_returns_none(self, emitter: EventEmitter, temp_queue):
        """Invalid entry_type causes validation failure."""
        event = emitter.emit_history_added("WP01", "invalid_type", "content")
        assert event is None

    def test_negative_wp_count_returns_none(self, emitter: EventEmitter, temp_queue):
        """Negative wp_count for MissionCreated causes validation failure."""
        event = emitter.emit_mission_created("028-sync", _TEST_MISSION_ID, 28, "main", -1)
        assert event is None


class TestConvenienceFunctions:
    """Test module-level convenience functions delegate to singleton."""

    def setup_method(self):
        reset_emitter()

    def teardown_method(self):
        reset_emitter()

    @patch("specify_cli.sync.events.get_emitter")
    def test_emit_wp_status_changed_delegates(self, mock_get):
        """emit_wp_status_changed delegates to singleton."""
        mock_emitter = MagicMock()
        mock_emitter.emit_wp_status_changed.return_value = {"event_id": "evt-1"}
        mock_get.return_value = mock_emitter
        with (
            patch(
                "specify_cli.sync.events._ensure_dashboard_sync_daemon_for_active_project",
                return_value=Path("/tmp/project"),
            ) as mock_daemon,
            patch("specify_cli.sync.events._publish_event_via_sync_daemon") as mock_publish,
            patch("specify_cli.sync.events._request_dashboard_sync") as mock_trigger,
        ):
            emit_wp_status_changed("WP01", "planned", "in_progress")
        mock_daemon.assert_called_once_with()
        mock_publish.assert_called_once_with({"event_id": "evt-1"}, Path("/tmp/project"))
        mock_trigger.assert_called_once_with(Path("/tmp/project"))
        mock_emitter.emit_wp_status_changed.assert_called_once()

    @patch("specify_cli.sync.events.get_emitter")
    def test_emit_wp_created_delegates(self, mock_get):
        """emit_wp_created delegates to singleton."""
        mock_emitter = MagicMock()
        mock_get.return_value = mock_emitter
        emit_wp_created("WP01", "Title", "028-sync")
        mock_emitter.emit_wp_created.assert_called_once()

    @patch("specify_cli.sync.events.get_emitter")
    def test_emit_wp_assigned_delegates(self, mock_get):
        """emit_wp_assigned delegates to singleton."""
        mock_emitter = MagicMock()
        mock_get.return_value = mock_emitter
        emit_wp_assigned("WP01", "agent", "implementation")
        mock_emitter.emit_wp_assigned.assert_called_once()

    @patch("specify_cli.sync.events.get_emitter")
    def test_emit_mission_created_delegates(self, mock_get):
        """emit_mission_created delegates to singleton."""
        mock_emitter = MagicMock()
        mock_get.return_value = mock_emitter
        emit_mission_created("028-sync", _TEST_MISSION_ID, "028", "main", 5)
        mock_emitter.emit_mission_created.assert_called_once()

    @patch("specify_cli.sync.events.get_emitter")
    def test_emit_mission_closed_delegates(self, mock_get):
        """emit_mission_closed delegates to singleton."""
        mock_emitter = MagicMock()
        mock_get.return_value = mock_emitter
        emit_mission_closed("028-sync", _TEST_MISSION_ID, 5)
        mock_emitter.emit_mission_closed.assert_called_once()

    @patch("specify_cli.sync.events.get_emitter")
    def test_emit_history_added_delegates(self, mock_get):
        """emit_history_added delegates to singleton."""
        mock_emitter = MagicMock()
        mock_get.return_value = mock_emitter
        emit_history_added("WP01", "note", "content")
        mock_emitter.emit_history_added.assert_called_once()

    @patch("specify_cli.sync.events.get_emitter")
    def test_emit_error_logged_delegates(self, mock_get):
        """emit_error_logged delegates to singleton."""
        mock_emitter = MagicMock()
        mock_get.return_value = mock_emitter
        emit_error_logged("runtime", "error")
        mock_emitter.emit_error_logged.assert_called_once()

    @patch("specify_cli.sync.events.get_emitter")
    def test_emit_dependency_resolved_delegates(self, mock_get):
        """emit_dependency_resolved delegates to singleton."""
        mock_emitter = MagicMock()
        mock_get.return_value = mock_emitter
        emit_dependency_resolved("WP02", "WP01", "completed")
        mock_emitter.emit_dependency_resolved.assert_called_once()


class TestConnectionStatus:
    """Test get_connection_status."""

    def test_offline_when_no_ws_client(self, emitter: EventEmitter):
        """Returns 'Offline' when ws_client is None."""
        assert emitter.get_connection_status() == "Offline"

    def test_delegates_to_ws_client(self, emitter: EventEmitter):
        """Delegates to ws_client.get_status() when present."""
        mock_ws = MagicMock()
        mock_ws.get_status.return_value = "Connected"
        emitter.ws_client = mock_ws
        assert emitter.get_connection_status() == "Connected"


class TestCausationId:
    """Test causation_id generation."""

    def test_generate_causation_id_is_ulid(self, emitter: EventEmitter):
        """generate_causation_id returns a valid ULID."""
        cid = emitter.generate_causation_id()
        assert len(cid) == 26
        assert _ULID_PATTERN.match(cid)

    def test_causation_ids_are_unique(self, emitter: EventEmitter):
        """Each generated causation_id is unique."""
        ids = {emitter.generate_causation_id() for _ in range(100)}
        assert len(ids) == 100


class TestGitMetadataInEvents:
    """Test git metadata field behavior in emitted events."""

    def test_null_git_metadata(
        self, temp_queue, temp_clock, mock_config, mock_identity, mock_auth
    ):
        """Events still emit when git metadata is all None."""
        del mock_auth  # side-effect-only
        from specify_cli.sync.git_metadata import GitMetadata, GitMetadataResolver

        null_metadata = GitMetadata()  # All None
        null_resolver = MagicMock(spec=GitMetadataResolver)
        null_resolver.resolve.return_value = null_metadata

        em = EventEmitter(
            clock=temp_clock,
            config=mock_config,
            queue=temp_queue,
            ws_client=None,
            _identity=mock_identity,
            _git_resolver=null_resolver,
        )
        event = em.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is not None
        assert event["git_branch"] is None
        assert event["head_commit_sha"] is None
        assert event["repo_slug"] is None

    def test_partial_git_metadata(
        self, temp_queue, temp_clock, mock_config, mock_identity, mock_auth
    ):
        """Events emit with partial git metadata (branch but no repo slug)."""
        del mock_auth  # side-effect-only
        from specify_cli.sync.git_metadata import GitMetadata, GitMetadataResolver

        partial = GitMetadata(git_branch="main", head_commit_sha="a" * 40, repo_slug=None)
        resolver = MagicMock(spec=GitMetadataResolver)
        resolver.resolve.return_value = partial

        em = EventEmitter(
            clock=temp_clock,
            config=mock_config,
            queue=temp_queue,
            ws_client=None,
            _identity=mock_identity,
            _git_resolver=resolver,
        )
        event = em.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is not None
        assert event["git_branch"] == "main"
        assert event["head_commit_sha"] == "a" * 40
        assert event["repo_slug"] is None


class TestOfflineReplayCompatibility:
    """Test that events with and without git metadata can be queued and replayed."""

    def test_event_with_git_fields_queued(self, temp_queue):
        """Events with git metadata fields are stored in offline queue."""
        event = {
            "event_id": "01HQXYZ" + "A" * 19,
            "event_type": "WPStatusChanged",
            "aggregate_id": "WP01",
            "aggregate_type": "WorkPackage",
            "payload": {
                "wp_id": "WP01",
                "from_lane": "planned",
                "to_lane": "in_progress",
                "actor": "user",
                "mission_slug": None,
            },
            "timestamp": "2026-02-07T12:00:00+00:00",
            "node_id": "test123",
            "lamport_clock": 1,
            "causation_id": None,
            "team_slug": "test",
            "project_uuid": "550e8400-e29b-41d4-a716-446655440000",
            "project_slug": "test",
            "git_branch": "main",
            "head_commit_sha": "a" * 40,
            "repo_slug": "org/repo",
        }
        temp_queue.queue_event(event)
        events = temp_queue.drain_queue()
        assert len(events) == 1
        assert events[0]["git_branch"] == "main"
        assert events[0]["head_commit_sha"] == "a" * 40
        assert events[0]["repo_slug"] == "org/repo"

    def test_event_without_git_fields_still_works(self, temp_queue):
        """Pre-033 events without git fields can be queued/drained."""
        event = {
            "event_id": "01HQXYZ" + "B" * 19,
            "event_type": "WPStatusChanged",
            "aggregate_id": "WP01",
            "aggregate_type": "WorkPackage",
            "payload": {
                "wp_id": "WP01",
                "from_lane": "planned",
                "to_lane": "in_progress",
                "actor": "user",
                "mission_slug": None,
            },
            "timestamp": "2026-02-07T12:00:00+00:00",
            "node_id": "test123",
            "lamport_clock": 1,
            "causation_id": None,
            "team_slug": "test",
            "project_uuid": "550e8400-e29b-41d4-a716-446655440000",
            "project_slug": "test",
            # No git_branch, head_commit_sha, repo_slug
        }
        temp_queue.queue_event(event)
        events = temp_queue.drain_queue()
        assert len(events) == 1
        assert "git_branch" not in events[0]


class TestInternalValidation:
    """Test internal _validate_event paths for edge cases."""

    def test_invalid_aggregate_type_via_emit(self, emitter: EventEmitter, temp_queue):
        """Invalid aggregate_type causes validation failure."""
        event = emitter._emit(
            event_type="WPStatusChanged",
            aggregate_id="WP01",
            aggregate_type="InvalidType",  # not in VALID_AGGREGATE_TYPES
            payload={"wp_id": "WP01", "from_lane": "planned", "to_lane": "in_progress"},
        )
        assert event is None

    def test_invalid_causation_id_format(self, emitter: EventEmitter, temp_queue):
        """Non-ULID causation_id causes validation failure."""
        event = emitter.emit_wp_status_changed(
            "WP01",
            "planned",
            "in_progress",
            causation_id="not-a-ulid",  # too short, wrong format
        )
        assert event is None

    def test_created_at_non_datetime_validation(self, emitter: EventEmitter, temp_queue):
        """Invalid created_at datetime string fails MissionCreated validation."""
        event = emitter.emit_mission_created(
            "028-sync",
            _TEST_MISSION_ID,
            28,  # int, not str (FR-044, WP02)
            "main",
            5,
            created_at="not-a-date",
        )
        assert event is None

    def test_completed_at_non_datetime_validation(self, emitter: EventEmitter, temp_queue):
        """Invalid completed_at datetime string fails MissionClosed validation."""
        event = emitter.emit_mission_closed(
            "028-sync",
            _TEST_MISSION_ID,
            5,
            completed_at="not-a-date",
        )
        assert event is None

    def test_validation_exception_returns_none(
        self, temp_queue, temp_clock, mock_config, mock_auth
    ):
        """Exception during validation returns None."""
        mock_auth.is_authenticated = False

        em = EventEmitter(
            clock=temp_clock,
            config=mock_config,
            queue=temp_queue,
            ws_client=None,
        )

        # Monkey-patch _validate_event to raise
        em._validate_event = MagicMock(side_effect=Exception("boom"))

        event = em.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is None

    def test_emitter_constructs_without_auth_arg(
        self, temp_queue, temp_clock, mock_config, mock_auth
    ):
        """Post-WP08 EventEmitter no longer takes an ``_auth`` argument.

        The sync layer reaches for ``get_token_manager()`` internally; the
        mocked token manager installed by ``mock_auth`` provides the fake
        session state. This test documents the current contract.
        """
        del mock_auth  # side-effect-only
        em = EventEmitter(
            clock=temp_clock,
            config=mock_config,
            queue=temp_queue,
            ws_client=None,
        )
        # With the fake TokenManager providing "test-team", the emitter
        # should produce an event tagged with that slug.
        event = em.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is not None
        assert event["team_slug"] == "test-team"

    def test_missing_team_slug_fails_validation(self, emitter: EventEmitter, temp_queue):
        """Events missing team_slug are rejected."""
        event_id = emitter.generate_causation_id()
        event = {
            "event_id": event_id,
            "event_type": "WPStatusChanged",
            "aggregate_id": "WP01",
            "aggregate_type": "WorkPackage",
            "payload": {"wp_id": "WP01", "from_lane": "planned", "to_lane": "in_progress"},
            "node_id": "test-node-id",
            "lamport_clock": 1,
            "causation_id": None,
            "timestamp": "2026-02-04T12:00:00+00:00",
            "team_slug": "",
        }
        assert emitter._validate_event(event) is False

    def test_invalid_event_id_fails_validation(self, emitter: EventEmitter, temp_queue):
        """Invalid event_id causes validation failure."""
        event = {
            "event_id": "short",
            "event_type": "WPStatusChanged",
            "aggregate_id": "WP01",
            "aggregate_type": "WorkPackage",
            "payload": {"wp_id": "WP01", "from_lane": "planned", "to_lane": "in_progress"},
            "node_id": "test-node-id",
            "lamport_clock": 1,
            "causation_id": None,
            "timestamp": "2026-02-04T12:00:00+00:00",
            "team_slug": "test-team",
        }
        assert emitter._validate_event(event) is False

    def test_invalid_causation_id_fails_validation(self, emitter: EventEmitter, temp_queue):
        """Invalid causation_id format causes validation failure."""
        event = {
            "event_id": emitter.generate_causation_id(),
            "event_type": "WPStatusChanged",
            "aggregate_id": "WP01",
            "aggregate_type": "WorkPackage",
            "payload": {"wp_id": "WP01", "from_lane": "planned", "to_lane": "in_progress"},
            "node_id": "test-node-id",
            "lamport_clock": 1,
            "causation_id": "xyz",
            "timestamp": "2026-02-04T12:00:00+00:00",
            "team_slug": "test-team",
        }
        assert emitter._validate_event(event) is False

    def test_validate_payload_missing_required_fields(self, emitter: EventEmitter):
        """Missing required payload fields are rejected."""
        assert emitter._validate_payload("WPStatusChanged", {"wp_id": "WP01"}) is False

    def test_load_contract_schema_caches(self):
        """Schema loader returns cached data on subsequent calls."""
        schema1 = _load_contract_schema()
        schema2 = _load_contract_schema()
        assert schema1 == schema2


class TestRouteEvent:
    """Test _route_event behavior with WebSocket integration."""

    def test_ws_send_with_running_loop(
        self, emitter: EventEmitter, mock_auth: MagicMock
    ):
        """WebSocket send uses ensure_future when loop is running."""
        import asyncio

        mock_ws = MagicMock()
        mock_ws.connected = True
        mock_ws.send_event = MagicMock()
        emitter.ws_client = mock_ws
        mock_auth.is_authenticated = True
        emitter.queue = MagicMock()

        class DummyLoop:
            def is_running(self):
                return True

        ensured = []

        def fake_ensure_future(coro):
            ensured.append(coro)
            task = MagicMock()
            task.add_done_callback = MagicMock()
            return task

        event = {
            "event_id": emitter.generate_causation_id(),
            "event_type": "WPStatusChanged",
            "aggregate_id": "WP01",
            "aggregate_type": "WorkPackage",
            "payload": {"wp_id": "WP01", "from_lane": "planned", "to_lane": "in_progress"},
            "node_id": "test-node-id",
            "lamport_clock": 1,
            "causation_id": None,
            "timestamp": "2026-02-04T12:00:00+00:00",
            "team_slug": "test-team",
        }

        original_get_event_loop = asyncio.get_event_loop
        original_ensure_future = asyncio.ensure_future
        try:
            asyncio.get_event_loop = lambda: DummyLoop()
            asyncio.ensure_future = fake_ensure_future
            assert emitter._route_event(event) is True
            assert ensured, "Expected ensure_future to be called"
        finally:
            asyncio.get_event_loop = original_get_event_loop
            asyncio.ensure_future = original_ensure_future

    def test_auth_exception_falls_back_to_queue(
        self, emitter: EventEmitter, monkeypatch
    ):
        """Auth failures do not prevent queueing."""
        emitter.ws_client = None

        def _boom():
            raise RuntimeError("auth failure")

        monkeypatch.setattr("specify_cli.auth.get_token_manager", _boom)
        emitter.queue = MagicMock()
        emitter.queue.queue_event.return_value = True
        event = {
            "event_id": emitter.generate_causation_id(),
            "event_type": "WPStatusChanged",
            "aggregate_id": "WP01",
            "aggregate_type": "WorkPackage",
            "payload": {"wp_id": "WP01", "from_lane": "planned", "to_lane": "in_progress"},
            "node_id": "test-node-id",
            "lamport_clock": 1,
            "causation_id": None,
            "timestamp": "2026-02-04T12:00:00+00:00",
            "team_slug": "test-team",
        }
        assert emitter._route_event(event) is True
        emitter.queue.queue_event.assert_called_once()
