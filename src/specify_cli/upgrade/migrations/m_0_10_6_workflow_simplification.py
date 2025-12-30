"""Migration: Simplify implement and review templates to use workflow commands."""

from __future__ import annotations

from pathlib import Path
from typing import List

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class WorkflowSimplificationMigration(BaseMigration):
    """Update implement and review slash commands to use new workflow commands.

    This migration simplifies the agent workflow by:
    1. Replacing complex implement.md template (78 lines) with minimal version (9 lines)
    2. Replacing complex review.md template (72 lines) with minimal version (9 lines)
    3. Templates now call `spec-kitty agent workflow implement/review` which:
       - Displays the full WP prompt directly to the agent
       - Shows clear "when done" instructions
       - No more file navigation or path confusion
    """

    migration_id = "0.10.6_workflow_simplification"
    description = "Simplify implement and review templates to use workflow commands"
    target_version = "0.10.6"

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
        """Check if slash commands need updating to workflow commands."""
        # Check if any agent directory has the old complex templates
        for agent_root, subdir in self.AGENT_DIRS:
            agent_dir = project_path / agent_root / subdir

            if not agent_dir.exists():
                continue

            # Check implement.md for old structure (looking for complex instructions)
            implement_file = agent_dir / "spec-kitty.implement.md"
            if implement_file.exists():
                content = implement_file.read_text(encoding="utf-8")
                # Old template has "Work Package Selection" or "Setup (Do This First)"
                if "Work Package Selection" in content or "Setup (Do This First)" in content:
                    return True
                # Or doesn't have the new workflow command
                if "spec-kitty agent workflow implement" not in content:
                    return True

            # Check review.md for old structure
            review_file = agent_dir / "spec-kitty.review.md"
            if review_file.exists():
                content = review_file.read_text(encoding="utf-8")
                # Old template has complex outline
                if "Location Pre-flight Check" in content or "Conduct the review:" in content:
                    return True
                # Or doesn't have the new workflow command
                if "spec-kitty agent workflow review" not in content:
                    return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if we have mission templates to copy from."""
        missions_dir = project_path / ".kittify" / "missions"
        if not missions_dir.exists():
            return False, "No missions directory found"

        # Look for software-dev mission with updated templates
        software_dev_templates = missions_dir / "software-dev" / "command-templates"
        if software_dev_templates.exists():
            # Check if templates have the new workflow commands
            implement = software_dev_templates / "implement.md"
            if implement.exists():
                content = implement.read_text(encoding="utf-8")
                if "spec-kitty agent workflow implement" in content:
                    return True, ""

        return False, "Mission templates not updated with workflow commands"

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Update implement and review slash commands with new workflow-based templates."""
        changes: List[str] = []
        warnings: List[str] = []
        errors: List[str] = []

        missions_dir = project_path / ".kittify" / "missions"
        software_dev_templates = missions_dir / "software-dev" / "command-templates"

        if not software_dev_templates.exists():
            errors.append("No software-dev mission templates found")
            return MigrationResult(
                success=False,
                changes_made=changes,
                errors=errors,
                warnings=warnings,
            )

        # Update implement.md and review.md in ALL agent directories
        templates_to_update = ["implement.md", "review.md"]
        total_updated = 0

        for agent_root, subdir in self.AGENT_DIRS:
            agent_dir = project_path / agent_root / subdir

            if not agent_dir.exists():
                continue

            updated_count = 0
            for template_name in templates_to_update:
                source_template = software_dev_templates / template_name
                if not source_template.exists():
                    continue

                dest_filename = f"spec-kitty.{template_name}"
                dest_path = agent_dir / dest_filename

                if dry_run:
                    changes.append(f"Would update {agent_root}: {dest_filename}")
                else:
                    dest_path.write_text(source_template.read_text(encoding="utf-8"), encoding="utf-8")
                    updated_count += 1

            if updated_count > 0:
                agent_name = agent_root.strip(".")
                changes.append(f"Updated {updated_count} templates for {agent_name}")
                total_updated += updated_count

        if total_updated > 0:
            changes.append(f"Total: Updated {total_updated} slash command templates")
            changes.append("Templates now use 'spec-kitty agent workflow' commands")
            changes.append("Agents now see prompts directly, no file navigation needed")

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )
