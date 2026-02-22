"""Managed git hook support for centralized Spec Kitty hook execution.

This module keeps repository hooks minimal by writing tiny shims into
``.git/hooks`` and running the real hook logic from ``~/.kittify/hooks``.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
from typing import Iterable

from specify_cli.runtime.home import get_kittify_home, get_package_asset_root

HOOK_ENTRYPOINTS: tuple[str, ...] = ("pre-commit", "commit-msg")
MANAGED_SHIM_MARKER = "SPEC_KITTY_MANAGED_HOOK_SHIM=1"


@dataclass(frozen=True)
class ProjectShimInstallResult:
    """Result of writing per-project git hook shims."""

    hooks_dir: Path
    installed: tuple[str, ...]
    updated: tuple[str, ...]
    unchanged: tuple[str, ...]
    skipped_custom: tuple[str, ...]
    missing_global_targets: tuple[str, ...]


@dataclass(frozen=True)
class ProjectShimRemoveResult:
    """Result of removing per-project git hook shims."""

    hooks_dir: Path
    removed: tuple[str, ...]
    skipped_custom: tuple[str, ...]
    missing: tuple[str, ...]


@dataclass(frozen=True)
class HookStatus:
    """Status for one managed hook entrypoint."""

    name: str
    global_path: Path
    global_exists: bool
    project_path: Path
    project_exists: bool
    project_managed: bool
    project_points_to_global: bool


@dataclass(frozen=True)
class HookSyncResult:
    """Combined global + project hook synchronization result."""

    global_home: Path
    global_hooks_dir: Path
    global_hooks: tuple[str, ...]
    project: ProjectShimInstallResult


def get_package_hook_templates_root() -> Path | None:
    """Return package hook template directory if present."""
    try:
        asset_root = get_package_asset_root()
        candidate = asset_root.parent / "templates" / "git-hooks"
        if candidate.is_dir():
            return candidate
    except FileNotFoundError:
        pass

    # Legacy fallback for packages that still ship hooks under specify_cli/templates
    try:
        from importlib.resources import files

        pkg_hooks = files("specify_cli").joinpath("templates", "git-hooks")
        if hasattr(pkg_hooks, "is_dir") and pkg_hooks.is_dir():
            return Path(str(pkg_hooks))
    except (ModuleNotFoundError, TypeError):
        pass

    return None


def _quote_shell_literal(value: str) -> str:
    """Return a POSIX-safe single-quoted literal."""
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _render_hook_shim(hook_name: str, global_home: Path) -> str:
    """Render tiny shim that delegates hook execution to ~/.kittify/hooks."""
    default_home = _quote_shell_literal(str(global_home))
    return (
        "#!/usr/bin/env bash\n"
        f"# {MANAGED_SHIM_MARKER}\n"
        f"# Spec Kitty managed git hook shim ({hook_name})\n"
        "set -euo pipefail\n\n"
        f"DEFAULT_SPEC_KITTY_HOME={default_home}\n"
        'SPEC_KITTY_HOME="${SPEC_KITTY_HOME:-$DEFAULT_SPEC_KITTY_HOME}"\n'
        f'SPEC_KITTY_HOOK_TARGET="$SPEC_KITTY_HOME/hooks/{hook_name}"\n\n'
        'if [ ! -x "$SPEC_KITTY_HOOK_TARGET" ]; then\n'
        '  echo "spec-kitty: missing hook target $SPEC_KITTY_HOOK_TARGET" >&2\n'
        '  echo "Run \'spec-kitty hooks install\' to install/update managed hooks." >&2\n'
        "  exit 1\n"
        "fi\n\n"
        'exec "$SPEC_KITTY_HOOK_TARGET" "$@"\n'
    )


def is_managed_shim(path: Path) -> bool:
    """Return True when *path* is a Spec Kitty-managed shim."""
    if not path.is_file():
        return False
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return MANAGED_SHIM_MARKER in content


def _set_executable(path: Path) -> None:
    if os.name != "nt":
        path.chmod(0o755)


def install_global_hook_assets(
    *,
    global_home: Path | None = None,
    template_hooks_dir: Path | None = None,
) -> tuple[Path, tuple[str, ...]]:
    """Install/refresh hook scripts under ``~/.kittify/hooks``."""
    home = global_home or get_kittify_home()
    source = template_hooks_dir or get_package_hook_templates_root()
    if source is None or not source.is_dir():
        raise FileNotFoundError("hook templates not found in package assets")

    hooks_dir = home / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    installed: list[str] = []
    for hook_template in sorted(source.iterdir()):
        if not hook_template.is_file() or hook_template.name.startswith("."):
            continue
        dest = hooks_dir / hook_template.name
        shutil.copy2(hook_template, dest)
        _set_executable(dest)
        installed.append(hook_template.name)

    return hooks_dir, tuple(installed)


def install_project_hook_shims(
    project_path: Path,
    *,
    global_home: Path | None = None,
    hook_names: Iterable[str] = HOOK_ENTRYPOINTS,
    force: bool = False,
) -> ProjectShimInstallResult:
    """Install/refresh hook shims inside ``.git/hooks`` for one project."""
    hooks_dir = project_path / ".git" / "hooks"
    if not hooks_dir.is_dir():
        raise FileNotFoundError(".git/hooks directory not found")

    home = global_home or get_kittify_home()
    installed: list[str] = []
    updated: list[str] = []
    unchanged: list[str] = []
    skipped_custom: list[str] = []
    missing_global_targets: list[str] = []

    for hook_name in hook_names:
        global_hook = home / "hooks" / hook_name
        if not global_hook.is_file():
            missing_global_targets.append(hook_name)
            continue
        if os.name != "nt" and not os.access(global_hook, os.X_OK):
            _set_executable(global_hook)

        hook_dest = hooks_dir / hook_name
        shim_content = _render_hook_shim(hook_name, home)

        if hook_dest.exists():
            if is_managed_shim(hook_dest):
                try:
                    existing = hook_dest.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    existing = ""
                if existing == shim_content:
                    unchanged.append(hook_name)
                    continue
                updated.append(hook_name)
            elif not force:
                skipped_custom.append(hook_name)
                continue
            else:
                updated.append(hook_name)
        else:
            installed.append(hook_name)

        hook_dest.write_text(shim_content, encoding="utf-8")
        _set_executable(hook_dest)

    return ProjectShimInstallResult(
        hooks_dir=hooks_dir,
        installed=tuple(installed),
        updated=tuple(updated),
        unchanged=tuple(unchanged),
        skipped_custom=tuple(skipped_custom),
        missing_global_targets=tuple(missing_global_targets),
    )


def install_or_update_hooks(
    project_path: Path,
    *,
    global_home: Path | None = None,
    template_hooks_dir: Path | None = None,
    hook_names: Iterable[str] = HOOK_ENTRYPOINTS,
    force: bool = False,
) -> HookSyncResult:
    """Sync global hook assets and install/update project shims."""
    home = global_home or get_kittify_home()
    global_hooks_dir, global_hooks = install_global_hook_assets(
        global_home=home,
        template_hooks_dir=template_hooks_dir,
    )
    project_result = install_project_hook_shims(
        project_path,
        global_home=home,
        hook_names=hook_names,
        force=force,
    )
    return HookSyncResult(
        global_home=home,
        global_hooks_dir=global_hooks_dir,
        global_hooks=global_hooks,
        project=project_result,
    )


def remove_project_hook_shims(
    project_path: Path,
    *,
    hook_names: Iterable[str] = HOOK_ENTRYPOINTS,
    force: bool = False,
) -> ProjectShimRemoveResult:
    """Remove managed per-project hook shims."""
    hooks_dir = project_path / ".git" / "hooks"
    if not hooks_dir.is_dir():
        raise FileNotFoundError(".git/hooks directory not found")

    removed: list[str] = []
    skipped_custom: list[str] = []
    missing: list[str] = []

    for hook_name in hook_names:
        hook_path = hooks_dir / hook_name
        if not hook_path.exists():
            missing.append(hook_name)
            continue
        if force or is_managed_shim(hook_path):
            hook_path.unlink()
            removed.append(hook_name)
        else:
            skipped_custom.append(hook_name)

    return ProjectShimRemoveResult(
        hooks_dir=hooks_dir,
        removed=tuple(removed),
        skipped_custom=tuple(skipped_custom),
        missing=tuple(missing),
    )


def get_project_hook_status(
    project_path: Path,
    *,
    global_home: Path | None = None,
    hook_names: Iterable[str] = HOOK_ENTRYPOINTS,
) -> tuple[HookStatus, ...]:
    """Inspect global hook targets and project shims."""
    hooks_dir = project_path / ".git" / "hooks"
    if not hooks_dir.is_dir():
        raise FileNotFoundError(".git/hooks directory not found")

    home = global_home or get_kittify_home()
    statuses: list[HookStatus] = []

    for hook_name in hook_names:
        global_path = home / "hooks" / hook_name
        project_path_hook = hooks_dir / hook_name
        project_exists = project_path_hook.exists()
        project_managed = is_managed_shim(project_path_hook)
        points_to_global = False

        if project_managed:
            try:
                content = project_path_hook.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                content = ""
            points_to_global = f"/hooks/{hook_name}" in content

        statuses.append(
            HookStatus(
                name=hook_name,
                global_path=global_path,
                global_exists=global_path.is_file(),
                project_path=project_path_hook,
                project_exists=project_exists,
                project_managed=project_managed,
                project_points_to_global=points_to_global,
            )
        )

    return tuple(statuses)
