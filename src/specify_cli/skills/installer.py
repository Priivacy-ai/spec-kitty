"""Skill installer: project skills are projected from user-global canonical roots."""

from __future__ import annotations

import shutil
import stat
import hashlib
import json
import os
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from kernel.clock import now_utc_iso
from pathlib import Path

from specify_cli.core.config import (
    AGENT_SKILL_CONFIG,
    SKILL_CLASS_SHARED,
    SKILL_CLASS_WRAPPER,
)
from specify_cli.core.atomic import atomic_write
from specify_cli.skills.command_renderer import ensure_skill_frontmatter
from specify_cli.skills.manifest import (
    ManagedFileEntry,
    ManagedSkillManifest,
    compute_content_hash,
    load_manifest,
)
from specify_cli.skills.paths import (
    get_primary_global_skill_root,
    get_primary_project_skill_root,
    SkillPathObservation,
    observe_skill_path,
    recheck_skill_paths,
    skill_path_observations,
)
from specify_cli.tool_surface.operations import FileState
from specify_cli.skills.registry import CanonicalSkill, SkillRegistry
from specify_cli.skills.retired import RETIRED_CANONICAL_SKILL_NAMES

DELIVERY_COPY = "copy"
DELIVERY_SYMLINK = "symlink"


def _make_path_writable(path: str | Path) -> None:
    """Clear Windows ReadOnly before deleting managed files."""
    path = Path(path)
    with suppress(OSError):
        path.chmod(path.stat().st_mode | stat.S_IWRITE)


def _force_writable_and_retry(function: Callable[[str], object], path: str, _exc_info: object) -> None:
    """shutil.rmtree onerror handler: clear readonly and retry the failed operation."""
    _make_path_writable(path)
    function(path)


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink()
    except PermissionError:
        _make_path_writable(path)
        path.unlink()


def _safe_rmtree(path: Path) -> None:
    shutil.rmtree(path, onerror=_force_writable_and_retry)


def _remove_retired_skill_dirs(root: Path, canonical_names: set[str]) -> None:
    retired_names = RETIRED_CANONICAL_SKILL_NAMES - canonical_names
    for skill_name in retired_names:
        dest = root / skill_name
        if not dest.exists() and not dest.is_symlink():
            continue
        if dest.is_symlink() or dest.is_file():
            _safe_unlink(dest)
        else:
            _safe_rmtree(dest)


def _make_tree_read_only(root: Path) -> None:
    """Remove write bits from all files in a managed canonical skill tree."""
    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        mode = file_path.stat().st_mode
        file_path.chmod(mode & ~0o222)


def _normalize_skill_md(skill: CanonicalSkill, dest_dir: Path) -> None:
    """Ensure generated host-visible SKILL.md files have YAML frontmatter."""
    skill_md = dest_dir / "SKILL.md"
    if not skill_md.is_file():
        return
    content = skill_md.read_text(encoding="utf-8")
    normalized = ensure_skill_frontmatter(content, skill.name)
    if normalized != content:
        skill_md.write_text(normalized, encoding="utf-8")


def _sync_global_skill(skill: CanonicalSkill, target_root: Path) -> Path:
    """Install one canonical skill into the user-global root."""
    target_root.mkdir(parents=True, exist_ok=True)
    dest_dir: Path = target_root / str(skill.name)
    if dest_dir.exists() or dest_dir.is_symlink():
        if dest_dir.is_symlink() or dest_dir.is_file():
            _safe_unlink(dest_dir)
        else:
            _safe_rmtree(dest_dir)
    shutil.copytree(skill.skill_dir, dest_dir)
    _normalize_skill_md(skill, dest_dir)
    _make_tree_read_only(dest_dir)
    return dest_dir


@dataclass(frozen=True)
class SkillBackupReplacement:
    """Stable replacement identity, excluding wall time and project location."""

    path: str
    before: FileState
    after: FileState


@dataclass(frozen=True)
class PreparedSkillBackup:
    root: Path
    observations: tuple[SkillPathObservation, ...]
    replacements: tuple[SkillBackupReplacement, ...]


def prepare_skill_backup(
    project_path: Path,
    replacements: tuple[SkillBackupReplacement, ...],
    *,
    explicit_root: Path | None = None,
) -> PreparedSkillBackup:
    """Allocate without writes; every occupied candidate remains user-owned."""
    if not replacements:
        raise ValueError("A skill backup requires replacements")
    ordered = tuple(sorted(replacements, key=lambda replacement: replacement.path))
    if len({replacement.path for replacement in ordered}) != len(ordered):
        raise ValueError("Duplicate skill backup path")
    records = []
    for replacement in ordered:
        relative = Path(replacement.path)
        if relative.is_absolute() or not relative.parts or ".." in relative.parts or relative.as_posix() != replacement.path:
            raise ValueError(f"Unsafe skill backup path: {relative}")
        records.append([
            relative.as_posix(),
            [replacement.before.kind, replacement.before.sha256, replacement.before.target, replacement.before.mode],
            [replacement.after.kind, replacement.after.sha256, replacement.after.target, replacement.after.mode],
        ])
    serialized = json.dumps(["agent-skills-backup-v1", records], separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(serialized).hexdigest()  # noqa: TID251 -- deterministic backup identity, not charter hashing
    parent = _backup_parent(project_path)
    candidate = explicit_root or parent / f"state-v1-{digest}"
    if candidate.parent != parent:
        raise ValueError("Explicit skill backup must be a direct child of the managed backup parent")
    observations: list[SkillPathObservation] = []
    index = 0
    while True:
        current = skill_path_observations(project_path, candidate)
        observations.extend(current)
        if current[-1].state.kind == "absent":
            return PreparedSkillBackup(candidate, tuple(observations), ordered)
        if explicit_root is not None:
            raise FileExistsError(f"Skill backup already exists: {candidate}")
        index += 1
        candidate = parent / f"state-v1-{digest}-{index}"


def create_skill_backup(prepared: PreparedSkillBackup) -> Path:
    """Consume the chosen absence, refusing races rather than reallocating."""
    recheck_skill_paths(prepared.observations)
    for observed in prepared.observations:
        if observed.path == prepared.root:
            continue
        if observed.state.kind == "absent":
            observed.path.mkdir(mode=0o700)
    prepared.root.mkdir(mode=0o700)
    return prepared.root


def _backup_parent(project_path: Path) -> Path:
    """Return the established owner-local retained-backup directory."""
    return project_path / ".kittify" / ".migration-backup" / "agent-skills"


def _archive_existing_path(
    dest: Path, project_path: Path, backup_root: Path | None, *, after: FileState | None = None
) -> Path:
    """Retain a file or literal link without following links or clobbering backups."""
    inputs = skill_path_observations(project_path, dest)
    before = inputs[-1].state
    if before.kind not in {"file", "symlink"}:
        raise ValueError(f"Cannot archive skill node: {dest}")
    content = dest.read_bytes() if before.kind == "file" else None
    if backup_root is None:
        allocation = prepare_skill_backup(project_path, (
            SkillBackupReplacement(dest.relative_to(project_path).as_posix(), before, after or FileState("absent")),
        ))
        recheck_skill_paths(inputs)
        backup_root = create_skill_backup(allocation)
    elif backup_root.parent != _backup_parent(project_path):
        raise ValueError("Skill backup is outside the managed backup parent")
    backup_path = backup_root / dest.relative_to(project_path)
    backup_inputs = skill_path_observations(project_path, backup_path)
    if backup_inputs[-1].state.kind != "absent":
        raise FileExistsError(f"Skill backup member already exists: {backup_path}")
    recheck_skill_paths(inputs + backup_inputs)
    for observed in backup_inputs[:-1]:
        if observed.state.kind == "absent":
            observed.path.mkdir(mode=0o700)
    if before.kind == "symlink":
        assert before.target is not None
        backup_path.symlink_to(before.target)
        if before.mode is not None and stat.S_IMODE(backup_path.lstat().st_mode) != before.mode:
            backup_path.chmod(before.mode, follow_symlinks=False)
    else:
        assert content is not None and before.mode is not None
        descriptor = os.open(backup_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, before.mode)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            os.fchmod(stream.fileno(), before.mode)
    if before.mtime_ns is not None:
        os.utime(backup_path, ns=(before.mtime_ns, before.mtime_ns), follow_symlinks=False)
    recheck_skill_paths(inputs)
    dest.unlink()
    return backup_root


def _replacement_is_owned(
    manifest: ManagedSkillManifest | None, project_path: Path, dest: Path, before: FileState
) -> bool:
    if manifest is None or before.kind != "file":
        return False
    owners = [entry for entry in manifest.entries if entry.installed_path == dest.relative_to(project_path).as_posix()]
    if not owners:
        return False
    for entry in owners:
        root = get_primary_project_skill_root(entry.agent_key)
        skill_name, source = Path(entry.skill_name), Path(entry.source_file)
        if root is None or len(skill_name.parts) != 1 or skill_name.is_absolute() or ".." in skill_name.parts:
            return False
        if source.is_absolute() or not source.parts or ".." in source.parts:
            return False
        if project_path / root / skill_name / source != dest:
            return False
        if entry.content_hash != f"sha256:{before.sha256}" or entry.delivery_mode != DELIVERY_COPY:
            return False
    return True


def _project_skill_file(
    source_file: Path,
    dest: Path,
    project_path: Path,
    *,
    backup_root: Path | None = None,
    archived_paths: list[Path] | None = None,
) -> tuple[str, Path | None]:
    """Project a global canonical skill file into the project.

    New files are portable copies (#2412). Unmodified manifest-owned files
    may be replaced with a retained backup. Unknown or modified content and
    unverified links return ``preserved`` without acquiring ownership.
    """
    inputs = skill_path_observations(project_path, dest)
    before = inputs[-1].state
    source = observe_skill_path(source_file)
    if source.state.kind != "file":
        raise ValueError(f"Canonical skill source is not a regular file: {source_file}")
    content = source_file.read_bytes()
    recheck_skill_paths(inputs + (source,))
    if before.kind == "file" and before.sha256 == source.state.sha256:
        return DELIVERY_COPY, backup_root
    if before.kind != "absent":
        manifest = load_manifest(project_path, strict=True)
        if not _replacement_is_owned(manifest, project_path, dest, before):
            return "preserved", backup_root
        recheck_skill_paths(inputs + (source,))
        backup_root = _archive_existing_path(dest, project_path, backup_root, after=source.state)
        if archived_paths is not None:
            archived_paths.append(backup_root / dest.relative_to(project_path))

    atomic_write(dest, content, mkdir=True)
    assert source.state.mode is not None
    dest.chmod(source.state.mode)
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
    now = now_utc_iso()
    backup_root: Path | None = None
    previous = load_manifest(project_path, strict=True)
    replacements = []
    observations: list[SkillPathObservation] = []
    for source_file in skill.all_files:
        relative = source_file.relative_to(skill.skill_dir)
        dest = target_skill_dir / relative
        destination_inputs = skill_path_observations(project_path, dest)
        source_inputs = skill_path_observations(global_skill_dir, global_skill_dir / relative)
        observations.extend(destination_inputs + source_inputs)
        before, after = destination_inputs[-1].state, source_inputs[-1].state
        if after.kind != "file":
            raise ValueError(f"Canonical skill source is not a regular file: {source_file}")
        if _replacement_is_owned(previous, project_path, dest, before) and before.sha256 != after.sha256:
            replacements.append(SkillBackupReplacement(dest.relative_to(project_path).as_posix(), before, after))
    if replacements:
        allocation = prepare_skill_backup(project_path, tuple(replacements))
        recheck_skill_paths(tuple(observations))
        backup_root = create_skill_backup(allocation)

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
        if delivery_mode == "preserved":
            if previous is not None:
                entries.extend(entry for entry in previous.entries if
                               entry.installed_path == dest.relative_to(project_path).as_posix() and entry.agent_key == agent_key)
            continue
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
    now = now_utc_iso()
    previous = load_manifest(project_path, strict=True)

    for source_file in skill.all_files:
        rel_within_skill = source_file.relative_to(skill.skill_dir)
        dest = target_skill_dir / rel_within_skill
        observations = skill_path_observations(project_path, dest)
        expected = source_file.read_bytes()
        if rel_within_skill == Path("SKILL.md"):
            expected = ensure_skill_frontmatter(expected.decode("utf-8"), skill.name).encode("utf-8")
        current = observations[-1].state
        if current.kind != "file" or dest.read_bytes() != expected:
            if previous is not None:
                entries.extend(entry for entry in previous.entries if
                               entry.installed_path == dest.relative_to(project_path).as_posix() and entry.agent_key == agent_key)
            continue
        recheck_skill_paths(observations)
        entries.append(
            ManagedFileEntry(
                skill_name=skill.name,
                source_file=str(rel_within_skill),
                installed_path=str(dest.relative_to(project_path)),
                installation_class=installation_class,
                agent_key=agent_key,
                content_hash=compute_content_hash(dest),
                installed_at=now,
                delivery_mode=DELIVERY_COPY,
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

    installation_class: str = config["class"]
    if installation_class == SKILL_CLASS_WRAPPER:
        return []

    project_root = get_primary_project_skill_root(agent_key)
    global_root = get_primary_global_skill_root(agent_key)
    if project_root is None or global_root is None:
        raise ValueError(f"Agent {agent_key!r} has no installable skill root")

    canonical_names = {skill.name for skill in skills}
    _remove_retired_skill_dirs(global_root, canonical_names)
    # Project retirement needs manifest ownership, never just a canonical-looking name.

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
    now = now_utc_iso()

    manifest = load_manifest(project_path, strict=True) or ManagedSkillManifest(
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
        for entry in entries:
            manifest.add_entry(entry)

    return manifest
