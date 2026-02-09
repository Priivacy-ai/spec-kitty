"""Migration from per-project .kittify/ to centralized runtime model.

Classifies per-project files as identical/customized/project-specific
and migrates them accordingly:
- IDENTICAL: removed (byte-identical to global runtime)
- CUSTOMIZED: moved to .kittify/overrides/
- PROJECT_SPECIFIC: kept in place
- UNKNOWN: kept in place with warning
"""

from __future__ import annotations

import filecmp
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from specify_cli.runtime.home import get_kittify_home


class AssetDisposition(Enum):
    """Classification of a per-project .kittify/ file."""

    IDENTICAL = "identical"  # Remove (byte-identical to global)
    CUSTOMIZED = "customized"  # Move to overrides
    PROJECT_SPECIFIC = "project_specific"  # Keep
    UNKNOWN = "unknown"  # Keep + warn


# Paths within .kittify/ that are always project-specific (never shared assets)
PROJECT_SPECIFIC_PATHS = {
    "config.yaml",
    "metadata.yaml",
    "memory",
    "workspaces",
    "logs",
    "overrides",
    "merge-state.json",
}

# Directories within .kittify/ that contain shared assets (may exist in global)
SHARED_ASSET_DIRS = {"templates", "missions", "scripts", "command-templates"}

# Individual files at .kittify/ root that are shared assets
SHARED_ASSET_FILES = {"AGENTS.md"}


def classify_asset(
    local_path: Path,
    global_home: Path,
    project_kittify: Path,
    mission: str = "software-dev",
) -> AssetDisposition:
    """Classify a per-project .kittify/ file.

    Args:
        local_path: Absolute path to the file inside per-project .kittify/
        global_home: Path to the global ~/.kittify/ directory
        project_kittify: Path to the per-project .kittify/ directory
        mission: Mission name for locating global counterparts

    Returns:
        AssetDisposition indicating how the file should be handled.
    """
    rel = local_path.relative_to(project_kittify)
    top_level = rel.parts[0] if rel.parts else ""

    # Project-specific paths: always keep
    if top_level in PROJECT_SPECIFIC_PATHS:
        return AssetDisposition.PROJECT_SPECIFIC

    # Shared asset: compare to global
    if top_level in SHARED_ASSET_DIRS or rel.name in SHARED_ASSET_FILES:
        # Find corresponding global file: try mission-specific path first
        global_path = global_home / "missions" / mission / str(rel)
        if not global_path.exists():
            # Fall back to direct path under global home
            global_path = global_home / str(rel)

        if global_path.exists() and local_path.is_file() and global_path.is_file():
            if filecmp.cmp(str(local_path), str(global_path), shallow=False):
                return AssetDisposition.IDENTICAL
            return AssetDisposition.CUSTOMIZED

        # No global counterpart found = treat as customized (user-created)
        return AssetDisposition.CUSTOMIZED

    return AssetDisposition.UNKNOWN


@dataclass
class MigrationReport:
    """Report of migration actions taken (or planned in dry-run mode)."""

    removed: list[Path] = field(default_factory=list)
    moved: list[tuple[Path, Path]] = field(default_factory=list)  # (from, to)
    kept: list[Path] = field(default_factory=list)
    unknown: list[Path] = field(default_factory=list)
    dry_run: bool = False


def execute_migration(
    project_dir: Path,
    dry_run: bool = False,
    verbose: bool = False,
    mission: str = "software-dev",
) -> MigrationReport:
    """Scan and migrate per-project .kittify/ shared assets.

    Identical files are removed, customized files are moved to
    .kittify/overrides/, and project-specific files are kept in place.

    Args:
        project_dir: Root of the project containing .kittify/
        dry_run: If True, report what would happen without modifying the filesystem
        verbose: If True, enable verbose output (reserved for CLI layer)
        mission: Mission name for global asset lookup

    Returns:
        MigrationReport with lists of affected files.
    """
    kittify_dir = project_dir / ".kittify"
    global_home = get_kittify_home()
    report = MigrationReport(dry_run=dry_run)

    for path in sorted(kittify_dir.rglob("*")):
        if path.is_dir():
            continue
        disposition = classify_asset(path, global_home, kittify_dir, mission=mission)

        if disposition == AssetDisposition.IDENTICAL:
            report.removed.append(path)
            if not dry_run:
                path.unlink()
        elif disposition == AssetDisposition.CUSTOMIZED:
            rel = path.relative_to(kittify_dir)
            dest = kittify_dir / "overrides" / rel
            report.moved.append((path, dest))
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                path.rename(dest)
        elif disposition == AssetDisposition.PROJECT_SPECIFIC:
            report.kept.append(path)
        else:
            report.unknown.append(path)

    # Clean up empty directories after removal/move
    if not dry_run:
        _cleanup_empty_dirs(kittify_dir)

    return report


def _cleanup_empty_dirs(kittify_dir: Path) -> None:
    """Remove empty directories within shared asset paths.

    Only removes directories that are children of SHARED_ASSET_DIRS
    or the root-level shared asset dirs themselves if empty.
    Does NOT touch project-specific directories.
    """
    # Walk bottom-up so child dirs are removed before parents
    for dirpath in sorted(kittify_dir.rglob("*"), reverse=True):
        if not dirpath.is_dir():
            continue

        # Only clean up shared asset directories, not project-specific ones
        try:
            rel = dirpath.relative_to(kittify_dir)
        except ValueError:
            continue

        top_level = rel.parts[0] if rel.parts else ""
        if top_level not in SHARED_ASSET_DIRS:
            continue

        # Remove if empty (no files, no subdirs)
        if not any(dirpath.iterdir()):
            dirpath.rmdir()
