"""Tests for background sync body queue drain integration."""

from __future__ import annotations

import pytest
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from kernel.clock import now_epoch
from specify_cli.sync.body_queue import BodyUploadTask, OfflineBodyUploadQueue
from specify_cli.sync.namespace import UploadOutcome, UploadStatus
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT_UUID = "aaaaaaaa-0000-0000-0000-000000000001"


class _ProjectBodyQueueFixture:
    """Connection-free test facade over the current project-owned body queue."""

    def __init__(self, store: ProjectSyncStore) -> None:
        self.store = store
        self.db_path = store.database_path

    def _call(self, method: str, *args: object, **kwargs: object) -> object:
        with self.store.unit_of_work() as unit:
            queue = OfflineBodyUploadQueue(unit, self.store.layout_generation())
            return getattr(queue, method)(*args, **kwargs)

    def enqueue(self, **kwargs: object) -> object:
        return self._call("enqueue", **kwargs)

    def size(self) -> int:
        return int(self._call("size"))

    def get_stats(self) -> object:
        return self._call("get_stats")

    def get_recent_failures(self) -> object:
        return self._call("get_recent_failures")


class _ProjectEventQueueFixture:
    def __init__(self, store: ProjectSyncStore) -> None:
        self.store = store

    def size(self) -> int:
        from specify_cli.sync.queue import OfflineQueue

        with self.store.unit_of_work() as unit:
            return OfflineQueue(unit, self.store.layout_generation()).size()

    def drain_queue(self, limit: int = 100) -> object:
        from specify_cli.sync.queue import OfflineQueue

        with self.store.unit_of_work() as unit:
            return OfflineQueue(unit, self.store.layout_generation()).drain_queue(limit=limit)


def _project_queues() -> tuple[_ProjectEventQueueFixture, _ProjectBodyQueueFixture]:
    store = ProjectSyncStore(PROJECT_UUID)
    return _ProjectEventQueueFixture(store), _ProjectBodyQueueFixture(store)


@pytest.fixture(autouse=True)
def _the_fixture_project_consents(tmp_path: Path, monkeypatch) -> None:
    """Record hosted-sync consent for the project these fixtures upload as.

    #3030 T025 made the body drain resolve consent per task from the task's own
    ``project_uuid``, deny-on-absence. Every task built below belongs to
    ``PROJECT_UUID``, and without a consent record for it the drain now (correctly)
    withholds them — which would leave this file measuring the refusal rather than
    the upload mechanics it exists to pin (queue lifecycle, backoff, outcome
    handling, timer wiring). Consent is a *precondition* here, not the subject; the
    refusal itself is pinned in ``test_body_drain_consent_3030.py``.

    Written through the real durable opt-in writer into a per-test
    ``SPEC_KITTY_HOME`` so no grant leaks into another test's default-deny.
    """
    from specify_cli.sync.consent import record_project_opt_in
    from specify_cli.sync.layout_generation import LayoutAuthorityError

    home = tmp_path / "consent-home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    record_project_opt_in(PROJECT_UUID, actor="background-body-test")
    store = ProjectSyncStore(PROJECT_UUID)
    authority = store.layout_generation()
    try:
        authority.begin_cutover("background-body-test")
    except LayoutAuthorityError as exc:
        if "already project-only" not in str(exc):
            raise
    else:
        authority.publish_project_only("background-body-test", verify_exact=lambda: True)
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'https://test.example.com', 'account-1', 'teamspace-1', 1, "
            "'admitted', '1', 'private-teamspace:teamspace-1')",
            (PROJECT_UUID,),
        )


@pytest.fixture(autouse=True)
def _patch_bg_token_fetch(monkeypatch):
    """Autouse: patch the background-sync token-fetch bridge so tests stay hermetic.

    Individual tests can override by directly monkeypatching the module
    attribute (e.g., ``_make_service(..., auth_token=None, monkeypatch=monkeypatch)``).
    """
    import specify_cli.sync.background as bg_mod

    monkeypatch.setattr(
        bg_mod,
        "_fetch_access_token_sync",
        MagicMock(return_value="token"),
    )
    manager = MagicMock()
    manager.get_current_session.return_value = SimpleNamespace(
        email="account-1",
        teams=[SimpleNamespace(id="teamspace-1", is_private_teamspace=True)],
    )
    monkeypatch.setattr(bg_mod, "get_token_manager", lambda: manager)
    yield


def _make_task(
    row_id: int = 1,
    artifact_path: str = "spec.md",
    content_hash: str = "abc123",
    retry_count: int = 0,
    next_attempt_at: float = 0.0,
) -> BodyUploadTask:
    return BodyUploadTask(
        row_id=row_id,
        project_uuid=PROJECT_UUID,
        mission_slug="047-feat",
        target_branch="main",
        mission_type="software-dev",
        manifest_version="1",
        artifact_path=artifact_path,
        content_hash=content_hash,
        hash_algorithm="sha256",
        content_body="# Spec\n",
        size_bytes=8,
        retry_count=retry_count,
        next_attempt_at=next_attempt_at,
        created_at=now_epoch(),
        last_error=None,
    )


def _enqueue_task(
    queue: OfflineBodyUploadQueue,
    artifact_path: str = "spec.md",
    content: str = "# Spec\n",
) -> None:
    """Enqueue a task into the body queue for testing."""
    from specify_cli.sync.namespace import NamespaceRef

    ns = NamespaceRef(
        project_uuid=PROJECT_UUID,
        mission_slug="047-feat",
        target_branch="main",
        mission_type="software-dev",
        manifest_version="1",
    )
    import hashlib

    content_hash = hashlib.sha256(content.encode()).hexdigest()  # noqa: TID251 — background body-upload content checksum (protocol-level), not charter freshness hashing
    queue.enqueue(
        namespace=ns,
        artifact_path=artifact_path,
        content_hash=content_hash,
        content_body=content,
        size_bytes=len(content.encode()),
    )


def _make_service(
    tmp_path: Path,
    auth_token: str | None = "test-token",
) -> MagicMock:
    """Create a BackgroundSyncService with mocked dependencies and real body queue.

    The ``_patch_bg_token_fetch`` autouse fixture seeds ``_fetch_access_token_sync``
    with a ``MagicMock(return_value="token")``. If a test asks for a different
    auth_token, we override that mock's return value on the currently-live
    module attribute.
    """
    from specify_cli.sync.background import BackgroundSyncService
    import specify_cli.sync.background as bg_mod

    del tmp_path
    event_queue, body_queue = _project_queues()

    if auth_token != "test-token":
        # Override the autouse-patched mock return value.
        bg_mod._fetch_access_token_sync.return_value = auth_token

    mock_config = MagicMock()
    mock_config.get_server_url.return_value = "https://test.example.com"
    mock_config.resolve_runtime_target.return_value = SimpleNamespace(resolved_server_url="https://test.example.com")

    service = BackgroundSyncService(
        queue=event_queue,
        config=mock_config,
    )
    service._body_queue = body_queue
    service._drain_body_queue = service._drain_discovered_body_queues
    return service


# --- Drain ordering ---
#
# ``test_events_drain_before_bodies`` lived here. #3030 FR-012 removed the
# queue-backed event drain from the daemon, so there is no longer an event
# drain to order against the body drain — the contract is gone, not changed.
# Body uploads remain the daemon's only drain and are covered below.


# --- Body outcome handling ---


class TestBodyOutcomeHandling:
    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.body_transport._send_content_request")
    def test_successful_upload_removes_task(
        self,
        mock_push: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:

        service = _make_service(tmp_path)
        _enqueue_task(service._body_queue, "spec.md")

        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.UPLOADED,
            reason="stored",
            content_hash="abc",
        )

        service._sync_once()

        stats = service._body_queue.get_stats()
        assert stats.total_count == 0

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.body_transport._send_content_request")
    def test_already_exists_removes_task(
        self,
        mock_push: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:

        service = _make_service(tmp_path)
        _enqueue_task(service._body_queue, "spec.md")

        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.ALREADY_EXISTS,
            reason="already_exists",
            content_hash="abc",
        )

        service._sync_once()

        stats = service._body_queue.get_stats()
        assert stats.total_count == 0

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.body_transport._send_content_request")
    def test_retryable_failure_keeps_task_with_backoff(
        self,
        mock_push: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:

        service = _make_service(tmp_path)
        _enqueue_task(service._body_queue, "spec.md")

        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.FAILED,
            reason="connection_error",
            content_hash="abc",
            retryable=True,
        )

        service._sync_once()

        stats = service._body_queue.get_stats()
        assert stats.total_count == 1
        assert stats.max_retry_count == 1

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.body_transport._send_content_request")
    def test_permanent_failure_removes_task(
        self,
        mock_push: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        import logging

        service = _make_service(tmp_path)
        _enqueue_task(service._body_queue, "spec.md")

        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.FAILED,
            reason="bad_request: invalid payload",
            content_hash="abc",
            retryable=False,
        )

        with caplog.at_level(logging.WARNING):
            service._sync_once()

        stats = service._body_queue.get_stats()
        assert stats.total_count == 0
        failures = service._body_queue.get_recent_failures()
        assert len(failures) == 1
        assert failures[0].artifact_path == "spec.md"
        assert failures[0].failure_reason == "bad_request: invalid payload"
        assert "Body upload permanent failure" not in caplog.text


# --- Edge cases ---


class TestEdgeCases:
    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.body_transport._send_content_request")
    def test_no_auth_token_skips_body_drain(
        self,
        mock_push: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:

        service = _make_service(tmp_path, auth_token=None)
        _enqueue_task(service._body_queue, "spec.md")

        service._sync_once()

        mock_push.assert_not_called()
        stats = service._body_queue.get_stats()
        assert stats.total_count == 1  # Task still queued

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.body_transport._send_content_request")
    def test_empty_queue_no_push_calls(
        self,
        mock_push: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:

        service = _make_service(tmp_path)

        service._sync_once()

        mock_push.assert_not_called()

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.body_transport._send_content_request")
    def test_backoff_respected_tasks_not_drained(
        self,
        mock_push: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Task with next_attempt_at in the future should not be drained."""
        import sqlite3

        service = _make_service(tmp_path)
        _enqueue_task(service._body_queue, "spec.md")

        # Push next_attempt_at far into the future
        conn = sqlite3.connect(service._body_queue.db_path)
        try:
            reference = json.loads(conn.execute("SELECT body_reference FROM body_upload_tasks").fetchone()[0])
            reference["next_attempt_at"] = now_epoch() + 9999
            conn.execute(
                "UPDATE body_upload_tasks SET body_reference = ?",
                (json.dumps(reference, sort_keys=True, separators=(",", ":")),),
            )
            conn.commit()
        finally:
            conn.close()

        service._sync_once()

        mock_push.assert_not_called()
        stats = service._body_queue.get_stats()
        assert stats.total_count == 1  # Still queued, not drained

    # ``test_event_sync_exception_skips_body_drain`` lived here. It asserted the
    # "events failed, therefore skip bodies" gate, which #3030 FR-012 removed
    # along with the event drain itself — bodies are now the only drain, so
    # there is nothing upstream of them left to fail.

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.body_transport._send_content_request")
    def test_stale_tasks_removed(
        self,
        mock_push: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Tasks exceeding max retry count should be removed."""
        import sqlite3

        service = _make_service(tmp_path)
        _enqueue_task(service._body_queue, "spec.md")

        # Set retry_count to 21 (exceeds max of 20)
        conn = sqlite3.connect(service._body_queue.db_path)
        try:
            reference = json.loads(conn.execute("SELECT body_reference FROM body_upload_tasks").fetchone()[0])
            reference["retry_count"] = 21
            conn.execute(
                "UPDATE body_upload_tasks SET body_reference = ?",
                (json.dumps(reference, sort_keys=True, separators=(",", ":")),),
            )
            conn.commit()
        finally:
            conn.close()

        service._sync_once()

        stats = service._body_queue.get_stats()
        assert stats.total_count == 0  # Removed as stale

    def test_no_body_queue_skips_drain(self, tmp_path: Path) -> None:
        """When _body_queue is None, drain is skipped gracefully."""
        from specify_cli.sync.background import BackgroundSyncService

        del tmp_path
        event_queue, _body_queue = _project_queues()
        service = BackgroundSyncService(
            queue=event_queue,
            config=MagicMock(),
        )
        # _body_queue is None by default — this should not raise
        with patch(
            "specify_cli.sync.background.is_saas_sync_enabled",
            return_value=True,
        ):
            service._sync_once()  # No error


# --- Body queue size() ---


class TestBodyQueueSize:
    def test_size_returns_zero_for_empty_queue(self, tmp_path: Path) -> None:
        del tmp_path
        _event_queue, queue = _project_queues()
        assert queue.size() == 0

    def test_size_returns_correct_count(self, tmp_path: Path) -> None:
        del tmp_path
        _event_queue, queue = _project_queues()
        _enqueue_task(queue, "spec.md", "# Spec\n")
        _enqueue_task(queue, "plan.md", "# Plan\n")
        assert queue.size() == 2


# --- Timer triggers with body queue ---


class TestTimerBodyQueue:
    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.body_transport._send_content_request")
    def test_timer_triggers_when_only_body_queue_has_tasks(
        self,
        mock_push: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Timer should trigger sync when event queue is empty but body queue has work."""
        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.UPLOADED,
            reason="stored",
            content_hash="abc",
        )

        service = _make_service(tmp_path)
        # Event queue is empty, body queue has a task
        _enqueue_task(service._body_queue, "spec.md", "# Spec\n")
        assert service.queue.size() == 0
        assert service._body_queue.size() == 1

        service._running = True
        try:
            service._on_timer()

            # Should have run a sync (via _perform_sync), observable as the
            # body upload being pushed — body work is the daemon's only
            # drain (FR-012).
            mock_push.assert_called_once()
            assert service._body_queue.size() == 0
        finally:
            # #3130 fold: _on_timer() self-reschedules a new threading.Timer
            # (_schedule_next_sync) while _running is True; stop() cancels it.
            service.stop()

    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    def test_timer_scans_existing_project_store_when_queue_count_is_unknown(
        self,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Discovery scans an existing store without treating its path as a grant."""
        service = _make_service(tmp_path)
        assert service.queue.size() == 0
        assert service._body_queue.size() == 0

        service._running = True
        try:
            with patch.object(service, "_perform_sync") as mock_perform:
                service._on_timer()
                mock_perform.assert_called_once()
        finally:
            # #3130 fold: _on_timer() self-reschedules a new threading.Timer
            # (_schedule_next_sync) while _running is True; stop() cancels it.
            service.stop()


# --- sync_now() drains body queue ---


class TestSyncNowBody:
    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.body_transport._send_content_request")
    def test_sync_now_drains_body_queue(
        self,
        mock_push: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.UPLOADED,
            reason="stored",
            content_hash="abc",
        )

        service = _make_service(tmp_path)
        _enqueue_task(service._body_queue, "spec.md", "# Spec\n")

        service.sync_now()

        mock_push.assert_called_once()
        assert service._body_queue.size() == 0


# --- stop() best-effort includes body queue ---


class TestStopBody:
    @patch("specify_cli.sync.background.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.body_transport._send_content_request")
    def test_stop_best_effort_includes_body_queue(
        self,
        mock_push: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_push.return_value = UploadOutcome(
            artifact_path="spec.md",
            status=UploadStatus.UPLOADED,
            reason="stored",
            content_hash="abc",
        )

        service = _make_service(tmp_path)
        _enqueue_task(service._body_queue, "spec.md", "# Spec\n")
        service._running = True

        service.stop()

        # Body queue should have been attempted
        mock_push.assert_called()


# --- Runtime lifecycle ---


class TestRuntimeLifecycle:
    @patch("specify_cli.sync.runtime.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.runtime._auto_start_enabled", return_value=True)
    @patch("specify_cli.sync.background.get_sync_service")
    def test_start_leaves_body_queue_project_discovered(
        self,
        mock_get_service: MagicMock,
        mock_auto_start: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        from specify_cli.sync.runtime import SyncRuntime

        del tmp_path
        mock_service = MagicMock()
        mock_service.queue, _body_queue = _project_queues()
        mock_get_service.return_value = mock_service

        runtime = SyncRuntime()
        runtime.start()
        try:
            assert runtime.body_queue is None
            assert mock_service._body_queue is None
        finally:
            # #3130 fold: start() spawns a real spec-kitty-sync-async-loop
            # thread; stop() joins it (unlike test_stop_clears_body_queue
            # below, which already calls stop() as part of its own assertion).
            runtime.stop()

    @patch("specify_cli.sync.runtime.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.runtime._auto_start_enabled", return_value=True)
    @patch("specify_cli.sync.background.get_sync_service")
    def test_stop_clears_body_queue(
        self,
        mock_get_service: MagicMock,
        mock_auto_start: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        from specify_cli.sync.runtime import SyncRuntime

        del tmp_path
        mock_service = MagicMock()
        mock_service.queue, _body_queue = _project_queues()
        mock_get_service.return_value = mock_service

        runtime = SyncRuntime()
        runtime.start()
        assert runtime.body_queue is None

        runtime.stop()
        assert runtime.body_queue is None

    @patch("specify_cli.sync.runtime.is_saas_sync_enabled", return_value=True)
    @patch("specify_cli.sync.runtime._auto_start_enabled", return_value=True)
    @patch("specify_cli.sync.background.get_sync_service")
    def test_runtime_does_not_alias_a_shared_payload_database(
        self,
        mock_get_service: MagicMock,
        mock_auto_start: MagicMock,
        mock_saas: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Runtime startup leaves payload ownership to project stores."""
        from specify_cli.sync.runtime import SyncRuntime

        del tmp_path
        mock_service = MagicMock()
        mock_service.queue, _body_queue = _project_queues()
        mock_get_service.return_value = mock_service

        runtime = SyncRuntime()
        runtime.start()
        try:
            assert runtime.body_queue is None
            assert mock_service._body_queue is None
        finally:
            # #3130 fold: start() spawns a real spec-kitty-sync-async-loop
            # thread; stop() joins it.
            runtime.stop()
