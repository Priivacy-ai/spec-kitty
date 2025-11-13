"""Template discovery and copy helpers."""

from __future__ import annotations

import os
import shutil
from importlib.resources import files
from pathlib import Path

from rich.console import Console

console = Console()


def get_local_repo_root(override_path: str | None = None) -> Path | None:
    """Return repository root when running from a local checkout, else None.

    Args:
        override_path: Optional override path (e.g., from --template-root flag)

    Returns:
        Path to repository root containing templates/commands, or None
    """
    # Check override path first (from --template-root flag)
    if override_path:
        override = Path(override_path).expanduser().resolve()
        if (override / "templates" / "commands").exists():
            return override
        console.print(
            f"[yellow]--template-root set to {override}, but templates/commands not found there. Ignoring.[/yellow]"
        )

    # Check environment variable
    env_root = os.environ.get("SPEC_KITTY_TEMPLATE_ROOT")
    if env_root:
        root_path = Path(env_root).expanduser().resolve()
        if (root_path / "templates" / "commands").exists():
            return root_path
        console.print(
            f"[yellow]SPEC_KITTY_TEMPLATE_ROOT set to {root_path}, but templates/commands not found there. Ignoring.[/yellow]"
        )

    # Check package location
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / "templates" / "commands").exists():
        return candidate
    return None


def copy_specify_base_from_local(repo_root: Path, project_path: Path, script_type: str) -> Path:
    """Copy the embedded .kittify assets from a local repository checkout."""
    specify_root = project_path / ".kittify"
    specify_root.mkdir(parents=True, exist_ok=True)

    memory_src = repo_root / "memory"
    if memory_src.exists():
        memory_dest = specify_root / "memory"
        if memory_dest.exists():
            shutil.rmtree(memory_dest)
        shutil.copytree(memory_src, memory_dest)

    scripts_src = repo_root / "scripts"
    if scripts_src.exists():
        scripts_dest = specify_root / "scripts"
        if scripts_dest.exists():
            shutil.rmtree(scripts_dest)
        scripts_dest.mkdir(parents=True, exist_ok=True)
        variant = "bash" if script_type == "sh" else "powershell"
        variant_src = scripts_src / variant
        if variant_src.exists():
            shutil.copytree(variant_src, scripts_dest / variant)
        tasks_src = scripts_src / "tasks"
        if tasks_src.exists():
            shutil.copytree(tasks_src, scripts_dest / "tasks")
        for item in scripts_src.iterdir():
            if item.is_file():
                shutil.copy2(item, scripts_dest / item.name)

    templates_src = repo_root / "templates"
    if templates_src.exists():
        templates_dest = specify_root / "templates"
        if templates_dest.exists():
            shutil.rmtree(templates_dest)
        shutil.copytree(templates_src, templates_dest)
        agents_template = templates_src / "AGENTS.md"
        if agents_template.exists():
            shutil.copy2(agents_template, specify_root / "AGENTS.md")

    missions_candidates = [
        repo_root / ".kittify" / "missions",
        repo_root / "src" / "specify_cli" / ".kittify" / "missions",
    ]
    for missions_src in missions_candidates:
        if missions_src.exists():
            missions_dest = specify_root / "missions"
            if missions_dest.exists():
                shutil.rmtree(missions_dest)
            shutil.copytree(missions_src, missions_dest)
            break

    return specify_root / "templates" / "commands"


def copy_package_tree(resource, dest: Path) -> None:
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


def copy_specify_base_from_package(project_path: Path, script_type: str) -> Path:
    """Copy the packaged .kittify assets that ship with the CLI."""
    data_root = files("specify_cli")
    specify_root = project_path / ".kittify"
    specify_root.mkdir(parents=True, exist_ok=True)

    memory_resource = data_root.joinpath("memory")
    if memory_resource.exists():
        copy_package_tree(memory_resource, specify_root / "memory")

    scripts_resource = data_root.joinpath("scripts")
    if scripts_resource.exists():
        scripts_dest = specify_root / "scripts"
        if scripts_dest.exists():
            shutil.rmtree(scripts_dest)
        scripts_dest.mkdir(parents=True, exist_ok=True)
        variant_name = "bash" if script_type == "sh" else "powershell"
        variant_resource = scripts_resource.joinpath(variant_name)
        if variant_resource.exists():
            copy_package_tree(variant_resource, scripts_dest / variant_name)
        tasks_resource = scripts_resource.joinpath("tasks")
        if tasks_resource.exists():
            copy_package_tree(tasks_resource, scripts_dest / "tasks")
        for resource_file in scripts_resource.iterdir():
            if resource_file.is_file():
                with resource_file.open("rb") as src, open(
                    scripts_dest / resource_file.name, "wb"
                ) as dst:
                    shutil.copyfileobj(src, dst)

    templates_resource = data_root.joinpath("templates")
    if templates_resource.exists():
        templates_dest = specify_root / "templates"
        copy_package_tree(templates_resource, templates_dest)
        agents_template = templates_resource.joinpath("AGENTS.md")
        if agents_template.exists():
            with agents_template.open("rb") as src, open(
                specify_root / "AGENTS.md", "wb"
            ) as dst:
                shutil.copyfileobj(src, dst)

    missions_resource_candidates = [
        data_root.joinpath(".kittify", "missions"),
        data_root.joinpath("template_data", "missions"),
    ]
    for missions_resource in missions_resource_candidates:
        if missions_resource.exists():
            copy_package_tree(missions_resource, specify_root / "missions")
            break

    return specify_root / "templates" / "commands"


__all__ = [
    "copy_package_tree",
    "copy_specify_base_from_local",
    "copy_specify_base_from_package",
    "get_local_repo_root",
]
