"""End-to-end regression: the detached dashboard spawn must actually serve.

#4125: ``spec-kitty dashboard`` on Windows spawned its server via
``python -c "<script>"``; the child died on import (a Windows-platform
transitive import reads ``__main__.__file__``, which ``-c`` does not provide)
with stdout/stderr sent to DEVNULL, so the CLI printed success for a dashboard
that silently wasn't there. The spawn now goes through ``python -m
specify_cli.dashboard._server_main`` with output piped to a log file and a
readiness probe before ``start_dashboard`` returns.

These tests spawn the real child process and assert the port actually accepts
a connection and serves the project's health payload — the exact guarantee
the previous suite never exercised, which is how the break shipped. The spawn
machinery is platform-independent, so the baseline test runs everywhere;
the Windows-critical twin carries ``windows_ci`` so the native Windows lane
(the only place the original crash reproduced) exercises it too.
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import psutil
import pytest

from specify_cli.dashboard import server

_READINESS_BUDGET_SECONDS = 15.0
_POLL_INTERVAL_SECONDS = 0.1


def _spawn_and_assert_serving(tmp_path: Path, *, port: int) -> None:
    (tmp_path / ".kittify").mkdir(exist_ok=True)
    port, pid = server.start_dashboard(
        tmp_path,
        port=port,
        background_process=True,
        project_token="regression-token",
    )
    try:
        deadline = time.monotonic() + _READINESS_BUDGET_SECONDS
        while time.monotonic() < deadline:
            if server._port_serves_our_dashboard(port, tmp_path.resolve(), "regression-token"):
                break
            time.sleep(_POLL_INTERVAL_SECONDS)
        else:
            pytest.fail(f"dashboard child (pid {pid}) never served this project's health payload on port {port}")

        # Belt-and-braces: not just any listener answering the identity probe —
        # the real dashboard, serving this project's health payload with the
        # token the parent handed the child.
        with urllib.request.urlopen(  # nosec B310 — loopback URL built from the OS-assigned port above
            f"http://127.0.0.1:{port}/api/health", timeout=2
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["project_path"] == str(tmp_path.resolve())
        assert payload["token"] == "regression-token"
    finally:
        _terminate_child(pid)


def _terminate_child(pid: int) -> None:
    try:
        child = psutil.Process(pid)
        child.terminate()
        try:
            child.wait(timeout=5)
        except psutil.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)
    except psutil.NoSuchProcess:
        pass


@pytest.mark.integration
@pytest.mark.regression
@pytest.mark.non_sandbox
def test_background_dashboard_spawn_binds_and_serves(tmp_path: Path) -> None:
    # port=0 exercises the OS-assigned-port reporting pipe (pass_fds fd
    # inheritance) — POSIX-only machinery, so this baseline stays off the
    # windows_ci lane.
    _spawn_and_assert_serving(tmp_path, port=0)


@pytest.mark.windows_ci
@pytest.mark.non_sandbox
def test_background_dashboard_spawn_binds_and_serves_windows_critical(tmp_path: Path) -> None:
    """Windows-critical twin of the spawn regression (#4125).

    Auto-skipped on non-Windows runs (the ``windows_ci`` chokepoint in
    ``tests/conftest.py``); the native Windows CI lane selects it via
    ``-m windows_ci``.

    The twin spawns on a concrete free port, not ``port=0``: the port=0 path
    hands the child a reporting pipe via ``subprocess.Popen(pass_fds=...)``,
    and CPython's Windows implementation rejects any non-empty ``pass_fds``
    outright (``assert not pass_fds``) — fd inheritance is POSIX-only. A
    concrete port needs no pipe, so the ``python -m`` spawn — the actual
    #4125 fix — is still exercised end-to-end on Windows, through the same
    concrete-port path production takes there.
    """
    _spawn_and_assert_serving(tmp_path, port=server.find_free_port())
