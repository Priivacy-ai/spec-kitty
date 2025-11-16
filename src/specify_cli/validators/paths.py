"""Path convention validation helpers for Spec Kitty missions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List

from specify_cli.mission import Mission

__all__ = [
    "PathValidationError",
    "PathValidationResult",
    "suggest_directory_creation",
    "validate_mission_paths",
]


class PathValidationError(Exception):
    """Raised when required mission paths are missing in strict mode."""

    def __init__(self, result: "PathValidationResult") -> None:
        self.result = result
        message = result.format_errors() or "Path convention validation failed."
        super().__init__(message)


@dataclass
class PathValidationResult:
    """Result of validating mission-declared paths against the workspace."""

    mission_name: str
    required_paths: Dict[str, str]
    existing_paths: List[str] = field(default_factory=list)
    missing_paths: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True when every required path exists."""
        return not self.missing_paths

    def format_warnings(self) -> str:
        """Return human-readable warning text."""
        if not self.warnings:
            return ""

        lines = ["Path Convention Warnings:"]
        for warning in self.warnings:
            lines.append(f"  - {warning}")

        if self.suggestions:
            lines.append("")
            lines.append("Suggestions:")
            for suggestion in self.suggestions:
                lines.append(f"  - {suggestion}")

        return "\n".join(lines)

    def format_errors(self) -> str:
        """Return human-readable error text for strict enforcement."""
        if self.is_valid:
            return ""

        lines = ["Path Convention Errors:"]
        for warning in self.warnings:
            lines.append(f"  - {warning}")

        if self.suggestions:
            lines.append("")
            lines.append("Required Actions:")
            for suggestion in self.suggestions:
                lines.append(f"  - {suggestion}")

        lines.append("")
        lines.append(
            "These directories are required by the active mission. "
            "Create them before continuing."
        )
        return "\n".join(lines)


def suggest_directory_creation(missing_paths: Iterable[str]) -> List[str]:
    """Generate shell-friendly suggestions for fixing missing paths."""

    missing = list(missing_paths)
    suggestions: List[str] = []

    for path_str in missing:
        path = Path(path_str)
        if path_str.endswith("/"):
            suggestions.append(f"mkdir -p {path_str}")
        elif "." in path.name:
            parent = path.parent
            if parent and str(parent) not in {"", "."}:
                suggestions.append(f"mkdir -p {parent} && touch {path_str}")
            else:
                suggestions.append(f"touch {path_str}")
        else:
            suggestions.append(f"mkdir -p {path_str}")

    dir_paths = [p for p in missing if p.endswith("/")]
    if len(dir_paths) > 1:
        joined = " ".join(dir_paths)
        suggestions.insert(0, f"Create directories in one go: mkdir -p {joined}")

    return suggestions


def validate_mission_paths(
    mission: Mission,
    project_root: Path,
    *,
    strict: bool = False,
) -> PathValidationResult:
    """Validate that project directories follow mission-defined conventions.

    Args:
        mission: Mission containing declared path conventions.
        project_root: Root of the active workspace/worktree.
        strict: When True, raise PathValidationError if paths are missing.

    Returns:
        PathValidationResult summarising the state of each required path.
    """

    required_paths = dict(mission.config.paths or {})
    result = PathValidationResult(
        mission_name=mission.name,
        required_paths=required_paths,
    )

    if not required_paths:
        return result

    for key, relative_path in required_paths.items():
        candidate = Path(relative_path)
        full_path = candidate if candidate.is_absolute() else project_root / candidate
        if full_path.exists():
            result.existing_paths.append(relative_path)
            continue

        result.missing_paths.append(relative_path)
        result.warnings.append(
            f"{mission.name} expects {key} path: {relative_path} (not found)"
        )

    if result.missing_paths:
        result.suggestions = suggest_directory_creation(result.missing_paths)
        if strict:
            raise PathValidationError(result)

    return result
