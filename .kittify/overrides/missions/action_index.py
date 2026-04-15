"""Action index loader for mission-scoped context retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError


@dataclass(frozen=True)
class ActionIndex:
    """Index of doctrine artifacts relevant to a specific mission action."""

    action: str
    directives: list[str] = field(default_factory=list)
    tactics: list[str] = field(default_factory=list)
    styleguides: list[str] = field(default_factory=list)
    toolguides: list[str] = field(default_factory=list)
    procedures: list[str] = field(default_factory=list)


def load_action_index(missions_root: Path, mission: str, action: str) -> ActionIndex:
    """Load action index from missions_root/<mission>/actions/<action>/index.yaml.

    Returns ActionIndex(action=action) as fallback when missing or corrupt.

    Args:
        missions_root: Root directory containing mission subdirectories.
        mission: Mission name (e.g. "software-dev").
        action: Action name (e.g. "implement").

    Returns:
        ActionIndex with the loaded data, or a minimal fallback on error.
    """
    index_path = missions_root / mission / "actions" / action / "index.yaml"
    fallback = ActionIndex(action=action)

    if not index_path.exists():
        return fallback

    try:
        yaml = YAML(typ="safe")
        data = yaml.load(index_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return fallback

        def _str_list(key: str) -> list[str]:
            raw = data.get(key, [])
            if not isinstance(raw, list):
                return []
            return [str(item) for item in raw if item is not None]

        return ActionIndex(
            action=str(data.get("action", action)),
            directives=_str_list("directives"),
            tactics=_str_list("tactics"),
            styleguides=_str_list("styleguides"),
            toolguides=_str_list("toolguides"),
            procedures=_str_list("procedures"),
        )
    except (OSError, UnicodeDecodeError, YAMLError):
        return fallback
