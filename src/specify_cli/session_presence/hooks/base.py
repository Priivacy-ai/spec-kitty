"""HookRegistrar protocol — interface for harness lifecycle hook registration.

All hook registrars (e.g. ``ClaudeCodeHookRegistrar``) must satisfy this
protocol so that writers can depend on a stable interface rather than a
concrete implementation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

__all__ = ["HookRegistrar"]


class HookRegistrar(Protocol):
    """Protocol for harness-specific hook registration.

    Implementations manage the mechanics of registering and unregistering a
    shell command in the harness's native hook configuration file (e.g.
    ``.claude/settings.json``).
    """

    def register(self, project_root: Path, command: str) -> None:
        """Register *command* as a harness lifecycle hook.

        Idempotent — calling when *command* is already registered is a no-op.
        """
        ...

    def unregister(self, project_root: Path, command: str) -> None:
        """Remove the *command* hook entry, if present.

        Must not touch any other registered hooks.  No-op when not registered.
        """
        ...

    def is_registered(self, project_root: Path, command: str) -> bool:
        """Return ``True`` when *command* is already registered as a hook."""
        ...
