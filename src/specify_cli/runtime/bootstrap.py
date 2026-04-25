"""DEPRECATED — specify_cli.runtime.bootstrap is a compatibility shim.

Import from runtime.orchestration.bootstrap instead:
    from runtime.orchestration.bootstrap import ensure_runtime, check_version_pin
"""
from __future__ import annotations

__deprecated__ = True
__canonical_import__ = "runtime.orchestration.bootstrap"
__removal_release__ = "3.4.0"
__deprecation_message__ = (
    "specify_cli.runtime.bootstrap is deprecated; "
    "use 'from runtime.orchestration.bootstrap import ...' instead. "
    "Scheduled for removal in 3.4.0."
)

import warnings

warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)

from runtime.orchestration.bootstrap import *  # noqa: F401, F403  # NOSONAR
