"""Unit coverage for the canonical non-interactive contract (#2876).

``specify_cli.core.env.is_interactive`` is the single authority every prompting
surface must consult. The #2876 defect was a prompt loop that consulted nothing.
"""

from __future__ import annotations

import io
import sys

import pytest

from specify_cli.core.env import is_interactive

pytestmark = [pytest.mark.unit]


class _FakeStdin(io.StringIO):
    def __init__(self, tty: bool) -> None:
        super().__init__("")
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


def test_non_interactive_env_wins_over_a_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", _FakeStdin(tty=True))
    monkeypatch.setenv("SPEC_KITTY_NON_INTERACTIVE", "1")
    monkeypatch.delenv("SPEC_KITTY_FORCE_INTERACTIVE", raising=False)
    assert is_interactive() is False


def test_force_interactive_outranks_non_interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", _FakeStdin(tty=False))
    monkeypatch.setenv("SPEC_KITTY_NON_INTERACTIVE", "1")
    monkeypatch.setenv("SPEC_KITTY_FORCE_INTERACTIVE", "1")
    assert is_interactive() is True


@pytest.mark.parametrize("token", ["1", "true", "TRUE", "yes", "y", "on"])
def test_truthy_grammar_is_honored_not_just_literal_one(monkeypatch: pytest.MonkeyPatch, token: str) -> None:
    """The predicate uses the canonical truthy grammar, so NON_INTERACTIVE=true counts."""
    monkeypatch.setattr(sys, "stdin", _FakeStdin(tty=True))
    monkeypatch.delenv("SPEC_KITTY_FORCE_INTERACTIVE", raising=False)
    monkeypatch.setenv("SPEC_KITTY_NON_INTERACTIVE", token)
    assert is_interactive() is False


@pytest.mark.parametrize("token", ["0", "false", "no", "", "off"])
def test_falsy_tokens_fall_through_to_the_tty_probe(monkeypatch: pytest.MonkeyPatch, token: str) -> None:
    monkeypatch.delenv("SPEC_KITTY_FORCE_INTERACTIVE", raising=False)
    monkeypatch.setenv("SPEC_KITTY_NON_INTERACTIVE", token)
    monkeypatch.setattr(sys, "stdin", _FakeStdin(tty=True))
    assert is_interactive() is True
    monkeypatch.setattr(sys, "stdin", _FakeStdin(tty=False))
    assert is_interactive() is False


def test_unset_env_falls_through_to_the_tty_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPEC_KITTY_FORCE_INTERACTIVE", raising=False)
    monkeypatch.delenv("SPEC_KITTY_NON_INTERACTIVE", raising=False)
    monkeypatch.setattr(sys, "stdin", _FakeStdin(tty=False))
    assert is_interactive() is False


def test_stdin_without_isatty_is_treated_as_non_interactive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SPEC_KITTY_FORCE_INTERACTIVE", raising=False)
    monkeypatch.delenv("SPEC_KITTY_NON_INTERACTIVE", raising=False)
    monkeypatch.setattr(sys, "stdin", object())
    assert is_interactive() is False
