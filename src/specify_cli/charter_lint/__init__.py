"""Deprecated path; re-exports from charter_runtime.lint for one cycle (C-008)."""

import importlib
import sys

from specify_cli.charter_runtime.lint import *  # noqa: F401,F403
from specify_cli.charter_runtime.lint import __all__  # noqa: F401

for _sub in ("_drg", "engine", "findings", "checks"):
    sys.modules[f"{__name__}.{_sub}"] = importlib.import_module(
        f"specify_cli.charter_runtime.lint.{_sub}"
    )
# Also alias nested checks submodules
for _sub in (
    "contradiction",
    "org_layer",
    "orphan",
    "reference_integrity",
    "staleness",
):
    sys.modules[f"{__name__}.checks.{_sub}"] = importlib.import_module(
        f"specify_cli.charter_runtime.lint.checks.{_sub}"
    )
