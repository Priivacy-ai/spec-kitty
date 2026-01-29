"""Migration: Update agent plan.md templates with centralized feature detection.

This migration updates all 12 agent template copies of plan.md to include
the new feature detection logic that prevents the agent from selecting the
wrong feature when multiple features exist.

The updated template instructs agents to:
1. Detect feature context from git branch or current directory
2. Pass the feature explicitly using --feature flag to avoid auto-detection
3. Prioritize features without plan.md if multiple exist
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Tuple

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult
from .m_0_9_1_complete_lane_migration import CompleteLaneMigration


def get_agent_dirs_for_project(project_path: Path) -> List[Tuple[str, str]]:
    """Get list of agent directories that should exist based on config.

    This respects user configuration (which agents they want) rather than
    assuming all 12 agents should always be present.

    Args:
        project_path: Path to the project root

    Returns:
        List of (agent_root_dir, subdirectory) tuples for configured agents
        Example: [(".claude", "commands"), (".github", "prompts"), ...]

    Note:
        Falls back to all agents if config doesn't exist (legacy projects).
    """
    from specify_cli.agent_config import load_agent_config, AGENT_DIR_TO_KEY

    # Try to load config
    config = load_agent_config(project_path)

    # Build reverse mapping: directory -> key
    dir_to_key = {dir_path: key for key, dir_path in AGENT_DIR_TO_KEY.items()}

    # Filter AGENT_DIRS based on configured agents
    result = []
    for agent_dir, subdir in CompleteLaneMigration.AGENT_DIRS:
        # Get agent key from directory
        agent_key = dir_to_key.get(agent_dir)

        # If no config exists (None), include all agents (legacy behavior)
        # If config exists but agent not in it, skip
        # If config exists and agent is in it, include
        if config is None or (agent_key and agent_key in config.available):
            result.append((agent_dir, subdir))

    return result


@MigrationRegistry.register
class CentralizedFeatureDetectionMigration(BaseMigration):
    """Update agent plan.md templates with feature detection logic.

    This migration regenerates the plan.md template for all configured agents
    from the updated source template that includes feature detection instructions.

    The new template instructs agents to:
    1. Detect feature context before running commands
    2. Pass --feature flag explicitly to setup-plan
    3. Handle multiple features gracefully
    """

    migration_id = "0.14.0_centralized_feature_detection"
    description = "Update agent plan.md templates with centralized feature detection"
    target_version = "0.14.0"

    # Template file to update
    TEMPLATE_FILE = "spec-kitty.plan.md"

    def detect(self, project_path: Path) -> bool:
        """Check if any agent templates need updating.

        We detect by checking if the plan.md template contains the new
        feature detection section (step 2 in the outline).
        """
        agent_dirs = get_agent_dirs_for_project(project_path)

        for agent_root, subdir in agent_dirs:
            agent_dir = project_path / agent_root / subdir

            # Skip if agent directory doesn't exist (user may have deleted it)
            if not agent_dir.exists():
                continue

            template_file = agent_dir / self.TEMPLATE_FILE
            if not template_file.exists():
                # Template missing, needs update
                return True

            # Check if template has the new feature detection section
            try:
                content = template_file.read_text(encoding="utf-8")
                if "2. **Detect feature context**" not in content:
                    # Old template without feature detection
                    return True
            except OSError:
                # Can't read, assume needs update
                return True

        return False

    def can_apply(self, project_path: Path) -> tuple[bool, str]:
        """Check if we can copy the updated template from the package."""
        package_template = self._find_package_template()
        if package_template is None:
            return (
                False,
                "Could not locate package plan.md template to copy from. "
                "This is expected in test environments. "
                "Run 'spec-kitty upgrade' again after installation.",
            )

        # Verify the package template has the new feature detection section
        try:
            content = package_template.read_text(encoding="utf-8")
            if "2. **Detect feature context**" not in content:
                return (
                    False,
                    "Package plan.md template is missing feature detection section. "
                    "Please upgrade spec-kitty-cli to version 0.14.0 or later.",
                )
        except OSError as e:
            return (False, f"Could not read package template: {e}")

        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        """Copy updated plan.md template to all configured agent directories."""
        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        package_template = self._find_package_template()

        if package_template is None:
            errors.append("Could not locate package plan.md template")
            return MigrationResult(success=False, errors=errors)

        # Get configured agent directories
        agent_dirs = get_agent_dirs_for_project(project_path)

        if not agent_dirs:
            # No agents configured, nothing to do
            return MigrationResult(
                success=True,
                changes_made=["No agents configured, skipping template update"],
            )

        # Update plan.md for each configured agent
        for agent_root, subdir in agent_dirs:
            agent_dir = project_path / agent_root / subdir

            # Skip if directory doesn't exist (respect user deletions)
            if not agent_dir.exists():
                continue

            dest = agent_dir / self.TEMPLATE_FILE

            if dry_run:
                changes.append(f"Would update {agent_root}/{subdir}/{self.TEMPLATE_FILE}")
            else:
                try:
                    # Ensure directory exists
                    agent_dir.mkdir(parents=True, exist_ok=True)

                    # Copy updated template
                    shutil.copy2(package_template, dest)
                    changes.append(f"Updated {agent_root}/{subdir}/{self.TEMPLATE_FILE}")
                except OSError as e:
                    errors.append(f"Failed to update {agent_root}/{subdir}/{self.TEMPLATE_FILE}: {e}")

        success = len(errors) == 0
        return MigrationResult(
            success=success,
            changes_made=changes,
            errors=errors,
            warnings=warnings,
        )

    def _find_package_template(self) -> Path | None:
        """Find the plan.md template in the installed package or local repo."""
        # First try from installed package
        try:
            from importlib.resources import files

            pkg_files = files("specify_cli")
            template_path = pkg_files.joinpath(
                "missions", "software-dev", "command-templates", "plan.md"
            )

            # Convert to Path and check if it exists
            template_str = str(template_path)
            if Path(template_str).exists():
                return Path(template_str)

        except (ImportError, TypeError, AttributeError):
            pass

        # Try from package __file__ location
        try:
            import specify_cli

            pkg_dir = Path(specify_cli.__file__).parent
            template_file = (
                pkg_dir / "missions" / "software-dev" / "command-templates" / "plan.md"
            )
            if template_file.exists():
                return template_file
        except (ImportError, AttributeError):
            pass

        # Fallback for development: Check current repository
        try:
            cwd = Path.cwd()
            for parent in [cwd] + list(cwd.parents):
                template_file = (
                    parent / "src" / "specify_cli" / "missions" / "software-dev" /
                    "command-templates" / "plan.md"
                )
                pyproject = parent / "pyproject.toml"
                if template_file.exists() and pyproject.exists():
                    try:
                        content = pyproject.read_text(encoding="utf-8-sig")
                        if "spec-kitty-cli" in content:
                            return template_file
                    except OSError:
                        pass
        except OSError:
            pass

        return None
