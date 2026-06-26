"""Path convention validation helpers for Spec Kitty missions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from collections.abc import Iterable

from specify_cli.mission import Mission

__all__ = [
    "PathValidationError",
    "PathValidationResult",
    "suggest_directory_creation",
    "validate_mission_paths",
]


class PathValidationError(Exception):
    """Raised when required mission paths are missing in strict mode."""

    def __init__(self, result: PathValidationResult) -> None:
        self.result = result
        message = result.format_errors() or "Path convention validation failed."
        super().__init__(message)


@dataclass
class PathValidationResult:
    """Result of validating mission-declared paths against the workspace."""

    mission_name: str
    required_paths: dict[str, str]
    existing_paths: list[str] = field(default_factory=list)
    missing_paths: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

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
        lines.append("These directories are required by the active mission. Create them before continuing.")
        return "\n".join(lines)


def suggest_directory_creation(missing_paths: Iterable[str]) -> list[str]:
    """Generate shell-friendly suggestions for fixing missing paths."""

    missing = list(missing_paths)
    suggestions: list[str] = []

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


def _prefix_required_path(path_prefix: str | Path | None, relative_path: str) -> str:
    """Return ``relative_path`` under ``path_prefix`` while preserving dir hints."""

    if not path_prefix:
        return relative_path
    candidate = Path(relative_path)
    if candidate.is_absolute():
        return relative_path

    prefix = str(path_prefix).strip().strip("/")
    if not prefix:
        return relative_path

    relative = relative_path.strip("/")
    joined = PurePosixPath(prefix) / relative
    if relative_path.endswith("/"):
        return joined.as_posix() + "/"
    return joined.as_posix()


def _normalize_path_token(token: str) -> str:
    """Normalise a path/artifact token for membership comparison (strip slashes)."""
    return str(token).strip().strip("/")


def validate_mission_paths(
    mission: Mission,
    project_root: Path,
    *,
    strict: bool = False,
    path_prefix: str | Path | None = None,
    feature_dir: Path | None = None,
) -> PathValidationResult:
    """Validate that project directories follow mission-defined conventions.

    Args:
        mission: Mission containing declared path conventions.
        project_root: Root of the active workspace/worktree.
        strict: When True, raise PathValidationError if paths are missing.
        path_prefix: Optional project-relative prefix to apply before checking
            mission-declared paths. Research missions use this to validate
            configured deliverable directories instead of fixed repository-root
            directories.
        feature_dir: The mission's PRIMARY-surface directory
            (``kitty-specs/<mission>/``). When supplied, a declared path that is
            also a mission artifact (a member of ``mission.config.artifacts``,
            e.g. ``contracts/``) is resolved against ``feature_dir`` — those live
            with the mission, NOT at the repo root. Build/repo paths
            (``src/``/``tests/``/``docs/``) keep resolving against ``project_root``.
            There is no repo-root fallback for an artifact path (#2115 / #1716
            residual of the "no resolution to the repo primary" rule — it mirrors
            the #2113 ``_planning_read_dir`` seam). Research's ``path_prefix``
            routing is unaffected.

    Returns:
        PathValidationResult summarising the state of each required path.
    """

    declared = dict(mission.config.paths or {})
    required_paths = {
        key: _prefix_required_path(path_prefix, relative_path)
        for key, relative_path in declared.items()
    }
    result = PathValidationResult(
        mission_name=mission.name,
        required_paths=required_paths,
    )

    if not required_paths:
        return result

    # Mission-artifact path tokens (e.g. ``contracts/``) — resolved against the
    # mission's feature_dir rather than the repo root. Only consulted when a
    # feature_dir is supplied and we are not in research's path_prefix mode.
    artifact_tokens: set[str] = set()
    if feature_dir is not None and not path_prefix:
        # Defensive: a real ``MissionConfig`` always carries ``artifacts``, but a
        # partial mock/config may not — treat its absence as "no artifact paths"
        # (all paths resolve at the repo root, the pre-feature_dir behaviour).
        artifacts = getattr(mission.config, "artifacts", None)
        required = getattr(artifacts, "required", ()) or ()
        optional = getattr(artifacts, "optional", ()) or ()
        artifact_tokens = {
            _normalize_path_token(name) for name in (*required, *optional)
        }

    for key, relative_path in required_paths.items():
        candidate = Path(relative_path)
        if candidate.is_absolute():
            full_path = candidate
        elif _normalize_path_token(declared[key]) in artifact_tokens:
            # Mission artifact → resolve on the mission's primary surface.
            full_path = feature_dir / candidate  # type: ignore[operator]
        else:
            full_path = project_root / candidate
        if full_path.exists():
            result.existing_paths.append(relative_path)
            continue

        result.missing_paths.append(relative_path)
        result.warnings.append(f"{mission.name} expects {key} path: {relative_path} (not found)")

    if result.missing_paths:
        result.suggestions = suggest_directory_creation(result.missing_paths)
        if strict:
            raise PathValidationError(result)

    return result
