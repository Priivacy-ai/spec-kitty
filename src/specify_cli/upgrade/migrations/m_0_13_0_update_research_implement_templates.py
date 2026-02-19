"""Migration: Update research implement.md with CSV schema documentation.

This migration adds the "Research CSV Schemas" section to all agent implement
slash commands for research missions, documenting the canonical schemas for
evidence-log.csv and source-register.csv.
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


@MigrationRegistry.register
class UpdateResearchImplementTemplatesMigration(BaseMigration):
    """Add Research CSV Schemas section to research implement slash commands.

    This migration:
    1. Loads the canonical research implement.md template from packaged missions
    2. Copies it to all agent slash command directories
    3. Only updates research templates (not software-dev)
    4. Skips agents that don't have research templates
    """

    migration_id = "0.13.0_update_research_implement_templates"
    description = "Add CSV schema docs to research implement slash commands"
    target_version = "0.13.0"

    MISSION_NAME = "research"
    TEMPLATE_FILE = "implement.md"
    SLASH_COMMAND_FILE = "spec-kitty.implement.md"

    def detect(self, project_path: Path) -> bool:
        """Check if any agent needs updated research template."""
        # Check for missing schema section
        agent_dirs = get_agent_dirs_for_project(project_path)
        for agent_dir, subdir in agent_dirs:
            slash_cmd = project_path / agent_dir / subdir / self.SLASH_COMMAND_FILE
            if slash_cmd.exists():
                content = slash_cmd.read_text(encoding="utf-8")
                # If it's a research template (has Sprint Planning Artifacts)
                # but missing schema docs
                if "Sprint Planning Artifacts" in content and "Research CSV Schemas" not in content:
                    return True
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if we can read the template from packaged missions."""
        try:
            data_root = files("specify_cli")
            template_path = data_root.joinpath(
                "missions", self.MISSION_NAME, "command-templates", self.TEMPLATE_FILE
            )
            if template_path.is_file():
                return True, ""
        except Exception as e:
            return False, f"Cannot access packaged missions: {e}"
        return False, "Template not found in packaged missions"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Update research implement slash command across all agent directories."""
        changes: List[str] = []
        warnings: List[str] = []
        errors: List[str] = []

        # Load template from packaged missions
        try:
            data_root = files("specify_cli")
            template_path = data_root.joinpath(
                "missions", self.MISSION_NAME, "command-templates", self.TEMPLATE_FILE
            )

            if not template_path.is_file():
                errors.append("Research template not found in packaged missions")
                return MigrationResult(
                    success=False,
                    changes_made=changes,
                    errors=errors,
                    warnings=warnings,
                )

            template_content = template_path.read_text(encoding="utf-8")
        except Exception as e:
            errors.append(f"Failed to read research template: {e}")
            return MigrationResult(
                success=False,
                changes_made=changes,
                errors=errors,
                warnings=warnings,
            )

        # Update configured agent directories (only research missions)
        agents_updated = 0
        agent_dirs = get_agent_dirs_for_project(project_path)
        for agent_dir, subdir in agent_dirs:
            agent_path = project_path / agent_dir / subdir
            slash_cmd = agent_path / self.SLASH_COMMAND_FILE

            # Skip if agent directory doesn't exist
            if not agent_path.exists():
                continue

            # Check if this agent has research template (not software-dev)
            if slash_cmd.exists():
                current_content = slash_cmd.read_text(encoding="utf-8")
                # Only update if it's a research template (has Sprint Planning Artifacts)
                if "Sprint Planning Artifacts" in current_content:
                    # Check if already migrated
                    if current_content == template_content:
                        continue  # Already up to date

                    if dry_run:
                        changes.append(f"Would update: {agent_dir}/{subdir}/{self.SLASH_COMMAND_FILE}")
                    else:
                        try:
                            slash_cmd.write_text(template_content, encoding="utf-8")
                            changes.append(f"Updated: {agent_dir}/{subdir}/{self.SLASH_COMMAND_FILE}")
                            agents_updated += 1
                        except Exception as e:
                            errors.append(f"Failed to update {agent_dir}/{subdir}: {e}")

        if agents_updated > 0:
            if dry_run:
                changes.append(f"Would update {agents_updated} agent research templates")
            else:
                changes.append(f"Updated {agents_updated} agent research templates")
        else:
            changes.append("No agent research templates needed updates")

        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )
