"""Deprecated path; re-exports from charter_runtime.freshness for one cycle (C-008).

Eager sys.modules aliasing — see
``specify_cli/charter_preflight/__init__.py`` for the design rationale
(module-object identity for ``mock.patch`` correctness).
"""

from __future__ import annotations

import importlib
import sys

from specify_cli.charter_runtime.freshness import *  # noqa: F401,F403
from specify_cli.charter_runtime.freshness import __all__  # noqa: F401

_CANONICAL = "specify_cli.charter_runtime.freshness"

for _sub in ("computer",):
    _module = importlib.import_module(f"{_CANONICAL}.{_sub}")
    sys.modules[f"{__name__}.{_sub}"] = _module
    setattr(sys.modules[__name__], _sub, _module)
