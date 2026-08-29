"""Fail-closed WP10 layout authority controls for background startup."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.sync.background import (
    BackgroundSyncService,
    LegacyQueueNotConvergedError,
    LegacyQueueUndeterminedError,
)
from specify_cli.sync.layout_generation import LayoutMode
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


def _routed_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ProjectSyncStore:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime"))
    repo = tmp_path / "repo"
    (repo / ".kittify").mkdir(parents=True)
    (repo / ".kittify" / "config.yaml").write_text(
        f"project:\n  uuid: {PROJECT}\n  slug: guard\n  node_id: guard-node\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo))
    monkeypatch.chdir(repo)
    return ProjectSyncStore(PROJECT)


def _publish(store: ProjectSyncStore) -> None:
    authority = store.layout_generation()
    authority.begin_cutover("guard")
    authority.publish_project_only("guard", verify_exact=lambda: True)
    with store.unit_of_work():
        pass


def _service() -> BackgroundSyncService:
    return BackgroundSyncService(queue=None, config=MagicMock())


class TestCounterIsAnchoredToARealQueue:
    def test_counts_the_rows_a_real_legacy_queue_actually_holds(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        store = _routed_store(tmp_path, monkeypatch)
        assert store.layout_generation().peek_state().mode is LayoutMode.LEGACY
        with pytest.raises(LegacyQueueNotConvergedError):
            _service()._assert_legacy_queue_converged()

    def test_no_legacy_db_is_a_genuine_zero(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        store = _routed_store(tmp_path, monkeypatch)
        _publish(store)
        _service()._assert_legacy_queue_converged()
        assert not (tmp_path / "runtime" / "queue.db").exists()

    def test_a_renamed_count_field_fails_loudly_instead_of_reporting_clean(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        store = _routed_store(tmp_path, monkeypatch)
        authority = store.layout_generation()
        authority.record_path.parent.mkdir(parents=True, exist_ok=True)
        authority.record_path.write_text('{"generation":"wrong"}', encoding="utf-8")
        with pytest.raises(LegacyQueueUndeterminedError):
            _service()._assert_legacy_queue_converged()

    def test_a_changed_arity_fails_loudly_instead_of_reporting_clean(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _routed_store(tmp_path, monkeypatch)
        with (
            patch("specify_cli.sync.layout_generation.LayoutGenerationAuthority.peek_state", side_effect=TypeError("changed shape")),
            pytest.raises(LegacyQueueUndeterminedError, match="changed shape"),
        ):
            _service()._assert_legacy_queue_converged()


class TestUndeterminedIsNotPermission:
    def test_unreadable_legacy_db_reports_undetermined_not_zero(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        store = _routed_store(tmp_path, monkeypatch)
        authority = store.layout_generation()
        authority.record_path.parent.mkdir(parents=True, exist_ok=True)
        authority.record_path.write_text("{bad", encoding="utf-8")
        with pytest.raises(LegacyQueueUndeterminedError):
            _service()._assert_legacy_queue_converged()

    def test_undetermined_refuses_to_start_the_daemon(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _routed_store(tmp_path, monkeypatch)
        with pytest.raises(LegacyQueueNotConvergedError):
            _service()._assert_legacy_queue_converged()

    def test_genuine_zero_starts_normally(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        store = _routed_store(tmp_path, monkeypatch)
        _publish(store)
        _service()._assert_legacy_queue_converged()

    def test_stranded_rows_still_refuse(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        store = _routed_store(tmp_path, monkeypatch)
        store.layout_generation().begin_cutover("pending")
        with pytest.raises(LegacyQueueNotConvergedError, match="cutover_pending"):
            _service()._assert_legacy_queue_converged()


class TestARefusedStartLeavesNoDeadSingleton:
    def test_get_sync_service_does_not_cache_a_service_that_failed_to_start(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import specify_cli.sync.background as bg

        store = _routed_store(tmp_path, monkeypatch)
        monkeypatch.setattr(bg, "_service", None)
        monkeypatch.setattr(bg, "is_saas_sync_enabled", lambda: True)
        with pytest.raises(LegacyQueueNotConvergedError):
            bg.get_sync_service()
        assert bg._service is None

        _publish(store)
        service = bg.get_sync_service()
        try:
            assert service.is_running is True
            assert service.queue is None
        finally:
            service.stop()
            bg._service = None

    def test_get_runtime_does_not_cache_a_runtime_that_failed_to_start(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import specify_cli.sync.runtime as rt

        monkeypatch.setattr(rt, "_runtime", None)
        monkeypatch.setattr(rt, "is_saas_sync_enabled", lambda: True)
        monkeypatch.setattr(rt, "_auto_start_enabled", lambda: True)
        monkeypatch.setattr(rt.SyncRuntime, "start", lambda self: (_ for _ in ()).throw(LegacyQueueNotConvergedError("nope")))
        with pytest.raises(LegacyQueueNotConvergedError):
            rt.get_runtime()
        assert rt._runtime is None
