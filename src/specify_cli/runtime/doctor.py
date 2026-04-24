"""DEPRECATED — specify_cli.runtime.doctor is a compatibility shim.

Import from runtime.orchestration.doctor instead:
    from runtime.orchestration.doctor import check_runtime_health
"""
from __future__ import annotations

__deprecated__ = True
__canonical_import__ = "runtime.orchestration.doctor"
__removal_release__ = "3.4.0"
__deprecation_message__ = (
    "specify_cli.runtime.doctor is deprecated; "
    "use 'from runtime.orchestration.doctor import ...' instead. "
    "Scheduled for removal in 3.4.0."
)

import warnings

warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)

from runtime.orchestration.doctor import *  # noqa: F401, F403
