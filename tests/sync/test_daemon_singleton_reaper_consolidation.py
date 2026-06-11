"""SC-6b / SC-7 — sync-daemon singleton + reaper consolidation (WP12, #1071/FR-015).

These tests lock the two acceptance criteria for the daemon half of #1789:

* **SC-6b** — across multiple interpreters on one host, exactly one
  ``run_sync_daemon`` runs per host/auth-scope and stale same-executable
  orphans are reaped at the ``ensure_sync_daemon_running`` spawn path; a daemon
  launched from a *different* interpreter (a legitimately-separate auth-scope)
  is never killed (reaper-over-kill guard).
* **SC-7** — exactly ONE daemon-lifecycle reaper and ONE liveness probe remain
  after the three-reaper collapse. Verified by source inspection (``rg``-style
  scan): the canonical kill path, the canonical reaper entry point, and
  ``_is_process_alive`` are each defined once across ``sync/`` + ``dashboard/``.

No real ``run_sync_daemon`` subprocess is spawned here, so there is no
test-induced daemon leak: the reaper is exercised against in-memory fake
``psutil`` processes.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from specify_cli.sync import daemon as daemon_module
from specify_cli.sync import owner as owner_module
from specify_cli.sync.owner import ReapResult, reap_orphan_daemons

pytestmark = [pytest.mark.unit]


_SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "specify_cli"


# ---------------------------------------------------------------------------
# Fake psutil process double
# ---------------------------------------------------------------------------


@dataclass
class _FakeProc:
    """Minimal psutil.Process double for the reaper's discovery + kill paths."""

    pid: int
    cmdline: Sequence[str]
    exe_path: str
    terminated: bool = False
    killed: bool = False
    _alive: bool = True

    def __post_init__(self) -> None:
        self.info = {"pid": self.pid, "cmdline": list(self.cmdline)}

    def exe(self) -> str:
        return self.exe_path

    def terminate(self) -> None:
        self.terminated = True
        self._alive = False

    def kill(self) -> None:
        self.killed = True
        self._alive = False

    def wait(self, timeout: float | None = None) -> int:  # noqa: ARG002
        return 0

    def is_running(self) -> bool:
        return self._alive


def _install_fake_host(
    monkeypatch: pytest.MonkeyPatch,
    procs: list[_FakeProc],
    *,
    state_pid: int | None,
) -> None:
    """Wire fake psutil + an absent/empty state file into the daemon module."""

    def fake_iter(attrs: object = None) -> list[_FakeProc]:  # noqa: ARG001
        return list(procs)

    def fake_lookup(pid: int) -> _FakeProc:
        for proc in procs:
            if proc.pid == pid:
                return proc
        raise daemon_module.psutil.NoSuchProcess(pid)

    # ``psutil`` is the same module object in both ``daemon`` and ``owner``,
    # so patching it once covers the canonical reaper's lookups too.
    monkeypatch.setattr(daemon_module.psutil, "process_iter", fake_iter)
    monkeypatch.setattr(daemon_module.psutil, "Process", fake_lookup)

    # The state-file singleton PID is excluded by ``scan_sync_daemons``.
    monkeypatch.setattr(
        daemon_module,
        "_parse_daemon_file",
        lambda _path: (None, None, None, state_pid),
    )

    class _FakeStateFile:
        def exists(self) -> bool:
            return state_pid is not None

    monkeypatch.setattr(daemon_module, "DAEMON_STATE_FILE", _FakeStateFile())


# ---------------------------------------------------------------------------
# SC-6b — singleton + scoped spawn-path reaping
# ---------------------------------------------------------------------------


def test_reaper_reaps_same_executable_orphans(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two same-interpreter orphans on fresh ports are both reaped (the #1071 leak)."""
    my_exe = owner_module.canonical_executable_scope()
    orphans = [
        _FakeProc(1001, [my_exe, "-c", "run_sync_daemon(9401)"], my_exe),
        _FakeProc(1002, [my_exe, "-c", "run_sync_daemon(9402)"], my_exe),
    ]
    _install_fake_host(monkeypatch, orphans, state_pid=None)

    result = reap_orphan_daemons()

    assert isinstance(result, ReapResult)
    assert sorted(result.reaped) == [1001, 1002]
    assert result.skipped_out_of_scope == []
    assert all(p.terminated for p in orphans)


def test_reaper_skips_other_executable_daemons(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A daemon from a different interpreter / $HOME is left untouched (reaper-over-kill guard)."""
    my_exe = owner_module.canonical_executable_scope()
    foreign = _FakeProc(
        2001,
        ["/opt/other-venv/bin/python", "-c", "run_sync_daemon(9403)"],
        "/opt/other-venv/bin/python",
    )
    mine = _FakeProc(2002, [my_exe, "-c", "run_sync_daemon(9404)"], my_exe)
    _install_fake_host(monkeypatch, [foreign, mine], state_pid=None)

    result = reap_orphan_daemons()

    assert result.reaped == [2002]
    assert result.skipped_out_of_scope == [2001]
    assert foreign.terminated is False
    assert foreign.killed is False
    assert mine.terminated is True


def test_reaper_excludes_recorded_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    """The recorded singleton PID is never reaped — one daemon survives per scope."""
    my_exe = owner_module.canonical_executable_scope()
    singleton = _FakeProc(3001, [my_exe, "-c", "run_sync_daemon(9400)"], my_exe)
    orphan = _FakeProc(3002, [my_exe, "-c", "run_sync_daemon(9405)"], my_exe)
    _install_fake_host(monkeypatch, [singleton, orphan], state_pid=3001)

    result = reap_orphan_daemons()

    assert result.reaped == [3002]
    assert singleton.terminated is False
    assert orphan.terminated is True


def test_reaper_dry_run_sends_no_signals(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dry-run classifies in-scope orphans without terminating anything."""
    my_exe = owner_module.canonical_executable_scope()
    orphan = _FakeProc(4001, [my_exe, "-c", "run_sync_daemon(9406)"], my_exe)
    _install_fake_host(monkeypatch, [orphan], state_pid=None)

    result = reap_orphan_daemons(dry_run=True)

    assert result.reaped == [4001]
    assert orphan.terminated is False
    assert orphan.killed is False


def test_spawn_path_invokes_canonical_reaper(monkeypatch: pytest.MonkeyPatch) -> None:
    """``ensure_sync_daemon_running`` spawn path reaps stale orphans before spawning.

    The canonical reaper is the SINGLE thing wired into the hot path; we prove
    the wiring without spawning a real daemon by stubbing the spawn primitives.
    """
    reap_calls: list[bool] = []

    def fake_reap() -> None:
        reap_calls.append(True)

    monkeypatch.setattr(daemon_module, "_reap_same_executable_orphans", fake_reap)
    # No reusable existing daemon → we will reach the reap-then-spawn branch.
    monkeypatch.setattr(daemon_module, "_reuse_or_cleanup_existing_daemon", lambda: None)
    monkeypatch.setattr(daemon_module, "_find_free_port", lambda: 9499)

    class _StubProc:
        pid = 7777

    monkeypatch.setattr(
        daemon_module, "_spawn_sync_daemon_process", lambda _port, _token: _StubProc()
    )
    # Make the freshly spawned daemon report healthy immediately.
    monkeypatch.setattr(
        daemon_module, "_check_sync_daemon_health", lambda *a, **k: True
    )
    monkeypatch.setattr(
        daemon_module, "_write_daemon_file", lambda *a, **k: None
    )

    url, port, started = daemon_module._ensure_sync_daemon_running_locked()

    assert reap_calls == [True], "spawn path must invoke the canonical reaper exactly once"
    assert port == 9499
    assert started is True
    assert url == "http://127.0.0.1:9499"


# ---------------------------------------------------------------------------
# SC-7 — exactly one reaper + one liveness probe remain (source inspection)
# ---------------------------------------------------------------------------


def _count_defs(name: str, *rel_paths: str) -> int:
    pattern = re.compile(rf"^\s*def {re.escape(name)}\b", re.MULTILINE)
    total = 0
    for rel in rel_paths:
        text = (_SRC_ROOT / rel).read_text(encoding="utf-8")
        total += len(pattern.findall(text))
    return total


def test_exactly_one_canonical_kill_path() -> None:
    """SC-7: the single canonical kill escalation is defined once (in owner.py)."""
    assert (
        _count_defs(
            "_sweep_daemon_process",
            "sync/owner.py",
            "sync/orphan_sweep.py",
            "sync/daemon.py",
            "dashboard/lifecycle.py",
        )
        == 1
    )


def test_exactly_one_canonical_reaper_entry_point() -> None:
    """SC-7: the single reaper entry point wired into spawn is defined once."""
    assert (
        _count_defs(
            "reap_orphan_daemons",
            "sync/owner.py",
            "sync/orphan_sweep.py",
            "sync/daemon.py",
            "dashboard/lifecycle.py",
        )
        == 1
    )


def test_exactly_one_liveness_probe_implementation() -> None:
    """SC-7: ``_is_process_alive`` has a single real implementation in sync/daemon.py.

    The dashboard retains a same-named wrapper that delegates to the canonical
    one (preserving its import surface), so its body must be a one-line
    delegation — never a second psutil-based implementation.
    """
    daemon_text = (_SRC_ROOT / "sync/daemon.py").read_text(encoding="utf-8")
    lifecycle_text = (_SRC_ROOT / "dashboard/lifecycle.py").read_text(encoding="utf-8")

    # Canonical: defines and uses psutil directly.
    assert "def _is_process_alive(pid: int) -> bool:" in daemon_text
    assert "psutil.Process(pid)" in daemon_text

    # Dashboard wrapper must delegate, not re-implement against psutil.
    assert "_canonical_is_process_alive(pid)" in lifecycle_text
    wrapper = lifecycle_text.split("def _is_process_alive(pid: int) -> bool:", 1)[1]
    wrapper_body = wrapper.split("\ndef ", 1)[0]
    assert "psutil.Process(pid)" not in wrapper_body
