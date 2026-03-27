"""Thin agent shim module.

Public API
----------
- ``generate_shims``   -- Write 3-line shim files for all configured agents.
- ``ShimTemplate``     -- Frozen dataclass for per-skill, per-agent identity.
- ``AgentShimConfig``  -- Frozen dataclass grouping all templates for one agent.
- ``SkillRegistry``    -- Convenience alias exposing skill allowlist helpers.
"""

from __future__ import annotations

from specify_cli.shims.generator import generate_all_shims as generate_shims
from specify_cli.shims.models import AgentShimConfig, ShimTemplate
from specify_cli.shims import registry as SkillRegistry  # noqa: N811

__all__ = [
    "AgentShimConfig",
    "ShimTemplate",
    "SkillRegistry",
    "generate_shims",
]
