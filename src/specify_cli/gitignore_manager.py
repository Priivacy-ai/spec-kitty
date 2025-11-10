"""
GitignoreManager module for protecting AI agent directories.

This module provides a centralized system for managing .gitignore entries
to protect AI agent directories from being accidentally committed to git.
It replaces the fragmented approach where only .codex/ was protected.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set


@dataclass
class AgentDirectory:
    """Represents a single agent's directory that needs protection."""

    name: str
    """Agent name identifier (e.g., 'claude', 'codex')"""

    directory: str
    """Directory path with trailing slash (e.g., '.claude/')"""

    is_special: bool
    """Indicates if special handling is needed (e.g., .github/)"""

    description: str
    """Human-readable description for documentation"""


@dataclass
class ProtectionResult:
    """Result of a gitignore protection operation."""

    success: bool
    """Whether the operation succeeded"""

    modified: bool
    """Whether .gitignore was modified"""

    entries_added: List[str] = field(default_factory=list)
    """New entries added to .gitignore"""

    entries_skipped: List[str] = field(default_factory=list)
    """Entries already present in .gitignore"""

    errors: List[str] = field(default_factory=list)
    """Error messages if any occurred"""

    warnings: List[str] = field(default_factory=list)
    """Warning messages if any were generated"""


# Registry of all known AI agent directories
AGENT_DIRECTORIES = [
    AgentDirectory("claude", ".claude/", False, "Claude Code CLI"),
    AgentDirectory("codex", ".codex/", False, "Codex (contains auth.json)"),
    AgentDirectory("opencode", ".opencode/", False, "opencode CLI"),
    AgentDirectory("windsurf", ".windsurf/", False, "Windsurf"),
    AgentDirectory("gemini", ".gemini/", False, "Google Gemini"),
    AgentDirectory("cursor", ".cursor/", False, "Cursor"),
    AgentDirectory("qwen", ".qwen/", False, "Qwen"),
    AgentDirectory("kilocode", ".kilocode/", False, "Kilocode"),
    AgentDirectory("auggie", ".augment/", False, "Auggie"),
    AgentDirectory("github", ".github/", True, "GitHub Copilot (shared with Actions)"),  # Special: dual use
    AgentDirectory("roo", ".roo/", False, "Roo Coder"),
    AgentDirectory("amazonq", ".amazonq/", False, "Amazon Q"),
]


class GitignoreManager:
    """Manages gitignore entries for AI agent directories."""

    def __init__(self, project_path: Path):
        """
        Initialize GitignoreManager with project root path.

        Args:
            project_path: Root directory of the project

        Raises:
            ValueError: If project_path doesn't exist or isn't a directory
        """
        if not isinstance(project_path, Path):
            project_path = Path(project_path)

        if not project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")

        if not project_path.is_dir():
            raise ValueError(f"Project path is not a directory: {project_path}")

        self.project_path = project_path
        self.gitignore_path = project_path / ".gitignore"
        self.marker = "# Added by Spec Kitty CLI (auto-managed)"
        self._line_ending = None

    def ensure_entries(self, entries: List[str]) -> bool:
        """
        Core method to add entries to .gitignore.

        This method migrates the logic from the original ensure_gitignore_entries
        function, maintaining the same behavior for compatibility.

        Args:
            entries: List of gitignore patterns to add

        Returns:
            True if .gitignore was modified, False otherwise
        """
        if not entries:
            return False

        # Read existing content or start with empty list
        if self.gitignore_path.exists():
            content = self.gitignore_path.read_text(encoding="utf-8")
            # Detect and store line ending style
            self._line_ending = self._detect_line_ending(content)
            lines = content.splitlines()
        else:
            lines = []
            # Use system default for new files
            self._line_ending = os.linesep

        existing = set(lines)
        changed = False

        # Check if any entry needs to be added
        if any(entry not in existing for entry in entries):
            # Add marker if not present
            if self.marker not in existing:
                if lines and lines[-1].strip():
                    lines.append("")  # Add blank line before marker
                lines.append(self.marker)
                existing.add(self.marker)
                changed = True

            # Add missing entries
            for entry in entries:
                if entry not in existing:
                    lines.append(entry)
                    existing.add(entry)
                    changed = True

        # Write back if changed
        if changed:
            # Ensure file ends with newline
            if lines and lines[-1] != "":
                lines.append("")

            # Join with detected line ending
            content = self._line_ending.join(lines)
            self.gitignore_path.write_text(content, encoding="utf-8")

        return changed

    def _detect_line_ending(self, content: str) -> str:
        """
        Detect and return the line ending style used in content.

        Args:
            content: File content to analyze

        Returns:
            Line ending string ('\r\n' for Windows, '\n' for Unix/Mac)
        """
        if '\r\n' in content:
            return '\r\n'
        else:
            return '\n'

    @classmethod
    def get_agent_directories(cls) -> List[AgentDirectory]:
        """
        Get a copy of the registry of all known agent directories.

        Returns:
            List of AgentDirectory objects representing all known agents
        """
        # Return a copy to prevent external modification
        return AGENT_DIRECTORIES.copy()