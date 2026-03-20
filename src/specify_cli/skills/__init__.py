"""Skill installation, manifest, and verification utilities."""

from __future__ import annotations

from specify_cli.skills.manifest import (
    MANIFEST_PATH,
    ManagedFile,
    SkillsManifest,
    compute_file_hash,
    load_manifest,
    write_manifest,
)
from specify_cli.skills.roots import resolve_skill_roots

__all__ = [
    "MANIFEST_PATH",
    "ManagedFile",
    "SkillsManifest",
    "compute_file_hash",
    "load_manifest",
    "resolve_skill_roots",
    "write_manifest",
]
