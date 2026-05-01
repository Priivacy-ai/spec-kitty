"""Audit target paths for codebase-wide work packages.

Defines the canonical set of directories that audit WPs should cover,
including all agent command directories, documentation, and template sources.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

from specify_cli.agent_utils.directories import AGENT_DIRS

__all__ = [
    "AUDIT_TEMPLATE_TARGETS",
    "get_audit_targets",
    "validate_audit_coverage",
]


def _build_audit_targets() -> tuple[str, ...]:
    """Build audit template targets from the canonical AGENT_DIRS list."""
    targets: list[str] = [
        "src/specify_cli/missions/*/command-templates/",
        "docs/",
    ]
    for agent_root, subdir in AGENT_DIRS:
        targets.append(f"{agent_root}/{subdir}/")
    return tuple(targets)


# Canonical list of directories that audit/codebase-wide WPs should cover.
# Derived from the agent directories in AGENT_DIRS plus template sources and docs.
AUDIT_TEMPLATE_TARGETS: tuple[str, ...] = _build_audit_targets()


def get_audit_targets(repo_root: Path) -> list[Path]:
    """Resolve audit template target patterns to directories that actually exist.

    Args:
        repo_root: Root directory of the repository.

    Returns:
        List of existing directory paths that match the audit target patterns.
    """
    existing: list[Path] = []
    for pattern in AUDIT_TEMPLATE_TARGETS:
        # Glob patterns with wildcards
        if "*" in pattern:
            # Strip trailing slash for globbing
            clean = pattern.rstrip("/")
            for match in sorted(repo_root.glob(clean)):
                if match.is_dir() and match not in existing:
                    existing.append(match)
        else:
            # Direct path
            target = repo_root / pattern.rstrip("/")
            if target.is_dir() and target not in existing:
                existing.append(target)
    return existing


def validate_audit_coverage(
    codebase_wide_owned_files: list[list[str]],
    repo_root: Path,
) -> list[str]:
    """Check whether codebase-wide WPs cover all audit template targets.

    This is a soft validation (warnings, not errors).  If there are no
    codebase-wide WPs, there is nothing to validate and no warnings are emitted.

    Args:
        codebase_wide_owned_files: List of owned_files lists from codebase-wide WPs.
        repo_root: Root directory of the repository.

    Returns:
        List of warning messages for uncovered audit targets.
    """
    if not codebase_wide_owned_files:
        return []

    warnings: list[str] = []
    targets = get_audit_targets(repo_root)

    for target in targets:
        target_str = str(target.relative_to(repo_root))
        covered = False
        for wp_files in codebase_wide_owned_files:
            for pattern in wp_files:
                # Check if the pattern covers the target directory
                if fnmatch.fnmatch(target_str, pattern):
                    covered = True
                    break
                if fnmatch.fnmatch(target_str + "/", pattern):
                    covered = True
                    break
                # Check prefix match: "**/*" covers everything
                if pattern in ("**/*", "**"):
                    covered = True
                    break
                # Check if the pattern is a parent of the target
                pattern_prefix = pattern.rstrip("*").rstrip("/")
                if pattern_prefix and target_str.startswith(pattern_prefix):
                    covered = True
                    break
            if covered:
                break
        if not covered:
            warnings.append(f"Audit target {target_str}/ not covered by any codebase-wide WP")

    return warnings
