"""DEPRECATED — specify_cli.runtime.agent_commands is a compatibility shim.

Import from runtime.agents.commands instead:
    from runtime.agents.commands import ensure_global_agent_commands
"""
from __future__ import annotations

__deprecated__ = True
__canonical_import__ = "runtime.agents.commands"
__removal_release__ = "3.4.0"
__deprecation_message__ = (
    "specify_cli.runtime.agent_commands is deprecated; "
    "use 'from runtime.agents.commands import ...' instead. "
    "Scheduled for removal in 3.4.0."
)

import warnings

warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)

from runtime.agents.commands import *  # noqa: F401, F403
from runtime.agents.commands import _sync_agent_commands  # noqa: F401 (private, not in *)

