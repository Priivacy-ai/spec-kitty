"""Migration: Add Commit Workflow section to implement.md templates.

This migration updates both software-dev and documentation mission implement
templates to include the commit workflow section that prevents agents from
marking WPs as complete without committing their work.

Fixes GitHub Issue #72 for existing projects.
"""

from __future__ import annotations

import json
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
class AddCommitWorkflowToTemplatesMigration(BaseMigration):
    """Add Commit Workflow section to implement slash commands.

    This migration:
    1. Loads canonical implement.md templates from packaged missions
    2. Copies to all agent slash command directories
    3. Updates both software-dev and documentation missions
    4. Only updates configured agents (respects agent config)
    """

    migration_id = "0.13.5_add_commit_workflow_to_templates"
    description = "Add commit workflow section to implement slash commands"
    target_version = "0.13.5"

    TEMPLATE_FILE = "implement.md"
    SLASH_COMMAND_FILE = "spec-kitty.implement.md"

    def detect(self, project_path: Path) -> bool:
        """Check if any agent needs updated implement template."""
        agent_dirs = get_agent_dirs_for_project(project_path)
        for agent_dir, subdir in agent_dirs:
            slash_cmd = project_path / agent_dir / subdir / self.SLASH_COMMAND_FILE
            if slash_cmd.exists():
                content = slash_cmd.read_text(encoding="utf-8")
                # Check if missing commit workflow section
                if "Commit Workflow" not in content:
                    return True
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if we can read templates from packaged missions."""
        try:
            data_root = files("specify_cli")
            for mission in ["software-dev", "documentation"]:
                template_path = data_root.joinpath(
                    "missions", mission, "command-templates", self.TEMPLATE_FILE
                )
                if not template_path.exists():
                    return False, f"Template not found: missions/{mission}/command-templates/{self.TEMPLATE_FILE}"
            return True, ""
        except Exception as e:
            return False, f"Cannot access packaged missions: {e}"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Update implement slash commands across all agent directories."""
        changes: List[str] = []
        warnings: List[str] = []
        errors: List[str] = []

        # Detect mission type from meta.json
        meta_file = project_path / ".kittify" / "meta.json"
        if not meta_file.exists():
            warnings.append("No meta.json found - cannot determine mission type")
            # Try both missions as fallback
            missions_to_update = ["software-dev", "documentation"]
        else:
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                current_mission = meta.get("mission_name", "software-dev")
                missions_to_update = [current_mission]
            except Exception as e:
                warnings.append(f"Cannot parse meta.json: {e}")
                missions_to_update = ["software-dev", "documentation"]

        # Load template from packaged missions
        for mission_name in missions_to_update:
            try:
                data_root = files("specify_cli")
                template_path = data_root.joinpath(
                    "missions", mission_name, "command-templates", self.TEMPLATE_FILE
                )

                if not template_path.exists():
                    warnings.append(f"Template not found for mission: {mission_name}")
                    continue

                template_content = template_path.read_text(encoding="utf-8")
            except Exception as e:
                errors.append(f"Failed to read {mission_name} template: {e}")
                continue

            # Update configured agent directories
            agents_updated = 0
            agent_dirs = get_agent_dirs_for_project(project_path)
            for agent_dir, subdir in agent_dirs:
                agent_path = project_path / agent_dir / subdir
                slash_cmd = agent_path / self.SLASH_COMMAND_FILE

                # Skip if agent directory doesn't exist
                if not agent_path.exists():
                    continue

                # Check if this agent has implement template
                if slash_cmd.exists():
                    current_content = slash_cmd.read_text(encoding="utf-8")

                    # Check if already migrated
                    if current_content == template_content:
                        continue  # Already up to date

                    # Check if needs migration (missing commit workflow)
                    if "Commit Workflow" not in current_content:
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
                    changes.append(f"Would update {agents_updated} agent implement templates ({mission_name})")
                else:
                    changes.append(f"Updated {agents_updated} agent implement templates ({mission_name})")
            elif not warnings:  # Only log if we tried to update this mission
                changes.append(f"No agent implement templates needed updates ({mission_name})")

        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )
