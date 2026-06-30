"""FR-012 / SC-006 — live reconfirmation of issue #1071 singleton leak.

Issue #1071 documented a same-``$HOME`` singleton leak: multiple
``run_sync_daemon`` processes accumulate under one ``$HOME``/runtime root
because the old reaper's executable-identity gate skipped daemons from
prior interpreter or package versions.  This test reproduces the exact
same-scope scenario with real subprocesses and asserts the new
scope-marker-as-authority model resolves it: stale same-scope daemons are
reaped and exactly **one** singleton survives — no leak.

Decision moment that chose this method:
    ``DM-01KWC36SFC7XVDVA9QQTN1NAK8`` (automated regression test in the
    live-subprocess harness reproducing the same-HOME singleton scenario;
    close #1071 with durable test evidence).

Architectural decision:
    ``docs/adr/3.x/2026-06-30-1-sync-daemon-identity-and-cleanup-classification.md``

Run this suite serially (real ports, OS-global resources)::

    PWHEADLESS=1 .venv/bin/pytest tests/sync/test_issue_1071_singleton_reconfirmation.py -n0 -q

Port range convention:
    WP08 / #1071 reconfirmation: ``[9401, 9425)``
    test_orphan_sweep: ``[9425, 9450)``
"""

from __future__ import annotations

import contextlib
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from specify_cli.sync import daemon as daemon_module
from specify_cli.sync import owner as owner_module
from specify_cli.sync.owner import ReapResult, reap_orphan_daemons
from tests.sync._daemon_harness import (
    DaemonHarness,
    find_free_port_in_range,
    wait_until_port_free,
)

# ---------------------------------------------------------------------------
# Suite metadata
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.integration]

# Skip on Windows — fork/exec lifecycle differences make the live-subprocess
# approach unreliable on win32; the unit-level reaper tests in
# test_daemon_singleton_reaper_consolidation.py provide equivalent win32 coverage.
if sys.platform == "win32":  # pragma: no cover
    pytest.skip("live-subprocess harness is not supported on win32", allow_module_level=True)

# Isolated port sub-range for this suite — must not overlap with other suites.
_PORT_START = 9401
_PORT_END = 9425  # exclusive -> [9401, 9425)

# Version strings that simulate the stale-upgrade scenario (#2261 field data).
_VERSION_STALE_A = "3.2.2"
_VERSION_STALE_B = "3.2.3"
_VERSION_STALE_C = "3.2.4"

# How long to wait for the port to be released after the reaper runs.
_PORT_RELEASE_TIMEOUT_S = 8.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pid_alive(pid: int) -> bool:
    """Return ``True`` if process *pid* is still alive."""
    try:
        import psutil

        return psutil.pid_exists(pid)
    except ImportError:  # pragma: no cover
        import os

        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False


def _port_listening(port: int, *, timeout_s: float = 0.5) -> bool:
    """Return ``True`` if *port* has an active listener within the deadline."""
    import socket

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.1)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.05)
    return False


# ---------------------------------------------------------------------------
# Fixture: isolated scope + harness
# ---------------------------------------------------------------------------


@pytest.fixture()
def harness_1071(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[DaemonHarness, Path]]:
    """Isolated DaemonHarness with a tmp-path scope root for #1071 reconfirmation.

    Pins ``_daemon_scope_root`` in both ``daemon`` and ``owner`` modules to a
    hermetic tmp path so the reaper can only ever match daemons spawned by
    this test — not any real daemon already running on the host.

    Yields ``(harness, daemon_root)`` so tests can:
    *  spawn daemons with ``harness.spawn_daemon(port, ..., scope_root=str(daemon_root))``
    *  write the state file with ``harness.write_state_file(...)``
    """
    daemon_root = tmp_path / "home" / ".spec-kitty"
    daemon_root.mkdir(parents=True)
    pinned_root = str(daemon_root.resolve())

    # Pin scope root for the reaper so only our test daemons match.
    monkeypatch.setattr(daemon_module, "_daemon_scope_root", lambda: pinned_root)
    monkeypatch.setattr(owner_module, "_daemon_scope_root", lambda: pinned_root)

    # Redirect DAEMON_STATE_FILE to tmp_path.
    state_file = tmp_path / "sync-daemon"
    monkeypatch.setattr(daemon_module, "DAEMON_STATE_FILE", state_file)

    h = DaemonHarness(state_file)
    try:
        yield h, daemon_root
    finally:
        h.shutdown()


# ---------------------------------------------------------------------------
# T038 — same-$HOME singleton scenario (#1071 reconfirmation)
# ---------------------------------------------------------------------------


class TestIssue1071SameHomeSingletonLeak:
    """Live-subprocess reconfirmation of the same-``$HOME`` singleton leak (#1071).

    Before this mission: stale same-scope daemons accumulated indefinitely
    because the reaper's executable-identity gate skipped prior-version
    daemons.  After this mission: the daemon-root scope marker is the primary
    kill authority and executable/version identity is evidence only (FR-008),
    so same-scope stale daemons are reaped.
    """

    def test_same_home_stale_daemons_are_reaped_singleton_survives(
        self,
        harness_1071: tuple[DaemonHarness, Path],
        tmp_path: Path,
    ) -> None:
        """Core #1071 reconfirmation: multiple same-scope daemons → exactly one survives.

        Scenario (mirrors the 18-orphan field report from issue #2261):
        - Three same-scope daemons spawn on separate ports, simulating
          daemons left over from versions 3.2.2, 3.2.3, 3.2.4.
        - One is recorded as the singleton in the state file.
        - ``reap_orphan_daemons()`` is called (the spawn-path auto-clean).
        - Assertion: the two stale daemons are reaped, the singleton survives,
          no additional daemon was spawned, and exactly one daemon-port remains
          listening after cleanup.
        """
        harness, daemon_root = harness_1071
        scope_root = str(daemon_root.resolve())

        port_singleton = find_free_port_in_range(_PORT_START, _PORT_END)
        port_stale_a = find_free_port_in_range(port_singleton + 1, _PORT_END)
        port_stale_b = find_free_port_in_range(port_stale_a + 1, _PORT_END)

        # Spawn the singleton first; it will be recorded in the state file.
        proc_singleton = harness.spawn_daemon(
            port_singleton,
            "tok-singleton",
            scope_root=scope_root,
        )
        # Stale daemons: same scope, simulate older versions.
        proc_stale_a = harness.spawn_daemon(
            port_stale_a,
            "tok-stale-a",
            version=_VERSION_STALE_A,
            scope_root=scope_root,
        )
        proc_stale_b = harness.spawn_daemon(
            port_stale_b,
            "tok-stale-b",
            version=_VERSION_STALE_B,
            scope_root=scope_root,
        )

        # Record the singleton in the state file so the reaper excludes it.
        harness.write_state_file(
            f"http://127.0.0.1:{port_singleton}",
            port_singleton,
            "tok-singleton",
            proc_singleton.pid,
        )

        # All three should be listening before we run the reaper.
        assert _port_listening(port_singleton), "singleton never started"
        assert _port_listening(port_stale_a), "stale-a never started"
        assert _port_listening(port_stale_b), "stale-b never started"

        # --- Run the canonical reaper (same path as ensure_sync_daemon_running).
        result = reap_orphan_daemons()

        # Both stale daemons must appear in ``reaped``.
        assert isinstance(result, ReapResult)
        assert proc_stale_a.pid in result.reaped, (
            f"stale-a (pid={proc_stale_a.pid}) was not reaped: {result!r}"
        )
        assert proc_stale_b.pid in result.reaped, (
            f"stale-b (pid={proc_stale_b.pid}) was not reaped: {result!r}"
        )

        # Singleton must not appear in reaped (it was excluded by state-file).
        assert proc_singleton.pid not in result.reaped, (
            f"singleton (pid={proc_singleton.pid}) was wrongly reaped: {result!r}"
        )

        # No failures.
        assert result.failed == [], f"unexpected reap failures: {result.failed!r}"

        # Wait for stale ports to be released.
        released_a = wait_until_port_free(port_stale_a, timeout_s=_PORT_RELEASE_TIMEOUT_S)
        released_b = wait_until_port_free(port_stale_b, timeout_s=_PORT_RELEASE_TIMEOUT_S)
        assert released_a, f"stale-a port {port_stale_a} still listening after reap"
        assert released_b, f"stale-b port {port_stale_b} still listening after reap"

        # Singleton must still be listening — no spurious kill.
        assert _port_listening(port_singleton), (
            f"singleton port {port_singleton} went down after reap"
        )
        assert proc_singleton.poll() is None, (
            f"singleton process (pid={proc_singleton.pid}) exited after reap"
        )

        # Exactly one daemon-port is listening in our allocated range.
        listening_ports = [
            p
            for p in range(_PORT_START, _PORT_END)
            if _port_listening(p, timeout_s=0.1)
        ]
        assert len(listening_ports) == 1, (
            f"expected exactly 1 listening port, got {len(listening_ports)}: {listening_ports}"
        )
        assert listening_ports[0] == port_singleton, (
            f"surviving port {listening_ports[0]} is not the singleton port {port_singleton}"
        )

    def test_same_home_three_version_matrix_all_stale_reaped(
        self,
        harness_1071: tuple[DaemonHarness, Path],
        tmp_path: Path,
    ) -> None:
        """Version matrix: three prior-version same-scope daemons are all reaped.

        Mirrors the 18-orphan scenario: versions 3.2.2, 3.2.3, 3.2.4 are all
        stale (no state-file entry → no singleton exclusion) and must all appear
        in the reap result.
        """
        harness, daemon_root = harness_1071
        scope_root = str(daemon_root.resolve())

        port_a = find_free_port_in_range(_PORT_START, _PORT_END)
        port_b = find_free_port_in_range(port_a + 1, _PORT_END)
        port_c = find_free_port_in_range(port_b + 1, _PORT_END)

        proc_a = harness.spawn_daemon(
            port_a, "tok-a", version=_VERSION_STALE_A, scope_root=scope_root
        )
        proc_b = harness.spawn_daemon(
            port_b, "tok-b", version=_VERSION_STALE_B, scope_root=scope_root
        )
        proc_c = harness.spawn_daemon(
            port_c, "tok-c", version=_VERSION_STALE_C, scope_root=scope_root
        )

        # No state file → all three are orphans; none is the recorded singleton.
        result = reap_orphan_daemons()

        assert isinstance(result, ReapResult)
        assert proc_a.pid in result.reaped, f"3.2.2 daemon not reaped: {result!r}"
        assert proc_b.pid in result.reaped, f"3.2.3 daemon not reaped: {result!r}"
        assert proc_c.pid in result.reaped, f"3.2.4 daemon not reaped: {result!r}"
        assert result.failed == [], f"unexpected reap failures: {result.failed!r}"

        # All three ports should be released.
        for port in (port_a, port_b, port_c):
            assert wait_until_port_free(port, timeout_s=_PORT_RELEASE_TIMEOUT_S), (
                f"port {port} still listening after reap"
            )

    def test_cross_home_daemon_not_reaped(
        self,
        harness_1071: tuple[DaemonHarness, Path],
        tmp_path: Path,
    ) -> None:
        """Cross-``$HOME`` daemon is never reaped — reaper-over-kill guard (#1071).

        A daemon whose scope marker names a DIFFERENT ``$HOME``/daemon-root
        must be classified ``operator_required/cross_root`` and left untouched
        by the spawn-path reaper.  It should appear in
        ``skipped_out_of_scope``, not in ``reaped``.
        """
        harness, daemon_root = harness_1071
        scope_root = str(daemon_root.resolve())

        # Same-scope daemon (will be reaped if no state-file entry).
        port_same = find_free_port_in_range(_PORT_START, _PORT_END)
        proc_same = harness.spawn_daemon(
            port_same, "tok-same", scope_root=scope_root
        )

        # Cross-home daemon: scope marker points to a different state root.
        other_root = str((tmp_path / "other-home" / ".spec-kitty").resolve())
        port_cross = find_free_port_in_range(port_same + 1, _PORT_END)
        proc_cross = harness.spawn_daemon(
            port_cross, "tok-cross", scope_root=other_root
        )

        result = reap_orphan_daemons()

        assert isinstance(result, ReapResult)
        # Same-scope orphan must be reaped.
        assert proc_same.pid in result.reaped, (
            f"same-scope orphan not reaped: {result!r}"
        )
        # Cross-home daemon must NOT be reaped — left to operator_required path.
        assert proc_cross.pid not in result.reaped, (
            f"cross-home daemon was wrongly reaped: {result!r}"
        )
        assert proc_cross.pid in result.skipped_out_of_scope, (
            f"cross-home daemon not in skipped_out_of_scope: {result!r}"
        )

        # Cross-home daemon's port must still be listening.
        assert _port_listening(port_cross), (
            f"cross-home daemon port {port_cross} went down after reap"
        )

        # Wait for same-scope port to be released.
        assert wait_until_port_free(port_same, timeout_s=_PORT_RELEASE_TIMEOUT_S), (
            f"same-scope port {port_same} still listening after reap"
        )

        # Explicit teardown: cross-home daemon was skipped by the reaper so
        # the harness shutdown handles it.

    def test_no_leak_after_reap_pgrep(
        self,
        harness_1071: tuple[DaemonHarness, Path],
        tmp_path: Path,
    ) -> None:
        """Post-reap: no same-scope orphan PIDs survive (no leak).

        Spawns two same-scope orphans, reaps them, and confirms both PIDs
        are gone — durable evidence that the #1071 leak does not remain.
        """
        harness, daemon_root = harness_1071
        scope_root = str(daemon_root.resolve())

        port_a = find_free_port_in_range(_PORT_START, _PORT_END)
        port_b = find_free_port_in_range(port_a + 1, _PORT_END)

        proc_a = harness.spawn_daemon(port_a, "tok-a", scope_root=scope_root)
        proc_b = harness.spawn_daemon(port_b, "tok-b", scope_root=scope_root)

        result = reap_orphan_daemons()

        assert proc_a.pid in result.reaped and proc_b.pid in result.reaped, (
            f"not all orphans reaped: {result!r}"
        )
        assert result.failed == [], f"unexpected failures: {result.failed!r}"

        # Both PIDs must be dead (no leak).
        deadline = time.monotonic() + _PORT_RELEASE_TIMEOUT_S
        for proc in (proc_a, proc_b):
            while proc.poll() is None:
                assert time.monotonic() < deadline, (
                    f"orphan pid={proc.pid} survived the reap (leak confirmed)"
                )
                time.sleep(0.05)

        assert not _pid_alive(proc_a.pid), (
            f"orphan a (pid={proc_a.pid}) still alive after reap — #1071 leak not fixed"
        )
        assert not _pid_alive(proc_b.pid), (
            f"orphan b (pid={proc_b.pid}) still alive after reap — #1071 leak not fixed"
        )

        # Suppress harmless ResourceWarning from the harness shutdown for
        # already-terminated processes (their Popen objects are still tracked).
        with contextlib.suppress(Exception):
            pass  # harness.shutdown() in fixture teardown handles this
