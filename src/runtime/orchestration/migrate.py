"""Migration from per-project .kittify/ to centralized runtime model.

Classifies per-project files as identical/customized/project-specific
and migrates them accordingly:
- IDENTICAL: removed (byte-identical to global runtime)
- SUPERSEDED: removed (old default that differs from current package — NOT a user customization)
- CUSTOMIZED: moved to .kittify/overrides/
- PROJECT_SPECIFIC: kept in place
- UNKNOWN: kept in place with warning
"""

from __future__ import annotations

import filecmp
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from runtime.discovery.home import get_kittify_home, get_package_asset_root


class AssetDisposition(Enum):
    """Classification of a per-project .kittify/ file."""

    IDENTICAL = "identical"  # Remove (byte-identical to global)
    SUPERSEDED = "superseded"  # Remove (outdated default, not user customization)
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


def _find_package_counterpart(rel: Path, package_root: Path, mission: str) -> Path | None:
    """Locate the package-bundled counterpart for a project .kittify/ relative path.

    Tries mission-specific path first, then direct path under package root.
    Returns None if no counterpart exists in the package.
    """
    # Try mission-specific path: package_root/{mission}/{rel}
    pkg_path = package_root / mission / str(rel)
    if pkg_path.exists() and pkg_path.is_file():
        return pkg_path

    # Fall back to direct path under package root
    pkg_path = package_root / str(rel)
    if pkg_path.exists() and pkg_path.is_file():
        return pkg_path

    return None


def classify_asset(
    local_path: Path,
    global_home: Path,
    project_kittify: Path,
    mission: str = "software-dev",
    package_root: Path | None = None,
) -> AssetDisposition:
    """Classify a per-project .kittify/ file.

    Args:
        local_path: Absolute path to the file inside per-project .kittify/
        global_home: Path to the global ~/.kittify/ directory
        project_kittify: Path to the per-project .kittify/ directory
        mission: Mission name for locating global counterparts
        package_root: Path to package-bundled assets (immutable). When provided,
            shared assets are compared against the package defaults to distinguish
            outdated defaults (SUPERSEDED) from genuine user customizations (CUSTOMIZED).

    Returns:
        AssetDisposition indicating how the file should be handled.
    """
    rel = local_path.relative_to(project_kittify)
    top_level = rel.parts[0] if rel.parts else ""

    # Project-specific paths: always keep
    if top_level in PROJECT_SPECIFIC_PATHS:
        return AssetDisposition.PROJECT_SPECIFIC

    # Shared asset: compare to package defaults (immutable) when available,
    # falling back to global home (mutable) for backwards compatibility.
    if top_level in SHARED_ASSET_DIRS or rel.name in SHARED_ASSET_FILES:
        if not local_path.is_file():
            return AssetDisposition.UNKNOWN
        return _classify_shared_asset(local_path, rel, global_home, mission, package_root)

    return AssetDisposition.UNKNOWN


def _classify_shared_asset(
    local_path: Path,
    rel: Path,
    global_home: Path,
    mission: str,
    package_root: Path | None,
) -> AssetDisposition:
    """Classify a shared asset against its canonical reference (package or global home)."""
    if package_root is not None:
        return _classify_against_package(local_path, rel, package_root, mission)
    return _classify_against_global_home(local_path, rel, global_home, mission)


def _classify_against_package(
    local_path: Path,
    rel: Path,
    package_root: Path,
    mission: str,
) -> AssetDisposition:
    """Compare a shared asset against immutable package-bundled defaults."""
    pkg_counterpart = _find_package_counterpart(rel, package_root, mission)
    if pkg_counterpart is None:
        return AssetDisposition.CUSTOMIZED  # No package counterpart = user-created
    if filecmp.cmp(str(local_path), str(pkg_counterpart), shallow=False):
        return AssetDisposition.IDENTICAL
    # Differs from package default — outdated, not a user customisation.
    return AssetDisposition.SUPERSEDED


def _classify_against_global_home(
    local_path: Path,
    rel: Path,
    global_home: Path,
    mission: str,
) -> AssetDisposition:
    """Compare a shared asset against the mutable global ~/.kittify/ (legacy path)."""
    global_path = global_home / "missions" / mission / str(rel)
    if not global_path.exists():
        global_path = global_home / str(rel)
    if global_path.exists() and global_path.is_file():
        if filecmp.cmp(str(local_path), str(global_path), shallow=False):
            return AssetDisposition.IDENTICAL
        return AssetDisposition.CUSTOMIZED
    return AssetDisposition.CUSTOMIZED


@dataclass
class MigrationReport:
    """Report of migration actions taken (or planned in dry-run mode)."""

    removed: list[Path] = field(default_factory=list)
    superseded: list[Path] = field(default_factory=list)
    moved: list[tuple[Path, Path]] = field(default_factory=list)  # (from, to)
    kept: list[Path] = field(default_factory=list)
    unknown: list[Path] = field(default_factory=list)
    dry_run: bool = False


def execute_migration(
    project_dir: Path,
    dry_run: bool = False,
    verbose: bool = False,  # noqa: ARG001
    mission: str = "software-dev",
) -> MigrationReport:
    """Scan and migrate per-project .kittify/ shared assets.

    Identical and superseded files are removed, customized files are moved to
    .kittify/overrides/, and project-specific files are kept in place.

    Compares shared assets against immutable package-bundled defaults (not the
    mutable ~/.kittify/) to correctly distinguish outdated defaults from genuine
    user customizations during version-skew upgrades.

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

    # Use immutable package-bundled assets as comparison target.
    # This prevents version-skew: ensure_runtime() may have already updated
    # ~/.kittify/ to the new version, making old defaults look "customized".
    try:
        package_root = get_package_asset_root()
    except FileNotFoundError:
        package_root = None

    for path in sorted(kittify_dir.rglob("*")):
        if path.is_dir():
            continue
        disposition = classify_asset(
            path, global_home, kittify_dir,
            mission=mission, package_root=package_root,
        )
        _apply_asset_disposition(path, disposition, kittify_dir, dry_run, report)

    # Clean up empty directories after removal/move
    if not dry_run:
        _cleanup_empty_dirs(kittify_dir)

    return report


def _apply_asset_disposition(
    path: Path,
    disposition: AssetDisposition,
    kittify_dir: Path,
    dry_run: bool,
    report: MigrationReport,
) -> None:
    """Apply a single asset's computed disposition to the filesystem and report."""
    if disposition in (AssetDisposition.IDENTICAL, AssetDisposition.SUPERSEDED):
        if disposition == AssetDisposition.SUPERSEDED:
            report.superseded.append(path)
        else:
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
