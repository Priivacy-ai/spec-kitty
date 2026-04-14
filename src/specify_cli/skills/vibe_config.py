"""Helpers for project-local Mistral Vibe configuration."""

from __future__ import annotations

from pathlib import Path
import tomllib

import toml

VIBE_SKILL_PATH = ".agents/skills"


def ensure_project_skill_path(project_root: Path) -> None:
    """Ensure Vibe's project-local config discovers Spec Kitty's shared skills.

    Vibe's official discovery roots are ``.vibe/skills/`` and any custom paths
    listed in ``.vibe/config.toml``. Spec Kitty installs command skills into the
    shared ``.agents/skills/`` tree, so projects that configure Vibe need a
    matching ``skill_paths`` entry.
    """
    vibe_dir = project_root / ".vibe"
    vibe_dir.mkdir(parents=True, exist_ok=True)
    config_path = vibe_dir / "config.toml"

    data: dict[str, object]
    if config_path.exists():
        raw = config_path.read_text(encoding="utf-8")
        data = tomllib.loads(raw) if raw.strip() else {}
    else:
        data = {}

    skill_paths_raw = data.get("skill_paths")
    if skill_paths_raw is None:
        skill_paths: list[str] = []
    elif isinstance(skill_paths_raw, list):
        skill_paths = [str(value) for value in skill_paths_raw]
    elif isinstance(skill_paths_raw, str):
        skill_paths = [skill_paths_raw]
    else:
        raise ValueError("Expected .vibe/config.toml skill_paths to be a string or list")

    if VIBE_SKILL_PATH not in skill_paths:
        skill_paths.append(VIBE_SKILL_PATH)

    data["skill_paths"] = skill_paths
    config_path.write_text(toml.dumps(data), encoding="utf-8")
