"""session_presence.hooks — lifecycle hook implementations.

Public exports:
- ``HookRegistrar`` — protocol all hook registrars must satisfy.
- ``ClaudeCodeHookRegistrar`` — manages ``.claude/settings.json`` hooks.
"""

from __future__ import annotations

from .base import HookRegistrar
from .claude_code_hook import ClaudeCodeHookRegistrar

__all__ = ["HookRegistrar", "ClaudeCodeHookRegistrar"]
