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


def test_resolve_preferred_agents_defaults_multi_agent():
    """First agent is implementer, second is reviewer when no explicit choice."""
    # Arrange / Act
    implementer, reviewer = init_module._resolve_preferred_agents(
        ["codex", "claude"],
        None,
        None,
    )
    # Assert
    assert implementer == "codex"
    assert reviewer == "claude"


def test_resolve_preferred_agents_defaults_single_agent():
    """Single agent list makes that agent both implementer and reviewer."""
    # Arrange / Act
    implementer, reviewer = init_module._resolve_preferred_agents(
        ["codex"],
        None,
        None,
    )
    # Assert
    assert implementer == "codex"
    assert reviewer == "codex"


def test_resolve_preferred_agents_invalid_preferred_agent():
    """Agent not in selected list raises ValueError."""
    # Arrange
    agents = ["codex", "claude"]
    # Assumption check
    assert "gemini" not in agents
    # Act / Assert
    with pytest.raises(ValueError):
        init_module._resolve_preferred_agents(agents, "gemini", None)


def test_resolve_preferred_agents_invalid_reviewer_agent():
    """Reviewer not in selected list raises ValueError."""
    # Arrange
    agents = ["codex", "claude"]
    # Assumption check
    assert "gemini" not in agents
    # Act / Assert
    with pytest.raises(ValueError):
        init_module._resolve_preferred_agents(agents, "codex", "gemini")
