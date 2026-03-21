"""Skill verification and repair — detects missing/drifted installed files."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from specify_cli.skills.manifest import (
    ManagedFileEntry,
    ManagedSkillManifest,
    compute_content_hash,
    load_manifest,
    save_manifest,
)
from specify_cli.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


@dataclass
class VerifyResult:
    """Structured result of a skill verification pass."""

    ok: bool
    missing: list[ManagedFileEntry] = field(default_factory=list)
    drifted: list[tuple[ManagedFileEntry, str]] = field(default_factory=list)  # (entry, actual_hash)
    unmanaged: list[str] = field(default_factory=list)  # paths not in manifest
    errors: list[str] = field(default_factory=list)

    @property
    def total_issues(self) -> int:
        return len(self.missing) + len(self.drifted) + len(self.errors)


def verify_installed_skills(project_path: Path) -> VerifyResult:
    """Verify all installed skill files against the manifest.

    If no manifest exists, returns ``VerifyResult(ok=True)`` — nothing to check.
    Otherwise, checks each manifest entry for existence and content hash match.
    """
    manifest = load_manifest(project_path)
    if manifest is None:
        return VerifyResult(ok=True)

    missing: list[ManagedFileEntry] = []
    drifted: list[tuple[ManagedFileEntry, str]] = []
    errors: list[str] = []

    for entry in manifest.entries:
        installed = project_path / entry.installed_path
        if not installed.exists():
            missing.append(entry)
            continue
        try:
            actual_hash = compute_content_hash(installed)
        except OSError as exc:
            errors.append(f"Cannot read {entry.installed_path}: {exc}")
            continue
        if actual_hash != entry.content_hash:
            drifted.append((entry, actual_hash))

    ok = len(missing) == 0 and len(drifted) == 0 and len(errors) == 0
    return VerifyResult(ok=ok, missing=missing, drifted=drifted, errors=errors)


def repair_skills(
    project_path: Path,
    verify_result: VerifyResult,
    registry: SkillRegistry,
) -> tuple[int, int]:
    """Repair missing and drifted skill files from the canonical registry.

    Returns ``(repaired_count, failed_count)``.
    """
    manifest = load_manifest(project_path)
    if manifest is None:
        manifest = ManagedSkillManifest()

    repaired = 0
    failed = 0

    entries_to_repair: list[ManagedFileEntry] = list(verify_result.missing)
    entries_to_repair.extend(entry for entry, _hash in verify_result.drifted)

    for entry in entries_to_repair:
        skill = registry.get_skill(entry.skill_name)
        if skill is None:
            logger.warning(
                "Cannot repair %s: skill %r not found in registry",
                entry.installed_path,
                entry.skill_name,
            )
            failed += 1
            continue

        # Find matching source file within the skill directory
        source_path = _find_source_file(skill.skill_dir, entry.source_file)
        if source_path is None:
            logger.warning(
                "Cannot repair %s: source file %r not found in skill %r",
                entry.installed_path,
                entry.source_file,
                entry.skill_name,
            )
            failed += 1
            continue

        dest = project_path / entry.installed_path
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, dest)
            new_hash = compute_content_hash(dest)
            # Update the manifest entry with the new hash
            manifest.add_entry(
                ManagedFileEntry(
                    skill_name=entry.skill_name,
                    source_file=entry.source_file,
                    installed_path=entry.installed_path,
                    installation_class=entry.installation_class,
                    agent_key=entry.agent_key,
                    content_hash=new_hash,
                    installed_at=entry.installed_at,
                )
            )
            repaired += 1
        except OSError as exc:
            logger.warning("Failed to repair %s: %s", entry.installed_path, exc)
            failed += 1

    if repaired > 0:
        save_manifest(manifest, project_path)

    return repaired, failed


def _find_source_file(skill_dir: Path, source_file: str) -> Path | None:
    """Locate a source file within a canonical skill directory.

    *source_file* is relative within the skill dir (e.g. ``"SKILL.md"`` or
    ``"references/agent-path-matrix.md"``).
    """
    candidate = skill_dir / source_file
    if candidate.is_file():
        return candidate
    return None
