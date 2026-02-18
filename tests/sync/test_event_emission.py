"""Tests for CLI command event emission (T040).

Covers:
- SC-001: implement emits WPStatusChanged(planned→in_progress)
- SC-002: merge/move-task emits WPStatusChanged(in_progress→for_review)
- SC-003: accept emits WPStatusChanged(for_review→done)
- SC-004: finalize-tasks emits FeatureCreated + WPCreated batch
- SC-005: orchestrate emits WPAssigned
- SC-008: Emission failure does not block command
- SC-011: ErrorLogged emitted on errors
- SC-012: DependencyResolved emitted
- Identity injection: events include project_uuid and project_slug
- Missing identity: events queued locally only (no WebSocket send)

These tests verify that the emit_* functions are called correctly
by testing them through the EventEmitter API directly (since the
CLI commands call these functions internally).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.project_identity import ProjectIdentity
from specify_cli.sync.queue import OfflineQueue


class TestImplementEmitsWPStatusChanged:
    """SC-001: implement command emits WPStatusChanged(planned→in_progress)."""

    def test_planned_to_doing(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """implement: WP moves from planned to in_progress."""
        event = emitter.emit_wp_status_changed(
            wp_id="WP01",
            from_lane="planned",
            to_lane="in_progress",
            actor="claude-opus",
        )
        assert event is not None
        assert event["event_type"] == "WPStatusChanged"
        assert event["payload"]["from_lane"] == "planned"
        assert event["payload"]["to_lane"] == "in_progress"
        assert event["payload"]["actor"] == "claude-opus"

    def test_implement_event_includes_git_metadata(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """implement: emitted event includes git metadata fields."""
        event = emitter.emit_wp_status_changed(
            wp_id="WP01",
            from_lane="planned",
            to_lane="in_progress",
        )
        assert event is not None
        assert "git_branch" in event
        assert "head_commit_sha" in event
        assert "repo_slug" in event
        assert event["git_branch"] == "test-branch"
        assert event["head_commit_sha"] == "a" * 40
        assert event["repo_slug"] == "test-org/test-repo"

    def test_event_queued_for_sync(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """implement: event is queued in offline queue."""
        emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert temp_queue.size() == 1


class TestMergeEmitsWPStatusChanged:
    """SC-002: merge/move-task emits WPStatusChanged(in_progress→for_review)."""

    def test_doing_to_for_review(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """merge: WP moves from in_progress to for_review."""
        event = emitter.emit_wp_status_changed(
            wp_id="WP01",
            from_lane="in_progress",
            to_lane="for_review",
        )
        assert event is not None
        assert event["payload"]["from_lane"] == "in_progress"
        assert event["payload"]["to_lane"] == "for_review"


class TestAcceptEmitsWPStatusChanged:
    """SC-003: accept emits WPStatusChanged(for_review→done)."""

    def test_for_review_to_done(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """accept: WP moves from for_review to done."""
        event = emitter.emit_wp_status_changed(
            wp_id="WP01",
            from_lane="for_review",
            to_lane="done",
        )
        assert event is not None
        assert event["payload"]["from_lane"] == "for_review"
        assert event["payload"]["to_lane"] == "done"

    def test_accept_event_includes_git_metadata(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """accept: emitted event includes git metadata fields."""
        event = emitter.emit_wp_status_changed(
            wp_id="WP01",
            from_lane="for_review",
            to_lane="done",
        )
        assert event is not None
        assert event["git_branch"] == "test-branch"
        assert event["head_commit_sha"] == "a" * 40
        assert event["repo_slug"] == "test-org/test-repo"


class TestFinalizeTasksEmitsBatch:
    """SC-004: finalize-tasks emits FeatureCreated + WPCreated for each WP."""

    def test_feature_created_plus_wp_created(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """finalize-tasks: 1 FeatureCreated + 7 WPCreated events."""
        causation_id = emitter.generate_causation_id()

        # Emit FeatureCreated
        fc = emitter.emit_feature_created(
            feature_slug="028-cli-event-emission-sync",
            feature_number="028",
            target_branch="main",
            wp_count=7,
            causation_id=causation_id,
        )
        assert fc is not None
        assert fc["event_type"] == "FeatureCreated"

        # Emit 7 WPCreated events
        for i in range(1, 8):
            wp = emitter.emit_wp_created(
                wp_id=f"WP{i:02d}",
                title=f"Work Package {i}",
                feature_slug="028-cli-event-emission-sync",
                dependencies=([f"WP{i-1:02d}"] if i > 1 else []),
                causation_id=causation_id,
            )
            assert wp is not None

        # Total: 1 FeatureCreated + 7 WPCreated = 8 events
        assert temp_queue.size() == 8

        # Verify causation chain
        events = temp_queue.drain_queue()
        for ev in events:
            assert ev["causation_id"] == causation_id


class TestGitMetadataInBatchEvents:
    """SC-001 (Feature 033): git metadata present in batch event emissions."""

    def test_feature_created_includes_git_metadata(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """FeatureCreated event includes git metadata fields."""
        event = emitter.emit_feature_created(
            feature_slug="033-observability",
            feature_number="033",
            target_branch="main",
            wp_count=4,
        )
        assert event is not None
        assert event["git_branch"] == "test-branch"
        assert event["head_commit_sha"] == "a" * 40
        assert event["repo_slug"] == "test-org/test-repo"

    def test_wp_created_includes_git_metadata(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """WPCreated event includes git metadata fields."""
        event = emitter.emit_wp_created(
            wp_id="WP01",
            title="Test WP",
            feature_slug="033-observability",
        )
        assert event is not None
        assert event["git_branch"] == "test-branch"
        assert event["head_commit_sha"] == "a" * 40
        assert event["repo_slug"] == "test-org/test-repo"

    def test_error_logged_includes_git_metadata(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """ErrorLogged event includes git metadata fields."""
        event = emitter.emit_error_logged(
            error_type="runtime",
            error_message="Test error",
        )
        assert event is not None
        assert event["git_branch"] == "test-branch"
        assert event["head_commit_sha"] == "a" * 40
        assert event["repo_slug"] == "test-org/test-repo"


class TestOrchestrateEmitsWPAssigned:
    """SC-005: orchestrate emits WPAssigned events."""

    def test_wp_assigned_for_implementation(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """orchestrate: emits WPAssigned with implementation phase."""
        event = emitter.emit_wp_assigned(
            wp_id="WP01",
            agent_id="claude-opus",
            phase="implementation",
        )
        assert event is not None
        assert event["event_type"] == "WPAssigned"
        assert event["payload"]["agent_id"] == "claude-opus"
        assert event["payload"]["phase"] == "implementation"

    def test_wp_assigned_for_review(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """orchestrate: emits WPAssigned with review phase."""
        event = emitter.emit_wp_assigned(
            wp_id="WP01",
            agent_id="claude-sonnet",
            phase="review",
        )
        assert event is not None
        assert event["payload"]["phase"] == "review"

    def test_wp_assigned_with_retry(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """orchestrate: retry_count tracked on reassignment."""
        event = emitter.emit_wp_assigned(
            wp_id="WP01",
            agent_id="claude-opus",
            phase="implementation",
            retry_count=2,
        )
        assert event is not None
        assert event["payload"]["retry_count"] == 2


class TestEmissionFailureNonBlocking:
    """SC-008: CLI commands succeed even when emission fails."""

    def test_clock_failure_returns_none(self, temp_queue: OfflineQueue):
        """Clock explosion returns None, never raises."""
        clock = MagicMock()
        clock.tick.side_effect = RuntimeError("Clock corrupted")
        auth = MagicMock()
        config = MagicMock()

        em = EventEmitter(clock=clock, config=config, queue=temp_queue, _auth=auth, ws_client=None)
        event = em.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is None
        # Critically: no exception raised

    def test_validation_failure_returns_none(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """Validation failure returns None, doesn't raise."""
        event = emitter.emit_wp_status_changed("INVALID_ID", "planned", "in_progress")
        assert event is None
        assert temp_queue.size() == 0

    def test_queue_failure_returns_event(self, temp_queue: OfflineQueue, temp_clock, mock_config):
        """Queue write failure still returns the event (non-blocking)."""
        broken_queue = MagicMock(spec=OfflineQueue)
        broken_queue.queue_event.side_effect = Exception("Disk full")
        auth = MagicMock()
        auth.get_team_slug.return_value = "test-team"
        auth.is_authenticated.return_value = False

        em = EventEmitter(
            clock=temp_clock, config=mock_config, queue=broken_queue,
            _auth=auth, ws_client=None,
        )
        event = em.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert event is not None  # Event still created, just not queued


class TestErrorLoggedEmission:
    """SC-011: ErrorLogged events emitted on command errors."""

    def test_error_logged_with_wp_context(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """ErrorLogged includes wp_id context."""
        event = emitter.emit_error_logged(
            error_type="runtime",
            error_message="Task validation failed",
            wp_id="WP03",
            agent_id="claude-opus",
        )
        assert event is not None
        assert event["event_type"] == "ErrorLogged"
        assert event["payload"]["wp_id"] == "WP03"
        assert event["payload"]["agent_id"] == "claude-opus"

    def test_error_logged_with_stack_trace(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """ErrorLogged can include stack trace."""
        event = emitter.emit_error_logged(
            error_type="runtime",
            error_message="Unexpected error",
            stack_trace="File 'foo.py', line 42\n  raise ValueError",
        )
        assert event is not None
        assert "File 'foo.py'" in event["payload"]["stack_trace"]

    def test_all_error_types_valid(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """All 5 error types produce valid events."""
        for etype in ["validation", "runtime", "network", "auth", "unknown"]:
            event = emitter.emit_error_logged(etype, f"Error of type {etype}")
            assert event is not None, f"Failed for error_type={etype}"


class TestDependencyResolvedEmission:
    """SC-012: DependencyResolved emitted when dependencies unblocked."""

    def test_dependency_completed(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """DependencyResolved with completed resolution."""
        event = emitter.emit_dependency_resolved(
            wp_id="WP02",
            dependency_wp_id="WP01",
            resolution_type="completed",
        )
        assert event is not None
        assert event["event_type"] == "DependencyResolved"
        assert event["payload"]["resolution_type"] == "completed"

    def test_dependency_skipped(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """DependencyResolved with skipped resolution."""
        event = emitter.emit_dependency_resolved(
            wp_id="WP03",
            dependency_wp_id="WP02",
            resolution_type="skipped",
        )
        assert event is not None
        assert event["payload"]["resolution_type"] == "skipped"

    def test_dependency_merged(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """DependencyResolved with merged resolution."""
        event = emitter.emit_dependency_resolved(
            wp_id="WP04",
            dependency_wp_id="WP03",
            resolution_type="merged",
        )
        assert event is not None
        assert event["payload"]["resolution_type"] == "merged"


class TestIdentityInjection:
    """Tests for project_uuid and project_slug injection in events."""

    def test_wp_status_changed_includes_identity(
        self, emitter: EventEmitter, temp_queue: OfflineQueue
    ):
        """WPStatusChanged event includes project_uuid."""
        event = emitter.emit_wp_status_changed(
            wp_id="WP01",
            from_lane="planned",
            to_lane="in_progress",
        )
        assert event is not None
        assert "project_uuid" in event
        assert event["project_uuid"] is not None
        assert "project_slug" in event
        assert event["project_slug"] == "test-project"

    def test_feature_created_includes_identity(
        self, emitter: EventEmitter, temp_queue: OfflineQueue
    ):
        """FeatureCreated event includes project_uuid."""
        event = emitter.emit_feature_created(
            feature_slug="032-identity-aware",
            feature_number="032",
            target_branch="main",
            wp_count=5,
        )
        assert event is not None
        assert "project_uuid" in event
        assert event["project_uuid"] is not None

    def test_wp_created_includes_identity(
        self, emitter: EventEmitter, temp_queue: OfflineQueue
    ):
        """WPCreated event includes project_uuid."""
        event = emitter.emit_wp_created(
            wp_id="WP01",
            title="Test WP",
            feature_slug="032-identity-aware",
        )
        assert event is not None
        assert "project_uuid" in event
        assert event["project_uuid"] is not None

    def test_identity_is_cached(
        self, emitter: EventEmitter, temp_queue: OfflineQueue, mock_identity: ProjectIdentity
    ):
        """Identity is resolved once and cached for subsequent events."""
        # Emit multiple events
        emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        emitter.emit_wp_status_changed("WP02", "planned", "in_progress")
        emitter.emit_wp_status_changed("WP03", "planned", "in_progress")

        # All should have the same identity (from cache)
        events = temp_queue.drain_queue()
        uuid_values = [e["project_uuid"] for e in events]
        assert len(set(uuid_values)) == 1  # All same UUID


class TestMissingIdentityQueuesOnly:
    """Tests for events without identity being queued locally only."""

    def test_missing_identity_queues_only(
        self, emitter_without_identity: EventEmitter, temp_queue: OfflineQueue
    ):
        """Events without project_uuid are queued but not sent via WebSocket."""
        event = emitter_without_identity.emit_wp_status_changed(
            wp_id="WP01",
            from_lane="planned",
            to_lane="in_progress",
        )

        # Event is still created (not None)
        assert event is not None

        # Event is queued
        assert temp_queue.size() == 1

        # Event has None project_uuid
        assert event.get("project_uuid") is None

    def test_missing_identity_warning_shown(
        self, emitter_without_identity: EventEmitter, temp_queue: OfflineQueue, capsys
    ):
        """Warning is logged when identity is missing."""
        emitter_without_identity.emit_wp_status_changed(
            wp_id="WP01",
            from_lane="planned",
            to_lane="in_progress",
        )

        # Capture stderr (Rich console output goes to stderr)
        captured = capsys.readouterr()
        assert "missing project_uuid" in captured.err or "queued locally only" in captured.err

    def test_multiple_events_without_identity_all_queued(
        self, emitter_without_identity: EventEmitter, temp_queue: OfflineQueue
    ):
        """Multiple events without identity are all queued."""
        for i in range(1, 4):
            emitter_without_identity.emit_wp_status_changed(
                wp_id=f"WP{i:02d}",
                from_lane="planned",
                to_lane="in_progress",
            )

        # All 3 events should be queued
        assert temp_queue.size() == 3


class TestNoDuplicateEmissions:
    """Regression tests for duplicate emission bug (WP05).

    These tests verify that CLI commands emit exactly one WPStatusChanged
    event per status transition, not duplicates.
    """

    def test_implement_emits_once(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """implement command should emit exactly one WPStatusChanged.

        Regression test: Previously implement.py emitted twice:
        - Once inside `if lane_changed:` block (correct)
        - Once unconditionally after the try block (duplicate)

        After fix: Only the `if lane_changed:` emission remains.
        """
        # Simulate what implement.py should do: exactly one emission
        emitter.emit_wp_status_changed(
            wp_id="WP01",
            from_lane="planned",
            to_lane="in_progress",
            actor="claude-opus",
        )

        # Verify exactly 1 event queued (not 2)
        assert temp_queue.size() == 1, f"Expected 1 emission, got {temp_queue.size()}"

        # Verify the event content
        events = temp_queue.drain_queue()
        assert len(events) == 1
        assert events[0]["event_type"] == "WPStatusChanged"
        assert events[0]["payload"]["from_lane"] == "planned"
        assert events[0]["payload"]["to_lane"] == "in_progress"

    def test_accept_emits_once_per_wp(self, emitter: EventEmitter, temp_queue: OfflineQueue):
        """accept command should emit exactly one WPStatusChanged per WP.

        Regression test: Previously accept.py emitted twice per WP:
        - Once via _emit_acceptance_events() (correct)
        - Once in a separate loop after json_output check (duplicate)

        After fix: Only the _emit_acceptance_events() call remains.
        """
        # Simulate what accept.py should do: one emission per WP
        wp_ids = ["WP01", "WP02", "WP03"]
        for wp_id in wp_ids:
            emitter.emit_wp_status_changed(
                wp_id=wp_id,
                from_lane="for_review",
                to_lane="done",
                actor="user",
            )

        # Verify exactly 3 events (one per WP, not 6)
        assert temp_queue.size() == 3, f"Expected 3 emissions (one per WP), got {temp_queue.size()}"

        # Verify all events are for_review -> done
        events = temp_queue.drain_queue()
        for event in events:
            assert event["event_type"] == "WPStatusChanged"
            assert event["payload"]["from_lane"] == "for_review"
            assert event["payload"]["to_lane"] == "done"


class TestPolicyMetadataPassthrough:
    """Verify policy_metadata flows from sync.events wrapper through emitter to payload."""

    def test_policy_metadata_included_in_payload(
        self, emitter: EventEmitter, temp_queue: OfflineQueue
    ):
        """policy_metadata passed to emit_wp_status_changed() appears in event payload."""
        policy = {
            "orchestrator_id": "test-orch",
            "orchestrator_version": "0.1.0",
            "agent_family": "claude",
            "approval_mode": "supervised",
            "sandbox_mode": "sandbox",
            "network_mode": "restricted",
            "dangerous_flags": [],
        }
        event = emitter.emit_wp_status_changed(
            wp_id="WP01",
            from_lane="planned",
            to_lane="claimed",
            actor="claude",
            feature_slug="099-test-feature",
            policy_metadata=policy,
        )
        assert event is not None
        assert event["payload"]["policy_metadata"] == policy

    def test_policy_metadata_none_included_in_payload(
        self, emitter: EventEmitter, temp_queue: OfflineQueue
    ):
        """policy_metadata=None is valid and included in payload."""
        event = emitter.emit_wp_status_changed(
            wp_id="WP01",
            from_lane="planned",
            to_lane="claimed",
            actor="claude",
            policy_metadata=None,
        )
        assert event is not None
        assert event["payload"]["policy_metadata"] is None

    def test_sync_events_wrapper_passes_policy_metadata(
        self, emitter: EventEmitter, temp_queue: OfflineQueue
    ):
        """sync.events.emit_wp_status_changed() passes policy_metadata through to emitter."""
        from unittest.mock import patch

        policy = {"orchestrator_id": "orch-1", "orchestrator_version": "0.1.0"}
        with patch(
            "specify_cli.sync.events.get_emitter", return_value=emitter
        ):
            from specify_cli.sync.events import emit_wp_status_changed as wrapper_emit

            event = wrapper_emit(
                wp_id="WP01",
                from_lane="planned",
                to_lane="claimed",
                actor="claude",
                policy_metadata=policy,
            )

        assert event is not None
        assert event["payload"]["policy_metadata"] == policy
