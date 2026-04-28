"""Focused tests for the machine-global sync daemon lifecycle."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.sync import daemon
from specify_cli.sync.daemon import DaemonIntent
from specify_cli.sync.config import BackgroundDaemonPolicy
from unittest.mock import MagicMock as _MagicMock

pytestmark = pytest.mark.fast


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_urlopen_factory(payload: dict, status: int = 200):
    """Return a monkeypatch-compatible urlopen that returns *payload*."""

    def fake_urlopen(_request, timeout=0.5):  # noqa: ARG001
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                return json.dumps(payload).encode("utf-8")

        resp = Response()
        resp.status = status
        return resp

    return fake_urlopen


# ---------------------------------------------------------------------------
# Fix #1 — TOCTOU race: file lock serialises concurrent callers
# ---------------------------------------------------------------------------


class TestDaemonFileLock:
    """ensure_sync_daemon_running uses an advisory file lock."""

    def test_lock_file_created(self, monkeypatch, tmp_path):
        """Calling ensure_sync_daemon_running creates a lock file."""
        lock_file = tmp_path / "sync-daemon.lock"
        state_file = tmp_path / "sync-daemon"
        monkeypatch.setattr(daemon, "SPEC_KITTY_DIR", tmp_path)
        monkeypatch.setattr(daemon, "DAEMON_STATE_FILE", state_file)
        monkeypatch.setattr(daemon, "DAEMON_LOCK_FILE", lock_file)
        monkeypatch.setattr(daemon, "DAEMON_LOG_FILE", tmp_path / "sync-daemon.log")

        # Healthy daemon already running
        state_file.write_text("http://127.0.0.1:9400\n9400\nsecret\n1234\n")

        health_payload = {
            "status": "ok",
            "token": "secret",
            "protocol_version": daemon.DAEMON_PROTOCOL_VERSION,
            "package_version": daemon._get_package_version(),
            "sync": {"running": True},
            "websocket_status": "Connected",
        }
        monkeypatch.setattr(daemon.urllib.request, "urlopen", _fake_urlopen_factory(health_payload))

        cfg = _MagicMock()
        cfg.get_background_daemon.return_value = BackgroundDaemonPolicy.AUTO
        outcome = daemon.ensure_sync_daemon_running(intent=DaemonIntent.REMOTE_REQUIRED, config=cfg)

        assert lock_file.exists()
        assert outcome.started is True  # reused existing daemon (started=True means daemon is up)

    def test_concurrent_spawn_serialised(self, monkeypatch, tmp_path):
        """Two concurrent callers should not both spawn; file lock serialises them."""
        lock_file = tmp_path / "sync-daemon.lock"
        state_file = tmp_path / "sync-daemon"
        monkeypatch.setattr(daemon, "SPEC_KITTY_DIR", tmp_path)
        monkeypatch.setattr(daemon, "DAEMON_STATE_FILE", state_file)
        monkeypatch.setattr(daemon, "DAEMON_LOCK_FILE", lock_file)
        monkeypatch.setattr(daemon, "DAEMON_LOG_FILE", tmp_path / "sync-daemon.log")

        spawn_count = {"n": 0}
        call_order = []

        def fake_locked(preferred_port=None):
            spawn_count["n"] += 1
            call_order.append(spawn_count["n"])
            # On first call, write state so second call finds a healthy daemon
            if spawn_count["n"] == 1:
                daemon._write_daemon_file(state_file, "http://127.0.0.1:9400", 9400, "tok", 9999)
            return "http://127.0.0.1:9400", 9400, spawn_count["n"] == 1

        monkeypatch.setattr(daemon, "_ensure_sync_daemon_running_locked", fake_locked)

        cfg = _MagicMock()
        cfg.get_background_daemon.return_value = BackgroundDaemonPolicy.AUTO

        results = []

        def call():
            results.append(
                daemon.ensure_sync_daemon_running(intent=DaemonIntent.REMOTE_REQUIRED, config=cfg)
            )

        t1 = threading.Thread(target=call)
        t2 = threading.Thread(target=call)
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        assert len(results) == 2
        # Both calls completed, and they were serialised (lock ensures sequential)
        assert call_order == [1, 2]


# ---------------------------------------------------------------------------
# Fix #2 — _background_script uses importlib, not hardcoded sys.path
# ---------------------------------------------------------------------------


class TestBackgroundScript:
    """_background_script must not hardcode a repo root path."""

    def test_no_sys_path_insert(self):
        script = daemon._background_script(9400, "tok123")
        assert "sys.path" not in script

    def test_uses_package_import(self):
        script = daemon._background_script(9400, "tok123")
        assert "from specify_cli.sync.daemon import run_sync_daemon" in script

    def test_contains_port_and_token(self):
        script = daemon._background_script(9401, "abc")
        assert "9401" in script
        assert "'abc'" in script


# ---------------------------------------------------------------------------
# Fix #3 — Daemon log file for stderr/stdout
# ---------------------------------------------------------------------------


class TestDaemonLogging:
    """Daemon subprocess output goes to a log file, not /dev/null."""

    def test_subprocess_redirected_to_log_file(self, monkeypatch, tmp_path):
        state_file = tmp_path / "sync-daemon"
        log_file = tmp_path / "sync-daemon.log"
        lock_file = tmp_path / "sync-daemon.lock"
        monkeypatch.setattr(daemon, "SPEC_KITTY_DIR", tmp_path)
        monkeypatch.setattr(daemon, "DAEMON_STATE_FILE", state_file)
        monkeypatch.setattr(daemon, "DAEMON_LOG_FILE", log_file)
        monkeypatch.setattr(daemon, "DAEMON_LOCK_FILE", lock_file)

        popen_kwargs = {}

        class FakeProc:
            pid = 55555

        def fake_popen(args, **kwargs):
            popen_kwargs.update(kwargs)
            return FakeProc()

        monkeypatch.setattr(daemon.subprocess, "Popen", fake_popen)
        monkeypatch.setattr(daemon, "_find_free_port", lambda **kw: 9400)

        # Make health check succeed on first try
        health_payload = {
            "status": "ok",
            "token": None,
            "protocol_version": daemon.DAEMON_PROTOCOL_VERSION,
            "package_version": daemon._get_package_version(),
            "sync": {"running": False},
            "websocket_status": "Offline",
        }

        call_count = {"n": 0}
        def fake_check(port, token, timeout=0.5):
            call_count["n"] += 1
            return call_count["n"] > 0  # succeed immediately

        monkeypatch.setattr(daemon, "_check_sync_daemon_health", fake_check)
        monkeypatch.setattr(daemon, "time", type("T", (), {"sleep": staticmethod(lambda x: None), "monotonic": staticmethod(time.monotonic)}))

        cfg = _MagicMock()
        cfg.get_background_daemon.return_value = BackgroundDaemonPolicy.AUTO
        daemon.ensure_sync_daemon_running(intent=DaemonIntent.REMOTE_REQUIRED, config=cfg)

        # stdout and stderr should NOT be DEVNULL
        assert popen_kwargs.get("stdout") is not None
        assert popen_kwargs["stdout"] != daemon.subprocess.DEVNULL
        assert popen_kwargs.get("stderr") is not None
        assert popen_kwargs["stderr"] != daemon.subprocess.DEVNULL


# ---------------------------------------------------------------------------
# Fix #4 — Port range separation (daemon starts at 9400, not 9248)
# ---------------------------------------------------------------------------


class TestPortRange:
    """Daemon port range must not overlap with dashboard range (9237-9337)."""

    def test_daemon_port_start_above_dashboard(self):
        assert daemon.DAEMON_PORT_START >= 9400

    def test_find_free_port_uses_daemon_range(self):
        # Default call should start at DAEMON_PORT_START
        with patch.object(daemon.socket, "socket") as mock_sock:
            instance = MagicMock()
            mock_sock.return_value = instance
            # Make connect fail (port free) and bind succeed
            instance.connect_ex.return_value = 1
            instance.__enter__ = lambda s: s
            instance.__exit__ = lambda s, *a: None

            port = daemon._find_free_port()
            assert port >= daemon.DAEMON_PORT_START


# ---------------------------------------------------------------------------
# Fix #6 — Health check retry window matches dashboard (~20s)
# ---------------------------------------------------------------------------


class TestHealthCheckRetryWindow:
    """ensure_sync_daemon_running waits long enough for slow starts."""

    def test_retry_delays_sum_at_least_15_seconds(self, monkeypatch, tmp_path):
        """The retry loop should wait at least 15 seconds total."""
        state_file = tmp_path / "sync-daemon"
        lock_file = tmp_path / "sync-daemon.lock"
        monkeypatch.setattr(daemon, "SPEC_KITTY_DIR", tmp_path)
        monkeypatch.setattr(daemon, "DAEMON_STATE_FILE", state_file)
        monkeypatch.setattr(daemon, "DAEMON_LOCK_FILE", lock_file)
        monkeypatch.setattr(daemon, "DAEMON_LOG_FILE", tmp_path / "sync-daemon.log")

        # Count how much total sleep time the retry loop accumulates
        total_sleep = {"s": 0.0}
        real_sleep = time.sleep

        class FakeProc:
            pid = 77777

        def fake_popen(args, **kwargs):
            return FakeProc()

        monkeypatch.setattr(daemon.subprocess, "Popen", fake_popen)
        monkeypatch.setattr(daemon, "_find_free_port", lambda **kw: 9400)
        monkeypatch.setattr(daemon, "_check_sync_daemon_health", lambda *a, **kw: False)
        monkeypatch.setattr(daemon, "_is_process_alive", lambda pid: False)

        def counting_sleep(seconds):
            total_sleep["s"] += seconds

        monkeypatch.setattr(daemon.time, "sleep", counting_sleep)

        cfg = _MagicMock()
        cfg.get_background_daemon.return_value = BackgroundDaemonPolicy.AUTO
        outcome = daemon.ensure_sync_daemon_running(intent=DaemonIntent.REMOTE_REQUIRED, config=cfg)

        # When inner start fails with RuntimeError, outcome is start_failed (not raised)
        assert outcome.started is False
        assert outcome.skipped_reason is not None
        assert outcome.skipped_reason.startswith("start_failed:")
        # Dashboard uses ~20s; daemon should be at least 15s
        assert total_sleep["s"] >= 15.0


# ---------------------------------------------------------------------------
# Fix #7 — Version check triggers daemon restart
# ---------------------------------------------------------------------------


class TestDaemonVersionCheck:
    """Stale daemons (wrong version) are recycled on ensure_sync_daemon_running."""

    def test_health_includes_version_fields(self):
        """SyncDaemonStatus should expose protocol_version and package_version."""
        status = daemon.SyncDaemonStatus(
            healthy=True,
            protocol_version=1,
            package_version="3.0.3",
        )
        assert status.protocol_version == 1
        assert status.package_version == "3.0.3"

    def test_version_mismatch_triggers_recycle(self, monkeypatch, tmp_path):
        state_file = tmp_path / "sync-daemon"
        lock_file = tmp_path / "sync-daemon.lock"
        monkeypatch.setattr(daemon, "SPEC_KITTY_DIR", tmp_path)
        monkeypatch.setattr(daemon, "DAEMON_STATE_FILE", state_file)
        monkeypatch.setattr(daemon, "DAEMON_LOCK_FILE", lock_file)
        monkeypatch.setattr(daemon, "DAEMON_LOG_FILE", tmp_path / "sync-daemon.log")

        # Existing daemon with wrong version
        daemon._write_daemon_file(state_file, "http://127.0.0.1:9400", 9400, "tok", 1234)

        stop_calls = {"n": 0}

        def fake_stop_http(url, token):
            stop_calls["n"] += 1

        monkeypatch.setattr(daemon, "_stop_daemon_by_http", fake_stop_http)

        class FakeProc:
            pid = 88888

        monkeypatch.setattr(daemon.subprocess, "Popen", lambda *a, **kw: FakeProc())
        monkeypatch.setattr(daemon, "_find_free_port", lambda **kw: 9401)
        monkeypatch.setattr(daemon.time, "sleep", lambda x: None)

        # Phase tracking: first health check is for old daemon (port 9400),
        # subsequent ones are for the new daemon (port 9401).
        health_calls = {"n": 0}

        def check_health(port, token, timeout=0.5):
            health_calls["n"] += 1
            if port == 9400:
                return True  # old daemon is healthy
            # New daemon becomes healthy after first retry
            return health_calls["n"] > 3

        monkeypatch.setattr(daemon, "_check_sync_daemon_health", check_health)

        # Version mismatch for old daemon, so it gets recycled
        def version_matches(port, token, timeout=0.5):
            return port != 9400  # old daemon = mismatch

        monkeypatch.setattr(daemon, "_daemon_version_matches", version_matches)

        cfg = _MagicMock()
        cfg.get_background_daemon.return_value = BackgroundDaemonPolicy.AUTO
        outcome = daemon.ensure_sync_daemon_running(intent=DaemonIntent.REMOTE_REQUIRED, config=cfg)

        assert stop_calls["n"] >= 1  # old daemon was stopped
        assert outcome.started  # new daemon was spawned

    def test_version_match_reuses_daemon(self, monkeypatch, tmp_path):
        state_file = tmp_path / "sync-daemon"
        lock_file = tmp_path / "sync-daemon.lock"
        monkeypatch.setattr(daemon, "SPEC_KITTY_DIR", tmp_path)
        monkeypatch.setattr(daemon, "DAEMON_STATE_FILE", state_file)
        monkeypatch.setattr(daemon, "DAEMON_LOCK_FILE", lock_file)

        daemon._write_daemon_file(state_file, "http://127.0.0.1:9400", 9400, "tok", 1234)

        monkeypatch.setattr(daemon, "_check_sync_daemon_health", lambda *a, **kw: True)
        monkeypatch.setattr(daemon, "_daemon_version_matches", lambda *a, **kw: True)

        cfg = _MagicMock()
        cfg.get_background_daemon.return_value = BackgroundDaemonPolicy.AUTO
        outcome = daemon.ensure_sync_daemon_running(intent=DaemonIntent.REMOTE_REQUIRED, config=cfg)

        assert outcome.started  # daemon is available (reused)
        assert outcome.pid == 1234  # PID read from state file

    def test_daemon_version_matches_checks_both_fields(self, monkeypatch):
        """_daemon_version_matches rejects if protocol or package differs."""
        good_payload = {
            "status": "ok",
            "token": "tok",
            "protocol_version": daemon.DAEMON_PROTOCOL_VERSION,
            "package_version": daemon._get_package_version(),
        }
        monkeypatch.setattr(daemon, "_fetch_health_payload", lambda *a, **kw: good_payload)
        assert daemon._daemon_version_matches(9400, "tok") is True

        # Wrong protocol
        bad_proto = {**good_payload, "protocol_version": 999}
        monkeypatch.setattr(daemon, "_fetch_health_payload", lambda *a, **kw: bad_proto)
        assert daemon._daemon_version_matches(9400, "tok") is False

        # Wrong package
        bad_pkg = {**good_payload, "package_version": "0.0.0"}
        monkeypatch.setattr(daemon, "_fetch_health_payload", lambda *a, **kw: bad_pkg)
        assert daemon._daemon_version_matches(9400, "tok") is False


# ---------------------------------------------------------------------------
# Fix #8 — _require_token control flow
# ---------------------------------------------------------------------------


class TestRequireTokenControlFlow:
    """_require_token cleanly separates auth failure from bad JSON."""

    def _make_handler(self, method, path, body=None, token=None):
        """Build a minimal SyncDaemonHandler-like object for unit testing."""
        handler = MagicMock(spec=daemon.SyncDaemonHandler)
        handler.command = method
        handler.path = path
        handler.daemon_token = token
        handler._send_json = MagicMock()

        if method == "POST" and body is not None:
            handler._read_json_body = MagicMock(return_value=body)
        elif method == "POST":
            handler._read_json_body = MagicMock(return_value={})

        handler._extract_token_from_query = MagicMock(return_value=None)
        # Call the real implementation
        return handler

    def test_post_bad_json_returns_400(self):
        """Malformed JSON body produces a 400, not a 403."""
        handler = daemon.SyncDaemonHandler.__new__(daemon.SyncDaemonHandler)
        handler.command = "POST"
        handler.daemon_token = "expected"
        handler.path = "/api/sync/trigger"
        handler._send_json = MagicMock()

        # _read_json_body raises on bad JSON
        handler._read_json_body = MagicMock(side_effect=json.JSONDecodeError("x", "", 0))
        result = daemon.SyncDaemonHandler._require_token(handler)

        assert result is None
        handler._send_json.assert_called_once()
        assert handler._send_json.call_args[0][0] == 400

    def test_post_missing_token_returns_403(self):
        """POST with valid JSON but wrong token produces 403."""
        handler = daemon.SyncDaemonHandler.__new__(daemon.SyncDaemonHandler)
        handler.command = "POST"
        handler.daemon_token = "expected"
        handler.path = "/api/sync/trigger"
        handler._send_json = MagicMock()
        handler._read_json_body = MagicMock(return_value={"token": "wrong"})

        result = daemon.SyncDaemonHandler._require_token(handler)

        assert result is None
        handler._send_json.assert_called_once()
        assert handler._send_json.call_args[0][0] == 403

    def test_get_token_from_query(self):
        """GET requests extract token from query string."""
        handler = daemon.SyncDaemonHandler.__new__(daemon.SyncDaemonHandler)
        handler.command = "GET"
        handler.daemon_token = "secret"
        handler.path = "/api/sync/trigger?token=secret"
        handler._send_json = MagicMock()

        result = daemon.SyncDaemonHandler._require_token(handler)

        assert result == {}
        handler._send_json.assert_not_called()


# ---------------------------------------------------------------------------
# Original test (preserved)
# ---------------------------------------------------------------------------


def test_get_sync_daemon_status_reads_health_metadata(monkeypatch, tmp_path):
    daemon_file = tmp_path / "sync-daemon"
    monkeypatch.setattr(daemon, "DAEMON_STATE_FILE", daemon_file)
    daemon._write_daemon_file(daemon_file, "http://127.0.0.1:9400", 9400, "secret", 4321)

    payload = {
        "status": "ok",
        "token": "secret",
        "protocol_version": daemon.DAEMON_PROTOCOL_VERSION,
        "package_version": daemon._get_package_version(),
        "sync": {
            "running": True,
            "last_sync": "2026-04-04T12:00:00+00:00",
            "consecutive_failures": 1,
        },
        "websocket_status": "Connected",
    }
    monkeypatch.setattr(daemon.urllib.request, "urlopen", _fake_urlopen_factory(payload))

    status = daemon.get_sync_daemon_status()

    assert status.healthy is True
    assert status.url == "http://127.0.0.1:9400"
    assert status.sync_running is True
    assert status.last_sync == "2026-04-04T12:00:00+00:00"
    assert status.consecutive_failures == 1
    assert status.websocket_status == "Connected"
    assert status.protocol_version == daemon.DAEMON_PROTOCOL_VERSION
    assert status.package_version == daemon._get_package_version()


def test_get_package_version_queries_distribution_name_in_pyproject():
    """Regression: ``_get_package_version`` must query the actual installed
    distribution name (``spec-kitty-cli`` per ``pyproject.toml``).

    Earlier code asked ``importlib.metadata.version("specify-cli")``, which
    is not installed and silently returned ``"unknown"``. That made the
    daemon health endpoint report ``package_version: unknown`` and broke
    the WP04 daemon-recycle path (FR-008) and WP06 finding F-004
    (daemon-version-mismatch detection in ``auth doctor``).
    """
    from importlib.metadata import version as _real_version

    # The function under test must return the same string the package-
    # metadata machinery returns for the canonical distribution name. If
    # someone reverts to ``version("specify-cli")`` this assertion fails
    # because that lookup raises and the function falls through to
    # ``"unknown"``.
    expected = _real_version("spec-kitty-cli")
    assert daemon._get_package_version() == expected
    assert daemon._get_package_version() != "unknown"
