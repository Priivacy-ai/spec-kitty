"""Skill installer: project skills are projected from user-global canonical roots."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone, UTC
from pathlib import Path

from specify_cli.core.config import (
    AGENT_SKILL_CONFIG,
    SKILL_CLASS_SHARED,
    SKILL_CLASS_WRAPPER,
)
from specify_cli.skills.manifest import (
    ManagedFileEntry,
    ManagedSkillManifest,
    compute_content_hash,
)
from specify_cli.skills.paths import (
    get_primary_global_skill_root,
    get_primary_project_skill_root,
)
from specify_cli.skills.registry import CanonicalSkill, SkillRegistry

DELIVERY_COPY = "copy"
DELIVERY_SYMLINK = "symlink"


def _make_tree_read_only(root: Path) -> None:
    """Remove write bits from all files in a managed canonical skill tree."""
    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        mode = file_path.stat().st_mode
        file_path.chmod(mode & ~0o222)


def _sync_global_skill(skill: CanonicalSkill, target_root: Path) -> Path:
    """Install one canonical skill into the user-global root."""
    target_root.mkdir(parents=True, exist_ok=True)
    dest_dir = target_root / skill.name
    if dest_dir.exists() or dest_dir.is_symlink():
        if dest_dir.is_symlink() or dest_dir.is_file():
            dest_dir.unlink()
        else:
            shutil.rmtree(dest_dir)
    shutil.copytree(skill.skill_dir, dest_dir)
    _make_tree_read_only(dest_dir)
    return dest_dir


def _ensure_backup_root(project_path: Path, backup_root: Path | None) -> Path:
    if backup_root is not None:
        return backup_root

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    root = project_path / ".kittify" / ".migration-backup" / "agent-skills" / timestamp
    root.mkdir(parents=True, exist_ok=True)
    return root


def _archive_existing_path(dest: Path, project_path: Path, backup_root: Path | None) -> Path:
    """Move an existing project-local skill file out of the way."""
    backup_root = _ensure_backup_root(project_path, backup_root)
    backup_path = backup_root / dest.relative_to(project_path)
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(dest), str(backup_path))
    return backup_root


def _project_skill_file(
    source_file: Path,
    dest: Path,
    project_path: Path,
    *,
    backup_root: Path | None = None,
    archived_paths: list[Path] | None = None,
) -> tuple[str, Path | None]:
    """Project a global canonical skill file into the project.

    Prefers a symlink so future CLI upgrades only need to refresh the
    global canonical roots. Falls back to a copy when symlinks are unavailable.
    """
    if dest.is_symlink():
        try:
            if dest.resolve() == source_file.resolve():
                return DELIVERY_SYMLINK, backup_root
        except OSError:
            pass
        dest.unlink()
    elif dest.exists():
        try:
            if dest.is_file() and compute_content_hash(dest) == compute_content_hash(source_file):
                dest.unlink()
            else:
                backup_root = _ensure_backup_root(project_path, backup_root)
                if archived_paths is not None:
                    archived_paths.append(backup_root / dest.relative_to(project_path))
                backup_root = _archive_existing_path(dest, project_path, backup_root)
        except OSError:
            backup_root = _ensure_backup_root(project_path, backup_root)
            if archived_paths is not None:
                archived_paths.append(backup_root / dest.relative_to(project_path))
            backup_root = _archive_existing_path(dest, project_path, backup_root)

    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        dest.symlink_to(source_file)
        return DELIVERY_SYMLINK, backup_root
    except OSError:
        shutil.copy2(source_file, dest)
        return DELIVERY_COPY, backup_root


def _project_skill_files(
    skill: CanonicalSkill,
    target_skill_dir: Path,
    global_skill_dir: Path,
    project_path: Path,
    installation_class: str,
    agent_key: str,
    archived_paths: list[Path] | None = None,
) -> list[ManagedFileEntry]:
    """Project all files for one skill into the project and return manifest entries."""
    entries: list[ManagedFileEntry] = []
    now = datetime.now(UTC).isoformat()
    backup_root: Path | None = None

    for source_file in skill.all_files:
        rel_within_skill = source_file.relative_to(skill.skill_dir)
        global_file = global_skill_dir / rel_within_skill
        dest = target_skill_dir / rel_within_skill
        delivery_mode, backup_root = _project_skill_file(
            global_file,
            dest,
            project_path,
            backup_root=backup_root,
            archived_paths=archived_paths,
        )
        entries.append(
            ManagedFileEntry(
                skill_name=skill.name,
                source_file=str(rel_within_skill),
                installed_path=str(dest.relative_to(project_path)),
                installation_class=installation_class,
                agent_key=agent_key,
                content_hash=compute_content_hash(dest),
                installed_at=now,
                delivery_mode=delivery_mode,
            )
        )

    return entries


def _make_entries_for_existing(
    skill: CanonicalSkill,
    target_skill_dir: Path,
    project_path: Path,
    installation_class: str,
    agent_key: str,
) -> list[ManagedFileEntry]:
    """Create manifest entries pointing to already-projected files."""
    entries: list[ManagedFileEntry] = []
    now = datetime.now(UTC).isoformat()

    for source_file in skill.all_files:
        rel_within_skill = source_file.relative_to(skill.skill_dir)
        dest = target_skill_dir / rel_within_skill

        entries.append(
            ManagedFileEntry(
                skill_name=skill.name,
                source_file=str(rel_within_skill),
                installed_path=str(dest.relative_to(project_path)),
                installation_class=installation_class,
                agent_key=agent_key,
                content_hash=compute_content_hash(dest),
                installed_at=now,
                delivery_mode=DELIVERY_SYMLINK if dest.is_symlink() else DELIVERY_COPY,
            )
        )

    return entries


def install_skills_for_agent(
    project_path: Path,
    agent_key: str,
    skills: list[CanonicalSkill],
    *,
    shared_root_installed: set[str] | None = None,
    archived_paths: list[Path] | None = None,
) -> list[ManagedFileEntry]:
    """Install skills for one agent. Returns manifest entries created."""
    config = AGENT_SKILL_CONFIG.get(agent_key)
    if config is None:
        raise ValueError(f"Unknown agent key: {agent_key!r}")

    installation_class: str = config["class"]  # type: ignore[assignment]
    if installation_class == SKILL_CLASS_WRAPPER:
        return []

    project_root = get_primary_project_skill_root(agent_key)
    global_root = get_primary_global_skill_root(agent_key)
    if project_root is None or global_root is None:
        raise ValueError(f"Agent {agent_key!r} has no installable skill root")

    all_entries: list[ManagedFileEntry] = []

    for skill in skills:
        global_skill_dir = _sync_global_skill(skill, global_root)
        target_skill_dir = project_path / project_root / skill.name

        if installation_class == SKILL_CLASS_SHARED:
            if shared_root_installed is not None and skill.name in shared_root_installed:
                entries = _make_entries_for_existing(
                    skill, target_skill_dir, project_path, installation_class, agent_key
                )
            else:
                entries = _project_skill_files(
                    skill,
                    target_skill_dir,
                    global_skill_dir,
                    project_path,
                    installation_class,
                    agent_key,
                    archived_paths=archived_paths,
                )
                if shared_root_installed is not None:
                    shared_root_installed.add(skill.name)
        else:
            entries = _project_skill_files(
                skill,
                target_skill_dir,
                global_skill_dir,
                project_path,
                installation_class,
                agent_key,
                archived_paths=archived_paths,
            )

        all_entries.extend(entries)

    return all_entries


def install_all_skills(
    project_path: Path,
    agent_keys: list[str],
    registry: SkillRegistry,
    *,
    archived_paths: list[Path] | None = None,
) -> ManagedSkillManifest:
    """Install skills for all agents. Returns populated manifest."""
    skills = registry.discover_skills()
    now = datetime.now(UTC).isoformat()

    manifest = ManagedSkillManifest(
        version=1,
        created_at=now,
        updated_at=now,
    )

    shared_root_installed: set[str] = set()

    for agent_key in agent_keys:
        entries = install_skills_for_agent(
            project_path,
            agent_key,
            skills,
            shared_root_installed=shared_root_installed,
            archived_paths=archived_paths,
        )
        manifest.entries.extend(entries)

    return manifest
