"""Migration: Update /spec-kitty.implement slash command across all agents (0.10.14).

IMPORTANT: This is a backport of m_0_11_1_update_implement_slash_command.py
for the 0.10.x release stream. It addresses the same bug for users on 0.10.x
before they upgrade to 0.11.x.

This migration fixes a critical bug where the /spec-kitty.implement slash command
was severely outdated after the 0.10.0-0.10.13 releases.

Issue: The slash command only documented step 1 (display prompt via workflow command)
but did NOT tell agents to run step 2 (create worktree via implement command).

This caused agents to see the prompt but never create the workspace, resulting in
"no such file or directory" errors when trying to cd to .worktrees/.

Fix: Copy the correct implement.md template from packaged missions to all 12
agent directories.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Tuple

try:
    from importlib.resources import files
except ImportError:
    from importlib_resources import files  # type: ignore

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class UpdateImplementSlashCommandMigration_0_10_14(BaseMigration):
    """Update /spec-kitty.implement slash command to show 2-step workflow (0.10.x).

    This is a backport of the 0.11.1 migration for the 0.10.x release stream.
    """

    migration_id = "0.10.14_update_implement_slash_command"
    description = "Update /spec-kitty.implement slash command to show 2-step workflow (0.10.x backport)"
    target_version = "0.10.14"

    # All 12 supported agent directories (canonical list)
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

    MISSION_NAME = "software-dev"
    TEMPLATE_FILE = "implement.md"
    SLASH_COMMAND_FILE = "spec-kitty.implement.md"

    def detect(self, project_path: Path) -> bool:
        """Check if any agent has outdated implement slash command."""
        # Check for old single-step pattern that's missing the critical step 2
        old_pattern = "spec-kitty agent workflow implement $ARGUMENTS"

        for agent_dir, subdir in self.AGENT_DIRS:
            slash_cmd = project_path / agent_dir / subdir / self.SLASH_COMMAND_FILE
            if slash_cmd.exists():
                content = slash_cmd.read_text(encoding="utf-8")
                # If it has the old single-command pattern and NOT the two-step section
                if old_pattern in content and "CRITICAL: This is a TWO-STEP Command" not in content:
                    return True
                # If it's missing step 2 entirely
                if "spec-kitty implement WP##" not in content:
                    return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if we can read the template from packaged missions."""
        # For 0.10.x: Try packaged missions (should work post-0.10.8)
        try:
            data_root = files("specify_cli")
            template_path = data_root.joinpath(
                "missions", self.MISSION_NAME, "command-templates", self.TEMPLATE_FILE
            )
            if template_path.exists():
                return True, ""
        except Exception as e:
            return False, f"Cannot access packaged missions: {e}"

        # Fallback: Try legacy .kittify location (pre-0.11.0)
        legacy_path = project_path / ".kittify" / "missions" / self.MISSION_NAME / "command-templates" / self.TEMPLATE_FILE
        if legacy_path.exists():
            return True, ""

        return False, "Template not found in packaged missions or legacy location"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Update implement slash command across all agent directories."""
        changes: List[str] = []
        warnings: List[str] = []
        errors: List[str] = []

        # Load template from packaged missions or legacy location
        template_content = None
        template_source = None

        try:
            # Try packaged missions first (0.10.8+)
            data_root = files("specify_cli")
            template_path = data_root.joinpath(
                "missions", self.MISSION_NAME, "command-templates", self.TEMPLATE_FILE
            )

            if template_path.exists():
                template_content = template_path.read_text(encoding="utf-8")
                template_source = "packaged missions"
        except Exception:
            pass

        # Fallback to legacy location (pre-0.11.0)
        if not template_content:
            legacy_path = project_path / ".kittify" / "missions" / self.MISSION_NAME / "command-templates" / self.TEMPLATE_FILE
            if legacy_path.exists():
                template_content = legacy_path.read_text(encoding="utf-8")
                template_source = "legacy .kittify/missions"

        if not template_content:
            errors.append("Template not found in packaged missions or legacy location")
            return MigrationResult(
                success=False,
                changes_made=changes,
                errors=errors,
                warnings=warnings,
            )

        changes.append(f"Using template from: {template_source}")

        # Update all agent directories
        agents_updated = 0
        for agent_dir, subdir in self.AGENT_DIRS:
            agent_path = project_path / agent_dir / subdir
            slash_cmd = agent_path / self.SLASH_COMMAND_FILE

            # Skip if agent directory doesn't exist
            if not agent_path.exists():
                continue

            # Check if command needs updating
            needs_update = False
            if slash_cmd.exists():
                current_content = slash_cmd.read_text(encoding="utf-8")
                if current_content != template_content:
                    needs_update = True
            else:
                needs_update = True

            if needs_update:
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
                changes.append(f"Would update {agents_updated} agent directories")
            else:
                changes.append(f"Updated {agents_updated} agent directories")
        else:
            changes.append("No agent directories needed updates")

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )
