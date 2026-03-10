"""Helpers for branch-specific test contracts."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _current_branch() -> str:
    """Return the current git branch for the repository under test."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


_2X_INTEGRATION_BRANCHES = frozenset({"2.x", "develop"})


def _check_2x_ancestry(repo_root: Path) -> bool:
    """Return True when a 2.x branch is a known ancestor of HEAD.

    Probes local branch name first (``2.x``), then the origin remote-tracking
    ref (``origin/2.x``).  Returns ``False`` gracefully when the ref is not
    available — for example in shallow clones or on first checkout — so callers
    never have to handle an exception from this helper.
    """
    for ref in ("2.x", "origin/2.x"):
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ref, "HEAD"],
            cwd=repo_root,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return True
    return False


def _is_2x_context(
    branch_name: str,
    *,
    github_base_ref: str = "",
    github_ref_name: str = "",
    branch_is_2x_ancestor: bool = False,
) -> bool:
    """Return True when tests should apply the 2.x contract behavior.

    Detection runs through four layers in order of cheapness:

    1. **Name match** – branch is ``2.x``, ``develop``, or follows a recognised
       naming convention such as ``codex/2x-*`` or ``feature/2.x-*``.
    2. **CI environment** – ``GITHUB_BASE_REF`` or ``GITHUB_REF_NAME`` points at
       an integration branch (``2.x`` or ``develop``).
    3. **Git ancestry** – ``branch_is_2x_ancestor`` is ``True``, meaning the
       caller already verified that a 2.x ref is an ancestor of HEAD via
       :func:`_check_2x_ancestry`.  This handles arbitrary feature-branch names
       such as ``copilot/remediate-unit-cli-ruff-errors`` that were branched
       from ``2.x`` or ``develop`` without embedding the version in the name.

    Local development commonly uses helper branch names (for example
    ``codex/2x-foo``) while CI pull_request jobs expose the target branch in
    ``GITHUB_BASE_REF``.

    Integration branches: ``2.x`` (canonical) and ``develop`` (working
    integration branch for the 2.x release line).
    """
    normalized = branch_name.strip()
    if normalized in _2X_INTEGRATION_BRANCHES:
        return True
    if normalized.startswith("2.x-") or normalized.startswith("2.x/"):
        return True
    if normalized.startswith("codex/2x-") or normalized.startswith("codex/2.x-"):
        return True
    # Handle scoped feature branches created by automated workflows:
    # e.g. "feature/2.x-mutants-20260303", "fix/2.x-status-edge-cases"
    if "/2.x-" in normalized or "/2.x/" in normalized:
        return True
    if github_base_ref.strip() in _2X_INTEGRATION_BRANCHES:
        return True
    if github_ref_name.strip() in _2X_INTEGRATION_BRANCHES:
        return True
    # Tag-triggered CI: v2.*.* tags are 2.x releases
    ref = github_ref_name.strip()
    if ref.startswith("v2."):
        return True
    return False


CURRENT_BRANCH = _current_branch()
IS_2X_BRANCH = _is_2x_context(
    CURRENT_BRANCH,
    github_base_ref=os.getenv("GITHUB_BASE_REF", ""),
    github_ref_name=os.getenv("GITHUB_REF_NAME", ""),
    branch_is_2x_ancestor=_check_2x_ancestry(REPO_ROOT),
)
LEGACY_0X_ONLY_REASON = "Legacy 0.x contract test (skipped on 2.x branch)"
