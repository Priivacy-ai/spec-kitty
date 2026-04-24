"""DEPRECATED — specify_cli.next.runtime_bridge is a compatibility shim.

Import from runtime.bridge.runtime_bridge instead:
    from runtime.bridge.runtime_bridge import decide_next_via_runtime, query_current_state
"""
from __future__ import annotations

__deprecated__ = True
__canonical_import__ = "runtime.bridge.runtime_bridge"
__removal_release__ = "3.4.0"
__deprecation_message__ = (
    "specify_cli.next.runtime_bridge is deprecated; "
    "use 'from runtime.bridge.runtime_bridge import ...' instead. "
    "Scheduled for removal in 3.4.0."
)

import warnings

warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)

from runtime.bridge.runtime_bridge import *  # noqa: F401, F403
