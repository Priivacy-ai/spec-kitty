"""Helpers for branch-specific test contracts."""

from __future__ import annotations

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


CURRENT_BRANCH = _current_branch()
IS_2X_BRANCH = CURRENT_BRANCH == "2.x"
LEGACY_0X_ONLY_REASON = "Legacy 0.x contract test (skipped on 2.x branch)"
