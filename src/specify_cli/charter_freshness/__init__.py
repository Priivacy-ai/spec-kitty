"""Deprecated path; re-exports from charter_runtime.freshness for one cycle (C-008).

Shares ``__path__`` with the canonical package + lazy ``__getattr__``.
See ``specify_cli/charter_preflight/__init__.py`` for the design rationale.
"""

from __future__ import annotations

import importlib
import sys

_CANONICAL = "specify_cli.charter_runtime.freshness"

__path__ = list(importlib.import_module(_CANONICAL).__path__)


def __getattr__(name: str) -> object:
    canonical = importlib.import_module(_CANONICAL)
    if hasattr(canonical, name):
        value = getattr(canonical, name)
        setattr(sys.modules[__name__], name, value)
        return value
    try:
        sub = importlib.import_module(f"{_CANONICAL}.{name}")
    except ModuleNotFoundError:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        ) from None
    setattr(sys.modules[__name__], name, sub)
    return sub


def __dir__() -> list[str]:
    canonical = importlib.import_module(_CANONICAL)
    return sorted(vars(canonical))
