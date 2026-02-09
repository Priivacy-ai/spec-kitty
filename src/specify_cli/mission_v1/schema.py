"""JSON Schema definition and validation for v1 mission YAML configs.

Provides:
- MISSION_V1_SCHEMA: JSON Schema dict for validating v1 mission structure
- MissionValidationError: Exception for schema validation failures
- is_v1_mission(config): Detect v1 vs v0 configs
- validate_mission_v1(config): Validate a config dict against the v1 schema
"""

from __future__ import annotations

from typing import Any

import jsonschema


class MissionValidationError(Exception):
    """Raised when a mission config fails v1 JSON Schema validation.

    Attributes:
        errors: List of validation error messages with field paths.
    """

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors: list[str] = errors or []


# --- Sub-schemas for reuse ---

_STATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["name"],
    "properties": {
        "name": {
            "type": "string",
            "description": "Unique state identifier",
        },
        "display_name": {
            "type": "string",
            "description": "Human-readable state label",
        },
        "on_enter": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Callbacks invoked when entering this state",
        },
        "on_exit": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Callbacks invoked when leaving this state",
        },
    },
    "additionalProperties": False,
}

_TRANSITION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["trigger", "dest"],
    "properties": {
        "trigger": {
            "type": "string",
            "description": "Event name that fires this transition",
        },
        "source": {
            "oneOf": [
                {"type": "string"},
                {"type": "array", "items": {"type": "string"}},
            ],
            "description": "Source state(s); may be a single name or list",
        },
        "dest": {
            "type": "string",
            "description": "Destination state",
        },
        "conditions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Guard functions that must ALL return True",
        },
        "unless": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Guard functions that must ALL return False",
        },
        "before": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Callbacks invoked before the transition",
        },
        "after": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Callbacks invoked after the transition",
        },
    },
    "additionalProperties": False,
}

_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["name", "type"],
    "properties": {
        "name": {
            "type": "string",
            "description": "Input parameter name",
        },
        "type": {
            "type": "string",
            "enum": ["string", "path", "url", "boolean", "integer"],
            "description": "Data type of this input",
        },
        "required": {
            "type": "boolean",
            "description": "Whether the input is mandatory",
        },
        "description": {
            "type": "string",
            "description": "Human-readable explanation of this input",
        },
    },
    "additionalProperties": False,
}

_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["name", "type"],
    "properties": {
        "name": {
            "type": "string",
            "description": "Output artifact name",
        },
        "type": {
            "type": "string",
            "enum": ["artifact", "report", "data"],
            "description": "Category of the output",
        },
        "path": {
            "type": "string",
            "description": "Relative path where the output is written",
        },
        "phase": {
            "type": "string",
            "description": "Mission phase that produces this output",
        },
        "description": {
            "type": "string",
            "description": "Human-readable explanation of this output",
        },
    },
    "additionalProperties": False,
}

_GUARD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["description", "check"],
    "properties": {
        "description": {
            "type": "string",
            "description": "Human-readable explanation of the guard",
        },
        "check": {
            "type": "string",
            "description": "Callable or expression to evaluate",
        },
    },
    "additionalProperties": False,
}


# --- Top-level v1 mission schema ---

MISSION_V1_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Spec Kitty Mission v1",
    "description": "Schema for v1 state-machine-based mission YAML configs.",
    "type": "object",
    "required": ["mission", "initial", "states", "transitions"],
    "properties": {
        "mission": {
            "type": "object",
            "required": ["name", "version", "description"],
            "properties": {
                "name": {"type": "string"},
                "version": {"type": "string"},
                "description": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "initial": {
            "type": "string",
            "description": "Name of the initial state",
        },
        "states": {
            "type": "array",
            "items": _STATE_SCHEMA,
            "minItems": 1,
            "description": "List of state definitions",
        },
        "transitions": {
            "type": "array",
            "items": _TRANSITION_SCHEMA,
            "minItems": 1,
            "description": "List of transition definitions",
        },
        "inputs": {
            "type": "array",
            "items": _INPUT_SCHEMA,
            "description": "Mission input parameters",
        },
        "outputs": {
            "type": "array",
            "items": _OUTPUT_SCHEMA,
            "description": "Mission output artifacts",
        },
        "guards": {
            "type": "object",
            "additionalProperties": _GUARD_SCHEMA,
            "description": "Named guard definitions keyed by guard name",
        },
    },
    # Allow v0 legacy keys (workflow, artifacts, paths, etc.) at top level
    "additionalProperties": True,
}


def is_v1_mission(config: dict[str, Any]) -> bool:
    """Detect whether a mission config dict is v1 format.

    A v1 mission has both ``states`` and ``transitions`` top-level keys.
    A v0 (phase-list) mission typically has ``workflow`` with ``phases`` instead.

    Args:
        config: Parsed mission YAML as a dict.

    Returns:
        True if the config looks like a v1 mission, False otherwise.
    """
    return "states" in config and "transitions" in config


def validate_mission_v1(config: dict[str, Any]) -> None:
    """Validate a mission config dict against the v1 JSON Schema.

    Raises:
        MissionValidationError: If the config fails schema validation.
            The exception's ``errors`` attribute contains per-field messages.
    """
    validator = jsonschema.Draft202012Validator(MISSION_V1_SCHEMA)
    raw_errors = sorted(validator.iter_errors(config), key=lambda e: list(e.path))

    if not raw_errors:
        return

    error_messages: list[str] = []
    for err in raw_errors:
        path = ".".join(str(p) for p in err.absolute_path) if err.absolute_path else "(root)"
        error_messages.append(f"{path}: {err.message}")

    raise MissionValidationError(
        f"Mission v1 validation failed with {len(error_messages)} error(s)",
        errors=error_messages,
    )


# ---------------------------------------------------------------------------
# v1 key stripping for v0 compatibility
# ---------------------------------------------------------------------------

#: Keys that only appear in v1 mission configs (state-machine DSL).
#: Stripping these allows a hybrid YAML to pass v0 Pydantic validation.
V1_ONLY_KEYS: frozenset[str] = frozenset({
    "states",
    "transitions",
    "initial",
    "guards",
    "inputs",
    "outputs",
    "mission",
})


def strip_v1_keys(config: dict[str, Any]) -> dict[str, Any]:
    """Remove v1-only keys from a config dict for v0 Pydantic validation.

    When a hybrid YAML contains both v1 keys (states, transitions, etc.)
    and v0 keys (workflow, artifacts, etc.), stripping the v1 keys allows
    the v0 ``MissionConfig.model_validate()`` to succeed without hitting
    ``extra="forbid"`` errors.

    Args:
        config: Raw mission config dict (not mutated).

    Returns:
        A new dict with v1-only keys removed.
    """
    return {k: v for k, v in config.items() if k not in V1_ONLY_KEYS}
