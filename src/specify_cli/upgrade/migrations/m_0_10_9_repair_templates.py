"""Migration: Repair broken templates for users affected by #62, #63, #64."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class RepairTemplatesMigration(BaseMigration):
    """Repair templates for projects with broken bash script references.

    This migration addresses issues #62, #63, #64 where PyPI installations
    received outdated templates with bash script references. It detects
    broken templates and regenerates them from the correct source.
    """

    migration_id = "0.10.9_repair_templates"
    description = "Repair broken templates with bash script references"
    target_version = "0.10.9"

    def detect(self, project_path: Path) -> bool:
        """Detect if project has broken templates with bash script references."""
        # Check all agent directories for broken slash commands
        agent_dirs = [
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

        for agent_dir, subdir in agent_dirs:
            commands_dir = project_path / agent_dir / subdir
            if not commands_dir.exists():
                continue

            # Check for bash script references in any command file
            for cmd_file in commands_dir.glob("spec-kitty.*.md"):
                try:
                    content = cmd_file.read_text(encoding="utf-8")
                    if "scripts/bash/" in content or "scripts/powershell/" in content:
                        return True  # Found broken template
                except Exception:
                    # Skip files we can't read
                    continue

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Migration can always be applied if broken templates detected."""
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Regenerate templates from correct source."""
        changes: List[str] = []
        errors: List[str] = []
        warnings: List[str] = []

        # Step 1: Remove broken templates from .kittify/templates/
        kittify_templates = project_path / ".kittify" / "templates"
        if kittify_templates.exists():
            if not dry_run:
                shutil.rmtree(kittify_templates)
                changes.append("Removed broken templates from .kittify/templates/")
            else:
                changes.append("Would remove broken templates from .kittify/templates/")

        # Step 2: Copy correct templates from package
        try:
            # Import here to avoid circular dependencies
            from specify_cli.template.manager import (
                get_local_repo_root,
                copy_specify_base_from_local,
                copy_specify_base_from_package,
            )

            local_repo = get_local_repo_root()
            command_templates_dir = None

            if local_repo:
                # For local dev, get templates from .kittify/templates/
                if not dry_run:
                    command_templates_dir = copy_specify_base_from_local(
                        local_repo, project_path, "sh"
                    )
                    changes.append("Copied correct templates from local repo")
                else:
                    changes.append("Would copy correct templates from local repo")
            else:
                # For package install, use bundled templates (now fixed)
                if not dry_run:
                    command_templates_dir = copy_specify_base_from_package(
                        project_path, "sh"
                    )
                    changes.append("Copied correct templates from package")
                else:
                    changes.append("Would copy correct templates from package")

            # Step 3: Regenerate all agent slash commands
            if not dry_run and command_templates_dir:
                # Import here to avoid circular dependencies
                from specify_cli.cli.commands.init import generate_agent_assets
                import yaml

                # Get AI configuration from metadata
                metadata_file = project_path / ".kittify" / "metadata.yaml"
                ai_config = "claude"  # default
                if metadata_file.exists():
                    try:
                        with open(metadata_file, encoding="utf-8") as f:
                            metadata = yaml.safe_load(f)
                            ai_config = metadata.get("ai", "claude")
                    except Exception:
                        # Use default if we can't read metadata
                        pass

                # Regenerate commands
                try:
                    generate_agent_assets(
                        command_templates_dir=command_templates_dir,
                        project_path=project_path,
                        agent_key=ai_config,
                        script_type="sh"
                    )
                    changes.append("Regenerated all agent slash commands")
                except Exception as e:
                    errors.append(f"Failed to regenerate agent commands: {e}")

                # Cleanup temporary templates
                if kittify_templates.exists():
                    shutil.rmtree(kittify_templates)
                    changes.append("Cleaned up temporary templates")
            else:
                changes.append("Would regenerate all agent slash commands")

        except Exception as e:
            errors.append(f"Failed to repair templates: {e}")

        # Step 4: Verify repair
        if not dry_run and len(errors) == 0:
            still_broken = self.detect(project_path)
            if still_broken:
                warnings.append(
                    "Some bash script references may still remain. "
                    "Please run 'spec-kitty upgrade' again or report an issue."
                )
            else:
                changes.append("✓ Templates successfully repaired - no bash script references found")

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )
