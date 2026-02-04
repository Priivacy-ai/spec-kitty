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

import re
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.sync.emitter import (
    EventEmitter,
    VALID_EVENT_TYPES,
    VALID_AGGREGATE_TYPES,
    _ULID_PATTERN,
    _WP_ID_PATTERN,
)
from specify_cli.sync.events import (
    get_emitter,
    reset_emitter,
    emit_wp_status_changed,
    emit_wp_created,
    emit_wp_assigned,
    emit_feature_created,
    emit_feature_completed,
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
    def test_get_emitter_returns_same_instance(self, _cfg, _queue, _clock):
        """get_emitter() returns same instance on repeated calls."""
        e1 = get_emitter()
        e2 = get_emitter()
        assert e1 is e2

    @patch("specify_cli.sync.emitter.LamportClock.load")
    @patch("specify_cli.sync.emitter.OfflineQueue")
    @patch("specify_cli.sync.emitter.SyncConfig")
    def test_reset_emitter_clears_singleton(self, _cfg, _queue, _clock):
        """reset_emitter() allows new instance creation."""
        e1 = get_emitter()
        reset_emitter()
        e2 = get_emitter()
        assert e1 is not e2


class TestEventEnvelope:
    """Test common envelope fields across all events."""

    def test_event_id_is_valid_ulid(self, emitter: EventEmitter, temp_queue):
        """Event ID is a 26-character ULID (SC-009 prerequisite)."""
        event = emitter.emit_wp_status_changed("WP01", "planned", "doing")
        assert event is not None
        assert len(event["event_id"]) == 26
        assert _ULID_PATTERN.match(event["event_id"])

    def test_lamport_clock_increments(self, emitter: EventEmitter, temp_queue):
        """Lamport clock increments on each emit (SC-009)."""
        ev1 = emitter.emit_wp_status_changed("WP01", "planned", "doing")
        ev2 = emitter.emit_wp_status_changed("WP02", "planned", "doing")
        assert ev1 is not None and ev2 is not None
        assert ev2["lamport_clock"] > ev1["lamport_clock"]

    def test_lamport_clock_starts_at_one(self, emitter: EventEmitter, temp_queue):
        """First event gets lamport_clock=1 (tick from 0)."""
        event = emitter.emit_wp_status_changed("WP01", "planned", "doing")
        assert event is not None
        assert event["lamport_clock"] == 1

    def test_node_id_present(self, emitter: EventEmitter, temp_queue):
        """Event includes node_id from clock."""
        event = emitter.emit_wp_status_changed("WP01", "planned", "doing")
        assert event is not None
        assert event["node_id"] == "test-node-id"

    def test_timestamp_is_iso8601(self, emitter: EventEmitter, temp_queue):
        """Event includes ISO 8601 timestamp."""
        event = emitter.emit_wp_status_changed("WP01", "planned", "doing")
        assert event is not None
        # Should contain T and timezone info
        assert "T" in event["timestamp"]

    def test_team_slug_from_auth(self, emitter: EventEmitter, temp_queue):
        """Event includes team_slug from AuthClient (SC-010)."""
        event = emitter.emit_wp_status_changed("WP01", "planned", "doing")
        assert event is not None
        assert event["team_slug"] == "test-team"

    def test_team_slug_defaults_to_local(self, temp_queue, temp_clock, mock_config):
        """team_slug defaults to 'local' when auth unavailable (SC-010)."""
        auth = MagicMock()
        auth.get_team_slug.side_effect = Exception("Not authenticated")
        em = EventEmitter(
            clock=temp_clock, config=mock_config, queue=temp_queue,
            _auth=auth, ws_client=None,
        )
        event = em.emit_wp_status_changed("WP01", "planned", "doing")
        assert event is not None
        assert event["team_slug"] == "local"

    def test_causation_id_included_when_provided(self, emitter: EventEmitter, temp_queue):
        """causation_id passed through to event envelope."""
        cid = emitter.generate_causation_id()
        event = emitter.emit_wp_status_changed("WP01", "planned", "doing", causation_id=cid)
        assert event is not None
        assert event["causation_id"] == cid

    def test_causation_id_none_by_default(self, emitter: EventEmitter, temp_queue):
        """causation_id is None when not provided."""
        event = emitter.emit_wp_status_changed("WP01", "planned", "doing")
        assert event is not None
        assert event["causation_id"] is None


class TestWPStatusChanged:
    """Test emit_wp_status_changed (SC-001, SC-002, SC-003)."""

    def test_basic_emission(self, emitter: EventEmitter, temp_queue):
        """WPStatusChanged event has correct structure."""
        event = emitter.emit_wp_status_changed(
            wp_id="WP01", previous_status="planned", new_status="doing",
        )
        assert event is not None
        assert event["event_type"] == "WPStatusChanged"
        assert event["aggregate_id"] == "WP01"
        assert event["aggregate_type"] == "WorkPackage"
        assert event["payload"]["wp_id"] == "WP01"
        assert event["payload"]["previous_status"] == "planned"
        assert event["payload"]["new_status"] == "doing"

    def test_changed_by_default(self, emitter: EventEmitter, temp_queue):
        """changed_by defaults to 'user'."""
        event = emitter.emit_wp_status_changed("WP01", "planned", "doing")
        assert event is not None
        assert event["payload"]["changed_by"] == "user"

    def test_changed_by_agent(self, emitter: EventEmitter, temp_queue):
        """changed_by can be set to agent name."""
        event = emitter.emit_wp_status_changed(
            "WP01", "planned", "doing", changed_by="claude-opus",
        )
        assert event is not None
        assert event["payload"]["changed_by"] == "claude-opus"

    def test_feature_slug_optional(self, emitter: EventEmitter, temp_queue):
        """feature_slug is optional and nullable."""
        event = emitter.emit_wp_status_changed(
            "WP01", "planned", "doing", feature_slug="028-sync",
        )
        assert event is not None
        assert event["payload"]["feature_slug"] == "028-sync"

    def test_queued_in_offline_queue(self, emitter: EventEmitter, temp_queue):
        """Event is queued when no WebSocket connected (SC-006)."""
        emitter.emit_wp_status_changed("WP01", "planned", "doing")
        assert temp_queue.size() == 1

    def test_all_valid_status_transitions(self, emitter: EventEmitter, temp_queue):
        """All status values pass validation."""
        statuses = ["planned", "doing", "for_review", "done"]
        for prev, new in zip(statuses, statuses[1:]):
            event = emitter.emit_wp_status_changed("WP01", prev, new)
            assert event is not None, f"Failed for {prev} -> {new}"


class TestWPCreated:
    """Test emit_wp_created."""

    def test_basic_emission(self, emitter: EventEmitter, temp_queue):
        """WPCreated event has correct structure."""
        event = emitter.emit_wp_created(
            wp_id="WP01", title="Implement sync", feature_slug="028-sync",
        )
        assert event is not None
        assert event["event_type"] == "WPCreated"
        assert event["aggregate_type"] == "WorkPackage"
        assert event["payload"]["wp_id"] == "WP01"
        assert event["payload"]["title"] == "Implement sync"
        assert event["payload"]["feature_slug"] == "028-sync"

    def test_dependencies_default_empty(self, emitter: EventEmitter, temp_queue):
        """Dependencies defaults to empty list."""
        event = emitter.emit_wp_created("WP01", "Title", "028-sync")
        assert event is not None
        assert event["payload"]["dependencies"] == []

    def test_dependencies_list(self, emitter: EventEmitter, temp_queue):
        """Dependencies can be a list of WP IDs."""
        event = emitter.emit_wp_created(
            "WP02", "Title", "028-sync", dependencies=["WP01"],
        )
        assert event is not None
        assert event["payload"]["dependencies"] == ["WP01"]


class TestWPAssigned:
    """Test emit_wp_assigned (SC-005)."""

    def test_basic_emission(self, emitter: EventEmitter, temp_queue):
        """WPAssigned event has correct structure."""
        event = emitter.emit_wp_assigned(
            wp_id="WP01", agent_id="claude-opus", phase="implementation",
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


class TestFeatureCreated:
    """Test emit_feature_created (SC-004)."""

    def test_basic_emission(self, emitter: EventEmitter, temp_queue):
        """FeatureCreated event has correct structure."""
        event = emitter.emit_feature_created(
            feature_slug="028-cli-event-emission-sync",
            feature_number="028",
            target_branch="main",
            wp_count=7,
        )
        assert event is not None
        assert event["event_type"] == "FeatureCreated"
        assert event["aggregate_type"] == "Feature"
        assert event["aggregate_id"] == "028-cli-event-emission-sync"
        assert event["payload"]["wp_count"] == 7

    def test_created_at_optional(self, emitter: EventEmitter, temp_queue):
        """created_at is optional."""
        event = emitter.emit_feature_created(
            "028-sync", "028", "main", 5,
            created_at="2026-02-04T12:00:00+00:00",
        )
        assert event is not None
        assert event["payload"]["created_at"] == "2026-02-04T12:00:00+00:00"


class TestFeatureCompleted:
    """Test emit_feature_completed."""

    def test_basic_emission(self, emitter: EventEmitter, temp_queue):
        """FeatureCompleted event has correct structure."""
        event = emitter.emit_feature_completed(
            feature_slug="028-sync", total_wps=7,
        )
        assert event is not None
        assert event["event_type"] == "FeatureCompleted"
        assert event["aggregate_type"] == "Feature"
        assert event["payload"]["total_wps"] == 7

    def test_optional_fields(self, emitter: EventEmitter, temp_queue):
        """completed_at and total_duration are optional."""
        event = emitter.emit_feature_completed(
            "028-sync", 7,
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
            wp_id="WP01", entry_type="note", entry_content="Started implementation",
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
            error_type="runtime", error_message="Something broke",
        )
        assert event is not None
        assert event["event_type"] == "ErrorLogged"
        assert event["payload"]["error_type"] == "runtime"
        assert event["payload"]["error_message"] == "Something broke"

    def test_aggregate_id_uses_wp_id(self, emitter: EventEmitter, temp_queue):
        """aggregate_id is wp_id when provided."""
        event = emitter.emit_error_logged(
            "runtime", "error", wp_id="WP01",
        )
        assert event is not None
        assert event["aggregate_id"] == "WP01"
        assert event["aggregate_type"] == "WorkPackage"

    def test_aggregate_id_fallback(self, emitter: EventEmitter, temp_queue):
        """aggregate_id is 'error' when no wp_id."""
        event = emitter.emit_error_logged("runtime", "error")
        assert event is not None
        assert event["aggregate_id"] == "error"
        assert event["aggregate_type"] == "Feature"

    def test_optional_fields(self, emitter: EventEmitter, temp_queue):
        """stack_trace and agent_id are optional."""
        event = emitter.emit_error_logged(
            "network", "timeout",
            wp_id="WP01", stack_trace="Traceback...", agent_id="claude",
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
            wp_id="WP02", dependency_wp_id="WP01", resolution_type="completed",
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
        event = emitter.emit_wp_status_changed("INVALID", "planned", "doing")
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

    def test_invalid_feature_slug_returns_none(self, emitter: EventEmitter, temp_queue):
        """Invalid feature_slug format for FeatureCreated causes validation failure."""
        event = emitter.emit_feature_created("NoNumbers", "abc", "main", 5)
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
        """Negative wp_count for FeatureCreated causes validation failure."""
        event = emitter.emit_feature_created("028-sync", "028", "main", -1)
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
        mock_get.return_value = mock_emitter
        emit_wp_status_changed("WP01", "planned", "doing")
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
    def test_emit_feature_created_delegates(self, mock_get):
        """emit_feature_created delegates to singleton."""
        mock_emitter = MagicMock()
        mock_get.return_value = mock_emitter
        emit_feature_created("028-sync", "028", "main", 5)
        mock_emitter.emit_feature_created.assert_called_once()

    @patch("specify_cli.sync.events.get_emitter")
    def test_emit_feature_completed_delegates(self, mock_get):
        """emit_feature_completed delegates to singleton."""
        mock_emitter = MagicMock()
        mock_get.return_value = mock_emitter
        emit_feature_completed("028-sync", 5)
        mock_emitter.emit_feature_completed.assert_called_once()

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


class TestInternalValidation:
    """Test internal _validate_event paths for edge cases."""

    def test_invalid_aggregate_type_via_emit(self, emitter: EventEmitter, temp_queue):
        """Invalid aggregate_type causes validation failure."""
        event = emitter._emit(
            event_type="WPStatusChanged",
            aggregate_id="WP01",
            aggregate_type="InvalidType",  # not in VALID_AGGREGATE_TYPES
            payload={"wp_id": "WP01", "previous_status": "planned", "new_status": "doing"},
        )
        assert event is None

    def test_invalid_causation_id_format(self, emitter: EventEmitter, temp_queue):
        """Non-ULID causation_id causes validation failure."""
        event = emitter.emit_wp_status_changed(
            "WP01", "planned", "doing",
            causation_id="not-a-ulid",  # too short, wrong format
        )
        assert event is None

    def test_created_at_non_datetime_validation(self, emitter: EventEmitter, temp_queue):
        """Invalid created_at datetime string fails FeatureCreated validation."""
        event = emitter.emit_feature_created(
            "028-sync", "028", "main", 5,
            created_at="not-a-date",
        )
        assert event is None

    def test_completed_at_non_datetime_validation(self, emitter: EventEmitter, temp_queue):
        """Invalid completed_at datetime string fails FeatureCompleted validation."""
        event = emitter.emit_feature_completed(
            "028-sync", 5,
            completed_at="not-a-date",
        )
        assert event is None

    def test_validation_exception_returns_none(self, temp_queue, temp_clock, mock_config):
        """Exception during validation returns None."""
        auth = MagicMock()
        auth.get_team_slug.return_value = "test"
        auth.is_authenticated.return_value = False

        em = EventEmitter(
            clock=temp_clock, config=mock_config, queue=temp_queue,
            _auth=auth, ws_client=None,
        )

        # Monkey-patch _validate_event to raise
        original = em._validate_event
        em._validate_event = MagicMock(side_effect=Exception("boom"))

        event = em.emit_wp_status_changed("WP01", "planned", "doing")
        assert event is None

    def test_lazy_auth_creation(self, temp_queue, temp_clock, mock_config):
        """Auth is lazily created when _auth is None."""
        em = EventEmitter(
            clock=temp_clock, config=mock_config, queue=temp_queue,
            _auth=None, ws_client=None,
        )
        # Accessing auth property should create AuthClient via lazy import
        with patch("specify_cli.sync.auth.AuthClient") as MockAuth:
            mock_instance = MagicMock()
            mock_instance.get_team_slug.return_value = "lazy-team"
            mock_instance.is_authenticated.return_value = False
            MockAuth.return_value = mock_instance

            # Access the auth property - triggers lazy creation
            auth = em.auth
            assert auth is mock_instance
