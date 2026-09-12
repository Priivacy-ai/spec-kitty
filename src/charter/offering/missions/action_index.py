"""Action index loader for mission-scoped context retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError


class ActionIndexError(ValueError):
    """A present action-index file is not a well-formed ActionIndex.

    Raised by :func:`load_action_index` when the index file exists but its
    content violates the contract: the root is not a YAML mapping, an
    artifact-kind field's value is not a list, or the file cannot be parsed
    or read. A genuinely-missing index file is NOT an error — it resolves to
    an empty :class:`ActionIndex` (present ⇒ well-formed; absent ⇒ empty).
    """


@dataclass(frozen=True)
class ActionIndex:
    """Index of doctrine artifacts relevant to a specific mission action."""

    action: str
    directives: list[str] = field(default_factory=list)
    tactics: list[str] = field(default_factory=list)
    paradigms: list[str] = field(default_factory=list)
    styleguides: list[str] = field(default_factory=list)
    toolguides: list[str] = field(default_factory=list)
    procedures: list[str] = field(default_factory=list)
    agent_profiles: list[str] = field(default_factory=list)


def load_action_index(missions_root: Path, mission: str, action: str) -> ActionIndex:
    """Load action index from missions_root/<mission>/actions/<action>/index.yaml.

    Contract (present ⇒ well-formed; absent ⇒ empty, operator DD-4 / #2667):
    a genuinely-missing index file silently resolves to an empty
    ``ActionIndex(action=action)``. A *present* index file must be
    well-formed — a present-but-malformed index raises
    :class:`ActionIndexError` rather than silently degrading to an empty
    grain, so callers (e.g. the FR-013 cross-grain union) never pass falsely
    over dropped doctrine.

    Args:
        missions_root: Root directory containing mission subdirectories.
        mission: Mission name (e.g. "software-dev").
        action: Action name (e.g. "implement").

    Returns:
        ActionIndex with the loaded data, or the missing-file fallback.

    Raises:
        ActionIndexError: The index file is present but not well-formed:
            the root is not a YAML mapping, an artifact-kind field's value
            is not a list, or the file cannot be parsed or read.
    """
    index_path = missions_root / mission / "actions" / action / "index.yaml"

    if not index_path.exists():
        return ActionIndex(action=action)

    data = _read_index_yaml(index_path)

    if not isinstance(data, dict):
        raise ActionIndexError(
            f"Expected a YAML mapping at <root> in {index_path}; "
            f"got {type(data).__name__}"
        )

    return ActionIndex(
        action=str(data.get("action", action)),
        directives=_require_list(data, "directives", index_path),
        tactics=_require_list(data, "tactics", index_path),
        paradigms=_require_list(data, "paradigms", index_path),
        styleguides=_require_list(data, "styleguides", index_path),
        toolguides=_require_list(data, "toolguides", index_path),
        procedures=_require_list(data, "procedures", index_path),
        agent_profiles=_require_list(data, "agent_profiles", index_path),
    )


def _read_index_yaml(index_path: Path) -> object:
    """Read and parse *index_path* as YAML, wrapping I/O and parse errors.

    Raises:
        ActionIndexError: The file could not be read or parsed. A present
            file that fails here is present-but-invalid, not missing.
    """
    try:
        yaml = YAML(typ="safe")
        return yaml.load(index_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, YAMLError) as exc:
        raise ActionIndexError(
            f"Could not read or parse action index at {index_path}: "
            f"{type(exc).__name__}: {exc}"
        ) from exc


def _require_list(data: dict[object, object], key: str, index_path: Path) -> list[str]:
    """Extract *key* from *data* as a list of strings, or raise.

    Raises:
        ActionIndexError: The field's value is present but not a list.
    """
    raw = data.get(key, [])
    if not isinstance(raw, list):
        raise ActionIndexError(
            f"Expected a list for {key!r} in {index_path}; got {type(raw).__name__}"
        )
    return [str(item) for item in raw if item is not None]
