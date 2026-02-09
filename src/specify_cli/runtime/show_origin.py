"""Show resolution origin for all known assets.

Enumerates templates, command-templates, and missions through the 4-tier
resolution chain and reports where each asset resolves from.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from specify_cli.runtime.resolver import (
    ResolutionTier,
    resolve_command,
    resolve_mission,
    resolve_template,
)

TEMPLATE_NAMES = [
    "spec-template.md",
    "plan-template.md",
    "tasks-template.md",
    "task-prompt-template.md",
]

COMMAND_NAMES = [
    "specify.md",
    "plan.md",
    "tasks.md",
    "implement.md",
    "review.md",
    "accept.md",
    "merge.md",
    "dashboard.md",
]

MISSION_NAMES = [
    "software-dev",
    "research",
    "documentation",
]


@dataclass
class OriginEntry:
    """A single resolved asset with its tier origin."""

    asset_type: str  # "template", "command", "mission"
    name: str  # "spec-template.md", "software-dev", etc.
    resolved_path: Path | None
    tier: str | None  # "override", "legacy", "global", "package_default"
    error: str | None  # If resolution failed


def collect_origins(
    project_dir: Path,
    mission: str = "software-dev",
) -> list[OriginEntry]:
    """Collect resolution origin for all known assets.

    Walks through templates, command-templates, and missions, resolving
    each through the 4-tier precedence chain.

    Args:
        project_dir: Project root containing ``.kittify/``.
        mission: Mission key for template/command resolution.

    Returns:
        List of OriginEntry with resolution details for every known asset.
    """
    entries: list[OriginEntry] = []

    # Templates
    for name in TEMPLATE_NAMES:
        try:
            result = resolve_template(name, project_dir, mission)
            entries.append(
                OriginEntry("template", name, result.path, result.tier.value, None)
            )
        except FileNotFoundError as e:
            entries.append(OriginEntry("template", name, None, None, str(e)))

    # Command templates
    for name in COMMAND_NAMES:
        try:
            result = resolve_command(name, project_dir, mission)
            entries.append(
                OriginEntry("command", name, result.path, result.tier.value, None)
            )
        except FileNotFoundError as e:
            entries.append(OriginEntry("command", name, None, None, str(e)))

    # Missions
    for name in MISSION_NAMES:
        try:
            result = resolve_mission(name, project_dir)
            entries.append(
                OriginEntry("mission", name, result.path, result.tier.value, None)
            )
        except FileNotFoundError as e:
            entries.append(OriginEntry("mission", name, None, None, str(e)))

    return entries
