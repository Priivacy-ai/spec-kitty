"""Migration: Fix charter.md next-step suggestion across all agents.

This migration updates the charter.md template to suggest /spec-kitty.specify
instead of /spec-kitty.plan as the next step after creating a project charter.
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
class UpdateCharterTemplatesMigration(BaseMigration):
    """Fix charter.md next-step suggestion across all agents.

    This migration:
    1. Loads the canonical charter.md template from packaged missions
    2. Copies it to all agent slash command directories
    3. Updates the "Next steps" text to suggest /spec-kitty.specify
    4. Only processes software-dev mission templates
    """

    migration_id = "0.13.0_update_charter_templates"
    description = "Fix charter next-step to /spec-kitty.specify"
    target_version = "0.13.0"

    MISSION_NAME = "software-dev"
    TEMPLATE_FILE = "charter.md"
    SLASH_COMMAND_FILE = "spec-kitty.charter.md"

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
        """Update charter slash command across all agent directories."""
        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        # Load template from packaged missions
        try:
            data_root = files("specify_cli")
            template_path = data_root.joinpath("missions", self.MISSION_NAME, "command-templates", self.TEMPLATE_FILE)

            if not template_path.is_file():
                errors.append("Charter template not found in packaged missions")
                return MigrationResult(
                    success=False,
                    changes_made=changes,
                    errors=errors,
                    warnings=warnings,
                )

            template_content = template_path.read_text(encoding="utf-8")
        except Exception as e:
            errors.append(f"Failed to read charter template: {e}")
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
                changes.append(f"Would update {agents_updated} agent charter templates")
            else:
                changes.append(f"Updated {agents_updated} agent charter templates")
        else:
            changes.append("No agent charter templates needed updates")

        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )
