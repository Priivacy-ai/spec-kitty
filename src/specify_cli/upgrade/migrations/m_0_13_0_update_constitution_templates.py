"""Migration: Fix constitution.md next-step suggestion across all agents.

This migration updates the constitution.md template to suggest /spec-kitty.specify
instead of /spec-kitty.plan as the next step after creating a project constitution.
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
class UpdateConstitutionTemplatesMigration(BaseMigration):
    """Fix constitution.md next-step suggestion across all agents.

    This migration:
    1. Loads the canonical constitution.md template from packaged missions
    2. Copies it to all agent slash command directories
    3. Updates the "Next steps" text to suggest /spec-kitty.specify
    4. Only processes software-dev mission templates
    """

    migration_id = "0.13.0_update_constitution_templates"
    description = "Fix constitution next-step to /spec-kitty.specify"
    target_version = "0.13.0"

    MISSION_NAME = "software-dev"
    TEMPLATE_FILE = "constitution.md"
    SLASH_COMMAND_FILE = "spec-kitty.constitution.md"

    def detect(self, project_path: Path) -> bool:
        """Check if any agent has old /spec-kitty.plan reference."""
        agent_dirs = get_agent_dirs_for_project(project_path)
        for agent_dir, subdir in agent_dirs:
            slash_cmd = project_path / agent_dir / subdir / self.SLASH_COMMAND_FILE
            if slash_cmd.exists():
                content = slash_cmd.read_text(encoding="utf-8")
                # Look for the wrong reference in the Next steps context
                if "run /spec-kitty.plan" in content and "Next steps" in content:
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
        """Update constitution slash command across all agent directories."""
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
                errors.append("Constitution template not found in packaged missions")
                return MigrationResult(
                    success=False,
                    changes_made=changes,
                    errors=errors,
                    warnings=warnings,
                )

            template_content = template_path.read_text(encoding="utf-8")
        except Exception as e:
            errors.append(f"Failed to read constitution template: {e}")
            return MigrationResult(
                success=False,
                changes_made=changes,
                errors=errors,
                warnings=warnings,
            )

        # Update configured agent directories
        agents_updated = 0
        agent_dirs = get_agent_dirs_for_project(project_path)
        for agent_dir, subdir in agent_dirs:
            agent_path = project_path / agent_dir / subdir
            slash_cmd = agent_path / self.SLASH_COMMAND_FILE

            # Skip if agent directory doesn't exist (respect deletions)
            if not agent_path.exists():
                continue

            # Update if file exists
            if slash_cmd.exists():
                current_content = slash_cmd.read_text(encoding="utf-8")

                # Check if already migrated
                if current_content == template_content:
                    continue  # Already up to date

                # Only update if it has the old reference
                if "run /spec-kitty.plan" in current_content and "Next steps" in current_content:
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
                changes.append(f"Would update {agents_updated} agent constitution templates")
            else:
                changes.append(f"Updated {agents_updated} agent constitution templates")
        else:
            changes.append("No agent constitution templates needed updates")

        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )
