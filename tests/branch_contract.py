"""Helpers for branch-specific test contracts."""

from __future__ import annotations

import os
import subprocess
import tomllib
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


def _current_project_version() -> str:
    """Return the checked-out project version from pyproject.toml."""
    pyproject_path = REPO_ROOT / "pyproject.toml"
    if not pyproject_path.exists():
        return ""

    try:
        with pyproject_path.open("rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return ""

    version = data.get("project", {}).get("version", "")
    return str(version).strip()


def _is_2x_context(
    branch_name: str,
    *,
    github_base_ref: str = "",
    github_ref_name: str = "",
    project_version: str = "",
) -> bool:
    """Return True when tests should apply the 2.x contract behavior.

    Prefer the checked-out project version because mission branches based on
    2.x often use unrelated branch names. Fall back to branch and CI refs for
    contexts where the version is unavailable.
    """
    version = project_version.strip().removeprefix("v")
    if version.startswith("2."):
        return True

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
    # Tag-triggered CI: v2.*.* tags are 2.x releases
    ref = github_ref_name.strip()
    return bool(ref.startswith("v2."))


CURRENT_BRANCH = _current_branch()
CURRENT_PROJECT_VERSION = _current_project_version()
IS_2X_BRANCH = _is_2x_context(
    CURRENT_BRANCH,
    github_base_ref=os.getenv("GITHUB_BASE_REF", ""),
    github_ref_name=os.getenv("GITHUB_REF_NAME", ""),
    project_version=CURRENT_PROJECT_VERSION,
)
LEGACY_0X_ONLY_REASON = "Legacy 0.x contract test (skipped on 2.x branch)"
