"""Tests for the sync daemon singleton diagnostics (issue #1071).

The legacy ``run_sync_daemon`` lifecycle relied on whichever process
managed to claim the state file first; everything else leaked. The new
``scan_sync_daemons`` and ``cleanup_orphan_sync_daemons`` helpers make
the singleton invariant testable: ``scan`` reports orphans, ``cleanup``
terminates them and returns the killed PIDs.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

import pytest

from specify_cli.sync import daemon as daemon_module
from specify_cli.sync.daemon import (
    DaemonSingletonReport,
    OrphanDaemonInfo,
    cleanup_orphan_sync_daemons,
    scan_sync_daemons,
)


@dataclass
class _FakeProcInfo:
    pid: int
    cmdline: Sequence[str]


class _FakeProcess:
    def __init__(self, pid: int, cmdline: Sequence[str]) -> None:
        self.pid = pid
        self.info = {"pid": pid, "cmdline": list(cmdline)}
        self.terminated = False
        self.killed = False

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    def wait(self, timeout: float | None = None) -> int:
        return 0


@pytest.fixture()
def daemon_state_absent(monkeypatch, tmp_path) -> None:
    fake_state = tmp_path / "sync-daemon"
    monkeypatch.setattr(daemon_module, "DAEMON_STATE_FILE", fake_state)


def _install_fake_psutil(monkeypatch, fake_processes: list[_FakeProcess]) -> None:
    def fake_iter(attrs=None):  # noqa: ARG001
        return list(fake_processes)

    def fake_process_lookup(pid: int) -> _FakeProcess:
        for proc in fake_processes:
            if proc.pid == pid:
                return proc
        raise daemon_module.psutil.NoSuchProcess(pid)

    monkeypatch.setattr(daemon_module.psutil, "process_iter", fake_iter)
    monkeypatch.setattr(daemon_module.psutil, "Process", fake_process_lookup)


def test_scan_reports_no_orphans_when_only_state_pid_alive(
    monkeypatch, tmp_path
) -> None:
    fake_state = tmp_path / "sync-daemon"
    fake_state.write_text(
        '{"url": "http://127.0.0.1:9400", "port": 9400, "token": "t", "pid": 4242}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(daemon_module, "DAEMON_STATE_FILE", fake_state)
    monkeypatch.setattr(
        daemon_module,
        "_parse_daemon_file",
        lambda _path: ("http://127.0.0.1:9400", 9400, "t", 4242),
    )

    processes = [_FakeProcess(4242, ["python", "-c", "run_sync_daemon(9400, ...)"])]
    _install_fake_psutil(monkeypatch, processes)

    report = scan_sync_daemons()
    assert isinstance(report, DaemonSingletonReport)
    assert report.state_pid == 4242
    assert report.is_singleton
    assert report.orphan_count == 0


def test_scan_reports_orphan_processes(monkeypatch, daemon_state_absent) -> None:
    processes = [
        _FakeProcess(1001, ["python", "-c", "run_sync_daemon(9401, ...)"]),
        _FakeProcess(1002, ["python", "-c", "run_sync_daemon(9402, ...)"]),
        _FakeProcess(9999, ["bash", "-c", "irrelevant"]),
    ]
    _install_fake_psutil(monkeypatch, processes)

    report = scan_sync_daemons()
    pids = {orphan.pid for orphan in report.orphan_processes}
    assert pids == {1001, 1002}
    assert all(isinstance(o, OrphanDaemonInfo) for o in report.orphan_processes)
    assert report.is_singleton is False


def test_cleanup_dry_run_does_not_terminate(monkeypatch, daemon_state_absent) -> None:
    processes = [
        _FakeProcess(2001, ["python", "-c", "run_sync_daemon(9410, ...)"]),
    ]
    _install_fake_psutil(monkeypatch, processes)

    report, killed = cleanup_orphan_sync_daemons(dry_run=True)
    assert killed == []
    assert report.orphan_count == 1
    assert processes[0].terminated is False
    assert processes[0].killed is False


def test_cleanup_terminates_orphans_and_returns_pids(
    monkeypatch, daemon_state_absent
) -> None:
    processes = [
        _FakeProcess(3001, ["python", "-c", "run_sync_daemon(9420, ...)"]),
        _FakeProcess(3002, ["python", "-c", "run_sync_daemon(9421, ...)"]),
    ]
    _install_fake_psutil(monkeypatch, processes)

    _report, killed = cleanup_orphan_sync_daemons()
    assert sorted(killed) == [3001, 3002]
    assert all(p.terminated for p in processes)
