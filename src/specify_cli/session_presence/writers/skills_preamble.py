"""SkillsPreambleWriter — session presence writer for skills-preamble harnesses.

Pattern D: orientation injected via a skills preamble or AGENTS.md fallback.

Defaults to AGENTS.md injection (same behaviour as ``AgentsMdWriter``) while
harness-specific research is open.  See
``docs/plans/research/session-presence-harness-gaps.md``.

When a harness-specific preamble path is confirmed, subclass and override
``rules_path`` and ``can_write()`` accordingly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .agents_md import AgentsMdWriter

__all__ = ["SkillsPreambleWriter"]


@dataclass
class SkillsPreambleWriter(AgentsMdWriter):
    """Pattern D: orientation injected via skills preamble or AGENTS.md fallback.

    Defaults to AGENTS.md injection (same as Pattern C) while harness-specific
    research is open.  Once a harness-specific preamble path is confirmed,
    subclass and override ``rules_path`` and ``can_write()`` accordingly.

    Used by Pi, Vibe, and Letta.
    """

    harness_key: str = field(default="")  # overridden per instance
