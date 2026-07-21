"""Frontmatter management with absolute consistency enforcement.

This module provides the ONLY way to read and write YAML frontmatter
in spec-kitty markdown files. All frontmatter operations MUST go through
these functions to ensure absolute consistency.

LLMs and scripts should NEVER manually edit YAML frontmatter.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

# The additive PID-reuse identity baseline (C-007) co-written alongside
# ``shell_pid`` at every claim-write site (D3b). Declared once here — the
# single shared constant mirrors the ``"shell_pid"`` field-name pattern in
# ``WP_FIELD_ORDER`` below — and read by ``core.stale_detection`` (the
# claim-liveness consumer) so the field name cannot drift into a re-duplicated
# literal (Sonar S1192).
SHELL_PID_BASELINE_FIELD = "shell_pid_created_at"


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

    # Standard field order for work package frontmatter.
    # Mutable status fields (lane, review_status, reviewed_by, review_feedback)
    # are managed exclusively via the canonical event log and are NOT written here.
    WP_FIELD_ORDER = [
        "work_package_id",
        "title",
        "dependencies",  # List of WP IDs this WP depends on (e.g., ['WP01', 'WP02'])
        "requirement_refs",  # Requirement IDs mapped to this WP (e.g., ['FR-001', 'NFR-002'])
        # "tracker_refs" is intentionally NOT listed here (WP07/T029, FR-006/FR-013):
        # it is event-sourced (emitted by WP08's map-requirements + WP06's
        # move-task as an InnerStateChanged delta) and read from the reduced
        # snapshot. Keeping it in this static authored schema would dual-home
        # it (dynamic-in-events AND static-in-frontmatter) -- the #2093
        # violation FR-013's arch test (WP10) catches. A legacy WP file that
        # still carries an authored ``tracker_refs:`` line is read tolerantly
        # into the ``remaining`` (sorted trailing) bucket, never an error.
        "planning_base_branch",  # Planning branch active when the WP prompt was generated
        "merge_target_branch",  # Final branch where completed WP changes must land
        "branch_strategy",  # Human-readable branch contract to prevent landing on wrong stream
        "base_branch",  # Git branch this workspace was created from (e.g., "kitty/mission-010-feature-lane-a" or "main")
        "base_commit",  # Git commit SHA this WP was created from (snapshot for validation)
        "created_at",  # ISO timestamp when workspace was created
        "subtasks",
        "phase",
        "assignee",
        "agent",
        "shell_pid",
        SHELL_PID_BASELINE_FIELD,  # PID-reuse identity baseline co-written with shell_pid (C-007)
        "scope",  # Optional: "codebase-wide" for audit/cutover WPs that need whole-repo access
        "history",
    ]

    def __init__(self) -> None:
        """Initialize with ruamel.yaml configured for consistency."""
        self.yaml = YAML()
        self.yaml.default_flow_style = False
        self.yaml.preserve_quotes = False  # Don't preserve quotes - let YAML decide
        self.yaml.width = 4096  # Prevent line wrapping
        self.yaml.indent(mapping=2, sequence=2, offset=0)

    def read(self, file_path: Path) -> tuple[dict[str, Any], str]:
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
            raise FrontmatterError(f"Invalid YAML in {file_path}: {e}") from e

        # Ensure dependencies field exists for WP files only (backward compatibility with pre-0.11.0)
        if file_path.name.startswith("WP") and "dependencies" not in frontmatter:
            frontmatter["dependencies"] = []

        # Get body (everything after closing ---)
        body = "\n".join(lines[closing_idx + 1 :])

        return frontmatter, body

    def write(self, file_path: Path, frontmatter: dict[str, Any], body: str) -> None:
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

    def update_fields(self, file_path: Path, updates: dict[str, Any]) -> None:
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

    def _normalize_frontmatter(self, frontmatter: dict[str, Any]) -> CommentedMap:
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

        wp_pattern = re.compile(r"^WP\d{2}$")
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
        # Note: `lane` is no longer a required frontmatter field — lane state
        # is managed exclusively via the canonical event log.
        if file_path.name.startswith("WP"):
            required = ["work_package_id", "title"]
            for field in required:
                if field not in frontmatter:
                    errors.append(f"Missing required field: {field}")

            # Validate dependencies field (if present)
            if "dependencies" in frontmatter:
                dep_errors = self._validate_dependencies(frontmatter["dependencies"])
                errors.extend(dep_errors)

        return errors


# The runtime claim/workspace-creation frontmatter fields ``spec-kitty implement``
# writes into ``tasks/WP##.md`` at claim time (``shell_pid``/``shell_pid_created_at``)
# and at workspace-creation time (``base_branch``/``base_commit``/``planning_base_branch``).
# Derived from :attr:`FrontmatterManager.WP_FIELD_ORDER` -- the ONE canonical
# field-name source -- so this set can never diverge from the class that
# actually owns those field names (#2570.1). Consumed by
# ``cli.commands.implement_cores._drop_runtime_frontmatter_only_wp`` (WP01,
# the allocator's dirty-tree claim guard); move-task (WP07) reaches the same
# decision transitively by reusing that ``resolve_planning_artifact_staging``
# seam rather than re-classifying keys itself -- the ONE shared source so no
# consumer hardcodes a fresh (and driftable) runtime-field tuple.
_RUNTIME_FIELD_NAMES = (
    "shell_pid",
    SHELL_PID_BASELINE_FIELD,
    "base_branch",
    "base_commit",
    "planning_base_branch",
)
WP_RUNTIME_FIELDS: frozenset[str] = frozenset(
    field for field in FrontmatterManager.WP_FIELD_ORDER if field in _RUNTIME_FIELD_NAMES
)

# Global instance for convenience
_manager = FrontmatterManager()


# Convenience functions that use the global manager
def read_frontmatter(file_path: Path) -> tuple[dict[str, Any], str]:
    """Read frontmatter and body from a markdown file."""
    return _manager.read(file_path)


def write_frontmatter(file_path: Path, frontmatter: dict[str, Any], body: str) -> None:
    """Write frontmatter and body to a markdown file."""
    _manager.write(file_path, frontmatter, body)


def update_fields(file_path: Path, updates: dict[str, Any]) -> None:
    """Update multiple fields in frontmatter."""
    _manager.update_fields(file_path, updates)


def get_field(file_path: Path, field: str, default: Any = None) -> Any:
    """Get a single field from frontmatter."""
    return _manager.get_field(file_path, field, default)


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
    "SHELL_PID_BASELINE_FIELD",
    "WP_RUNTIME_FIELDS",
    "FrontmatterError",
    "FrontmatterManager",
    "read_frontmatter",
    "write_frontmatter",
    "update_fields",
    "get_field",
    "validate_frontmatter",
    "normalize_file",
]
