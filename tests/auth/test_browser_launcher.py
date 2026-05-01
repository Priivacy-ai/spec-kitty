"""Tests for ``specify_cli.auth.loopback.browser_launcher`` (feature 080, WP02 T015).

**Critical**: these tests must never open a real browser. All
``webbrowser`` calls are monkeypatched.
"""

from __future__ import annotations

import webbrowser

import pytest

from specify_cli.auth.loopback.browser_launcher import BrowserLauncher


def test_is_available_true_when_webbrowser_get_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webbrowser, "get", lambda *a, **kw: object())
    assert BrowserLauncher.is_available() is True


def test_is_available_false_when_webbrowser_get_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*_a: object, **_kw: object) -> object:
        raise webbrowser.Error("no browser")

    monkeypatch.setattr(webbrowser, "get", _raise)
    assert BrowserLauncher.is_available() is False


def test_launch_returns_true_when_webbrowser_open_returns_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def _fake_open(url: str, new: int = 0, autoraise: bool = True) -> bool:
        calls.append((url, {"new": new, "autoraise": autoraise}))
        return True

    monkeypatch.setattr(webbrowser, "open", _fake_open)

    result = BrowserLauncher.launch("https://example.test/authorize?foo=bar")
    assert result is True
    assert calls == [("https://example.test/authorize?foo=bar", {"new": 2, "autoraise": True})]


def test_launch_returns_false_when_webbrowser_open_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(webbrowser, "open", lambda url, new=0, autoraise=True: False)
    assert BrowserLauncher.launch("https://example.test/authorize") is False


def test_launch_returns_false_when_webbrowser_open_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(*_a: object, **_kw: object) -> bool:
        raise webbrowser.Error("no browser registered")

    monkeypatch.setattr(webbrowser, "open", _raise)
    assert BrowserLauncher.launch("https://example.test/authorize") is False


def test_launch_does_not_call_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression guard: BrowserLauncher must NOT shell out to open/xdg-open/start."""
    import subprocess

    def _boom(*_a: object, **_kw: object) -> object:
        raise AssertionError("BrowserLauncher must not use subprocess")

    monkeypatch.setattr(subprocess, "run", _boom)
    monkeypatch.setattr(subprocess, "Popen", _boom)
    monkeypatch.setattr(webbrowser, "open", lambda url, new=0, autoraise=True: True)

    assert BrowserLauncher.launch("https://example.test/authorize") is True
