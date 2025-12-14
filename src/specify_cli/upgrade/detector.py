"""Version detection for Spec Kitty projects."""

from __future__ import annotations

from pathlib import Path
from typing import List

from .metadata import ProjectMetadata


class VersionDetector:
    """Detects project version through heuristics when metadata is missing."""

    # Agent directories that should be in .gitignore (v0.4.8+)
    EXPECTED_AGENTS = [
        ".claude/",
        ".codex/",
        ".opencode/",
        ".windsurf/",
        ".gemini/",
        ".cursor/",
        ".qwen/",
        ".kilocode/",
        ".augment/",
        ".roo/",
        ".amazonq/",
        ".github/copilot/",
    ]

    def __init__(self, project_path: Path):
        """Initialize the detector.

        Args:
            project_path: Root of the project
        """
        self.project_path = project_path
        self.kittify_dir = project_path / ".kittify"
        self.specify_dir = project_path / ".specify"  # Old name

    def detect_version(self) -> str:
        """Detect the approximate version of a project.

        Returns:
            A version string like "0.1.0" (oldest detectable)
            or "0.6.7" (current).
        """
        # First try to load from metadata
        if self.kittify_dir.exists():
            metadata = ProjectMetadata.load(self.kittify_dir)
            if metadata:
                return metadata.version

        # Heuristic detection based on directory structure
        return self._detect_from_structure()

    def _detect_from_structure(self) -> str:
        """Detect version from project structure."""
        # v0.1.x: Uses .specify/ directory and /specs/
        if self.specify_dir.exists():
            return "0.1.0"

        # No .kittify at all - not initialized or very old
        if not self.kittify_dir.exists():
            return "0.0.0"

        # Check for command-templates vs commands directory
        # v0.6.5+ uses command-templates/
        templates_dir = self.kittify_dir / "templates"
        missions_dir = self.kittify_dir / "missions"

        # Check templates location
        has_command_templates = (templates_dir / "command-templates").exists()
        has_old_commands = (templates_dir / "commands").exists()

        # Check missions for command-templates
        has_mission_command_templates = False
        has_mission_commands = False
        if missions_dir.exists():
            for mission in missions_dir.iterdir():
                if mission.is_dir():
                    if (mission / "command-templates").exists():
                        has_mission_command_templates = True
                    if (mission / "commands").exists():
                        has_mission_commands = True

        # v0.6.5+: Has command-templates (not commands)
        if has_command_templates or has_mission_command_templates:
            if not has_old_commands and not has_mission_commands:
                return "0.6.5"

        # v0.6.4 and earlier: Has old commands/ directory
        if has_old_commands or has_mission_commands:
            return "0.6.4"

        # Check for git hooks (v0.5.0+)
        git_hooks = self.project_path / ".git" / "hooks"
        if git_hooks.exists() and (git_hooks / "pre-commit").exists():
            try:
                hook_content = (git_hooks / "pre-commit").read_text(
                    encoding="utf-8", errors="ignore"
                )
                if "spec-kitty" in hook_content.lower() or "encoding" in hook_content.lower():
                    return "0.5.0"
            except OSError:
                pass

        # Check .gitignore for agent directories (v0.4.8+)
        gitignore = self.project_path / ".gitignore"
        if gitignore.exists():
            try:
                content = gitignore.read_text(encoding="utf-8-sig", errors="ignore")
                agent_dirs = [".claude/", ".codex/", ".gemini/", ".cursor/"]
                agent_count = sum(1 for d in agent_dirs if d in content)
                if agent_count >= 4:
                    return "0.4.8"
            except OSError:
                pass

        # Check for missions directory (v0.2.0+)
        if missions_dir.exists():
            return "0.2.0"

        # Default to oldest .kittify-based version
        return "0.2.0"

    def get_needed_migrations(self, target_version: str) -> List[str]:
        """Get list of migration IDs needed to reach target version.

        Args:
            target_version: Version to upgrade to

        Returns:
            List of migration IDs in order
        """
        from .registry import MigrationRegistry

        current = self.detect_version()
        migrations = MigrationRegistry.get_applicable(current, target_version)
        return [m.migration_id for m in migrations]

    def has_old_commands_structure(self) -> bool:
        """Check if the project uses old commands/ directories.

        Returns:
            True if old commands/ directories exist
        """
        templates_commands = self.kittify_dir / "templates" / "commands"
        if templates_commands.exists():
            return True

        missions_dir = self.kittify_dir / "missions"
        if missions_dir.exists():
            for mission in missions_dir.iterdir():
                if mission.is_dir() and (mission / "commands").exists():
                    return True

        return False

    def has_old_specify_structure(self) -> bool:
        """Check if the project uses old .specify/ structure.

        Returns:
            True if .specify/ directory exists
        """
        return self.specify_dir.exists()

    def count_missing_agent_gitignore_entries(self) -> int:
        """Count how many agent directories are missing from .gitignore.

        Returns:
            Number of missing entries
        """
        gitignore = self.project_path / ".gitignore"
        if not gitignore.exists():
            return len(self.EXPECTED_AGENTS)

        try:
            content = gitignore.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            return len(self.EXPECTED_AGENTS)

        missing = [d for d in self.EXPECTED_AGENTS if d not in content]
        return len(missing)

    @classmethod
    def detect_broken_mission_system(cls, project_path: Path) -> bool:
        """Detect if the mission system has corrupted files.

        Checks for:
        1. Missing mission.yaml files in mission directories
        2. Invalid YAML syntax in mission.yaml files
        3. Missing required fields (name)

        Args:
            project_path: Path to the project root

        Returns:
            True if mission system is broken/corrupted, False if healthy
        """
        import yaml

        missions_dir = project_path / ".kittify" / "missions"

        # No missions directory at all is broken
        if not missions_dir.exists():
            return True

        # Check each mission directory
        has_any_mission = False
        for mission_dir in missions_dir.iterdir():
            if not mission_dir.is_dir():
                continue

            has_any_mission = True
            mission_yaml = mission_dir / "mission.yaml"

            # Check if mission.yaml exists
            if not mission_yaml.exists():
                return True

            # Check if mission.yaml is valid YAML with required fields
            try:
                with open(mission_yaml, encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                # Check required fields
                if not data or "name" not in data:
                    return True

            except yaml.YAMLError:
                return True
            except OSError:
                return True

        # If no mission directories found, that's broken
        if not has_any_mission:
            return True

        return False
