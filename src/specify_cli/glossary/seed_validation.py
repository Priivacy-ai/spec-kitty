"""Validation orchestration for glossary seed files.

Translates Pydantic ``ValidationError`` into structured
``SeedValidationError`` lists and validates scope filenames.

This module is the single entry point for all validation call sites
(load, save, CLI, CI).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .exceptions import SeedFileValidationError, SeedValidationError
from .scope import GlossaryScope
from .seed_schema import GlossarySeedFile

__all__ = [
    "VALID_SCOPE_FILENAMES",
    "validate_scope_filename",
    "validate_seed_file_data",
]

# ---------------------------------------------------------------------------
# Scope filename mapping
# ---------------------------------------------------------------------------

VALID_SCOPE_FILENAMES: dict[str, GlossaryScope] = {
    f"{scope.value}.yaml": scope for scope in GlossaryScope
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_seed_file_data(
    data: Any,
    file_path: Path,
) -> GlossarySeedFile:
    """Validate parsed YAML data against the glossary seed file schema.

    Returns the validated ``GlossarySeedFile`` on success.
    Raises ``SeedFileValidationError`` on failure with all errors collected.
    """
    try:
        return GlossarySeedFile.model_validate(data)
    except ValidationError as exc:
        errors = _translate_pydantic_errors(exc, data, file_path)
        raise SeedFileValidationError(file_path, errors) from exc


def validate_scope_filename(file_path: Path) -> GlossaryScope | None:
    """Return the ``GlossaryScope`` for a seed filename, or ``None`` if unknown.

    Only checks the filename against known scope values.
    Does not validate file contents.
    """
    return VALID_SCOPE_FILENAMES.get(file_path.name)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _translate_pydantic_errors(
    exc: ValidationError,
    data: Any,
    file_path: Path,
) -> list[SeedValidationError]:
    """Translate Pydantic ``ValidationError`` entries into ``SeedValidationError`` records."""
    errors: list[SeedValidationError] = []
    for err in exc.errors():
        loc = err.get("loc", ())
        msg = err.get("msg", "validation error")

        term_index: int | None = None
        term_surface: str | None = None
        field_name: str | None = None

        # Parse loc tuple: ("terms", 2, "surface") -> term_index=2, field="surface"
        loc_iter = iter(loc)
        for part in loc_iter:
            if part == "terms":
                # Next part should be the index
                try:
                    idx = next(loc_iter)
                    if isinstance(idx, int):
                        term_index = idx
                        # Try to extract surface from input data for context
                        if (
                            isinstance(data, dict)
                            and isinstance(data.get("terms"), list)
                            and 0 <= idx < len(data["terms"])
                            and isinstance(data["terms"][idx], dict)
                        ):
                            term_surface = data["terms"][idx].get("surface")
                        # Next part is the field
                        try:
                            field_part = next(loc_iter)
                            field_name = str(field_part)
                        except StopIteration:
                            pass
                    else:
                        # Non-integer after "terms" — treat as field name
                        field_name = str(idx)
                except StopIteration:
                    # loc was just ("terms",) — file-level error about terms field
                    field_name = "terms"
            elif isinstance(part, str):
                field_name = part

        errors.append(
            SeedValidationError(
                file_path=file_path,
                term_index=term_index,
                term_surface=str(term_surface) if term_surface else None,
                field=field_name,
                message=msg,
            )
        )
    return errors
