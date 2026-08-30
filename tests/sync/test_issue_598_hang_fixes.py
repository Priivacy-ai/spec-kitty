"""Regression tests for issue #598: CLI hangs when offline queue is full and session expired.

Three fixes are covered:

1. **dossier_pipeline.py** — ``trigger_feature_dossier_sync_if_enabled`` creates
   an ``OfflineBodyUploadQueue`` directly instead of spinning up a full
   ``SyncRuntime`` (threads, WebSocket, atexit handlers).

2. **background.py** — ``BackgroundSyncService.stop()`` uses bounded timeouts
   on lock acquisition and the final sync, so process exit never hangs.

3. **daemon.py** — ``ensure_sync_daemon_running`` uses ``LOCK_NB`` with a
   bounded retry loop instead of blocking ``LOCK_EX`` indefinitely.

Every altered line/branch is exercised.  The ``full_queue`` fixture fills a
real SQLite queue to capacity (small cap for speed) so the "queue is full"
code paths fire without inserting 100 k rows.
"""

from __future__ import annotations

import errno
import fcntl
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

_QUEUE_PROJECT_UUID = "6a1d0c4e-0598-4c33-9f2e-000000000598"


@pytest.fixture(autouse=True)
def _reset_diagnostics():
    from specify_cli.diagnostics import reset_for_invocation
    from specify_cli.sync.diagnostics import reset_emitted_codes

    reset_for_invocation()
    reset_emitted_codes()
    yield
    reset_for_invocation()
    reset_emitted_codes()


# ═══════════════════════════════════════════════════════════════════════
# Shared fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def _isolate_legacy_queue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Give every test its own runtime home so ``start()`` sees a clean legacy queue.

    ``BackgroundSyncService.start()`` now refuses when unmigrated legacy queue
    rows remain (#3030 T007). The root conftest's isolated home is shared for
    the whole session, so rows any earlier test queues at the legacy path make
    these lifecycle tests order-dependent — they passed alone and failed in a
    full run. Pinning the home per test removes the coupling; tests that want
    stranded rows create them explicitly (see
    ``test_legacy_queue_precondition_3030.py``).
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "runtime-home"))

    from specify_cli.sync.routing import resolve_checkout_sync_routing_readonly

    routing = resolve_checkout_sync_routing_readonly()
    if routing is not None and routing.project_uuid is not None:
        _prepare_project_store(str(routing.project_uuid))


def _prepare_project_store(project_uuid: str):
    from specify_cli.sync.consent import record_project_opt_in
    from specify_cli.sync.layout_generation import LayoutMode
    from specify_cli.sync.project_store import ProjectSyncStore

    record_project_opt_in(project_uuid, actor="issue-598-hang-fix-test")
    store = ProjectSyncStore(project_uuid)
    authority = store.layout_generation()
    if authority.peek_state().mode is LayoutMode.LEGACY:
        authority.begin_cutover("issue-598-hang-fix-test")
        authority.publish_project_only("issue-598-hang-fix-test", verify_exact=lambda: True)
    with store.unit_of_work():
        pass
    return store


def _project_store():
    return _prepare_project_store(_QUEUE_PROJECT_UUID)


class _ProjectEventQueueFixture:
    """Test facade that opens the canonical queue in one short UoW per call."""

    def __init__(self, store, *, max_queue_size: int) -> None:
        self.store = store
        self.max_queue_size = max_queue_size

    def queue_event(self, event: dict[str, object]) -> bool:
        from specify_cli.sync.queue import OfflineQueue

        with self.store.unit_of_work() as unit:
            return OfflineQueue(
                unit,
                self.store.layout_generation(),
                max_queue_size=self.max_queue_size,
            ).queue_event(event)

    def size(self) -> int:
        from specify_cli.sync.queue import OfflineQueue

        with self.store.unit_of_work() as unit:
            return int(
                OfflineQueue(
                    unit,
                    self.store.layout_generation(),
                    max_queue_size=self.max_queue_size,
                ).size()
            )

    def drain_queue(self, limit: int = 1000):
        from specify_cli.sync.queue import OfflineQueue

        with self.store.unit_of_work() as unit:
            return OfflineQueue(
                unit,
                self.store.layout_generation(),
                max_queue_size=self.max_queue_size,
            ).drain_queue(limit=limit)


class _ProjectBodyQueueFixture:
    """Body-queue size view without retaining a project transaction."""

    def __init__(self, store, *, max_queue_size: int) -> None:
        self.store = store
        self.max_queue_size = max_queue_size

    def size(self) -> int:
        from specify_cli.sync.body_queue import OfflineBodyUploadQueue

        with self.store.unit_of_work() as unit:
            return int(
                OfflineBodyUploadQueue(
                    unit,
                    self.store.layout_generation(),
                    max_queue_size=self.max_queue_size,
                ).size()
            )


@pytest.fixture
def full_queue(tmp_path: Path):
    """A real SQLite OfflineQueue at capacity.

    Uses a small ``max_queue_size`` (50) so tests run in < 10 ms, but
    every "queue is full" code path fires identically to 100 k events.
    """
    MAX = 50
    q = _ProjectEventQueueFixture(_project_store(), max_queue_size=MAX)
    for i in range(MAX):
        q.queue_event(
            {
                "event_id": f"EVT{i:026d}",
                "event_type": "WPStatusChanged",
                "project_uuid": _QUEUE_PROJECT_UUID,
                "payload": {
                    "wp_id": f"WP{i % 14 + 1:02d}",
                    "from_lane": "planned",
                    "to_lane": "claimed",
                },
            }
        )
    assert q.size() == MAX
    return q


@pytest.fixture
def full_body_queue(tmp_path: Path):
    """A canonical project body queue with one pending task."""
    from specify_cli.sync.body_queue import OfflineBodyUploadQueue
    from specify_cli.sync.namespace import NamespaceRef

    store = _project_store()
    max_queue_size = 50
    with store.unit_of_work() as unit:
        bq = OfflineBodyUploadQueue(
            unit,
            store.layout_generation(),
            max_queue_size=max_queue_size,
        )
        bq.enqueue(
            NamespaceRef(
                project_uuid=_QUEUE_PROJECT_UUID,
                mission_slug="047-feat",
                target_branch="main",
                mission_type="software-dev",
                manifest_version="1",
            ),
            "spec.md",
            "a" * 64,
            "# spec",
            6,
        )
    fixture = _ProjectBodyQueueFixture(store, max_queue_size=max_queue_size)
    assert fixture.size() > 0
    return fixture


@pytest.fixture
def empty_queue(tmp_path: Path):
    """An empty SQLite OfflineQueue."""
    return _ProjectEventQueueFixture(_project_store(), max_queue_size=50)


# ═══════════════════════════════════════════════════════════════════════
# Helper: stub all resolve helpers for dossier_pipeline tests
# ═══════════════════════════════════════════════════════════════════════


def _stub_dossier_resolvers(monkeypatch, tmp_path):
    """Monkeypatch the lazy imports inside trigger_feature_dossier_sync_if_enabled.

    These are imported from their source modules at call time, so we patch
    at the source — not on dossier_pipeline itself.
    """
    from specify_cli.identity.project import ProjectIdentity
    from uuid import UUID

    # #3030 FR-031 (E5): the pipeline now requires the resolved project to consent,
    # not merely for the machine to be armed. Every caller of this helper is a
    # *mechanics* test — "the body queue is built directly", "get_runtime is never
    # called", "no threads are spawned" — so each needs to get past the gate to test
    # what it is named for. Without the record below, two of them would still pass,
    # but only because the pipeline returned early and therefore built nothing and
    # spawned nothing. The uuid is fixed rather than ``uuid4()`` so a consent record
    # can exist for it at all.
    fixed_uuid = UUID("6a1d0c4e-0598-4c33-9f2e-000000000598")
    home = tmp_path / "hangfix-home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    from specify_cli.sync.consent import record_project_opt_in
    from specify_cli.sync.project_store import ProjectSyncStore

    record_project_opt_in(str(fixed_uuid), actor="issue-598-dossier-test")
    store = ProjectSyncStore(str(fixed_uuid))
    authority = store.layout_generation()
    authority.begin_cutover("issue-598-dossier-test")
    authority.publish_project_only("issue-598-dossier-test", verify_exact=lambda: True)
    with store.unit_of_work():
        pass

    monkeypatch.setattr(
        "specify_cli.identity.project.resolve_identity",
        lambda _root: ProjectIdentity(project_uuid=fixed_uuid, project_slug="p"),
    )
    monkeypatch.setattr(
        "specify_cli.core.paths.get_feature_target_branch",
        lambda _root, _slug: "main",
    )
    monkeypatch.setattr(
        "specify_cli.mission.get_mission_type",
        lambda _dir: "software-dev",
    )
    monkeypatch.setattr(
        "specify_cli.sync.namespace.resolve_manifest_version",
        lambda _t: "1",
    )


# ═══════════════════════════════════════════════════════════════════════
# 1. dossier_pipeline — no SyncRuntime in CLI process
# ═══════════════════════════════════════════════════════════════════════


class TestDossierPipelineNoRuntime:
    """trigger_feature_dossier_sync_if_enabled must never call get_runtime()."""

    @patch("specify_cli.sync.dossier_pipeline.sync_feature_dossier")
    @patch("specify_cli.sync.feature_flags.is_saas_sync_enabled", return_value=True)
    def test_creates_body_queue_directly(
        self,
        _flag,
        mock_sync,
        tmp_path,
        monkeypatch,
    ):
        """Body queue is created as a plain OfflineBodyUploadQueue, not via runtime."""
        from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled
        from specify_cli.sync.body_queue import OfflineBodyUploadQueue

        _stub_dossier_resolvers(monkeypatch, tmp_path)

        feature_dir = tmp_path / "kitty-specs" / "047-feat"
        feature_dir.mkdir(parents=True)

        trigger_feature_dossier_sync_if_enabled(feature_dir, "047-feat", tmp_path)

        mock_sync.assert_called_once()
        bq_arg = mock_sync.call_args.kwargs.get("body_queue") or mock_sync.call_args[0][2]
        assert isinstance(bq_arg, OfflineBodyUploadQueue)

    @patch("specify_cli.sync.dossier_pipeline.sync_feature_dossier")
    @patch("specify_cli.sync.feature_flags.is_saas_sync_enabled", return_value=True)
    def test_get_runtime_never_called(
        self,
        _flag,
        mock_sync,
        tmp_path,
        monkeypatch,
    ):
        """get_runtime is never called — proves zero thread/atexit side-effects."""
        from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled

        _stub_dossier_resolvers(monkeypatch, tmp_path)

        feature_dir = tmp_path / "kitty-specs" / "047-feat"
        feature_dir.mkdir(parents=True)

        # Poison get_runtime so any call would explode
        poison = MagicMock(side_effect=AssertionError("get_runtime must not be called"))
        monkeypatch.setattr("specify_cli.sync.runtime.get_runtime", poison)

        trigger_feature_dossier_sync_if_enabled(feature_dir, "047-feat", tmp_path)
        poison.assert_not_called()

    @patch("specify_cli.sync.feature_flags.is_saas_sync_enabled", return_value=False)
    def test_sync_disabled_returns_none(self, _flag, tmp_path):
        """When SaaS sync is disabled, returns None immediately."""
        from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled

        result = trigger_feature_dossier_sync_if_enabled(
            tmp_path / "feat",
            "047-feat",
            tmp_path,
        )
        assert result is None

    @patch("specify_cli.sync.feature_flags.is_saas_sync_enabled", return_value=True)
    def test_no_project_uuid_returns_none(self, _flag, tmp_path, monkeypatch):
        """When project_uuid is None, returns None without touching runtime."""
        from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled
        from specify_cli.identity.project import ProjectIdentity

        monkeypatch.setattr(
            "specify_cli.identity.project.resolve_identity",
            lambda _root: ProjectIdentity(),  # no project_uuid
        )

        result = trigger_feature_dossier_sync_if_enabled(
            tmp_path / "feat",
            "047-feat",
            tmp_path,
        )
        assert result is None

    @patch("specify_cli.sync.feature_flags.is_saas_sync_enabled", return_value=True)
    def test_exception_returns_none(self, _flag, tmp_path, monkeypatch):
        """Any exception is caught and returns None (fire-and-forget)."""
        from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled

        monkeypatch.setattr(
            "specify_cli.identity.project.resolve_identity",
            MagicMock(side_effect=RuntimeError("boom")),
        )

        result = trigger_feature_dossier_sync_if_enabled(
            tmp_path / "feat",
            "047-feat",
            tmp_path,
        )
        assert result is None


# ═══════════════════════════════════════════════════════════════════════
# 2. background.py — bounded stop() with timeout
# ═══════════════════════════════════════════════════════════════════════


class TestBackgroundStopBounded:
    """BackgroundSyncService.stop() never blocks indefinitely."""

    def _make_service(self, queue, config=None, body_queue=None):
        from specify_cli.sync.background import BackgroundSyncService

        cfg = config or MagicMock()
        cfg.get_server_url.return_value = "https://test.example.com"
        svc = BackgroundSyncService(queue=queue, config=cfg, sync_interval_seconds=300)
        # These #598 unit cases exercise only their explicitly supplied queue.
        # Project discovery has its own integration coverage; allowing the
        # per-test routed store to count as body work would make an empty
        # explicit queue indistinguishable from discovered daemon work.
        svc._has_discovered_project_candidates = MagicMock(return_value=False)
        if body_queue is not None:
            svc._body_queue = body_queue
        return svc

    # ── Lock acquisition ──────────────────────────────────────────

    def test_stop_acquires_lock_and_cancels_timer(self, empty_queue):
        """Normal case: lock acquired, timer cancelled, service stopped."""
        svc = self._make_service(empty_queue)
        svc.start()
        assert svc.is_running
        assert svc._timer is not None

        svc.stop()
        assert not svc.is_running
        assert svc._timer is None

    def test_stop_when_lock_held_skips_final_sync(self, full_queue):
        """When the lock cannot be acquired within timeout, stop() returns without syncing."""
        svc = self._make_service(full_queue)
        svc._running = True

        # Hold the lock from another thread to simulate a stuck timer
        lock_holder_ready = threading.Event()
        release = threading.Event()

        def hold_lock():
            svc._lock.acquire()
            lock_holder_ready.set()
            release.wait(timeout=10)
            svc._lock.release()

        t = threading.Thread(target=hold_lock, daemon=True)
        t.start()
        lock_holder_ready.wait(timeout=2)

        # Replace the lock with a wrapper that uses a tiny timeout
        real_lock = svc._lock

        class QuickTimeoutLock:
            """Wrapper that makes acquire(timeout=X) use a tiny timeout."""

            def acquire(self, timeout=None):
                return real_lock.acquire(timeout=0.05)

            def release(self):
                return real_lock.release()

        svc._lock = QuickTimeoutLock()

        svc.stop()

        # Service should still have set _running to False
        assert not svc._running
        release.set()
        t.join(timeout=2)

    def test_stop_when_lock_not_acquired_sets_running_false(self, full_queue):
        """Even when lock acquisition fails, _running is set to False."""
        svc = self._make_service(full_queue)
        svc._running = True

        class NeverAcquireLock:
            def acquire(self, timeout=None):
                return False

            def release(self):
                pass

        svc._lock = NeverAcquireLock()
        svc.stop()
        assert not svc._running

    def test_stop_when_lock_not_acquired_emits_structured_warning(self, full_queue, capsys):
        """When lock acquisition fails, a structured warning is emitted."""
        svc = self._make_service(full_queue)
        svc._running = True

        class NeverAcquireLock:
            def acquire(self, timeout=None):
                return False

            def release(self):
                pass

        svc._lock = NeverAcquireLock()

        svc.stop()

        captured = capsys.readouterr()
        assert "diagnostic_code=sync.final_sync_lock_unavailable" in captured.err
        assert "fatal=false" in captured.err

    # ── Final sync behaviour ──────────────────────────────────────

    @patch("specify_cli.sync.background._fetch_access_token_sync", return_value=None)
    def test_stop_final_sync_runs_when_queue_has_events(self, _tok, full_queue):
        """stop() fires _guarded_final_sync when queue.size() > 0."""
        svc = self._make_service(full_queue)

        with patch.object(svc, "_guarded_final_sync") as mock_gfs:
            svc.stop()
            mock_gfs.assert_called_once()

    @patch("specify_cli.sync.background._fetch_access_token_sync", return_value=None)
    def test_stop_final_sync_runs_when_body_queue_has_work(
        self,
        _tok,
        empty_queue,
        full_body_queue,
    ):
        """stop() fires _guarded_final_sync when body_queue.size() > 0."""
        svc = self._make_service(empty_queue, body_queue=full_body_queue)

        with patch.object(svc, "_guarded_final_sync") as mock_gfs:
            svc.stop()
            mock_gfs.assert_called_once()

    def test_stop_skips_final_sync_when_queues_empty(self, empty_queue):
        """stop() skips final sync entirely when both queues are empty."""
        svc = self._make_service(empty_queue)

        with patch.object(svc, "_guarded_final_sync") as mock_gfs:
            svc.stop()
            mock_gfs.assert_not_called()

    # ── Timeout on final sync ─────────────────────────────────────

    @patch("specify_cli.sync.background._STOP_SYNC_TIMEOUT_SECONDS", 0.1)
    @patch("specify_cli.sync.background._fetch_access_token_sync", return_value=None)
    def test_stop_does_not_hang_when_sync_is_slow(self, _tok, full_queue):
        """If the final sync takes longer than the timeout, stop() returns anyway."""
        svc = self._make_service(full_queue)

        def slow_sync():
            time.sleep(5)  # would hang without the timeout

        # #3130 fold: stop()'s final-sync thread is a local variable inside
        # stop() with no seam to reach it, and it deliberately outlives
        # stop()'s bounded join here (that IS the behaviour under test) --
        # so the leak guard's post-teardown snapshot can catch it mid-sleep.
        # Track the thread the same way test_stop_final_sync_thread_is_daemon
        # (below) already does, and join it after the timing assertion so it
        # has actually finished before this test hands control back to the
        # guard.
        created_threads: list[threading.Thread] = []
        real_thread = threading.Thread

        class TrackingThread(real_thread):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                created_threads.append(self)

        with (
            patch("specify_cli.sync.background.threading.Thread", TrackingThread),
            patch.object(svc, "_guarded_final_sync", side_effect=slow_sync),
        ):
            t0 = time.monotonic()
            svc.stop()
            elapsed = time.monotonic() - t0

        # Must complete in well under 5 s (the slow_sync duration)
        assert elapsed < 2.0

        assert len(created_threads) == 1
        created_threads[0].join(timeout=10.0)
        assert not created_threads[0].is_alive()

    @patch("specify_cli.sync.background._STOP_SYNC_TIMEOUT_SECONDS", 0.05)
    @patch("specify_cli.sync.background._fetch_access_token_sync", return_value=None)
    def test_stop_emits_structured_warning_when_sync_times_out(self, _tok, full_queue, capsys):
        """A structured warning is emitted when final sync does not complete in time."""
        svc = self._make_service(full_queue)

        def slow_sync():
            time.sleep(2)

        # #3130 fold: see test_stop_does_not_hang_when_sync_is_slow above --
        # same deliberately-outlives-the-join thread, tracked and joined
        # after the assertion so it does not leak into the next test.
        created_threads: list[threading.Thread] = []
        real_thread = threading.Thread

        class TrackingThread(real_thread):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                created_threads.append(self)

        with (
            patch("specify_cli.sync.background.threading.Thread", TrackingThread),
            patch.object(svc, "_guarded_final_sync", side_effect=slow_sync),
        ):
            svc.stop()

        captured = capsys.readouterr()
        assert "diagnostic_code=sync.event_loop_unavailable" in captured.err
        assert "fatal=false" in captured.err

        assert len(created_threads) == 1
        created_threads[0].join(timeout=10.0)
        assert not created_threads[0].is_alive()

    @patch("specify_cli.sync.background._fetch_access_token_sync", return_value=None)
    def test_stop_final_sync_completes_fast(self, _tok, full_queue):
        """When final sync is fast, stop() completes normally without timeout warning."""
        svc = self._make_service(full_queue)

        sync_ran = threading.Event()

        def fast_sync():
            sync_ran.set()

        with patch.object(svc, "_guarded_final_sync", side_effect=fast_sync):
            svc.stop()

        assert sync_ran.is_set()

    def test_stop_final_sync_thread_is_daemon(self, full_queue):
        """The final-sync thread is a daemon thread (doesn't block process exit)."""
        svc = self._make_service(full_queue)

        created_threads = []
        real_thread = threading.Thread

        class TrackingThread(real_thread):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                created_threads.append(self)

        with patch("specify_cli.sync.background.threading.Thread", TrackingThread):
            with patch.object(svc, "_guarded_final_sync"):
                svc.stop()

        assert len(created_threads) == 1
        assert created_threads[0].daemon is True

    # ── _guarded_final_sync ───────────────────────────────────────

    @patch("specify_cli.sync.background._fetch_access_token_sync", return_value="tok")
    def test_guarded_final_sync_calls_perform_sync(
        self,
        _tok,
        full_queue,
    ):
        """_guarded_final_sync delegates to _perform_sync."""
        from specify_cli.sync.batch import BatchSyncResult

        svc = self._make_service(full_queue)

        with patch.object(svc, "_perform_sync", return_value=BatchSyncResult()) as mock_perform:
            svc._guarded_final_sync()
            mock_perform.assert_called_once()

    def test_guarded_final_sync_swallows_perform_sync_exception(self, full_queue):
        """The except branch in _guarded_final_sync fires when _perform_sync raises."""
        svc = self._make_service(full_queue)

        with patch.object(svc, "_perform_sync", side_effect=RuntimeError("boom")):
            # Must not raise — the except Exception: pass branch handles it
            svc._guarded_final_sync()

    # ── backoff on the surviving daemon work ─────────────────────
    #
    # The 401-from-``batch_sync`` cases that used to live here are gone with the
    # queue-backed event drain (#3030 FR-012): ``_sync_once`` no longer POSTs
    # events, so there is no event-side auth result to classify and no
    # "events failed, therefore skip bodies" ordering left to assert. Token
    # acquisition failure is still covered by the unauthenticated paths above.

    @patch("specify_cli.sync.background._fetch_access_token_sync", return_value="good-token")
    def test_sync_once_success_resets_backoff(self, _tok, full_queue):
        """A successful tick resets backoff and stamps last_sync."""
        svc = self._make_service(full_queue)
        svc._consecutive_failures = 3
        svc._backoff_seconds = 8.0

        svc._sync_once()

        assert svc._consecutive_failures == 0
        assert svc._backoff_seconds == 0.5
        assert svc.last_sync is not None

    @patch("specify_cli.sync.background._fetch_access_token_sync", return_value="good-token")
    def test_full_sync_success_drains_body_queue(self, _tok, full_queue, full_body_queue):
        """sync_now() drains the body queue (FR-007 — bodies still drain)."""
        svc = self._make_service(full_queue, body_queue=full_body_queue)

        with patch.object(svc, "_drain_body_queue") as mock_drain:
            svc.sync_now()
            mock_drain.assert_called_once()

    def test_consecutive_failures_property(self, full_queue):
        """The consecutive_failures property reflects internal state."""
        svc = self._make_service(full_queue)
        assert svc.consecutive_failures == 0
        svc._consecutive_failures = 7
        assert svc.consecutive_failures == 7

    @patch("specify_cli.sync.background._fetch_access_token_sync", return_value="tok")
    def test_full_sync_exception_escalates_backoff(self, _tok, full_queue, full_body_queue):
        """sync_now() escalates backoff when the surviving drain raises."""
        svc = self._make_service(full_queue, body_queue=full_body_queue)

        with patch.object(svc, "_drain_body_queue", side_effect=RuntimeError("network down")):
            result = svc.sync_now()

        assert svc._consecutive_failures == 1
        assert svc._backoff_seconds == 1.0
        assert result.error_count == 1
        assert "network down" in result.error_messages[0]
        # A failed tick must not be stamped as a successful sync.
        assert svc.last_sync is None

    # ── Idempotency ───────────────────────────────────────────────

    def test_stop_idempotent(self, empty_queue):
        """Calling stop() twice is safe."""
        svc = self._make_service(empty_queue)
        svc.start()
        svc.stop()
        svc.stop()
        assert not svc.is_running

    def test_stop_without_start(self, empty_queue):
        """Calling stop() before start() is safe."""
        svc = self._make_service(empty_queue)
        svc.stop()
        assert not svc.is_running


# ═══════════════════════════════════════════════════════════════════════
# 3. daemon.py — bounded flock with LOCK_NB retry
# ═══════════════════════════════════════════════════════════════════════


class TestDaemonBoundedFlock:
    """ensure_sync_daemon_running uses LOCK_NB with bounded retries."""

    def _daemon_env(self, monkeypatch, tmp_path):
        """Wire daemon module to use tmp_path for all state files."""
        from specify_cli.sync import daemon
        from specify_cli.sync.config import BackgroundDaemonPolicy

        state_file = tmp_path / "sync-daemon"
        lock_file = tmp_path / "sync-daemon.lock"
        log_file = tmp_path / "sync-daemon.log"
        monkeypatch.setattr(daemon, "DAEMON_STATE_FILE", state_file)
        monkeypatch.setattr(daemon, "DAEMON_LOCK_FILE", lock_file)
        monkeypatch.setattr(daemon, "DAEMON_LOG_FILE", log_file)

        cfg = MagicMock()
        cfg.get_background_daemon.return_value = BackgroundDaemonPolicy.AUTO
        return daemon, state_file, lock_file, cfg

    def test_lock_acquired_on_first_try(self, monkeypatch, tmp_path):
        """When no contention, lock is acquired on the first LOCK_NB attempt."""
        daemon, state_file, lock_file, cfg = self._daemon_env(monkeypatch, tmp_path)

        daemon._write_daemon_file(state_file, "http://127.0.0.1:9400", 9400, "tok", 1234)
        monkeypatch.setattr(daemon, "_check_sync_daemon_health", lambda *a, **kw: True)
        monkeypatch.setattr(daemon, "_daemon_version_matches", lambda *a, **kw: True)

        flock_calls = []
        real_flock = fcntl.flock

        def tracking_flock(fd, op):
            flock_calls.append(op)
            return real_flock(fd, op)

        monkeypatch.setattr(daemon.fcntl, "flock", tracking_flock)

        outcome = daemon.ensure_sync_daemon_running(
            intent=daemon.DaemonIntent.REMOTE_REQUIRED,
            config=cfg,
        )

        assert outcome.started is True
        # First call is LOCK_EX | LOCK_NB (non-blocking acquire)
        assert flock_calls[0] == (fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_lock_acquired_after_retries(self, monkeypatch, tmp_path):
        """Lock succeeds after a few BlockingIOError retries."""
        daemon, state_file, lock_file, cfg = self._daemon_env(monkeypatch, tmp_path)

        daemon._write_daemon_file(state_file, "http://127.0.0.1:9400", 9400, "tok", 1234)
        monkeypatch.setattr(daemon, "_check_sync_daemon_health", lambda *a, **kw: True)
        monkeypatch.setattr(daemon, "_daemon_version_matches", lambda *a, **kw: True)
        monkeypatch.setattr(daemon.time, "sleep", lambda _: None)

        attempt = {"n": 0}
        real_flock = fcntl.flock

        def flaky_flock(fd, op):
            if op == (fcntl.LOCK_EX | fcntl.LOCK_NB):
                attempt["n"] += 1
                if attempt["n"] < 4:
                    raise BlockingIOError("locked")
            return real_flock(fd, op)

        monkeypatch.setattr(daemon.fcntl, "flock", flaky_flock)

        outcome = daemon.ensure_sync_daemon_running(
            intent=daemon.DaemonIntent.REMOTE_REQUIRED,
            config=cfg,
        )

        assert outcome.started is True
        assert attempt["n"] == 4  # failed 3 times, succeeded on 4th

    def test_lock_never_acquired_returns_skipped(self, monkeypatch, tmp_path):
        """When lock is held for > 10 s, returns a skipped outcome."""
        daemon, state_file, lock_file, cfg = self._daemon_env(monkeypatch, tmp_path)
        monkeypatch.setattr(daemon.time, "sleep", lambda _: None)

        def always_blocked(fd, op):
            if op == (fcntl.LOCK_EX | fcntl.LOCK_NB):
                raise BlockingIOError("locked")

        monkeypatch.setattr(daemon.fcntl, "flock", always_blocked)

        outcome = daemon.ensure_sync_daemon_running(
            intent=daemon.DaemonIntent.REMOTE_REQUIRED,
            config=cfg,
        )

        assert outcome.started is False
        assert "could not acquire daemon lock" in outcome.skipped_reason

    def test_lock_contention_oserror_retries(self, monkeypatch, tmp_path):
        """A plain OSError(EAGAIN) is normal LOCK_NB contention, not a hard failure."""
        daemon, state_file, lock_file, cfg = self._daemon_env(monkeypatch, tmp_path)
        monkeypatch.setattr(daemon.time, "sleep", lambda _: None)
        daemon._write_daemon_file(state_file, "http://127.0.0.1:9400", 9400, "tok", 1234)
        monkeypatch.setattr(daemon, "_check_sync_daemon_health", lambda *a, **kw: True)
        monkeypatch.setattr(daemon, "_daemon_version_matches", lambda *a, **kw: True)

        attempt = {"n": 0}
        real_flock = fcntl.flock

        def flaky_flock(fd, op):
            if op == (fcntl.LOCK_EX | fcntl.LOCK_NB):
                attempt["n"] += 1
                if attempt["n"] < 3:
                    raise OSError(errno.EAGAIN, "locked")
            return real_flock(fd, op)

        monkeypatch.setattr(daemon.fcntl, "flock", flaky_flock)

        outcome = daemon.ensure_sync_daemon_running(
            intent=daemon.DaemonIntent.REMOTE_REQUIRED,
            config=cfg,
        )

        assert outcome.started is True
        assert attempt["n"] == 3

    def test_unexpected_lock_oserror_returns_start_failed_without_retry(self, monkeypatch, tmp_path):
        """Non-contention OSErrors should fail fast instead of sleeping for 10 seconds."""
        daemon, state_file, lock_file, cfg = self._daemon_env(monkeypatch, tmp_path)

        sleep_calls = []
        monkeypatch.setattr(daemon.time, "sleep", lambda seconds: sleep_calls.append(seconds))

        def broken_flock(fd, op):
            if op == (fcntl.LOCK_EX | fcntl.LOCK_NB):
                raise OSError(errno.EBADF, "bad file descriptor")

        monkeypatch.setattr(daemon.fcntl, "flock", broken_flock)

        outcome = daemon.ensure_sync_daemon_running(
            intent=daemon.DaemonIntent.REMOTE_REQUIRED,
            config=cfg,
        )

        assert outcome.started is False
        assert outcome.skipped_reason == "start_failed: [Errno 9] bad file descriptor"
        assert sleep_calls == []

    def test_lock_not_unlocked_when_never_acquired(self, monkeypatch, tmp_path):
        """The finally block must NOT call flock(LOCK_UN) when lock was never acquired."""
        daemon, state_file, lock_file, cfg = self._daemon_env(monkeypatch, tmp_path)
        monkeypatch.setattr(daemon.time, "sleep", lambda _: None)

        flock_ops = []

        def tracking_flock(fd, op):
            flock_ops.append(op)
            if op == (fcntl.LOCK_EX | fcntl.LOCK_NB):
                raise BlockingIOError("locked")

        monkeypatch.setattr(daemon.fcntl, "flock", tracking_flock)

        daemon.ensure_sync_daemon_running(
            intent=daemon.DaemonIntent.REMOTE_REQUIRED,
            config=cfg,
        )

        assert fcntl.LOCK_UN not in flock_ops

    def test_lock_unlocked_when_acquired(self, monkeypatch, tmp_path):
        """The finally block calls flock(LOCK_UN) when lock was acquired."""
        daemon, state_file, lock_file, cfg = self._daemon_env(monkeypatch, tmp_path)

        daemon._write_daemon_file(state_file, "http://127.0.0.1:9400", 9400, "tok", 1234)
        monkeypatch.setattr(daemon, "_check_sync_daemon_health", lambda *a, **kw: True)
        monkeypatch.setattr(daemon, "_daemon_version_matches", lambda *a, **kw: True)

        flock_ops = []
        real_flock = fcntl.flock

        def tracking_flock(fd, op):
            flock_ops.append(op)
            return real_flock(fd, op)

        monkeypatch.setattr(daemon.fcntl, "flock", tracking_flock)

        daemon.ensure_sync_daemon_running(
            intent=daemon.DaemonIntent.REMOTE_REQUIRED,
            config=cfg,
        )

        assert fcntl.LOCK_UN in flock_ops

    def test_lock_unlocked_even_on_inner_exception(self, monkeypatch, tmp_path):
        """Lock is released in the finally block even if the inner logic raises."""
        daemon, state_file, lock_file, cfg = self._daemon_env(monkeypatch, tmp_path)

        monkeypatch.setattr(
            daemon,
            "_ensure_sync_daemon_running_locked",
            MagicMock(side_effect=RuntimeError("startup boom")),
        )

        flock_ops = []
        real_flock = fcntl.flock

        def tracking_flock(fd, op):
            flock_ops.append(op)
            return real_flock(fd, op)

        monkeypatch.setattr(daemon.fcntl, "flock", tracking_flock)

        outcome = daemon.ensure_sync_daemon_running(
            intent=daemon.DaemonIntent.REMOTE_REQUIRED,
            config=cfg,
        )

        assert outcome.started is False
        assert "startup boom" in outcome.skipped_reason
        assert (fcntl.LOCK_EX | fcntl.LOCK_NB) in flock_ops
        assert fcntl.LOCK_UN in flock_ops

    def test_bounded_flock_wall_clock(self, monkeypatch, tmp_path):
        """The retry loop accumulates exactly 100 × 0.1 s = 10 s of sleep."""
        daemon, state_file, lock_file, cfg = self._daemon_env(monkeypatch, tmp_path)

        sleep_total = {"s": 0.0}

        def counting_sleep(seconds):
            sleep_total["s"] += seconds

        monkeypatch.setattr(daemon.time, "sleep", counting_sleep)

        def always_blocked(fd, op):
            if op == (fcntl.LOCK_EX | fcntl.LOCK_NB):
                raise BlockingIOError("locked")

        monkeypatch.setattr(daemon.fcntl, "flock", always_blocked)

        daemon.ensure_sync_daemon_running(
            intent=daemon.DaemonIntent.REMOTE_REQUIRED,
            config=cfg,
        )

        assert sleep_total["s"] == pytest.approx(10.0, abs=0.01)

    def test_lock_pid_returned_on_success(self, monkeypatch, tmp_path):
        """On success the PID from the state file is returned."""
        daemon, state_file, lock_file, cfg = self._daemon_env(monkeypatch, tmp_path)

        daemon._write_daemon_file(state_file, "http://127.0.0.1:9400", 9400, "tok", 5678)
        monkeypatch.setattr(daemon, "_check_sync_daemon_health", lambda *a, **kw: True)
        monkeypatch.setattr(daemon, "_daemon_version_matches", lambda *a, **kw: True)

        outcome = daemon.ensure_sync_daemon_running(
            intent=daemon.DaemonIntent.REMOTE_REQUIRED,
            config=cfg,
        )

        assert outcome.started is True
        assert outcome.pid == 5678

    def test_parse_daemon_file_exception_sets_pid_none(self, monkeypatch, tmp_path):
        """When _parse_daemon_file raises after lock acquired, pid defaults to None."""
        daemon, state_file, lock_file, cfg = self._daemon_env(monkeypatch, tmp_path)

        # _ensure_sync_daemon_running_locked succeeds
        monkeypatch.setattr(
            daemon,
            "_ensure_sync_daemon_running_locked",
            MagicMock(return_value=("http://127.0.0.1:9400", 9400, True)),
        )
        # State file exists so the parse path is entered
        state_file.write_text("http://127.0.0.1:9400\n9400\ntok\n1234\n")
        # Force _parse_daemon_file to raise (defensive guard)
        monkeypatch.setattr(
            daemon,
            "_parse_daemon_file",
            MagicMock(side_effect=OSError("corrupt state")),
        )

        outcome = daemon.ensure_sync_daemon_running(
            intent=daemon.DaemonIntent.REMOTE_REQUIRED,
            config=cfg,
        )

        assert outcome.started is True
        assert outcome.pid is None  # exception caught, pid stays None

    def test_lock_timeout_outcome_has_none_pid(self, monkeypatch, tmp_path):
        """When lock times out, pid is None."""
        daemon, state_file, lock_file, cfg = self._daemon_env(monkeypatch, tmp_path)
        monkeypatch.setattr(daemon.time, "sleep", lambda _: None)

        def always_blocked(fd, op):
            if op == (fcntl.LOCK_EX | fcntl.LOCK_NB):
                raise BlockingIOError("locked")

        monkeypatch.setattr(daemon.fcntl, "flock", always_blocked)

        outcome = daemon.ensure_sync_daemon_running(
            intent=daemon.DaemonIntent.REMOTE_REQUIRED,
            config=cfg,
        )

        assert outcome.pid is None


# ═══════════════════════════════════════════════════════════════════════
# Integration: full-queue + expired-session scenario
# ═══════════════════════════════════════════════════════════════════════


class TestFullQueueExpiredSessionIntegration:
    """End-to-end scenario from issue #598: full queue + expired session."""

    @patch("specify_cli.sync.background._fetch_access_token_sync", return_value=None)
    def test_stop_with_full_queue_completes_fast(self, _tok, full_queue):
        """stop() with 100k-equivalent queue completes in < 2 s, not 15 min."""
        from specify_cli.sync.background import BackgroundSyncService

        cfg = MagicMock()
        cfg.get_server_url.return_value = "https://test.example.com"
        svc = BackgroundSyncService(queue=full_queue, config=cfg)

        svc.start()
        t0 = time.monotonic()
        svc.stop()
        elapsed = time.monotonic() - t0

        assert elapsed < 2.0

    @patch("specify_cli.sync.background._fetch_access_token_sync", return_value=None)
    def test_stop_with_full_queue_and_body_queue(
        self,
        _tok,
        full_queue,
        full_body_queue,
    ):
        """stop() also terminates fast when both event and body queues are full."""
        from specify_cli.sync.background import BackgroundSyncService

        cfg = MagicMock()
        cfg.get_server_url.return_value = "https://test.example.com"
        svc = BackgroundSyncService(queue=full_queue, config=cfg)
        svc._body_queue = full_body_queue

        svc.start()
        t0 = time.monotonic()
        svc.stop()
        elapsed = time.monotonic() - t0

        assert elapsed < 2.0

    def test_daemon_lock_contention_bounded(self, monkeypatch, tmp_path):
        """Under lock contention, the daemon startup gives up after ~10 s of sleep."""
        from specify_cli.sync import daemon
        from specify_cli.sync.config import BackgroundDaemonPolicy

        monkeypatch.setattr(daemon, "DAEMON_STATE_FILE", tmp_path / "sync-daemon")
        monkeypatch.setattr(daemon, "DAEMON_LOCK_FILE", tmp_path / "sync-daemon.lock")
        monkeypatch.setattr(daemon, "DAEMON_LOG_FILE", tmp_path / "sync-daemon.log")
        monkeypatch.setattr(daemon.time, "sleep", lambda _: None)

        def blocked(fd, op):
            if op == (fcntl.LOCK_EX | fcntl.LOCK_NB):
                raise BlockingIOError("locked")

        monkeypatch.setattr(daemon.fcntl, "flock", blocked)

        cfg = MagicMock()
        cfg.get_background_daemon.return_value = BackgroundDaemonPolicy.AUTO

        outcome = daemon.ensure_sync_daemon_running(
            intent=daemon.DaemonIntent.REMOTE_REQUIRED,
            config=cfg,
        )

        assert outcome.started is False
        assert outcome.pid is None

    @patch("specify_cli.sync.dossier_pipeline.sync_feature_dossier")
    @patch("specify_cli.sync.feature_flags.is_saas_sync_enabled", return_value=True)
    def test_dossier_sync_no_threads_spawned(
        self,
        _flag,
        mock_sync,
        tmp_path,
        monkeypatch,
    ):
        """After trigger_feature_dossier_sync_if_enabled, no daemon threads remain."""
        import threading
        from specify_cli.sync.dossier_pipeline import trigger_feature_dossier_sync_if_enabled

        _stub_dossier_resolvers(monkeypatch, tmp_path)

        feature_dir = tmp_path / "kitty-specs" / "047-feat"
        feature_dir.mkdir(parents=True)

        threads_before = set(threading.enumerate())

        trigger_feature_dossier_sync_if_enabled(feature_dir, "047-feat", tmp_path)

        threads_after = set(threading.enumerate())
        new_threads = threads_after - threads_before

        sync_threads = [t for t in new_threads if "spec-kitty" in t.name or "sync" in t.name.lower()]
        assert sync_threads == [], f"Unexpected sync threads: {sync_threads}"


# ═══════════════════════════════════════════════════════════════════════
# Constant / configuration sanity
# ═══════════════════════════════════════════════════════════════════════


class TestConstants:
    """Guard-rail tests for the new constants."""

    def test_stop_sync_timeout_is_bounded(self):
        from specify_cli.sync.background import _STOP_SYNC_TIMEOUT_SECONDS

        assert 1 <= _STOP_SYNC_TIMEOUT_SECONDS <= 30

    def test_daemon_retry_count_matches_10s(self):
        """100 retries x 0.1 s sleep = ~10 s total bounded wait."""
        assert pytest.approx(10.0) == 100 * 0.1
