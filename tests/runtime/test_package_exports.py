"""Tests for lazy exports from specify_cli.runtime."""

from __future__ import annotations

import pytest

import specify_cli.runtime as runtime_pkg


def test_runtime_lazy_exports_resolve_symbols() -> None:
    assert runtime_pkg.resolve_template is not None
    assert runtime_pkg.get_kittify_home is not None


def test_runtime_unknown_export_raises_attribute_error() -> None:
    with pytest.raises(AttributeError):
        getattr(runtime_pkg, "definitely_missing_export")
