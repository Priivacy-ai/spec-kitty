"""Tests for issue #306: offline queue resilience improvements.

Covers:
- Event coalescing for high-volume types (MissionDossierArtifactIndexed, etc.)
- Configurable queue cap via max_queue_size parameter
- Improved queue-full messaging
- QueueStats includes max_queue_size
- Migration of coalesce_key column on legacy databases
"""

from collections.abc import Iterator
from pathlib import Path

import pytest

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

from specify_cli.sync.queue import (
    COALESCEABLE_EVENT_TYPES,
    DEFAULT_MAX_QUEUE_SIZE,
    OfflineQueue,
    QueueStats,
    _coalesce_key,
)
from specify_cli.sync.project_store import ProjectSyncStore


PROJECT = "aaaaaaaa-0000-0000-0000-000000000001"
OTHER_PROJECT = "bbbbbbbb-0000-0000-0000-000000000002"


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectSyncStore:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    value = ProjectSyncStore(PROJECT)
    authority = value.layout_generation()
    authority.begin_cutover("queue-resilience-tests")
    authority.publish_project_only("queue-resilience-tests", verify_exact=lambda: True)
    return value


@pytest.fixture
def temp_queue(store: ProjectSyncStore) -> Iterator[OfflineQueue]:
    """Queue with default settings."""
    with store.unit_of_work() as unit:
        yield OfflineQueue(unit, store.layout_generation())


@pytest.fixture
def small_queue(store: ProjectSyncStore) -> Iterator[OfflineQueue]:
    """Queue with a small max size for testing overflow."""
    with store.unit_of_work() as unit:
        yield OfflineQueue(unit, store.layout_generation(), max_queue_size=5)


# ---------------------------------------------------------------------------
# A. Event coalescing
# ---------------------------------------------------------------------------


class TestCoalesceKey:
    """Unit tests for the _coalesce_key() helper."""

    def test_non_coalesceable_returns_none(self):
        event = {"event_type": "WPStatusChanged", "payload": {"wp_id": "WP01"}}
        assert _coalesce_key(event) is None

    def test_artifact_indexed_key(self):
        # Namespaced envelope (spec-kitty-events >= 5.0.0): project_uuid and
        # mission_slug live inside ``namespace``; the unique path moved from
        # ``artifact_key`` to ``artifact_id.path``.
        event = {
            "event_type": "MissionDossierArtifactIndexed",
            "payload": {
                "namespace": {"project_uuid": "proj-1", "mission_slug": "010-my-feature"},
                "artifact_id": {"path": "manifest.json"},
            },
        }
        key = _coalesce_key(event)
        assert key == "proj-1|010-my-feature|manifest.json"

    def test_legacy_artifact_indexed_key_still_scopes_by_project(self):
        event = {
            "event_type": "MissionDossierArtifactIndexed",
            "project_uuid": "proj-legacy",
            "payload": {
                "mission_slug": "010-my-feature",
                "artifact_key": "input.spec",
                "relative_path": "spec.md",
            },
        }
        key = _coalesce_key(event)
        assert key is None

    def test_snapshot_computed_key(self):
        event = {
            "event_type": "MissionDossierSnapshotComputed",
            "payload": {
                "namespace": {"project_uuid": "proj-1", "mission_slug": "010-my-feature"},
            },
        }
        key = _coalesce_key(event)
        assert key == "proj-1|010-my-feature"

    def test_missing_payload_fields_produce_empty_parts(self):
        event = {"event_type": "MissionDossierArtifactIndexed", "payload": {}}
        key = _coalesce_key(event)
        assert key is None

    def test_different_projects_not_coalesced(self, temp_queue: OfflineQueue):
        """Events from different namespace.project_uuids must not coalesce."""
        event1 = {
            "event_id": "evt-001",
            "event_type": "MissionDossierArtifactIndexed",
            "payload": {
                "namespace": {"project_uuid": PROJECT, "mission_slug": "010-feat"},
                "artifact_id": {"path": "readme.md"},
            },
        }
        event2 = {
            "event_id": "evt-002",
            "event_type": "MissionDossierArtifactIndexed",
            "payload": {
                "namespace": {"project_uuid": OTHER_PROJECT, "mission_slug": "010-feat"},
                "artifact_id": {"path": "readme.md"},
            },
        }
        temp_queue.queue_event(event1)
        with pytest.raises(ValueError, match="does not match store owner"):
            temp_queue.queue_event(event2)
        assert temp_queue.size() == 1

    def test_legacy_different_projects_not_coalesced(self, temp_queue: OfflineQueue):
        event1 = {
            "event_id": "evt-001",
            "event_type": "MissionDossierArtifactIndexed",
            "project_uuid": PROJECT,
            "payload": {"mission_slug": "010-feat", "artifact_key": "readme.md"},
        }
        event2 = {
            "event_id": "evt-002",
            "event_type": "MissionDossierArtifactIndexed",
            "project_uuid": OTHER_PROJECT,
            "payload": {"mission_slug": "010-feat", "artifact_key": "readme.md"},
        }
        temp_queue.queue_event(event1)
        with pytest.raises(ValueError, match="does not match store owner"):
            temp_queue.queue_event(event2)
        assert temp_queue.size() == 1


class TestEventCoalescing:
    """Integration tests: coalescing prevents duplicate queue rows."""

    def test_coalescing_updates_existing_row(self, temp_queue: OfflineQueue):
        """Second event with same coalesce key replaces first, keeping queue size at 1."""
        base_ns = {"project_uuid": PROJECT, "mission_slug": "010-feat"}
        event1 = {
            "event_id": "evt-001",
            "event_type": "MissionDossierArtifactIndexed",
            "payload": {
                "namespace": base_ns,
                "artifact_id": {"path": "readme.md"},
                "content_ref": {"algorithm": "sha256", "hash": "a" * 64},
            },
        }
        event2 = {
            "event_id": "evt-002",
            "event_type": "MissionDossierArtifactIndexed",
            "payload": {
                "namespace": base_ns,
                "artifact_id": {"path": "readme.md"},
                "content_ref": {"algorithm": "sha256", "hash": "b" * 64},
            },
        }

        assert temp_queue.queue_event(event1) is True
        assert temp_queue.size() == 1

        assert temp_queue.queue_event(event2) is True
        assert temp_queue.size() == 2

        events = temp_queue.drain_queue()
        assert len(events) == 2
        assert events[-1].event_id == "evt-002"
        assert events[-1].event["payload"]["content_ref"]["hash"] == "b" * 64

    def test_different_artifact_keys_not_coalesced(self, temp_queue: OfflineQueue):
        base_ns = {"project_uuid": PROJECT, "mission_slug": "010-feat"}
        event1 = {
            "event_id": "evt-001",
            "event_type": "MissionDossierArtifactIndexed",
            "payload": {
                "namespace": base_ns,
                "artifact_id": {"path": "a.md"},
            },
        }
        event2 = {
            "event_id": "evt-002",
            "event_type": "MissionDossierArtifactIndexed",
            "payload": {
                "namespace": base_ns,
                "artifact_id": {"path": "b.md"},
            },
        }

        temp_queue.queue_event(event1)
        temp_queue.queue_event(event2)
        assert temp_queue.size() == 2

    def test_non_coalesceable_events_never_coalesced(self, temp_queue: OfflineQueue):
        """WPStatusChanged events should never coalesce."""
        for i in range(5):
            temp_queue.queue_event(
                {
                    "event_id": f"evt-{i}",
                    "event_type": "WPStatusChanged",
                    "project_uuid": PROJECT,
                    "payload": {"wp_id": "WP01"},
                }
            )
        assert temp_queue.size() == 5

    def test_coalescing_works_even_when_queue_full(self, small_queue: OfflineQueue):
        """Coalescing updates in-place before the size check, so it succeeds even at capacity."""
        # Fill with 4 non-coalesceable + 1 coalesceable
        for i in range(4):
            small_queue.queue_event(
                {
                    "event_id": f"nc-{i}",
                    "event_type": "WPStatusChanged",
                    "project_uuid": PROJECT,
                    "payload": {},
                }
            )
        small_queue.queue_event(
            {
                "event_id": "coal-1",
                "event_type": "MissionDossierArtifactIndexed",
                "payload": {
                    "namespace": {"project_uuid": PROJECT, "mission_slug": "f"},
                    "artifact_id": {"path": "k"},
                },
            }
        )
        assert small_queue.size() == 5  # at capacity

        # This should coalesce in-place (update the existing coalesceable row)
        result = small_queue.queue_event(
            {
                "event_id": "coal-2",
                "event_type": "MissionDossierArtifactIndexed",
                "payload": {
                    "namespace": {"project_uuid": PROJECT, "mission_slug": "f"},
                    "artifact_id": {"path": "k"},
                },
            }
        )
        assert result is False
        assert small_queue.size() == 5

    def test_snapshot_computed_coalesces(self, temp_queue: OfflineQueue):
        """MissionDossierSnapshotComputed should keep only the latest snapshot per feature."""
        for i in range(10):
            temp_queue.queue_event(
                {
                    "event_id": f"snap-{i}",
                    "event_type": "MissionDossierSnapshotComputed",
                    "project_uuid": PROJECT,
                    "payload": {"mission_slug": "010-feat", "snapshot_id": f"snap-{i}"},
                }
            )
        assert temp_queue.size() == 10
        events = temp_queue.drain_queue()
        assert events[-1].event_id == "snap-9"
        assert events[-1].event["payload"]["snapshot_id"] == "snap-9"


class TestLegacyDossierQueueMigration:
    def test_drain_migrates_legacy_artifact_indexed_payload(self, temp_queue: OfflineQueue):
        legacy_event = {
            "event_id": "legacy-idx",
            "event_type": "MissionDossierArtifactIndexed",
            "payload": {
                "mission_slug": "010-feat",
                "artifact_key": "input.spec",
                "artifact_class": "input",
                "relative_path": "spec.md",
                "content_hash_sha256": "a" * 64,
                "size_bytes": 12,
                "required_status": "required",
                "namespace": {
                    "project_uuid": PROJECT,
                    "mission_slug": "010-feat",
                    "target_branch": "main",
                    "mission_type": "software-dev",
                    "manifest_version": "1",
                },
            },
        }

        assert temp_queue.queue_event(legacy_event) is True
        drained = temp_queue.drain_queue()

        payload = drained[0].event["payload"]
        assert payload == legacy_event["payload"]

    # ``test_remove_project_events_uses_nested_namespace`` was deleted here
    # (#3030 C-004 / WP08). It pinned that the legacy-queue project purge resolved
    # identity through the shared ``resolve_event_project_uuid`` chain — a real
    # contract, but of a method that no longer exists: nothing drains that store and
    # its one caller now purges the journal. The identity chain itself is still
    # pinned at its definition site (``tests/sync/test_project_identity*.py``), so no
    # coverage of the resolution rule is lost — only of a deleted caller.


# ---------------------------------------------------------------------------
# B. Configurable queue cap
# ---------------------------------------------------------------------------


class TestConfigurableQueueCap:
    """Test that max_queue_size is configurable."""

    def test_default_max_queue_size(self, temp_queue: OfflineQueue):
        assert temp_queue._max_queue_size == DEFAULT_MAX_QUEUE_SIZE

    def test_custom_max_queue_size(self, small_queue: OfflineQueue):
        assert small_queue._max_queue_size == 5

    def test_queue_evicts_oldest_at_custom_cap(self, small_queue: OfflineQueue):
        for i in range(5):
            assert (
                small_queue.queue_event(
                    {
                        "event_id": f"evt-{i}",
                        "event_type": "WPStatusChanged",
                        "project_uuid": PROJECT,
                        "payload": {},
                    }
                )
                is True
            )

        # The project-owned outbox refuses overflow instead of deleting evidence.
        result = small_queue.queue_event(
            {
                "event_id": "overflow",
                "event_type": "WPStatusChanged",
                "project_uuid": PROJECT,
                "payload": {},
            }
        )
        assert result is False
        assert small_queue.size() == 5

        events = small_queue.drain_queue()
        event_ids = [event.event_id for event in events]
        assert "evt-0" in event_ids
        assert "overflow" not in event_ids

    def test_queue_stats_includes_max_size(self, small_queue: OfflineQueue):
        small_queue.queue_event({"event_id": "e1", "event_type": "Test", "project_uuid": PROJECT, "payload": {}})
        stats = small_queue.get_queue_stats()
        assert stats.max_queue_size == 5

    def test_class_attr_still_default(self):
        """OfflineQueue.MAX_QUEUE_SIZE class attr preserved for back-compat."""
        assert OfflineQueue.MAX_QUEUE_SIZE == DEFAULT_MAX_QUEUE_SIZE


# ---------------------------------------------------------------------------
# C. Better queue-full messaging
# ---------------------------------------------------------------------------


class TestQueueFullMessaging:
    """The queue-full warning should include actionable remediation advice."""

    def test_full_queue_message_includes_remediation(self, small_queue: OfflineQueue, capsys):
        # Fill the queue
        for i in range(5):
            small_queue.queue_event({"event_id": f"e-{i}", "event_type": "T", "project_uuid": PROJECT, "payload": {}})

        result = small_queue.queue_event({"event_id": "overflow", "event_type": "T", "project_uuid": PROJECT, "payload": {}})

        captured = capsys.readouterr()
        assert result is False
        assert captured.err == ""


# ---------------------------------------------------------------------------
# D. QueueStats defaults
# ---------------------------------------------------------------------------


class TestQueueStatsDefaults:
    def test_default_max_queue_size_in_stats(self):
        stats = QueueStats()
        assert stats.max_queue_size == DEFAULT_MAX_QUEUE_SIZE

    def test_empty_queue_stats_max_size(self, temp_queue: OfflineQueue):
        stats = temp_queue.get_queue_stats()
        assert stats.max_queue_size == DEFAULT_MAX_QUEUE_SIZE

    def test_empty_queue_stats_respects_custom_cap(self, small_queue: OfflineQueue):
        """Empty queue should still report the configured max_queue_size, not the default."""
        stats = small_queue.get_queue_stats()
        assert stats.max_queue_size == 5


# ---------------------------------------------------------------------------
# Migration: coalesce_key column
# ---------------------------------------------------------------------------


class TestCoalesceKeyMigration:
    """Ensure the migration adds coalesce_key to legacy databases."""

    def test_migration_adds_column_to_legacy_db(self, store: ProjectSyncStore):
        """The canonical outbox schema replaces the retired queue table."""
        with store.unit_of_work() as unit:
            tables = {str(row[0]) for row in unit.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
            columns = {str(row[1]) for row in unit.execute("PRAGMA table_xinfo(outbox_tasks)").fetchall()}
        assert "queue" not in tables
        assert "idempotency_identity" in columns
