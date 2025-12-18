"""Migration: Populate missing slash commands from mission templates."""

from __future__ import annotations

from pathlib import Path
from typing import List

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class PopulateSlashCommandsMigration(BaseMigration):
    """Populate agent command directories from mission templates if missing.

    Some v0.9.x projects initialized before proper template extraction
    may have empty agent command directories. This migration ensures
    all projects have slash commands available.

    This migration:
    1. Checks if agent command directories are empty or missing slash commands
    2. Finds mission command templates (software-dev or active mission)
    3. Copies templates to all agent directories with spec-kitty. prefix
    4. Handles all 12 supported agents
    """

    migration_id = "0.10.1_populate_slash_commands"
    description = "Populate missing slash commands from mission templates"
    target_version = "0.10.1"

    # Canonical list from m_0_9_1 (all supported agents)
    AGENT_DIRS = [
        (".claude", "commands"),
        (".github", "prompts"),
        (".gemini", "commands"),
        (".cursor", "commands"),
        (".qwen", "commands"),
        (".opencode", "command"),
        (".windsurf", "workflows"),
        (".codex", "prompts"),
        (".kilocode", "workflows"),
        (".augment", "commands"),
        (".roo", "commands"),
        (".amazonq", "prompts"),
    ]

    def detect(self, project_path: Path) -> bool:
        """Check if slash commands are missing from agent directories."""
        # Check .claude/commands/ directory
        claude_commands = project_path / ".claude" / "commands"

        # If directory doesn't exist or is empty, migration needed
        if not claude_commands.exists():
            return True

        # Check if it has spec-kitty commands
        slash_commands = list(claude_commands.glob("spec-kitty.*.md"))
        if len(slash_commands) == 0:
            return True

        # If we have fewer than expected commands (should be ~10+), migration needed
        if len(slash_commands) < 8:
            return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if we have mission templates to copy from."""
        # Check for mission templates
        missions_dir = project_path / ".kittify" / "missions"
        if not missions_dir.exists():
            return False, "No missions directory found"

        # Look for software-dev mission (most common)
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
        """Populate slash commands from mission templates."""
        changes: List[str] = []
        warnings: List[str] = []
        errors: List[str] = []

        # Find mission templates
        missions_dir = project_path / ".kittify" / "missions"

        # Prefer software-dev, fallback to first available mission
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

        # Populate all agent command directories
        total_created = 0
        for agent_root, subdir in self.AGENT_DIRS:
            agent_dir = project_path / agent_root / subdir

            # Always create .claude/commands/, only create others if parent exists
            if agent_dir.parent.exists() or agent_root == ".claude":
                created = self._populate_agent_commands(
                    command_templates_dir,
                    agent_dir,
                    "md",
                    dry_run,
                    changes
                )
                if created > 0:
                    agent_name = agent_root.strip(".")
                    changes.append(f"Created {created} slash commands for {agent_name} from {mission_name}")
                    total_created += created

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )

    def _populate_agent_commands(
        self,
        templates_dir: Path,
        output_dir: Path,
        extension: str,
        dry_run: bool,
        changes: List[str]
    ) -> int:
        """Copy command templates to agent directory."""
        created_count = 0

        # Create directory if needed
        if not output_dir.exists():
            if dry_run:
                changes.append(f"Would create: {output_dir}")
            else:
                output_dir.mkdir(parents=True, exist_ok=True)
                changes.append(f"Created: {output_dir}")

        # Copy each template
        for template_path in sorted(templates_dir.glob("*.md")):
            filename = f"spec-kitty.{template_path.stem}.{extension}" if extension else f"spec-kitty.{template_path.stem}"
            dest_path = output_dir / filename

            # Skip if already exists
            if dest_path.exists():
                continue

            if dry_run:
                changes.append(f"Would create: {dest_path.name}")
            else:
                # Simple copy - no variable substitution needed for basic setup
                dest_path.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")
                changes.append(f"Created: {dest_path.name}")

            created_count += 1

        return created_count
