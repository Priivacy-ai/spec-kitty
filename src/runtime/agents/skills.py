"""Bootstrap user-global canonical doctrine skills."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from runtime.orchestration.bootstrap import _get_cli_version, _lock_exclusive
from runtime.discovery.home import get_kittify_home
from specify_cli.skills.paths import get_primary_global_skill_root, iter_installable_agents
from specify_cli.skills.registry import CanonicalSkill, SkillRegistry
from specify_cli.template import get_local_repo_root

logger = logging.getLogger(__name__)

_VERSION_FILENAME = "agent-skills.lock"
_LOCK_FILENAME = ".agent-skills.lock"


def _discover_registry() -> SkillRegistry | None:
    """Resolve the canonical bundled skill registry."""
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


def _unique_global_roots() -> list[Path]:
    roots: list[Path] = []
    seen: set[Path] = set()

    for agent_key in iter_installable_agents():
        root = get_primary_global_skill_root(agent_key)
        if root is None or root in seen:
            continue
        seen.add(root)
        roots.append(root)

    return roots


def _remove_entry(entry: Path) -> None:
    """Delete `entry` whether it is a symlink, file, or directory."""
    if entry.is_symlink() or entry.is_file():
        entry.unlink()
    elif entry.is_dir():
        shutil.rmtree(entry)


def _remove_stale_skills(root: Path, canonical_names: set[str]) -> None:
    """Delete any `spec-kitty-*` entry under `root` not in `canonical_names`."""
    for existing in root.iterdir():
        if not existing.name.startswith("spec-kitty-"):
            continue
        if existing.name in canonical_names:
            continue
        _remove_entry(existing)


def _mark_readonly_recursive(dest: Path) -> None:
    """Remove write bits from every file under `dest`."""
    for file_path in dest.rglob("*"):
        if not file_path.is_file():
            continue
        mode = file_path.stat().st_mode
        file_path.chmod(mode & ~0o222)


def _install_skill(skill: CanonicalSkill, root: Path) -> None:
    """Copy `skill` into `root`, overwriting any existing entry and making files read-only."""
    dest = root / skill.name
    if dest.exists() or dest.is_symlink():
        _remove_entry(dest)
    shutil.copytree(skill.skill_dir, dest)
    _mark_readonly_recursive(dest)


def _sync_skill_root(root: Path, registry: SkillRegistry) -> None:
    root.mkdir(parents=True, exist_ok=True)
    skills = registry.discover_skills()
    canonical_names = {skill.name for skill in skills}
    _remove_stale_skills(root, canonical_names)
    for skill in skills:
        _install_skill(skill, root)


def ensure_global_agent_skills() -> None:
    """Ensure user-global canonical skill roots are populated for this CLI version."""
    registry = _discover_registry()
    if registry is None:
        return

    kittify_home = get_kittify_home()
    kittify_home.mkdir(parents=True, exist_ok=True)
    cache_dir = kittify_home / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    version_file = cache_dir / _VERSION_FILENAME
    cli_version = _get_cli_version()
    if version_file.exists() and version_file.read_text().strip() == cli_version:
        return

    lock_path = cache_dir / _LOCK_FILENAME
    lock_fd = open(lock_path, "w")  # noqa: SIM115
    try:
        _lock_exclusive(lock_fd)
        if version_file.exists() and version_file.read_text().strip() == cli_version:
            return

        for root in _unique_global_roots():
            _sync_skill_root(root, registry)
        version_file.write_text(cli_version)
    finally:
        lock_fd.close()
