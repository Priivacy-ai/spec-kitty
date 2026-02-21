"""Migration: Add missing task-prompt-template.md and tasks.md to research mission.

This migration fixes a bug where research missions were missing:
1. task-prompt-template.md - The YAML frontmatter template for WP files
2. tasks.md command template - Instructions for generating WP files

Without these templates, LLMs generating research WP files created files
with **Status**: in the markdown body instead of lane: in YAML frontmatter,
causing the review command to not find WPs ready for review.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class ResearchMissionTemplatesMigration(BaseMigration):
    """Add missing templates to research mission.

    This fixes the bug where:
    - Research WP files used **Status**: for_review in markdown body
    - Review command expected lane: "for_review" in YAML frontmatter

    The fix adds:
    - templates/task-prompt-template.md with proper YAML frontmatter
    - command-templates/tasks.md with instructions to use the template
    """

    migration_id = "0.9.2_research_mission_templates"
    description = "Add missing task-prompt-template.md and tasks.md to research mission"
    target_version = "0.9.2"

    # Files that should exist in the research mission
    REQUIRED_FILES = [
        ("templates", "task-prompt-template.md"),
        ("command-templates", "tasks.md"),
    ]

    def detect(self, project_path: Path) -> bool:
        """Check if research mission is missing required templates."""
        research_mission = project_path / ".kittify" / "missions" / "research"

        if not research_mission.exists():
            return False  # No research mission, nothing to fix

        for subdir, filename in self.REQUIRED_FILES:
            target = research_mission / subdir / filename
            if not target.exists():
                return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if we can copy templates from the package."""
        package_research = self._find_package_research_mission()
        if package_research is None:
            return (
                False,
                "Could not locate package research mission to copy templates from. "
                "This is expected in test environments. "
                "Run 'spec-kitty init --force' to repair missions manually.",
            )

        # Check that package has the required files
        missing_in_pkg = []
        for subdir, filename in self.REQUIRED_FILES:
            src = package_research / subdir / filename
            if not src.exists():
                missing_in_pkg.append(f"{subdir}/{filename}")

        if missing_in_pkg:
            return (
                False,
                f"Package research mission is missing: {', '.join(missing_in_pkg)}. "
                "Please upgrade spec-kitty-cli to the latest version.",
            )

        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Copy missing templates from the package."""
        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        research_mission = project_path / ".kittify" / "missions" / "research"
        package_research = self._find_package_research_mission()

        if package_research is None:
            errors.append("Could not locate package research mission")
            return MigrationResult(success=False, errors=errors)

        if not research_mission.exists():
            # No research mission in project, nothing to do
            return MigrationResult(
                success=True,
                changes_made=["Research mission not present, skipping"],
            )

        # Copy missing files
        for subdir, filename in self.REQUIRED_FILES:
            src = package_research / subdir / filename
            dest_dir = research_mission / subdir
            dest = dest_dir / filename

            if dest.exists():
                continue  # Already exists

            if dry_run:
                changes.append(f"Would add research/{subdir}/{filename}")
            else:
                try:
                    # Ensure directory exists
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)
                    changes.append(f"Added research/{subdir}/{filename}")
                except OSError as e:
                    errors.append(f"Failed to copy {subdir}/{filename}: {e}")

        # Also update worktrees
        worktrees_dir = project_path / ".worktrees"
        if worktrees_dir.exists():
            for worktree in worktrees_dir.iterdir():
                if not worktree.is_dir():
                    continue

                wt_research = worktree / ".kittify" / "missions" / "research"
                if not wt_research.exists():
                    continue

                for subdir, filename in self.REQUIRED_FILES:
                    src = package_research / subdir / filename
                    dest_dir = wt_research / subdir
                    dest = dest_dir / filename

                    if dest.exists():
                        continue

                    if dry_run:
                        changes.append(f"Would add research/{subdir}/{filename} to worktree {worktree.name}")
                    else:
                        try:
                            dest_dir.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(src, dest)
                            changes.append(f"Added research/{subdir}/{filename} to worktree {worktree.name}")
                        except OSError as e:
                            warnings.append(f"Could not copy to worktree {worktree.name}: {e}")

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )

    def _find_package_research_mission(self) -> Path | None:
        """Find the research mission directory in the installed package or local repo."""
        # First try from installed package
        try:
            from importlib.resources import files

            pkg_files = files("specify_cli")
            missions_path = pkg_files.joinpath("missions", "research")

            # Convert to Path and check if it exists
            missions_str = str(missions_path)
            if Path(missions_str).exists():
                return Path(missions_str)

        except (ImportError, TypeError, AttributeError):
            pass

        # Try from package __file__ location
        try:
            import specify_cli

            pkg_dir = Path(specify_cli.__file__).parent
            research_dir = pkg_dir / "missions" / "research"
            if research_dir.exists():
                return research_dir
        except (ImportError, AttributeError):
            pass

        # Fallback for development: Check SPEC_KITTY_TEMPLATE_ROOT env var
        import os

        template_root = os.environ.get("SPEC_KITTY_TEMPLATE_ROOT")
        if template_root:
            research_dir = Path(template_root) / ".kittify" / "missions" / "research"
            if research_dir.exists():
                return research_dir

        # Fallback: Try to find the spec-kitty repo root
        try:
            cwd = Path.cwd()
            for parent in [cwd] + list(cwd.parents):
                research_dir = parent / "src" / "specify_cli" / "missions" / "research"
                pyproject = parent / "pyproject.toml"
                if research_dir.exists() and pyproject.exists():
                    try:
                        content = pyproject.read_text(encoding="utf-8-sig")
                        if "spec-kitty-cli" in content:
                            return research_dir
                    except OSError:
                        pass
        except OSError:
            pass

        return None
