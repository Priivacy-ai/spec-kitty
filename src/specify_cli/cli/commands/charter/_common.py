"""Shared helpers used by multiple ``charter`` subcommands.

Lifted unchanged from the legacy ``charter.py`` during the WP06 MS-1 split.
Keep these helpers behaviour-preserving; if you need to specialise behaviour
for one subcommand, copy the helper into that subcommand module instead of
forking this file.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from charter.versioning import check_bundle_compatibility, get_bundle_schema_version

from specify_cli.task_utils import TaskCliError


def default_interview(*args: Any, **kwargs: Any) -> Any:
    """Patchable lazy wrapper for default charter interview generation."""
    from charter.interview import default_interview as _default_interview

    return _default_interview(*args, **kwargs)


def _resolve_charter_path(repo_root: Path) -> Path:
    """Find charter.md in canonical location only.

    Does not fall back to legacy locations. Users with pre-charter state
    must run 'spec-kitty upgrade' first (handled by the charter-rename migration).
    """
    charter_path = repo_root / ".kittify" / "charter" / "charter.md"
    if charter_path.exists():
        return charter_path

    raise TaskCliError(
        f"Charter not found at {charter_path}\n"
        "  Run 'spec-kitty charter interview' to create one,\n"
        "  or 'spec-kitty upgrade' if migrating from an older version."
    )


def _resolve_actor() -> str:
    """Return the git user email or ``"cli"`` as fallback."""
    try:
        result = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        email = result.stdout.strip()
        if email:
            return email
    except Exception:  # noqa: BLE001 — git may be absent or misconfigured; fall back to "cli" identity
        pass
    return "cli"


def _parse_csv_option(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    values = [part.strip() for part in raw.split(",")]
    normalized = [value for value in values if value]
    return normalized if normalized else []


def _interview_path(repo_root: Path) -> Path:
    return repo_root / ".kittify" / "charter" / "interview" / "answers.yaml"


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _assert_bundle_compatible(charter_dir: Path) -> None:
    """Raise TaskCliError if the bundle at charter_dir is not compatible with this CLI.

    Called by ``status``, ``resynthesize``, and ``bundle validate`` when the
    charter bundle directory is known to exist.  Fresh synthesis (no prior
    bundle) must NOT call this function — ``metadata.yaml`` would be absent.
    """
    bundle_version = get_bundle_schema_version(charter_dir)
    result = check_bundle_compatibility(bundle_version)
    if not result.is_compatible:
        raise TaskCliError(result.message)
