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


def test_resolve_non_interactive_defaults_multi_agent():
    strategy, implementer, reviewer = init_module._resolve_non_interactive_strategy(
        ["codex", "claude"],
        None,
        None,
        None,
    )
    assert strategy == "preferred"
    assert implementer == "codex"
    assert reviewer == "claude"


def test_resolve_non_interactive_defaults_single_agent():
    strategy, implementer, reviewer = init_module._resolve_non_interactive_strategy(
        ["codex"],
        None,
        None,
        None,
    )
    assert strategy == "preferred"
    assert implementer == "codex"
    assert reviewer == "codex"


def test_resolve_non_interactive_random_rejects_preferred():
    with pytest.raises(ValueError):
        init_module._resolve_non_interactive_strategy(
            ["codex", "claude"],
            "random",
            "codex",
            None,
        )


def test_resolve_non_interactive_invalid_preferred_agent():
    with pytest.raises(ValueError):
        init_module._resolve_non_interactive_strategy(
            ["codex", "claude"],
            "preferred",
            "gemini",
            None,
        )
