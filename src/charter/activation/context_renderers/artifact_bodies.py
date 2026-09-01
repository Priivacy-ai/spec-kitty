"""Artifact-body formatting — pure transforms (WP04 T021, #2532).

Relocated verbatim from ``charter.activation.context`` (single-owner, no-net-growth for
that file). Every formatter here is a pure function over a generic doctrine
object (accessed via ``getattr`` so any of the real Pydantic models or a
test stub satisfies the shape) — no repository lookups, no I/O, no charter
selection/decision logic.
"""

from __future__ import annotations

import json
import re

__all__ = [
    "_format_full_artifact_payload_body",
    "_format_inline_agent_profile_body",
    "_format_inline_directive_body",
    "_format_inline_paradigm_body",
    "_format_inline_procedure_body",
    "_format_inline_step_contract_body",
    "_format_inline_styleguide_body",
    "_format_inline_tactic_body",
    "_format_inline_toolguide_body",
    "_format_profile_directive_code",
    "_jsonable_artifact_value",
]

# S1192: shared "Steps:" section header, referenced by every inline body
# formatter below that lists a doctrine artifact's ``steps`` sequence
# (tactic / procedure / mission-step-contract).
_STEPS_SECTION_HEADER = "    Steps:"


def _format_profile_directive_code(raw: object) -> str:
    """Normalise a directive-ref code to the canonical ``DIRECTIVE_NNN`` form.

    Profile YAML stores codes as bare numerals (``"010"``) or already in
    ``DIRECTIVE_NNN`` form. Operator-facing directive selectors also use the
    active pack's numeric slug (for example, ``"025-boy-scout-rule"``). The
    catalog lookup needs the canonical form in every case.
    """
    text = str(raw).strip()
    if re.match(r"^DIRECTIVE_\d+$", text):
        return text
    match = re.match(r"^(\d+)(?:[-_].*)?$", text)
    if match:
        return f"DIRECTIVE_{match.group(1).zfill(3)}"
    return text


def _jsonable_artifact_value(value: object) -> object:
    """Return a deterministic JSON-safe representation of a doctrine object."""

    if value is None or isinstance(value, str | int | float | bool):
        return value

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            dumped = model_dump(by_alias=True, mode="json", exclude_none=True)
        except TypeError:
            dumped = model_dump()
        return _jsonable_artifact_value(dumped)

    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str | int | float | bool):
        return enum_value

    if isinstance(value, dict):
        return {
            str(key): _jsonable_artifact_value(item)
            for key, item in value.items()
            if item is not None
        }

    if isinstance(value, set):
        normalized = [_jsonable_artifact_value(item) for item in value]
        return sorted(
            normalized,
            key=lambda item: json.dumps(item, sort_keys=True),
        )

    if isinstance(value, list | tuple):
        return [_jsonable_artifact_value(item) for item in value]

    attrs = getattr(value, "__dict__", None)
    if isinstance(attrs, dict):
        return {
            key: _jsonable_artifact_value(item)
            for key, item in attrs.items()
            if not key.startswith("_") and item is not None
        }

    return str(value)


def _format_full_artifact_payload_body(artifact: object) -> list[str]:
    """Render the full doctrine payload for fetch-selector recovery."""

    payload = _jsonable_artifact_value(artifact)
    if not isinstance(payload, dict) or not payload:
        return []

    json_lines = json.dumps(payload, indent=2, sort_keys=True).splitlines()
    return ["    Full artifact:", *(f"      {line}" for line in json_lines)]


def _format_inline_directive_body(directive: object) -> list[str]:
    """Render the verbatim body of a directive as indented lines."""
    body_lines: list[str] = []
    intent = getattr(directive, "intent", None)
    if isinstance(intent, str) and intent.strip():
        body_lines.append(f"    Intent: {intent.strip()}")
    scope = getattr(directive, "scope", None)
    if isinstance(scope, str) and scope.strip():
        body_lines.append(f"    Scope: {scope.strip()}")
    for label, attr in (
        ("Procedures", "procedures"),
        ("Integrity rules", "integrity_rules"),
        ("Validation criteria", "validation_criteria"),
    ):
        items = getattr(directive, attr, None)
        if isinstance(items, list) and items:
            body_lines.append(f"    {label}:")
            for item in items:
                body_lines.append(f"      - {item}")
    return body_lines


def _format_inline_styleguide_body(styleguide: object) -> list[str]:
    """Render the verbatim body of a styleguide as indented lines."""
    body_lines: list[str] = []
    title = getattr(styleguide, "title", None)
    if isinstance(title, str) and title.strip():
        body_lines.append(f"    Title: {title.strip()}")
    scope = getattr(styleguide, "scope", None)
    if scope is not None:
        scope_str = scope.value if hasattr(scope, "value") else str(scope)
        if scope_str:
            body_lines.append(f"    Scope: {scope_str}")
    principles = getattr(styleguide, "principles", None)
    if isinstance(principles, list) and principles:
        body_lines.append("    Principles:")
        for principle in principles:
            body_lines.append(f"      - {principle}")
    return body_lines


def _format_inline_paradigm_body(paradigm: object) -> list[str]:
    """Render the verbatim body of a paradigm as indented lines."""
    body_lines: list[str] = []
    name = getattr(paradigm, "name", None)
    if isinstance(name, str) and name.strip():
        body_lines.append(f"    Name: {name.strip()}")
    summary = getattr(paradigm, "summary", None)
    if isinstance(summary, str) and summary.strip():
        body_lines.append(f"    Summary: {summary.strip()}")
    return body_lines


def _format_inline_tactic_body(tactic: object) -> list[str]:
    """Render the verbatim body of a tactic as indented lines."""
    body_lines: list[str] = []
    name = getattr(tactic, "name", None)
    if isinstance(name, str) and name.strip():
        body_lines.append(f"    Name: {name.strip()}")
    purpose = getattr(tactic, "purpose", None)
    if isinstance(purpose, str) and purpose.strip():
        body_lines.append(f"    Purpose: {purpose.strip()}")
    steps = getattr(tactic, "steps", None)
    if isinstance(steps, list) and steps:
        body_lines.append(_STEPS_SECTION_HEADER)
        for step in steps:
            step_title = getattr(step, "title", str(step))
            body_lines.append(f"      - {step_title}")
    return body_lines


def _format_inline_toolguide_body(toolguide: object) -> list[str]:
    """Render the verbatim body of a toolguide as indented lines."""
    body_lines: list[str] = []
    title = getattr(toolguide, "title", None)
    if isinstance(title, str) and title.strip():
        body_lines.append(f"    Title: {title.strip()}")
    tool = getattr(toolguide, "tool", None)
    if isinstance(tool, str) and tool.strip():
        body_lines.append(f"    Tool: {tool.strip()}")
    summary = getattr(toolguide, "summary", None)
    if isinstance(summary, str) and summary.strip():
        body_lines.append(f"    Summary: {summary.strip()}")
    return body_lines


def _format_inline_procedure_body(procedure: object) -> list[str]:
    """Render the verbatim body of a procedure as indented lines."""
    body_lines: list[str] = []
    name = getattr(procedure, "name", None)
    if isinstance(name, str) and name.strip():
        body_lines.append(f"    Name: {name.strip()}")
    purpose = getattr(procedure, "purpose", None)
    if isinstance(purpose, str) and purpose.strip():
        body_lines.append(f"    Purpose: {purpose.strip()}")
    entry = getattr(procedure, "entry_condition", None)
    if isinstance(entry, str) and entry.strip():
        body_lines.append(f"    Entry condition: {entry.strip()}")
    exit_ = getattr(procedure, "exit_condition", None)
    if isinstance(exit_, str) and exit_.strip():
        body_lines.append(f"    Exit condition: {exit_.strip()}")
    steps = getattr(procedure, "steps", None)
    if isinstance(steps, list) and steps:
        body_lines.append(_STEPS_SECTION_HEADER)
        for step in steps:
            step_title = getattr(step, "title", str(step))
            body_lines.append(f"      - {step_title}")
    return body_lines


def _format_inline_agent_profile_body(profile_obj: object) -> list[str]:
    """Render the verbatim body of an agent profile as indented lines."""
    body_lines: list[str] = []
    name = getattr(profile_obj, "name", None)
    if isinstance(name, str) and name.strip():
        body_lines.append(f"    Name: {name.strip()}")
    purpose = getattr(profile_obj, "purpose", None)
    if isinstance(purpose, str) and purpose.strip():
        body_lines.append(f"    Purpose: {purpose.strip()}")
    roles = getattr(profile_obj, "roles", None)
    if isinstance(roles, list) and roles:
        role_names = [
            role.value if hasattr(role, "value") else str(role) for role in roles
        ]
        body_lines.append(f"    Roles: {', '.join(role_names)}")
    return body_lines


def _format_inline_step_contract_body(contract: object) -> list[str]:
    """Render the verbatim body of a mission step contract as indented lines."""
    body_lines: list[str] = []
    action = getattr(contract, "action", None)
    if isinstance(action, str) and action.strip():
        body_lines.append(f"    Action: {action.strip()}")
    mission = getattr(contract, "mission", None)
    if isinstance(mission, str) and mission.strip():
        body_lines.append(f"    Mission: {mission.strip()}")
    steps = getattr(contract, "steps", None)
    if isinstance(steps, list) and steps:
        body_lines.append(_STEPS_SECTION_HEADER)
        for step in steps:
            step_id = getattr(step, "id", None)
            step_desc = getattr(step, "description", "")
            if step_id:
                body_lines.append(f"      - {step_id}: {step_desc}")
            else:
                body_lines.append(f"      - {step_desc}")
    return body_lines
