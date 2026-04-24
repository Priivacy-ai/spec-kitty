"""DEPRECATED — specify_cli.runtime is a compatibility shim.

Import from runtime instead:
    from runtime import PresentationSink, StepContractExecutor, ProfileInvocationExecutor
"""
from __future__ import annotations

__deprecated__ = True
__canonical_import__ = "runtime"
__removal_release__ = "3.4.0"
__deprecation_message__ = (
    "specify_cli.runtime is deprecated; "
    "use 'from runtime import ...' instead. "
    "Scheduled for removal in 3.4.0."
)

import warnings

warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)

from runtime import *  # noqa: F401, F403
