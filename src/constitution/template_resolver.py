"""Project-aware template resolution through the 5-tier override chain.

Composes MissionTemplateRepository (doctrine-level, tier 5) with the
specify_cli runtime resolver (tiers 1-4). Constitution is the
concretization of doctrine into local context-aware legislation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from doctrine.missions.repository import MissionTemplateRepository, TemplateResult
from doctrine.resolver import (
    ResolutionTier,
    resolve_command,
    resolve_template,
)


class ConstitutionTemplateResolver:
    """5-tier project-aware template resolution.

    Resolution order: OVERRIDE > LEGACY > GLOBAL_MISSION > GLOBAL > PACKAGE_DEFAULT.
    """

    def __init__(self, repo: MissionTemplateRepository | None = None) -> None:
        self._repo = repo or MissionTemplateRepository.default()

    def resolve_command_template(
        self,
        mission: str,
        name: str,
        project_dir: Path | None = None,
    ) -> TemplateResult:
        """Resolve a command template through the 5-tier override chain.

        Args:
            mission: Mission name.
            name: Template name without ``.md`` extension.
            project_dir: Project root for override/legacy lookups.
                If ``None``, falls back to doctrine-level lookup only.

        Returns:
            TemplateResult with content, origin, and tier.

        Raises:
            FileNotFoundError: If template not found at any tier.
        """
        if project_dir is not None:
            result = resolve_command(f"{name}.md", project_dir, mission=mission)
            content = result.path.read_text(encoding="utf-8")
            origin = self._tier_to_origin(result.tier, mission, "command-templates", f"{name}.md")
            return TemplateResult(content=content, origin=origin, tier=result.tier)

        # No project context — doctrine-only lookup
        template = self._repo.get_command_template(mission, name)
        if template is None:
            raise FileNotFoundError(
                f"Command template '{name}.md' not found for mission '{mission}'"
            )
        return TemplateResult(
            content=template.content,
            origin=template.origin,
            tier=ResolutionTier.PACKAGE_DEFAULT,
        )

    def resolve_content_template(
        self,
        mission: str,
        name: str,
        project_dir: Path | None = None,
    ) -> TemplateResult:
        """Resolve a content template through the 5-tier override chain.

        Args:
            mission: Mission name.
            name: Template filename with extension.
            project_dir: Project root for override/legacy lookups.
                If ``None``, falls back to doctrine-level lookup only.

        Returns:
            TemplateResult with content, origin, and tier.

        Raises:
            FileNotFoundError: If template not found at any tier.
        """
        if project_dir is not None:
            result = resolve_template(name, project_dir, mission=mission)
            content = result.path.read_text(encoding="utf-8")
            origin = self._tier_to_origin(result.tier, mission, "templates", name)
            return TemplateResult(content=content, origin=origin, tier=result.tier)

        # No project context — doctrine-only lookup
        template = self._repo.get_content_template(mission, name)
        if template is None:
            raise FileNotFoundError(
                f"Content template '{name}' not found for mission '{mission}'"
            )
        return TemplateResult(
            content=template.content,
            origin=template.origin,
            tier=ResolutionTier.PACKAGE_DEFAULT,
        )

    @staticmethod
    def _tier_to_origin(tier: Any, mission: str, asset_type: str, filename: str) -> str:
        tier_prefix = {
            ResolutionTier.OVERRIDE: "override",
            ResolutionTier.LEGACY: "legacy",
            ResolutionTier.GLOBAL_MISSION: "global",
            ResolutionTier.GLOBAL: "global",
            ResolutionTier.PACKAGE_DEFAULT: "doctrine",
        }
        prefix = tier_prefix.get(tier, "unknown")
        return f"{prefix}/{mission}/{asset_type}/{filename}"
