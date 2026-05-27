---
work_package_id: WP02
title: Validation Orchestration
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-007
- FR-008
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
agent: claude
history:
- at: '2026-05-27T17:32:55+00:00'
  event: created
  agent: claude
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/glossary/
execution_mode: code_change
owned_files:
- src/specify_cli/glossary/seed_validation.py
- tests/specify_cli/glossary/test_seed_validation.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load implementer-ivan
```

## Objective

Build the validation orchestration layer that translates Pydantic errors into structured `SeedValidationError` lists and validates scope filenames. This module is the single entry point for all validation call sites (load, save, CLI, CI).

## Context

WP01 created the Pydantic models (`GlossarySeedFile`, `GlossarySeedTerm`) and error types (`SeedValidationError`, `SeedFileValidationError`). This WP builds the orchestration function that:
1. Calls `GlossarySeedFile.model_validate(data)`
2. Catches `ValidationError`
3. Translates Pydantic's `loc` tuples into human-readable `SeedValidationError` records
4. Raises `SeedFileValidationError` with all errors collected

## Branch Strategy

- **Planning base branch**: `main`
- **Final merge target**: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`.

## Detailed Guidance

### T007: Create validate_seed_file_data()

**Purpose**: The single validation entry point for all call sites.

**Steps**:
1. Create `src/specify_cli/glossary/seed_validation.py`
2. Implement:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .exceptions import SeedFileValidationError, SeedValidationError
from .seed_schema import GlossarySeedFile
from .scope import GlossaryScope


def validate_seed_file_data(
    data: Any,
    file_path: Path,
) -> GlossarySeedFile:
    """Validate parsed YAML data against the glossary seed file schema.

    Returns the validated GlossarySeedFile on success.
    Raises SeedFileValidationError on failure with all errors collected.
    """
    try:
        return GlossarySeedFile.model_validate(data)
    except ValidationError as exc:
        errors = _translate_pydantic_errors(exc, data, file_path)
        raise SeedFileValidationError(file_path, errors) from exc
```

**Files**: `src/specify_cli/glossary/seed_validation.py`

### T008: Add validate_scope_filename()

**Purpose**: Validate that a seed filename corresponds to a known `GlossaryScope`.

**Steps**:
1. In `src/specify_cli/glossary/seed_validation.py`, add:

```python
VALID_SCOPE_FILENAMES: dict[str, GlossaryScope] = {
    f"{scope.value}.yaml": scope for scope in GlossaryScope
}


def validate_scope_filename(file_path: Path) -> GlossaryScope | None:
    """Return the GlossaryScope for a seed filename, or None if unknown.

    Only checks the filename stem against known scope values.
    Does not validate file contents.
    """
    return VALID_SCOPE_FILENAMES.get(file_path.name)
```

**Files**: `src/specify_cli/glossary/seed_validation.py`

### T009: Implement Pydantic Error Translation

**Purpose**: Convert Pydantic v2 `ValidationError.errors()` into `SeedValidationError` records with file/term/field context.

**Steps**:
1. In `src/specify_cli/glossary/seed_validation.py`, add:

```python
def _translate_pydantic_errors(
    exc: ValidationError,
    data: Any,
    file_path: Path,
) -> list[SeedValidationError]:
    """Translate Pydantic ValidationError entries into SeedValidationError records."""
    errors: list[SeedValidationError] = []
    for err in exc.errors():
        loc = err.get("loc", ())
        msg = err.get("msg", "validation error")

        term_index: int | None = None
        term_surface: str | None = None
        field_name: str | None = None

        # Parse loc tuple: ("terms", 2, "surface") → term_index=2, field="surface"
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
                except StopIteration:
                    pass
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
```

2. Add `__all__` export:
```python
__all__ = [
    "validate_seed_file_data",
    "validate_scope_filename",
    "VALID_SCOPE_FILENAMES",
]
```

**Files**: `src/specify_cli/glossary/seed_validation.py`

**Key detail**: Pydantic v2 `err.errors()` returns dicts like:
```python
{"type": "value_error", "loc": ("terms", 2, "surface"), "msg": "Value error, surface must be normalized..."}
```
The translation must handle:
- `("terms",)` — missing terms key entirely
- `("terms", 0, "surface")` — field-level error on specific term
- `("terms", 0)` — term-level error (e.g., extra field at term level)

### T010: Write Unit Tests

**Purpose**: Test validation orchestration, error translation, and scope filename validation.

**Steps**:
1. Create `tests/specify_cli/glossary/test_seed_validation.py`
2. Test `validate_seed_file_data()`:
   - Valid data returns `GlossarySeedFile` instance
   - Non-normalized surface raises `SeedFileValidationError` with correct term_index, term_surface, field
   - Multiple errors in one file are all collected
   - Missing `terms` key raises with file-level error
   - Non-mapping root (e.g., list) raises with clear error
   - Empty definition raises with correct field attribution
   - Invalid confidence raises with correct field
   - Invalid status raises with correct field
   - Unknown field at term level raises
3. Test `validate_scope_filename()`:
   - `mission_local.yaml` → `GlossaryScope.MISSION_LOCAL`
   - `spec_kitty_core.yaml` → `GlossaryScope.SPEC_KITTY_CORE`
   - `unknown.yaml` → `None`
   - `readme.md` → `None`
4. Test `_translate_pydantic_errors()`:
   - Verify loc tuple parsing handles all patterns
   - Verify term_surface extraction from input data
   - Verify field attribution for nested errors

**Files**: `tests/specify_cli/glossary/test_seed_validation.py`

## Definition of Done

- [ ] `validate_seed_file_data()` returns `GlossarySeedFile` on valid input
- [ ] `validate_seed_file_data()` raises `SeedFileValidationError` with all errors collected on invalid input
- [ ] Each `SeedValidationError` has file_path, term_index, term_surface (when available), field, and message
- [ ] `validate_scope_filename()` maps known filenames to `GlossaryScope` and returns `None` for unknown
- [ ] All tests pass, mypy --strict passes

## Risks

- Pydantic v2 error `loc` tuple format may vary by error type. Test with all validator types to ensure translation covers all patterns.

## Reviewer Guidance

- Verify error translation handles all Pydantic `loc` shapes (file-level, term-level, field-level)
- Check that term_surface is extracted from input data for context, not from the error itself
- Confirm `validate_seed_file_data` is a pure function with no side effects (no file I/O)
