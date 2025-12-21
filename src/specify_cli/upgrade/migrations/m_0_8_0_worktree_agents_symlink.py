"""Migration: Create AGENTS.md and templates symlinks in worktrees."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class WorktreeAgentsSymlinkMigration(BaseMigration):
    """Create .kittify/AGENTS.md and .kittify/templates symlinks in worktrees.

    Worktrees need access to the main repo's .kittify/AGENTS.md file
    and .kittify/templates/ directory for command templates that reference them.
    Since .kittify/ is gitignored, worktrees don't automatically have them.

    This migration creates symlinks from each worktree's .kittify/AGENTS.md
    and .kittify/templates/ to the main repo's corresponding directories.
    """

    migration_id = "0.8.0_worktree_agents_symlink"
    description = "Create .kittify/AGENTS.md and templates symlinks in worktrees"
    target_version = "0.8.0"

    def detect(self, project_path: Path) -> bool:
        """Check if any worktrees are missing .kittify/AGENTS.md or templates."""
        worktrees_dir = project_path / ".worktrees"
        main_agents = project_path / ".kittify" / "AGENTS.md"
        main_templates = project_path / ".kittify" / "templates"

        # No main resources means nothing to symlink
        if not main_agents.exists() and not main_templates.exists():
            return False

        if not worktrees_dir.exists():
            return False

        for worktree in worktrees_dir.iterdir():
            if worktree.is_dir() and not worktree.name.startswith('.'):
                wt_agents = worktree / ".kittify" / "AGENTS.md"
                wt_templates = worktree / ".kittify" / "templates"
                
                # Check if AGENTS.md is missing or broken
                if main_agents.exists():
                    if not wt_agents.exists() and not wt_agents.is_symlink():
                        return True
                    if wt_agents.is_symlink() and not wt_agents.exists():
                        return True
                
                # Check if templates is missing or broken
                if main_templates.exists():
                    if not wt_templates.exists() and not wt_templates.is_symlink():
                        return True
                    if wt_templates.is_symlink() and not wt_templates.exists():
                        return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check that main repo has AGENTS.md and/or templates."""
        main_agents = project_path / ".kittify" / "AGENTS.md"
        main_templates = project_path / ".kittify" / "templates"

        if not main_agents.exists() and not main_templates.exists():
            return (
                False,
                "Main repo .kittify/AGENTS.md or templates must exist before creating symlinks"
            )
        return (True, "")

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Create .kittify/AGENTS.md and templates symlinks in all worktrees."""
        changes = []
        errors = []
        warnings = []

        worktrees_dir = project_path / ".worktrees"
        main_agents = project_path / ".kittify" / "AGENTS.md"
        main_templates = project_path / ".kittify" / "templates"

        if not main_agents.exists() and not main_templates.exists():
            warnings.append("Main repo .kittify/AGENTS.md and templates not found, skipping")
            return MigrationResult(
                success=True,
                changes_made=[],
                errors=[],
                warnings=warnings,
            )

        if worktrees_dir.exists():
            for worktree in worktrees_dir.iterdir():
                if worktree.is_dir() and not worktree.name.startswith('.'):
                    wt_kittify = worktree / ".kittify"
                    wt_agents = wt_kittify / "AGENTS.md"
                    wt_templates = wt_kittify / "templates"

                    # Handle AGENTS.md symlink
                    if main_agents.exists():
                        # Skip if already exists and is valid
                        if wt_agents.exists() and not wt_agents.is_symlink():
                            warnings.append(
                                f"Worktree {worktree.name} has non-symlink AGENTS.md, skipping"
                            )
                        elif wt_agents.is_symlink() and wt_agents.exists():
                            # Valid symlink already exists
                            pass
                        else:
                            # Create AGENTS.md symlink
                            relative_path = "../../../.kittify/AGENTS.md"
                            if dry_run:
                                changes.append(
                                    f"Would create .kittify/AGENTS.md symlink in worktree {worktree.name}"
                                )
                            else:
                                try:
                                    wt_kittify.mkdir(parents=True, exist_ok=True)
                                    if wt_agents.is_symlink():
                                        wt_agents.unlink()
                                    
                                    original_cwd = os.getcwd()
                                    try:
                                        os.chdir(wt_kittify)
                                        os.symlink(relative_path, "AGENTS.md")
                                    finally:
                                        os.chdir(original_cwd)

                                    changes.append(
                                        f"Created .kittify/AGENTS.md symlink in worktree {worktree.name}"
                                    )
                                except OSError as e:
                                    # Symlink failed (Windows?), try copying instead
                                    try:
                                        shutil.copy2(main_agents, wt_agents)
                                        changes.append(
                                            f"Copied .kittify/AGENTS.md to worktree {worktree.name} (symlink failed)"
                                        )
                                    except OSError as copy_error:
                                        errors.append(
                                            f"Failed to create AGENTS.md in {worktree.name}: {e}, copy also failed: {copy_error}"
                                        )

                    # Handle templates/ symlink
                    if main_templates.exists():
                        # Skip if already exists and is valid
                        if wt_templates.exists() and not wt_templates.is_symlink():
                            warnings.append(
                                f"Worktree {worktree.name} has non-symlink templates, skipping"
                            )
                        elif wt_templates.is_symlink() and wt_templates.exists():
                            # Valid symlink already exists
                            pass
                        else:
                            # Create templates symlink
                            relative_path = "../../../.kittify/templates"
                            if dry_run:
                                changes.append(
                                    f"Would create .kittify/templates symlink in worktree {worktree.name}"
                                )
                            else:
                                try:
                                    wt_kittify.mkdir(parents=True, exist_ok=True)
                                    if wt_templates.is_symlink():
                                        wt_templates.unlink()
                                    elif wt_templates.exists():
                                        try:
                                            shutil.rmtree(wt_templates)
                                        except OSError as remove_error:
                                            errors.append(
                                                f"Failed to remove existing templates directory in worktree {worktree.name}: {remove_error}"
                                            )
                                            continue
                                    
                                    original_cwd = os.getcwd()
                                    try:
                                        os.chdir(wt_kittify)
                                        os.symlink(relative_path, "templates", target_is_directory=True)
                                    finally:
                                        os.chdir(original_cwd)

                                    changes.append(
                                        f"Created .kittify/templates symlink in worktree {worktree.name}"
                                    )
                                except OSError as e:
                                    # Symlink failed (Windows?), try copying instead
                                    try:
                                        shutil.copytree(main_templates, wt_templates, dirs_exist_ok=True)
                                        changes.append(
                                            f"Copied .kittify/templates to worktree {worktree.name} (symlink failed)"
                                        )
                                    except OSError as copy_error:
                                        errors.append(
                                            f"Failed to create templates in {worktree.name}: {e}, copy also failed: {copy_error}"
                                        )

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )

