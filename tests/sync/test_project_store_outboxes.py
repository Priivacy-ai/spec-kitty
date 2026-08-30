"""Public contract for UUID-owned event and body outboxes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from specify_cli.sync.body_queue import BodyEnqueueResult, OfflineBodyUploadQueue
from specify_cli.sync.queue import OfflineQueue, ProjectOutboxTask
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


PROJECT = "aaaaaaaa-0000-0000-0000-000000000001"
OTHER = "bbbbbbbb-0000-0000-0000-000000000002"


@dataclass(frozen=True)
class _Namespace:
    project_uuid: str
    mission_slug: str = "mission"
    target_branch: str = "develop"
    mission_type: str = "software-dev"
    manifest_version: str = "1"

    def to_dict(self) -> dict[str, str]:
        return self.__dict__


def _project_only(store: ProjectSyncStore) -> None:
    authority = store.layout_generation()
    authority.begin_cutover("wp04-test")
    authority.publish_project_only("wp04-test", verify_exact=lambda: True)


def test_event_and_body_tasks_are_typed_owned_and_sequenced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT)
    _project_only(store)
    event = {
        "event_id": "event-1",
        "event_type": "WPStatusChanged",
        "project_uuid": PROJECT,
        "payload": {"project_uuid": PROJECT},
    }
    with store.unit_of_work() as unit:
        queue = OfflineQueue(unit, store.layout_generation(), max_queue_size=10)
        body_queue = OfflineBodyUploadQueue(unit, store.layout_generation(), max_queue_size=10)
        assert queue.queue_event(event) is True
        assert body_queue.enqueue(_Namespace(PROJECT), "spec.md", "abc", "body", 4) is BodyEnqueueResult.ENQUEUED
        event_task = queue.drain_queue()[0]
        body_task = body_queue.drain()[0]

    assert isinstance(event_task, ProjectOutboxTask)
    assert event_task.project_uuid == PROJECT
    assert body_task.project_uuid == PROJECT
    assert event_task.capture_sequence < body_task.capture_sequence
    assert event_task.epoch_id == body_task.epoch_id


def test_outboxes_reject_foreign_owner_before_insert(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT)
    _project_only(store)
    with store.unit_of_work() as unit:
        queue = OfflineQueue(unit, store.layout_generation())
        body_queue = OfflineBodyUploadQueue(unit, store.layout_generation())
        with pytest.raises(ValueError, match="owner"):
            queue.queue_event({"event_id": "foreign", "event_type": "x", "project_uuid": OTHER, "payload": {}})
        with pytest.raises(ValueError, match="owner"):
            body_queue.enqueue(_Namespace(OTHER), "spec.md", "abc", "body", 4)


def test_journal_outbox_and_body_fault_roll_back_together(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store = ProjectSyncStore(PROJECT)
    _project_only(store)
    with pytest.raises(RuntimeError, match="fault"), store.unit_of_work() as unit:
        queue = OfflineQueue(unit, store.layout_generation())
        body_queue = OfflineBodyUploadQueue(unit, store.layout_generation())
        queue.queue_event({"event_id": "event-1", "event_type": "x", "project_uuid": PROJECT, "payload": {}})
        body_queue.enqueue(_Namespace(PROJECT), "spec.md", "abc", "body", 4)
        raise RuntimeError("fault")

    with store.unit_of_work() as unit:
        assert OfflineQueue(unit, store.layout_generation()).size() == 0
        assert OfflineBodyUploadQueue(unit, store.layout_generation()).size() == 0
