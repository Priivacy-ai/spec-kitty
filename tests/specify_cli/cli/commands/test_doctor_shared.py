"""Behavioral safety checks for the shared doctor infrastructure."""

from __future__ import annotations

import logging
import sys

import pytest

from specify_cli.cli.commands import _doctor_shared

pytestmark = [pytest.mark.fast]


def _clear_interactivity_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPEC_KITTY_FORCE_INTERACTIVE", raising=False)
    monkeypatch.delenv("SPEC_KITTY_NON_INTERACTIVE", raising=False)
    for name in _doctor_shared._CI_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_interactivity_precedence_never_prompts_ci(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TTY and explicit overrides work, but a CI signal always vetoes prompts."""
    _clear_interactivity_env(monkeypatch)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    assert _doctor_shared._is_interactive_environment() is True

    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    assert _doctor_shared._is_interactive_environment() is False

    monkeypatch.setenv("SPEC_KITTY_FORCE_INTERACTIVE", "1")
    assert _doctor_shared._is_interactive_environment() is True

    monkeypatch.delenv("SPEC_KITTY_FORCE_INTERACTIVE")
    monkeypatch.setenv("SPEC_KITTY_NON_INTERACTIVE", "1")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    assert _doctor_shared._is_interactive_environment() is False

    monkeypatch.delenv("SPEC_KITTY_NON_INTERACTIVE")
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("SPEC_KITTY_FORCE_INTERACTIVE", "1")
    assert _doctor_shared._is_interactive_environment() is False


def test_json_output_guard_restores_logging_on_every_exit() -> None:
    """The live guard suppresses logging only while JSON output is active."""
    previous = logging.root.manager.disable

    with _doctor_shared._json_output_guard(False):
        assert logging.root.manager.disable == previous

    with _doctor_shared._json_output_guard(True):
        assert logging.root.manager.disable == logging.CRITICAL
    assert logging.root.manager.disable == previous

    with pytest.raises(RuntimeError), _doctor_shared._json_output_guard(True):
        raise RuntimeError("controlled failure")
    assert logging.root.manager.disable == previous
