"""Migration: Fix clarify template - replace placeholder with check-prerequisites command.

This migration updates the clarify.md template for all agents to use the correct
command for getting feature context, replacing the broken "(Missing script command for sh)"
placeholder with the proper `spec-kitty agent feature check-prerequisites` command.
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
class FixClarifyTemplateMigration(BaseMigration):
    """Fix clarify template with correct check-prerequisites command.

    This migration:
    1. Loads the canonical clarify.md template from packaged missions
    2. Copies it to all agent slash command directories
    3. Replaces broken placeholder with proper command
    4. Only updates software-dev clarify templates
    """

    migration_id = "0.13.5_fix_clarify_template"
    description = "Fix clarify template - replace placeholder with check-prerequisites command"
    target_version = "0.13.5"

    MISSION_NAME = "software-dev"
    TEMPLATE_FILE = "clarify.md"
    SLASH_COMMAND_FILE = "spec-kitty.clarify.md"

    def detect(self, project_path: Path) -> bool:
        """Check if any agent needs updated clarify template."""
        # Check for broken placeholder
        agent_dirs = get_agent_dirs_for_project(project_path)
        for agent_dir, subdir in agent_dirs:
            slash_cmd = project_path / agent_dir / subdir / self.SLASH_COMMAND_FILE
            if slash_cmd.exists():
                content = slash_cmd.read_text(encoding="utf-8")
                # If it has the broken placeholder or old manual detection logic
                if "(Missing script command for sh)" in content or "Check git branch name for pattern" in content:
                    return True
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if we can read the template from packaged missions."""
        try:
            data_root = files("specify_cli")
            template_path = data_root.joinpath(
                "missions", self.MISSION_NAME, "command-templates", self.TEMPLATE_FILE
            )
            if template_path.exists():
                return True, ""
        except Exception as e:
            return False, f"Cannot access packaged missions: {e}"
        return False, "Template not found in packaged missions"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Update clarify slash command across all agent directories."""
        changes: List[str] = []
        warnings: List[str] = []
        errors: List[str] = []

        # Load template from packaged missions
        try:
            data_root = files("specify_cli")
            template_path = data_root.joinpath(
                "missions", self.MISSION_NAME, "command-templates", self.TEMPLATE_FILE
            )

            if not template_path.exists():
                errors.append("Clarify template not found in packaged missions")
                return MigrationResult(
                    success=False,
                    changes_made=changes,
                    errors=errors,
                    warnings=warnings,
                )

            template_content = template_path.read_text(encoding="utf-8")
        except Exception as e:
            errors.append(f"Failed to read clarify template: {e}")
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

            # Skip if agent directory doesn't exist
            if not agent_path.exists():
                continue

            # Check if this agent has clarify template
            if slash_cmd.exists():
                current_content = slash_cmd.read_text(encoding="utf-8")

                # Check if already migrated
                if current_content == template_content:
                    continue  # Already up to date

                # Check if needs migration (has broken placeholder or old logic)
                needs_migration = (
                    "(Missing script command for sh)" in current_content or
                    "Check git branch name for pattern" in current_content
                )

                if needs_migration:
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
                changes.append(f"Would update {agents_updated} agent clarify templates")
            else:
                changes.append(f"Updated {agents_updated} agent clarify templates")
        else:
            changes.append("No agent clarify templates needed updates")

        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )
