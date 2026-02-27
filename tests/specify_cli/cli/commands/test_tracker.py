"""Tests for tracker command registration and gating."""

from __future__ import annotations

import importlib

import typer
from typer.testing import CliRunner

runner = CliRunner()


def _build_root_app(*, enabled: bool, monkeypatch) -> typer.Typer:
    if enabled:
        monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    else:
        monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)

    import specify_cli.cli.commands as commands_module

    commands_module = importlib.reload(commands_module)
    app = typer.Typer()
    commands_module.register_commands(app)
    return app


def test_tracker_not_registered_when_flag_disabled(monkeypatch) -> None:
    app = _build_root_app(enabled=False, monkeypatch=monkeypatch)

    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "tracker" not in result.output


def test_tracker_registered_when_flag_enabled(monkeypatch) -> None:
    app = _build_root_app(enabled=True, monkeypatch=monkeypatch)

    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "tracker" in result.output


def test_tracker_direct_invocation_fails_when_flag_disabled(monkeypatch) -> None:
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)

    from specify_cli.cli.commands import tracker as tracker_module

    result = runner.invoke(tracker_module.app, ["providers"])

    assert result.exit_code == 1
    assert "SaaS sync is disabled by feature flag" in result.output
