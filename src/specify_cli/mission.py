"""Mission system for Spec Kitty.

This module provides the infrastructure for loading and managing missions,
which allow Spec Kitty to support multiple domains (software dev, research,
writing, etc.) with domain-specific templates, workflows, and validation.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml


class MissionError(Exception):
    """Base exception for mission-related errors."""
    pass


class MissionNotFoundError(MissionError):
    """Raised when a mission cannot be found."""
    pass


class Mission:
    """Represents a Spec Kitty mission with its configuration and resources."""

    def __init__(self, mission_path: Path):
        """Initialize a mission from a directory path.

        Args:
            mission_path: Path to the mission directory containing mission.yaml

        Raises:
            MissionNotFoundError: If mission directory or config doesn't exist
        """
        self.path = mission_path.resolve()

        if not self.path.exists():
            raise MissionNotFoundError(f"Mission directory not found: {self.path}")

        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load mission configuration from mission.yaml.

        Returns:
            Dictionary containing mission configuration

        Raises:
            MissionNotFoundError: If mission.yaml doesn't exist
            yaml.YAMLError: If mission.yaml is malformed
        """
        config_file = self.path / "mission.yaml"

        if not config_file.exists():
            raise MissionNotFoundError(
                f"Mission config not found: {config_file}\n"
                f"Expected mission.yaml in mission directory"
            )

        with open(config_file, 'r') as f:
            try:
                return yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise MissionError(f"Invalid mission.yaml: {e}")

    @property
    def name(self) -> str:
        """Get the mission name (e.g., 'Software Dev Kitty')."""
        return self.config.get("name", "Unknown Mission")

    @property
    def description(self) -> str:
        """Get the mission description."""
        return self.config.get("description", "")

    @property
    def version(self) -> str:
        """Get the mission version."""
        return self.config.get("version", "0.0.0")

    @property
    def domain(self) -> str:
        """Get the mission domain (e.g., 'software', 'research')."""
        return self.config.get("domain", "unknown")

    @property
    def templates_dir(self) -> Path:
        """Get the templates directory for this mission."""
        return self.path / "templates"

    @property
    def commands_dir(self) -> Path:
        """Get the commands directory for this mission."""
        return self.path / "commands"

    @property
    def constitution_dir(self) -> Path:
        """Get the constitution directory for this mission."""
        return self.path / "constitution"

    def get_template(self, template_name: str) -> Path:
        """Get path to a template file.

        Args:
            template_name: Name of template (e.g., 'spec-template.md')

        Returns:
            Path to the template file

        Raises:
            FileNotFoundError: If template doesn't exist
        """
        template_path = self.templates_dir / template_name

        if not template_path.exists():
            raise FileNotFoundError(
                f"Template not found: {template_path}\n"
                f"Mission: {self.name}\n"
                f"Available templates: {self.list_templates()}"
            )

        return template_path

    def get_command_template(self, command_name: str) -> Path:
        """Get path to a command template file.

        Args:
            command_name: Name of command (e.g., 'plan', 'implement')

        Returns:
            Path to the command template file

        Raises:
            FileNotFoundError: If command template doesn't exist
        """
        # Support both with and without .md extension
        if not command_name.endswith('.md'):
            command_name = f"{command_name}.md"

        command_path = self.commands_dir / command_name

        if not command_path.exists():
            raise FileNotFoundError(
                f"Command template not found: {command_path}\n"
                f"Mission: {self.name}\n"
                f"Available commands: {self.list_commands()}"
            )

        return command_path

    def list_templates(self) -> List[str]:
        """List all available templates in this mission."""
        if not self.templates_dir.exists():
            return []
        return [f.name for f in self.templates_dir.glob("*.md")]

    def list_commands(self) -> List[str]:
        """List all available command templates in this mission."""
        if not self.commands_dir.exists():
            return []
        return [f.stem for f in self.commands_dir.glob("*.md")]

    def get_validation_checks(self) -> List[str]:
        """Get list of validation checks for this mission."""
        return self.config.get("validation", {}).get("checks", [])

    def has_custom_validators(self) -> bool:
        """Check if mission has custom validators.py."""
        return self.config.get("validation", {}).get("custom_validators", False)

    def get_workflow_phases(self) -> List[Dict[str, str]]:
        """Get workflow phases for this mission.

        Returns:
            List of dicts with 'name' and 'description' keys
        """
        return self.config.get("workflow", {}).get("phases", [])

    def get_required_artifacts(self) -> List[str]:
        """Get list of required artifacts for this mission."""
        return self.config.get("artifacts", {}).get("required", [])

    def get_optional_artifacts(self) -> List[str]:
        """Get list of optional artifacts for this mission."""
        return self.config.get("artifacts", {}).get("optional", [])

    def get_path_conventions(self) -> Dict[str, str]:
        """Get path conventions for this mission (e.g., workspace, tests)."""
        return self.config.get("paths", {})

    def get_mcp_tools(self) -> Dict[str, List[str]]:
        """Get MCP tools configuration for this mission.

        Returns:
            Dict with 'required', 'recommended', 'optional' lists
        """
        mcp_tools = self.config.get("mcp_tools", {})
        return {
            "required": mcp_tools.get("required", []),
            "recommended": mcp_tools.get("recommended", []),
            "optional": mcp_tools.get("optional", [])
        }

    def get_agent_context(self) -> str:
        """Get agent personality/instructions for this mission."""
        return self.config.get("agent_context", "")

    def get_command_config(self, command_name: str) -> Dict[str, str]:
        """Get configuration for a specific command.

        Args:
            command_name: Name of command (e.g., 'plan', 'implement')

        Returns:
            Dict with command configuration (e.g., 'prompt')
        """
        commands_config = self.config.get("commands", {})
        return commands_config.get(command_name, {})

    def __repr__(self) -> str:
        return f"Mission(name='{self.name}', domain='{self.domain}', version='{self.version}')"


def get_active_mission(project_root: Optional[Path] = None) -> Mission:
    """Get the currently active mission for a project.

    Args:
        project_root: Path to project root (defaults to current directory)

    Returns:
        Mission object for the active mission

    Raises:
        MissionNotFoundError: If no active mission is configured
    """
    if project_root is None:
        project_root = Path.cwd()

    kittify_dir = project_root / ".kittify"

    if not kittify_dir.exists():
        raise MissionNotFoundError(
            f"No .kittify directory found in {project_root}\n"
            f"Is this a Spec Kitty project? Run 'spec-kitty init' to create one."
        )

    # Check for active-mission symlink
    active_mission_link = kittify_dir / "active-mission"

    if active_mission_link.exists():
        mission_path: Optional[Path] = None
        if active_mission_link.is_symlink():
            # Resolve symlink to actual mission directory (supports relative targets)
            mission_path = active_mission_link.resolve()
        elif active_mission_link.is_file():
            try:
                mission_name = active_mission_link.read_text(encoding="utf-8").strip()
            except OSError:
                mission_name = ""
            if mission_name:
                mission_path = kittify_dir / "missions" / mission_name
        if mission_path is None:
            # Fallback to interpreting the target path directly
            try:
                target = Path(os.readlink(active_mission_link))
                mission_path = (active_mission_link.parent / target).resolve()
            except (OSError, RuntimeError):
                mission_path = None

        if mission_path is None:
            mission_path = kittify_dir / "missions" / "software-dev"
    else:
        # Default to software-dev if no active mission set
        mission_path = kittify_dir / "missions" / "software-dev"

    if not mission_path.exists():
        raise MissionNotFoundError(
            f"Active mission directory not found: {mission_path}\n"
            f"Available missions: {list_available_missions(kittify_dir)}"
        )

    return Mission(mission_path)


def list_available_missions(kittify_dir: Optional[Path] = None) -> List[str]:
    """List all available missions in a project.

    Args:
        kittify_dir: Path to .kittify directory (defaults to current project)

    Returns:
        List of mission names (directory names)
    """
    if kittify_dir is None:
        kittify_dir = Path.cwd() / ".kittify"

    missions_dir = kittify_dir / "missions"

    if not missions_dir.exists():
        return []

    missions = []
    for mission_dir in missions_dir.iterdir():
        if mission_dir.is_dir() and (mission_dir / "mission.yaml").exists():
            missions.append(mission_dir.name)

    return sorted(missions)


def get_mission_by_name(mission_name: str, kittify_dir: Optional[Path] = None) -> Mission:
    """Get a mission by name.

    Args:
        mission_name: Name of the mission (e.g., 'software-dev', 'research')
        kittify_dir: Path to .kittify directory (defaults to current project)

    Returns:
        Mission object

    Raises:
        MissionNotFoundError: If mission doesn't exist
    """
    if kittify_dir is None:
        kittify_dir = Path.cwd() / ".kittify"

    mission_path = kittify_dir / "missions" / mission_name

    if not mission_path.exists():
        available = list_available_missions(kittify_dir)
        raise MissionNotFoundError(
            f"Mission '{mission_name}' not found.\n"
            f"Available missions: {', '.join(available) if available else 'none'}"
        )

    return Mission(mission_path)


def set_active_mission(mission_name: str, kittify_dir: Optional[Path] = None) -> None:
    """Set the active mission for a project.

    Args:
        mission_name: Name of the mission to activate
        kittify_dir: Path to .kittify directory (defaults to current project)

    Raises:
        MissionNotFoundError: If mission doesn't exist
    """
    if kittify_dir is None:
        kittify_dir = Path.cwd() / ".kittify"

    # Validate mission exists
    mission = get_mission_by_name(mission_name, kittify_dir)

    # Create or update symlink
    active_mission_link = kittify_dir / "active-mission"

    # Remove existing symlink if it exists
    if active_mission_link.exists() or active_mission_link.is_symlink():
        active_mission_link.unlink()

    # Create new symlink (relative path keeps worktrees portable)
    try:
        active_mission_link.symlink_to(Path("missions") / mission_name)
    except (OSError, NotImplementedError):
        # Fall back to plain file marker when symlinks are unavailable
        active_mission_link.write_text(f"{mission_name}\n", encoding="utf-8")
