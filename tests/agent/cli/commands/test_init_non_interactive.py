"""Scope: init non interactive unit tests — no real git or subprocesses."""

from __future__ import annotations

import pytest

from specify_cli.cli.commands import init as init_module

pytestmark = pytest.mark.fast


def test_is_truthy_env():
    """Truthy strings return True; falsy/empty/None return False."""
    # Arrange
    truthy = ["1", "true", "YES", "on", "y"]
    falsy = ["0", "false", "", None]
    # Assumption check
    assert len(truthy) == 5
    # Act / Assert
    for val in truthy:
        assert init_module._is_truthy_env(val) is True
    for val in falsy:
        assert init_module._is_truthy_env(val) is False


def test_non_interactive_env_override(monkeypatch: pytest.MonkeyPatch):
    """Env var SPEC_KITTY_NON_INTERACTIVE=1 forces non-interactive mode."""
    # Arrange
    monkeypatch.setenv("SPEC_KITTY_NON_INTERACTIVE", "1")
    monkeypatch.setattr(init_module.sys.stdin, "isatty", lambda: True)
    # Assumption check
    assert init_module._is_truthy_env("1") is True
    # Act
    result = init_module._is_non_interactive_mode(False)
    # Assert
    assert result is True


def test_non_interactive_non_tty(monkeypatch: pytest.MonkeyPatch):
    """Non-TTY stdin forces non-interactive mode regardless of env var."""
    # Arrange
    monkeypatch.delenv("SPEC_KITTY_NON_INTERACTIVE", raising=False)
    monkeypatch.setattr(init_module.sys.stdin, "isatty", lambda: False)
    # Assumption check
    assert init_module._is_truthy_env(None) is False
    # Act
    result = init_module._is_non_interactive_mode(False)
    # Assert
    assert result is True


# _resolve_preferred_agents() was removed in feature 076-init-command-overhaul.
# The preferred-implementer / preferred-reviewer system was deleted entirely.
