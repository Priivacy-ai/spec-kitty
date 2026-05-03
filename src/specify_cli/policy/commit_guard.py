"""Pre-commit ownership guard.

Validates that staged files in a worktree belong to the WP's owned_files
scope and blocks modifications to kitty-specs/ from implementation branches.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field

from specify_cli.policy.config import CommitGuardConfig


@dataclass
class CommitGuardResult:
    """Result of pre-commit guard validation."""

    allowed: bool
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class OwnershipScope:
    """Active WP ownership context resolved at guard invocation time."""

    owned_files: list[str]
    active_wp_id: str | None = None
    lane_id: str | None = None
    context_source: str = "absent"
    diagnostic_code: str | None = None
    diagnostic_message: str | None = None
    warnings: list[str] = field(default_factory=list)


# Matches lane branches (kitty/mission-057-feat-lane-a)
_LANE_BRANCH_RE = re.compile(r"^kitty/mission-.+-lane-[a-z]$")


def is_implementation_branch(branch_name: str) -> bool:
    """Return True if the branch is a lane implementation branch."""
    return bool(_LANE_BRANCH_RE.match(branch_name))


def validate_staged_files(
    staged_files: list[str],
    owned_files: list[str],
    branch_name: str,
    policy: CommitGuardConfig,
    ownership_scope: OwnershipScope | None = None,
) -> CommitGuardResult:
    """Validate staged files against ownership and protected path rules.

    Args:
        staged_files: Relative paths of files staged for commit.
        owned_files: Glob patterns from WP frontmatter.
        branch_name: Current git branch name.
        policy: Commit guard configuration.
        ownership_scope: Active WP context resolved at guard invocation time.

    Returns:
        CommitGuardResult with allowed status and any violations.
    """
    if not policy.enabled or policy.mode == "off":
        return CommitGuardResult(allowed=True)

    if not is_implementation_branch(branch_name):
        return CommitGuardResult(allowed=True)

    violations: list[str] = []
    warnings = list(ownership_scope.warnings) if ownership_scope else []
    effective_owned_files = list(ownership_scope.owned_files) if ownership_scope else owned_files

    if policy.enforce_ownership and ownership_scope and ownership_scope.diagnostic_code:
        violations.append(
            ownership_scope.diagnostic_message
            or _format_context_diagnostic(ownership_scope)
        )

    # Check kitty-specs/ protection.
    if policy.block_kitty_specs:
        for f in staged_files:
            if f.startswith("kitty-specs/"):
                violations.append(
                    f"Protected path: {f} — implementation branches must not modify kitty-specs/"
                )

    # Check ownership enforcement.
    if (
        policy.enforce_ownership
        and ownership_scope
        and ownership_scope.active_wp_id
        and not effective_owned_files
        and not ownership_scope.diagnostic_code
    ):
        violations.append(
            "ACTIVE_WP_OWNERSHIP_MISSING: "
            f"active_wp={ownership_scope.active_wp_id} has no owned_files; "
            f"lane_id={ownership_scope.lane_id or 'unknown'}; "
            f"context_source={ownership_scope.context_source}"
        )

    if policy.enforce_ownership and effective_owned_files and not (ownership_scope and ownership_scope.diagnostic_code):
        for f in staged_files:
            if f.startswith("kitty-specs/"):
                continue  # Already flagged above
            if not _matches_any_glob(f, effective_owned_files):
                violations.append(_format_scope_violation(f, effective_owned_files, ownership_scope))

    if not violations:
        return CommitGuardResult(allowed=True, warnings=warnings)

    if policy.mode == "warn":
        return CommitGuardResult(allowed=True, warnings=warnings + violations)

    # mode == "block"
    return CommitGuardResult(allowed=False, violations=violations, warnings=warnings)


def _format_context_diagnostic(scope: OwnershipScope) -> str:
    return (
        f"{scope.diagnostic_code}: Cannot prove active WP for ownership guard; "
        f"active_wp={scope.active_wp_id or 'unknown'}; "
        f"lane_id={scope.lane_id or 'unknown'}; "
        f"context_source={scope.context_source}"
    )


def _format_scope_violation(
    filepath: str,
    owned_files: list[str],
    ownership_scope: OwnershipScope | None,
) -> str:
    if ownership_scope and ownership_scope.active_wp_id:
        return (
            f"ACTIVE_WP_SCOPE_VIOLATION: {filepath} is outside "
            f"active_wp={ownership_scope.active_wp_id} owned_files {owned_files}; "
            f"lane_id={ownership_scope.lane_id or 'unknown'}; "
            f"context_source={ownership_scope.context_source}"
        )
    return f"Out of scope: {filepath} — not matched by owned_files {owned_files}"


def _matches_any_glob(filepath: str, patterns: list[str]) -> bool:
    """Check if filepath matches any of the ownership glob patterns."""
    for pattern in patterns:
        if fnmatch.fnmatch(filepath, pattern):
            return True
        # Also check prefix match for ** patterns.
        prefix = pattern.replace("/**", "").replace("/*", "").rstrip("/")
        if prefix and filepath.startswith(prefix + "/"):
            return True
    return False
