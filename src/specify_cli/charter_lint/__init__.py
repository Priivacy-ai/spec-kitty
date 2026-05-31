"""Deprecated path; re-exports from charter_runtime.lint for one cycle (C-008).

Eager sys.modules aliasing — see
``specify_cli/charter_preflight/__init__.py`` for the design rationale
(module-object identity for ``mock.patch`` correctness).
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
import types

from specify_cli.charter_runtime.lint import *  # noqa: F401,F403
from specify_cli.charter_runtime.lint import __all__  # noqa: F401

_CANONICAL = "specify_cli.charter_runtime.lint"

for _sub in ("_drg", "engine", "findings"):
    _module = importlib.import_module(f"{_CANONICAL}.{_sub}")
    sys.modules[f"{__name__}.{_sub}"] = _module
    setattr(sys.modules[__name__], _sub, _module)

_canonical_checks = importlib.import_module(f"{_CANONICAL}.checks")
_checks_shim_name = f"{__name__}.checks"
_checks_shim = types.ModuleType(_checks_shim_name, _canonical_checks.__doc__)
_checks_shim.__package__ = _checks_shim_name
_checks_shim.__path__ = []
_checks_shim.__all__ = getattr(_canonical_checks, "__all__", ())  # type: ignore[attr-defined]
sys.modules[_checks_shim_name] = _checks_shim
checks = _checks_shim

# Nested ``checks/*`` submodules — tests legitimately import these via the
# legacy dotted path (e.g. ``specify_cli.charter_lint.checks.staleness``).
# Discover canonical modules dynamically, but keep the legacy parent package's
# path empty so missing aliases fail loudly instead of creating duplicates.
for _module_info in pkgutil.iter_modules(_canonical_checks.__path__):
    _sub = _module_info.name
    _module = importlib.import_module(f"{_CANONICAL}.checks.{_sub}")
    sys.modules[f"{_checks_shim_name}.{_sub}"] = _module
    setattr(_checks_shim, _sub, _module)
