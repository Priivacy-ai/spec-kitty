"""Public contract for explicit, one-store retention operations."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.delivery.retention import purge_project_payloads
from specify_cli.sync.body_queue import OfflineBodyUploadQueue
from specify_cli.sync.queue import OfflineQueue
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


PROJECT_A = "aaaaaaaa-0000-0000-0000-000000000001"
PROJECT_B = "bbbbbbbb-0000-0000-0000-000000000002"


def _project_only(store: ProjectSyncStore) -> None:
    authority = store.layout_generation()
    authority.begin_cutover("wp04-test")
    authority.publish_project_only("wp04-test", verify_exact=lambda: True)


def test_explicit_purge_can_only_observe_and_delete_its_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    store_a = ProjectSyncStore(PROJECT_A)
    store_b = ProjectSyncStore(PROJECT_B)
    _project_only(store_a)
    with store_a.unit_of_work() as unit:
        OfflineQueue(unit, store_a.layout_generation()).queue_event({"event_id": "a", "event_type": "x", "project_uuid": PROJECT_A, "payload": {}})
    with store_b.unit_of_work() as unit:
        OfflineQueue(unit, store_b.layout_generation()).queue_event({"event_id": "b", "event_type": "x", "project_uuid": PROJECT_B, "payload": {}})

    with store_a.unit_of_work() as unit:
        result = purge_project_payloads(unit, store_a.layout_generation())
        assert result.target_before == 1
        assert result.target_after == 0
        assert result.other_project_differential == 0
    with store_b.unit_of_work() as unit:
        assert OfflineQueue(unit, store_b.layout_generation()).size() == 1
        assert OfflineBodyUploadQueue(unit, store_b.layout_generation()).size() == 0
