"""
Centralized feature detection for spec-kitty.

This module provides a single source of truth for detecting feature context
across all CLI commands and agent workflows. It replaces multiple scattered
implementations with a unified, deterministic, and well-tested approach.

Design principles:
- Deterministic by default (no "highest numbered" guessing)
- Explicit when ambiguous (error message guides user to --feature flag)
- Flexible modes (strict raises errors, lenient returns None)
- Consistent types (FeatureContext dataclass for rich results)
- Well-tested (comprehensive test coverage for all scenarios)

Priority order:
1. Explicit --feature parameter (highest priority)
2. SPECIFY_FEATURE environment variable
3. Git branch name (strips -WP## suffix for worktree branches)
4. Current directory path (walk up looking for ###-feature-name)
5. Single feature auto-detect (only if exactly one feature exists)
6. Fallback to latest incomplete feature (auto-selects if no explicit context)
7. Error with clear guidance (if all features complete or ambiguous)
"""

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Optional


# ============================================================================
# Error Types
# ============================================================================


class FeatureDetectionError(Exception):
    """Base exception for feature detection failures."""
    pass


class MultipleFeaturesError(FeatureDetectionError):
    """Raised when multiple features exist and no context clarifies which."""

    def __init__(self, features: list[str], message: str):
        super().__init__(message)
        self.features = features


class NoFeatureFoundError(FeatureDetectionError):
    """Raised when no feature can be detected."""
    pass


# ============================================================================
# Core Types
# ============================================================================


@dataclass
class FeatureContext:
    """Rich result from feature detection.

    Attributes:
        slug: Full feature slug (e.g., "020-my-feature")
        number: Feature number only (e.g., "020")
        name: Feature name only (e.g., "my-feature")
        directory: Path to feature directory (e.g., Path("kitty-specs/020-my-feature"))
        detection_method: How feature was detected (e.g., "git_branch", "env_var", "explicit")
    """
    slug: str
    number: str
    name: str
    directory: Path
    detection_method: str

    @classmethod
    def from_slug(cls, slug: str, repo_root: Path, detection_method: str) -> "FeatureContext":
        """Construct FeatureContext from a feature slug.

        Args:
            slug: Feature slug in format ###-feature-name
            repo_root: Repository root path
            detection_method: How the feature was detected

        Returns:
            FeatureContext instance

        Raises:
            FeatureDetectionError: If slug format is invalid
        """
        match = re.match(r'^(\d{3})-(.+)$', slug)
        if not match:
            raise FeatureDetectionError(
                f"Invalid feature slug format: {slug}\n"
                f"Expected format: ###-feature-name (e.g., 020-my-feature)"
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
    # Check if we're in a worktree
    git_common_dir = repo_root / ".git"
    if git_common_dir.is_file():
        # Worktree: .git is a file pointing to actual git dir
        git_dir_content = git_common_dir.read_text().strip()
        if git_dir_content.startswith("gitdir: "):
            git_dir = Path(git_dir_content[8:])  # Remove "gitdir: " prefix
            # Git dir for worktree is: <main-repo>/.git/worktrees/<name>
            # Navigate up two levels to get main repo
            main_git_dir = git_dir.parent.parent
            return main_git_dir.parent  # Parent of .git is main repo root

    return repo_root


def _list_all_features(repo_root: Path) -> list[str]:
    """List all feature directories in kitty-specs.

    Args:
        repo_root: Repository root path

    Returns:
        List of feature slugs (e.g., ["020-feature-a", "021-feature-b"])
    """
    main_repo_root = _get_main_repo_root(repo_root)
    kitty_specs_dir = main_repo_root / "kitty-specs"

    if not kitty_specs_dir.is_dir():
        return []

    features = []
    for path in kitty_specs_dir.iterdir():
        if path.is_dir() and re.match(r'^\d{3}-', path.name):
            features.append(path.name)

    return sorted(features)


def _detect_from_git_branch(repo_root: Path) -> Optional[str]:
    """Detect feature from git branch name.

    Args:
        repo_root: Repository root path

    Returns:
        Feature slug if detected, None otherwise
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()

        # Pattern 1: Worktree branch (###-feature-name-WP##)
        # Check this FIRST - more specific pattern
        # Extract feature slug by removing -WP## suffix
        match = re.match(r'^((\d{3})-.+)-WP\d{2}$', branch)
        if match:
            feature_slug = match.group(1)
            return feature_slug

        # Pattern 2: Feature branch (###-feature-name)
        match = re.match(r'^(\d{3})-.+$', branch)
        if match:
            return branch

    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return None


def _detect_from_cwd(cwd: Path, repo_root: Path) -> Optional[str]:
    """Detect feature from current working directory.

    Walks up the directory tree looking for ###-feature-name pattern.

    Args:
        cwd: Current working directory
        repo_root: Repository root path

    Returns:
        Feature slug if detected, None otherwise
    """
    # Walk up directory tree
    for parent in [cwd, *cwd.parents]:
        # Stop at repo root
        if parent == repo_root or parent.parent == repo_root:
            break

        # Check for .worktrees/###-feature-name pattern
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

        # Check for kitty-specs/###-feature-name pattern
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


def _validate_feature_exists(slug: str, repo_root: Path) -> bool:
    """Check if a feature directory exists.

    Args:
        slug: Feature slug
        repo_root: Repository root path

    Returns:
        True if feature directory exists
    """
    main_repo_root = _get_main_repo_root(repo_root)
    feature_dir = main_repo_root / "kitty-specs" / slug
    return feature_dir.is_dir()


def is_feature_complete(feature_dir: Path) -> bool:
    """Check if all work packages in a feature are complete.

    A feature is considered complete when all WP files have lane: 'done'.

    Args:
        feature_dir: Path to feature directory (e.g., kitty-specs/020-my-feature)

    Returns:
        True if all WPs have lane: 'done', False otherwise
        Returns False on any parse errors (safe default - feature stays incomplete)
    """
    from specify_cli.frontmatter import read_frontmatter

    tasks_dir = feature_dir / "tasks"
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


def find_latest_incomplete_feature(repo_root: Path) -> Optional[str]:
    """Find the highest numbered incomplete feature.

    An incomplete feature is one where at least one WP has lane != 'done'.

    Args:
        repo_root: Repository root path

    Returns:
        Feature slug of the latest incomplete feature, or None if all complete
    """
    all_features = _list_all_features(repo_root)
    if not all_features:
        return None

    main_repo_root = _get_main_repo_root(repo_root)
    kitty_specs_dir = main_repo_root / "kitty-specs"
    incomplete = []

    for slug in all_features:
        feature_dir = kitty_specs_dir / slug
        if not is_feature_complete(feature_dir):
            incomplete.append(slug)

    if not incomplete:
        return None

    # Extract numbers and find highest
    def extract_num(s: str) -> int:
        m = re.match(r'^(\d{3})-', s)
        return int(m.group(1)) if m else 0

    return max(incomplete, key=extract_num)


# ============================================================================
# Core Detection Function
# ============================================================================


def detect_feature(
    repo_root: Path,
    *,
    explicit_feature: str | None = None,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    mode: Literal["strict", "lenient"] = "strict",
    allow_single_auto: bool = True,
) -> FeatureContext | None:
    """
    Unified feature detection with configurable behavior.

    Priority:
    1. explicit_feature parameter
    2. SPECIFY_FEATURE env var
    3. Git branch name (strips -WP## suffix)
    4. Current directory path (walks up to find ###-feature-name)
    5. Single feature auto-detect (if allow_single_auto=True)
    6. Fallback to latest incomplete feature (if explicit_feature is None)
    7. Error (strict mode) or None (lenient mode)

    Args:
        repo_root: Repository root path
        explicit_feature: Feature slug passed explicitly (highest priority)
        cwd: Current working directory (defaults to Path.cwd())
        env: Environment variables (defaults to os.environ)
        mode: "strict" raises error if ambiguous, "lenient" returns None
        allow_single_auto: Auto-detect if exactly one feature exists

    Returns:
        FeatureContext with detection details, or None in lenient mode

    Raises:
        FeatureDetectionError: In strict mode when detection fails
        MultipleFeaturesError: Multiple features exist and none selected
        NoFeatureFoundError: No features found

    Examples:
        >>> # Explicit feature (highest priority)
        >>> ctx = detect_feature(Path("."), explicit_feature="020-my-feature")
        >>> ctx.slug
        '020-my-feature'

        >>> # From git branch
        >>> ctx = detect_feature(Path("."))  # Assumes git branch is "020-my-feature-WP01"
        >>> ctx.slug
        '020-my-feature'

        >>> # Lenient mode (returns None instead of raising)
        >>> ctx = detect_feature(Path("."), mode="lenient")
        >>> ctx is None
        True
    """
    env = env or os.environ
    cwd = cwd or Path.cwd()

    detected_slug: Optional[str] = None
    detection_method: str = ""

    # Priority 1: Explicit --feature parameter
    if explicit_feature:
        detected_slug = explicit_feature.strip()
        detection_method = "explicit"

    # Priority 2: SPECIFY_FEATURE environment variable
    elif "SPECIFY_FEATURE" in env and env["SPECIFY_FEATURE"].strip():
        detected_slug = env["SPECIFY_FEATURE"].strip()
        detection_method = "env_var"

    # Priority 3: Git branch name
    elif (branch_slug := _detect_from_git_branch(repo_root)):
        detected_slug = branch_slug
        detection_method = "git_branch"

    # Priority 4: Current directory path
    elif (cwd_slug := _detect_from_cwd(cwd, repo_root)):
        detected_slug = cwd_slug
        detection_method = "cwd_path"

    # Priority 5: Single feature auto-detect
    elif allow_single_auto:
        all_features = _list_all_features(repo_root)
        if len(all_features) == 1:
            detected_slug = all_features[0]
            detection_method = "single_auto"
        elif len(all_features) > 1:
            # Priority 6: Fallback to latest incomplete feature
            # Only activate if no explicit feature requested (respect explicit choices)
            if explicit_feature is None:
                latest = find_latest_incomplete_feature(repo_root)
                if latest:
                    # Import console only if needed (avoid circular imports at module level)
                    try:
                        from rich.console import Console
                        console = Console()
                        console.print(f"[yellow]ℹ️  Auto-selected latest incomplete: {latest}[/yellow]")
                    except ImportError:
                        pass  # Silently skip if rich not available

                    detected_slug = latest
                    detection_method = "fallback_latest_incomplete"

            # Priority 7: Error (no fallback available or all features complete)
            if not detected_slug:
                # Check if all features are complete
                main_repo_root = _get_main_repo_root(repo_root)
                kitty_specs_dir = main_repo_root / "kitty-specs"
                all_complete = all(
                    is_feature_complete(kitty_specs_dir / slug)
                    for slug in all_features
                )

                if all_complete:
                    error_msg = (
                        f"All features are complete ({len(all_features)} features).\n\n"
                        + "Please specify explicitly using:\n"
                        + "  --feature <feature-slug>  (e.g., --feature 020-my-feature)\n"
                        + "  SPECIFY_FEATURE=<feature-slug>  (environment variable)\n"
                        + "  Or create a new feature using:\n"
                        + "  spec-kitty specify\n"
                        + "  /spec-kitty.specify  (in agent workflow)"
                    )
                else:
                    error_msg = (
                        f"Multiple features found ({len(all_features)}), cannot auto-detect:\n"
                        + "\n".join(f"  - {f}" for f in all_features[:10])
                        + ("\n  ... and more" if len(all_features) > 10 else "")
                        + "\n\nPlease specify explicitly using:\n"
                        + "  --feature <feature-slug>  (e.g., --feature 020-my-feature)\n"
                        + "  SPECIFY_FEATURE=<feature-slug>  (environment variable)\n"
                        + "  Or run from inside a feature directory or worktree"
                    )

                if mode == "strict":
                    raise MultipleFeaturesError(all_features, error_msg)
                return None
        else:
            # No features found
            error_msg = (
                "No features found in kitty-specs/\n\n"
                "Create a feature first using:\n"
                "  spec-kitty specify\n"
                "  /spec-kitty.specify  (in agent workflow)"
            )
            if mode == "strict":
                raise NoFeatureFoundError(error_msg)
            return None

    # If still no slug detected
    if not detected_slug:
        error_msg = (
            "Unable to detect feature automatically.\n\n"
            "Please specify explicitly using:\n"
            "  --feature <feature-slug>  (e.g., --feature 020-my-feature)\n"
            "  SPECIFY_FEATURE=<feature-slug>  (environment variable)\n"
            "  Or run from inside a feature directory or worktree"
        )
        if mode == "strict":
            raise NoFeatureFoundError(error_msg)
        return None

    # Validate slug format FIRST (before checking if directory exists)
    if not re.match(r'^\d{3}-.+$', detected_slug):
        error_msg = (
            f"Invalid feature slug format: {detected_slug}\n"
            f"Expected format: ###-feature-name (e.g., 020-my-feature)"
        )
        if mode == "strict":
            raise FeatureDetectionError(error_msg)
        return None

    # Validate feature exists
    if not _validate_feature_exists(detected_slug, repo_root):
        error_msg = (
            f"Feature directory not found: kitty-specs/{detected_slug}\n\n"
            f"Available features:\n"
            + "\n".join(f"  - {f}" for f in _list_all_features(repo_root))
            + "\n\nCreate the feature first using:\n"
            + "  spec-kitty specify\n"
            + "  /spec-kitty.specify  (in agent workflow)"
        )
        if mode == "strict":
            raise NoFeatureFoundError(error_msg)
        return None

    # Build FeatureContext (re-validates format, but we've already checked above)
    try:
        return FeatureContext.from_slug(detected_slug, repo_root, detection_method)
    except FeatureDetectionError:
        if mode == "strict":
            raise
        return None


# ============================================================================
# Simplified Wrapper Functions
# ============================================================================


def detect_feature_slug(repo_root: Path, **kwargs) -> str:
    """Simplified wrapper that returns just the slug string.

    Args:
        repo_root: Repository root path
        **kwargs: Additional arguments passed to detect_feature()

    Returns:
        Feature slug (e.g., "020-my-feature")

    Raises:
        FeatureDetectionError: If detection fails
    """
    # Force strict mode for this wrapper (always raises on failure)
    kwargs["mode"] = "strict"
    ctx = detect_feature(repo_root, **kwargs)
    assert ctx is not None  # Guaranteed in strict mode
    return ctx.slug


def detect_feature_directory(repo_root: Path, **kwargs) -> Path:
    """Simplified wrapper that returns just the directory Path.

    Args:
        repo_root: Repository root path
        **kwargs: Additional arguments passed to detect_feature()

    Returns:
        Path to feature directory (e.g., Path("kitty-specs/020-my-feature"))

    Raises:
        FeatureDetectionError: If detection fails
    """
    # Force strict mode for this wrapper (always raises on failure)
    kwargs["mode"] = "strict"
    ctx = detect_feature(repo_root, **kwargs)
    assert ctx is not None  # Guaranteed in strict mode
    return ctx.directory


def get_feature_target_branch(repo_root: Path, feature_slug: str) -> str:
    """Get target branch for feature from meta.json.

    This function reads the target_branch field from a feature's meta.json file.
    The target_branch determines where status commits and implementation work
    should be routed (e.g., "main" for 1.x features, "2.x" for SaaS features).

    Args:
        repo_root: Repository root path (may be worktree)
        feature_slug: Feature slug (e.g., "025-cli-event-log-integration")

    Returns:
        Target branch name (defaults to "main" for legacy features without
        the target_branch field, or if meta.json cannot be read)

    Examples:
        >>> # Feature targeting main branch
        >>> get_feature_target_branch(Path("."), "024-feature-name")
        'main'

        >>> # Feature targeting 2.x branch
        >>> get_feature_target_branch(Path("."), "025-cli-event-log-integration")
        '2.x'

    Note:
        This function always returns "main" as a safe default if:
        - meta.json doesn't exist
        - meta.json is malformed (invalid JSON)
        - target_branch field is missing
        - Any I/O error occurs

        This ensures backward compatibility with legacy features created
        before the target_branch field was introduced (version 0.13.8).
    """
    import json

    main_repo_root = _get_main_repo_root(repo_root)
    feature_dir = main_repo_root / "kitty-specs" / feature_slug
    meta_file = feature_dir / "meta.json"

    if not meta_file.exists():
        return "main"

    try:
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        return meta.get("target_branch", "main")
    except (json.JSONDecodeError, KeyError, OSError):
        # Safe fallback for any error
        return "main"


# ============================================================================
# Exports
# ============================================================================


__all__ = [
    # Core types
    "FeatureContext",
    # Error types
    "FeatureDetectionError",
    "MultipleFeaturesError",
    "NoFeatureFoundError",
    # Core function
    "detect_feature",
    # Simplified wrappers
    "detect_feature_slug",
    "detect_feature_directory",
    # Target branch detection
    "get_feature_target_branch",
]
