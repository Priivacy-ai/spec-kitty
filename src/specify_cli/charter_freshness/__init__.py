"""Deprecated path; re-exports from charter_runtime.freshness for one cycle (C-008)."""

import importlib
import sys

from specify_cli.charter_runtime.freshness import *  # noqa: F401,F403
from specify_cli.charter_runtime.freshness import __all__  # noqa: F401

for _sub in ("computer",):
    sys.modules[f"{__name__}.{_sub}"] = importlib.import_module(
        f"specify_cli.charter_runtime.freshness.{_sub}"
    )
