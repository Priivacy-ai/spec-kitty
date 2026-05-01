"""Ownership validation for spec-kitty work packages.

Validates that:
- No two WPs have overlapping owned_files glob patterns.
- Each WP's authoritative_surface is a prefix of at least one owned_files entry.
- execution_mode is consistent with the owned_files paths (warnings only).

Codebase-wide WPs (scope == "codebase-wide") are exempt from overlap,
authoritative-surface, and execution-mode consistency checks.
"""

from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

from specify_cli.ownership.models import ExecutionMode, OwnershipManifest

__all__ = [
    "ValidationResult",
    "validate_no_overlap",
    "validate_authoritative_surface",
    "validate_execution_mode_consistency",
    "validate_all",
    "validate_ownership",
    "validate_glob_matches",
]

logger = logging.getLogger(__name__)

# Paths considered "planning only" for execution_mode consistency checks.
_PLANNING_PREFIXES = ("kitty-specs/", "docs/")
# Paths considered "code" for execution_mode consistency checks.
_CODE_PREFIXES = ("src/", "tests/")


@dataclass
class ValidationResult:
    """Structured result of ownership validation across all WPs in a feature."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if there are no hard errors."""
        return len(self.errors) == 0


def _globs_overlap(pattern_a: str, pattern_b: str) -> bool:
    """Return True if the two glob patterns can match a common path.

    Strategy: we test whether each pattern matches the other as a literal,
    and also whether a synthetic "worst-case" path derived from each pattern
    is matched by the other.  This catches the most common overlap cases
    (e.g. ``src/**`` vs ``src/context/**``) without requiring pathspec.
    """
    # Exact equality → trivially overlap
    if pattern_a == pattern_b:
        return True

    # Strip trailing wildcards to get the path prefix of each pattern.
    def _prefix(pattern: str) -> str:
        for suffix in ("/**", "/*", "**", "*"):
            if pattern.endswith(suffix):
                return pattern[: -len(suffix)]
        return pattern

    prefix_a = _prefix(pattern_a)
    prefix_b = _prefix(pattern_b)

    # One prefix is a path-prefix of the other → the globs overlap.
    if prefix_a and prefix_b:
        if prefix_b.startswith(prefix_a) or prefix_a.startswith(prefix_b):
            return True

    # Fnmatch cross-check: does pattern_a match the literal prefix_b (or vice versa)?
    if fnmatch.fnmatch(prefix_b, pattern_a) or fnmatch.fnmatch(prefix_a, pattern_b):
        return True

    return False


def validate_no_overlap(manifests: dict[str, OwnershipManifest]) -> list[str]:
    """Check that no two WPs have overlapping owned_files glob patterns.

    Codebase-wide WPs are excluded from overlap checks because they are
    expected to overlap with everything -- that is their purpose.

    Args:
        manifests: Mapping of WP ID (e.g. ``"WP01"``) to its OwnershipManifest.

    Returns:
        List of error messages.  Empty list means no overlaps detected.
    """
    errors: list[str] = []

    # Filter out codebase-wide WPs -- they are allowed to overlap with anything.
    narrow_manifests = {
        wp_id: m for wp_id, m in manifests.items() if not m.is_codebase_wide
    }
    skipped = set(manifests.keys()) - set(narrow_manifests.keys())
    for wp_id in sorted(skipped):
        logger.info("Skipping overlap check for %s (codebase-wide scope)", wp_id)

    wp_ids = list(narrow_manifests.keys())

    for wp_a, wp_b in combinations(wp_ids, 2):
        manifest_a = narrow_manifests[wp_a]
        manifest_b = narrow_manifests[wp_b]

        for glob_a in manifest_a.owned_files:
            for glob_b in manifest_b.owned_files:
                if _globs_overlap(glob_a, glob_b):
                    errors.append(
                        f"Overlap: {wp_a} ({glob_a!r}) and {wp_b} ({glob_b!r}) "
                        f"claim overlapping paths."
                    )

    return errors


def validate_authoritative_surface(manifest: OwnershipManifest) -> list[str]:
    """Check that authoritative_surface is a prefix of at least one owned_files entry.

    Codebase-wide WPs are skipped -- they may have broad authoritative_surface
    values like ``"/"`` that do not follow the narrow prefix convention.

    Args:
        manifest: The OwnershipManifest to validate.

    Returns:
        List of error messages.  Empty list means the manifest is valid.
    """
    if manifest.is_codebase_wide:
        return []

    errors: list[str] = []
    surface = manifest.authoritative_surface

    if not surface:
        errors.append("authoritative_surface is empty.")
        return errors

    for pattern in manifest.owned_files:
        if pattern == surface or pattern.startswith(surface):
            return []  # At least one match — valid

    errors.append(
        f"authoritative_surface {surface!r} is not a prefix of any owned_files entry: "
        f"{list(manifest.owned_files)!r}"
    )
    return errors


def validate_execution_mode_consistency(manifest: OwnershipManifest) -> list[str]:
    """Warn when owned_files are inconsistent with execution_mode.

    These are warnings, not hard errors, because users can manually override
    inferred values.  Codebase-wide WPs are exempt because an audit WP may
    legitimately mix code and planning paths.

    Args:
        manifest: The OwnershipManifest to check.

    Returns:
        List of warning messages.  Empty list means no inconsistencies found.
    """
    if manifest.is_codebase_wide:
        return []

    warnings: list[str] = []

    if manifest.execution_mode == ExecutionMode.PLANNING_ARTIFACT:
        # All owned_files should be under kitty-specs/ or docs/
        bad = [
            p
            for p in manifest.owned_files
            if not any(p.startswith(prefix) for prefix in _PLANNING_PREFIXES)
        ]
        if bad:
            warnings.append(
                f"planning_artifact WP owns files outside planning paths "
                f"(kitty-specs/, docs/): {bad!r}"
            )

    elif manifest.execution_mode == ExecutionMode.CODE_CHANGE:
        # At least one owned_files entry should be under src/ or tests/ (not kitty-specs-only)
        has_code_path = any(
            p.startswith(prefix) for p in manifest.owned_files for prefix in _CODE_PREFIXES
        )
        if manifest.owned_files and not has_code_path:
            warnings.append(
                f"code_change WP does not own any files under src/ or tests/. "
                f"owned_files: {list(manifest.owned_files)!r}"
            )

    return warnings


def validate_all(manifests: dict[str, OwnershipManifest]) -> ValidationResult:
    """Run all ownership validations across every WP in a feature.

    Args:
        manifests: Mapping of WP ID to OwnershipManifest.

    Returns:
        A ValidationResult with errors (hard) and warnings (soft).
    """
    result = ValidationResult()

    # Cross-WP: overlap detection (hard error)
    result.errors.extend(validate_no_overlap(manifests))

    # Per-WP: authoritative_surface prefix (hard error)
    # Per-WP: execution_mode consistency (warning)
    for wp_id, manifest in manifests.items():
        surface_errors = validate_authoritative_surface(manifest)
        result.errors.extend(f"{wp_id}: {e}" for e in surface_errors)

        mode_warnings = validate_execution_mode_consistency(manifest)
        result.warnings.extend(f"{wp_id}: {w}" for w in mode_warnings)

    return result


# Public alias used by __init__.py
validate_ownership = validate_all


def validate_glob_matches(
    manifests: dict[str, OwnershipManifest],
    repo_root: Path,
) -> list[str]:
    """Warn when owned_files globs match zero files in the repository.

    This is a soft check — it returns warnings, not errors.  A zero-match
    glob is not a hard failure because WPs may legitimately target files
    that do not yet exist (new file creation), but it is suspicious enough
    to warrant a warning so operators can verify the pattern is correct.

    Args:
        manifests: Mapping of WP ID to OwnershipManifest.
        repo_root: Root directory of the repository for glob resolution.

    Returns:
        List of warning messages.  Empty list means all globs matched at
        least one file.
    """
    warnings: list[str] = []
    for wp_id in sorted(manifests):
        manifest = manifests[wp_id]
        for pattern in manifest.owned_files:
            if not any(repo_root.glob(pattern)):
                warnings.append(
                    f"{wp_id}: owned_files glob '{pattern}' matches "
                    f"zero files in the repository"
                )
    return warnings
