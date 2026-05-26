"""Regression: replacing a healthy version-mismatched daemon kills the prior PID.

#1071 acceptance criterion: ``ensure_sync_daemon_running()`` must not leave
older daemons alive after starting a replacement for version/protocol
mismatch. The kill path goes through ``_kill_and_cleanup``, which now waits
for the killed PID to actually exit before unlinking the state file so that
the next ``ensure_running`` observes a clean slate.

These tests exercise the locked replacement path with fake processes so
they stay fast and platform-portable; the real-subprocess sweep tests in
``test_orphan_sweep.py`` already cover the network/HTTP side.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from specify_cli.sync import daemon as daemon_module
from specify_cli.sync.daemon import _kill_and_cleanup


pytestmark = pytest.mark.fast


@dataclass
class _FakeKillableProcess:
    """A psutil.Process stand-in that records kill/wait calls."""

    pid: int
    alive: bool = True
    kill_called: bool = False
    wait_calls: list[float | None] = field(default_factory=list)
    exit_on_wait: bool = True

    def kill(self) -> None:
        self.kill_called = True
        # The real kernel may take a moment to reap the process; the
        # production code now waits explicitly. We model "process exits
        # promptly after SIGKILL" as ``exit_on_wait=True``.

    def wait(self, timeout: float | None = None) -> int:
        self.wait_calls.append(timeout)
        if self.exit_on_wait:
            self.alive = False
            return 0
        raise daemon_module.psutil.TimeoutExpired(self.pid, timeout)


@pytest.fixture()
def isolated_state_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    state_file = tmp_path / "sync-daemon"
    state_file.write_text(
        "http://127.0.0.1:9400\n9400\ntok\n4242\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(daemon_module, "DAEMON_STATE_FILE", state_file)
    return state_file


def test_kill_and_cleanup_waits_for_killed_process_to_exit(
    isolated_state_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``_kill_and_cleanup`` issues kill() *and* wait() before unlinking state.

    Without the explicit wait, the next ``ensure_sync_daemon_running`` call
    could race the prior daemon's teardown — exactly the failure mode that
    leaves stale daemons live on the box per #1071.
    """
    proc = _FakeKillableProcess(pid=4242, exit_on_wait=True)
    monkeypatch.setattr(
        daemon_module.psutil,
        "Process",
        lambda pid: proc if pid == 4242 else (_ for _ in ()).throw(daemon_module.psutil.NoSuchProcess(pid)),
    )

    assert isolated_state_file.exists()
    _kill_and_cleanup(4242)

    assert proc.kill_called is True, "expected kill() to be issued"
    assert proc.wait_calls, "expected wait() to be issued after kill()"
    # The wait timeout must be the production default unless the caller overrode it.
    assert proc.wait_calls[0] == 2.0
    # State file must be cleared so the next ensure_running observes a clean slate.
    assert not isolated_state_file.exists()
    assert proc.alive is False


def test_kill_and_cleanup_clears_state_even_when_process_ignores_kill(
    isolated_state_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A daemon that ignores SIGKILL must not leave the state file dangling.

    Worst case: the kernel hasn't reaped the daemon within the wait budget.
    We still unlink the state file so the next ``ensure_running`` call can
    publish a fresh singleton; the orphan is then visible through the new
    ``scan_sync_daemons`` diagnostic surface and can be killed by hand.
    """
    proc = _FakeKillableProcess(pid=4242, exit_on_wait=False)
    monkeypatch.setattr(
        daemon_module.psutil,
        "Process",
        lambda pid: proc if pid == 4242 else (_ for _ in ()).throw(daemon_module.psutil.NoSuchProcess(pid)),
    )

    _kill_and_cleanup(4242, wait_timeout=0.1)

    assert proc.kill_called is True
    assert proc.wait_calls and proc.wait_calls[0] == 0.1
    assert not isolated_state_file.exists()


def test_kill_and_cleanup_handles_already_dead_process(
    isolated_state_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the PID is already gone, ``_kill_and_cleanup`` still clears state."""

    def raise_no_such_process(pid: int):
        raise daemon_module.psutil.NoSuchProcess(pid)

    monkeypatch.setattr(daemon_module.psutil, "Process", raise_no_such_process)

    _kill_and_cleanup(4242)

    assert not isolated_state_file.exists()


def test_kill_and_cleanup_tolerates_none_pid(
    isolated_state_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the state file was malformed (no PID) we still clear it."""
    _kill_and_cleanup(None)
    assert not isolated_state_file.exists()
