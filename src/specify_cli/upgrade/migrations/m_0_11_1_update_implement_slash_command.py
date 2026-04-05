"""Migration: Update /spec-kitty.implement slash command across all agents.

This migration fixes a critical bug where the /spec-kitty.implement slash command
drifted away from the packaged workflow templates.

Issue: The slash command only documented step 1 (display prompt via workflow command)
but did NOT tell agents to run step 2 (create worktree via implement command).

This caused agents to see the prompt but never create the workspace, resulting in
"no such file or directory" errors when trying to cd to .worktrees/.

Fix: Copy the correct implement.md template from packaged missions to all 12
agent directories.
"""

from __future__ import annotations

from pathlib import Path

try:
    from importlib.resources import files
except ImportError:
    from importlib_resources import files  # type: ignore

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult
from .m_0_9_1_complete_lane_migration import get_agent_dirs_for_project


@MigrationRegistry.register
class UpdateImplementSlashCommandMigration(BaseMigration):
    """Update /spec-kitty.implement slash command to show 2-step workflow.

    Earlier template changes updated mission templates but did NOT update agent
    slash commands. This migration copies the correct implement.md template
    from packaged missions to all agent directories.
    """

    migration_id = "0.11.1_update_implement_slash_command"
    description = "Update /spec-kitty.implement slash command to show 2-step workflow"
    target_version = "0.11.1"

    MISSION_NAME = "software-dev"
    TEMPLATE_FILE = "implement.md"
    SLASH_COMMAND_FILE = "spec-kitty.implement.md"

    def detect(self, project_path: Path) -> bool:  # noqa: ARG002
        """Always returns False — command templates removed in WP10 (canonical context architecture).

        Shim generation (spec-kitty agent shim) now replaces template-based agent commands.
        This migration is retained for history but is permanently inert.
        """
        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:  # noqa: ARG002
        """Always returns False — command templates removed in WP10."""
        return (
            False,
            "Command templates were removed in WP10 (canonical context architecture). "
            "Shim generation replaces template-based commands.",
        )

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Update implement slash command across all agent directories."""
        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        # Load template from packaged missions
        try:
            data_root = files("specify_cli")
            template_path = data_root.joinpath("missions", self.MISSION_NAME, "command-templates", self.TEMPLATE_FILE)

            if not template_path.exists():
                errors.append("Template not found in packaged missions")
                return MigrationResult(
                    success=False,
                    changes_made=changes,
                    errors=errors,
                    warnings=warnings,
                )

            template_content = template_path.read_text(encoding="utf-8")
        except Exception as e:
            errors.append(f"Failed to read template: {e}")
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
