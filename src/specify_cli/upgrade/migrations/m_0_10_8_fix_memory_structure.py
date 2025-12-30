"""Migration: Fix memory/ and AGENTS.md structure - move from root to .kittify/."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class FixMemoryStructureMigration(BaseMigration):
    """Move memory/ directory and AGENTS.md from root to .kittify/.

    Historical context: When spec-kitty was developed in a worktree, symlinks
    were created (.kittify/memory -> ../../../.kittify/memory) that became
    circular when merged to main. All code expects files in .kittify/ but some
    user projects may have them at root level.

    This migration:
    1. Moves memory/ from root to .kittify/memory/ (if needed)
    2. Removes broken .kittify/memory symlink (if exists)
    3. Ensures .kittify/AGENTS.md exists (not symlink)
    4. Updates worktrees to use proper .kittify/ paths
    """

    migration_id = "0.10.8_fix_memory_structure"
    description = "Move memory/ and AGENTS.md from root to .kittify/"
    target_version = "0.10.8"

    def detect(self, project_path: Path) -> bool:
        """Check if project has broken memory structure."""
        # Check for root-level memory/ directory
        root_memory = project_path / "memory"
        kittify_memory = project_path / ".kittify" / "memory"

        # If root memory exists and .kittify/memory doesn't (or is a broken symlink)
        if root_memory.exists() and root_memory.is_dir():
            if not kittify_memory.exists():
                return True
            if kittify_memory.is_symlink() and not kittify_memory.resolve().exists():
                return True  # Broken symlink

        # Check for broken .kittify/memory symlink
        if kittify_memory.is_symlink():
            try:
                # Try to resolve - if it points to itself or doesn't exist, it's broken
                resolved = kittify_memory.resolve()
                if not resolved.exists() or resolved == kittify_memory:
                    return True
            except (OSError, RuntimeError):
                return True  # Circular symlink or resolution error

        # Check for broken .kittify/AGENTS.md symlink
        kittify_agents = project_path / ".kittify" / "AGENTS.md"
        if kittify_agents.is_symlink():
            try:
                resolved = kittify_agents.resolve()
                if not resolved.exists() or resolved == kittify_agents:
                    return True
            except (OSError, RuntimeError):
                return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if migration can be safely applied."""
        root_memory = project_path / "memory"
        kittify_dir = project_path / ".kittify"

        # .kittify must exist
        if not kittify_dir.exists():
            return False, ".kittify directory must exist before migration"

        # If root memory exists, we can migrate it
        if root_memory.exists() and root_memory.is_dir():
            return True, "Ready to migrate memory/ to .kittify/"

        # If broken symlinks exist, we can fix them
        kittify_memory = kittify_dir / "memory"
        kittify_agents = kittify_dir / "AGENTS.md"

        if kittify_memory.is_symlink() or kittify_agents.is_symlink():
            return True, "Ready to fix broken symlinks"

        return True, "Ready to apply"

    def apply(self, project_path: Path, *, dry_run: bool = False) -> MigrationResult:
        """Move memory/ and fix broken symlinks."""
        warnings: List[str] = []
        changes_made: List[str] = []

        root_memory = project_path / "memory"
        kittify_dir = project_path / ".kittify"
        kittify_memory = kittify_dir / "memory"
        kittify_agents = kittify_dir / "AGENTS.md"
        templates_agents = kittify_dir / "templates" / "AGENTS.md"

        # Step 1: Fix .kittify/memory
        if kittify_memory.exists():
            if kittify_memory.is_symlink():
                # Remove broken symlink
                if dry_run:
                    changes_made.append(f"Would remove broken symlink: {kittify_memory}")
                else:
                    kittify_memory.unlink()
                    changes_made.append(f"Removed broken symlink: {kittify_memory}")

        # Step 2: Move or copy root memory/ to .kittify/memory/
        if root_memory.exists() and root_memory.is_dir():
            if not kittify_memory.exists():
                if dry_run:
                    changes_made.append(f"Would move {root_memory} -> {kittify_memory}")
                else:
                    try:
                        # Move the directory
                        shutil.move(str(root_memory), str(kittify_memory))
                        changes_made.append(f"Moved {root_memory} -> {kittify_memory}")
                    except Exception as e:
                        # If move fails, try copy
                        try:
                            shutil.copytree(root_memory, kittify_memory)
                            changes_made.append(f"Copied {root_memory} -> {kittify_memory} (move failed: {e})")
                            warnings.append(f"Could not move (copied instead): {e}")
                        except Exception as copy_error:
                            return MigrationResult(
                                success=False,
                                changes_made=changes_made,
                                warnings=warnings,
                                errors=[f"Failed to move or copy memory/: {copy_error}"]
                            )
            else:
                warnings.append(f"{kittify_memory} already exists, skipping root memory/ migration")

        # Step 3: Create .kittify/memory/ from template if missing
        if not kittify_memory.exists():
            # Check if there's a template in missions
            template_constitution = None
            missions_dir = kittify_dir / "missions" / "software-dev"
            if missions_dir.exists():
                # Look for constitution template in command templates
                template_path = missions_dir / "command-templates" / "constitution.md"
                if not template_path.exists():
                    template_path = kittify_dir / "templates" / "command-templates" / "constitution.md"
                if template_path.exists():
                    template_constitution = template_path

            if template_constitution:
                if dry_run:
                    changes_made.append(f"Would create {kittify_memory} from template")
                else:
                    kittify_memory.mkdir(parents=True, exist_ok=True)
                    constitution_dest = kittify_memory / "constitution.md"
                    shutil.copy2(template_constitution, constitution_dest)
                    changes_made.append(f"Created {kittify_memory} from template")
            else:
                warnings.append(f"{kittify_memory} doesn't exist and no template found")

        # Step 4: Fix .kittify/AGENTS.md
        if kittify_agents.exists() and kittify_agents.is_symlink():
            # Remove broken symlink
            if dry_run:
                changes_made.append(f"Would remove broken symlink: {kittify_agents}")
            else:
                kittify_agents.unlink()
                changes_made.append(f"Removed broken symlink: {kittify_agents}")

        # Step 5: Create .kittify/AGENTS.md from template if missing
        if not kittify_agents.exists() or kittify_agents.is_symlink():
            if templates_agents.exists():
                if dry_run:
                    changes_made.append(f"Would copy {templates_agents} -> {kittify_agents}")
                else:
                    shutil.copy2(templates_agents, kittify_agents)
                    changes_made.append(f"Copied {templates_agents} -> {kittify_agents}")
            else:
                warnings.append(f"No AGENTS.md template found at {templates_agents}")

        # Step 6: Update worktrees if they exist
        worktrees_dir = project_path / ".worktrees"
        if worktrees_dir.exists():
            for worktree_path in worktrees_dir.iterdir():
                if not worktree_path.is_dir():
                    continue

                wt_kittify = worktree_path / ".kittify"
                if not wt_kittify.exists():
                    continue

                wt_memory = wt_kittify / "memory"
                wt_agents = wt_kittify / "AGENTS.md"

                # Remove broken symlinks in worktrees
                if wt_memory.is_symlink():
                    try:
                        resolved = wt_memory.resolve()
                        if not resolved.exists() or resolved == wt_memory:
                            if dry_run:
                                changes_made.append(f"Would remove broken worktree symlink: {wt_memory}")
                            else:
                                wt_memory.unlink()
                                changes_made.append(f"Removed broken worktree symlink: {wt_memory}")
                    except (OSError, RuntimeError):
                        if not dry_run:
                            wt_memory.unlink()
                            changes_made.append(f"Removed broken worktree symlink: {wt_memory}")

                # Recreate worktree symlink to point to main repo's .kittify/memory
                if not wt_memory.exists() and kittify_memory.exists():
                    relative_path = Path("../../../.kittify/memory")
                    if dry_run:
                        changes_made.append(f"Would create worktree symlink: {wt_memory} -> {relative_path}")
                    else:
                        try:
                            wt_memory.symlink_to(relative_path, target_is_directory=True)
                            changes_made.append(f"Created worktree symlink: {wt_memory} -> {relative_path}")
                        except OSError:
                            # Fallback: copy instead of symlink
                            shutil.copytree(kittify_memory, wt_memory)
                            changes_made.append(f"Copied to worktree (symlink failed): {wt_memory}")

                # Fix AGENTS.md in worktree
                if wt_agents.is_symlink():
                    try:
                        resolved = wt_agents.resolve()
                        if not resolved.exists() or resolved == wt_agents:
                            if not dry_run:
                                wt_agents.unlink()
                    except (OSError, RuntimeError):
                        if not dry_run:
                            wt_agents.unlink()

                if not wt_agents.exists() and kittify_agents.exists():
                    relative_path = Path("../../../.kittify/AGENTS.md")
                    if dry_run:
                        changes_made.append(f"Would create worktree symlink: {wt_agents} -> {relative_path}")
                    else:
                        try:
                            wt_agents.symlink_to(relative_path)
                            changes_made.append(f"Created worktree symlink: {wt_agents} -> {relative_path}")
                        except OSError:
                            shutil.copy2(kittify_agents, wt_agents)
                            changes_made.append(f"Copied to worktree (symlink failed): {wt_agents}")

        return MigrationResult(
            success=True,
            changes_made=changes_made,
            warnings=warnings,
            errors=[]
        )
