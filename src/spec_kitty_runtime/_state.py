"""Persistence and template resolution helpers for the runtime shim."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import DiscoveryContext, PendingDecision, RuntimeState, Snapshot
from .schema import MissionRuntimeError, MissionStep, MissionTemplate, load_mission_template_file


def state_path(run_dir: Path) -> Path:
    return run_dir / "state.json"


def events_path(run_dir: Path) -> Path:
    return run_dir / "run.events.jsonl"


def append_event(run_dir: Path, event_type: str, payload: dict[str, object]) -> None:
    record = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    path = events_path(run_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True))
        handle.write("\n")


def _pending_to_json(pending: dict[str, PendingDecision]) -> dict[str, dict[str, object]]:
    return {
        decision_id: {
            "input_key": value.input_key,
            "question": value.question,
            "options": list(value.options),
            "step_id": value.step_id,
        }
        for decision_id, value in pending.items()
    }


def _pending_from_json(raw: Any) -> dict[str, PendingDecision]:
    if not isinstance(raw, dict):
        return {}
    pending: dict[str, PendingDecision] = {}
    for decision_id, value in raw.items():
        if not isinstance(decision_id, str) or not isinstance(value, dict):
            continue
        input_key = value.get("input_key")
        question = value.get("question")
        options = value.get("options")
        step_id = value.get("step_id")
        if not isinstance(input_key, str) or not isinstance(question, str) or not isinstance(step_id, str):
            continue
        if not isinstance(options, list) or any(not isinstance(opt, str) for opt in options):
            continue
        pending[decision_id] = PendingDecision(
            input_key=input_key,
            question=question,
            options=list(options),
            step_id=step_id,
        )
    return pending


def _step_dicts(steps: list[MissionStep]) -> list[dict[str, object]]:
    return [
        {
            "id": step.id,
            "title": step.title,
            "description": step.description,
            "prompt_template": step.prompt_template,
            "depends_on": list(step.depends_on),
            "requires_inputs": list(step.requires_inputs),
        }
        for step in steps
    ]


def create_initial_state(run_id: str, template: MissionTemplate) -> RuntimeState:
    return RuntimeState(
        run_id=run_id,
        mission_key=template.mission.key,
        steps=_step_dicts(template.steps),
    )


def write_state(run_dir: Path, state: RuntimeState) -> None:
    payload = {
        "run_id": state.run_id,
        "mission_key": state.mission_key,
        "steps": state.steps,
        "current_index": state.current_index,
        "issued_step_id": state.issued_step_id,
        "terminal": state.terminal,
        "pending_decisions": _pending_to_json(state.pending_decisions),
        "answered_inputs": state.answered_inputs,
    }
    path = state_path(run_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def read_state(run_dir: Path) -> RuntimeState:
    path = state_path(run_dir)
    if not path.exists():
        raise MissionRuntimeError(f"Run state not found: {path}")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MissionRuntimeError(f"Unable to read runtime state: {path}") from exc

    if not isinstance(raw, dict):
        raise MissionRuntimeError(f"Invalid runtime state format: {path}")

    run_id = raw.get("run_id")
    mission_key = raw.get("mission_key")
    steps = raw.get("steps")
    if not isinstance(run_id, str) or not isinstance(mission_key, str) or not isinstance(steps, list):
        raise MissionRuntimeError(f"Invalid runtime state fields: {path}")

    pending = _pending_from_json(raw.get("pending_decisions"))
    answered_raw = raw.get("answered_inputs")
    answered: dict[str, object] = answered_raw if isinstance(answered_raw, dict) else {}
    answered_clean = {key: value for key, value in answered.items() if isinstance(key, str) and isinstance(value, str)}

    issued_step_id = raw.get("issued_step_id")
    if issued_step_id is not None and not isinstance(issued_step_id, str):
        issued_step_id = None

    current_index = raw.get("current_index")
    if not isinstance(current_index, int):
        current_index = -1

    terminal = raw.get("terminal")
    if not isinstance(terminal, bool):
        terminal = False

    return RuntimeState(
        run_id=run_id,
        mission_key=mission_key,
        steps=list(steps),
        current_index=current_index,
        issued_step_id=issued_step_id,
        terminal=terminal,
        pending_decisions=pending,
        answered_inputs=answered_clean,
    )


def _candidate_templates_for_root(root: Path, mission_key: str) -> list[Path]:
    if root.is_file():
        return [root]

    if not root.exists() or not root.is_dir():
        return []

    candidates = [
        root / mission_key / "mission-runtime.yaml",
        root / mission_key / "mission.yaml",
        root / "missions" / mission_key / "mission-runtime.yaml",
        root / "missions" / mission_key / "mission.yaml",
        root / "mission-runtime.yaml",
        root / "mission.yaml",
    ]
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _split_env_paths(env_value: str) -> list[Path]:
    if not env_value.strip():
        return []
    return [Path(chunk) for chunk in env_value.split(os.pathsep) if chunk.strip()]


def resolve_template(template_key: str, context: DiscoveryContext) -> Path:
    explicit = [Path(template_key)] if template_key else []
    env_paths = _split_env_paths(os.environ.get(context.env_var_name, ""))

    roots: list[Path] = [
        *explicit,
        *context.explicit_paths,
        *env_paths,
        context.project_dir / ".kittify" / "overrides" / "missions",
        context.project_dir / ".kittify" / "missions",
        context.user_home / ".kittify" / "missions",
        *context.builtin_roots,
    ]

    for root in roots:
        for candidate in _candidate_templates_for_root(root, template_key):
            if not candidate.exists() or not candidate.is_file():
                continue
            try:
                template = load_mission_template_file(candidate)
            except MissionRuntimeError:
                continue
            if template.mission.key == template_key:
                return candidate.resolve()

    # Last chance: explicit file path (may not match mission key if caller already resolved)
    explicit_path = Path(template_key)
    if explicit_path.exists() and explicit_path.is_file():
        return explicit_path.resolve()

    raise MissionRuntimeError(f"Mission template not found for key '{template_key}'")


def read_template(path: Path) -> MissionTemplate:
    return load_mission_template_file(path)


def read_snapshot(run_dir: Path) -> Snapshot:
    state = read_state(run_dir)
    return Snapshot(
        run_id=state.run_id,
        mission_key=state.mission_key,
        issued_step_id=state.issued_step_id,
        pending_decisions=dict(state.pending_decisions),
        current_index=state.current_index,
        terminal=state.terminal,
    )
