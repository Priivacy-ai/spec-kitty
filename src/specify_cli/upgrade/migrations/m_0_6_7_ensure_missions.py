"""Migration: Ensure all missions are present in the project."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


@MigrationRegistry.register
class EnsureMissionsMigration(BaseMigration):
    """Ensure all required missions are present in the project.

    This migration addresses the bug in v0.6.5-0.6.6 where the software-dev
    mission was missing from PyPI packages due to symlink handling issues
    during build.

    It copies missing missions from the package to the project.
    """

    migration_id = "0.6.7_ensure_missions"
    description = "Ensure all required missions (software-dev, research) are present"
    target_version = "0.6.7"

    # Required missions that should always be present
    REQUIRED_MISSIONS = ["software-dev", "research"]

    def detect(self, project_path: Path) -> bool:
        """Check if any required missions are missing."""
        missions_dir = project_path / ".kittify" / "missions"

        if not missions_dir.exists():
            return True  # No missions directory at all

        for mission_name in self.REQUIRED_MISSIONS:
            mission_dir = missions_dir / mission_name
            if not mission_dir.exists():
                return True
            # Check for essential files
            if not (mission_dir / "mission.yaml").exists():
                return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if we can copy missions from the package."""
        # Try to find package missions
        package_missions = self._find_package_missions()
        if package_missions is None:
            # In test environments, package missions may not be available
            # Skip gracefully rather than blocking all upgrades
            return (
                False,
                "Could not locate package missions to copy from. "
                "This is expected in test environments. "
                "Run 'spec-kitty init --force' to repair missions manually.",
            )

        # Check we have all required missions in the package
        missing_in_pkg = []
        for mission_name in self.REQUIRED_MISSIONS:
            pkg_mission = package_missions / mission_name
            if not pkg_mission.exists():
                missing_in_pkg.append(mission_name)

        if missing_in_pkg:
            return (
                False,
                f"Package is missing missions: {', '.join(missing_in_pkg)}. "
                "Please upgrade spec-kitty-cli to the latest version.",
            )

        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Copy missing missions from the package."""
        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        missions_dir = project_path / ".kittify" / "missions"
        package_missions = self._find_package_missions()

        if package_missions is None:
            errors.append("Could not locate package missions")
            return MigrationResult(success=False, errors=errors)

        # Ensure missions directory exists
        if not missions_dir.exists():
            if dry_run:
                changes.append("Would create .kittify/missions/ directory")
            else:
                missions_dir.mkdir(parents=True, exist_ok=True)
                changes.append("Created .kittify/missions/ directory")

        # Copy missing missions
        for mission_name in self.REQUIRED_MISSIONS:
            dest_mission = missions_dir / mission_name
            src_mission = package_missions / mission_name

            if dest_mission.exists():
                # Check if it has essential files
                if (dest_mission / "mission.yaml").exists():
                    continue
                else:
                    # Mission directory exists but is incomplete
                    if dry_run:
                        changes.append(
                            f"Would repair incomplete mission: {mission_name}"
                        )
                    else:
                        try:
                            # Remove incomplete and copy fresh
                            shutil.rmtree(dest_mission)
                            shutil.copytree(src_mission, dest_mission)
                            changes.append(f"Repaired incomplete mission: {mission_name}")
                        except OSError as e:
                            errors.append(f"Failed to repair mission {mission_name}: {e}")
            else:
                # Mission doesn't exist, copy it
                if dry_run:
                    changes.append(f"Would copy missing mission: {mission_name}")
                else:
                    try:
                        shutil.copytree(src_mission, dest_mission)
                        changes.append(f"Copied missing mission: {mission_name}")
                    except OSError as e:
                        errors.append(f"Failed to copy mission {mission_name}: {e}")

        # Also fix worktrees
        worktrees_dir = project_path / ".worktrees"
        if worktrees_dir.exists():
            for worktree in worktrees_dir.iterdir():
                if not worktree.is_dir():
                    continue

                wt_missions = worktree / ".kittify" / "missions"
                if not wt_missions.exists():
                    continue

                for mission_name in self.REQUIRED_MISSIONS:
                    wt_mission = wt_missions / mission_name
                    src_mission = package_missions / mission_name

                    if not wt_mission.exists():
                        if dry_run:
                            changes.append(
                                f"Would copy missing mission to worktree {worktree.name}: {mission_name}"
                            )
                        else:
                            try:
                                shutil.copytree(src_mission, wt_mission)
                                changes.append(
                                    f"Copied missing mission to worktree {worktree.name}: {mission_name}"
                                )
                            except OSError as e:
                                warnings.append(
                                    f"Could not copy mission to worktree {worktree.name}: {e}"
                                )

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )

    def _find_package_missions(self) -> Path | None:
        """Find the missions directory in the installed package or local repo."""
        # First try from installed package
        try:
            from importlib.resources import files

            pkg_files = files("specify_cli")
            missions_path = pkg_files.joinpath("missions")

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
            missions_dir = pkg_dir / "missions"
            if missions_dir.exists():
                return missions_dir
        except (ImportError, AttributeError):
            pass

        # Fallback for development: Check SPEC_KITTY_TEMPLATE_ROOT env var
        import os

        template_root = os.environ.get("SPEC_KITTY_TEMPLATE_ROOT")
        if template_root:
            missions_dir = Path(template_root) / ".kittify" / "missions"
            if missions_dir.exists():
                return missions_dir

        # Fallback: Try to find the spec-kitty repo root from current working directory
        # This handles cases where we're running from the repo in development
        try:
            cwd = Path.cwd()
            # Check if we're in the spec-kitty repo
            for parent in [cwd] + list(cwd.parents):
                missions_dir = parent / ".kittify" / "missions"
                pyproject = parent / "pyproject.toml"
                if missions_dir.exists() and pyproject.exists():
                    # Verify it's the spec-kitty repo by checking pyproject.toml
                    try:
                        content = pyproject.read_text()
                        if "spec-kitty-cli" in content:
                            return missions_dir
                    except OSError:
                        pass
        except OSError:
            pass

        return None
