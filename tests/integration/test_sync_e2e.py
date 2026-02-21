"""End-to-end integration tests for identity-aware CLI event sync.

This module tests the full flow from init to event emission, including:
- T027: Reusable test fixtures
- T028: Init -> implement flow with identity
- T029: Unauthenticated graceful degradation
- T030: Config backfill on existing projects
- T031: Read-only repo fallback to in-memory identity
- T032: No duplicate emissions

These tests validate the acceptance scenarios from spec.md:
- AC-01: project_uuid injected into all emitted events
- AC-02: New projects get identity on init
- AC-03: Existing projects backfill identity on first command
- AC-04: Read-only repos use in-memory identity
- AC-05: Unauthenticated users get queue-only mode
"""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from ruamel.yaml import YAML

from specify_cli.sync.project_identity import (
    ensure_identity,
    load_identity,
)
from specify_cli.sync.queue import OfflineQueue
from specify_cli.sync.emitter import EventEmitter
from specify_cli.sync.runtime import SyncRuntime, reset_runtime


# ── T027: Test Fixtures ──────────────────────────────────────────────


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    """Create temporary git repository."""
    repo = tmp_path / "test-repo"
    repo.mkdir()

    # Initialize git
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create .kittify directory (project context)
    (repo / ".kittify").mkdir()

    return repo


@pytest.fixture
def temp_repo_with_config(temp_repo: Path) -> Path:
    """Temp repo with existing config.yaml (no identity)."""
    config_path = temp_repo / ".kittify" / "config.yaml"
    config_path.write_text("vcs:\n  type: git\n")
    return temp_repo


@pytest.fixture
def mock_queue(tmp_path: Path) -> OfflineQueue:
    """Real OfflineQueue for inspecting queued events."""
    db_path = tmp_path / "test_events.db"
    return OfflineQueue(db_path=db_path)


@pytest.fixture
def mock_websocket() -> MagicMock:
    """Mock WebSocketClient."""
    ws = MagicMock()
    ws.connected = False
    ws.connect = MagicMock()
    ws.send_event = MagicMock()
    ws.disconnect = MagicMock()
    return ws


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singletons before and after each test."""
    reset_runtime()
    from specify_cli.sync.events import reset_emitter

    reset_emitter()
    yield
    reset_runtime()
    from specify_cli.sync.events import reset_emitter

    reset_emitter()


# ── T028: Init -> Implement Flow with Identity ───────────────────────


class TestIdentityAwareFlow:
    """Test full flow from init to event emission with identity."""

    def test_init_creates_identity(self, temp_repo: Path) -> None:
        """spec-kitty init creates config.yaml with identity."""
        # Trigger identity creation
        identity = ensure_identity(temp_repo)

        # Verify identity created
        assert identity.project_uuid is not None
        assert isinstance(identity.project_uuid, UUID)
        assert identity.project_slug == "test-repo"
        assert identity.node_id is not None
        assert len(identity.node_id) == 12

        # Verify persisted
        config_path = temp_repo / ".kittify" / "config.yaml"
        assert config_path.exists()

        # Load and verify
        identity2 = load_identity(config_path)
        assert identity2.project_uuid == identity.project_uuid
        assert identity2.project_slug == identity.project_slug
        assert identity2.node_id == identity.node_id

    def test_identity_is_idempotent(self, temp_repo: Path) -> None:
        """Multiple calls to ensure_identity return same identity."""
        identity1 = ensure_identity(temp_repo)
        identity2 = ensure_identity(temp_repo)
        identity3 = ensure_identity(temp_repo)

        assert identity1.project_uuid == identity2.project_uuid
        assert identity2.project_uuid == identity3.project_uuid

    def test_event_contains_identity(self, temp_repo: Path, mock_queue: OfflineQueue, tmp_path: Path) -> None:
        """Emitted events contain project_uuid and project_slug."""
        # Create identity first
        identity = ensure_identity(temp_repo)

        # Create emitter with the identity
        from specify_cli.sync.clock import LamportClock
        from specify_cli.sync.config import SyncConfig

        clock_path = tmp_path / "clock.json"
        clock = LamportClock(value=0, node_id="test-node", _storage_path=clock_path)
        mock_config = MagicMock(spec=SyncConfig)
        mock_config.get_server_url.return_value = "https://test.spec-kitty.dev"
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_access_token.return_value = "test-token"
        mock_auth.get_team_slug.return_value = "test-team"

        emitter = EventEmitter(
            clock=clock,
            config=mock_config,
            queue=mock_queue,
            _auth=mock_auth,
            ws_client=None,
            _identity=identity,
        )

        event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

        assert event is not None
        assert "project_uuid" in event
        assert event["project_uuid"] == str(identity.project_uuid)
        assert "project_slug" in event
        assert event["project_slug"] == identity.project_slug

        # Verify it's a valid UUID string
        UUID(event["project_uuid"])  # Should not raise

    def test_implement_emits_status_change(self, temp_repo: Path, mock_queue: OfflineQueue, tmp_path: Path) -> None:
        """Implement command triggers WPStatusChanged event."""
        identity = ensure_identity(temp_repo)

        from specify_cli.sync.clock import LamportClock
        from specify_cli.sync.config import SyncConfig

        clock_path = tmp_path / "clock.json"
        clock = LamportClock(value=0, node_id="test-node", _storage_path=clock_path)
        mock_config = MagicMock(spec=SyncConfig)
        mock_config.get_server_url.return_value = "https://test.spec-kitty.dev"
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_access_token.return_value = "test-token"
        mock_auth.get_team_slug.return_value = "test-team"

        emitter = EventEmitter(
            clock=clock,
            config=mock_config,
            queue=mock_queue,
            _auth=mock_auth,
            ws_client=None,
            _identity=identity,
        )

        # Emit event like implement command would
        event = emitter.emit_wp_status_changed(
            wp_id="WP01",
            from_lane="planned",
            to_lane="in_progress",
            actor="claude-opus",
        )

        assert event is not None
        assert event["event_type"] == "WPStatusChanged"
        assert event["payload"]["wp_id"] == "WP01"
        assert event["payload"]["from_lane"] == "planned"
        assert event["payload"]["to_lane"] == "in_progress"

        # Event should be queued
        assert mock_queue.size() == 1


# ── T029: Unauthenticated Graceful Degradation ───────────────────────


class TestUnauthenticatedGracefulDegradation:
    """Test queue-only mode when not authenticated."""

    def test_unauthenticated_queues_only(
        self, temp_repo: Path, mock_queue: OfflineQueue, tmp_path: Path, monkeypatch
    ) -> None:
        """Events are queued (not sent via WS) when unauthenticated."""
        monkeypatch.chdir(temp_repo)
        identity = ensure_identity(temp_repo)

        from specify_cli.sync.clock import LamportClock
        from specify_cli.sync.config import SyncConfig

        clock_path = tmp_path / "clock.json"
        clock = LamportClock(value=0, node_id="test-node", _storage_path=clock_path)
        mock_config = MagicMock(spec=SyncConfig)
        mock_config.get_server_url.return_value = "https://test.spec-kitty.dev"

        # Unauthenticated client - return plain string (not MagicMock) to avoid JSON serialization issues
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = False
        mock_auth.get_access_token.return_value = None
        mock_auth.get_team_slug.return_value = None

        emitter = EventEmitter(
            clock=clock,
            config=mock_config,
            queue=mock_queue,
            _auth=mock_auth,
            ws_client=None,  # No WebSocket when unauthenticated
            _identity=identity,
        )

        # Emit event
        event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

        # Event should still be created and queued
        assert event is not None
        assert mock_queue.size() == 1

    def test_runtime_no_websocket_when_unauthenticated(self, temp_repo: Path, monkeypatch) -> None:
        """SyncRuntime doesn't create WebSocket when not authenticated."""
        monkeypatch.chdir(temp_repo)

        mock_service = MagicMock()
        with patch("specify_cli.sync.background.get_sync_service") as mock_get_service:
            mock_get_service.return_value = mock_service
            with patch("specify_cli.sync.auth.AuthClient") as mock_auth_class:
                mock_auth = MagicMock()
                mock_auth.is_authenticated.return_value = False
                mock_auth_class.return_value = mock_auth

                runtime = SyncRuntime()
                runtime.start()

                # WebSocket should not be connected
                assert runtime.ws_client is None
                # Background service should still be running
                assert runtime.background_service is not None

                runtime.stop()


# ── T030: Config Backfill on Existing Project ────────────────────────


class TestConfigBackfill:
    """Test identity backfill for existing projects without identity."""

    def test_backfill_existing_config(self, temp_repo_with_config: Path) -> None:
        """Identity added to existing config.yaml without overwriting other fields."""
        config_path = temp_repo_with_config / ".kittify" / "config.yaml"

        # Verify config exists but has no identity
        yaml = YAML()
        with open(config_path) as f:
            config = yaml.load(f)
        assert "project" not in config
        assert config["vcs"]["type"] == "git"

        # Trigger backfill
        identity = ensure_identity(temp_repo_with_config)

        # Verify identity created
        assert identity.is_complete
        assert isinstance(identity.project_uuid, UUID)

        # Verify other fields preserved
        with open(config_path) as f:
            config = yaml.load(f)
        assert config["vcs"]["type"] == "git"  # Preserved
        assert config["project"]["uuid"] is not None  # Added
        assert config["project"]["slug"] == "test-repo"  # Added

    def test_backfill_partial_identity(self, temp_repo: Path) -> None:
        """Backfills missing fields in partial identity."""
        config_path = temp_repo / ".kittify" / "config.yaml"

        # Write partial identity (only UUID)
        yaml = YAML()
        existing_uuid = "12345678-1234-5678-1234-567812345678"
        with open(config_path, "w") as f:
            yaml.dump({"project": {"uuid": existing_uuid}}, f)

        # Trigger backfill
        identity = ensure_identity(temp_repo)

        # Existing UUID preserved
        assert str(identity.project_uuid) == existing_uuid
        # Missing fields generated
        assert identity.project_slug is not None
        assert identity.node_id is not None
        assert identity.is_complete


# ── T031: Read-Only Repo Fallback ────────────────────────────────────


class TestReadOnlyFallback:
    """Test in-memory identity when config is not writable."""

    def test_readonly_fallback_existing_config(self, temp_repo: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Read-only existing config uses in-memory identity with warning."""
        config_path = temp_repo / ".kittify" / "config.yaml"

        # Create config
        config_path.write_text("vcs:\n  type: git\n")

        # Make read-only
        config_path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

        try:
            identity = ensure_identity(temp_repo)

            # Identity should still be complete (in-memory)
            assert identity.is_complete
            assert isinstance(identity.project_uuid, UUID)

            # Config should NOT have identity (couldn't write)
            yaml = YAML()
            with open(config_path) as f:
                config = yaml.load(f)
            assert "project" not in config
        finally:
            # Restore permissions for cleanup
            config_path.chmod(stat.S_IRUSR | stat.S_IWUSR)

    def test_readonly_directory_fallback(self, temp_repo: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Read-only .kittify directory uses in-memory identity."""
        kittify_dir = temp_repo / ".kittify"

        # Make directory read-only
        kittify_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)

        try:
            identity = ensure_identity(temp_repo)

            # Identity should still be complete (in-memory)
            assert identity.is_complete
        finally:
            # Restore permissions for cleanup
            kittify_dir.chmod(stat.S_IRWXU)


# ── T032: No Duplicate Emissions ─────────────────────────────────────


class TestNoDuplicateEmissions:
    """Test that each command emits exactly one status change."""

    def test_single_emission_per_transition(self, temp_repo: Path, mock_queue: OfflineQueue, tmp_path: Path) -> None:
        """Commands emit exactly one WPStatusChanged per transition."""
        identity = ensure_identity(temp_repo)

        from specify_cli.sync.clock import LamportClock
        from specify_cli.sync.config import SyncConfig

        clock_path = tmp_path / "clock.json"
        clock = LamportClock(value=0, node_id="test-node", _storage_path=clock_path)
        mock_config = MagicMock(spec=SyncConfig)
        mock_config.get_server_url.return_value = "https://test.spec-kitty.dev"
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_access_token.return_value = "test-token"
        mock_auth.get_team_slug.return_value = "test-team"

        emitter = EventEmitter(
            clock=clock,
            config=mock_config,
            queue=mock_queue,
            _auth=mock_auth,
            ws_client=None,
            _identity=identity,
        )

        # Simulate implement command (planned -> doing)
        emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        assert mock_queue.size() == 1

        # Simulate move-task (doing -> for_review)
        emitter.emit_wp_status_changed("WP01", "in_progress", "for_review")
        assert mock_queue.size() == 2

        # Simulate accept (for_review -> done)
        emitter.emit_wp_status_changed("WP01", "for_review", "done")
        assert mock_queue.size() == 3

        # Each transition is exactly one event
        events = mock_queue.drain_queue()
        assert len(events) == 3

        # Verify no duplicates (all unique event_id)
        event_ids = [e["event_id"] for e in events]
        assert len(set(event_ids)) == 3

    def test_causation_chain_no_duplicates(self, temp_repo: Path, mock_queue: OfflineQueue, tmp_path: Path) -> None:
        """Causation chain doesn't cause duplicate emissions."""
        identity = ensure_identity(temp_repo)

        from specify_cli.sync.clock import LamportClock
        from specify_cli.sync.config import SyncConfig

        clock_path = tmp_path / "clock.json"
        clock = LamportClock(value=0, node_id="test-node", _storage_path=clock_path)
        mock_config = MagicMock(spec=SyncConfig)
        mock_config.get_server_url.return_value = "https://test.spec-kitty.dev"
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_access_token.return_value = "test-token"
        mock_auth.get_team_slug.return_value = "test-team"

        emitter = EventEmitter(
            clock=clock,
            config=mock_config,
            queue=mock_queue,
            _auth=mock_auth,
            ws_client=None,
            _identity=identity,
        )

        # Simulate finalize-tasks batch with causation chain
        causation_id = emitter.generate_causation_id()

        emitter.emit_feature_created(
            feature_slug="032-identity-aware",
            feature_number="032",
            target_branch="main",
            wp_count=3,
            causation_id=causation_id,
        )

        for i in range(1, 4):
            emitter.emit_wp_created(
                wp_id=f"WP{i:02d}",
                title=f"Work Package {i}",
                feature_slug="032-identity-aware",
                dependencies=[f"WP{i - 1:02d}"] if i > 1 else [],
                causation_id=causation_id,
            )

        # Should be exactly 4 events (1 FeatureCreated + 3 WPCreated)
        assert mock_queue.size() == 4

        events = mock_queue.drain_queue()
        assert len(events) == 4

        # All share same causation_id
        for e in events:
            assert e["causation_id"] == causation_id


# ── Additional E2E Scenarios ─────────────────────────────────────────


class TestFullWorkflowIntegration:
    """Full workflow integration tests."""

    def test_full_wp_lifecycle(self, temp_repo: Path, mock_queue: OfflineQueue, tmp_path: Path) -> None:
        """Test complete WP lifecycle: create -> implement -> review -> done."""
        identity = ensure_identity(temp_repo)

        from specify_cli.sync.clock import LamportClock
        from specify_cli.sync.config import SyncConfig

        clock_path = tmp_path / "clock.json"
        clock = LamportClock(value=0, node_id="test-node", _storage_path=clock_path)
        mock_config = MagicMock(spec=SyncConfig)
        mock_config.get_server_url.return_value = "https://test.spec-kitty.dev"
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_access_token.return_value = "test-token"
        mock_auth.get_team_slug.return_value = "test-team"

        emitter = EventEmitter(
            clock=clock,
            config=mock_config,
            queue=mock_queue,
            _auth=mock_auth,
            ws_client=None,
            _identity=identity,
        )

        causation_id = emitter.generate_causation_id()

        # 1. Feature created (use valid feature_slug pattern: ###-slug-name)
        emitter.emit_feature_created(
            feature_slug="001-test-feature",
            feature_number="001",
            target_branch="main",
            wp_count=1,
            causation_id=causation_id,
        )

        # 2. WP created (use valid feature_slug pattern: ###-slug-name)
        emitter.emit_wp_created(
            wp_id="WP01",
            title="Test Work Package",
            feature_slug="001-test-feature",
            dependencies=[],
            causation_id=causation_id,
        )

        # 3. WP assigned
        emitter.emit_wp_assigned(
            wp_id="WP01",
            agent_id="claude-opus",
            phase="implementation",
        )

        # 4. Implement (planned -> doing)
        emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

        # 5. Submit for review (doing -> for_review)
        emitter.emit_wp_status_changed("WP01", "in_progress", "for_review")

        # 6. Accept (for_review -> done)
        emitter.emit_wp_status_changed("WP01", "for_review", "done")

        # 7. Feature completed (use valid feature_slug pattern: ###-slug-name)
        emitter.emit_feature_completed(
            feature_slug="001-test-feature",
            total_wps=1,
        )

        events = mock_queue.drain_queue()
        assert len(events) == 7

        # All events have project identity
        for e in events:
            assert e["project_uuid"] == str(identity.project_uuid)
            assert e["project_slug"] == identity.project_slug

        # Verify event types in order
        event_types = [e["event_type"] for e in events]
        assert event_types == [
            "FeatureCreated",
            "WPCreated",
            "WPAssigned",
            "WPStatusChanged",
            "WPStatusChanged",
            "WPStatusChanged",
            "FeatureCompleted",
        ]

    def test_events_queued_when_offline(self, temp_repo: Path, mock_queue: OfflineQueue, tmp_path: Path) -> None:
        """Events are queued for later sync when offline."""
        identity = ensure_identity(temp_repo)

        from specify_cli.sync.clock import LamportClock
        from specify_cli.sync.config import SyncConfig

        clock_path = tmp_path / "clock.json"
        clock = LamportClock(value=0, node_id="test-node", _storage_path=clock_path)
        mock_config = MagicMock(spec=SyncConfig)
        mock_config.get_server_url.return_value = "https://test.spec-kitty.dev"
        # Return plain values instead of MagicMock to avoid JSON serialization issues
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = False
        mock_auth.get_access_token.return_value = None
        mock_auth.get_team_slug.return_value = None

        emitter = EventEmitter(
            clock=clock,
            config=mock_config,
            queue=mock_queue,
            _auth=mock_auth,
            ws_client=None,  # No WebSocket
            _identity=identity,
        )

        # Emit several events while "offline"
        emitter.emit_wp_status_changed("WP01", "planned", "in_progress")
        emitter.emit_wp_status_changed("WP02", "planned", "in_progress")
        emitter.emit_wp_status_changed("WP01", "in_progress", "for_review")

        # All events should be queued
        assert mock_queue.size() == 3

        # Events can be drained for later sync (drain_queue retrieves but doesn't remove)
        events = mock_queue.drain_queue()
        assert len(events) == 3

        # Queue still has events (drain doesn't remove - mark_synced does)
        assert mock_queue.size() == 3

        # Simulate successful sync by marking events as synced
        event_ids = [e["event_id"] for e in events]
        mock_queue.mark_synced(event_ids)

        # Queue is now empty
        assert mock_queue.size() == 0


class TestEventPayloadValidation:
    """Test event payload structure and validation."""

    def test_wp_status_changed_payload(self, temp_repo: Path, mock_queue: OfflineQueue, tmp_path: Path) -> None:
        """WPStatusChanged has correct payload structure."""
        identity = ensure_identity(temp_repo)

        from specify_cli.sync.clock import LamportClock
        from specify_cli.sync.config import SyncConfig

        clock_path = tmp_path / "clock.json"
        clock = LamportClock(value=0, node_id="test-node", _storage_path=clock_path)
        mock_config = MagicMock(spec=SyncConfig)
        mock_config.get_server_url.return_value = "https://test.spec-kitty.dev"
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_access_token.return_value = "test-token"
        mock_auth.get_team_slug.return_value = "test-team"

        emitter = EventEmitter(
            clock=clock,
            config=mock_config,
            queue=mock_queue,
            _auth=mock_auth,
            ws_client=None,
            _identity=identity,
        )

        event = emitter.emit_wp_status_changed(
            wp_id="WP01",
            from_lane="planned",
            to_lane="in_progress",
            actor="claude-opus",
            feature_slug="test-feature",
        )

        # Required fields
        assert event["event_type"] == "WPStatusChanged"
        assert "event_id" in event
        assert "timestamp" in event
        assert "project_uuid" in event
        assert "project_slug" in event

        # Payload fields
        payload = event["payload"]
        assert payload["wp_id"] == "WP01"
        assert payload["from_lane"] == "planned"
        assert payload["to_lane"] == "in_progress"
        assert payload["actor"] == "claude-opus"
        assert payload["feature_slug"] == "test-feature"

    def test_event_id_is_ulid(self, temp_repo: Path, mock_queue: OfflineQueue, tmp_path: Path) -> None:
        """Event IDs are valid ULIDs."""
        identity = ensure_identity(temp_repo)

        from specify_cli.sync.clock import LamportClock
        from specify_cli.sync.config import SyncConfig
        import re

        clock_path = tmp_path / "clock.json"
        clock = LamportClock(value=0, node_id="test-node", _storage_path=clock_path)
        mock_config = MagicMock(spec=SyncConfig)
        mock_config.get_server_url.return_value = "https://test.spec-kitty.dev"
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_access_token.return_value = "test-token"
        mock_auth.get_team_slug.return_value = "test-team"

        emitter = EventEmitter(
            clock=clock,
            config=mock_config,
            queue=mock_queue,
            _auth=mock_auth,
            ws_client=None,
            _identity=identity,
        )

        event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

        # ULID pattern: 26 characters from Crockford's base32 alphabet
        ulid_pattern = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
        assert ulid_pattern.match(event["event_id"]) is not None

    def test_timestamp_is_iso8601(self, temp_repo: Path, mock_queue: OfflineQueue, tmp_path: Path) -> None:
        """Event timestamps are ISO 8601 format."""
        identity = ensure_identity(temp_repo)

        from specify_cli.sync.clock import LamportClock
        from specify_cli.sync.config import SyncConfig
        from datetime import datetime

        clock_path = tmp_path / "clock.json"
        clock = LamportClock(value=0, node_id="test-node", _storage_path=clock_path)
        mock_config = MagicMock(spec=SyncConfig)
        mock_config.get_server_url.return_value = "https://test.spec-kitty.dev"
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_access_token.return_value = "test-token"
        mock_auth.get_team_slug.return_value = "test-team"

        emitter = EventEmitter(
            clock=clock,
            config=mock_config,
            queue=mock_queue,
            _auth=mock_auth,
            ws_client=None,
            _identity=identity,
        )

        event = emitter.emit_wp_status_changed("WP01", "planned", "in_progress")

        # Should parse as ISO 8601
        ts = event["timestamp"]
        # Handle Z suffix
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        parsed = datetime.fromisoformat(ts)
        assert parsed is not None
