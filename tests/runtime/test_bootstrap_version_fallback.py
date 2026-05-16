"""Regression tests for runtime bootstrap when the package version is unknown.

Covers issue #1070: ``spec-kitty sync status --check`` previously crashed
with ``TypeError: data must be str, not NoneType`` whenever
``specify_cli.__version__`` resolved to ``None`` (broken editable
install, partial wheel, etc.). ``_get_cli_version`` now returns a safe
default so the runtime cache always receives a string.
"""

from __future__ import annotations

import importlib
import sys


def test_get_cli_version_returns_string_when_version_is_none(monkeypatch) -> None:
    bootstrap = importlib.import_module("specify_cli.runtime.bootstrap")
    fake_module = sys.modules["specify_cli"]
    monkeypatch.setattr(fake_module, "__version__", None, raising=False)
    result = bootstrap._get_cli_version()
    assert isinstance(result, str)
    assert result, "fallback version must be a non-empty string"


def test_get_cli_version_returns_string_when_version_missing(monkeypatch) -> None:
    bootstrap = importlib.import_module("specify_cli.runtime.bootstrap")
    fake_module = sys.modules["specify_cli"]
    if hasattr(fake_module, "__version__"):
        monkeypatch.delattr(fake_module, "__version__", raising=False)
    result = bootstrap._get_cli_version()
    assert isinstance(result, str)
    assert result


def test_get_cli_version_returns_string_when_version_blank(monkeypatch) -> None:
    bootstrap = importlib.import_module("specify_cli.runtime.bootstrap")
    fake_module = sys.modules["specify_cli"]
    monkeypatch.setattr(fake_module, "__version__", "", raising=False)
    result = bootstrap._get_cli_version()
    assert isinstance(result, str)
    assert result
