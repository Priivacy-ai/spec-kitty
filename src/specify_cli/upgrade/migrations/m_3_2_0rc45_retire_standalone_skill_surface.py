"""Migration: remove stale standalone governance skill packages."""

from __future__ import annotations

import shutil
import stat
from collections.abc import Callable, Iterator
from contextlib import suppress
from pathlib import Path

from specify_cli.core.config import AGENT_SKILL_CONFIG, SKILL_CLASS_WRAPPER
from specify_cli.skills.retired import RETIRED_STANDALONE_SKILL_NAMES

from ..registry import MigrationRegistry
from .base import BaseMigration, MigrationResult


def _make_path_writable(path: str | Path) -> None:
    path = Path(path)
    with suppress(OSError):
        path.chmod(path.stat().st_mode | stat.S_IWRITE)


def _force_writable_and_retry(function: Callable[[str], object], path: str, _exc_info: object) -> None:
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


def _project_skill_roots(project_path: Path) -> list[Path]:
    roots: set[Path] = set()
    for config in AGENT_SKILL_CONFIG.values():
        if config["class"] == SKILL_CLASS_WRAPPER:
            continue
        skill_roots = config["skill_roots"]
        if not isinstance(skill_roots, list):
            continue
        for root in skill_roots:
            roots.add(project_path / root.strip("/"))
    return sorted(roots)


def _path_contains_retired_skill(path: str) -> bool:
    return any(part in RETIRED_STANDALONE_SKILL_NAMES for part in Path(path).parts)


def _iter_existing_retired_skill_paths(project_path: Path) -> Iterator[Path]:
    for root in _project_skill_roots(project_path):
        for skill_name in sorted(RETIRED_STANDALONE_SKILL_NAMES):
            dest = root / skill_name
            if dest.exists() or dest.is_symlink():
                yield dest


def _managed_manifest_has_retired_entries(project_path: Path) -> bool:
    from specify_cli.skills.manifest import load_manifest

    manifest = load_manifest(project_path)
    if manifest is None:
        return False
    return any(
        entry.skill_name in RETIRED_STANDALONE_SKILL_NAMES
        or _path_contains_retired_skill(entry.installed_path)
        for entry in manifest.entries
    )


def _command_manifest_has_retired_entries(project_path: Path) -> bool:
    from specify_cli.skills import manifest_store
    from specify_cli.skills.manifest_errors import ManifestError

    manifest_path = project_path / ".kittify" / "command-skills-manifest.json"
    if not manifest_path.exists():
        return False
    try:
        manifest = manifest_store.load(project_path)
    except ManifestError:
        return False
    return any(_path_contains_retired_skill(entry.path) for entry in manifest.entries)


def _prune_managed_manifest(project_path: Path, *, dry_run: bool) -> tuple[list[str], list[str]]:
    from specify_cli.skills.manifest import load_manifest, save_manifest

    changes: list[str] = []
    errors: list[str] = []
    manifest = load_manifest(project_path)
    if manifest is None:
        return changes, errors

    removed = [
        entry.installed_path
        for entry in manifest.entries
        if entry.skill_name in RETIRED_STANDALONE_SKILL_NAMES
        or _path_contains_retired_skill(entry.installed_path)
    ]
    if not removed:
        return changes, errors

    if dry_run:
        changes.extend(f"Would prune retired skill manifest entry {path}" for path in sorted(removed))
        return changes, errors

    manifest.entries = [
        entry
        for entry in manifest.entries
        if entry.skill_name not in RETIRED_STANDALONE_SKILL_NAMES
        and not _path_contains_retired_skill(entry.installed_path)
    ]
    try:
        save_manifest(manifest, project_path)
        changes.extend(f"Pruned retired skill manifest entry {path}" for path in sorted(removed))
    except OSError as exc:
        errors.append(f"Failed to update .kittify/skills-manifest.json: {exc}")
    return changes, errors


def _prune_command_manifest(project_path: Path, *, dry_run: bool) -> tuple[list[str], list[str], list[str]]:
    from specify_cli.skills import manifest_store
    from specify_cli.skills.manifest_errors import ManifestError

    changes: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    manifest_path = project_path / ".kittify" / "command-skills-manifest.json"
    if not manifest_path.exists():
        return changes, warnings, errors

    try:
        manifest = manifest_store.load(project_path)
    except ManifestError as exc:
        warnings.append(f"Could not prune command skills manifest: {exc}")
        return changes, warnings, errors

    removed = [entry.path for entry in manifest.entries if _path_contains_retired_skill(entry.path)]
    if not removed:
        return changes, warnings, errors

    if dry_run:
        changes.extend(f"Would prune retired command skills manifest entry {path}" for path in sorted(removed))
        return changes, warnings, errors

    manifest.entries = [
        entry for entry in manifest.entries if not _path_contains_retired_skill(entry.path)
    ]
    try:
        manifest_store.save(project_path, manifest)
        changes.extend(f"Pruned retired command skills manifest entry {path}" for path in sorted(removed))
    except OSError as exc:
        errors.append(f"Failed to update .kittify/command-skills-manifest.json: {exc}")
    return changes, warnings, errors


@MigrationRegistry.register
class RetireStandaloneSkillSurfaceMigration(BaseMigration):
    """Remove stale standalone governance skill packages from project surfaces."""

    migration_id = "3.2.0rc45_retire_standalone_skill_surface"
    description = "Remove stale standalone governance skill packages"
    target_version = "3.2.0rc45"

    def detect(self, project_path: Path) -> bool:
        return (
            any(_iter_existing_retired_skill_paths(project_path))
            or _managed_manifest_has_retired_entries(project_path)
            or _command_manifest_has_retired_entries(project_path)
        )

    def can_apply(self, project_path: Path) -> tuple[bool, str]:  # noqa: ARG002
        return True, ""

    def apply(self, project_path: Path, dry_run: bool = False) -> MigrationResult:
        changes: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        for dest in _iter_existing_retired_skill_paths(project_path):
            rel = str(dest.relative_to(project_path))
            if dry_run:
                changes.append(f"Would remove retired skill surface {rel}")
                continue

            try:
                if dest.is_symlink() or dest.is_file():
                    _safe_unlink(dest)
                else:
                    _safe_rmtree(dest)
                changes.append(f"Removed retired skill surface {rel}")
            except OSError as exc:
                errors.append(f"Failed to remove {rel}: {exc}")

        manifest_changes, manifest_errors = _prune_managed_manifest(project_path, dry_run=dry_run)
        changes.extend(manifest_changes)
        errors.extend(manifest_errors)

        command_changes, command_warnings, command_errors = _prune_command_manifest(
            project_path,
            dry_run=dry_run,
        )
        changes.extend(command_changes)
        warnings.extend(command_warnings)
        errors.extend(command_errors)

        if not changes and not warnings and not errors:
            changes.append("Retired standalone governance skill surfaces absent")

        return MigrationResult(
            success=len(errors) == 0,
            changes_made=changes,
            warnings=warnings,
            errors=errors,
        )
