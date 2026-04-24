"""DEPRECATED — specify_cli.runtime.migrate is a compatibility shim.

Import from runtime.orchestration.migrate instead:
    from runtime.orchestration.migrate import classify_asset, execute_migration
"""
from __future__ import annotations

__deprecated__ = True
__canonical_import__ = "runtime.orchestration.migrate"
__removal_release__ = "3.4.0"
__deprecation_message__ = (
    "specify_cli.runtime.migrate is deprecated; "
    "use 'from runtime.orchestration.migrate import ...' instead. "
    "Scheduled for removal in 3.4.0."
)

import warnings

warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)

from runtime.orchestration.migrate import *  # noqa: F401, F403
