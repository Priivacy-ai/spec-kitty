"""Asset merging: populate global runtime from package assets.

Overwrites package-managed directories and files while preserving
user-owned data (config.yaml, missions/custom/, cache/).
"""

from __future__ import annotations

import shutil
from pathlib import Path

# Directories managed by the package — overwritten on every update.
# NEVER add missions/custom/ here; it is user-owned.
MANAGED_DIRS: list[str] = [
    "missions/software-dev",
    "missions/research",
    "missions/documentation",
    "missions/plan",
    "missions/audit",
    "missions/refactor",
    "scripts",
]

# Individual files managed by the package — overwritten on every update.
MANAGED_FILES: list[str] = [
    "AGENTS.md",
]


def merge_package_assets(source: Path, dest: Path) -> None:
    """Overwrite package-managed files only. User files are untouched.

    For each managed directory: if it exists in source, remove the
    corresponding directory in dest (if present) and replace it with the
    source version.  For each managed file: copy from source to dest if
    it exists in source.

    Files/directories NOT listed in MANAGED_DIRS or MANAGED_FILES
    (e.g. config.yaml, missions/custom/) are never touched.

    Args:
        source: Temporary directory with fresh package assets.
        dest: Target ~/.kittify/ directory.
    """
    for managed_dir in MANAGED_DIRS:
        src = source / managed_dir
        dst = dest / managed_dir
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst)

    for managed_file in MANAGED_FILES:
        src = source / managed_file
        dst = dest / managed_file
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
