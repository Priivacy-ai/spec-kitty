"""Skill installer: copies canonical skills to agent-specific skill roots."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from specify_cli.core.config import (
    AGENT_SKILL_CONFIG,
    SKILL_CLASS_NATIVE,
    SKILL_CLASS_SHARED,
    SKILL_CLASS_WRAPPER,
)
from specify_cli.skills.manifest import (
    ManagedFileEntry,
    ManagedSkillManifest,
    compute_content_hash,
)
from specify_cli.skills.registry import CanonicalSkill, SkillRegistry


def _install_skill_files(
    skill: CanonicalSkill,
    target_skill_dir: Path,
    project_path: Path,
    installation_class: str,
    agent_key: str,
) -> list[ManagedFileEntry]:
    """Copy all files for one skill to *target_skill_dir* and return manifest entries."""
    entries: list[ManagedFileEntry] = []
    now = datetime.now(timezone.utc).isoformat()

    for source_file in skill.all_files:
        rel_within_skill = source_file.relative_to(skill.skill_dir)
        dest = target_skill_dir / rel_within_skill
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, dest)

        entries.append(
            ManagedFileEntry(
                skill_name=skill.name,
                source_file=str(rel_within_skill),
                installed_path=str(dest.relative_to(project_path)),
                installation_class=installation_class,
                agent_key=agent_key,
                content_hash=compute_content_hash(dest),
                installed_at=now,
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
    """Create manifest entries pointing to already-installed shared files (no copy)."""
    entries: list[ManagedFileEntry] = []
    now = datetime.now(timezone.utc).isoformat()

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
            )
        )

    return entries


def install_skills_for_agent(
    project_path: Path,
    agent_key: str,
    skills: list[CanonicalSkill],
    *,
    shared_root_installed: set[str] | None = None,
) -> list[ManagedFileEntry]:
    """Install skills for one agent. Returns manifest entries created.

    Args:
        project_path: Project root directory.
        agent_key: Agent identifier (e.g., "claude").
        skills: List of canonical skills to install.
        shared_root_installed: Set of skill names already installed to shared root.
            Pass a mutable set to enable deduplication across agents.

    Returns:
        List of ManagedFileEntry for each installed file.
    """
    config = AGENT_SKILL_CONFIG.get(agent_key)
    if config is None:
        raise ValueError(f"Unknown agent key: {agent_key!r}")

    installation_class: str = config["class"]  # type: ignore[assignment]

    # wrapper-only agents get no skill files
    if installation_class == SKILL_CLASS_WRAPPER:
        return []

    skill_roots: list[str] = config["skill_roots"]  # type: ignore[assignment]
    root = skill_roots[0]  # Use the first (primary) root

    all_entries: list[ManagedFileEntry] = []

    for skill in skills:
        target_skill_dir = project_path / root / skill.name

        if installation_class == SKILL_CLASS_SHARED:
            # Shared-root deduplication
            if shared_root_installed is not None and skill.name in shared_root_installed:
                # Files already on disk -- just create manifest entries
                entries = _make_entries_for_existing(
                    skill, target_skill_dir, project_path, installation_class, agent_key
                )
            else:
                # First shared-root agent to need this skill: copy files
                entries = _install_skill_files(
                    skill, target_skill_dir, project_path, installation_class, agent_key
                )
                if shared_root_installed is not None:
                    shared_root_installed.add(skill.name)
        else:
            # native-root-required: always copy
            entries = _install_skill_files(
                skill, target_skill_dir, project_path, installation_class, agent_key
            )

        all_entries.extend(entries)

    return all_entries


def install_all_skills(
    project_path: Path,
    agent_keys: list[str],
    registry: SkillRegistry,
) -> ManagedSkillManifest:
    """Install skills for all agents. Returns populated manifest.

    Args:
        project_path: Project root directory.
        agent_keys: List of agent identifiers to install skills for.
        registry: SkillRegistry used to discover canonical skills.

    Returns:
        Populated ManagedSkillManifest with entries for all installed files.
    """
    skills = registry.discover_skills()
    now = datetime.now(timezone.utc).isoformat()

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
        )
        # Append directly: shared-root agents legitimately produce entries
        # with the same installed_path but different agent_key.  Using
        # add_entry() would replace the earlier agent's entry.
        manifest.entries.extend(entries)

    return manifest
