"""DEPRECATED — specify_cli.runtime.agent_skills is a compatibility shim.

Import from runtime.agents.skills instead:
    from runtime.agents.skills import ensure_global_agent_skills
"""
from __future__ import annotations

__deprecated__ = True
__canonical_import__ = "runtime.agents.skills"
__removal_release__ = "3.4.0"
__deprecation_message__ = (
    "specify_cli.runtime.agent_skills is deprecated; "
    "use 'from runtime.agents.skills import ...' instead. "
    "Scheduled for removal in 3.4.0."
)

import warnings

warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)

from runtime.agents.skills import *  # noqa: F401, F403
