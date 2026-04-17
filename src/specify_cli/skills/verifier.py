"""Skill verification and repair — detects missing/drifted installed files."""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from specify_cli.skills.manifest import (
    ManagedFileEntry,
    ManagedSkillManifest,
    compute_content_hash,
    load_manifest,
    save_manifest,
)
from specify_cli.skills.paths import get_primary_global_skill_root
from specify_cli.skills.registry import SkillRegistry
from specify_cli.template import get_local_repo_root

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
    registry = _discover_registry()

    for entry in manifest.entries:
        installed = _project_managed_path(project_path, entry.installed_path)
        # Guard against path traversal — installed path must stay within project
        if not installed.is_relative_to(project_path.resolve()):
            errors.append(f"Unsafe path {entry.installed_path}: escapes project root")
            continue
        if not installed.exists():
            missing.append(entry)
            continue
        try:
            actual_hash = compute_content_hash(installed)
        except OSError as exc:
            errors.append(f"Cannot read {entry.installed_path}: {exc}")
            continue
        expected_hash = _expected_hash(entry, registry) or entry.content_hash
        if actual_hash != expected_hash:
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
        # Guard against path traversal in installed_path
        dest = _project_managed_path(project_path, entry.installed_path)
        if not dest.is_relative_to(project_path.resolve()):
            logger.warning("Unsafe path %s: escapes project root", entry.installed_path)
            failed += 1
            continue

        skill = registry.get_skill(entry.skill_name)
        if skill is None:
            logger.warning(
                "Cannot repair %s: skill %r not found in registry",
                entry.installed_path,
                entry.skill_name,
            )
            failed += 1
            continue

        # Find matching source file within the skill directory — must stay inside skill_dir
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
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            delivery_mode = entry.delivery_mode
            if entry.delivery_mode == "symlink":
                global_root = get_primary_global_skill_root(entry.agent_key)
                if global_root is None:
                    raise OSError(f"No global skill root configured for agent {entry.agent_key}")
                global_source = global_root / entry.skill_name / entry.source_file
                if not global_source.exists():
                    _sync_skill_to_global_root(skill, global_root)
                if dest.exists() or dest.is_symlink():
                    if dest.is_symlink() or dest.is_file():
                        dest.unlink()
                    else:
                        shutil.rmtree(dest)
                try:
                    dest.symlink_to(global_source)
                except OSError:
                    shutil.copy2(source_path, dest)
                    delivery_mode = "copy"
            else:
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
                    delivery_mode=delivery_mode,
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
    ``"references/agent-path-matrix.md"``).  The resolved path must remain
    within *skill_dir* to prevent path traversal.
    """
    candidate = (skill_dir / source_file).resolve()
    # Guard against path traversal — source must stay inside skill directory
    if not candidate.is_relative_to(skill_dir.resolve()):
        return None
    if candidate.is_file():
        return candidate
    return None


def _discover_registry() -> SkillRegistry | None:
    """Resolve the canonical skill registry for dynamic drift detection."""
    try:
        registry = SkillRegistry.from_package()
        if registry.discover_skills():
            return registry
    except Exception:
        logger.debug("Package skill registry unavailable", exc_info=True)

    local_repo = get_local_repo_root()
    if local_repo is not None:
        registry = SkillRegistry.from_local_repo(local_repo)
        if registry.discover_skills():
            return registry

    return None


def _expected_hash(entry: ManagedFileEntry, registry: SkillRegistry | None) -> str | None:
    """Return the current canonical hash for an entry when available."""
    if entry.delivery_mode == "symlink":
        global_root = get_primary_global_skill_root(entry.agent_key)
        if global_root is not None:
            global_source = global_root / entry.skill_name / entry.source_file
            if global_source.is_file():
                return compute_content_hash(global_source)

    if registry is None:
        return None

    skill = registry.get_skill(entry.skill_name)
    if skill is None:
        return None

    source_path = _find_source_file(skill.skill_dir, entry.source_file)
    if source_path is None:
        return None

    return compute_content_hash(source_path)


def _sync_skill_to_global_root(skill: Any, global_root: Path) -> None:
    """Refresh one global canonical skill directory before relinking a project file."""
    dest_dir = global_root / skill.name
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    if dest_dir.exists() or dest_dir.is_symlink():
        if dest_dir.is_symlink() or dest_dir.is_file():
            dest_dir.unlink()
        else:
            shutil.rmtree(dest_dir)
    shutil.copytree(skill.skill_dir, dest_dir)


def _project_managed_path(project_path: Path, installed_path: str) -> Path:
    """Normalize a managed project path without resolving symlink targets."""
    normalized = Path(os.path.normpath(str(project_path / installed_path)))
    if not normalized.is_absolute():
        normalized = (project_path / normalized).absolute()
    return normalized
