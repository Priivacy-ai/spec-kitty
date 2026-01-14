"""Migration: Update workflow templates with end-of-output instructions."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class ImprovedWorkflowTemplatesMigration(BaseMigration):
    """Update implement and review templates with improved agent guidance.

    This migration addresses workflow command state corruption issues by:
    1. Warning agents about long output (1000+ lines)
    2. Instructing agents to scroll to bottom for completion commands
    3. Emphasizing that Python scripts handle all file updates automatically
    4. Removing manual file editing requirements from instructions

    The workflow.py commands now repeat completion instructions at the END
    of output, after the long WP prompt content.
    """

    migration_id = "0.11.2_improved_workflow_templates"
    description = "Update workflow templates with end-of-output instructions and --agent requirement"
    target_version = "0.11.2"

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
        """Check if slash commands need updating with improved guidance."""
        # Check if any agent directory has the old templates (without scroll warning)
        for agent_root, subdir in self.AGENT_DIRS:
            agent_dir = project_path / agent_root / subdir

            if not agent_dir.exists():
                continue

            # Check implement.md for new structure
            implement_file = agent_dir / "spec-kitty.implement.md"
            if implement_file.exists():
                content = implement_file.read_text(encoding="utf-8")
                # New template has warning about scrolling to bottom
                if "scroll to the BOTTOM" not in content.lower():
                    return True

            # Check review.md for new structure
            review_file = agent_dir / "spec-kitty.review.md"
            if review_file.exists():
                content = review_file.read_text(encoding="utf-8")
                # New template has warning about scrolling to bottom
                if "scroll to the BOTTOM" not in content.lower():
                    return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if we can apply this migration."""
        kittify_dir = project_path / ".kittify"
        if not kittify_dir.exists():
            return False, "No .kittify directory (not a spec-kitty project)"

        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Update implement and review slash commands with improved templates."""
        changes: List[str] = []
        warnings: List[str] = []
        errors: List[str] = []

        missions_dir = project_path / ".kittify" / "missions"
        software_dev_templates = missions_dir / "software-dev" / "command-templates"

        # Copy updated mission templates from package first (if available)
        try:
            import specify_cli
        except ImportError as exc:
            errors.append(f"Failed to import specify_cli: {exc}")
            return MigrationResult(
                success=False,
                changes_made=changes,
                errors=errors,
                warnings=warnings,
            )

        pkg_root = Path(specify_cli.__file__).parent
        pkg_templates = pkg_root / "missions" / "software-dev" / "command-templates"
        if not pkg_templates.exists():
            pkg_templates = pkg_root / ".kittify" / "missions" / "software-dev" / "command-templates"

        if pkg_templates.exists():
            if not dry_run:
                software_dev_templates.mkdir(parents=True, exist_ok=True)
            for template_name in ("implement.md", "review.md"):
                src = pkg_templates / template_name
                if not src.exists():
                    warnings.append(f"Package template missing: {template_name}")
                    continue
                if dry_run:
                    changes.append(f"Would update mission template: software-dev/{template_name}")
                else:
                    try:
                        shutil.copy2(src, software_dev_templates / template_name)
                        changes.append(f"Updated mission template: software-dev/{template_name}")
                    except OSError as e:
                        warnings.append(f"Failed to copy mission template {template_name}: {e}")
        else:
            warnings.append(
                "Mission templates not found in package. "
                "Slash commands may already be updated or require manual repair."
            )

        # Update implement.md and review.md in ALL agent directories
        templates_to_update = ["implement.md", "review.md"]
        total_updated = 0

        for agent_root, subdir in self.AGENT_DIRS:
            agent_dir = project_path / agent_root / subdir

            # Create agent directory if it doesn't exist (for new agents)
            if not agent_dir.exists():
                if not dry_run:
                    agent_dir.mkdir(parents=True, exist_ok=True)
                    changes.append(f"Created {agent_root}/{subdir} directory")

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
                    try:
                        dest_path.write_text(
                            source_template.read_text(encoding="utf-8"),
                            encoding="utf-8",
                        )
                        updated_count += 1
                    except OSError as e:
                        warnings.append(f"Failed to update {agent_root}/{dest_filename}: {e}")

            if updated_count > 0:
                agent_name = agent_root.strip(".")
                changes.append(f"Updated {updated_count} templates for {agent_name}")
                total_updated += updated_count

        if total_updated > 0:
            changes.append(f"Total: Updated {total_updated} slash command templates across all agents")
            changes.append("Templates now warn agents to scroll to bottom of long output")
            changes.append("Templates emphasize automated file updates (no manual editing)")
            changes.append("Prevents state corruption from incomplete workflows")
        elif not changes:
            warnings.append(
                "No templates were updated (already updated or mission templates missing)"
            )

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )
