"""Scope: mock-boundary tests for tracker command registration and gating — no real git."""

from __future__ import annotations

import pytest
import importlib

import typer
from typer.testing import CliRunner

pytestmark = pytest.mark.fast

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
    """Tracker sub-command absent from help when SAAS_SYNC flag is off."""
    # Arrange
    app = _build_root_app(enabled=False, monkeypatch=monkeypatch)

    # Assumption check
    # (no precondition)

    # Act
    result = runner.invoke(app, ["--help"])

    # Assert
    assert result.exit_code == 0
    assert "tracker" not in result.output


def test_tracker_registered_when_flag_enabled(monkeypatch) -> None:
    """Tracker sub-command appears in help when SAAS_SYNC flag is on."""
    # Arrange
    app = _build_root_app(enabled=True, monkeypatch=monkeypatch)

    # Assumption check
    # (no precondition)

    # Act
    result = runner.invoke(app, ["--help"])

    # Assert
    assert result.exit_code == 0
    assert "tracker" in result.output


def test_tracker_direct_invocation_fails_when_flag_disabled(monkeypatch) -> None:
    """Direct tracker invocation exits with code 1 and a flag-disabled message."""
    # Arrange
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)

    from specify_cli.cli.commands import tracker as tracker_module

    # Assumption check
    # (no precondition)

    # Act
    result = runner.invoke(tracker_module.app, ["providers"])

    # Assert
    assert result.exit_code == 1
    assert "SaaS sync is disabled by feature flag" in result.output
