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
  scan): the canonical kill path and the canonical reaper entry point are each
  defined once across ``sync/`` + ``dashboard/``, and ``is_process_alive`` has
  its one real implementation in ``core/process_liveness.py`` (promoted per
  C-002) with ``sync/daemon.py`` carrying only a re-export alias.

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
from specify_cli.sync.owner import reap_orphan_daemons

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.unit, pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


_SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "specify_cli"

# Mirror ``daemon.DAEMON_SCOPE_ARG_PREFIX`` / ``daemon.DAEMON_EXEC_ARG_PREFIX``
# (coupling asserted below) so the fixtures stay literal about the on-host
# cmdline shape being matched.
_SCOPE_MARKER_PREFIX = "--spec-kitty-daemon-root="
_EXEC_MARKER_PREFIX = "--spec-kitty-daemon-exec="


def _scope_marker(root: Path) -> str:
    """Build the daemon-root scope marker argv element for *root*."""
    return _SCOPE_MARKER_PREFIX + str(root.resolve())


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
    # #3624: the spawn probes interpreter capability first; stub it so the argv
    # assertion below exercises the marker wiring, not a real subprocess probe.
    monkeypatch.setattr(
        daemon_module, "_interpreter_can_import_specify_cli", lambda *a, **k: True
    )
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
    # #3624: stub the pre-spawn interpreter-capability probe so the resolved
    # interpreter is sys.executable and the marker equals daemon_exec_marker().
    monkeypatch.setattr(
        daemon_module, "_interpreter_can_import_specify_cli", lambda *a, **k: True
    )
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
    """SC-7: ``is_process_alive`` has a single real implementation, promoted to

    ``core/process_liveness.py`` (C-002) so ``core``/``lanes`` can consult it
    without depending on the daemon's socket/HTTPServer machinery. ``sync/daemon.py``
    keeps only a thin re-export alias (``_is_process_alive = is_process_alive``),
    never a redefinition — ``dashboard/lifecycle.py`` retains a same-named wrapper
    that delegates to the canonical one (preserving its import surface), so its
    body must be a one-line delegation — never a second psutil-based
    implementation.
    """
    core_text = (_SRC_ROOT / "core/process_liveness.py").read_text(encoding="utf-8")
    daemon_text = (_SRC_ROOT / "sync/daemon.py").read_text(encoding="utf-8")
    lifecycle_text = (_SRC_ROOT / "dashboard/lifecycle.py").read_text(encoding="utf-8")

    # Canonical: core/process_liveness.py defines and uses psutil directly.
    assert "def is_process_alive(pid: int) -> bool:" in core_text
    assert "psutil.Process(pid)" in core_text

    # sync/daemon.py must not redefine _is_process_alive as a function — only a
    # thin re-export alias binding to the promoted core implementation.
    assert "def _is_process_alive(pid: int) -> bool:" not in daemon_text
    assert "_is_process_alive = is_process_alive" in daemon_text
    assert "from specify_cli.core.process_liveness import is_process_alive" in daemon_text

    # Dashboard wrapper must delegate, not re-implement against psutil.
    assert "_canonical_is_process_alive(pid)" in lifecycle_text
    wrapper = lifecycle_text.split("def _is_process_alive(pid: int) -> bool:", 1)[1]
    wrapper_body = wrapper.split("\ndef ", 1)[0]
    assert "psutil.Process(pid)" not in wrapper_body
