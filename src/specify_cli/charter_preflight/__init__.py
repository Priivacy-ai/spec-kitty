"""Deprecated path; re-exports from charter_runtime.preflight for one cycle (C-008)."""

import importlib
import sys

from specify_cli.charter_runtime.preflight import *  # noqa: F401,F403
from specify_cli.charter_runtime.preflight import __all__  # noqa: F401

for _sub in ("cli", "config", "dashboard_warning", "hook", "result", "runner"):
    sys.modules[f"{__name__}.{_sub}"] = importlib.import_module(
        f"specify_cli.charter_runtime.preflight.{_sub}"
    )
