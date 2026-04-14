"""Tests for render_runtime_path() rendering behavior per platform."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from specify_cli.paths import render_runtime_path


def test_windows_returns_absolute(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    # Simulate Windows absolute path semantics on a POSIX test runner by using
    # a concrete path that exists. The helper uses resolve(strict=False) so
    # rendering stays stable.
    p = Path("/tmp/fake-windows-path/spec-kitty/auth")
    rendered = render_runtime_path(p)
    assert not rendered.startswith("~/")
    assert "spec-kitty" in rendered


def test_posix_tilde_compression_under_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    p = tmp_path / ".spec-kitty" / "auth"
    assert render_runtime_path(p) == "~/.spec-kitty/auth"


def test_posix_absolute_outside_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    p = Path("/var/lib/spec-kitty")
    rendered = render_runtime_path(p)
    assert not rendered.startswith("~/")
    assert "spec-kitty" in rendered


def test_for_user_false_always_absolute(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    p = tmp_path / ".spec-kitty" / "auth"
    rendered = render_runtime_path(p, for_user=False)
    assert not rendered.startswith("~/")
