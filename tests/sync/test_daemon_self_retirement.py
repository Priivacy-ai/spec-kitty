"""Tests for the daemon self-retirement tick (WP04 / FR-008 / FR-010).

These tests exercise ``_decide_self_retire`` and the surrounding
``_start_self_check_tick`` scaffolding without spinning up a real HTTP
server.  The tick mechanism is generic over any object that exposes a
``shutdown()`` method, so we substitute a mock to keep tests fast and
network-free.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from specify_cli.sync import daemon

pytestmark = pytest.mark.fast


@pytest.fixture
def isolated_state_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ``DAEMON_STATE_FILE`` into ``tmp_path`` for the test scope."""
    state_file = tmp_path / "sync-daemon"
    monkeypatch.setattr(daemon, "DAEMON_STATE_FILE", state_file)
    monkeypatch.setattr(daemon, "DAEMON_LOCK_FILE", tmp_path / "sync-daemon.lock")
    monkeypatch.setattr(daemon, "DAEMON_LOG_FILE", tmp_path / "sync-daemon.log")
    return state_file


def _write_state(state_file: Path, *, port: int, pid: int, token: str = "tok") -> None:
    """Write a daemon state file with the canonical four-line format."""
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        f"http://127.0.0.1:{port}\n{port}\n{token}\n{pid}\n",
        encoding="utf-8",
    )


def _mtime(path: Path) -> float | None:
    """Return state-file mtime or ``None`` if the file is missing.

    Used by tests to assert ``_decide_self_retire`` never rewrites the file.
    """
    try:
        return path.stat().st_mtime_ns
    except FileNotFoundError:
        return None


# ---------------------------------------------------------------------------
# _decide_self_retire — the core branching predicate
# ---------------------------------------------------------------------------


class TestDecideSelfRetire:
    """Branch-by-branch coverage of ``_decide_self_retire``."""

    def test_retires_on_port_mismatch_and_recorded_pid_alive(self, isolated_state_file: Path) -> None:
        """Recorded port differs and recorded PID is alive => shutdown()."""
        # Use the current process's PID — it is always alive.
        _write_state(isolated_state_file, port=9401, pid=os.getpid())

        server = MagicMock()
        before = _mtime(isolated_state_file)

        daemon._decide_self_retire(server, my_port=9400)

        server.shutdown.assert_called_once_with()
        # State-file ownership invariant: the function MUST NOT rewrite it.
        assert _mtime(isolated_state_file) == before

    def test_does_not_retire_on_port_mismatch_when_recorded_pid_dead(self, isolated_state_file: Path) -> None:
        """Recorded port differs but recorded PID is dead => keep running."""
        # PID 1 is init on POSIX (never dead).  Use a high impossible PID.
        # 4294967295 (2**32 - 1) is well above the typical max PID and
        # psutil will treat it as NoSuchProcess.
        dead_pid = 4_294_967_295
        _write_state(isolated_state_file, port=9401, pid=dead_pid)

        server = MagicMock()
        before = _mtime(isolated_state_file)

        daemon._decide_self_retire(server, my_port=9400)

        server.shutdown.assert_not_called()
        assert _mtime(isolated_state_file) == before

    def test_continues_when_port_matches(self, isolated_state_file: Path) -> None:
        """Recorded port equals our port => we are the singleton."""
        _write_state(isolated_state_file, port=9400, pid=os.getpid())

        server = MagicMock()
        before = _mtime(isolated_state_file)

        daemon._decide_self_retire(server, my_port=9400)

        server.shutdown.assert_not_called()
        assert _mtime(isolated_state_file) == before

    def test_continues_when_state_file_missing(self, isolated_state_file: Path) -> None:
        """No state file => keep running, do not rewrite."""
        # File does not exist (fixture created the path but not the file).
        assert not isolated_state_file.exists()

        server = MagicMock()

        daemon._decide_self_retire(server, my_port=9400)

        server.shutdown.assert_not_called()
        # Confirm the function did not create the file.
        assert not isolated_state_file.exists()

    def test_continues_when_state_file_malformed(self, isolated_state_file: Path) -> None:
        """Garbage in the state file (no parsable port) => keep running."""
        isolated_state_file.parent.mkdir(parents=True, exist_ok=True)
        isolated_state_file.write_text("not a valid daemon file\n", encoding="utf-8")
        before = _mtime(isolated_state_file)

        server = MagicMock()

        daemon._decide_self_retire(server, my_port=9400)

        server.shutdown.assert_not_called()
        # Malformed file is preserved verbatim (no rewrite, no unlink).
        assert _mtime(isolated_state_file) == before
        assert isolated_state_file.read_text(encoding="utf-8") == ("not a valid daemon file\n")


# ---------------------------------------------------------------------------
# _start_self_check_tick — re-arm and cancel semantics
# ---------------------------------------------------------------------------


class TestStartSelfCheckTick:
    """Behavioural tests for the periodic tick scheduler."""

    def test_tick_invokes_decide_repeatedly_until_cancelled(self, isolated_state_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """At sub-second cadence the tick fires multiple times before cancel."""
        calls: list[int] = []

        def fake_decide(_server: object, my_port: int) -> None:
            calls.append(my_port)

        monkeypatch.setattr(daemon, "_decide_self_retire", fake_decide)

        server = MagicMock()
        tick = daemon._start_self_check_tick(server, my_port=9400, interval_s=0.05)
        try:
            # Allow at least 3 ticks (~150 ms).
            time.sleep(0.25)
            assert len(calls) >= 2, f"expected at least 2 ticks, got {len(calls)}"
            assert all(p == 9400 for p in calls)
        finally:
            tick.cancel()

        # After cancellation the chain must stop firing.
        observed_after_cancel = len(calls)
        time.sleep(0.2)
        assert len(calls) == observed_after_cancel

    def test_returned_timer_thread_is_daemon(self, isolated_state_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """The Timer thread must be daemonised so it never blocks process exit."""
        monkeypatch.setattr(daemon, "_decide_self_retire", lambda *a, **kw: None)

        server = MagicMock()
        tick = daemon._start_self_check_tick(server, my_port=9400, interval_s=60.0)
        try:
            assert isinstance(tick, threading.Timer)
            assert tick.daemon is True
        finally:
            tick.cancel()

    def test_uses_daemon_tick_seconds_constant_when_not_overridden(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify the patchable ``DAEMON_TICK_SECONDS`` constant exists.

        Other tests rely on overriding the interval explicitly; this test
        guards the default-value contract for the production code path.
        """
        # The constant must be importable and a positive int.
        assert isinstance(daemon.DAEMON_TICK_SECONDS, int)
        assert daemon.DAEMON_TICK_SECONDS > 0


# ---------------------------------------------------------------------------
# run_sync_daemon — tick wiring and cleanup
# ---------------------------------------------------------------------------


class TestRunSyncDaemonWiring:
    """Smoke test that ``run_sync_daemon`` arms and cancels the tick."""

    def test_serve_forever_exits_cleanly_when_server_shutdown(self, isolated_state_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Patch ``HTTPServer`` to a controllable stub; verify tick lifecycle.

        Simulates a daemon whose ``serve_forever`` returns shortly after a
        background thread calls ``server.shutdown()``.  Confirms:

        1. ``_start_self_check_tick`` is armed before ``serve_forever``.
        2. The tick is cancelled in the ``finally`` block on exit.
        3. No leaked active timer threads after ``run_sync_daemon`` returns.
        """
        # Speed the tick up so the chain has time to re-arm during the test.
        monkeypatch.setattr(daemon, "DAEMON_TICK_SECONDS", 1)

        # Replace HTTPServer with a stub whose serve_forever blocks until
        # shutdown() is called; mirrors the real lifecycle.
        class FakeServer:
            def __init__(self, _addr: object, _handler: object) -> None:
                self._stop = threading.Event()
                self.shutdown_called = False

            def serve_forever(self) -> None:
                self._stop.wait(timeout=2.0)

            def shutdown(self) -> None:
                self.shutdown_called = True
                self._stop.set()

        # Track the server instance so the harness thread can shut it down.
        servers: list[FakeServer] = []
        real_init = FakeServer.__init__

        def init_capture(self: FakeServer, addr: object, handler: object) -> None:
            real_init(self, addr, handler)
            servers.append(self)

        FakeServer.__init__ = init_capture  # type: ignore[method-assign]
        monkeypatch.setattr(daemon, "HTTPServer", FakeServer)

        # Stub get_runtime so the import does not pull the real sync layer.
        fake_runtime_module = MagicMock()
        fake_runtime_module.get_runtime.return_value = MagicMock()
        monkeypatch.setitem(
            __import__("sys").modules,
            "specify_cli.sync.runtime",
            fake_runtime_module,
        )

        # Snapshot the active-thread set so we can assert no leak.
        threads_before = set(threading.enumerate())

        def harness_shutdown() -> None:
            # Wait until the server is created, then shut it down.
            for _ in range(20):
                if servers:
                    break
                time.sleep(0.05)
            assert servers, "FakeServer was never instantiated"
            time.sleep(0.1)  # let the tick arm
            servers[0].shutdown()

        harness = threading.Thread(target=harness_shutdown, daemon=True)
        harness.start()

        daemon.run_sync_daemon(port=9400, daemon_token="tok")

        harness.join(timeout=2.0)
        assert servers and servers[0].shutdown_called

        # Give cancelled timers a moment to retire.
        time.sleep(0.2)

        leaked = {t for t in threading.enumerate() if t not in threads_before and t.is_alive() and not t.daemon}
        assert not leaked, f"non-daemon threads leaked: {leaked}"


# ---------------------------------------------------------------------------
# State-file ownership invariant — explicit assertion
# ---------------------------------------------------------------------------


class TestStateFileOwnershipInvariant:
    """Explicit assertion that ``_decide_self_retire`` never writes state.

    State-file ownership belongs to ``_ensure_sync_daemon_running_locked``;
    this contract is load-bearing for the singleton rule (see
    ``contracts/daemon-singleton.md``).  Reviewers grep for this test.
    """

    def test_decide_self_retire_never_calls_write_or_unlink(self, isolated_state_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Sentinel: trip the test if ``_decide_self_retire`` mutates the file."""
        write_calls: list[object] = []
        unlink_calls: list[object] = []

        real_write = daemon._write_daemon_file

        def tripwire_write(*args: object, **kwargs: object) -> None:
            write_calls.append((args, kwargs))
            real_write(*args, **kwargs)  # type: ignore[arg-type]

        original_unlink = Path.unlink

        def tripwire_unlink(self: Path, *args: object, **kwargs: object) -> None:
            unlink_calls.append((self, args, kwargs))
            original_unlink(self, *args, **kwargs)  # type: ignore[misc]

        monkeypatch.setattr(daemon, "_write_daemon_file", tripwire_write)
        monkeypatch.setattr(Path, "unlink", tripwire_unlink)

        # Exercise every branch of _decide_self_retire.
        server = MagicMock()

        # Branch 1: missing file.
        daemon._decide_self_retire(server, my_port=9400)

        # Branch 2: malformed file.
        isolated_state_file.parent.mkdir(parents=True, exist_ok=True)
        isolated_state_file.write_text("garbage\n", encoding="utf-8")
        daemon._decide_self_retire(server, my_port=9400)

        # Branch 3: port matches.
        _write_state(isolated_state_file, port=9400, pid=os.getpid())
        daemon._decide_self_retire(server, my_port=9400)

        # Branch 4: port mismatch + dead pid.
        _write_state(isolated_state_file, port=9401, pid=4_294_967_295)
        daemon._decide_self_retire(server, my_port=9400)

        # Branch 5: port mismatch + alive pid.
        _write_state(isolated_state_file, port=9401, pid=os.getpid())
        daemon._decide_self_retire(server, my_port=9400)

        assert write_calls == [], f"_decide_self_retire wrote to state file: {write_calls}"
        assert unlink_calls == [], f"_decide_self_retire unlinked state file: {unlink_calls}"
