"""Bootstrap user-global canonical doctrine skills."""

from __future__ import annotations

import logging
import shutil
import stat
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from specify_cli.runtime.bootstrap import _get_cli_version
from specify_cli.runtime.asset_preparation import AssetPreparation, _GlobalAssetPreparation
from specify_cli.runtime.home import get_kittify_home
from specify_cli.skills.command_renderer import ensure_skill_frontmatter
from specify_cli.skills.paths import get_primary_global_skill_root, iter_installable_agents
from specify_cli.skills.registry import CanonicalSkill, SkillRegistry
from specify_cli.skills.retired import RETIRED_CANONICAL_SKILL_NAMES
from specify_cli.template import get_local_repo_root
from specify_cli.tool_surface.operations import ApplyConsent, OwnerAssessment

logger = logging.getLogger(__name__)

_VERSION_FILENAME = "agent-skills.lock"
_LOCK_FILENAME = ".agent-skills.lock"


def _make_path_writable(path: str | Path) -> None:
    path = Path(path)
    try:
        path.chmod(path.stat().st_mode | stat.S_IWRITE)
    except OSError:
        logger.debug("Could not make skill path writable: %s", path, exc_info=True)


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


def _discover_registry() -> SkillRegistry | None:
    """Resolve the canonical bundled skill registry."""
    try:
        registry = SkillRegistry.from_package()
        if registry.discover_skills():
            return registry
    except ModuleNotFoundError:
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


def _retired_skill_cleanup_needed() -> bool:
    for root in _unique_global_roots():
        for skill_name in RETIRED_CANONICAL_SKILL_NAMES:
            dest = root / skill_name
            if dest.exists() or dest.is_symlink():
                return True
    return False


def _prepare_skill_tree(
    prepared: AssetPreparation,
    source: Path,
    destination: Path,
    skill_name: str,
    *,
    normalize_frontmatter: bool = True,
) -> None:
    state = prepared.observe(source, members=True)
    if state.kind != "directory":
        raise ValueError(f"Required skill directory unavailable: {source}")
    if prepared.observe(destination).kind not in {"directory", "absent"}:
        prepared.preserve(destination, "Unproven canonical skill path replacement")
        return
    prepared.asset(destination, None, state.mode or 0o755)
    for child in sorted(source.iterdir()):
        child_state = prepared.observe(child)
        target = destination / child.name
        if child_state.kind == "directory":
            _prepare_skill_tree(prepared, child, target, skill_name, normalize_frontmatter=False)
        elif child_state.kind == "file":
            data = prepared.source(child)
            if child.name == "SKILL.md" and normalize_frontmatter:
                data = ensure_skill_frontmatter(data.decode("utf-8"), skill_name).encode("utf-8")
            prepared.asset(target, data, (child_state.mode or 0o644) & ~0o222)
        else:
            raise ValueError(f"Unsupported canonical skill source: {child}")


def _observe_registry_catalog(prepared: AssetPreparation, skills: list[CanonicalSkill]) -> None:
    """Retain catalog membership, including directories not yet valid skills."""
    catalog_roots = {skill.skill_dir.parent for skill in skills}
    if len(catalog_roots) != 1:
        raise ValueError("Canonical skill registry must have one source root")
    catalog_root = next(iter(catalog_roots))
    if prepared.observe(catalog_root, members=True).kind != "directory":
        raise ValueError("Canonical skill catalog is not a regular directory")
    discovered = set()
    for child in sorted(catalog_root.iterdir()):
        state = prepared.observe(child, members=True)
        if state.kind == "symlink":
            raise ValueError(f"Unproven canonical skill source link: {child}")
        if state.kind == "directory" and prepared.observe(child / "SKILL.md").kind == "file":
            discovered.add(child.name)
    if discovered != {skill.name for skill in skills}:
        raise ValueError("Canonical skill catalog changed during discovery")


def assess_global_agent_skills(
    *,
    consent: ApplyConsent = ApplyConsent(),
    _batch: _GlobalAssetPreparation | None = None,
) -> OwnerAssessment:
    """Prepare complete global skill trees without writes or marker shortcuts.

    Global callers, including project installers, must delegate this exact
    assessment once; project copy/manifest/backup policy stays in the installer.
    """
    from specify_cli.runtime.asset_preparation import global_asset_root, incomplete

    home = get_kittify_home()
    roots = tuple(_unique_global_roots())
    root = global_asset_root("global_skills", (home, *roots))
    try:
        prepared = AssetPreparation("global_skills", root, home / "cache", _LOCK_FILENAME, consent)
        registry = _discover_registry()
        if registry is None:
            raise ValueError("Required canonical skill registry unavailable")
        skills = registry.discover_skills()
        if not skills:
            raise ValueError("Required canonical skill registry is empty")
        _observe_registry_catalog(prepared, skills)
        for destination_root in roots:
            state = prepared.observe(destination_root, members=True)
            if state.kind not in {"directory", "absent"}:
                prepared.preserve(destination_root, "Unproven global skill root replacement")
                continue
            canonical = {skill.name for skill in skills}
            for skill in skills:
                prepared.source(skill.skill_md)
                _prepare_skill_tree(prepared, skill.skill_dir, destination_root / skill.name, skill.name)
                prepared.prune_missing(destination_root / skill.name)
            if state.kind == "directory":
                for existing in destination_root.iterdir():
                    if existing.name not in canonical:
                        if existing.name in RETIRED_CANONICAL_SKILL_NAMES:
                            prepared.retire(existing)
                        else:
                            prepared.preserve(existing, "Unproven custom skill; preserve content and links")
        assessment = prepared.finish(home / "cache" / _VERSION_FILENAME, _get_cli_version())
        agents = tuple(iter_installable_agents())
        effects = []
        for effect in assessment.effects:
            logical = tuple(
                agent
                for agent in agents
                if (agent_root := get_primary_global_skill_root(agent)) is not None
                and (agent_root == effect.destination or agent_root in effect.destination.parents)
            )
            effects.append(replace(effect, logical_owners=logical or agents))
        assessment = replace(assessment, effects=tuple(effects))
        if _batch is not None:
            _batch.include(prepared, assessment.effects)
        return assessment
    except (OSError, ValueError, UnicodeError) as exc:
        return incomplete("global_skills", root, exc)


def ensure_global_agent_skills() -> None:
    """Repair actual canonical skill health and retain unchanged assets."""
    from specify_cli.runtime.asset_preparation import apply_assets, assess_global_assets, recheck_assets

    assessment = assess_global_assets(runtime=False, commands=False)
    if not assessment.complete:
        raise RuntimeError("; ".join(d.message for d in assessment.diagnostics))
    if not assessment.effects:
        return
    with recheck_assets(assessment) as diagnostics:
        if diagnostics:
            raise RuntimeError("; ".join(d.message for d in diagnostics))
        result = apply_assets(assessment, ApplyConsent(automatic=True))
    if result.outcome != "applied":
        raise RuntimeError("; ".join(d.message for d in result.diagnostics))
