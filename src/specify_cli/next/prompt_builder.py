"""DEPRECATED — specify_cli.next.prompt_builder is a compatibility shim.

Import from runtime.prompts.builder instead:
    from runtime.prompts.builder import build_prompt, build_decision_prompt
"""
from __future__ import annotations

__deprecated__ = True
__canonical_import__ = "runtime.prompts.builder"
__removal_release__ = "3.4.0"
__deprecation_message__ = (
    "specify_cli.next.prompt_builder is deprecated; "
    "use 'from runtime.prompts.builder import ...' instead. "
    "Scheduled for removal in 3.4.0."
)

import warnings

warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)

from runtime.prompts.builder import *  # noqa: F401, F403  # NOSONAR
