"""
Centralized mission detection for spec-kitty.

This module provides a single source of truth for detecting mission context
across all CLI commands and agent workflows. It replaces multiple scattered
implementations with a unified, deterministic, and well-tested approach.

Design principles:
- Deterministic by default (no "highest numbered" guessing)
- Explicit when ambiguous (error message guides user to --mission flag)
- Flexible modes (strict raises errors, lenient returns None)
- Consistent types (MissionContext dataclass for rich results)
- Well-tested (comprehensive test coverage for all scenarios)

Priority order:
1. Explicit --mission parameter (highest priority)
2. SPECIFY_MISSION / SPECIFY_FEATURE environment variable
3. Git branch name (strips -WP## suffix for worktree branches)
4. Current directory path (walk up looking for ###-mission-name)
5. Single mission auto-detect (only if exactly one mission exists)
6. Optional fallback to latest incomplete mission (opt-in only)
7. Error with clear guidance (if all missions complete or ambiguous)
"""

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from collections.abc import Mapping

from specify_cli.core.paths import get_main_repo_root as _resolve_main_repo_root


# ============================================================================
# Error Types
# ============================================================================


class MissionDetectionError(Exception):
    """Base exception for mission detection failures."""
    pass


class MultipleMissionsError(MissionDetectionError):
    """Raised when multiple missions exist and no context clarifies which."""

    def __init__(self, missions: list[str], message: str):
        super().__init__(message)
        self.missions = missions


class NoMissionFoundError(MissionDetectionError):
    """Raised when no mission can be detected."""
    pass


# ============================================================================
# Core Types
# ============================================================================


@dataclass
class MissionContext:
    """Rich result from mission detection.

    Attributes:
        slug: Full mission slug (e.g., "020-my-mission")
        number: Mission number only (e.g., "020")
        name: Mission name only (e.g., "my-mission")
        directory: Path to mission directory (e.g., Path("kitty-specs/020-my-mission"))
        detection_method: How mission was detected (e.g., "git_branch", "env_var", "explicit")
    """
    slug: str
    number: str
    name: str
    directory: Path
    detection_method: str

    @classmethod
    def from_slug(cls, slug: str, repo_root: Path, detection_method: str) -> "MissionContext":
        """Construct MissionContext from a mission slug.

        Args:
            slug: Mission slug in format ###-mission-name
            repo_root: Repository root path
            detection_method: How the mission was detected

        Returns:
            MissionContext instance

        Raises:
            MissionDetectionError: If slug format is invalid
        """
        match = re.match(r'^(\d{3})-(.+)$', slug)
        if not match:
            raise MissionDetectionError(
                f"Invalid mission slug format: {slug}\n"
                f"Expected format: ###-mission-name (e.g., 020-my-mission)"
            )

        number = match.group(1)
        name = match.group(2)
        directory = repo_root / "kitty-specs" / slug

        return cls(
            slug=slug,
            number=number,
            name=name,
            directory=directory,
            detection_method=detection_method,
        )


# ============================================================================
# Helper Functions (Internal)
# ============================================================================


def _get_main_repo_root(repo_root: Path) -> Path:
    """Get main repository root (handles worktree context).

    Args:
        repo_root: Repository root path (may be worktree)

    Returns:
        Main repository root path
    """
    return _resolve_main_repo_root(repo_root)


def _list_all_missions(repo_root: Path) -> list[str]:
    """List all mission directories in kitty-specs.

    Args:
        repo_root: Repository root path

    Returns:
        List of mission slugs (e.g., ["020-mission-a", "021-mission-b"])
    """
    main_repo_root = _get_main_repo_root(repo_root)
    kitty_specs_dir = main_repo_root / "kitty-specs"

    if not kitty_specs_dir.is_dir():
        return []

    missions = []
    for path in kitty_specs_dir.iterdir():
        if path.is_dir() and re.match(r'^\d{3}-', path.name):
            missions.append(path.name)

    return sorted(missions)


def _resolve_numeric_mission_slug(
    mission_number: str,
    repo_root: Path,
    *,
    mode: Literal["strict", "lenient"],
) -> str | None:
    """Resolve a 3-digit mission number (e.g., ``019``) to full slug.

    This is a compatibility affordance for agents that pass only the numeric
    mission id after parsing logs or UI text.
    """
    all_missions = _list_all_missions(repo_root)
    matches = [slug for slug in all_missions if slug.startswith(f"{mission_number}-")]

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        error_msg = (
            f"Mission number '{mission_number}' matches multiple missions:\n"
            + "\n".join(f"  - {slug}" for slug in matches)
            + "\n\nUse the full slug with --mission <###-mission-name>."
        )
        if mode == "strict":
            raise MultipleMissionsError(matches, error_msg)
        return None

    error_msg = (
        f"No mission found for number '{mission_number}'.\n\n"
        + "Available missions:\n"
        + "\n".join(f"  - {slug}" for slug in all_missions[:20])
    )
    if mode == "strict":
        raise NoMissionFoundError(error_msg)
    return None


def _detect_from_git_branch(repo_root: Path) -> str | None:
    """Detect mission from git branch name.

    Args:
        repo_root: Repository root path

    Returns:
        Mission slug if detected, None otherwise
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        branch = result.stdout.strip()

        # Pattern 1: Worktree branch (###-mission-name-WP##)
        # Check this FIRST - more specific pattern
        # Extract mission slug by removing -WP## suffix
        match = re.match(r'^((\d{3})-.+)-WP\d{2}$', branch)
        if match:
            mission_slug = match.group(1)
            return mission_slug

        # Pattern 2: Mission branch (###-mission-name)
        match = re.match(r'^(\d{3})-.+$', branch)
        if match:
            return branch

    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return None


def _detect_from_cwd(cwd: Path, repo_root: Path) -> str | None:
    """Detect mission from current working directory.

    Walks up the directory tree looking for ###-mission-name pattern.

    Args:
        cwd: Current working directory
        repo_root: Repository root path

    Returns:
        Mission slug if detected, None otherwise
    """
    # Walk up directory tree
    for parent in [cwd, *cwd.parents]:
        # Stop at repo root
        if parent == repo_root:
            break

        # Check for .worktrees/###-mission-name pattern
        if parent.name == ".worktrees":
            continue
        if ".worktrees" in parent.parts:
            parts = list(parent.parts)
            try:
                idx = parts.index(".worktrees")
                candidate = parts[idx + 1]
                # Strip -WP## suffix if present
                candidate = re.sub(r'-WP\d{2}$', '', candidate)
                if re.match(r'^\d{3}-.+$', candidate):
                    return candidate
            except (ValueError, IndexError):
                pass

        # Check for kitty-specs/###-mission-name pattern
        if parent.name == "kitty-specs":
            continue
        if "kitty-specs" in parent.parts:
            parts = list(parent.parts)
            try:
                idx = parts.index("kitty-specs")
                candidate = parts[idx + 1]
                if re.match(r'^\d{3}-.+$', candidate):
                    return candidate
            except (ValueError, IndexError):
                pass

        # Check if current directory itself matches pattern
        if re.match(r'^\d{3}-.+$', parent.name):
            return parent.name

    return None


def _validate_mission_exists(slug: str, repo_root: Path) -> bool:
    """Check if a mission directory exists.

    Args:
        slug: Mission slug
        repo_root: Repository root path

    Returns:
        True if mission directory exists
    """
    main_repo_root = _get_main_repo_root(repo_root)
    mission_dir = main_repo_root / "kitty-specs" / slug
    return mission_dir.is_dir()


def is_mission_complete(mission_dir: Path) -> bool:
    """Check if all work packages in a mission are complete.

    A mission is considered complete when all WP files have lane: 'done'.

    Args:
        mission_dir: Path to mission directory (e.g., kitty-specs/020-my-mission)

    Returns:
        True if all WPs have lane: 'done', False otherwise
        Returns False on any parse errors (safe default - mission stays incomplete)
    """
    from specify_cli.frontmatter import read_frontmatter

    tasks_dir = mission_dir / "tasks"
    if not tasks_dir.exists():
        return False

    wp_files = list(tasks_dir.glob("WP*.md"))
    if not wp_files:
        return False

    for wp_file in wp_files:
        try:
            frontmatter, _ = read_frontmatter(wp_file)
            lane = frontmatter.get("lane", "planned")
            if lane != "done":
                return False
        except Exception:
            # On any error, treat as incomplete (safe default)
            return False

    return True


def _is_mission_runnable(mission_dir: Path) -> bool:
    """Return True when a mission has concrete WP task files to operate on."""
    tasks_dir = mission_dir / "tasks"
    if not tasks_dir.exists():
        return False
    return any(tasks_dir.glob("WP*.md"))


# ============================================================================
# Core Detection Function
# ============================================================================


def detect_mission(
    repo_root: Path,
    *,
    explicit_mission: str | None = None,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    mode: Literal["strict", "lenient"] = "strict",
    allow_single_auto: bool = True,
    allow_latest_incomplete: bool = False,
    # Backward-compat alias — callers using ``explicit_feature=`` keep working.
    explicit_feature: str | None = None,
) -> MissionContext | None:
    """
    Unified mission detection with configurable behavior.

    Priority:
    1. explicit_mission parameter
    2. SPECIFY_MISSION / SPECIFY_FEATURE env var
    3. Git branch name (strips -WP## suffix)
    4. Current directory path (walks up to find ###-mission-name)
    5. Single mission auto-detect (if allow_single_auto=True)
    6. Optional latest-incomplete fallback (if allow_latest_incomplete=True)
    6. Error (strict mode) or None (lenient mode)

    Args:
        repo_root: Repository root path
        explicit_mission: Mission slug passed explicitly (highest priority)
        cwd: Current working directory (defaults to Path.cwd())
        env: Environment variables (defaults to os.environ)
        mode: "strict" raises error if ambiguous, "lenient" returns None
        allow_single_auto: Auto-detect if exactly one mission exists
        allow_latest_incomplete: Auto-select the latest incomplete mission
            when multiple missions exist and no other context is available.
        explicit_feature: Deprecated alias for explicit_mission (backward compat)

    Returns:
        MissionContext with detection details, or None in lenient mode

    Raises:
        MissionDetectionError: In strict mode when detection fails
        MultipleMissionsError: Multiple missions exist and none selected
        NoMissionFoundError: No missions found

    Examples:
        >>> # Explicit mission (highest priority)
        >>> ctx = detect_mission(Path("."), explicit_mission="020-my-mission")
        >>> ctx.slug
        '020-my-mission'

        >>> # From git branch
        >>> ctx = detect_mission(Path("."))  # Assumes git branch is "020-my-mission-WP01"
        >>> ctx.slug
        '020-my-mission'

        >>> # Lenient mode (returns None instead of raising)
        >>> ctx = detect_mission(Path("."), mode="lenient")
        >>> ctx is None
        True
    """
    # Merge deprecated alias into canonical parameter
    resolved_explicit = explicit_mission or explicit_feature

    env = env or os.environ
    cwd = cwd or Path.cwd()

    detected_slug: str | None = None
    detection_method: str = ""

    # Priority 1: Explicit --mission parameter
    if resolved_explicit:
        detected_slug = resolved_explicit.strip()
        if re.fullmatch(r"\d{3}", detected_slug):
            resolved = _resolve_numeric_mission_slug(detected_slug, repo_root, mode=mode)
            if resolved is None:
                return None
            detected_slug = resolved
            detection_method = "explicit_number"
        else:
            detection_method = "explicit"

    # Priority 2: SPECIFY_MISSION env var (primary), SPECIFY_FEATURE (deprecated fallback)
    elif ("SPECIFY_MISSION" in env and env["SPECIFY_MISSION"].strip()) or \
         ("SPECIFY_FEATURE" in env and env["SPECIFY_FEATURE"].strip()):
        detected_slug = (env.get("SPECIFY_MISSION", "").strip() or env.get("SPECIFY_FEATURE", "").strip())
        if re.fullmatch(r"\d{3}", detected_slug):
            resolved = _resolve_numeric_mission_slug(detected_slug, repo_root, mode=mode)
            if resolved is None:
                return None
            detected_slug = resolved
            detection_method = "env_var_number"
        else:
            detection_method = "env_var"

    # Priority 3: Git branch name
    elif (branch_slug := _detect_from_git_branch(repo_root)):
        detected_slug = branch_slug
        detection_method = "git_branch"

    # Priority 4: Current directory path
    elif (cwd_slug := _detect_from_cwd(cwd, repo_root)):
        detected_slug = cwd_slug
        detection_method = "cwd_path"

    # Priority 5: Single mission auto-detect
    elif allow_single_auto:
        all_missions = _list_all_missions(repo_root)
        if len(all_missions) == 1:
            detected_slug = all_missions[0]
            detection_method = "single_auto"
        elif len(all_missions) > 1:
            main_repo_root = _get_main_repo_root(repo_root)
            kitty_specs_dir = main_repo_root / "kitty-specs"
            incomplete_missions = [
                slug for slug in all_missions if not is_mission_complete(kitty_specs_dir / slug)
            ]

            if not incomplete_missions:
                error_msg = (
                    f"All missions are complete ({len(all_missions)} missions).\n\n"
                    + "Please specify explicitly using:\n"
                    + "  --mission <mission-slug>  (e.g., --mission 020-my-mission)\n"
                    + "  SPECIFY_MISSION=<mission-slug>  (environment variable)\n"
                    + "  Or create a new mission using:\n"
                    + "  spec-kitty specify\n"
                    + "  /spec-kitty.specify  (in agent workflow)"
                )
                if mode == "strict":
                    raise MultipleMissionsError(all_missions, error_msg)
                return None
            elif allow_latest_incomplete:
                detected_slug = incomplete_missions[-1]
                detection_method = "latest_incomplete"
            else:
                error_msg = (
                    f"Multiple missions found ({len(all_missions)} total, "
                    f"{len(incomplete_missions)} incomplete).\n\n"
                    "Please specify explicitly using:\n"
                    "  --mission <mission-slug>  (e.g., --mission 020-my-mission)\n"
                    "  SPECIFY_MISSION=<mission-slug>  (environment variable)\n"
                    "\nAvailable missions:\n"
                    + "\n".join(f"  - {slug}" for slug in all_missions[:20])
                )
                if len(all_missions) > 20:
                    error_msg += f"\n  ... and {len(all_missions) - 20} more"
                if mode == "strict":
                    raise MultipleMissionsError(all_missions, error_msg)
                return None
        else:
            # No missions found
            error_msg = (
                "No missions found in kitty-specs/\n\n"
                "Create a mission first using:\n"
                "  spec-kitty specify\n"
                "  /spec-kitty.specify  (in agent workflow)"
            )
            if mode == "strict":
                raise NoMissionFoundError(error_msg)
            return None

    # If still no slug detected
    if not detected_slug:
        error_msg = (
            "Unable to detect mission automatically.\n\n"
            "Please specify explicitly using:\n"
            "  --mission <mission-slug>  (e.g., --mission 020-my-mission)\n"
            "  SPECIFY_MISSION=<mission-slug>  (environment variable)\n"
            "  Or run from inside a mission directory or worktree"
        )
        if mode == "strict":
            raise NoMissionFoundError(error_msg)
        return None

    # Validate slug format FIRST (before checking if directory exists)
    if not re.match(r'^\d{3}-.+$', detected_slug):
        error_msg = (
            f"Invalid mission slug format: {detected_slug}\n"
            f"Expected format: ###-mission-name (e.g., 020-my-mission)"
        )
        if mode == "strict":
            raise MissionDetectionError(error_msg)
        return None

    # Validate mission exists
    if not _validate_mission_exists(detected_slug, repo_root):
        error_msg = (
            f"Mission directory not found: kitty-specs/{detected_slug}\n\n"
            f"Available missions:\n"
            + "\n".join(f"  - {m}" for m in _list_all_missions(repo_root))
            + "\n\nCreate the mission first using:\n"
            + "  spec-kitty specify\n"
            + "  /spec-kitty.specify  (in agent workflow)"
        )
        if mode == "strict":
            raise NoMissionFoundError(error_msg)
        return None

    # Build MissionContext using the MAIN repo root so that the directory
    # path always points to the real kitty-specs/ location (even when
    # called from a worktree that lacks kitty-specs/ via sparse checkout).
    main_repo_root = _get_main_repo_root(repo_root)
    try:
        return MissionContext.from_slug(detected_slug, main_repo_root, detection_method)
    except MissionDetectionError:
        if mode == "strict":
            raise
        return None


# ============================================================================
# Simplified Wrapper Functions
# ============================================================================


def detect_mission_slug(repo_root: Path, **kwargs) -> str:
    """Simplified wrapper that returns just the slug string.

    Args:
        repo_root: Repository root path
        **kwargs: Additional arguments passed to detect_mission()

    Returns:
        Mission slug (e.g., "020-my-mission")

    Raises:
        MissionDetectionError: If detection fails
    """
    # Force strict mode for this wrapper (always raises on failure)
    kwargs["mode"] = "strict"
    ctx = detect_mission(repo_root, **kwargs)
    assert ctx is not None  # Guaranteed in strict mode
    return ctx.slug


def detect_mission_directory(repo_root: Path, **kwargs) -> Path:
    """Simplified wrapper that returns just the directory Path.

    Args:
        repo_root: Repository root path
        **kwargs: Additional arguments passed to detect_mission()

    Returns:
        Path to mission directory (e.g., Path("kitty-specs/020-my-mission"))

    Raises:
        MissionDetectionError: If detection fails
    """
    # Force strict mode for this wrapper (always raises on failure)
    kwargs["mode"] = "strict"
    ctx = detect_mission(repo_root, **kwargs)
    assert ctx is not None  # Guaranteed in strict mode
    return ctx.directory


def get_mission_target_branch(repo_root: Path, mission_slug: str) -> str:
    """Get target branch for mission from meta.json.

    This function reads the target_branch field from a mission's meta.json file.
    The target_branch determines where status commits and implementation work
    should be routed (e.g., "main" for 1.x missions, "2.x" for SaaS missions).

    Args:
        repo_root: Repository root path (may be worktree)
        mission_slug: Mission slug (e.g., "025-cli-event-log-integration")

    Returns:
        Target branch name (defaults to "main" for legacy missions without
        the target_branch field, or if meta.json cannot be read)

    Examples:
        >>> # Mission targeting main branch
        >>> get_mission_target_branch(Path("."), "024-mission-name")
        'main'

        >>> # Mission targeting 2.x branch
        >>> get_mission_target_branch(Path("."), "025-cli-event-log-integration")
        '2.x'

    Note:
        This function always returns "main" as a safe default if:
        - meta.json doesn't exist
        - meta.json is malformed (invalid JSON)
        - target_branch field is missing
        - Any I/O error occurs

        This ensures backward compatibility with legacy missions created
        before the target_branch field was introduced (version 0.13.8).
    """
    import json
    from specify_cli.core.git_ops import resolve_primary_branch

    main_repo_root = _get_main_repo_root(repo_root)
    mission_dir = main_repo_root / "kitty-specs" / mission_slug
    meta_file = mission_dir / "meta.json"

    fallback = resolve_primary_branch(main_repo_root)

    if not meta_file.exists():
        return fallback

    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        return meta.get("target_branch", fallback)
    except (json.JSONDecodeError, KeyError, OSError):
        # Safe fallback for any error
        return fallback


# ============================================================================
# Backward-compatibility aliases
# ============================================================================

# These aliases allow existing callers (and test patch paths) to keep working
# during the transition period.  New code should use the Mission* names.
FeatureContext = MissionContext
FeatureDetectionError = MissionDetectionError
MultipleFeaturesError = MultipleMissionsError
NoFeatureFoundError = NoMissionFoundError
detect_feature = detect_mission
detect_feature_slug = detect_mission_slug
detect_feature_directory = detect_mission_directory
get_feature_target_branch = get_mission_target_branch
is_feature_complete = is_mission_complete

# Internal-function aliases so ``patch("…feature_detection._list_all_features")``
# style test paths keep resolving.
_list_all_features = _list_all_missions
_validate_feature_exists = _validate_mission_exists
_is_feature_runnable = _is_mission_runnable
_resolve_numeric_feature_slug = _resolve_numeric_mission_slug


# ============================================================================
# Exports
# ============================================================================


__all__ = [
    # Core types (canonical)
    "MissionContext",
    # Error types (canonical)
    "MissionDetectionError",
    "MultipleMissionsError",
    "NoMissionFoundError",
    # Core function (canonical)
    "detect_mission",
    # Simplified wrappers (canonical)
    "detect_mission_slug",
    "detect_mission_directory",
    # Target branch detection (canonical)
    "get_mission_target_branch",
    # Mission completeness check
    "is_mission_complete",
    # Backward-compat aliases (deprecated — use Mission* names)
    "FeatureContext",
    "FeatureDetectionError",
    "MultipleFeaturesError",
    "NoFeatureFoundError",
    "detect_feature",
    "detect_feature_slug",
    "detect_feature_directory",
    "get_feature_target_branch",
    "is_feature_complete",
    # Internal-function backward-compat aliases
    "_list_all_features",
    "_validate_feature_exists",
    "_is_feature_runnable",
    "_resolve_numeric_feature_slug",
]
