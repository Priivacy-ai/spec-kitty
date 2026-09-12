"""Tests for the dashboard background-process module entry point (#4125).

``specify_cli.dashboard._server_main`` replaces the former ``python -c
"<codegen>"`` launch: run as ``python -m specify_cli.dashboard._server_main``
so the child gets a real ``__main__.__file__`` (a ``-c`` child has none, and a
transitive import that reads it crashed with ``AttributeError`` on Windows).
"""

from __future__ import annotations

import socket

import pytest

from specify_cli.dashboard import _server_main

pytestmark = [pytest.mark.integration]


def test_main_parses_required_args_and_calls_run_dashboard_server(monkeypatch, tmp_path):
    calls = {}

    def fake_run_dashboard_server(project_dir, port, project_token, port_report_path=None):
        calls["project_dir"] = project_dir
        calls["port"] = port
        calls["project_token"] = project_token
        calls["port_report_path"] = port_report_path

    monkeypatch.setattr(
        "specify_cli.dashboard.server.run_dashboard_server",
        fake_run_dashboard_server,
    )

    exit_code = _server_main._main(
        [
            "--project-dir",
            str(tmp_path),
            "--port",
            "12401",
            "--token",
            "sekret",
        ]
    )

    assert exit_code == 0
    assert calls["project_dir"] == tmp_path
    assert calls["port"] == 12401
    assert calls["project_token"] == "sekret"
    assert calls["port_report_path"] is None


def test_main_wires_port_report_file_when_given(monkeypatch, tmp_path):
    calls = {}

    def fake_run_dashboard_server(project_dir, port, project_token, port_report_path=None):
        calls["port_report_path"] = port_report_path

    monkeypatch.setattr(
        "specify_cli.dashboard.server.run_dashboard_server",
        fake_run_dashboard_server,
    )

    report_path = tmp_path / "port-report.txt"
    _server_main._main(
        [
            "--project-dir",
            str(tmp_path),
            "--port",
            "0",
            "--port-report-file",
            str(report_path),
        ]
    )

    assert calls["port_report_path"] == report_path


def test_main_requires_project_dir_and_port():
    with pytest.raises(SystemExit):
        _server_main._main([])


def test_module_entry_point_real_subprocess_serves_over_loopback(tmp_path):
    """End-to-end: `python -m specify_cli.dashboard._server_main` actually runs.

    This is the exact invocation `start_dashboard` launches; running it for
    real (not mocked) is what would have caught the `-c` `__main__.__file__`
    crash class in the first place.
    """
    import subprocess
    import sys
    import time

    from specify_cli.dashboard.server import find_free_port

    port = find_free_port(start_port=15200, max_attempts=100)
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "specify_cli.dashboard._server_main",
            "--project-dir",
            str(tmp_path),
            "--port",
            str(port),
        ],
    )
    try:
        deadline = time.monotonic() + 10.0
        reachable = False
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                pytest.fail(f"module entry point exited early with status {proc.poll()}")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    reachable = True
                    break
            except OSError:
                time.sleep(0.05)
        assert reachable, "dashboard did not become reachable via `python -m ..._server_main`"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
