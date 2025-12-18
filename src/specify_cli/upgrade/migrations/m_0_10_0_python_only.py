"""Migration: Remove bash scripts and update templates to use Python CLI."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class PythonOnlyMigration(BaseMigration):
    """Migrate from bash scripts to Python-only CLI commands.

    As of v0.10.0, all spec-kitty commands are available through the
    `spec-kitty agent` CLI namespace. Bash wrapper scripts in
    `.kittify/scripts/bash/` are replaced with Python implementations.

    This migration:
    1. Detects and removes bash scripts from .kittify/scripts/bash/
    2. Updates slash command templates to use `spec-kitty agent` commands
    3. Cleans up bash scripts in worktrees
    4. Detects custom modifications and warns users
    5. Is idempotent (safe to run multiple times)
    """

    migration_id = "0.10.0_python_only"
    description = "Remove bash scripts and update templates to use Python CLI"
    target_version = "0.10.0"

    # Bash scripts that should be removed (package scripts only)
    PACKAGE_SCRIPTS = (
        "common.sh",
        "create-new-feature.sh",
        "check-prerequisites.sh",
        "setup-plan.sh",
        "update-agent-context.sh",
        "accept-feature.sh",
        "merge-feature.sh",
        "tasks-move-to-lane.sh",
        "tasks-list-lanes.sh",
        "mark-task-status.sh",
        "tasks-add-history-entry.sh",
        "tasks-rollback-move.sh",
        "validate-task-workflow.sh",
        "move-task-to-doing.sh",
    )

    # Bash → Python command mappings for template updates
    COMMAND_REPLACEMENTS = {
        # Feature management
        r"\.kittify/scripts/bash/create-new-feature\.sh": "spec-kitty agent create-feature",
        r"scripts/bash/create-new-feature\.sh": "spec-kitty agent create-feature",
        r"\.kittify/scripts/bash/check-prerequisites\.sh": "spec-kitty agent check-prerequisites",
        r"scripts/bash/check-prerequisites\.sh": "spec-kitty agent check-prerequisites",
        r"\.kittify/scripts/bash/setup-plan\.sh": "spec-kitty agent setup-plan",
        r"scripts/bash/setup-plan\.sh": "spec-kitty agent setup-plan",
        r"\.kittify/scripts/bash/update-agent-context\.sh": "spec-kitty agent update-context",
        r"scripts/bash/update-agent-context\.sh": "spec-kitty agent update-context",
        r"\.kittify/scripts/bash/accept-feature\.sh": "spec-kitty agent feature accept",
        r"scripts/bash/accept-feature\.sh": "spec-kitty agent feature accept",
        r"\.kittify/scripts/bash/merge-feature\.sh": "spec-kitty agent feature merge",
        r"scripts/bash/merge-feature\.sh": "spec-kitty agent feature merge",

        # Task workflow
        r"\.kittify/scripts/bash/tasks-move-to-lane\.sh": "spec-kitty agent move-task",
        r"scripts/bash/tasks-move-to-lane\.sh": "spec-kitty agent move-task",
        r"\.kittify/scripts/bash/tasks-list-lanes\.sh": "spec-kitty agent list-tasks",
        r"scripts/bash/tasks-list-lanes\.sh": "spec-kitty agent list-tasks",
        r"\.kittify/scripts/bash/mark-task-status\.sh": "spec-kitty agent mark-status",
        r"scripts/bash/mark-task-status\.sh": "spec-kitty agent mark-status",
        r"\.kittify/scripts/bash/tasks-add-history-entry\.sh": "spec-kitty agent add-history",
        r"scripts/bash/tasks-add-history-entry\.sh": "spec-kitty agent add-history",
        r"\.kittify/scripts/bash/tasks-rollback-move\.sh": "spec-kitty agent rollback-move",
        r"scripts/bash/tasks-rollback-move\.sh": "spec-kitty agent rollback-move",
        r"\.kittify/scripts/bash/validate-task-workflow\.sh": "spec-kitty agent validate-workflow",
        r"scripts/bash/validate-task-workflow\.sh": "spec-kitty agent validate-workflow",
        r"\.kittify/scripts/bash/move-task-to-doing\.sh": "spec-kitty agent move-task",
        r"scripts/bash/move-task-to-doing\.sh": "spec-kitty agent move-task",

        # Legacy tasks_cli.py references
        r"tasks_cli\.py move": "spec-kitty agent move-task",
        r"tasks_cli\.py list": "spec-kitty agent list-tasks",
        r"tasks_cli\.py mark": "spec-kitty agent mark-status",
        r"tasks_cli\.py history": "spec-kitty agent add-history",
        r"tasks_cli\.py rollback": "spec-kitty agent rollback-move",
        r"tasks_cli\.py validate": "spec-kitty agent validate-workflow",
    }

    def detect(self, project_path: Path) -> bool:
        """Check if bash scripts still exist in user's .kittify directory."""
        kittify_bash = project_path / ".kittify" / "scripts" / "bash"

        if not kittify_bash.exists():
            return False

        # Check if ANY .sh files exist (not just known scripts)
        # This catches custom scripts and ensures complete cleanup
        bash_scripts = list(kittify_bash.glob("*.sh"))
        return len(bash_scripts) > 0

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Migration can always be applied if bash scripts are detected."""
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Remove bash scripts and update templates."""
        changes: List[str] = []
        warnings: List[str] = []
        errors: List[str] = []

        # Step 1: Detect and remove bash scripts from .kittify
        bash_changes, bash_warnings = self._remove_bash_scripts(
            project_path, dry_run
        )
        changes.extend(bash_changes)
        warnings.extend(bash_warnings)

        # Step 2: Clean up bash scripts in worktrees
        worktree_changes = self._cleanup_worktree_bash_scripts(
            project_path, dry_run
        )
        changes.extend(worktree_changes)

        # Step 3: Update slash command templates
        template_changes, template_errors = self._update_command_templates(
            project_path, dry_run
        )
        changes.extend(template_changes)
        errors.extend(template_errors)

        # Note: Custom script detection now happens in _remove_bash_scripts()
        # before deletion, so users get warnings about custom scripts

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )

    def _remove_bash_scripts(
        self, project_path: Path, dry_run: bool
    ) -> Tuple[List[str], List[str]]:
        """Remove bash scripts from .kittify/scripts/bash/."""
        changes: List[str] = []
        warnings: List[str] = []

        kittify_bash = project_path / ".kittify" / "scripts" / "bash"

        if not kittify_bash.exists():
            warnings.append("No .kittify/scripts/bash/ directory found - already migrated?")
            return changes, warnings

        # First, detect custom scripts (not in PACKAGE_SCRIPTS) and warn user
        all_bash_scripts = list(kittify_bash.glob("*.sh"))
        custom_scripts = [s for s in all_bash_scripts if s.name not in self.PACKAGE_SCRIPTS]

        if custom_scripts:
            custom_names = [s.name for s in custom_scripts]
            warnings.append(f"Custom bash scripts detected: {', '.join(custom_names)}")
            warnings.append(
                "These custom scripts will be removed as part of the migration to Python-only. "
                "If you need this functionality, please migrate it manually before upgrading."
            )

        # Now delete ALL .sh files (including custom ones)
        # This ensures complete cleanup, matching PowerShell/worktree behavior
        scripts_removed = len(all_bash_scripts)

        for script in all_bash_scripts:
            if dry_run:
                changes.append(f"Would remove: .kittify/scripts/bash/{script.name}")
            else:
                script.unlink()
                changes.append(f"Removed: .kittify/scripts/bash/{script.name}")

        # Remove PowerShell equivalents if they exist
        kittify_ps = project_path / ".kittify" / "scripts" / "powershell"
        if kittify_ps.exists():
            ps_scripts = list(kittify_ps.glob("*.ps1"))
            if ps_scripts:
                for ps_script in ps_scripts:
                    if dry_run:
                        changes.append(f"Would remove: .kittify/scripts/powershell/{ps_script.name}")
                    else:
                        ps_script.unlink()
                        changes.append(f"Removed: .kittify/scripts/powershell/{ps_script.name}")
                    scripts_removed += 1

        # Remove directories if empty
        if not dry_run:
            if kittify_bash.exists() and not any(kittify_bash.iterdir()):
                kittify_bash.rmdir()
                changes.append("Removed empty: .kittify/scripts/bash/")
            if kittify_ps.exists() and not any(kittify_ps.iterdir()):
                kittify_ps.rmdir()
                changes.append("Removed empty: .kittify/scripts/powershell/")

        if scripts_removed > 0:
            changes.append(f"Total scripts removed: {scripts_removed}")
        else:
            warnings.append("No bash scripts found to remove - already migrated?")

        return changes, warnings

    def _cleanup_worktree_bash_scripts(
        self, project_path: Path, dry_run: bool
    ) -> List[str]:
        """Remove bash scripts from all worktrees."""
        changes: List[str] = []

        worktrees_dir = project_path / ".worktrees"
        if not worktrees_dir.exists():
            return changes

        for worktree in sorted(worktrees_dir.iterdir()):
            if not worktree.is_dir():
                continue

            wt_bash = worktree / ".kittify" / "scripts" / "bash"
            if not wt_bash.exists():
                continue

            scripts_found = list(wt_bash.glob("*.sh"))
            if scripts_found:
                if dry_run:
                    changes.append(f"Would remove {len(scripts_found)} scripts from worktree: {worktree.name}")
                else:
                    for script in scripts_found:
                        script.unlink()
                    if not any(wt_bash.iterdir()):
                        wt_bash.rmdir()
                    changes.append(f"Removed {len(scripts_found)} scripts from worktree: {worktree.name}")

        return changes

    def _update_command_templates(
        self, project_path: Path, dry_run: bool
    ) -> Tuple[List[str], List[str]]:
        """Update slash command templates to use Python CLI."""
        changes: List[str] = []
        errors: List[str] = []

        # Templates in .kittify/templates/command-templates/
        templates_dir = project_path / ".kittify" / "templates" / "command-templates"

        if not templates_dir.exists():
            errors.append("Templates directory not found: .kittify/templates/command-templates/")
            return changes, errors

        templates_updated = 0
        for template_path in sorted(templates_dir.glob("*.md")):
            try:
                updated, replacements = self._update_template_file(
                    template_path, dry_run
                )
                if updated:
                    templates_updated += 1
                    if dry_run:
                        changes.append(f"Would update: {template_path.name} ({replacements} replacements)")
                    else:
                        changes.append(f"Updated: {template_path.name} ({replacements} replacements)")
            except Exception as e:
                errors.append(f"Error updating {template_path.name}: {e}")

        if templates_updated > 0:
            changes.append(f"Total templates updated: {templates_updated}")

        return changes, errors

    def _update_template_file(
        self, template_path: Path, dry_run: bool
    ) -> Tuple[bool, int]:
        """Update a single template file with bash → Python replacements."""
        content = template_path.read_text(encoding="utf-8")
        original_content = content
        replacements_made = 0

        # Apply all replacements
        for pattern, replacement in self.COMMAND_REPLACEMENTS.items():
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                replacements_made += count

        # Write if changes were made
        if content != original_content:
            if not dry_run:
                template_path.write_text(content, encoding="utf-8")
            return True, replacements_made

        return False, 0

    def _detect_custom_modifications(self, project_path: Path) -> List[str]:
        """Detect custom modifications to bash scripts."""
        warnings: List[str] = []

        kittify_bash = project_path / ".kittify" / "scripts" / "bash"
        if not kittify_bash.exists():
            return warnings

        # Look for non-standard scripts (not in PACKAGE_SCRIPTS)
        custom_scripts = []
        for script_path in kittify_bash.glob("*.sh"):
            if script_path.name not in self.PACKAGE_SCRIPTS:
                custom_scripts.append(script_path.name)

        if custom_scripts:
            warnings.append(
                f"Custom bash scripts detected: {', '.join(custom_scripts)}"
            )
            warnings.append(
                "These scripts will NOT be removed automatically. "
                "Please migrate them manually or remove if no longer needed."
            )

        return warnings
