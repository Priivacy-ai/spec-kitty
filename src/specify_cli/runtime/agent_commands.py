"""Bootstrap canonical command files and project projections."""

from __future__ import annotations

import filecmp
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from specify_cli.core.config import AGENT_COMMAND_CONFIG, LEGACY_ONLY_COMMAND_AGENTS
from specify_cli.runtime.bootstrap import _get_cli_version, _lock_exclusive
from specify_cli.runtime.home import get_kittify_home, get_package_asset_root
from specify_cli.runtime.resolver import resolve_command
from specify_cli.shims.generator import generate_shims_for_agent_dir
from specify_cli.shims.registry import CLI_DRIVEN_COMMANDS, PROMPT_DRIVEN_COMMANDS
from specify_cli.template.asset_generator import (
    generate_agent_assets_to_dir,
    render_command_template,
)

logger = logging.getLogger(__name__)

_DEFAULT_MISSION = "software-dev"
_DEFAULT_SCRIPT_TYPE = "sh"
_VERSION_FILENAME = "agent-commands.lock"
_LOCK_FILENAME = ".agent-commands.lock"


@dataclass
class AgentCommandInstallResult:
    """Summary of one project command installation pass."""

    agent_key: str
    mode: str
    files_written: list[Path] = field(default_factory=list)
    files_removed: list[Path] = field(default_factory=list)


def supports_managed_commands(agent_key: str) -> bool:
    """Return True when Spec Kitty should manage command files for *agent_key*."""
    return agent_key in AGENT_COMMAND_CONFIG and agent_key not in LEGACY_ONLY_COMMAND_AGENTS


def iter_command_agents() -> list[str]:
    """Return agents whose command files are centrally managed."""
    return sorted(agent_key for agent_key in AGENT_COMMAND_CONFIG if supports_managed_commands(agent_key))


def get_primary_project_command_root(agent_key: str) -> str | None:
    """Return the project-local managed command root for an agent."""
    if not supports_managed_commands(agent_key):
        return None
    return AGENT_COMMAND_CONFIG[agent_key]["dir"]


def get_primary_global_command_root(agent_key: str) -> Path | None:
    """Return the user-global canonical command root for an agent."""
    project_root = get_primary_project_command_root(agent_key)
    if project_root is None:
        return None
    return Path.home() / project_root.strip("/")


def _resolve_script_type() -> str:
    return "ps" if os.name == "nt" else _DEFAULT_SCRIPT_TYPE


def _make_tree_read_only(root: Path) -> None:
    for file_path in root.glob("spec-kitty.*"):
        if not file_path.is_file():
            continue
        mode = file_path.stat().st_mode
        file_path.chmod(mode & ~0o222)


def _command_templates_dir() -> Path | None:
    try:
        pkg_root = get_package_asset_root()
    except FileNotFoundError:
        return None
    templates_dir = pkg_root / _DEFAULT_MISSION / "command-templates"
    if templates_dir.is_dir():
        return templates_dir
    return None


def _sync_global_command_root(agent_key: str, templates_dir: Path, script_type: str) -> list[Path]:
    root = get_primary_global_command_root(agent_key)
    if root is None:
        return []

    root.mkdir(parents=True, exist_ok=True)
    written = generate_agent_assets_to_dir(
        templates_dir,
        root,
        agent_key,
        script_type,
        clear_existing=False,
    )
    written.extend(generate_shims_for_agent_dir(root, agent_key))
    _make_tree_read_only(root)
    return sorted(written)


def ensure_global_agent_commands() -> None:
    """Ensure user-global canonical command roots are current for this CLI version."""
    templates_dir = _command_templates_dir()
    if templates_dir is None:
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

        script_type = _resolve_script_type()
        for agent_key in iter_command_agents():
            _sync_global_command_root(agent_key, templates_dir, script_type)
        version_file.write_text(cli_version)
    finally:
        lock_fd.close()


def _ensure_backup_root(project_path: Path, backup_root: Path | None) -> Path:
    if backup_root is not None:
        return backup_root

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = project_path / ".kittify" / ".migration-backup" / "agent-commands" / timestamp
    root.mkdir(parents=True, exist_ok=True)
    return root


def _archive_existing_path(dest: Path, project_path: Path, backup_root: Path | None) -> Path:
    backup_root = _ensure_backup_root(project_path, backup_root)
    backup_path = backup_root / dest.relative_to(project_path)
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(dest), str(backup_path))
    return backup_root


def _project_global_file(
    source_file: Path,
    dest: Path,
    project_path: Path,
    *,
    backup_root: Path | None,
) -> tuple[Path | None, bool]:
    if dest.is_symlink():
        try:
            if dest.resolve() == source_file.resolve():
                return backup_root, False
        except OSError:
            pass
        dest.unlink()
    elif dest.exists():
        backup_root = _archive_existing_path(dest, project_path, backup_root)

    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        dest.symlink_to(source_file)
    except OSError:
        shutil.copy2(source_file, dest)
    return backup_root, True


def _files_match(source_file: Path, dest: Path) -> bool:
    """Return True when *dest* already mirrors *source_file*."""
    if not dest.exists():
        return False

    if dest.is_symlink():
        try:
            return dest.resolve() == source_file.resolve()
        except OSError:
            return False

    if not dest.is_file():
        return False

    try:
        return filecmp.cmp(source_file, dest, shallow=False)
    except OSError:
        return False


def _expected_managed_filenames(agent_key: str) -> set[str]:
    config = AGENT_COMMAND_CONFIG[agent_key]
    ext = config["ext"]
    filenames: set[str] = set()

    for command in sorted(PROMPT_DRIVEN_COMMANDS):
        stem = command
        if agent_key == "codex":
            stem = stem.replace("-", "_")
        filenames.add(f"spec-kitty.{stem}.{ext}" if ext else f"spec-kitty.{stem}")

    for command in sorted(CLI_DRIVEN_COMMANDS):
        filenames.add(f"spec-kitty.{command}.md")

    return filenames


def project_command_install_needed(project_path: Path, agent_key: str) -> bool:
    """Return True when an agent's managed command surface needs normalization."""
    if agent_key in LEGACY_ONLY_COMMAND_AGENTS:
        codex_config = AGENT_COMMAND_CONFIG.get(agent_key)
        if codex_config is None:
            return False
        return (project_path / codex_config["dir"]).exists()

    if not supports_managed_commands(agent_key):
        return False

    project_root = get_primary_project_command_root(agent_key)
    if project_root is None:
        return False

    target_root = project_path / project_root
    expected_names = _expected_managed_filenames(agent_key)

    if _project_has_command_overrides(project_path):
        if not target_root.is_dir():
            return True
        current_names = {
            path.name
            for path in target_root.glob("spec-kitty.*")
            if path.is_file() or path.is_symlink()
        }
        return current_names != expected_names

    global_root = get_primary_global_command_root(agent_key)
    if global_root is None or not global_root.is_dir():
        return True
    if not target_root.is_dir():
        return True

    canonical_files = sorted(
        path for path in global_root.glob("spec-kitty.*") if path.is_file() or path.is_symlink()
    )
    current_names = {
        path.name
        for path in target_root.glob("spec-kitty.*")
        if path.is_file() or path.is_symlink()
    }
    if current_names != {path.name for path in canonical_files}:
        return True

    for source_file in canonical_files:
        if not _files_match(source_file, target_root / source_file.name):
            return True

    return False


def _project_global_commands(project_path: Path, agent_key: str) -> AgentCommandInstallResult:
    global_root = get_primary_global_command_root(agent_key)
    project_root = get_primary_project_command_root(agent_key)
    if global_root is None or project_root is None:
        return AgentCommandInstallResult(agent_key=agent_key, mode="unsupported")

    ensure_global_agent_commands()
    target_root = project_path / project_root
    target_root.mkdir(parents=True, exist_ok=True)

    canonical_files = sorted(
        path for path in global_root.glob("spec-kitty.*") if path.is_file() or path.is_symlink()
    )
    expected_names = {path.name for path in canonical_files}

    backup_root: Path | None = None
    files_written: list[Path] = []
    files_removed: list[Path] = []

    for existing in sorted(target_root.glob("spec-kitty.*")):
        if existing.name in expected_names:
            continue
        backup_root = _archive_existing_path(existing, project_path, backup_root)
        files_removed.append(existing)

    for source_file in canonical_files:
        dest = target_root / source_file.name
        backup_root, changed = _project_global_file(
            source_file,
            dest,
            project_path,
            backup_root=backup_root,
        )
        if changed:
            files_written.append(dest)

    return AgentCommandInstallResult(
        agent_key=agent_key,
        mode="projected",
        files_written=files_written,
        files_removed=files_removed,
    )


def _project_has_command_overrides(project_path: Path) -> bool:
    candidates = (
        project_path / ".kittify" / "overrides" / "command-templates",
        project_path / ".kittify" / "command-templates",
    )
    return any(candidate.is_dir() and any(candidate.glob("*.md")) for candidate in candidates)


def _render_override_commands(project_path: Path, agent_key: str) -> AgentCommandInstallResult:
    project_root = get_primary_project_command_root(agent_key)
    if project_root is None:
        return AgentCommandInstallResult(agent_key=agent_key, mode="unsupported")

    config = AGENT_COMMAND_CONFIG[agent_key]
    target_root = project_path / project_root
    target_root.mkdir(parents=True, exist_ok=True)

    # Replace only Spec Kitty managed files so user-defined commands survive.
    for existing in target_root.glob("spec-kitty.*"):
        existing.unlink()

    written: list[Path] = []
    script_type = _resolve_script_type()
    for command in sorted(PROMPT_DRIVEN_COMMANDS):
        resolved = resolve_command(f"{command}.md", project_path, mission=_DEFAULT_MISSION)
        rendered = render_command_template(
            template_path=resolved.path,
            script_type=script_type,
            agent_key=agent_key,
            arg_format=config["arg_format"],
            extension=config["ext"],
        )
        stem = command
        if agent_key == "codex":
            stem = stem.replace("-", "_")
        filename = f"spec-kitty.{stem}.{config['ext']}" if config["ext"] else f"spec-kitty.{stem}"
        out_path = target_root / filename
        out_path.write_text(rendered, encoding="utf-8")
        written.append(out_path)

    written.extend(generate_shims_for_agent_dir(target_root, agent_key))
    return AgentCommandInstallResult(agent_key=agent_key, mode="override-local", files_written=written)


def retire_legacy_codex_prompts(project_path: Path) -> AgentCommandInstallResult:
    """Archive/remove legacy Spec Kitty prompt files from `.codex/prompts`."""
    codex_config = AGENT_COMMAND_CONFIG.get("codex")
    if codex_config is None:
        return AgentCommandInstallResult(agent_key="codex", mode="legacy-retired")

    target_root = project_path / codex_config["dir"]
    if not target_root.exists():
        return AgentCommandInstallResult(agent_key="codex", mode="legacy-retired")

    backup_root: Path | None = None
    removed: list[Path] = []
    for existing in sorted(target_root.glob("spec-kitty.*")):
        backup_root = _archive_existing_path(existing, project_path, backup_root)
        removed.append(existing)

    if target_root.is_dir() and not any(target_root.iterdir()):
        target_root.rmdir()
        codex_root = target_root.parent
        if codex_root.is_dir() and not any(codex_root.iterdir()):
            codex_root.rmdir()

    return AgentCommandInstallResult(agent_key="codex", mode="legacy-retired", files_removed=removed)


def install_project_commands_for_agent(project_path: Path, agent_key: str) -> AgentCommandInstallResult:
    """Install managed project command files for one agent."""
    if agent_key in LEGACY_ONLY_COMMAND_AGENTS:
        return retire_legacy_codex_prompts(project_path)

    if not supports_managed_commands(agent_key):
        return AgentCommandInstallResult(agent_key=agent_key, mode="unsupported")

    if _project_has_command_overrides(project_path):
        return _render_override_commands(project_path, agent_key)

    return _project_global_commands(project_path, agent_key)
