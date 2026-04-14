"""YAML schema validation utilities for tactics."""

from typing import Any

import jsonschema

from doctrine.shared.errors import reject_inline_refs
from doctrine.shared.schema_utils import SchemaUtilities


def reject_tactic_inline_refs(data: dict[str, Any], *, file_path: str) -> None:
    """Raise ``InlineReferenceRejectedError`` if the tactic YAML carries a
    forbidden inline reference field."""
    reject_inline_refs(data, file_path=file_path, artifact_kind="tactic")


def validate_tactic(data: dict[str, Any]) -> list[str]:
    """Validate a dict against the tactic YAML schema.

    Args:
        data: Dictionary loaded from tactic YAML file.

    Returns:
        List of validation error messages (empty if valid).
    """
    schema = SchemaUtilities.load_schema("tactic")
    validator = jsonschema.Draft202012Validator(schema)

    errors: list[str] = []
    for error in validator.iter_errors(data):
        field_path = ".".join(str(p) for p in error.path) if error.path else "root"
        errors.append(f"{field_path}: {error.message}")

    return errors
