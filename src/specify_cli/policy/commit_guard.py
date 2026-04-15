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
) -> CommitGuardResult:
    """Validate staged files against ownership and protected path rules.

    Args:
        staged_files: Relative paths of files staged for commit.
        owned_files: Glob patterns from WP frontmatter.
        branch_name: Current git branch name.
        policy: Commit guard configuration.

    Returns:
        CommitGuardResult with allowed status and any violations.
    """
    if not policy.enabled or policy.mode == "off":
        return CommitGuardResult(allowed=True)

    if not is_implementation_branch(branch_name):
        return CommitGuardResult(allowed=True)

    violations: list[str] = []

    # Check kitty-specs/ protection.
    if policy.block_kitty_specs:
        for f in staged_files:
            if f.startswith("kitty-specs/"):
                violations.append(
                    f"Protected path: {f} — implementation branches must not modify kitty-specs/"
                )

    # Check ownership enforcement.
    if policy.enforce_ownership and owned_files:
        for f in staged_files:
            if f.startswith("kitty-specs/"):
                continue  # Already flagged above
            if not _matches_any_glob(f, owned_files):
                violations.append(
                    f"Out of scope: {f} — not matched by owned_files {owned_files}"
                )

    if not violations:
        return CommitGuardResult(allowed=True)

    if policy.mode == "warn":
        return CommitGuardResult(allowed=True, warnings=violations)

    # mode == "block"
    return CommitGuardResult(allowed=False, violations=violations)


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
