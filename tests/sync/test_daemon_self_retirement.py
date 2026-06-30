"""Tests for the daemon self-retirement tick (WP04 / FR-008 / FR-010).

These tests exercise ``_decide_self_retire`` and the surrounding
``_start_self_check_tick`` scaffolding without spinning up a real HTTP
server.  The tick mechanism is generic over any object that exposes a
``shutdown()`` method, so we substitute a mock to keep tests fast and
network-free.
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from specify_cli.sync import daemon

pytestmark = [pytest.mark.integration]


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


def _unused_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_daemon_health(port: int, proc: subprocess.Popen[str]) -> None:
    url = f"http://127.0.0.1:{port}/api/health"
    deadline = time.monotonic() + 10.0
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            stdout, stderr = proc.communicate(timeout=1)
            raise AssertionError(
                f"daemon exited before health check: rc={proc.returncode}\n"
                f"stdout={stdout}\nstderr={stderr}"
            )
        try:
            with urllib.request.urlopen(url, timeout=0.25) as response:  # noqa: S310
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError) as exc:
            last_error = exc
        time.sleep(0.05)
    raise AssertionError(f"daemon health check timed out: {last_error}")


# ---------------------------------------------------------------------------
# _decide_self_retire — the core branching predicate
# ---------------------------------------------------------------------------


class TestDecideSelfRetire:
    """Branch-by-branch coverage of ``_decide_self_retire``."""

    def test_retires_on_port_mismatch_and_recorded_pid_alive(
        self, isolated_state_file: Path
    ) -> None:
        """Recorded port differs and recorded PID is alive => shutdown()."""
        # Use the current process's PID — it is always alive.
        _write_state(isolated_state_file, port=9401, pid=os.getpid())

        server = MagicMock()
        before = _mtime(isolated_state_file)

        daemon._decide_self_retire(server, my_port=9400)

        server.shutdown.assert_called_once_with()
        # State-file ownership invariant: the function MUST NOT rewrite it.
        assert _mtime(isolated_state_file) == before

    def test_does_not_retire_on_port_mismatch_when_recorded_pid_dead(
        self, isolated_state_file: Path
    ) -> None:
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

    def test_continues_when_state_file_missing(
        self, isolated_state_file: Path
    ) -> None:
        """No state file => keep running, do not rewrite."""
        # File does not exist (fixture created the path but not the file).
        assert not isolated_state_file.exists()

        server = MagicMock()

        daemon._decide_self_retire(server, my_port=9400)

        server.shutdown.assert_not_called()
        # Confirm the function did not create the file.
        assert not isolated_state_file.exists()

    def test_continues_when_state_file_malformed(
        self, isolated_state_file: Path
    ) -> None:
        """Garbage in the state file (no parsable port) => keep running."""
        isolated_state_file.parent.mkdir(parents=True, exist_ok=True)
        isolated_state_file.write_text("not a valid daemon file\n", encoding="utf-8")
        before = _mtime(isolated_state_file)

        server = MagicMock()

        daemon._decide_self_retire(server, my_port=9400)

        server.shutdown.assert_not_called()
        # Malformed file is preserved verbatim (no rewrite, no unlink).
        assert _mtime(isolated_state_file) == before
        assert isolated_state_file.read_text(encoding="utf-8") == (
            "not a valid daemon file\n"
        )


# ---------------------------------------------------------------------------
# _start_self_check_tick — re-arm and cancel semantics
# ---------------------------------------------------------------------------


class TestStartSelfCheckTick:
    """Behavioural tests for the periodic tick scheduler."""

    def test_tick_invokes_decide_repeatedly_until_cancelled(
        self, isolated_state_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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

    def test_returned_timer_thread_is_daemon(
        self, isolated_state_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The Timer thread must be daemonised so it never blocks process exit."""
        monkeypatch.setattr(daemon, "_decide_self_retire", lambda *a, **kw: None)

        server = MagicMock()
        tick = daemon._start_self_check_tick(server, my_port=9400, interval_s=60.0)
        try:
            assert isinstance(tick, threading.Timer)
            assert tick.daemon is True
        finally:
            tick.cancel()

    def test_uses_daemon_tick_seconds_constant_when_not_overridden(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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

    def test_serve_forever_exits_cleanly_when_server_shutdown(
        self, isolated_state_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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

            def serve_forever(self, poll_interval: float = 0.5) -> None:
                del poll_interval
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

        monkeypatch.setattr(FakeServer, "__init__", init_capture)
        monkeypatch.setattr(daemon, "create_loopback_server", lambda *_args, **_kwargs: FakeServer(None, None))

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
            # Wait until the server is created, then shut it down. WP06 (R10
            # part 2): wait budget trimmed 20 -> 10 iterations (~0.5s), ample
            # for the server thread to instantiate ``FakeServer``.
            for _ in range(10):
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

        leaked = {
            t
            for t in threading.enumerate()
            if t not in threads_before and t.is_alive() and not t.daemon
        }
        assert not leaked, f"non-daemon threads leaked: {leaked}"

    @pytest.mark.skipif(os.name == "nt", reason="POSIX signal semantics only")
    def test_sigterm_exits_without_deadlocking_server_shutdown(self, tmp_path: Path) -> None:
        """SIGTERM must stop the daemon instead of deadlocking serve_forever()."""
        port = _unused_local_port()
        env = os.environ.copy()
        env["HOME"] = str(tmp_path)
        env["LOCALAPPDATA"] = str(tmp_path / "AppData")
        env["SPEC_KITTY_ENABLE_SAAS_SYNC"] = "1"
        src_dir = Path(__file__).resolve().parents[2] / "src"
        env["PYTHONPATH"] = (
            str(src_dir)
            if not env.get("PYTHONPATH")
            else f"{src_dir}{os.pathsep}{env['PYTHONPATH']}"
        )

        script = (
            "from specify_cli.sync.daemon import run_sync_daemon\n"
            f"run_sync_daemon({port}, 'tok')\n"
        )
        proc = subprocess.Popen(  # noqa: S603
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[2],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            _wait_for_daemon_health(port, proc)
            owner_path = tmp_path / ".spec-kitty" / "sync" / "daemon" / "owner.json"
            assert owner_path.exists()

            proc.send_signal(signal.SIGTERM)
            stdout, stderr = proc.communicate(timeout=5.0)

            assert proc.returncode == 0, (
                f"daemon did not exit cleanly after SIGTERM\n"
                f"stdout={stdout}\nstderr={stderr}"
            )
            assert not owner_path.exists()
        except Exception:
            if proc.poll() is None:
                proc.kill()
                proc.communicate(timeout=5)
            raise


# ---------------------------------------------------------------------------
# State-file ownership invariant — explicit assertion
# ---------------------------------------------------------------------------


class TestStateFileOwnershipInvariant:
    """Explicit assertion that ``_decide_self_retire`` never writes state.

    State-file ownership belongs to ``_ensure_sync_daemon_running_locked``;
    this contract is load-bearing for the singleton rule (see
    ``contracts/daemon-singleton.md``).  Reviewers grep for this test.
    """

    def test_decide_self_retire_never_calls_write_or_unlink(
        self, isolated_state_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sentinel: trip the test if ``_decide_self_retire`` mutates the file."""
        write_calls: list[object] = []
        unlink_calls: list[object] = []

        real_write = daemon._write_daemon_file

        def tripwire_write(
            path: Path,
            url: str,
            port: int,
            token: str | None,
            pid: int | None,
        ) -> None:
            write_calls.append((path, url, port, token, pid))
            real_write(path, url, port, token, pid)

        original_unlink = Path.unlink

        def tripwire_unlink(self: Path, *, missing_ok: bool = False) -> None:
            unlink_calls.append((self, missing_ok))
            original_unlink(self, missing_ok=missing_ok)

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

        assert write_calls == [], (
            f"_decide_self_retire wrote to state file: {write_calls}"
        )
        assert unlink_calls == [], (
            f"_decide_self_retire unlinked state file: {unlink_calls}"
        )


# ---------------------------------------------------------------------------
# _should_self_retire — pure predicate (T019 / FR-010 / FR-011)
# ---------------------------------------------------------------------------


class TestShouldSelfRetire:
    """Direct tests of the ``_should_self_retire`` pure predicate."""

    def _call(
        self,
        *,
        my_port: int = 9400,
        parsed_port: int | None = 9400,
        parsed_pid: int | None = None,
        sync_is_running: bool = False,
        idle_seconds: float = 0.0,
    ) -> tuple[bool, str]:
        return daemon._should_self_retire(
            my_port=my_port,
            parsed_port=parsed_port,
            parsed_pid=parsed_pid,
            sync_is_running=sync_is_running,
            idle_seconds=idle_seconds,
        )

    # -- FR-010: never retire while sync work is in flight --

    def test_busy_daemon_never_retires_even_when_superseded(self) -> None:
        """sync_is_running=True must block retirement regardless of state file."""
        # State file points to a *different* port with a live PID.
        should_retire, reason = self._call(
            my_port=9400,
            parsed_port=9401,
            parsed_pid=os.getpid(),  # alive
            sync_is_running=True,
            idle_seconds=99999.0,  # far past idle threshold
        )
        assert not should_retire
        assert reason == "sync_in_flight"

    def test_busy_daemon_never_retires_on_idle_timeout(self) -> None:
        """FR-010: busy daemon ignores the idle timeout."""
        should_retire, reason = self._call(
            my_port=9400,
            parsed_port=9400,  # singleton (not superseded)
            parsed_pid=os.getpid(),
            sync_is_running=True,
            idle_seconds=99999.0,
        )
        assert not should_retire
        assert reason == "sync_in_flight"

    # -- Superseded path --

    def test_superseded_idle_daemon_retires_promptly(self) -> None:
        """A superseded daemon (state file = different port, PID alive) must retire."""
        should_retire, reason = self._call(
            my_port=9400,
            parsed_port=9401,
            parsed_pid=os.getpid(),  # alive
            sync_is_running=False,
            idle_seconds=0.0,  # NOT idle — but superseded overrides
        )
        assert should_retire
        assert reason == "superseded"

    def test_superseded_with_dead_pid_does_not_retire(self) -> None:
        """State file has different port but dead PID — not superseded (stale file)."""
        should_retire, reason = self._call(
            my_port=9400,
            parsed_port=9401,
            parsed_pid=4_294_967_295,  # no such process
            sync_is_running=False,
            idle_seconds=0.0,
        )
        assert not should_retire

    def test_matching_port_and_alive_pid_is_not_superseded(self) -> None:
        """State file records OUR port — we are the singleton, not superseded."""
        should_retire, reason = self._call(
            my_port=9400,
            parsed_port=9400,  # same port → singleton
            parsed_pid=os.getpid(),
            sync_is_running=False,
            idle_seconds=0.0,
        )
        assert not should_retire
        # Not idle either (idle_seconds=0).
        assert reason == "active"

    # -- Idle timeout path --

    def test_idle_daemon_retires_after_threshold(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Idle past ``SYNC_DAEMON_IDLE_RETIREMENT_SECONDS`` → retire."""
        # Patch the constant to 1.0 s so we can pass a matching idle_seconds.
        monkeypatch.setattr(daemon, "SYNC_DAEMON_IDLE_RETIREMENT_SECONDS", 1.0)
        should_retire, reason = self._call(
            my_port=9400,
            parsed_port=9400,  # singleton (not superseded)
            sync_is_running=False,
            idle_seconds=1.5,  # exceeds patched threshold
        )
        assert should_retire
        assert reason == "idle_timeout"

    def test_idle_daemon_does_not_retire_before_threshold(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Idle below ``SYNC_DAEMON_IDLE_RETIREMENT_SECONDS`` → keep running."""
        monkeypatch.setattr(daemon, "SYNC_DAEMON_IDLE_RETIREMENT_SECONDS", 1.0)
        should_retire, reason = self._call(
            my_port=9400,
            parsed_port=9400,
            sync_is_running=False,
            idle_seconds=0.5,  # below threshold
        )
        assert not should_retire
        assert reason == "active"

    def test_idle_threshold_exactly_at_boundary_retires(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Exactly at the threshold (>=) is sufficient to trigger retirement."""
        monkeypatch.setattr(daemon, "SYNC_DAEMON_IDLE_RETIREMENT_SECONDS", 2.0)
        should_retire, reason = self._call(
            my_port=9400,
            parsed_port=9400,
            sync_is_running=False,
            idle_seconds=2.0,  # exactly at threshold
        )
        assert should_retire
        assert reason == "idle_timeout"


# ---------------------------------------------------------------------------
# Named constant existence and default value (T018 / FR-011)
# ---------------------------------------------------------------------------


class TestIdleRetirementConstant:
    """Guard the ``SYNC_DAEMON_IDLE_RETIREMENT_SECONDS`` named constant."""

    def test_constant_exists_and_is_positive_float(self) -> None:
        """``SYNC_DAEMON_IDLE_RETIREMENT_SECONDS`` must be a positive number."""
        val = daemon.SYNC_DAEMON_IDLE_RETIREMENT_SECONDS
        assert isinstance(val, (int, float))
        assert val > 0

    def test_default_value_is_900_seconds(self) -> None:
        """FR-011 / DD-03: the production default is 900 s (15 min)."""
        assert daemon.SYNC_DAEMON_IDLE_RETIREMENT_SECONDS == 900.0

    def test_constant_is_patchable_via_monkeypatch(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Tests must be able to patch the constant to a low value."""
        monkeypatch.setattr(daemon, "SYNC_DAEMON_IDLE_RETIREMENT_SECONDS", 0.1)
        assert daemon.SYNC_DAEMON_IDLE_RETIREMENT_SECONDS == 0.1


# ---------------------------------------------------------------------------
# _decide_self_retire integration with _should_self_retire (end-to-end wiring)
# ---------------------------------------------------------------------------


class TestDecideSelfRetireWithIdleAndBusy:
    """Verify ``_decide_self_retire`` respects FR-010 and triggers on idle."""

    def test_decide_does_not_retire_busy_daemon(
        self, isolated_state_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Busy daemon (sync_is_running=True) must NOT be retired by the tick.

        Exercises the FR-010 guard via ``_should_self_retire`` directly: when
        sync work is in flight the helper returns ``(False, "sync_in_flight")``,
        and ``_decide_self_retire`` must not call ``server.shutdown()``.

        We patch ``_should_self_retire`` to return the busy response rather than
        mocking the full runtime import chain (which is fragile across test-ordering
        due to sys.modules caching from real-subprocess tests earlier in the suite).
        """
        # Write a superseded state — would normally trigger retirement if not busy.
        _write_state(isolated_state_file, port=9401, pid=os.getpid())

        # Patch the pure predicate to simulate a busy (sync_in_flight) daemon.
        # This verifies the integration between _decide_self_retire and the helper
        # without coupling to the runtime import path.
        monkeypatch.setattr(
            daemon,
            "_should_self_retire",
            lambda **_kw: (False, "sync_in_flight"),
        )

        server = MagicMock()
        daemon._decide_self_retire(server, my_port=9400)

        server.shutdown.assert_not_called()

    def test_decide_retires_superseded_idle_daemon(
        self, isolated_state_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Superseded + not busy → the tick must call ``server.shutdown()``."""
        _write_state(isolated_state_file, port=9401, pid=os.getpid())

        # Stub runtime to report sync NOT in flight.
        fake_rt_mod = MagicMock()
        fake_rt = MagicMock()
        fake_rt.background_service = MagicMock()
        fake_rt.background_service.is_running = False
        fake_rt_mod._runtime = fake_rt
        monkeypatch.setitem(
            __import__("sys").modules,
            "specify_cli.sync.runtime",
            fake_rt_mod,
        )

        server = MagicMock()
        daemon._decide_self_retire(server, my_port=9400)

        server.shutdown.assert_called_once_with()

    def test_decide_retires_on_idle_timeout(
        self, isolated_state_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """After the idle timeout the tick retires the daemon (not superseded)."""
        # State file matches our port → we are the singleton, not superseded.
        _write_state(isolated_state_file, port=9400, pid=os.getpid())

        # Patch constant low and fake last-activity to be long ago.
        monkeypatch.setattr(daemon, "SYNC_DAEMON_IDLE_RETIREMENT_SECONDS", 1.0)
        monkeypatch.setattr(daemon, "_daemon_last_activity_time", 0.0)  # epoch → very old

        # Stub runtime → not busy.
        fake_rt_mod = MagicMock()
        fake_rt_mod._runtime = None
        monkeypatch.setitem(
            __import__("sys").modules,
            "specify_cli.sync.runtime",
            fake_rt_mod,
        )

        server = MagicMock()
        daemon._decide_self_retire(server, my_port=9400)

        server.shutdown.assert_called_once_with()

    def test_decide_does_not_retire_within_idle_window(
        self, isolated_state_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Within the idle window the daemon must keep running."""
        _write_state(isolated_state_file, port=9400, pid=os.getpid())

        monkeypatch.setattr(daemon, "SYNC_DAEMON_IDLE_RETIREMENT_SECONDS", 900.0)
        # last_activity = now → idle_seconds ≈ 0.
        import time as _time

        monkeypatch.setattr(daemon, "_daemon_last_activity_time", _time.monotonic())

        fake_rt_mod = MagicMock()
        fake_rt_mod._runtime = None
        monkeypatch.setitem(
            __import__("sys").modules,
            "specify_cli.sync.runtime",
            fake_rt_mod,
        )

        server = MagicMock()
        daemon._decide_self_retire(server, my_port=9400)

        server.shutdown.assert_not_called()
