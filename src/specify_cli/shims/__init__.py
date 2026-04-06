"""Agent command file generation module.

Public API
----------
- ``generate_shims``   -- Write command files for all configured agents.
- ``SkillRegistry``    -- Convenience alias exposing skill allowlist helpers.
"""

from __future__ import annotations

from specify_cli.shims.generator import generate_all_shims as generate_shims
from specify_cli.shims import registry as SkillRegistry  # noqa: N811

__all__ = [
    "SkillRegistry",
    "generate_shims",
]
