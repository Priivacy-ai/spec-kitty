"""Mission template schema utilities for the runtime shim."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class MissionRuntimeError(RuntimeError):
    """Raised when runtime operations cannot proceed."""


@dataclass(frozen=True)
class ActorIdentity:
    """Actor metadata attached to decision answers."""

    actor_id: str
    actor_type: str


@dataclass(frozen=True)
class MissionMeta:
    key: str
    name: str
    version: str


@dataclass(frozen=True)
class MissionStep:
    id: str
    title: str = ""
    description: str = ""
    prompt_template: str | None = None
    depends_on: list[str] = field(default_factory=list)
    requires_inputs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MissionTemplate:
    mission: MissionMeta
    steps: list[MissionStep]



def _as_string(value: Any, *, field_name: str) -> str:
    if isinstance(value, str) and value.strip():
        return value
    raise MissionRuntimeError(f"Invalid mission template: '{field_name}' must be a non-empty string")



def _as_string_list(value: Any, *, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise MissionRuntimeError(f"Invalid mission template: '{field_name}' must be a list of strings")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise MissionRuntimeError(f"Invalid mission template: '{field_name}' must contain only strings")
        result.append(item)
    return result



def load_mission_template_file(path: Path | str) -> MissionTemplate:
    """Load a mission runtime template from YAML."""
    template_path = Path(path)
    try:
        raw = yaml.safe_load(template_path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise MissionRuntimeError(f"Unable to read mission template: {template_path}") from exc
    except yaml.YAMLError as exc:
        raise MissionRuntimeError(f"Invalid YAML in mission template: {template_path}") from exc

    if not isinstance(raw, dict):
        raise MissionRuntimeError("Invalid mission template: root must be a mapping")

    mission_raw = raw.get("mission")
    if not isinstance(mission_raw, dict):
        raise MissionRuntimeError("Invalid mission template: missing 'mission' section")

    mission = MissionMeta(
        key=_as_string(mission_raw.get("key"), field_name="mission.key"),
        name=str(mission_raw.get("name") or mission_raw.get("key") or ""),
        version=str(mission_raw.get("version") or "0.0.0"),
    )

    steps_raw = raw.get("steps")
    if not isinstance(steps_raw, list) or not steps_raw:
        raise MissionRuntimeError("Invalid mission template: 'steps' must be a non-empty list")

    steps: list[MissionStep] = []
    for idx, step_raw in enumerate(steps_raw):
        if not isinstance(step_raw, dict):
            raise MissionRuntimeError(f"Invalid mission template: step {idx} must be a mapping")
        step = MissionStep(
            id=_as_string(step_raw.get("id"), field_name=f"steps[{idx}].id"),
            title=str(step_raw.get("title") or ""),
            description=str(step_raw.get("description") or ""),
            prompt_template=(
                str(step_raw.get("prompt_template"))
                if step_raw.get("prompt_template") is not None
                else None
            ),
            depends_on=_as_string_list(step_raw.get("depends_on"), field_name=f"steps[{idx}].depends_on"),
            requires_inputs=_as_string_list(step_raw.get("requires_inputs"), field_name=f"steps[{idx}].requires_inputs"),
        )
        steps.append(step)

    return MissionTemplate(mission=mission, steps=steps)
