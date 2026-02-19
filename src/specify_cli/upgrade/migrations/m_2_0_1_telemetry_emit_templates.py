"""Migration: Add telemetry emit section to workflow slash command templates.

This migration updates specify, plan, tasks, review, and merge templates
to include a final telemetry emit step that instructs agents to call
`spec-kitty agent telemetry emit` after completing each phase.

Part of Feature 048: Full-Lifecycle Telemetry Events.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

try:
    from importlib.resources import files
except ImportError:
    from importlib_resources import files  # type: ignore

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult
from .m_0_9_1_complete_lane_migration import get_agent_dirs_for_project


TEMPLATES_TO_UPDATE = [
    "specify.md",
    "plan.md",
    "tasks.md",
    "review.md",
    "merge.md",
]

TELEMETRY_MARKER = "spec-kitty agent telemetry emit"


@MigrationRegistry.register
class TelemetryEmitTemplatesMigration(BaseMigration):
    """Add telemetry emit section to workflow slash command templates.

    This migration:
    1. Loads canonical templates from packaged software-dev mission
    2. Copies updated specify, plan, tasks, review, merge to all configured agents
    3. Only updates agents that are missing the telemetry emit section
    """

    migration_id = "2.0.1_telemetry_emit_templates"
    description = "Add telemetry emit section to workflow slash command templates"
    target_version = "2.0.1"

    def detect(self, project_path: Path) -> bool:
        """Check if any agent needs updated templates."""
        agent_dirs = get_agent_dirs_for_project(project_path)
        for agent_dir, subdir in agent_dirs:
            agent_path = project_path / agent_dir / subdir
            if not agent_path.exists():
                continue
            for template_name in TEMPLATES_TO_UPDATE:
                slash_cmd = agent_path / f"spec-kitty.{template_name}"
                if slash_cmd.exists():
                    content = slash_cmd.read_text(encoding="utf-8")
                    if TELEMETRY_MARKER not in content:
                        return True
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if we can read templates from packaged missions."""
        try:
            data_root = files("specify_cli")
            for template_name in TEMPLATES_TO_UPDATE:
                template_path = data_root.joinpath(
                    "missions", "software-dev", "command-templates", template_name
                )
                if not template_path.exists():
                    return False, f"Template not found: missions/software-dev/command-templates/{template_name}"
            return True, ""
        except Exception as e:
            return False, f"Cannot access packaged missions: {e}"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Update workflow slash commands across all configured agent directories."""
        changes: List[str] = []
        warnings: List[str] = []
        errors: List[str] = []

        # Load all canonical templates
        templates: dict[str, str] = {}
        try:
            data_root = files("specify_cli")
            for template_name in TEMPLATES_TO_UPDATE:
                template_path = data_root.joinpath(
                    "missions", "software-dev", "command-templates", template_name
                )
                templates[template_name] = template_path.read_text(encoding="utf-8")
        except Exception as e:
            return MigrationResult(
                success=False,
                changes_made=changes,
                errors=[f"Failed to read templates: {e}"],
                warnings=warnings,
            )

        # Update configured agent directories
        agents_updated = 0
        agent_dirs = get_agent_dirs_for_project(project_path)

        for agent_dir, subdir in agent_dirs:
            agent_path = project_path / agent_dir / subdir

            # Skip if agent directory doesn't exist (respect deletions)
            if not agent_path.exists():
                continue

            for template_name in TEMPLATES_TO_UPDATE:
                slash_cmd = agent_path / f"spec-kitty.{template_name}"

                if not slash_cmd.exists():
                    continue

                current_content = slash_cmd.read_text(encoding="utf-8")

                # Skip if already has telemetry section
                if TELEMETRY_MARKER in current_content:
                    continue

                if dry_run:
                    changes.append(f"Would update: {agent_dir}/{subdir}/spec-kitty.{template_name}")
                else:
                    try:
                        slash_cmd.write_text(templates[template_name], encoding="utf-8")
                        changes.append(f"Updated: {agent_dir}/{subdir}/spec-kitty.{template_name}")
                        agents_updated += 1
                    except Exception as e:
                        errors.append(f"Failed to update {agent_dir}/{subdir}/spec-kitty.{template_name}: {e}")

        if agents_updated > 0:
            changes.append(f"Updated {agents_updated} agent template files with telemetry emit section")
        elif not errors:
            changes.append("No agent templates needed updates (all already have telemetry section)")

        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )
