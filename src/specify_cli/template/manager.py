"""Template discovery and copy helpers."""

from __future__ import annotations

import os
import shutil
from importlib.resources.abc import Traversable
from importlib.resources import files
from pathlib import Path

from rich.console import Console

console = Console()


def _copy_charter_toolguide_from_path(source: Path, project_path: Path) -> bool:
    """Copy a local toolguide file into .kittify/memory/templates/."""
    if not source.exists():
        return False
    dest_dir = project_path / ".kittify" / "memory" / "templates"
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest_dir / source.name)
    return True


def _resource_exists(resource: Traversable) -> bool:
    return resource.is_file() or resource.is_dir()


def _copy_charter_toolguide_from_resource(resource: Traversable, project_path: Path) -> bool:
    """Copy a package resource toolguide into .kittify/memory/templates/."""
    if not _resource_exists(resource):
        return False
    dest_dir = project_path / ".kittify" / "memory" / "templates"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / resource.name
    with resource.open("rb") as src, open(dest_file, "wb") as dst:
        shutil.copyfileobj(src, dst)
    return True


def copy_charter_templates(project_path: Path, repo_root: Path | None = None) -> None:
    """Install charter-scoped template assets (toolguides).

    Currently installs the PowerShell syntax guide to:
    ``.kittify/memory/templates/POWERSHELL_SYNTAX.md``.
    """
    if repo_root is not None:
        local_toolguide = repo_root / "src" / "doctrine" / "toolguides" / "POWERSHELL_SYNTAX.md"
        if _copy_charter_toolguide_from_path(local_toolguide, project_path):
            return

    # Package-first source for installed distributions
    try:
        doctrine_root = files("doctrine")
        doctrine_toolguide = doctrine_root.joinpath("toolguides", "POWERSHELL_SYNTAX.md")
        if _copy_charter_toolguide_from_resource(doctrine_toolguide, project_path):
            return
    except ModuleNotFoundError:
        pass


def copy_specify_base_from_local(repo_root: Path, project_path: Path) -> Path:
    """Copy the embedded .kittify assets from a local repository checkout."""
    specify_root = project_path / ".kittify"
    specify_root.mkdir(parents=True, exist_ok=True)

    # Copy from .kittify/memory/ for consistency with other .kittify paths
    memory_src = repo_root / ".kittify" / "memory"
    if memory_src.exists():
        memory_dest = specify_root / "memory"
        if memory_dest.exists():
            shutil.rmtree(memory_dest)
        shutil.copytree(memory_src, memory_dest)

    # Copy from src/doctrine/templates/ (doctrine artifacts).
    # Mission content templates live under src/doctrine/missions/<mission>/templates.
    templates_src = repo_root / "src" / "doctrine" / "templates"
    if templates_src.exists():
        templates_dest = specify_root / "templates"
        if templates_dest.exists():
            shutil.rmtree(templates_dest)
        shutil.copytree(templates_src, templates_dest)
        agents_template = templates_src / "AGENTS.md"
        if agents_template.exists():
            shutil.copy2(agents_template, specify_root / "AGENTS.md")

    missions_src = repo_root / "src" / "doctrine" / "missions"
    if missions_src.exists():
        missions_dest = specify_root / "missions"
        if missions_dest.exists():
            shutil.rmtree(missions_dest)
        shutil.copytree(missions_src, missions_dest)

    copy_charter_templates(project_path, repo_root=repo_root)

    # NOTE: Templates are copied temporarily for agent command generation
    # They will be cleaned up after all commands are generated (see init.py)
    return specify_root / "templates" / "command-templates"


def copy_package_tree(resource: Traversable, dest: Path) -> None:
    """Recursively copy an importlib.resources directory tree."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for child in resource.iterdir():
        target = dest / child.name
        if child.is_dir():
            copy_package_tree(child, target)
        else:
            with child.open("rb") as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)


def copy_specify_base_from_package(project_path: Path) -> Path:
    """Copy the packaged .kittify assets that ship with the CLI."""
    specify_data_root = files("specify_cli")
    specify_root = project_path / ".kittify"
    specify_root.mkdir(parents=True, exist_ok=True)

    memory_resource = specify_data_root.joinpath("memory")
    if _resource_exists(memory_resource):
        copy_package_tree(memory_resource, specify_root / "memory")

    try:
        doctrine_data_root = files("doctrine")
    except (ModuleNotFoundError, TypeError):
        doctrine_data_root = specify_data_root

    templates_resource_candidates = [
        doctrine_data_root.joinpath("templates"),
        specify_data_root.joinpath("templates"),  # Legacy fallback
    ]
    for templates_resource in templates_resource_candidates:
        if _resource_exists(templates_resource):
            templates_dest = specify_root / "templates"
            copy_package_tree(templates_resource, templates_dest)
            agents_template = templates_resource.joinpath("AGENTS.md")
            if _resource_exists(agents_template):
                with agents_template.open("rb") as src, open(specify_root / "AGENTS.md", "wb") as dst:
                    shutil.copyfileobj(src, dst)
            break

    missions_resource_candidates = [
        doctrine_data_root.joinpath("missions"),
        specify_data_root.joinpath("missions"),  # Legacy fallback
        specify_data_root.joinpath(".kittify", "missions"),  # Legacy fallback
        specify_data_root.joinpath("template_data", "missions"),  # Legacy fallback
    ]
    for missions_resource in missions_resource_candidates:
        if _resource_exists(missions_resource):
            copy_package_tree(missions_resource, specify_root / "missions")
            break

    copy_charter_templates(project_path)

    return specify_root / "templates" / "command-templates"


def get_local_repo_root(override_path: str | None = None) -> Path | None:
    """Return repository root when running from a local checkout, else None.

    Args:
        override_path: Optional override path (e.g., from --template-root flag)

    Returns:
        Path to repository root containing doctrine templates and missions, or None
    """
    def _is_template_root(path: Path) -> bool:
        return (
            (path / "src" / "doctrine" / "templates" / "AGENTS.md").is_file()
            and (path / "src" / "doctrine" / "missions").is_dir()
        )

    # Check override path first (from --template-root flag)
    if override_path:
        override = Path(override_path).expanduser().resolve()
        if _is_template_root(override):
            return override
        # Legacy fallback for old template structure
        if (override / ".kittify" / "templates" / "command-templates").exists():
            return override
        console.print(
            f"[yellow]--template-root {override} is not a Spec Kitty checkout/template root; using packaged templates.[/yellow]"  # noqa: E501
        )

    # Check environment variable
    env_root = os.environ.get("SPEC_KITTY_TEMPLATE_ROOT")
    if env_root:
        root_path = Path(env_root).expanduser().resolve()
        if _is_template_root(root_path):
            return root_path
        # Legacy fallback for old template structure
        if (root_path / ".kittify" / "templates" / "command-templates").exists():
            return root_path
        console.print(
            f"[yellow]SPEC_KITTY_TEMPLATE_ROOT {root_path} is not a Spec Kitty checkout/template root; using packaged templates.[/yellow]"  # noqa: E501
        )

    # Check package location
    candidate = Path(__file__).resolve().parents[3]
    if _is_template_root(candidate):
        return candidate
    # Legacy fallback for old template structure
    if (candidate / ".kittify" / "templates" / "command-templates").exists():
        return candidate
    return None


__all__ = [
    "copy_package_tree",
    "copy_charter_templates",
    "copy_specify_base_from_local",
    "copy_specify_base_from_package",
    "get_local_repo_root",
]
