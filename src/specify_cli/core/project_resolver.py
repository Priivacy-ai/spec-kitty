"""Project path resolution helpers for Spec Kitty."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from rich.console import Console

from specify_cli.core.config import DEFAULT_MISSION_KEY

ConsoleType = Console | None


def _resolve_console(console: ConsoleType) -> Console:
    return console if console is not None else Console()


def locate_project_root(start: Path | None = None) -> Optional[Path]:
    """Walk upwards from *start* (or CWD) to find the directory that owns .kittify."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".kittify").is_dir():
            return candidate
    return None


def resolve_template_path(project_root: Path, mission_key: str, template_subpath: str | Path) -> Optional[Path]:
    """Resolve a template path, preferring mission overrides before global templates."""
    subpath = Path(template_subpath)
    candidates = [
        project_root / ".kittify" / "missions" / mission_key / "templates" / subpath,
        project_root / ".kittify" / "templates" / subpath,
        project_root / "templates" / subpath,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def resolve_worktree_aware_feature_dir(
    repo_root: Path,
    feature_slug: str,
    cwd: Path | None = None,
    console: ConsoleType = None,
) -> Path:
    """Resolve the correct feature directory, preferring worktree locations when available."""
    resolved_console = _resolve_console(console)
    current_dir = (cwd or Path.cwd()).resolve()

    parts = current_dir.parts
    for idx, part in enumerate(parts):
        if part == ".worktrees" and idx + 1 < len(parts) and parts[idx + 1] == feature_slug:
            worktree_root = Path(*parts[: idx + 2])
            feature_dir = worktree_root / "kitty-specs" / feature_slug
            resolved_console.print(f"[green]✓[/green] Using worktree location: {feature_dir}")
            return feature_dir

    worktree_path = repo_root / ".worktrees" / feature_slug
    if worktree_path.exists():
        feature_dir = worktree_path / "kitty-specs" / feature_slug
        resolved_console.print(f"[green]✓[/green] Found worktree, using: {feature_dir}")
        resolved_console.print(f"[yellow]Tip:[/yellow] Run commands from {worktree_path} for better isolation")
        return feature_dir

    feature_dir = repo_root / "kitty-specs" / feature_slug
    resolved_console.print(f"[yellow]⚠[/yellow] No worktree found, using root location: {feature_dir}")
    resolved_console.print(
        f"[yellow]Tip:[/yellow] Consider creating a worktree with: git worktree add .worktrees/{feature_slug} {feature_slug}"
    )
    return feature_dir


def get_active_mission_key(project_path: Path) -> str:
    """Return the mission key stored in .kittify/active-mission, falling back to default."""
    active_path = project_path / ".kittify" / "active-mission"
    if not active_path.exists():
        return DEFAULT_MISSION_KEY

    if active_path.is_symlink():
        try:
            target = Path(os.readlink(active_path))
            key = target.name
            if key:
                return key
        except OSError:
            pass
        resolved = active_path.resolve()
        if resolved.parent.name == "missions":
            return resolved.name

    if active_path.is_file():
        try:
            key = active_path.read_text(encoding="utf-8").strip()
            if key:
                return key
        except OSError:
            pass

    return DEFAULT_MISSION_KEY


__all__ = [
    "get_active_mission_key",
    "locate_project_root",
    "resolve_template_path",
    "resolve_worktree_aware_feature_dir",
]
