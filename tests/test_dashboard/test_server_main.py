"""Argument contract for the detached dashboard child's ``python -m`` entry point.

The parent (`dashboard.server._spawn_dashboard_process`) builds the child's
argv; these tests pin that `_server_main._main` parses exactly that shape —
and refuses everything else with the usage line instead of starting a server
on garbage arguments (#4125).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.dashboard import _server_main

pytestmark = [pytest.mark.unit]


def test_main_rejects_wrong_argument_counts(capsys: pytest.CaptureFixture[str]) -> None:
    assert _server_main._main([]) == 2
    assert _server_main._main(["/proj"]) == 2
    assert _server_main._main(["/proj", "8080", "tok", "stray"]) == 2
    stderr = capsys.readouterr().err
    assert "usage: python -m specify_cli.dashboard._server_main" in stderr


def test_main_rejects_non_numeric_port(capsys: pytest.CaptureFixture[str]) -> None:
    assert _server_main._main(["/proj", "not-a-port"]) == 2
    assert "usage" in capsys.readouterr().err


def test_main_rejects_malformed_port_fd(capsys: pytest.CaptureFixture[str]) -> None:
    # A --port-fd without a value, and one whose value is not an integer.
    assert _server_main._main(["/proj", "8080", "--port-fd"]) == 2
    assert _server_main._main(["/proj", "8080", "tok", "--port-fd", "x"]) == 2
    assert "usage" in capsys.readouterr().err


def test_main_delegates_to_run_dashboard_server(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: dict[tuple[object, ...], None] = {}

    def fake_run(*args: object) -> None:
        calls[args] = None

    monkeypatch.setattr(_server_main, "run_dashboard_server", fake_run)

    assert _server_main._main([str(tmp_path), "9237", "tok", "--port-fd", "7"]) == 0
    assert list(calls) == [(tmp_path, 9237, "tok", 7)]


def test_main_defaults_optional_arguments_to_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: dict[tuple[object, ...], None] = {}

    def fake_run(*args: object) -> None:
        calls[args] = None

    monkeypatch.setattr(_server_main, "run_dashboard_server", fake_run)

    assert _server_main._main([str(tmp_path), "9237"]) == 0
    assert list(calls) == [(tmp_path, 9237, None, None)]
