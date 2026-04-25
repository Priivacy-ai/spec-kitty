"""DEPRECATED — specify_cli.runtime.resolver is a compatibility shim.

Import from runtime.discovery.resolver instead:
    from runtime.discovery.resolver import resolve_command, resolve_mission, ResolutionResult
"""
from __future__ import annotations

__deprecated__ = True
__canonical_import__ = "runtime.discovery.resolver"
__removal_release__ = "3.4.0"
__deprecation_message__ = (
    "specify_cli.runtime.resolver is deprecated; "
    "use 'from runtime.discovery.resolver import ...' instead. "
    "Scheduled for removal in 3.4.0."
)

import warnings

warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)

from runtime.discovery.resolver import *  # noqa: F401, F403  # NOSONAR
