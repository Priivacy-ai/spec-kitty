"""Project-store layout precondition for the background daemon (#3030/WP10)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.sync.background import (
    BackgroundSyncService,
    LegacyQueueNotConvergedError,
    LegacyQueueUndeterminedError,
)
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


def _service() -> BackgroundSyncService:
    return BackgroundSyncService(queue=None, config=MagicMock())


def _route_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectSyncStore:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    repo = tmp_path / "repo"
    (repo / ".kittify").mkdir(parents=True)
    (repo / ".kittify" / "config.yaml").write_text(
        f"project:\n  uuid: {PROJECT}\n  slug: background-test\n  node_id: node\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo))
    monkeypatch.chdir(repo)
    return ProjectSyncStore(PROJECT)


def _project_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectSyncStore:
    store = _route_project(tmp_path, monkeypatch)
    authority = store.layout_generation()
    authority.begin_cutover("background-layout")
    authority.publish_project_only("background-layout", verify_exact=lambda: True)
    with store.unit_of_work():
        pass
    return store


def test_converged_legacy_queue_starts_normally(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _project_only(tmp_path, monkeypatch)
    _service()._assert_legacy_queue_converged()


def test_unconverged_legacy_rows_fail_loudly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    import logging

    _route_project(tmp_path, monkeypatch)
    with caplog.at_level(logging.ERROR), pytest.raises(LegacyQueueNotConvergedError, match="legacy"):
        _service()._assert_legacy_queue_converged()


def test_guard_does_not_mutate_the_operators_queues(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = _route_project(tmp_path, monkeypatch)
    authority = store.layout_generation()
    before = tuple(path.exists() for path in (store.database_path, authority.record_path, authority.marker_path, authority.lock_path))
    with pytest.raises(LegacyQueueNotConvergedError):
        _service()._assert_legacy_queue_converged()
    assert tuple(path.exists() for path in (store.database_path, authority.record_path, authority.marker_path, authority.lock_path)) == before


def test_an_unreadable_legacy_db_refuses_rather_than_reporting_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = _route_project(tmp_path, monkeypatch)
    authority = store.layout_generation()
    authority.record_path.parent.mkdir(parents=True, exist_ok=True)
    authority.record_path.write_text("{bad", encoding="utf-8")
    with pytest.raises(LegacyQueueUndeterminedError, match="unreadable"):
        _service()._assert_legacy_queue_converged()


def test_an_unexpected_error_type_propagates_instead_of_being_swallowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _route_project(tmp_path, monkeypatch)
    with (
        patch("specify_cli.sync.layout_generation.LayoutGenerationAuthority.peek_state", side_effect=TypeError("shape drift")),
        pytest.raises(LegacyQueueUndeterminedError, match="shape drift"),
    ):
        _service()._assert_legacy_queue_converged()


@pytest.mark.usefixtures("canonical_home")  # R1b (#3121): owner pins SPEC_KITTY_HOME (then _route_project re-pins to tmp_path/runtime, as before)
def test_a_credentials_read_failure_is_not_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _project_only(tmp_path, monkeypatch)
    with patch("specify_cli.sync.queue.read_queue_scope_from_credentials", side_effect=OSError("unused")):
        _service()._assert_legacy_queue_converged()


def test_counter_reads_a_real_legacy_queue_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = _project_only(tmp_path, monkeypatch)
    store.verify_existing_readonly()
    assert not (tmp_path / "home" / "queue.db").exists()


def test_start_refuses_while_legacy_rows_are_stranded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = _route_project(tmp_path, monkeypatch)
    store.layout_generation().begin_cutover("still-cutting-over")
    service = _service()
    with patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True), pytest.raises(LegacyQueueNotConvergedError):
        service.start()
    assert service.is_running is False
    assert service._timer is None
