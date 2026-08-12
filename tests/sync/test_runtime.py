"""Tests for SyncRuntime lazy singleton lifecycle."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

pytestmark = pytest.mark.fast

from specify_cli.sync.runtime import (
    SyncRuntime,
    get_runtime,
    reset_runtime,
    _auto_start_enabled,
)

# Captured from its defining module at import time, i.e. before any fixture runs, so
# this name is the real resolver even inside a test that ``tests/sync/conftest.py``'s
# autouse ``_consented_checkout_by_default`` has granted blanket consent to. That
# fixture patches the *rebound* copy on ``specify_cli.sync.runtime``; it never touches
# ``sync.routing``.
from specify_cli.sync.routing import (
    is_sync_enabled_for_checkout as _real_is_sync_enabled_for_checkout,
)


@contextmanager
def _consent_gate(answer: bool) -> Iterator[None]:
    """State a test's consent premise explicitly, instead of inheriting one.

    ``_auto_start_enabled`` consults ``is_sync_enabled_for_checkout`` for every
    checkout that does not carry an explicit project-local ``sync.auto_start``.
    ``tests/sync/conftest.py`` grants that seam unconditionally for any file whose
    name contains neither ``"consent"`` nor ``"capture_gate"`` — which this file's
    name does not — so a test here that does not say what it assumes is silently
    assuming *consent granted*, the one premise #3030 exists to stop defaulting to.

    Wrapping the call site makes the premise part of the test rather than part of the
    package, and keeps these tests correct whatever that guard becomes.
    """
    with patch("specify_cli.sync.runtime.is_sync_enabled_for_checkout", return_value=answer):
        yield


@pytest.fixture(autouse=True)
def reset_singleton():
    """Isolate runtime tests without destroying prior worker state."""
    from specify_cli.sync import runtime as runtime_module

    prior_runtime = runtime_module._runtime
    runtime_module._runtime = None
    try:
        yield
    finally:
        current_runtime = runtime_module._runtime
        runtime_module._runtime = None
        try:
            if current_runtime is not None and current_runtime is not prior_runtime:
                current_runtime.stop()
        finally:
            runtime_module._runtime = prior_runtime


@pytest.fixture(autouse=True)
def mock_body_queue():
    """Prevent OfflineBodyUploadQueue from opening a real SQLite DB."""
    with (
        patch("specify_cli.sync.body_queue.OfflineBodyUploadQueue.__init__", return_value=None),
        patch("specify_cli.sync.body_queue.OfflineBodyUploadQueue.size", return_value=0),
    ):
        yield


@pytest.fixture(autouse=True)
def mock_sync_feature_flag():
    """Keep runtime tests independent of the caller's environment."""
    with patch("specify_cli.sync.runtime.is_saas_sync_enabled", return_value=True):
        yield


@pytest.fixture
def auto_start_premise():
    """Grant the auto-start gate for tests whose subject is *past* that gate.

    These tests ``chdir`` into a bare ``tmp_path`` and then call ``start()`` to
    assert on background-service / WebSocket wiring. Under #3030 T028 an
    unlocatable project root denies auto-start, so ``start()`` now returns before
    the behaviour they measure — a fixture-premise artefact, not a finding.

    Named and requested per-test rather than autouse, so it can never quietly
    grant permission to ``TestAutoStartEnabled``, which asserts on the gate itself.
    """
    with patch("specify_cli.sync.runtime._auto_start_enabled", return_value=True):
        yield


class TestAutoStartEnabled:
    """Tests for _auto_start_enabled() config reading."""

    def test_denies_when_no_project_root_is_locatable(self, tmp_path, monkeypatch):
        """No project root -> no project identity -> no consent (#3030 T028).

        This used to return True: sync auto-started for a checkout whose consent
        nobody could establish. Consent is per project, so "which project?" being
        unanswerable is a denial, not a default-allow (FR-003's rule applied to
        this gate).
        """
        monkeypatch.chdir(tmp_path)
        with patch("specify_cli.sync.runtime.locate_project_root", return_value=None):
            assert _auto_start_enabled() is False

    def test_denies_when_routing_resolution_raises(self, tmp_path, monkeypatch):
        """An unreadable routing config denies rather than auto-starting (#3030 T028)."""
        monkeypatch.chdir(tmp_path)
        with (
            patch("specify_cli.sync.runtime.locate_project_root", return_value=tmp_path),
            patch(
                "specify_cli.sync.runtime.is_sync_enabled_for_checkout",
                side_effect=OSError("routing config unreadable"),
            ),
        ):
            assert _auto_start_enabled() is False

    def test_explicit_project_auto_start_still_wins_over_the_denial(
        self, tmp_path, monkeypatch
    ):
        """The denials must not swallow an explicit local opt-in."""
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("sync:\n  auto_start: true\n")
        with patch(
            "specify_cli.sync.runtime.is_sync_enabled_for_checkout",
            side_effect=OSError("unreadable"),
        ):
            assert _auto_start_enabled() is True

    def test_absent_sync_section_defers_to_the_consent_gate(self, tmp_path, monkeypatch):
        """A config with no ``sync`` section states no auto-start preference.

        The subject is the *absence of a key*, not a permission: with nothing local
        to honour, ``_auto_start_enabled`` must hand the decision to the
        consent-derived gate and return its answer unchanged, in **both**
        directions. Pinning only the granting direction is what this test used to
        do — ``assert _auto_start_enabled() is True`` on a checkout with no consent
        record, which is the incident's exact state and the opposite of FR-002. It
        passed solely because ``tests/sync/conftest.py`` had patched the gate this
        file never mentions; with the real resolver the answer here is ``False``
        (see ``TestAutoStartWithoutTheConsentFixture``).
        """
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("agents:\n  available: []\n")

        with _consent_gate(False):
            assert _auto_start_enabled() is False, (
                "no sync section is not a local grant; a denying gate must be obeyed"
            )
        with _consent_gate(True):
            assert _auto_start_enabled() is True, (
                "and the deny above must come from the gate, not from the missing section"
            )

    def test_absent_auto_start_key_defers_to_the_consent_gate(self, tmp_path, monkeypatch):
        """A ``sync`` section that omits ``auto_start`` decides nothing either.

        Distinct from the test above because it exercises the other branch of
        ``_read_project_auto_start``: the section parses as a mapping, it simply has
        no ``auto_start`` key. Same contract — the gate's answer, both ways.
        """
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("sync:\n  server_url: https://example.com\n")

        with _consent_gate(False):
            assert _auto_start_enabled() is False, (
                "a sync section without auto_start is not an opt-in to auto-start"
            )
        with _consent_gate(True):
            assert _auto_start_enabled() is True

    def test_returns_true_when_auto_start_true(self, tmp_path, monkeypatch):
        """Returns True when auto_start is explicitly True."""
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("sync:\n  auto_start: true\n")
        assert _auto_start_enabled() is True

    def test_returns_false_when_auto_start_false(self, tmp_path, monkeypatch):
        """Returns False when checkout routing disables sync."""
        monkeypatch.chdir(tmp_path)
        with (
            patch("specify_cli.sync.runtime.locate_project_root", return_value=tmp_path),
            patch("specify_cli.sync.runtime.is_sync_enabled_for_checkout", return_value=False),
        ):
            assert _auto_start_enabled() is False

    def test_unparseable_config_is_not_read_as_a_grant(self, tmp_path, monkeypatch):
        """An unparseable config must not crash the gate, and must not open it.

        The subject is the parse failure: ``_read_project_auto_start`` swallows the
        YAML error and reports "no local preference", so the decision falls through
        to the consent gate exactly as an absent key does. The consent answer is
        therefore incidental to what is being tested — which is why it is pinned
        deliberately in both directions rather than left to a package fixture.

        The denying direction is the one that carries weight: this test previously
        read ``assert _auto_start_enabled() is True`` for a checkout with no consent
        record, i.e. it stated that a config file nobody could parse auto-starts
        sync. Under the real resolver an unparseable project config is itself a
        denial (``routing.py`` treats it as a consent fault), so that reading was
        wrong twice over.
        """
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("invalid: yaml: content: [")

        with _consent_gate(False):
            assert _auto_start_enabled() is False, (
                "an unreadable config is not an opt-in to anything"
            )
        with _consent_gate(True):
            assert _auto_start_enabled() is True, (
                "no exception escaped the parse failure: the gate was still consulted"
            )


class TestAutoStartWithoutTheConsentFixture:
    """``_auto_start_enabled`` against the **real** consent resolver (#3030 FR-002).

    Every test in ``TestAutoStartEnabled`` states its consent premise by patching the
    gate — which is what makes them statements about ``_auto_start_enabled`` rather
    than about consent. The case none of them can cover is the one the incident was:
    a checkout with **no consent record at all**, decided end to end by production
    code. Its absence is what let three tests in the class above go on asserting the
    pre-T028 default-allow after T028 changed it; a test naming the real answer would
    have contradicted them out loud.

    Both tests restore the real resolver inside the test body, the way T028's denial
    pins do, so they survive any future change to ``tests/sync/conftest.py``'s
    filename-token guard rather than depending on it.
    """

    @staticmethod
    def _checkout(tmp_path: Path, monkeypatch, *, sync_enabled: bool | None) -> None:
        """A fresh checkout under a fresh HOME with no machine-global sync config.

        Mirrors ``tests/sync/test_sync_consent_default_deny.py::isolated_machine``:
        the state of every project on a machine where nobody has ever run
        ``sync opt-in``. The identity block is complete so routing resolves normally
        and the *consent* decision is the only variable.
        """
        home = tmp_path / "home"
        repo = tmp_path / "repo"
        home.mkdir()
        (repo / ".kittify").mkdir(parents=True)
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)

        lines = [
            "project:",
            f"  uuid: {uuid4()}",
            "  slug: engagement-assistant",
            "  node_id: node12345678",
            "  repo_slug: regnology-example/engagement-assistant",
            "  build_id: 8a4a7da6-a97c-4bb4-893a-b31664abfee4",
        ]
        if sync_enabled is not None:
            lines += ["sync:", f"  enabled: {str(sync_enabled).lower()}"]
        (repo / ".kittify" / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
        monkeypatch.chdir(repo)

    def test_no_consent_record_denies_auto_start(self, tmp_path, monkeypatch):
        """The incident's state: identity resolves, nobody ever opted in -> no daemon.

        This gate decides whether the background daemon starts draining a project's
        events off the machine, so FR-002 applies to it directly: absence of a record
        is not consent. Verified against the production resolver, not against a
        patched seam.
        """
        self._checkout(tmp_path, monkeypatch, sync_enabled=None)

        with patch(
            "specify_cli.sync.runtime.is_sync_enabled_for_checkout",
            _real_is_sync_enabled_for_checkout,
        ):
            assert _auto_start_enabled() is False

    def test_project_config_consent_grants_auto_start(self, tmp_path, monkeypatch):
        """POSITIVE CONTROL for the test above — it must not be allowed to pass alone.

        Same fixture, same real resolver, one line of ``sync.enabled: true`` added.
        Without this, a denial from any unrelated cause — an unresolvable project
        root, a stray consent fault, the restore silently not taking — would read as
        the FR-002 denial being proven.
        """
        self._checkout(tmp_path, monkeypatch, sync_enabled=True)

        with patch(
            "specify_cli.sync.runtime.is_sync_enabled_for_checkout",
            _real_is_sync_enabled_for_checkout,
        ):
            assert _auto_start_enabled() is True


class TestAutoStartDenialNamesItsCause:
    """The reported cause must be the cause that actually fired (#3030 WP12 MINOR-3).

    The unresolvable-project-root denial was logged at ``debug`` while ``start()``
    then told the operator, at INFO, "Sync auto-start disabled via config". An
    operator on such a checkout is sent to edit ``sync.auto_start``, which was never
    consulted, and nothing changes — the real cause sits behind a log level they
    have not enabled. The routing-exception path already got this right with a
    ``logger.warning`` naming its cause, so the two denials disagreed about how to
    report themselves.

    These assert on the operator-visible record, not on the boolean: the boolean was
    already correct, and it is the *explanation* that was wrong.
    """

    def _visible(self, caplog) -> str:
        """Everything an operator without debug logging would see."""
        return "\n".join(
            r.getMessage() for r in caplog.records if r.levelno >= logging.INFO
        )

    def test_unresolvable_project_root_is_reported_as_such(
        self, tmp_path, monkeypatch, caplog
    ):
        monkeypatch.chdir(tmp_path)
        with (
            caplog.at_level(logging.DEBUG, logger="specify_cli.sync.runtime"),
            patch("specify_cli.sync.runtime.locate_project_root", return_value=None),
        ):
            assert _auto_start_enabled() is False

        visible = self._visible(caplog)
        assert "project root" in visible, (
            f"the real cause is invisible above debug; operator saw: {visible!r}"
        )
        assert "via config" not in visible, (
            "reporting a config cause sends the operator to edit a file that was "
            "never consulted"
        )

    def test_config_denial_is_still_reported_as_a_config_denial(
        self, tmp_path, monkeypatch, caplog
    ):
        """The honest case must stay honest: a real config opt-out names the config.

        Without this, 'stop claiming config' could be satisfied by never mentioning
        config at all, which trades one misdirection for another.
        """
        monkeypatch.chdir(tmp_path)
        config_dir = tmp_path / ".kittify"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("sync:\n  auto_start: false\n")

        with caplog.at_level(logging.DEBUG, logger="specify_cli.sync.runtime"):
            assert _auto_start_enabled() is False

        visible = self._visible(caplog)
        assert "auto_start" in visible, (
            f"a genuine config opt-out must name the config key; operator saw: {visible!r}"
        )

    def test_start_does_not_restate_a_cause_it_cannot_know(
        self, tmp_path, monkeypatch, caplog
    ):
        """``start()`` receives only a boolean, so it must not name a cause.

        This is the assertion that would have caught the original defect: the lie
        lived at the call site, which guessed 'via config' for every denial.
        """
        monkeypatch.chdir(tmp_path)
        runtime = SyncRuntime()
        with (
            caplog.at_level(logging.DEBUG, logger="specify_cli.sync.runtime"),
            patch("specify_cli.sync.runtime._auto_start_enabled", return_value=False),
        ):
            runtime.start()

        assert runtime.started is False
        assert "via config" not in self._visible(caplog)


class TestSyncRuntime:
    """Tests for SyncRuntime dataclass behavior."""

    def test_initial_state(self):
        """Runtime starts with all fields at default values."""
        runtime = SyncRuntime()
        assert runtime.background_service is None
        assert runtime.ws_client is None
        assert runtime.emitter is None
        assert runtime.started is False

    def test_start_is_idempotent(self, tmp_path, monkeypatch):
        """Multiple start() calls are safe."""
        monkeypatch.chdir(tmp_path)
        runtime = SyncRuntime()
        with patch("specify_cli.sync.runtime._auto_start_enabled", return_value=False):
            runtime.start()
            runtime.start()  # Should not raise
            runtime.start()  # Should not raise
        assert runtime.started is False  # Because auto_start is disabled

    def test_auto_start_disabled_prevents_start(self, tmp_path, monkeypatch):
        """When checkout routing disables sync, runtime doesn't start services."""
        monkeypatch.chdir(tmp_path)

        runtime = SyncRuntime()
        with patch("specify_cli.sync.runtime._auto_start_enabled", return_value=False):
            runtime.start()

        assert runtime.started is False
        assert runtime.background_service is None
        assert runtime.ws_client is None

    def test_starts_background_service(self, tmp_path, monkeypatch, auto_start_premise):
        """start() initializes BackgroundSyncService."""
        monkeypatch.chdir(tmp_path)
        mock_service = MagicMock()

        # Patch the TokenManager factory so the runtime's
        # _connect_websocket_if_authenticated short-circuits to "not
        # authenticated".
        fake_tm = MagicMock()
        fake_tm.is_authenticated = False
        monkeypatch.setattr(
            "specify_cli.auth.get_token_manager", lambda: fake_tm
        )

        with patch("specify_cli.sync.background.get_sync_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            runtime = SyncRuntime()
            runtime.start()
            try:
                assert runtime.started is True
                assert runtime.background_service is mock_service
                mock_get_service.assert_called_once()
            finally:
                # #3130 fold: start() spawns a real spec-kitty-sync-async-loop
                # thread (this test does not patch _ensure_async_loop, unlike
                # its authenticated-websocket siblings below); stop() joins it.
                runtime.stop()

    def test_attach_emitter_wires_ws_client(self):
        """attach_emitter wires existing ws_client to emitter."""
        runtime = SyncRuntime()
        mock_ws = MagicMock()
        runtime.ws_client = mock_ws

        mock_emitter = MagicMock()
        runtime.attach_emitter(mock_emitter)

        assert runtime.emitter is mock_emitter
        assert mock_emitter.ws_client is mock_ws

    def test_attach_emitter_without_ws_client(self):
        """attach_emitter stores emitter even without ws_client."""
        runtime = SyncRuntime()
        mock_emitter = MagicMock()
        runtime.attach_emitter(mock_emitter)

        assert runtime.emitter is mock_emitter
        # ws_client not set since it was None

    def test_attach_emitter_sets_project_identity_on_existing_ws_client(self):
        """attach_emitter injects the emitter identity into the websocket client."""
        runtime = SyncRuntime()
        mock_ws = MagicMock()
        runtime.ws_client = mock_ws

        identity = MagicMock()
        identity.is_complete = True
        identity.build_id = "build-123"
        identity.project_uuid = UUID("12345678-1234-5678-1234-567812345678")
        identity.project_slug = "test-project"
        identity.node_id = "node-123"

        git_meta = MagicMock()
        git_meta.repo_slug = "test-org/test-repo"

        mock_emitter = MagicMock()
        mock_emitter._get_identity.return_value = identity
        mock_emitter._get_git_metadata.return_value = git_meta
        mock_emitter.emit_build_registered.return_value = {"event_id": "evt-1"}

        runtime.attach_emitter(mock_emitter)

        assert mock_ws._project_identity is identity

    def test_attach_emitter_emits_build_registered_once_and_wakes_background(self):
        """attach_emitter emits one BuildRegistered and wakes background sync."""
        runtime = SyncRuntime()
        runtime.background_service = MagicMock()

        identity = MagicMock()
        identity.is_complete = True
        identity.build_id = "build-123"
        identity.project_uuid = UUID("12345678-1234-5678-1234-567812345678")
        identity.project_slug = "test-project"
        identity.node_id = "node-123"

        git_meta = MagicMock()
        git_meta.repo_slug = "test-org/test-repo"

        mock_emitter = MagicMock()
        mock_emitter._get_identity.return_value = identity
        mock_emitter._get_git_metadata.return_value = git_meta
        mock_emitter.emit_build_registered.return_value = {"event_id": "evt-1"}

        runtime.attach_emitter(mock_emitter)
        runtime.attach_emitter(mock_emitter)

        mock_emitter.emit_build_registered.assert_called_once_with()
        runtime.background_service.wake.assert_called_once_with()

    def test_stop_is_safe_when_not_started(self):
        """stop() is safe to call when not started."""
        runtime = SyncRuntime()
        runtime.stop()  # Should not raise
        assert runtime.started is False

    def test_stop_cleans_up_services(self, tmp_path, monkeypatch, auto_start_premise):
        """stop() cleans up background service and ws_client."""
        monkeypatch.chdir(tmp_path)
        mock_service = MagicMock()

        # Mock TokenManager to return unauthenticated (skip WebSocket)
        fake_tm = MagicMock()
        fake_tm.is_authenticated = False
        monkeypatch.setattr(
            "specify_cli.auth.get_token_manager", lambda: fake_tm
        )

        with patch("specify_cli.sync.background.get_sync_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            runtime = SyncRuntime()
            runtime.start()
            assert runtime.started is True

            runtime.stop()

            assert runtime.started is False
            assert runtime.background_service is None
            mock_service.stop.assert_called_once()


class TestGetRuntime:
    """Tests for get_runtime() singleton accessor."""

    @patch("specify_cli.sync.runtime.SyncRuntime.start")
    def test_returns_singleton(self, mock_start):
        """get_runtime returns same instance on repeated calls."""
        r1 = get_runtime()
        r2 = get_runtime()
        r3 = get_runtime()

        assert r1 is r2
        assert r2 is r3
        # start() only called once
        assert mock_start.call_count == 1

    @patch("specify_cli.sync.runtime.SyncRuntime.start")
    def test_auto_starts_on_first_access(self, mock_start):
        """get_runtime calls start() on first access."""
        get_runtime()
        mock_start.assert_called_once()

    @patch("specify_cli.sync.runtime.SyncRuntime.start")
    def test_thread_safe_concurrent_access(self, mock_start):
        """get_runtime creates exactly one instance under concurrent access (Fix #10)."""
        import threading

        results: list[SyncRuntime] = []
        barrier = threading.Barrier(10)

        def call():
            barrier.wait()
            results.append(get_runtime())

        threads = [threading.Thread(target=call) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(results) == 10
        assert all(r is results[0] for r in results)
        assert mock_start.call_count == 1


class TestResetRuntime:
    """Tests for reset_runtime() test helper."""

    @patch("specify_cli.sync.runtime.SyncRuntime.start")
    def test_stops_existing_runtime(self, mock_start):
        """reset_runtime stops existing runtime before clearing."""
        runtime = get_runtime()
        with patch.object(runtime, "stop") as mock_stop:
            reset_runtime()
            mock_stop.assert_called_once()

    @patch("specify_cli.sync.runtime.SyncRuntime.start")
    def test_creates_new_instance_after_reset(self, mock_start):
        """After reset, get_runtime returns a new instance."""
        r1 = get_runtime()
        reset_runtime()
        r2 = get_runtime()

        assert r1 is not r2


class TestUnauthenticatedBehavior:
    """Tests for behavior when user is not authenticated."""

    def test_no_websocket_when_unauthenticated(self, tmp_path, monkeypatch, auto_start_premise):
        """WebSocket is not created when not authenticated."""
        monkeypatch.chdir(tmp_path)
        mock_service = MagicMock()

        fake_tm = MagicMock()
        fake_tm.is_authenticated = False
        monkeypatch.setattr(
            "specify_cli.auth.get_token_manager", lambda: fake_tm
        )

        with patch("specify_cli.sync.background.get_sync_service") as mock_get_service:
            mock_get_service.return_value = mock_service

            runtime = SyncRuntime()
            runtime.start()
            try:
                assert runtime.ws_client is None
                assert runtime.background_service is not None  # Queue still works
            finally:
                # #3130 fold: start() spawns a real spec-kitty-sync-async-loop
                # thread (this test does not patch _ensure_async_loop); stop()
                # joins it.
                runtime.stop()

    def test_websocket_created_when_authenticated(self, tmp_path, monkeypatch, auto_start_premise):
        """WebSocket client is created when authenticated."""
        monkeypatch.chdir(tmp_path)
        mock_service = MagicMock()
        mock_ws = MagicMock()
        mock_connect_coro = MagicMock()
        mock_ws.connect.return_value = mock_connect_coro

        fake_tm = MagicMock()
        fake_tm.is_authenticated = True
        monkeypatch.setattr(
            "specify_cli.auth.get_token_manager", lambda: fake_tm
        )

        with patch("specify_cli.sync.background.get_sync_service") as mock_get_service:
            mock_get_service.return_value = mock_service
            with patch("specify_cli.sync.client.WebSocketClient") as mock_ws_class:
                mock_ws_class.return_value = mock_ws

                with patch("specify_cli.sync.config.SyncConfig") as mock_config_class:
                    mock_config = MagicMock()
                    mock_config.get_server_url.return_value = "https://example.com"
                    mock_config_class.return_value = mock_config

                    # Daemon runtime creates its own async loop and schedules connect.
                    with (
                        patch.object(SyncRuntime, "_ensure_async_loop") as mock_ensure_loop,
                        patch("asyncio.run_coroutine_threadsafe") as mock_run_coroutine_threadsafe,
                    ):
                        def fake_ensure_loop():
                            runtime._async_loop = MagicMock()

                        runtime = SyncRuntime()
                        mock_ensure_loop.side_effect = fake_ensure_loop
                        runtime.start()

                        mock_ws_class.assert_called_once()
                        assert runtime.ws_client is mock_ws
                        mock_run_coroutine_threadsafe.assert_called_once_with(mock_connect_coro, runtime._async_loop)

    def test_websocket_connect_scheduled_on_daemon_loop(self, tmp_path, monkeypatch, auto_start_premise):
        """Runtime should schedule async connect on its dedicated daemon loop."""
        monkeypatch.chdir(tmp_path)
        mock_service = MagicMock()
        mock_ws = MagicMock()
        mock_connect_coro = MagicMock()
        mock_ws.connect.return_value = mock_connect_coro

        fake_tm = MagicMock()
        fake_tm.is_authenticated = True
        monkeypatch.setattr(
            "specify_cli.auth.get_token_manager", lambda: fake_tm
        )

        with patch("specify_cli.sync.background.get_sync_service") as mock_get_service:
            mock_get_service.return_value = mock_service
            with patch("specify_cli.sync.client.WebSocketClient") as mock_ws_class:
                mock_ws_class.return_value = mock_ws
                with patch("specify_cli.sync.config.SyncConfig") as mock_config_class:
                    mock_config = MagicMock()
                    mock_config.get_server_url.return_value = "https://example.com"
                    mock_config_class.return_value = mock_config

                    with (
                        patch.object(SyncRuntime, "_ensure_async_loop") as mock_ensure_loop,
                        patch("asyncio.run_coroutine_threadsafe") as mock_run_coroutine_threadsafe,
                    ):
                        def fake_ensure_loop():
                            runtime._async_loop = MagicMock()

                        runtime = SyncRuntime()
                        mock_ensure_loop.side_effect = fake_ensure_loop
                        runtime.start()

                        mock_ws_class.assert_called_once()
                        mock_run_coroutine_threadsafe.assert_called_once_with(mock_connect_coro, runtime._async_loop)
