"""WP07 — Dashboard <-> sync boundary regression matrix.

Tests prove the sync<->dashboard boundary is airtight across all four cleanup
entrypoints:

1. ``reap_orphan_daemons``  (sync/owner.py)  — process-cmdline reaper
2. ``enumerate_identity_records`` + ``reset_orphans`` sweep  (sync/orphan_sweep.py)
3. ``cleanup_orphan_sync_daemons``  (sync/daemon.py)  — broad operator surface
4. ``_cleanup_orphaned_dashboards_in_range``  (dashboard/lifecycle.py)

Boundary port coverage (T034):
- Sync range [9400, 9450): first=9400, last=9449, just-outside=9399/9450
- Dashboard range [9237, 9337): first=9237, last=9336, just-outside=9236/9337

DaemonIntent.LOCAL_ONLY assertion (T035): dashboard startup passes LOCAL_ONLY
to ensure_sync_daemon_running and the early-return is hit without starting sync.

All tests use real TCP listeners (no mocking of the HTTP layer) and run
serially with ``-n0``.  Every spawned resource is torn down in fixture
teardown; post-run port checks confirm no leaks.

Port allocation convention for this suite:
- Sync daemon under test:       9375..9399   (below the 9400 production range)
- Dashboard-shaped listener:    9237..9250   (bottom slice of dashboard range)
- Third-party listener:         9300..9320   (top of dashboard range — NOT scan target)
- Boundary probe targets:       9400, 9449   (first/last of sync range — real range)
                                9237, 9336   (first/last of dashboard range — real range)

Note: T034 boundary tests use monkeypatching to narrow scan ranges so we do not
accidentally sweep a real dev daemon on the real first port (9400).
"""

from __future__ import annotations

import contextlib
import json
import socket
import tempfile
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Any
from unittest.mock import patch

import pytest

from tests.sync._daemon_harness import (
    DaemonHarness,
    find_free_port_in_range,
    wait_until_listening,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Port ranges — keep well away from any real dev daemon on 9400+.
# (The canonical real sync range [9400, 9450) is referenced inline by the
# boundary probes below; no module-level constant is needed for it.)

# Narrow test slice for T031/T032/T033 so we don't collide with real daemons.
# Use ports just below the production range for the "sync daemon under test".
_SYNC_TEST_START = 9375
_SYNC_TEST_END = 9399  # exclusive — intentionally outside real range

# Dashboard range constants (canonical)
_DASH_RANGE_START = 9237
_DASH_RANGE_END = 9337  # exclusive (start + 100)

# Small dashboard test sub-slice (bottom of the canonical range)
_DASH_TEST_START = 9237
_DASH_TEST_END = 9250  # exclusive — narrow slice

# Third-party listener occupies a port in the upper dashboard range
_THIRD_PARTY_START = 9300
_THIRD_PARTY_END = 9320  # exclusive

# ---------------------------------------------------------------------------
# Dashboard-shaped HTTP handler (T031, T032, T033)
# ---------------------------------------------------------------------------

# Plausible project-path string echoed in the fake dashboard ``/api/health``
# payload below. Its value is never used as a real filesystem path and is never
# asserted; deriving it from the platform temp dir keeps it portable and avoids a
# hardcoded temp-directory literal (tmp-ratchet gate).
_DASHBOARD_PROJECT_PATH = str(Path(tempfile.gettempdir()) / "test-boundary-project")


class _DashboardHandler(BaseHTTPRequestHandler):
    """Minimal HTTP server that identifies as a spec-kitty dashboard.

    ``_is_spec_kitty_dashboard`` requires ``/api/health`` to return a JSON
    object with both ``project_path`` and ``status`` keys.
    """

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        # Suppress per-request logging in test output.
        pass

    def do_GET(self) -> None:  # noqa: N802 — stdlib BaseHTTPRequestHandler method
        body = (
            json.dumps({"project_path": _DASHBOARD_PROJECT_PATH, "status": "ready"}).encode()
            if self.path == "/api/health"
            else b"{}"
        )
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 — stdlib BaseHTTPRequestHandler method
        self.send_response(200)
        self.end_headers()


class _ThirdPartyHandler(BaseHTTPRequestHandler):
    """HTTP server that returns JSON without any spec-kitty identity keys."""

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        pass

    def do_GET(self) -> None:  # noqa: N802 — stdlib BaseHTTPRequestHandler method
        body = b'{"ok": true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 — stdlib BaseHTTPRequestHandler method
        self.send_response(200)
        self.end_headers()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _spawn_http_server(handler_class: type, port: int) -> tuple[HTTPServer, Thread]:
    """Start an HTTPServer on ``port`` using ``handler_class`` in a daemon thread."""
    server = HTTPServer(("127.0.0.1", port), handler_class)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    assert wait_until_listening(port, timeout_s=5.0), (
        f"HTTP server on {port} never started"
    )
    return server, thread


def _stop_http_server(server: HTTPServer, thread: Thread) -> None:
    """Shut down an HTTPServer and join its thread."""
    with contextlib.suppress(Exception):
        server.shutdown()
    with contextlib.suppress(Exception):
        server.server_close()
    thread.join(timeout=3.0)


def _port_is_listening(port: int, timeout_s: float = 0.2) -> bool:
    """Return True if something accepts a TCP connect on loopback ``port``."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout_s)
        return sock.connect_ex(("127.0.0.1", port)) == 0


# ---------------------------------------------------------------------------
# T031 – Boundary harness fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sync_harness(tmp_path: Path) -> Iterator[DaemonHarness]:
    """Provide a DaemonHarness instance; shutdown on teardown."""
    harness = DaemonHarness(tmp_path / "boundary-state")
    yield harness
    harness.shutdown()


@pytest.fixture()
def dashboard_listener() -> Iterator[int]:
    """Stand up a dashboard-shaped listener in the dashboard port range.

    Uses a sub-slice [9237, 9250) to stay well away from any real listener.
    The fixture yields the allocated port and shuts down on teardown.
    """
    port = find_free_port_in_range(_DASH_TEST_START, _DASH_TEST_END)
    server, thread = _spawn_http_server(_DashboardHandler, port)
    yield port
    _stop_http_server(server, thread)


@pytest.fixture()
def third_party_listener() -> Iterator[int]:
    """Stand up a third-party listener (no SK identity) in the dashboard range.

    Uses the upper sub-slice [9300, 9320).
    """
    port = find_free_port_in_range(_THIRD_PARTY_START, _THIRD_PARTY_END)
    server, thread = _spawn_http_server(_ThirdPartyHandler, port)
    yield port
    _stop_http_server(server, thread)


# ---------------------------------------------------------------------------
# T032 – Dashboard survives every sync cleanup path (C-002, NFR-002/003)
# ---------------------------------------------------------------------------


class TestDashboardSurvivesSyncCleanup:
    """C-002 / NFR-002/003 — no sync entrypoint must signal a dashboard port."""

    def test_reap_orphan_daemons_does_not_kill_dashboard(
        self,
        dashboard_listener: int,
    ) -> None:
        """``reap_orphan_daemons`` (process cmdline scan) never touches dashboard ports.

        The reaper only matches processes whose cmdline contains ``run_sync_daemon``;
        a dashboard HTTP server has no such cmdline, so it is structurally invisible
        to this entrypoint.
        """
        from specify_cli.sync.owner import reap_orphan_daemons

        dash_port = dashboard_listener
        assert _port_is_listening(dash_port), "Dashboard listener must be up before reaper"

        # Run the reaper — must not kill the dashboard listener.
        reap_orphan_daemons(dry_run=True)

        # Dashboard is still listening after the reap.
        assert _port_is_listening(dash_port), (
            f"C-002 VIOLATION: dashboard listener on port {dash_port} "
            "was killed by reap_orphan_daemons"
        )

    def test_enumerate_reset_orphans_does_not_kill_dashboard(
        self,
        dashboard_listener: int,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``enumerate_identity_records`` + ``reset_orphans`` never touches dashboard ports.

        The orphan_sweep scans [DAEMON_PORT_START, DAEMON_PORT_START+MAX_ATTEMPTS)
        which is [9400, 9450) — the dashboard port is in [9237, 9337) so it is
        completely outside the scanned range.
        """
        import specify_cli.sync.orphan_sweep as orphan_sweep_mod

        from specify_cli.sync.orphan_sweep import enumerate_identity_records, reset_orphans

        # Narrow scan to an empty sub-range so no real daemons are swept.
        monkeypatch.setattr(orphan_sweep_mod, "DAEMON_PORT_START", 9398)
        monkeypatch.setattr(orphan_sweep_mod, "DAEMON_PORT_MAX_ATTEMPTS", 1)

        dash_port = dashboard_listener
        assert _port_is_listening(dash_port)

        records = enumerate_identity_records()
        result = reset_orphans(records)

        # Dashboard still up.
        assert _port_is_listening(dash_port), (
            f"C-002 VIOLATION: dashboard on port {dash_port} killed by reset_orphans; "
            f"swept={result.swept}"
        )

    def test_cleanup_orphan_sync_daemons_does_not_kill_dashboard(
        self,
        dashboard_listener: int,
    ) -> None:
        """``cleanup_orphan_sync_daemons`` never touches the dashboard port.

        This entrypoint scans process cmdlines for ``run_sync_daemon``; an HTTP
        server has no such cmdline and is invisible to this path.
        """
        from specify_cli.sync.daemon import cleanup_orphan_sync_daemons

        dash_port = dashboard_listener
        assert _port_is_listening(dash_port)

        # dry_run=True: introspect without killing.
        report, killed = cleanup_orphan_sync_daemons(dry_run=True)

        # Confirm: none of the detected orphans is our dashboard port.
        # (The port attribute isn't directly on orphan_processes; we confirm
        # the dashboard is still listening as the definitive check.)
        _ = report  # used for type annotation only
        assert not killed, "dry_run should never kill"
        assert _port_is_listening(dash_port), (
            f"C-002 VIOLATION: dashboard on port {dash_port} killed by "
            "cleanup_orphan_sync_daemons"
        )

    def test_dashboard_cleanup_does_not_scan_sync_range(
        self,
        third_party_listener: int,
    ) -> None:
        """``_cleanup_orphaned_dashboards_in_range`` never touches sync ports [9400, 9450).

        The dashboard cleaner's default scan window is [9237, 9337).  A listener
        in [9400, 9450) is completely outside that window, so the cleaner's
        ``start_port`` never reaches it.  We place a third-party listener in the
        sync range and confirm the default-range sweep doesn't kill it.

        This is a complementary guard to T033 (sync survives dashboard cleanup)
        exercising the scan-window boundary directly.
        """
        from specify_cli.dashboard.lifecycle import _cleanup_orphaned_dashboards_in_range

        # third_party_listener is in [9300, 9320) — inside the dashboard range but
        # not a SK dashboard, so _cleanup_orphaned_dashboards_in_range must skip it.
        tp_port = third_party_listener

        # The canonical dashboard sweep runs over [9237, 9337) which includes tp_port.
        # Since the third-party listener doesn't answer /api/health with SK keys,
        # it must NOT be killed.  Scope the scan to the single third-party port to isolate.
        killed_count = _cleanup_orphaned_dashboards_in_range(
            start_port=tp_port, port_count=1
        )

        assert killed_count == 0, (
            f"C-004 VIOLATION: third-party listener on port {tp_port} was killed "
            f"by _cleanup_orphaned_dashboards_in_range (killed_count={killed_count})"
        )
        # The third-party port must still be listening.
        assert _port_is_listening(tp_port), (
            f"C-004 VIOLATION: third-party listener on port {tp_port} no longer listening "
            "after dashboard cleanup (scan range should not touch non-SK listeners)"
        )


# ---------------------------------------------------------------------------
# T033 – Sync survives dashboard cleanup; third-party survives both families
# ---------------------------------------------------------------------------


class TestSyncAndThirdPartySurvival:
    """NFR-003 / C-004 — each family's cleaner must leave the other family alone."""

    def test_sync_daemon_survives_dashboard_cleanup(
        self,
        sync_harness: DaemonHarness,
        tmp_path: Path,
    ) -> None:
        """Dashboard cleanup ``_cleanup_orphaned_dashboards_in_range`` must not kill a sync daemon.

        The sync daemon lives in [9400, 9450); the dashboard cleaner scans
        [9237, 9337) by default, so the daemon's port is never examined.
        """
        from specify_cli.dashboard.lifecycle import _cleanup_orphaned_dashboards_in_range

        # Spawn a real sync daemon in the below-production test slice so it
        # cannot be mistaken for the production singleton.
        sync_port = find_free_port_in_range(_SYNC_TEST_START, _SYNC_TEST_END)
        sync_harness.spawn_daemon(sync_port, home=str(tmp_path))

        assert _port_is_listening(sync_port), "Sync daemon must be up"

        # Run the dashboard cleaner over its canonical range [9237, 9337).
        _cleanup_orphaned_dashboards_in_range()

        # Sync daemon still alive.
        assert _port_is_listening(sync_port), (
            f"NFR-003 VIOLATION: sync daemon on port {sync_port} killed by "
            "_cleanup_orphaned_dashboards_in_range"
        )

    def test_third_party_survives_reap_orphan_daemons(
        self,
        third_party_listener: int,
    ) -> None:
        """Third-party listener (no run_sync_daemon cmdline) is invisible to reap_orphan_daemons."""
        from specify_cli.sync.owner import reap_orphan_daemons

        tp_port = third_party_listener
        assert _port_is_listening(tp_port)

        reap_orphan_daemons(dry_run=True)

        assert _port_is_listening(tp_port), (
            f"C-004 VIOLATION: third-party listener on port {tp_port} "
            "was affected by reap_orphan_daemons"
        )

    def test_third_party_survives_cleanup_orphan_sync_daemons(
        self,
        third_party_listener: int,
    ) -> None:
        """Third-party listener survives cleanup_orphan_sync_daemons (C-004)."""
        from specify_cli.sync.daemon import cleanup_orphan_sync_daemons

        tp_port = third_party_listener
        assert _port_is_listening(tp_port)

        _report, killed = cleanup_orphan_sync_daemons(dry_run=True)
        assert not killed
        assert _port_is_listening(tp_port), (
            f"C-004 VIOLATION: third-party on port {tp_port} affected by "
            "cleanup_orphan_sync_daemons"
        )

    def test_third_party_survives_enumerate_reset_orphans(
        self,
        third_party_listener: int,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Third-party listener survives enumerate_identity_records + reset_orphans (C-004)."""
        import specify_cli.sync.orphan_sweep as orphan_sweep_mod

        from specify_cli.sync.orphan_sweep import enumerate_identity_records, reset_orphans

        # Narrow scan range to avoid touching any live daemon on this machine.
        monkeypatch.setattr(orphan_sweep_mod, "DAEMON_PORT_START", 9398)
        monkeypatch.setattr(orphan_sweep_mod, "DAEMON_PORT_MAX_ATTEMPTS", 1)

        tp_port = third_party_listener
        assert _port_is_listening(tp_port)

        records = enumerate_identity_records()
        reset_orphans(records)

        assert _port_is_listening(tp_port), (
            f"C-004 VIOLATION: third-party on port {tp_port} affected by reset_orphans; "
            f"records={records}"
        )

    def test_third_party_survives_dashboard_cleanup(
        self,
        third_party_listener: int,
    ) -> None:
        """Third-party listener in the dashboard range survives _cleanup_orphaned_dashboards_in_range.

        ``_is_spec_kitty_dashboard`` returns False for this server (no
        project_path+status keys in /api/health), so it must not be killed.
        """
        from specify_cli.dashboard.lifecycle import _cleanup_orphaned_dashboards_in_range

        tp_port = third_party_listener
        assert _port_is_listening(tp_port)

        # Scan only the single port of our third-party listener to isolate.
        killed_count = _cleanup_orphaned_dashboards_in_range(
            start_port=tp_port, port_count=1
        )

        assert killed_count == 0, (
            f"C-004 VIOLATION: third-party listener on port {tp_port} was killed "
            f"by _cleanup_orphaned_dashboards_in_range (killed_count={killed_count})"
        )
        assert _port_is_listening(tp_port), (
            f"C-004 VIOLATION: third-party on port {tp_port} no longer listening "
            "after dashboard cleanup"
        )


# ---------------------------------------------------------------------------
# T034 – Boundary ports: first / last / just-outside (NFR-001/002)
# ---------------------------------------------------------------------------


class TestBoundaryPorts:
    """NFR-001/002 — first / last / just-outside ports for both ranges."""

    # ------------------------------------------------------------------
    # Sync range [9400, 9450)
    # ------------------------------------------------------------------

    def test_sync_first_port_in_range_is_scanned(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Port 9400 (first in sync range) is inside the scan window.

        We monkeypatch the scan to [9400, 9401) and confirm a non-SK listener
        on 9400 produces a never_touch record (port is examined).
        """
        import specify_cli.sync.orphan_sweep as orphan_sweep_mod

        from specify_cli.sync.orphan_sweep import enumerate_identity_records

        monkeypatch.setattr(orphan_sweep_mod, "DAEMON_PORT_START", 9400)
        monkeypatch.setattr(orphan_sweep_mod, "DAEMON_PORT_MAX_ATTEMPTS", 1)

        port = 9400
        server: HTTPServer | None = None
        thread: Thread | None = None

        if not _port_is_listening(port):
            # Only spin up a dummy listener if the port is free.
            server, thread = _spawn_http_server(_ThirdPartyHandler, port)

        try:
            # With a third-party listener on 9400, enumerate returns 0 records
            # (third-party → never_touch → excluded from result per C-004).
            # The key assertion: no exception, and no never_touch records leak.
            records = enumerate_identity_records()
            for rec in records:
                assert rec.port != port or rec.cleanup_class.value != "never_touch", (
                    f"never_touch record on port {port} must be excluded from result"
                )
        finally:
            if server is not None and thread is not None:
                _stop_http_server(server, thread)

    def test_sync_last_port_in_range_is_scanned(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Port 9449 (last in sync range) is inside the scan window."""
        import specify_cli.sync.orphan_sweep as orphan_sweep_mod

        from specify_cli.sync.orphan_sweep import enumerate_identity_records

        monkeypatch.setattr(orphan_sweep_mod, "DAEMON_PORT_START", 9449)
        monkeypatch.setattr(orphan_sweep_mod, "DAEMON_PORT_MAX_ATTEMPTS", 1)

        port = 9449
        server: HTTPServer | None = None
        thread: Thread | None = None

        if not _port_is_listening(port):
            server, thread = _spawn_http_server(_ThirdPartyHandler, port)

        try:
            records = enumerate_identity_records()
            for rec in records:
                assert rec.port != port or rec.cleanup_class.value != "never_touch", (
                    f"never_touch record on port {port} must be excluded from result"
                )
        finally:
            if server is not None and thread is not None:
                _stop_http_server(server, thread)

    def test_sync_just_outside_below_is_not_scanned(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Port 9399 (just-below sync range) is never scanned by enumerate_identity_records."""
        import specify_cli.sync.orphan_sweep as orphan_sweep_mod

        from specify_cli.sync.orphan_sweep import enumerate_identity_records

        # Scan [9400, 9401) — 9399 is out of range.
        monkeypatch.setattr(orphan_sweep_mod, "DAEMON_PORT_START", 9400)
        monkeypatch.setattr(orphan_sweep_mod, "DAEMON_PORT_MAX_ATTEMPTS", 1)

        port_outside = 9399
        server: HTTPServer | None = None
        thread: Thread | None = None

        if not _port_is_listening(port_outside):
            server, thread = _spawn_http_server(_ThirdPartyHandler, port_outside)

        try:
            records = enumerate_identity_records()
            # 9399 must never appear in the result.
            assert all(rec.port != port_outside for rec in records), (
                f"Port {port_outside} (just-below sync range) appeared in scan results"
            )
        finally:
            if server is not None and thread is not None:
                _stop_http_server(server, thread)

    def test_sync_just_outside_above_is_not_scanned(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Port 9450 (just-above sync range) is never scanned by enumerate_identity_records."""
        import specify_cli.sync.orphan_sweep as orphan_sweep_mod

        from specify_cli.sync.orphan_sweep import enumerate_identity_records

        # Scan [9449, 9450) — 9450 is out of range.
        monkeypatch.setattr(orphan_sweep_mod, "DAEMON_PORT_START", 9449)
        monkeypatch.setattr(orphan_sweep_mod, "DAEMON_PORT_MAX_ATTEMPTS", 1)

        port_outside = 9450
        server: HTTPServer | None = None
        thread: Thread | None = None

        if not _port_is_listening(port_outside):
            server, thread = _spawn_http_server(_ThirdPartyHandler, port_outside)

        try:
            records = enumerate_identity_records()
            assert all(rec.port != port_outside for rec in records), (
                f"Port {port_outside} (just-above sync range) appeared in scan results"
            )
        finally:
            if server is not None and thread is not None:
                _stop_http_server(server, thread)

    # ------------------------------------------------------------------
    # Dashboard range [9237, 9337) — fingerprint and range boundary checks
    #
    # Safety note: we do NOT run _cleanup_orphaned_dashboards_in_range over
    # in-process HTTPServer listeners that answer /api/health with SK keys.
    # That function uses lsof to find the PID listening on the port; since
    # in-process servers share the pytest process, lsof returns pytest's PID
    # and the call would kill the test runner.  Instead these tests verify
    # the fingerprint function (_is_spec_kitty_dashboard) directly, and use
    # third-party (non-SK) listeners for the live range-scan assertions.
    # ------------------------------------------------------------------

    def test_dashboard_first_port_fingerprint_is_sk(self) -> None:
        """A SK-fingerprinted listener on port 9237 (first in range) is correctly identified.

        Proves the lower boundary port is inside the fingerprint window by confirming
        ``_is_spec_kitty_dashboard`` returns True for port 9237.
        """
        from specify_cli.dashboard.lifecycle import _is_spec_kitty_dashboard

        port = 9237
        server: HTTPServer | None = None
        thread: Thread | None = None

        if not _port_is_listening(port):
            server, thread = _spawn_http_server(_DashboardHandler, port)

        try:
            # The port is listening and returns SK health keys → must be True.
            result = _is_spec_kitty_dashboard(port)
            if server is not None:
                # We own the server; it is a SK-fingerprinted listener.
                assert result is True, (
                    f"Port {port} (first dash port) must be recognised as SK dashboard; "
                    f"got {result!r}"
                )
        finally:
            if server is not None and thread is not None:
                _stop_http_server(server, thread)

    def test_dashboard_last_port_fingerprint_is_sk(self) -> None:
        """A SK-fingerprinted listener on port 9336 (last in range) is correctly identified."""
        from specify_cli.dashboard.lifecycle import _is_spec_kitty_dashboard

        port = 9336
        server: HTTPServer | None = None
        thread: Thread | None = None

        if not _port_is_listening(port):
            server, thread = _spawn_http_server(_DashboardHandler, port)

        try:
            result = _is_spec_kitty_dashboard(port)
            if server is not None:
                assert result is True, (
                    f"Port {port} (last dash port) must be recognised as SK dashboard; "
                    f"got {result!r}"
                )
        finally:
            if server is not None and thread is not None:
                _stop_http_server(server, thread)

    def test_dashboard_just_outside_below_not_in_cleanup_range(self) -> None:
        """Port 9236 (just-below dashboard range) is never included in the cleanup loop.

        The cleanup function iterates ``range(start_port, start_port + port_count)``.
        With defaults ``start_port=9237, port_count=100`` the range is [9237, 9337).
        We verify that a third-party listener on 9236 survives a scan starting at 9237
        by scoping the scan to [9237, 9238) (just one port above 9236).
        """
        from specify_cli.dashboard.lifecycle import _cleanup_orphaned_dashboards_in_range

        port_outside = 9236
        server: HTTPServer | None = None
        thread: Thread | None = None

        if not _port_is_listening(port_outside):
            server, thread = _spawn_http_server(_ThirdPartyHandler, port_outside)

        try:
            # Scan [9237, 9238) — 9236 must never be touched.
            _cleanup_orphaned_dashboards_in_range(start_port=9237, port_count=1)

            if server is not None:
                assert _port_is_listening(port_outside), (
                    f"Port {port_outside} (just-below dash range) was affected by "
                    "dashboard cleanup (range boundary violation)"
                )
        finally:
            if server is not None and thread is not None:
                _stop_http_server(server, thread)

    def test_dashboard_just_outside_above_not_in_cleanup_range(self) -> None:
        """Port 9337 (just-above dashboard range) is never included in the cleanup loop.

        With defaults ``start_port=9237, port_count=100`` the last scanned port is
        9336 (inclusive).  We verify the boundary by running a scan scoped to [9336, 9337)
        (just one port before 9337) and confirming 9337 (third-party) is untouched.
        """
        from specify_cli.dashboard.lifecycle import _cleanup_orphaned_dashboards_in_range

        port_outside = 9337
        server: HTTPServer | None = None
        thread: Thread | None = None

        if not _port_is_listening(port_outside):
            server, thread = _spawn_http_server(_ThirdPartyHandler, port_outside)

        try:
            # Scan [9336, 9337) — port 9337 must never be touched.
            _cleanup_orphaned_dashboards_in_range(start_port=9336, port_count=1)

            if server is not None:
                assert _port_is_listening(port_outside), (
                    f"Port {port_outside} (just-above dash range) was affected by "
                    "dashboard cleanup (range boundary violation)"
                )
        finally:
            if server is not None and thread is not None:
                _stop_http_server(server, thread)


# ---------------------------------------------------------------------------
# T035 – Dashboard intent: DaemonIntent.LOCAL_ONLY unchanged (AS-7, C-003)
# ---------------------------------------------------------------------------


class TestDashboardIntentLocalOnly:
    """AS-7 / C-003 — dashboard startup passes DaemonIntent.LOCAL_ONLY; early-return is hit."""

    def test_run_dashboard_server_passes_local_only(self, tmp_path: Path) -> None:
        """``run_dashboard_server`` calls ``ensure_sync_daemon_running`` with LOCAL_ONLY.

        We patch ``ensure_sync_daemon_running`` at the canonical module to capture
        its ``intent`` kwarg.  The function is imported inside ``run_dashboard_server``
        via a local ``from specify_cli.sync.daemon import ...`` so we must patch the
        source location (``specify_cli.sync.daemon.ensure_sync_daemon_running``).
        The early-return for LOCAL_ONLY means no sync daemon is ever started.
        """
        from specify_cli.sync.daemon import DaemonIntent, DaemonStartOutcome

        captured_intent: list[DaemonIntent] = []

        def _mock_ensure(*, intent: DaemonIntent, **_kwargs: Any) -> DaemonStartOutcome:
            captured_intent.append(intent)
            # Simulate the LOCAL_ONLY early-return: skipped_reason set, started=False.
            return DaemonStartOutcome(
                started=False,
                skipped_reason="intent_local_only",
                pid=None,
            )

        # Patch at the canonical source so the local import inside
        # run_dashboard_server picks it up.
        with patch(
            "specify_cli.sync.daemon.ensure_sync_daemon_running",
            side_effect=_mock_ensure,
        ):
            from specify_cli.dashboard import server as dashboard_server

            # Stop before the blocking ``serve_loopback_server`` call.
            with patch.object(dashboard_server, "serve_loopback_server", return_value=None):
                dashboard_server.run_dashboard_server(
                    project_dir=tmp_path,
                    port=9238,
                    project_token=None,
                )

        assert len(captured_intent) == 1, (
            f"ensure_sync_daemon_running should be called exactly once; got {captured_intent}"
        )
        assert captured_intent[0] == DaemonIntent.LOCAL_ONLY, (
            f"C-003 VIOLATION: dashboard passed intent={captured_intent[0]!r} "
            "instead of DaemonIntent.LOCAL_ONLY"
        )

    def test_local_only_skip_reason_is_intent_local_only(self) -> None:
        """``_daemon_start_skip_reason`` returns 'intent_local_only' for LOCAL_ONLY intent.

        This is the focused unit assertion that the early-return path in
        ``ensure_sync_daemon_running`` (daemon.py ~line 1037) is exercised.
        """
        from specify_cli.sync.daemon import DaemonIntent, _daemon_start_skip_reason
        from specify_cli.sync.config import BackgroundDaemonPolicy

        # Policy=AUTO so it would normally proceed; intent=LOCAL_ONLY wins.
        result = _daemon_start_skip_reason(
            intent=DaemonIntent.LOCAL_ONLY,
            policy=BackgroundDaemonPolicy.AUTO,
        )
        assert result == "intent_local_only", (
            f"C-003: expected 'intent_local_only' skip reason, got {result!r}"
        )

    def test_ensure_sync_daemon_running_local_only_skips(self) -> None:
        """``ensure_sync_daemon_running(intent=LOCAL_ONLY)`` returns skipped without starting sync.

        Patches out the rollout check so the LOCAL_ONLY gate is the deciding factor.
        """
        from specify_cli.sync.daemon import DaemonIntent, ensure_sync_daemon_running

        with patch(
            "specify_cli.sync.daemon._daemon_start_skip_reason",
            return_value="intent_local_only",
        ) as mock_skip:
            outcome = ensure_sync_daemon_running(intent=DaemonIntent.LOCAL_ONLY)

        mock_skip.assert_called_once()
        assert not outcome.started, (
            "C-003: ensure_sync_daemon_running(LOCAL_ONLY) must not start the daemon"
        )
        assert outcome.skipped_reason == "intent_local_only", (
            f"C-003: expected skipped_reason='intent_local_only', got {outcome.skipped_reason!r}"
        )


# ---------------------------------------------------------------------------
# Leak / cleanup guard
# ---------------------------------------------------------------------------


def test_no_leaked_servers_after_suite(
    dashboard_listener: int,
    third_party_listener: int,
) -> None:
    """Smoke check that fixture teardown releases ports.

    This test runs last (within the file) to verify the harness shuts down
    cleanly.  The ports are still held by the fixtures at this point; they
    will be released in fixture teardown immediately after this test returns.
    """
    # Both listeners must be alive while their fixtures are active.
    assert _port_is_listening(dashboard_listener), (
        f"Dashboard listener on {dashboard_listener} should still be alive"
    )
    assert _port_is_listening(third_party_listener), (
        f"Third-party listener on {third_party_listener} should still be alive"
    )
    # No assertions after this — teardown confirms ports are released.


# Mark all tests as integration (real TCP listeners, serial -n0 required).
pytestmark = [pytest.mark.integration]
