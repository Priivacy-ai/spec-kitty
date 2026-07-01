"""SC-6b / SC-7 — sync-daemon singleton + reaper consolidation (WP12, #1071/FR-015).

These tests lock the two acceptance criteria for the daemon half of #1789:

* **SC-6b** — across multiple interpreters on one host, exactly one
  ``run_sync_daemon`` runs per daemon-root scope and stale same-scope orphans
  are reaped at the ``ensure_sync_daemon_running`` spawn path. The reap scope
  authority is the daemon-root scope marker (FR-008): a candidate whose cmdline
  carries the marker for THIS process's daemon state root is in-scope and will
  be reaped regardless of interpreter/executable identity. Executable identity is
  stale-version evidence only, not a skip gate. A daemon carrying a marker for a
  different ``$HOME``/state root (cross-root) or one carrying NO marker at all
  (pre-marker spawns) is never killed (reaper-over-kill guard, #1071).
* **SC-7** — exactly ONE daemon-lifecycle reaper and ONE liveness probe remain
  after the three-reaper collapse. Verified by source inspection (``rg``-style
  scan): the canonical kill path, the canonical reaper entry point, and
  ``_is_process_alive`` are each defined once across ``sync/`` + ``dashboard/``.

No real ``run_sync_daemon`` subprocess is spawned here, so there is no
test-induced daemon leak: the reaper is exercised against in-memory fake
``psutil`` processes.
"""

from __future__ import annotations

import contextlib
import re
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from specify_cli.sync import daemon as daemon_module
from specify_cli.sync import owner as owner_module
from specify_cli.sync.owner import ReapResult, reap_orphan_daemons

pytestmark = [pytest.mark.unit, pytest.mark.fast]


_SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "specify_cli"

# Mirror ``daemon.DAEMON_SCOPE_ARG_PREFIX`` / ``daemon.DAEMON_EXEC_ARG_PREFIX``
# (coupling asserted below) so the fixtures stay literal about the on-host
# cmdline shape being matched.
_SCOPE_MARKER_PREFIX = "--spec-kitty-daemon-root="
_EXEC_MARKER_PREFIX = "--spec-kitty-daemon-exec="


def _scope_marker(root: Path) -> str:
    """Build the daemon-root scope marker argv element for *root*."""
    return _SCOPE_MARKER_PREFIX + str(root.resolve())


def _exec_marker(executable: str) -> str:
    """Build the spawn-recorded interpreter identity argv element."""
    return _EXEC_MARKER_PREFIX + executable


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
    daemon_root: Path,
) -> None:
    """Wire fake psutil + an absent/empty state file into the daemon module.

    ``daemon_root`` pins the reaper's own daemon-root scope (normally derived
    from ``$HOME``) to a tmp path so marker matching is hermetic.
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


@pytest.mark.quarantine  # host-dependent process-shape reaping (psutil exe/argv0) — environmental (Wave-0 orphan-bind triage, #2034/#2283)
def test_reaper_reaps_same_executable_orphans(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Two same-interpreter, same-root orphans on fresh ports are both reaped (the #1071 leak)."""
    my_exe = owner_module.canonical_executable_scope()
    my_root = tmp_path / "home" / ".spec-kitty"
    orphans = [
        _FakeProc(1001, [my_exe, "-c", "run_sync_daemon(9401)", _scope_marker(my_root)], my_exe),
        _FakeProc(1002, [my_exe, "-c", "run_sync_daemon(9402)", _scope_marker(my_root)], my_exe),
    ]
    _install_fake_host(monkeypatch, orphans, state_pid=None, daemon_root=my_root)

    result = reap_orphan_daemons()

    assert isinstance(result, ReapResult)
    assert sorted(result.reaped) == [1001, 1002]
    assert result.skipped_out_of_scope == []
    assert all(p.terminated for p in orphans)


@pytest.mark.quarantine  # host-dependent process-shape reaping (psutil exe/argv0) — environmental (Wave-0 orphan-bind triage, #2034/#2283)
def test_reaper_skips_same_executable_daemon_from_other_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Same interpreter, different $HOME/state root → skipped, never killed.

    Two daemons share ``canonical_executable_scope`` but carry scope markers
    for different daemon state roots (the shared-interpreter / multi-$HOME
    host). Only the daemon belonging to THIS root is reaped; the cross-scope
    one is a legitimately-separate daemon (reaper-over-kill guard, #1071).
    """
    my_exe = owner_module.canonical_executable_scope()
    my_root = tmp_path / "home-a" / ".spec-kitty"
    other_root = tmp_path / "home-b" / ".spec-kitty"
    foreign = _FakeProc(
        2001,
        [my_exe, "-c", "run_sync_daemon(9403)", _scope_marker(other_root)],
        my_exe,
    )
    mine = _FakeProc(
        2002,
        [my_exe, "-c", "run_sync_daemon(9404)", _scope_marker(my_root)],
        my_exe,
    )
    _install_fake_host(monkeypatch, [foreign, mine], state_pid=None, daemon_root=my_root)

    result = reap_orphan_daemons()

    assert result.reaped == [2002]
    assert result.skipped_out_of_scope == [2001]
    assert foreign.terminated is False
    assert foreign.killed is False
    assert mine.terminated is True


@pytest.mark.quarantine  # host-dependent process-shape reaping (psutil exe/argv0) — environmental (Wave-0 orphan-bind triage, #2034/#2283)
def test_reaper_reaps_other_interpreter_same_scope_daemon(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A same-scope daemon from a different interpreter is reaped (FR-008).

    # FR-008: scope-marker is the kill authority; exe mismatch is stale-version
    # evidence only, not a skip gate.  A different interpreter with a MATCHING
    # daemon-root marker is still in-scope and must be reaped.
    """
    my_root = tmp_path / "home" / ".spec-kitty"
    foreign = _FakeProc(
        2101,
        ["/opt/other-venv/bin/python", "-c", "run_sync_daemon(9405)", _scope_marker(my_root)],
        "/opt/other-venv/bin/python",
    )
    _install_fake_host(monkeypatch, [foreign], state_pid=None, daemon_root=my_root)

    result = reap_orphan_daemons()

    assert result.reaped == [2101]           # FR-008: same-scope, stale exe → reaped
    assert result.skipped_out_of_scope == []
    assert foreign.terminated is True


def test_reaper_skips_unmarked_pre_marker_daemons(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A same-interpreter daemon with NO scope marker is conservatively skipped.

    Daemons spawned before the marker existed cannot be positively attributed
    to a daemon root, so the auto-reaper leaves them alone. ``sync status`` /
    ``sync doctor`` surface them (via ``scan_sync_daemons``) for the operator;
    clearing them is a manual step — no production surface invokes
    ``cleanup_orphan_sync_daemons`` automatically.
    """
    my_exe = owner_module.canonical_executable_scope()
    my_root = tmp_path / "home" / ".spec-kitty"
    unmarked = _FakeProc(2201, [my_exe, "-c", "run_sync_daemon(9406)"], my_exe)
    _install_fake_host(monkeypatch, [unmarked], state_pid=None, daemon_root=my_root)

    result = reap_orphan_daemons()

    assert result.reaped == []
    assert result.skipped_out_of_scope == [2201]
    assert unmarked.terminated is False
    assert unmarked.killed is False


@pytest.mark.quarantine  # host-dependent process-shape reaping (psutil exe/argv0) — environmental (Wave-0 orphan-bind triage, #2034/#2283)
def test_reaper_matches_when_exe_diverges_but_argv0_is_spawn_interpreter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A divergent ``exe()`` with a preserved argv[0] still matches via argv[0].

    This pins the argv[0] identity dimension on its own (e.g. ``exe()``
    misreported or unreadable while argv was left intact). NOTE: this is NOT
    the real macOS framework shape — there the re-exec rewrites BOTH ``exe()``
    AND argv[0] to the ``Python.app`` stub; that shape is covered by
    ``test_reaper_matches_macos_framework_rewritten_exe_and_argv0``.
    """
    my_root = tmp_path / "home" / ".spec-kitty"
    framework_stub = (
        "/opt/fake-framework/Python.framework/Versions/3.11/"
        "Resources/Python.app/Contents/MacOS/Python"
    )
    orphan = _FakeProc(
        2301,
        [sys.executable, "-c", "run_sync_daemon(9407)", _scope_marker(my_root)],
        framework_stub,
    )
    _install_fake_host(monkeypatch, [orphan], state_pid=None, daemon_root=my_root)

    result = reap_orphan_daemons()

    assert result.reaped == [2301]
    assert result.skipped_out_of_scope == []
    assert orphan.terminated is True


@pytest.mark.quarantine  # host-dependent process-shape reaping (psutil exe/argv0) — environmental (Wave-0 orphan-bind triage, #2034/#2283)
def test_reaper_matches_macos_framework_rewritten_exe_and_argv0(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """macOS framework Python rewrites BOTH ``exe()`` AND argv[0] to the stub.

    Empirically proven on Homebrew framework builds: the spawned interpreter
    re-execs ``Resources/Python.app/Contents/MacOS/Python``, so the running
    daemon's ``Process.exe()`` and ``cmdline[0]`` BOTH report the stub path
    while ``canonical_executable_scope()`` is the resolved ``bin/python3.x``.
    Neither live-process identity source can ever match — the reaper must
    recover the spawn interpreter from the spawn-recorded exec marker
    (``daemon.DAEMON_EXEC_ARG_PREFIX``) embedded in argv at spawn, which the
    re-exec preserves verbatim.
    """
    my_scope = owner_module.canonical_executable_scope()
    my_root = tmp_path / "home" / ".spec-kitty"
    framework_stub = (
        "/opt/fake-framework/Python.framework/Versions/3.11/"
        "Resources/Python.app/Contents/MacOS/Python"
    )
    orphan = _FakeProc(
        2401,
        [
            framework_stub,  # argv[0] rewritten by the re-exec, like exe()
            "-c",
            "run_sync_daemon(9411)",
            _scope_marker(my_root),
            _exec_marker(my_scope),
        ],
        framework_stub,
    )
    _install_fake_host(monkeypatch, [orphan], state_pid=None, daemon_root=my_root)

    result = reap_orphan_daemons()

    assert result.reaped == [2401]
    assert result.skipped_out_of_scope == []
    assert orphan.terminated is True


@pytest.mark.quarantine  # host-dependent process-shape reaping (psutil exe/argv0) — environmental (Wave-0 orphan-bind triage, #2034/#2283)
def test_reaper_reaps_rewritten_same_scope_daemon_without_exec_marker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Same-scope daemon with rewritten exe()+argv[0] and no exec marker is reaped (FR-008).

    # FR-008: scope-marker is the kill authority.  Once the daemon-root marker
    # matches and the spawn shape is present, an unprovable interpreter (macOS
    # framework stub with no exec-identity token) no longer skips the candidate
    # — the root marker is sufficient kill authority.
    """
    my_root = tmp_path / "home" / ".spec-kitty"
    framework_stub = (
        "/opt/fake-framework/Python.framework/Versions/3.11/"
        "Resources/Python.app/Contents/MacOS/Python"
    )
    orphan = _FakeProc(
        2501,
        [framework_stub, "-c", "run_sync_daemon(9412)", _scope_marker(my_root)],
        framework_stub,
    )
    _install_fake_host(monkeypatch, [orphan], state_pid=None, daemon_root=my_root)

    result = reap_orphan_daemons()

    assert result.reaped == [2501]           # FR-008: same-scope marker is the kill authority
    assert result.skipped_out_of_scope == []
    assert orphan.terminated is True


@pytest.mark.quarantine  # host-dependent process-shape reaping (psutil exe/argv0) — environmental (Wave-0 orphan-bind triage, #2034/#2283)
def test_reaper_skips_non_spawn_shaped_cmdline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A cmdline without the ``-c``+``run_sync_daemon`` spawn signature is skipped.

    Marker and interpreter identity alone are not enough: the kill decision
    also requires the production spawn shape (a ``-c`` flag whose script
    payload references ``run_sync_daemon``). A tool that merely *mentions*
    the daemon in a script-path argv (and somehow carries the markers) is
    never a kill candidate.
    """
    my_exe = owner_module.canonical_executable_scope()
    my_root = tmp_path / "home" / ".spec-kitty"
    bystander = _FakeProc(
        2601,
        [my_exe, "/tmp/run_sync_daemon_helper.py", _scope_marker(my_root), _exec_marker(my_exe)],
        my_exe,
    )
    _install_fake_host(monkeypatch, [bystander], state_pid=None, daemon_root=my_root)

    result = reap_orphan_daemons()

    assert result.reaped == []
    assert result.skipped_out_of_scope == [2601]
    assert bystander.terminated is False
    assert bystander.killed is False


@pytest.mark.quarantine  # host-dependent process-shape reaping (psutil exe/argv0) — environmental (Wave-0 orphan-bind triage, #2034/#2283)
def test_reaper_excludes_recorded_singleton(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The recorded singleton PID is never reaped — one daemon survives per scope."""
    my_exe = owner_module.canonical_executable_scope()
    my_root = tmp_path / "home" / ".spec-kitty"
    singleton = _FakeProc(
        3001, [my_exe, "-c", "run_sync_daemon(9400)", _scope_marker(my_root)], my_exe
    )
    orphan = _FakeProc(
        3002, [my_exe, "-c", "run_sync_daemon(9408)", _scope_marker(my_root)], my_exe
    )
    _install_fake_host(monkeypatch, [singleton, orphan], state_pid=3001, daemon_root=my_root)

    result = reap_orphan_daemons()

    assert result.reaped == [3002]
    assert singleton.terminated is False
    assert orphan.terminated is True


@pytest.mark.quarantine  # host-dependent process-shape reaping (psutil exe/argv0) — environmental (Wave-0 orphan-bind triage, #2034/#2283)
def test_reaper_dry_run_sends_no_signals(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Dry-run classifies in-scope orphans without terminating anything."""
    my_exe = owner_module.canonical_executable_scope()
    my_root = tmp_path / "home" / ".spec-kitty"
    orphan = _FakeProc(
        4001, [my_exe, "-c", "run_sync_daemon(9409)", _scope_marker(my_root)], my_exe
    )
    _install_fake_host(monkeypatch, [orphan], state_pid=None, daemon_root=my_root)

    result = reap_orphan_daemons(dry_run=True)

    assert result.reaped == [4001]
    assert orphan.terminated is False
    assert orphan.killed is False


def test_scope_marker_prefix_matches_daemon_constant() -> None:
    """The fixture marker prefix must stay coupled to the spawn-side constant."""
    assert _SCOPE_MARKER_PREFIX == daemon_module.DAEMON_SCOPE_ARG_PREFIX


def test_exec_marker_prefix_matches_daemon_constant() -> None:
    """The fixture exec-marker prefix must stay coupled to the spawn-side constant."""
    assert _EXEC_MARKER_PREFIX == daemon_module.DAEMON_EXEC_ARG_PREFIX


def test_spawned_daemon_cmdline_carries_scope_marker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``_spawn_sync_daemon_process`` embeds this root's scope marker in argv.

    Without this wiring the canonical reaper could never positively attribute
    a real spawned daemon to its daemon state root.
    """
    captured: dict[str, list[str]] = {}

    class _FakePopen:
        pid = 4242

        def __init__(self, args: list[str], **kwargs: object) -> None:
            captured["args"] = list(args)

    monkeypatch.setattr("specify_cli.sync.daemon.subprocess.Popen", _FakePopen)
    monkeypatch.setattr(daemon_module, "DAEMON_LOG_FILE", tmp_path / "daemon.log")

    proc = daemon_module._spawn_sync_daemon_process(9410, "tok")

    assert proc.pid == 4242
    markers = [
        arg for arg in captured["args"] if arg.startswith(daemon_module.DAEMON_SCOPE_ARG_PREFIX)
    ]
    assert markers == [
        daemon_module.DAEMON_SCOPE_ARG_PREFIX + daemon_module._daemon_scope_root()
    ]


def test_spawned_daemon_cmdline_carries_exec_identity_marker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``_spawn_sync_daemon_process`` records the spawn interpreter in argv.

    The exec marker is what survives the macOS framework re-exec (which
    rewrites both ``exe()`` and argv[0] to the ``Python.app`` stub), so the
    reaper compares spawn-recorded identity instead of guessing platform
    rewrites.
    """
    captured: dict[str, list[str]] = {}

    class _FakePopen:
        pid = 4343

        def __init__(self, args: list[str], **kwargs: object) -> None:
            captured["args"] = list(args)

    monkeypatch.setattr("specify_cli.sync.daemon.subprocess.Popen", _FakePopen)
    monkeypatch.setattr(daemon_module, "DAEMON_LOG_FILE", tmp_path / "daemon.log")

    daemon_module._spawn_sync_daemon_process(9413, "tok")

    exec_markers = [
        arg for arg in captured["args"] if arg.startswith(daemon_module.DAEMON_EXEC_ARG_PREFIX)
    ]
    assert exec_markers == [daemon_module.daemon_exec_marker()]
    recorded = exec_markers[0][len(daemon_module.DAEMON_EXEC_ARG_PREFIX):]
    # The recorded identity must equal the canonical interpreter scope the
    # reap-time foreground computes, or the comparison can never succeed.
    assert recorded == owner_module.canonical_executable_scope()


@pytest.mark.quarantine  # host-dependent process-shape reaping (psutil exe/argv0) — environmental (Wave-0 orphan-bind triage, #2034/#2283)
@pytest.mark.skipif(sys.platform == "win32", reason="POSIX spawn shape (start_new_session)")
def test_live_stub_with_production_spawn_shape_is_reaped_on_this_host(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Host-level proof: a REAL process spawned with the production argv shape is reaped.

    Uses the actual production spawner (``_spawn_sync_daemon_process``) with
    only the ``-c`` script swapped for an inert sleep stub, so the argv shape
    — interpreter, ``-c``, run_sync_daemon-referencing script, scope marker,
    exec marker — is exactly what real daemons carry. On macOS framework
    Python (e.g. Homebrew) the live process reports the ``Python.app`` stub
    for BOTH ``exe()`` and argv[0]; the reaper must still positively match it
    via the spawn-recorded exec marker. On non-framework hosts the live
    identity matches directly; either way the stub must be classified
    in-scope and reaped.
    """
    my_root = tmp_path / "home" / ".spec-kitty"
    my_root.mkdir(parents=True)
    pinned_root = str(my_root.resolve())
    monkeypatch.setattr(daemon_module, "_daemon_scope_root", lambda: pinned_root)
    monkeypatch.setattr(owner_module, "_daemon_scope_root", lambda: pinned_root)
    monkeypatch.setattr(daemon_module, "DAEMON_STATE_FILE", tmp_path / "sync-daemon")
    monkeypatch.setattr(daemon_module, "DAEMON_LOG_FILE", tmp_path / "daemon.log")

    ready_file = tmp_path / "stub-ready"
    stub_script = (
        "# inert sleep stub standing in for: "
        "from specify_cli.sync.daemon import run_sync_daemon\n"
        "import pathlib, time\n"
        f"pathlib.Path({str(ready_file)!r}).touch()\n"
        "time.sleep(120)\n"
    )
    monkeypatch.setattr(
        daemon_module, "_background_script", lambda _port, _token: stub_script
    )

    proc = daemon_module._spawn_sync_daemon_process(9414, "tok")
    try:
        deadline = time.monotonic() + 15.0
        while not ready_file.exists():
            assert time.monotonic() < deadline, "stub process never came up"
            assert proc.poll() is None, "stub process exited prematurely"
            time.sleep(0.05)

        # Classification proof first (no signals): the live stub — whose
        # exe()/argv[0] macOS may have rewritten to the Python.app stub —
        # must be the ONLY process attributed to this (tmp) daemon root.
        dry = reap_orphan_daemons(dry_run=True)
        assert dry.reaped == [proc.pid]
        assert proc.poll() is None

        # Now the real reap: the stub must actually die.
        result = reap_orphan_daemons()
        assert proc.pid in result.reaped
        deadline = time.monotonic() + 5.0
        while proc.poll() is None:
            assert time.monotonic() < deadline, "stub survived the reap"
            time.sleep(0.05)
    finally:
        if proc.poll() is None:
            proc.kill()
            with contextlib.suppress(Exception):
                proc.wait(timeout=5)


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
    assert url == "http://localhost:9499"


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
