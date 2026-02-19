"""Frontmatter management with absolute consistency enforcement.

This module provides the ONLY way to read and write YAML frontmatter
in spec-kitty markdown files. All frontmatter operations MUST go through
these functions to ensure absolute consistency.

LLMs and scripts should NEVER manually edit YAML frontmatter.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap


class FrontmatterError(Exception):
    """Error in frontmatter operations."""
    pass


class FrontmatterManager:
    """Manages YAML frontmatter with enforced consistency.

    Rules:
    1. Always use ruamel.yaml for parsing/writing
    2. Never quote scalar values (let YAML decide)
    3. Use consistent indentation (2 spaces)
    4. Preserve comments
    5. Sort keys in consistent order
    """

    # Standard field order for work package frontmatter
    WP_FIELD_ORDER = [
        "work_package_id",
        "title",
        "lane",
        "dependencies",  # List of WP IDs this WP depends on (e.g., ['WP01', 'WP02'])
        "base_branch",  # Git branch this WP was created from (e.g., "010-feature-WP01" or "main")
        "base_commit",  # Git commit SHA this WP was created from (snapshot for validation)
        "created_at",  # ISO timestamp when workspace was created
        "subtasks",
        "phase",
        "assignee",
        "agent",
        "shell_pid",
        "review_status",
        "reviewed_by",
        "history",
    ]

    def __init__(self) -> None:
        """Initialize with ruamel.yaml configured for consistency."""
        self.yaml = YAML()
        self.yaml.default_flow_style = False
        self.yaml.preserve_quotes = False  # Don't preserve quotes - let YAML decide
        self.yaml.width = 4096  # Prevent line wrapping
        self.yaml.indent(mapping=2, sequence=2, offset=0)

    def read(self, file_path: Path) -> tuple[Dict[str, Any], str]:
        """Read frontmatter and body from a markdown file.

        Args:
            file_path: Path to markdown file

        Returns:
            Tuple of (frontmatter_dict, body_text)

        Raises:
            FrontmatterError: If file has no frontmatter or is malformed
        """
        if not file_path.exists():
            raise FrontmatterError(f"File not found: {file_path}")

        content = file_path.read_text(encoding="utf-8-sig")

        if not content.startswith("---"):
            raise FrontmatterError(f"File has no frontmatter: {file_path}")

        # Find closing ---
        lines = content.split("\n")
        closing_idx = -1
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                closing_idx = i
                break

        if closing_idx == -1:
            raise FrontmatterError(f"Malformed frontmatter (no closing ---): {file_path}")

        # Parse frontmatter
        frontmatter_text = "\n".join(lines[1:closing_idx])
        try:
            frontmatter = self.yaml.load(frontmatter_text)
            if frontmatter is None:
                frontmatter = {}
        except Exception as e:
            raise FrontmatterError(f"Invalid YAML in {file_path}: {e}")

        # Ensure dependencies field exists for WP files only (backward compatibility with pre-0.11.0)
        if file_path.name.startswith("WP") and "dependencies" not in frontmatter:
            frontmatter["dependencies"] = []

        # Get body (everything after closing ---)
        body = "\n".join(lines[closing_idx + 1:])

        return frontmatter, body

    def write(self, file_path: Path, frontmatter: Dict[str, Any], body: str) -> None:
        """Write frontmatter and body to a markdown file.

        Args:
            file_path: Path to markdown file
            frontmatter: Dictionary of frontmatter fields
            body: Body text (everything after frontmatter)
        """
        # Normalize frontmatter (sort keys, clean values)
        normalized = self._normalize_frontmatter(frontmatter)

        # Write to string buffer first
        import io
        buffer = io.StringIO()
        buffer.write("---\n")
        self.yaml.dump(normalized, buffer)
        buffer.write("---\n")
        buffer.write(body)

        # Write to file
        file_path.write_text(buffer.getvalue(), encoding="utf-8")

    def update_field(self, file_path: Path, field: str, value: Any) -> None:
        """Update a single field in frontmatter.

        Args:
            file_path: Path to markdown file
            field: Field name to update
            value: New value for field
        """
        frontmatter, body = self.read(file_path)
        frontmatter[field] = value
        self.write(file_path, frontmatter, body)

    def update_fields(self, file_path: Path, updates: Dict[str, Any]) -> None:
        """Update multiple fields in frontmatter.

        Args:
            file_path: Path to markdown file
            updates: Dictionary of field updates
        """
        frontmatter, body = self.read(file_path)
        frontmatter.update(updates)
        self.write(file_path, frontmatter, body)

    def get_field(self, file_path: Path, field: str, default: Any = None) -> Any:
        """Get a single field from frontmatter.

        Args:
            file_path: Path to markdown file
            field: Field name to get
            default: Default value if field doesn't exist

        Returns:
            Field value or default
        """
        frontmatter, _ = self.read(file_path)
        return frontmatter.get(field, default)

    def add_history_entry(
        self,
        file_path: Path,
        action: str,
        agent: Optional[str] = None,
        note: Optional[str] = None
    ) -> None:
        """Add an entry to the history field.

        Args:
            file_path: Path to markdown file
            action: Action description (e.g., "moved to for_review")
            agent: Agent name (optional)
            note: Additional note (optional)
        """
        frontmatter, body = self.read(file_path)

        # Get or create history list
        history = frontmatter.get("history", [])
        if not isinstance(history, list):
            history = []

        # Create entry
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
        }
        if agent:
            entry["agent"] = agent
        if note:
            entry["note"] = note

        history.append(entry)
        frontmatter["history"] = history

        self.write(file_path, frontmatter, body)

    def _normalize_frontmatter(self, frontmatter: Dict[str, Any]) -> CommentedMap:
        """Normalize frontmatter for consistent output.

        Args:
            frontmatter: Raw frontmatter dictionary

        Returns:
            Normalized CommentedMap with consistent field order
        """
        # Create ordered map
        normalized = CommentedMap()

        # Add fields in standard order (if they exist)
        for field in self.WP_FIELD_ORDER:
            if field in frontmatter:
                normalized[field] = frontmatter[field]

        # Add any remaining fields (alphabetically)
        remaining = sorted(set(frontmatter.keys()) - set(self.WP_FIELD_ORDER))
        for field in remaining:
            normalized[field] = frontmatter[field]

        return normalized

    def _validate_dependencies(self, dependencies: Any) -> list[str]:
        """Validate dependencies field format.

        Args:
            dependencies: Dependencies value to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not isinstance(dependencies, list):
            errors.append(f"dependencies must be a list, got {type(dependencies).__name__}")
            return errors

        wp_pattern = re.compile(r'^WP\d{2}$')
        seen = set()

        for dep in dependencies:
            if not isinstance(dep, str):
                errors.append(f"Dependency must be string, got {type(dep).__name__}")
            elif not wp_pattern.match(dep):
                errors.append(f"Invalid WP ID format: {dep} (must be WP## like WP01, WP02)")
            elif dep in seen:
                errors.append(f"Duplicate dependency: {dep}")
            else:
                seen.add(dep)

        return errors

    def validate(self, file_path: Path) -> list[str]:
        """Validate frontmatter consistency.

        Args:
            file_path: Path to markdown file

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        try:
            frontmatter, _ = self.read(file_path)
        except FrontmatterError as e:
            return [str(e)]

        # Check for required fields (work packages only)
        if file_path.name.startswith("WP"):
            required = ["work_package_id", "title", "lane"]
            for field in required:
                if field not in frontmatter:
                    errors.append(f"Missing required field: {field}")

            # Validate lane value
            if "lane" in frontmatter:
                valid_lanes = [
                    "planned", "claimed", "in_progress", "for_review",
                    "done", "blocked", "canceled",
                    "doing",  # Accepted alias for in_progress
                ]
                if frontmatter["lane"] not in valid_lanes:
                    errors.append(
                        f"Invalid lane value: {frontmatter['lane']} "
                        f"(must be one of: {', '.join(valid_lanes)})"
                    )

            # Validate dependencies field (if present)
            if "dependencies" in frontmatter:
                dep_errors = self._validate_dependencies(frontmatter["dependencies"])
                errors.extend(dep_errors)

        return errors


# Global instance for convenience
_manager = FrontmatterManager()


# Convenience functions that use the global manager
def read_frontmatter(file_path: Path) -> tuple[Dict[str, Any], str]:
    """Read frontmatter and body from a markdown file."""
    return _manager.read(file_path)


def write_frontmatter(file_path: Path, frontmatter: Dict[str, Any], body: str) -> None:
    """Write frontmatter and body to a markdown file."""
    _manager.write(file_path, frontmatter, body)


def update_field(file_path: Path, field: str, value: Any) -> None:
    """Update a single field in frontmatter."""
    _manager.update_field(file_path, field, value)


def update_fields(file_path: Path, updates: Dict[str, Any]) -> None:
    """Update multiple fields in frontmatter."""
    _manager.update_fields(file_path, updates)


def get_field(file_path: Path, field: str, default: Any = None) -> Any:
    """Get a single field from frontmatter."""
    return _manager.get_field(file_path, field, default)


def add_history_entry(
    file_path: Path,
    action: str,
    agent: Optional[str] = None,
    note: Optional[str] = None
) -> None:
    """Add an entry to the history field."""
    _manager.add_history_entry(file_path, action, agent, note)


def validate_frontmatter(file_path: Path) -> list[str]:
    """Validate frontmatter consistency."""
    return _manager.validate(file_path)


def normalize_file(file_path: Path) -> bool:
    """Normalize an existing file's frontmatter.

    Args:
        file_path: Path to markdown file

    Returns:
        True if file was modified, False if already normalized
    """
    try:
        # Read current content
        original_content = file_path.read_text(encoding="utf-8-sig")

        # Read and rewrite (which normalizes)
        frontmatter, body = _manager.read(file_path)
        _manager.write(file_path, frontmatter, body)

        # Check if changed
        new_content = file_path.read_text(encoding="utf-8-sig")
        return original_content != new_content

    except FrontmatterError:
        return False


__all__ = [
    "FrontmatterError",
    "FrontmatterManager",
    "read_frontmatter",
    "write_frontmatter",
    "update_field",
    "update_fields",
    "get_field",
    "add_history_entry",
    "validate_frontmatter",
    "normalize_file",
]
