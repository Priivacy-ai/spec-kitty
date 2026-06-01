"""Compatibility shim for the extracted ``runtime.next`` package.

Deprecated: import from ``runtime.next`` instead. Scheduled for removal in
3.3.0.
"""

from __future__ import annotations

import importlib
import sys
import warnings
from typing import Any

__deprecated__ = True
__canonical_import__ = "runtime.next"
__removal_release__ = "3.3.0"
__deprecation_message__ = (
    "specify_cli.next is deprecated; import from runtime.next. "
    "Scheduled for removal in 3.3.0."
)

warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)

_runtime_next = importlib.import_module("runtime.next")
__all__ = list(getattr(_runtime_next, "__all__", ()))

for _export in __all__:
    globals()[_export] = getattr(_runtime_next, _export)

_SUBMODULES = (
    "_internal_runtime",
    "_runtime_pkg_notice",
    "decision",
    "discovery",
    "prompt_builder",
    "runtime_bridge",
)

_INTERNAL_RUNTIME_SUBMODULES = (
    "contracts",
    "discovery",
    "emitter",
    "engine",
    "events",
    "lifecycle",
    "models",
    "planner",
    "raci",
    "retrospective_hook",
    "retrospective_terminus",
    "schema",
    "significance",
    "workflow_registry",
    "workflow_schema",
)

for _name in _SUBMODULES:
    _module = importlib.import_module(f"runtime.next.{_name}")
    sys.modules[f"{__name__}.{_name}"] = _module
    globals()[_name] = _module

for _name in _INTERNAL_RUNTIME_SUBMODULES:
    _module = importlib.import_module(f"runtime.next._internal_runtime.{_name}")
    sys.modules[f"{__name__}._internal_runtime.{_name}"] = _module


def __getattr__(name: str) -> Any:
    value = getattr(_runtime_next, name)
    globals()[name] = value
    return value


del _export
del _module
del _name
