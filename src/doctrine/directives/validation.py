"""YAML schema validation utilities for directives."""

from typing import Any

import jsonschema

from doctrine.shared.errors import reject_inline_refs
from doctrine.shared.schema_utils import SchemaUtilities


def reject_directive_inline_refs(data: dict[str, Any], *, file_path: str) -> None:
    """Raise ``InlineReferenceRejectedError`` if ``data`` carries a forbidden
    inline reference field (``tactic_refs`` / ``paradigm_refs`` / ``applies_to``).

    Intended to be called after ``yaml.safe_load`` and BEFORE Pydantic model
    construction so the error carries the structured migration hint required
    by ``contracts/validator-rejection-error.schema.json``.
    """
    reject_inline_refs(data, file_path=file_path, artifact_kind="directive")


def validate_directive(data: dict[str, Any]) -> list[str]:
    """Validate a dict against the directive YAML schema.

    Args:
        data: Dictionary loaded from directive YAML file.

    Returns:
        List of validation error messages (empty if valid).
    """
    schema = SchemaUtilities.load_schema("directive")
    validator = jsonschema.Draft202012Validator(schema)

    errors: list[str] = []
    for error in validator.iter_errors(data):
        field_path = ".".join(str(p) for p in error.path) if error.path else "root"
        errors.append(f"{field_path}: {error.message}")

    return errors
