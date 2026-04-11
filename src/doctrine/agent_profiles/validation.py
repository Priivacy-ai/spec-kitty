"""YAML schema validation utilities for agent profiles."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonschema
from importlib.resources import files
from ruamel.yaml import YAML


@lru_cache(maxsize=1)
def _load_agent_profile_schema() -> dict[str, Any]:
    """Load the agent-profile JSON schema (cached).

    Returns:
        Schema dict loaded from YAML file
    """
    try:
        # Try package resources first
        resource = files("doctrine.schemas")
        if hasattr(resource, "joinpath"):
            schema_path = Path(str(resource.joinpath("agent-profile.schema.yaml")))
        else:
            schema_path = Path(str(resource)) / "agent-profile.schema.yaml"
    except (ModuleNotFoundError, TypeError):
        # Fallback to relative path
        schema_path = Path(__file__).parent.parent / "schemas" / "agent-profile.schema.yaml"

    yaml = YAML(typ="safe")
    with schema_path.open() as f:
        schema_data: dict[str, Any] = yaml.load(f)

    return schema_data


def validate_agent_profile_yaml(data: dict[str, Any]) -> list[str]:
    """Validate a dict against the agent-profile YAML schema.

    Args:
        data: Dictionary loaded from agent profile YAML file

    Returns:
        List of validation error messages (empty if valid)
    """
    schema = _load_agent_profile_schema()
    validator = jsonschema.Draft7Validator(schema)

    errors = []
    for error in validator.iter_errors(data):
        # Build a human-readable error message
        field_path = ".".join(str(p) for p in error.path) if error.path else "root"
        errors.append(f"{field_path}: {error.message}")

    return errors


def is_agent_profile_file(file_path: Path) -> bool:
    """Check if a file is an agent profile YAML file.

    Args:
        file_path: Path to check

    Returns:
        True if file has .agent.yaml extension
    """
    return file_path.suffix == ".yaml" and file_path.stem.endswith(".agent")
