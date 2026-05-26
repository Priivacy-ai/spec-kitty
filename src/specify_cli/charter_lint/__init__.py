"""Deprecated path; re-exports from charter_runtime.lint for one cycle (C-008).

Eager sys.modules aliasing — see
``specify_cli/charter_preflight/__init__.py`` for the design rationale
(module-object identity for ``mock.patch`` correctness).
"""

from __future__ import annotations

import importlib
import sys

from specify_cli.charter_runtime.lint import *  # noqa: F401,F403
from specify_cli.charter_runtime.lint import __all__  # noqa: F401

_CANONICAL = "specify_cli.charter_runtime.lint"

for _sub in ("_drg", "engine", "findings", "checks"):
    _module = importlib.import_module(f"{_CANONICAL}.{_sub}")
    sys.modules[f"{__name__}.{_sub}"] = _module
    setattr(sys.modules[__name__], _sub, _module)

# Nested ``checks/*`` submodules — tests legitimately import these via the
# legacy dotted path (e.g. ``specify_cli.charter_lint.checks.staleness``).
for _sub in (
    "contradiction",
    "org_layer",
    "orphan",
    "reference_integrity",
    "staleness",
):
    _module = importlib.import_module(f"{_CANONICAL}.checks.{_sub}")
    sys.modules[f"{__name__}.checks.{_sub}"] = _module
