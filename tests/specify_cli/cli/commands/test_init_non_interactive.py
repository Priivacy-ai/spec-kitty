from __future__ import annotations

import pytest

from specify_cli.cli.commands import init as init_module


def test_is_truthy_env():
    assert init_module._is_truthy_env("1") is True
    assert init_module._is_truthy_env("true") is True
    assert init_module._is_truthy_env("YES") is True
    assert init_module._is_truthy_env("on") is True
    assert init_module._is_truthy_env("y") is True
    assert init_module._is_truthy_env("0") is False
    assert init_module._is_truthy_env("false") is False
    assert init_module._is_truthy_env("") is False
    assert init_module._is_truthy_env(None) is False


def test_non_interactive_env_override(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SPEC_KITTY_NON_INTERACTIVE", "1")
    monkeypatch.setattr(init_module.sys.stdin, "isatty", lambda: True)
    assert init_module._is_non_interactive_mode(False) is True


def test_non_interactive_non_tty(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SPEC_KITTY_NON_INTERACTIVE", raising=False)
    monkeypatch.setattr(init_module.sys.stdin, "isatty", lambda: False)
    assert init_module._is_non_interactive_mode(False) is True


def test_resolve_preferred_agents_defaults_multi_agent():
    implementer, reviewer = init_module._resolve_preferred_agents(
        ["codex", "claude"],
        None,
        None,
    )
    assert implementer == "codex"
    assert reviewer == "claude"


def test_resolve_preferred_agents_defaults_single_agent():
    implementer, reviewer = init_module._resolve_preferred_agents(
        ["codex"],
        None,
        None,
    )
    assert implementer == "codex"
    assert reviewer == "codex"


def test_resolve_preferred_agents_invalid_preferred_agent():
    with pytest.raises(ValueError):
        init_module._resolve_preferred_agents(
            ["codex", "claude"],
            "gemini",
            None,
        )


def test_resolve_preferred_agents_invalid_reviewer_agent():
    with pytest.raises(ValueError):
        init_module._resolve_preferred_agents(
            ["codex", "claude"],
            "codex",
            "gemini",
        )
