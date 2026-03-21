"""Skill distribution runtime for Spec Kitty 2.0.11+."""

from __future__ import annotations

from .installer import install_all_skills, install_skills_for_agent
from .manifest import (
    MANIFEST_FILENAME,
    ManagedFileEntry,
    ManagedSkillManifest,
    clear_manifest,
    compute_content_hash,
    load_manifest,
    save_manifest,
)
from .registry import CanonicalSkill, SkillRegistry
from .verifier import VerifyResult, repair_skills, verify_installed_skills

__all__ = [
    "CanonicalSkill",
    "MANIFEST_FILENAME",
    "ManagedFileEntry",
    "ManagedSkillManifest",
    "SkillRegistry",
    "VerifyResult",
    "clear_manifest",
    "compute_content_hash",
    "install_all_skills",
    "install_skills_for_agent",
    "load_manifest",
    "repair_skills",
    "save_manifest",
    "verify_installed_skills",
]
