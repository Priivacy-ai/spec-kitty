"""WP02 — Reaper scope authority tests (T006–T010).

Proves that the daemon-root scope marker is the **primary kill authority**
after FR-008: executable / version identity is stale-version evidence, not a
skip gate.  Same-scope daemons from a prior installed version are now reaped;
cross-root and pre-marker daemons remain strictly untouched.

Key design (WP02)
-----------------
* Kill gate in ``reap_orphan_daemons``: scope marker == root AND spawn shape.
  Executable identity is NOT in the gate (FR-008).
* ``_classify_orphan`` (testable helper) calls ``classify_candidate`` for
  structured output / ``skipped_details``; it accepts an optional ``health``
  kwarg so callers with port access can supply a live probe and get a fully
  classified record (used by WP03 ``auth doctor`` path).
* ``owner.json`` (``read_owner_record``) is never consulted for kill decisions
  (FR-003).

All tests use the ``_FakeProc`` double pattern (no real subprocess, no real
daemon port) for fast, deterministic execution.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import psutil
import pytest

from specify_cli.sync import daemon as daemon_module
from specify_cli.sync import owner as owner_module
from specify_cli.sync.classification import (
    CleanupClass,
    ForegroundScope,
    HealthProbe,
    SingletonRef,
    SkipReason,
)
from specify_cli.sync.owner import ReapResult, _classify_orphan, reap_orphan_daemons

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_SCOPE_MARKER_PREFIX = "--spec-kitty-daemon-root="
_EXEC_MARKER_PREFIX = "--spec-kitty-daemon-exec="


def _scope_marker(root: Path) -> str:
    return _SCOPE_MARKER_PREFIX + str(root.resolve())


def _exec_marker(executable: str) -> str:
    return _EXEC_MARKER_PREFIX + executable


# ---------------------------------------------------------------------------
# Fake psutil process double (mirrors test_daemon_singleton_reaper_consolidation)
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


# ---------------------------------------------------------------------------
# Health probe helpers for _classify_orphan unit tests
# ---------------------------------------------------------------------------


def _healthy_probe(pid: int, port: int, package_version: str = "3.2.4") -> HealthProbe:
    """Build a ``HealthProbe`` simulating a live, correctly self-reporting daemon."""
    return HealthProbe(
        responded=True,
        status="ok",
        protocol_version=1,
        package_version=package_version,
        daemon_family="sync",
        owner_pid=pid,
        owner_port=port,
        queue_db_path=None,
        auth_scope=None,
        server_url=None,
    )


def _no_response_probe() -> HealthProbe:
    """Build a ``HealthProbe`` simulating a wedged / unresponsive daemon."""
    return HealthProbe(
        responded=False,
        status=None,
        protocol_version=None,
        package_version=None,
        daemon_family=None,
        owner_pid=None,
        owner_port=None,
        queue_db_path=None,
        auth_scope=None,
        server_url=None,
    )


# ---------------------------------------------------------------------------
# Test fixture helper
# ---------------------------------------------------------------------------


def _install_fake_host(
    monkeypatch: pytest.MonkeyPatch,
    procs: list[_FakeProc],
    *,
    state_pid: int | None,
    daemon_root: Path,
) -> None:
    """Wire fake psutil + state file into daemon/owner modules.

    Mirrors the fixture from ``test_daemon_singleton_reaper_consolidation``
    so tests run against deterministic, in-memory process state.
    """
    monkeypatch.setattr(
        owner_module,
        "_daemon_scope_root",
        lambda: str(daemon_root.resolve()),
    )

    def fake_iter(attrs: object = None) -> list[_FakeProc]:  # noqa: ARG001
        return list(procs)

    def fake_lookup(pid: int) -> _FakeProc:
        for proc in procs:
            if proc.pid == pid:
                return proc
        raise daemon_module.psutil.NoSuchProcess(pid)

    monkeypatch.setattr(daemon_module.psutil, "process_iter", fake_iter)
    monkeypatch.setattr(daemon_module.psutil, "Process", fake_lookup)

    monkeypatch.setattr(
        daemon_module,
        "_parse_daemon_file",
        lambda _path: (None, None, None, state_pid),
    )

    class _FakeStateFile:
        def exists(self) -> bool:
            return state_pid is not None

    monkeypatch.setattr(daemon_module, "DAEMON_STATE_FILE", _FakeStateFile())

    def fake_probe_health(port: int) -> HealthProbe:
        for proc in procs:
            parsed_port = owner_module._extract_port_from_cmdline(proc.cmdline)
            if parsed_port == port:
                return _healthy_probe(proc.pid, port, package_version="3.2.2")
        return _no_response_probe()

    monkeypatch.setattr(owner_module, "_probe_health", fake_probe_health)


# ---------------------------------------------------------------------------
# T006 / T007 / T008 — FR-008: exe-identity gate is removed; same-scope
# daemons from prior versions are now reaped
# ---------------------------------------------------------------------------


def test_same_scope_older_version_is_reaped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """FR-008: same-scope daemon with a different exe/version is now reaped.

    Before WP02 the reaper required the orphan's executable to match the
    foreground interpreter; a prior-version daemon with a different
    ``sys.executable`` was unconditionally skipped.  After WP02 the scope
    marker alone is the kill authority: marker==scope + spawn-shape → reaped,
    regardless of interpreter path or package version.
    """
    my_root = tmp_path / "home" / ".spec-kitty"
    stale_exe = "/opt/old-venv/bin/python"
    orphan_pid = 5001
    orphan_port = 9440

    # Different executable than the foreground, but same scope marker.
    orphan = _FakeProc(
        orphan_pid,
        [stale_exe, "-c", f"run_sync_daemon({orphan_port})", _scope_marker(my_root)],
        stale_exe,
    )
    _install_fake_host(monkeypatch, [orphan], state_pid=None, daemon_root=my_root)

    result = reap_orphan_daemons()

    assert result.reaped == [orphan_pid], (
        "same-scope daemon with different exe/version must be reaped (FR-008)"
    )
    assert result.skipped_out_of_scope == []
    assert orphan.terminated is True


def test_same_scope_older_version_dry_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Dry-run: same-scope older-version orphan is classified as would-reap."""
    my_root = tmp_path / "home" / ".spec-kitty"
    stale_exe = "/opt/old-venv/bin/python"
    orphan_pid = 5002
    orphan_port = 9441

    orphan = _FakeProc(
        orphan_pid,
        [stale_exe, "-c", f"run_sync_daemon({orphan_port})", _scope_marker(my_root)],
        stale_exe,
    )
    _install_fake_host(monkeypatch, [orphan], state_pid=None, daemon_root=my_root)

    result = reap_orphan_daemons(dry_run=True)

    assert result.reaped == [orphan_pid]
    assert orphan.terminated is False, "dry_run must not send signals"


def test_same_scope_unresponsive_is_not_reaped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """D-01 / FR-006: same-scope spawn-shaped daemon without health is not auto-killed."""
    my_root = tmp_path / "home" / ".spec-kitty"
    stale_exe = "/opt/old-venv/bin/python"
    orphan_pid = 5004
    orphan_port = 9441

    orphan = _FakeProc(
        orphan_pid,
        [stale_exe, "-c", f"run_sync_daemon({orphan_port})", _scope_marker(my_root)],
        stale_exe,
    )
    _install_fake_host(monkeypatch, [orphan], state_pid=None, daemon_root=my_root)
    monkeypatch.setattr(owner_module, "_probe_health", lambda _port: _no_response_probe())

    result = reap_orphan_daemons()

    assert result.reaped == []
    assert orphan.terminated is False
    assert len(result.skipped_details) == 1
    assert result.skipped_details[0].cleanup_class == CleanupClass.OPERATOR_REQUIRED
    assert result.skipped_details[0].skip_reason == SkipReason.unresponsive


def test_skipped_out_of_scope_is_backward_compatible(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Skipped candidates still appear in ``skipped_out_of_scope`` (backward compat)."""
    my_root = tmp_path / "home" / ".spec-kitty"
    other_root = tmp_path / "other" / ".spec-kitty"
    my_exe = sys.executable
    orphan_pid = 5003
    orphan_port = 9442

    orphan = _FakeProc(
        orphan_pid,
        [my_exe, "-c", f"run_sync_daemon({orphan_port})", _scope_marker(other_root)],
        my_exe,
    )
    _install_fake_host(monkeypatch, [orphan], state_pid=None, daemon_root=my_root)

    result = reap_orphan_daemons()

    assert result.reaped == []
    assert orphan_pid in result.skipped_out_of_scope
    assert isinstance(result, ReapResult)


# ---------------------------------------------------------------------------
# T009 — Cross-root and pre-marker safety preserved
# ---------------------------------------------------------------------------


def test_cross_root_is_never_reaped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Cross-root daemon must never be reaped (T009, operator_required/cross_root)."""
    my_root = tmp_path / "home-a" / ".spec-kitty"
    other_root = tmp_path / "home-b" / ".spec-kitty"
    my_exe = sys.executable
    foreign_pid = 6001
    foreign_port = 9443

    foreign = _FakeProc(
        foreign_pid,
        [my_exe, "-c", f"run_sync_daemon({foreign_port})", _scope_marker(other_root)],
        my_exe,
    )
    _install_fake_host(monkeypatch, [foreign], state_pid=None, daemon_root=my_root)

    result = reap_orphan_daemons()

    assert result.reaped == []
    assert foreign_pid in result.skipped_out_of_scope
    assert foreign.terminated is False
    # skipped_details must carry structured classification for the skipped candidate.
    cross_root_records = [
        r for r in result.skipped_details
        if r.skip_reason == SkipReason.cross_root
    ]
    assert len(cross_root_records) == 1, "cross_root skip_reason must be in skipped_details"


def test_pre_marker_is_never_reaped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Pre-marker daemon must never be reaped (T009, operator_required/pre_marker)."""
    my_root = tmp_path / "home" / ".spec-kitty"
    my_exe = sys.executable
    orphan_pid = 6101
    orphan_port = 9444

    # No scope marker in cmdline.
    orphan = _FakeProc(
        orphan_pid,
        [my_exe, "-c", f"run_sync_daemon({orphan_port})"],
        my_exe,
    )
    _install_fake_host(monkeypatch, [orphan], state_pid=None, daemon_root=my_root)

    result = reap_orphan_daemons()

    assert result.reaped == []
    assert orphan_pid in result.skipped_out_of_scope
    assert orphan.terminated is False
    pre_marker_records = [
        r for r in result.skipped_details
        if r.skip_reason == SkipReason.pre_marker
    ]
    assert len(pre_marker_records) == 1, "pre_marker skip_reason must be in skipped_details"


def test_recorded_singleton_is_never_reaped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The recorded singleton is excluded from orphan_processes (T009).

    ``scan_sync_daemons`` already filters the state-file PID, so the reaper
    never even encounters the singleton as a candidate.
    """
    my_root = tmp_path / "home" / ".spec-kitty"
    my_exe = sys.executable
    singleton_pid = 7001
    singleton_port = 9445

    singleton = _FakeProc(
        singleton_pid,
        [my_exe, "-c", f"run_sync_daemon({singleton_port})", _scope_marker(my_root)],
        my_exe,
    )
    # state_pid == singleton_pid → excluded from orphan_processes.
    _install_fake_host(monkeypatch, [singleton], state_pid=singleton_pid, daemon_root=my_root)

    result = reap_orphan_daemons()

    assert result.reaped == [], "the recorded singleton must never be reaped"
    assert singleton.terminated is False


def test_owner_json_present_without_marker_not_reaped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """owner.json present but no daemon-root marker → not reaped (FR-003, T009).

    The owner record is reporting data only and must never be the kill
    authority.  A daemon with an owner record but no cmdline scope marker
    is pre-marker and must remain not-reaped.
    """
    my_root = tmp_path / "home" / ".spec-kitty"
    my_exe = sys.executable
    orphan_pid = 7101
    orphan_port = 9446

    # No scope marker — simulates a pre-marker daemon.
    orphan = _FakeProc(
        orphan_pid,
        [my_exe, "-c", f"run_sync_daemon({orphan_port})"],
        my_exe,
    )
    _install_fake_host(monkeypatch, [orphan], state_pid=None, daemon_root=my_root)

    # Patch read_owner_record to return a non-None record: if any code path
    # consulted owner.json for kill authority it would have the opportunity to
    # act — but must not (FR-003).
    from specify_cli.sync.owner import DaemonOwnerRecord

    fake_record = DaemonOwnerRecord(
        pid=orphan_pid,
        port=orphan_port,
        token="fake-token",
        package_version="3.2.2",
        executable_path=my_exe,
        source_checkout_path=str(my_root),
        server_url=f"http://127.0.0.1:{orphan_port}",
        auth_principal=None,
        auth_team=None,
        auth_scope=None,
        queue_db_path=str(my_root / "queue.db"),
        started_at="2026-06-30T00:00:00+00:00",
    )
    monkeypatch.setattr(owner_module, "read_owner_record", lambda: fake_record)

    result = reap_orphan_daemons()

    assert result.reaped == [], (
        "owner.json present but no scope marker must NOT trigger reaping (FR-003)"
    )
    assert orphan.terminated is False


# ---------------------------------------------------------------------------
# T010 — _classify_orphan unit tests (internal helper, tests classifier path)
# ---------------------------------------------------------------------------


def test_classify_orphan_safe_auto_same_scope_old_version(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``_classify_orphan`` with a live health probe: same-scope older-version → safe_auto.

    Proves FR-008 at the classification level: the ``package_version`` / exe
    mismatch is stale-version evidence (row 9 in the decision table) and does
    not prevent ``safe_auto`` once scope marker + spawn-shape + health pass
    rows 1–8.
    """
    my_root = tmp_path / "home" / ".spec-kitty"
    stale_exe = "/opt/old-venv/bin/python"
    orphan_pid = 8001
    orphan_port = 9447

    monkeypatch.setattr(
        owner_module, "_daemon_scope_root", lambda: str(my_root.resolve())
    )

    orphan_cmdline = [
        stale_exe, "-c", f"run_sync_daemon({orphan_port})", _scope_marker(my_root)
    ]

    foreground = ForegroundScope(
        scope_id=str(my_root.resolve()),
        executable_scope=sys.executable,
        singleton=SingletonRef(pid=None, port=None),
    )

    class _StubProc:
        def __init__(self, _pid: int) -> None:
            pass

        def exe(self) -> str:
            return stale_exe

    monkeypatch.setattr(psutil, "Process", _StubProc)

    # Provide a live health probe: owner_pid/port match the listener.
    health = _healthy_probe(orphan_pid, orphan_port, package_version="3.2.2")

    record = _classify_orphan(orphan_pid, orphan_cmdline, foreground, health=health)

    assert record.cleanup_class == CleanupClass.SAFE_AUTO, (
        "same-scope older-version with live health must be safe_auto (FR-008)"
    )
    assert record.skip_reason is None
    assert record.package_version == "3.2.2"


def test_classify_orphan_operator_required_cross_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``_classify_orphan`` returns operator_required/cross_root for a different-root orphan."""
    my_root = tmp_path / "home-a" / ".spec-kitty"
    other_root = tmp_path / "home-b" / ".spec-kitty"
    my_exe = sys.executable
    orphan_pid = 8101
    orphan_port = 9448

    orphan_cmdline = [
        my_exe, "-c", f"run_sync_daemon({orphan_port})", _scope_marker(other_root)
    ]

    foreground = ForegroundScope(
        scope_id=str(my_root.resolve()),
        executable_scope=my_exe,
        singleton=SingletonRef(pid=None, port=None),
    )

    class _StubProc:
        def __init__(self, _pid: int) -> None:
            pass

        def exe(self) -> str:
            return my_exe

    monkeypatch.setattr(psutil, "Process", _StubProc)

    health = _healthy_probe(orphan_pid, orphan_port)
    record = _classify_orphan(orphan_pid, orphan_cmdline, foreground, health=health)

    assert record.cleanup_class == CleanupClass.OPERATOR_REQUIRED
    assert record.skip_reason == SkipReason.cross_root


def test_classify_orphan_operator_required_pre_marker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``_classify_orphan`` returns operator_required/pre_marker for a no-marker orphan."""
    my_root = tmp_path / "home" / ".spec-kitty"
    my_exe = sys.executable
    orphan_pid = 8201
    orphan_port = 9449

    # No scope marker.
    orphan_cmdline = [my_exe, "-c", f"run_sync_daemon({orphan_port})"]

    foreground = ForegroundScope(
        scope_id=str(my_root.resolve()),
        executable_scope=my_exe,
        singleton=SingletonRef(pid=None, port=None),
    )

    class _StubProc:
        def __init__(self, _pid: int) -> None:
            pass

        def exe(self) -> str:
            return my_exe

    monkeypatch.setattr(psutil, "Process", _StubProc)

    health = _healthy_probe(orphan_pid, orphan_port)
    record = _classify_orphan(orphan_pid, orphan_cmdline, foreground, health=health)

    assert record.cleanup_class == CleanupClass.OPERATOR_REQUIRED
    assert record.skip_reason == SkipReason.pre_marker


def test_classify_orphan_operator_required_unresponsive(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``_classify_orphan`` returns operator_required/unresponsive when health is not provided."""
    my_root = tmp_path / "home" / ".spec-kitty"
    my_exe = sys.executable
    orphan_pid = 8301
    orphan_port = 9449

    orphan_cmdline = [
        my_exe, "-c", f"run_sync_daemon({orphan_port})", _scope_marker(my_root)
    ]

    foreground = ForegroundScope(
        scope_id=str(my_root.resolve()),
        executable_scope=my_exe,
        singleton=SingletonRef(pid=None, port=None),
    )

    class _StubProc:
        def __init__(self, _pid: int) -> None:
            pass

        def exe(self) -> str:
            return my_exe

    monkeypatch.setattr(psutil, "Process", _StubProc)

    # No health probe supplied → unresponsive (D-01).
    record = _classify_orphan(orphan_pid, orphan_cmdline, foreground, health=None)

    assert record.cleanup_class == CleanupClass.OPERATOR_REQUIRED
    assert record.skip_reason == SkipReason.unresponsive


def test_classify_orphan_skipped_details_carry_cleanup_class(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``reap_orphan_daemons`` populates ``skipped_details`` with classification records.

    Each skipped candidate must have its ``cleanup_class`` and ``skip_reason``
    available for downstream reporting (T008).
    """
    my_root = tmp_path / "home" / ".spec-kitty"
    other_root = tmp_path / "other" / ".spec-kitty"
    my_exe = sys.executable
    foreign_pid = 8401
    foreign_port = 9449

    foreign = _FakeProc(
        foreign_pid,
        [my_exe, "-c", f"run_sync_daemon({foreign_port})", _scope_marker(other_root)],
        my_exe,
    )
    _install_fake_host(monkeypatch, [foreign], state_pid=None, daemon_root=my_root)

    result = reap_orphan_daemons()

    assert result.reaped == []
    assert len(result.skipped_details) == 1
    detail = result.skipped_details[0]
    assert detail.pid == foreign_pid
    assert detail.cleanup_class == CleanupClass.OPERATOR_REQUIRED
    assert detail.skip_reason == SkipReason.cross_root
