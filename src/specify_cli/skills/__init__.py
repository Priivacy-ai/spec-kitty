"""Skills management for Spec Kitty agent surfaces."""

from __future__ import annotations

from specify_cli.skills.manifest import (
    MANIFEST_PATH,
    ManagedFile,
    SkillsManifest,
    compute_file_hash,
    load_manifest,
    write_manifest,
)

__all__ = [
    "MANIFEST_PATH",
    "ManagedFile",
    "SkillsManifest",
    "compute_file_hash",
    "load_manifest",
    "write_manifest",
]
