"""Backward-compat shim — all types have moved to dashboard.api_types.

removal_release: FastAPI transport migration milestone
"""
# ruff: noqa: F401, F403
from dashboard.api_types import *  # noqa: F401, F403
from dashboard.api_types import __all__

__removal_release__ = "FastAPI transport migration milestone"
