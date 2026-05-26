"""Deprecated path; re-exports from charter_runtime.preflight for one cycle (C-008).

Two-pronged shim:

1. ``__path__`` is shared with the canonical package so Python's import
   machinery finds submodules under ``specify_cli.charter_preflight.cli``
   etc. via the canonical directory's source files. No disk I/O on package
   import.
2. ``__getattr__`` (PEP 562) handles ``from specify_cli.charter_preflight
   import hook`` style attribute access by deferring to the canonical
   module.

NFR-003 latency: an earlier WP08 shim eagerly imported every submodule via
``importlib.import_module`` at package import. That added ~189 ms to
``spec-kitty next`` startup. Sharing ``__path__`` removes that overhead.
"""

from __future__ import annotations

import importlib
import sys

_CANONICAL = "specify_cli.charter_runtime.preflight"

# Share the canonical package's __path__ so ``import
# specify_cli.charter_preflight.X`` finds ``X.py`` in the canonical
# directory via Python's normal import machinery.
__path__ = list(importlib.import_module(_CANONICAL).__path__)


def __getattr__(name: str) -> object:
    canonical = importlib.import_module(_CANONICAL)
    if hasattr(canonical, name):
        value = getattr(canonical, name)
        setattr(sys.modules[__name__], name, value)
        return value
    # Submodule access: try to import it lazily.
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
