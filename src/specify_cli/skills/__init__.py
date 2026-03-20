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
from specify_cli.skills.verification import VerificationResult, verify_installation

__all__ = [
    "MANIFEST_PATH",
    "ManagedFile",
    "SkillsManifest",
    "VerificationResult",
    "compute_file_hash",
    "load_manifest",
    "resolve_skill_roots",
    "verify_installation",
    "write_manifest",
]
