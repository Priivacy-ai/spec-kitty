"""Version compatibility checking for spec-kitty CLI and projects."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from packaging.version import Version, InvalidVersion

from specify_cli.upgrade.metadata import ProjectMetadata


MismatchType = Literal["cli_newer", "project_newer", "match", "unknown"]


def get_cli_version() -> str:
    """Get the installed spec-kitty-cli version.

    Returns:
        Version string (e.g., "0.9.0" or "0.5.0-dev")
    """
    try:
        from importlib.metadata import version as get_version
        return get_version("spec-kitty-cli")
    except Exception:
        # Fall back to __version__ from __init__.py
        try:
            from specify_cli import __version__
            return __version__
        except Exception:
            return "unknown"


def get_project_version(project_root: Path) -> Optional[str]:
    """Get the project's spec-kitty version from metadata.

    Args:
        project_root: Path to project root (parent of .kittify)

    Returns:
        Version string if metadata exists, None for legacy projects
    """
    kittify_dir = project_root / ".kittify"
    if not kittify_dir.exists():
        return None

    metadata = ProjectMetadata.load(kittify_dir)
    if metadata is None:
        return None

    return metadata.version


def compare_versions(cli_version: str, project_version: str) -> tuple[int, MismatchType]:
    """Compare CLI and project versions using semantic versioning.

    Args:
        cli_version: Installed CLI version
        project_version: Project's spec-kitty version

    Returns:
        Tuple of (comparison_result, mismatch_type):
        - comparison_result: -1 (CLI older), 0 (equal), 1 (CLI newer)
        - mismatch_type: Type of mismatch or "match"
    """
    # Handle unknown versions
    if cli_version == "unknown" or project_version == "unknown":
        return (0, "unknown")

    try:
        cli_ver = Version(cli_version)
        proj_ver = Version(project_version)

        if cli_ver > proj_ver:
            return (1, "cli_newer")
        elif cli_ver < proj_ver:
            return (-1, "project_newer")
        else:
            return (0, "match")

    except InvalidVersion:
        # If version parsing fails, treat as unknown
        return (0, "unknown")


def format_version_error(
    cli_version: str,
    project_version: str,
    mismatch_type: MismatchType
) -> str:
    """Format a user-facing error message for version mismatch.

    Args:
        cli_version: Installed CLI version
        project_version: Project's spec-kitty version
        mismatch_type: Type of mismatch

    Returns:
        Formatted error message with resolution instructions
    """
    border = "━" * 80

    if mismatch_type == "cli_newer":
        # Check if this is the critical 0.8.x -> 0.9.x upgrade
        try:
            from packaging.version import Version
            cli_ver = Version(cli_version)
            proj_ver = Version(project_version)
            is_090_upgrade = cli_ver >= Version("0.9.0") and proj_ver < Version("0.9.0")
        except Exception:
            is_090_upgrade = False

        if is_090_upgrade:
            return f"""
{border}
🚨 CRITICAL: BREAKING CHANGES - Version Mismatch Detected 🚨
{border}

CLI version:     {cli_version}  ← NEWER (v0.9.0+ has BREAKING CHANGES)
Project version: {project_version}  ← OLDER (pre-0.9.0 format)

⚠️  YOU CANNOT USE v0.9.0+ CLI WITH PRE-0.9.0 PROJECTS! ⚠️

╔════════════════════════════════════════════════════════════════════════════╗
║ 🔴 CRITICAL BREAKING CHANGE IN v0.9.0: LANE SYSTEM REDESIGNED 🔴          ║
╚════════════════════════════════════════════════════════════════════════════╝

📂 OLD STRUCTURE (pre-0.9.0):
   kitty-specs/<feature>/tasks/
   ├── planned/WP01.md
   ├── doing/WP02.md
   ├── for_review/WP03.md
   └── done/WP04.md

📂 NEW STRUCTURE (v0.9.0+):
   kitty-specs/<feature>/tasks/
   ├── WP01.md  (with "lane: planned" in frontmatter)
   ├── WP02.md  (with "lane: doing" in frontmatter)
   ├── WP03.md  (with "lane: for_review" in frontmatter)
   └── WP04.md  (with "lane: done" in frontmatter)

⚠️  THIS AFFECTS ALL YOUR HISTORICAL WORK IN kitty-specs/ ⚠️

🔧 REQUIRED ACTION - You MUST upgrade your project:

  spec-kitty upgrade

This will:
  ✅ Migrate ALL features from directory-based to frontmatter-only lanes
  ✅ Move all WP files from subdirectories to flat tasks/ directory
  ✅ Add "lane:" field to frontmatter in all WP files
  ✅ Update .kittify/metadata.yaml to v{cli_version}
  ✅ Remove empty lane subdirectories

🛡️  SAFETY: The upgrade is idempotent and safe to run multiple times.

❌ Commands are BLOCKED until you upgrade to prevent data corruption.

{border}
""".strip()
        else:
            return f"""
{border}
❌ ERROR: Version Mismatch Detected
{border}

CLI version:     {cli_version}
Project version: {project_version}

Your CLI is NEWER than your project.

This means your project templates and scripts are out of date.
Please upgrade your project to match:

  spec-kitty upgrade

This will update your project templates and configuration
to match the installed CLI version.

{border}
""".strip()

    elif mismatch_type == "project_newer":
        return f"""
{border}
❌ ERROR: Version Mismatch Detected
{border}

CLI version:     {cli_version}
Project version: {project_version}

Your project is NEWER than your CLI.

This project was created or upgraded with a newer version
of spec-kitty-cli. Please upgrade your CLI:

  pip install --upgrade spec-kitty-cli

After upgrading, run:

  spec-kitty --version

to verify the update.

{border}
""".strip()

    else:
        return f"Version mismatch: CLI={cli_version}, Project={project_version}"


def should_check_version(command_name: str) -> bool:
    """Determine if version check is required for a command.

    Args:
        command_name: Name of the command being executed

    Returns:
        True if version check required, False if should skip
    """
    # Commands that skip version check (they create or fix version issues)
    skip_commands = {
        "init",
        "upgrade",
        "version",  # --version flag
        "help",     # --help flag
    }

    return command_name not in skip_commands


__all__ = [
    "get_cli_version",
    "get_project_version",
    "compare_versions",
    "format_version_error",
    "should_check_version",
    "MismatchType",
]
