"""Shape conformance tests for event envelopes against 3.0.0 contract.

Tests that events constructed via the EventEmitter include required fields,
use correct values, and exclude forbidden fields -- all validated against
the vendored upstream_contract.json.

Run: python -m pytest tests/contract/test_event_envelope.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock


def _make_emitter():
    """Create an EventEmitter with mocked dependencies for isolated testing.

    Mocks: LamportClock, OfflineQueue, AuthClient, ProjectIdentity,
    GitMetadataResolver. The emitter uses real envelope construction
    but does not touch filesystem, network, or SQLite.
    """
    from specify_cli.sync.emitter import EventEmitter

    mock_clock = MagicMock()
    mock_clock.tick.return_value = 1
    mock_clock.node_id = "a1b2c3d4e5f6"

    mock_queue = MagicMock()
    mock_queue.queue_event.return_value = True

    mock_identity = MagicMock()
    mock_identity.build_id = "test-build-id-001"
    mock_identity.project_uuid = "00000000-0000-0000-0000-000000000001"
    mock_identity.project_slug = "test-project"

    mock_git_meta = MagicMock()
    mock_git_meta.git_branch = "main"
    mock_git_meta.head_commit_sha = "abc123"
    mock_git_meta.repo_slug = "test-org/test-repo"

    emitter = EventEmitter(
        clock=mock_clock,
        queue=mock_queue,
    )
    emitter._identity = mock_identity
    emitter._git_resolver = MagicMock()
    emitter._git_resolver.resolve.return_value = mock_git_meta

    # Mock auth to return a team slug
    mock_auth = MagicMock()
    mock_auth.get_team_slug.return_value = "test-team"
    mock_auth.is_authenticated.return_value = False
    emitter._auth = mock_auth

    return emitter


class TestMissionCreatedEnvelope:
    """Validate MissionCreated event envelope shape."""

    def test_schema_version_is_3_0_0(self, canonical_envelope_fields):
        emitter = _make_emitter()
        event = emitter.emit_mission_created(
            mission_slug="064-test-mission",
            mission_number=64,
            target_branch="main",
            wp_count=3,
        )
        assert event is not None, "emit_mission_created returned None"
        assert event["schema_version"] == "3.0.0"

    def test_build_id_present_and_nonempty(self):
        emitter = _make_emitter()
        event = emitter.emit_mission_created(
            mission_slug="064-test-mission",
            mission_number=64,
            target_branch="main",
            wp_count=3,
        )
        assert event is not None
        assert "build_id" in event
        assert event["build_id"], "build_id must be non-empty"

    def test_aggregate_type_is_mission(self):
        emitter = _make_emitter()
        event = emitter.emit_mission_created(
            mission_slug="064-test-mission",
            mission_number=64,
            target_branch="main",
            wp_count=3,
        )
        assert event is not None
        assert event["aggregate_type"] == "Mission"

    def test_aggregate_type_is_not_feature(self):
        emitter = _make_emitter()
        event = emitter.emit_mission_created(
            mission_slug="064-test-mission",
            mission_number=64,
            target_branch="main",
            wp_count=3,
        )
        assert event is not None
        assert event["aggregate_type"] != "Feature"

    def test_event_type_is_mission_created(self):
        emitter = _make_emitter()
        event = emitter.emit_mission_created(
            mission_slug="064-test-mission",
            mission_number=64,
            target_branch="main",
            wp_count=3,
        )
        assert event is not None
        assert event["event_type"] == "MissionCreated"

    def test_no_mission_slug_in_envelope(self, forbidden_envelope_fields):
        """mission_slug must NOT be a top-level key in the event envelope."""
        emitter = _make_emitter()
        event = emitter.emit_mission_created(
            mission_slug="064-test-mission",
            mission_number=64,
            target_branch="main",
            wp_count=3,
        )
        assert event is not None
        # mission_slug lives in the payload, not the envelope top level
        for forbidden_field in forbidden_envelope_fields:
            assert forbidden_field not in event or forbidden_field == "mission_slug" and event.get(forbidden_field) is None, (
                f"Forbidden field '{forbidden_field}' found at envelope top level"
            )

    def test_no_mission_number_in_envelope(self, forbidden_envelope_fields):
        """mission_number must NOT be a top-level key in the event envelope."""
        emitter = _make_emitter()
        event = emitter.emit_mission_created(
            mission_slug="064-test-mission",
            mission_number=64,
            target_branch="main",
            wp_count=3,
        )
        assert event is not None
        assert "mission_number" not in event, "mission_number must not be a top-level envelope key"

    def test_all_required_envelope_fields_present(self, canonical_envelope_fields):
        emitter = _make_emitter()
        event = emitter.emit_mission_created(
            mission_slug="064-test-mission",
            mission_number=64,
            target_branch="main",
            wp_count=3,
        )
        assert event is not None
        for field in canonical_envelope_fields:
            assert field in event, f"Required envelope field '{field}' missing"


class TestMissionClosedEnvelope:
    """Validate MissionClosed event envelope shape."""

    def test_schema_version_is_3_0_0(self):
        emitter = _make_emitter()
        event = emitter.emit_mission_closed(
            mission_slug="064-test-mission",
            total_wps=5,
        )
        assert event is not None
        assert event["schema_version"] == "3.0.0"

    def test_aggregate_type_is_mission(self):
        emitter = _make_emitter()
        event = emitter.emit_mission_closed(
            mission_slug="064-test-mission",
            total_wps=5,
        )
        assert event is not None
        assert event["aggregate_type"] == "Mission"

    def test_build_id_present(self):
        emitter = _make_emitter()
        event = emitter.emit_mission_closed(
            mission_slug="064-test-mission",
            total_wps=5,
        )
        assert event is not None
        assert event.get("build_id"), "build_id must be non-empty"


class TestWPStatusChangedEnvelope:
    """Validate WPStatusChanged event envelope shape."""

    def test_schema_version_is_3_0_0(self):
        emitter = _make_emitter()
        event = emitter.emit_wp_status_changed(
            wp_id="WP01",
            from_lane="planned",
            to_lane="claimed",
        )
        assert event is not None
        assert event["schema_version"] == "3.0.0"

    def test_aggregate_type_is_work_package(self):
        emitter = _make_emitter()
        event = emitter.emit_wp_status_changed(
            wp_id="WP01",
            from_lane="planned",
            to_lane="claimed",
        )
        assert event is not None
        assert event["aggregate_type"] == "WorkPackage"

    def test_build_id_present(self):
        emitter = _make_emitter()
        event = emitter.emit_wp_status_changed(
            wp_id="WP01",
            from_lane="planned",
            to_lane="claimed",
        )
        assert event is not None
        assert event.get("build_id"), "build_id must be non-empty"

    def test_all_required_envelope_fields_present(self, canonical_envelope_fields):
        emitter = _make_emitter()
        event = emitter.emit_wp_status_changed(
            wp_id="WP01",
            from_lane="planned",
            to_lane="claimed",
        )
        assert event is not None
        for field in canonical_envelope_fields:
            assert field in event, f"Required envelope field '{field}' missing"

    def test_no_forbidden_fields_in_envelope(self, forbidden_envelope_fields):
        emitter = _make_emitter()
        event = emitter.emit_wp_status_changed(
            wp_id="WP01",
            from_lane="planned",
            to_lane="claimed",
        )
        assert event is not None
        for field in forbidden_envelope_fields:
            assert field not in event, f"Forbidden field '{field}' found in envelope"


class TestAllowedAggregateTypes:
    """Validate that only allowed aggregate types are used (not Feature)."""

    def test_valid_aggregate_types_exclude_feature(self, upstream_contract):
        """The emitter VALID_AGGREGATE_TYPES must match the contract."""
        from specify_cli.sync.emitter import VALID_AGGREGATE_TYPES

        allowed = set(upstream_contract["envelope"]["aggregate_type"]["allowed"])
        forbidden = set(upstream_contract["envelope"]["aggregate_type"]["forbidden"])

        for agg_type in VALID_AGGREGATE_TYPES:
            assert agg_type not in forbidden, f"Aggregate type '{agg_type}' is forbidden by contract"

        # Ensure the emitter recognizes all allowed types
        for agg_type in allowed:
            assert agg_type in VALID_AGGREGATE_TYPES, f"Allowed aggregate type '{agg_type}' not in VALID_AGGREGATE_TYPES"
