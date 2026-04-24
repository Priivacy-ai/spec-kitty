"""DEPRECATED — specify_cli.runtime.merge is a compatibility shim.

Import from runtime.orchestration.merge instead:
    from runtime.orchestration.merge import merge_runtime_assets
"""
from __future__ import annotations

__deprecated__ = True
__canonical_import__ = "runtime.orchestration.merge"
__removal_release__ = "3.4.0"
__deprecation_message__ = (
    "specify_cli.runtime.merge is deprecated; "
    "use 'from runtime.orchestration.merge import ...' instead. "
    "Scheduled for removal in 3.4.0."
)

import warnings

warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)

from runtime.orchestration.merge import *  # noqa: F401, F403
