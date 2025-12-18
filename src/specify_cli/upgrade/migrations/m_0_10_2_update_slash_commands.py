"""Migration: Update slash commands to Python CLI and flat structure."""

from __future__ import annotations

from pathlib import Path
from typing import List

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class UpdateSlashCommandsMigration(BaseMigration):
    """Update .claude/commands/ to use Python CLI and flat tasks/ structure.

    This migration addresses two critical issues from feature 008 and 007:
    1. Slash commands still referenced deleted bash scripts (feature 008 bug)
    2. Slash commands instructed agents to create subdirectories (feature 007 violation)

    This migration:
    1. Detects if slash commands have old bash script references
    2. Detects if slash commands have subdirectory instructions
    3. Re-copies templates from mission to get latest Python CLI + flat structure
    """

    migration_id = "0.10.2_update_slash_commands"
    description = "Update slash commands to Python CLI and flat structure"
    target_version = "0.10.2"

    def detect(self, project_path: Path) -> bool:
        """Check if slash commands need updating."""
        claude_commands = project_path / ".claude" / "commands"

        if not claude_commands.exists():
            return True

        # Check for bash script references (old)
        for cmd_file in claude_commands.glob("spec-kitty.*.md"):
            content = cmd_file.read_text(encoding="utf-8")
            if ".kittify/scripts/bash/" in content or "scripts/bash/" in content:
                return True
            if "tasks/planned/" in content or "tasks/doing/" in content:
                return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if we have mission templates to copy from."""
        missions_dir = project_path / ".kittify" / "missions"
        if not missions_dir.exists():
            return False, "No missions directory found"

        # Look for software-dev mission
        software_dev_templates = missions_dir / "software-dev" / "command-templates"
        if software_dev_templates.exists():
            return True, ""

        # Look for any mission with command-templates
        for mission_dir in missions_dir.iterdir():
            if mission_dir.is_dir():
                templates = mission_dir / "command-templates"
                if templates.exists():
                    return True, ""

        return False, "No mission command templates found"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Update slash commands with latest templates."""
        changes: List[str] = []
        warnings: List[str] = []
        errors: List[str] = []

        missions_dir = project_path / ".kittify" / "missions"
        claude_commands = project_path / ".claude" / "commands"

        # Find mission templates
        command_templates_dir = None
        software_dev_templates = missions_dir / "software-dev" / "command-templates"

        if software_dev_templates.exists():
            command_templates_dir = software_dev_templates
            mission_name = "software-dev"
        else:
            # Find first mission with templates
            for mission_dir in sorted(missions_dir.iterdir()):
                if mission_dir.is_dir():
                    templates = mission_dir / "command-templates"
                    if templates.exists():
                        command_templates_dir = templates
                        mission_name = mission_dir.name
                        break

        if not command_templates_dir:
            errors.append("No mission command templates found")
            return MigrationResult(
                success=False,
                changes_made=changes,
                errors=errors,
                warnings=warnings,
            )

        # Update slash commands in all agent directories (overwrite existing)
        agent_dirs = [
            (project_path / ".claude" / "commands", "md", "Claude"),
            (project_path / ".codex" / "prompts", "md", "Codex"),
            (project_path / ".opencode" / "command", "md", "OpenCode"),
        ]

        total_updated = 0
        for agent_dir, extension, agent_name in agent_dirs:
            if not agent_dir.exists():
                continue

            updated_count = 0
            for template_path in sorted(command_templates_dir.glob("*.md")):
                filename = f"spec-kitty.{template_path.stem}.{extension}"
                dest_path = agent_dir / filename

                if dry_run:
                    changes.append(f"Would update {agent_name}: {dest_path.name}")
                else:
                    dest_path.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")
                    updated_count += 1

            if updated_count > 0:
                changes.append(f"Updated {updated_count} slash commands for {agent_name}")
                total_updated += updated_count

        if total_updated > 0:
            changes.append(f"Total: Updated {total_updated} slash commands from {mission_name} mission")
            changes.append("Slash commands now use Python CLI (no bash scripts)")
            changes.append("Slash commands now enforce flat tasks/ structure (feature 007)")

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )
