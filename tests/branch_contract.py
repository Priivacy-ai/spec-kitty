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


def _is_2x_context(
    branch_name: str,
    *,
    github_base_ref: str = "",
    github_ref_name: str = "",
) -> bool:
    """Return True when tests should apply the 2.x contract behavior.

    Local development commonly uses helper branch names (for example
    ``codex/2x-foo``) while CI pull_request jobs expose the target branch in
    ``GITHUB_BASE_REF``.
    """
    normalized = branch_name.strip()
    if normalized == "2.x":
        return True
    if normalized.startswith("2.x-") or normalized.startswith("2.x/"):
        return True
    if normalized.startswith("codex/2x-") or normalized.startswith("codex/2.x-"):
        return True
    if github_base_ref.strip() == "2.x":
        return True
    if github_ref_name.strip() == "2.x":
        return True
    return False


CURRENT_BRANCH = _current_branch()
IS_2X_BRANCH = _is_2x_context(
    CURRENT_BRANCH,
    github_base_ref=os.getenv("GITHUB_BASE_REF", ""),
    github_ref_name=os.getenv("GITHUB_REF_NAME", ""),
)
LEGACY_0X_ONLY_REASON = "Legacy 0.x contract test (skipped on 2.x branch)"
