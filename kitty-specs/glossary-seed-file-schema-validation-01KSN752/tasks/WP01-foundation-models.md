---
work_package_id: WP01
title: Foundation — Pydantic Models and Error Types
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-015
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-glossary-seed-file-schema-validation-01KSN752
base_commit: efec054539979268c404cee54726d746657776c4
created_at: '2026-05-27T17:42:27.293034+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
agent: "claude:opus:implementer-ivan:reviewer"
shell_pid: "66942"
history:
- at: '2026-05-27T17:32:55+00:00'
  event: created
  agent: claude
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/glossary/
execution_mode: code_change
owned_files:
- src/specify_cli/glossary/seed_schema.py
- src/specify_cli/glossary/exceptions.py
- .kittify/glossaries/spec_kitty_core.yaml
- tests/specify_cli/glossary/test_seed_schema.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load implementer-ivan
```

This sets your identity, governance scope, boundaries, and initialization declaration for this work package.

## Objective

Create the foundational Pydantic validation models and error types that all downstream WPs depend on. Fix the known bad data in the glossary seed file.

## Context

A non-normalized `surface` value (`Sonar quality gate`) in `.kittify/glossaries/spec_kitty_core.yaml` causes `load_seed_file()` to throw `ValueError: TermSurface must be normalized`. Dashboard handlers catch this silently and show zero glossary terms.

This WP creates the Pydantic model layer following the doctrine pattern (`src/doctrine/directives/models.py`) and the error types needed by the validation pipeline.

## Branch Strategy

- **Planning base branch**: `main`
- **Final merge target**: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`. Do not create branches manually.

## Detailed Guidance

### T001: Fix Bad Data

**Purpose**: Normalize the non-normalized surface value so existing tests and runtime can load the seed file.

**Steps**:
1. Open `.kittify/glossaries/spec_kitty_core.yaml`
2. Find the entry with `surface: Sonar quality gate`
3. Change it to `surface: sonar quality gate`
4. Verify no other non-normalized surfaces exist (grep for uppercase letters in surface values)

**Files**: `.kittify/glossaries/spec_kitty_core.yaml`

**Validation**:
- [ ] No surface values contain uppercase letters
- [ ] `spec-kitty glossary list` works without errors after the fix

### T002: Add SeedValidationError Dataclass

**Purpose**: A structured error record with file/term/field context for a single validation failure.

**Steps**:
1. Open `src/specify_cli/glossary/exceptions.py`
2. Add imports: `from dataclasses import dataclass` and `from pathlib import Path`
3. Add frozen dataclass after the existing exception classes:

```python
@dataclass(frozen=True)
class SeedValidationError:
    """A single validation error with location context."""
    file_path: Path
    term_index: int | None
    term_surface: str | None
    field: str | None
    message: str
```

**Files**: `src/specify_cli/glossary/exceptions.py`

### T003: Add SeedFileValidationError Exception

**Purpose**: Aggregated validation failure for a seed file, containing all individual errors.

**Steps**:
1. In `src/specify_cli/glossary/exceptions.py`, add after `SeedValidationError`:

```python
class SeedFileValidationError(GlossaryError):
    """Aggregated validation failure for a glossary seed file."""

    def __init__(self, file_path: Path, errors: list[SeedValidationError]):
        self.file_path = file_path
        self.errors = errors
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        lines = [f"{len(self.errors)} validation error(s) in {self.file_path}:"]
        for err in self.errors:
            loc_parts: list[str] = []
            if err.term_index is not None:
                surface_label = f" '{err.term_surface}'" if err.term_surface else ""
                loc_parts.append(f"term[{err.term_index}]{surface_label}")
            if err.field:
                loc_parts.append(err.field)
            loc = " → ".join(loc_parts) if loc_parts else "file"
            lines.append(f"  - {loc}: {err.message}")
        return "\n".join(lines)
```

**Files**: `src/specify_cli/glossary/exceptions.py`

**Validation**:
- [ ] `SeedFileValidationError` extends `GlossaryError`
- [ ] `str(error)` produces multi-line output with file path, term index, surface, field, and message
- [ ] `error.errors` list is accessible

### T004: Create GlossarySeedTerm Pydantic Model

**Purpose**: Pydantic model for a single glossary term entry with all domain invariants.

**Steps**:
1. Create new file `src/specify_cli/glossary/seed_schema.py`
2. Follow the doctrine pattern from `src/doctrine/directives/models.py`:
   - Use `ConfigDict(frozen=True, extra="forbid")`
   - Use `@field_validator` for domain invariants

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class GlossarySeedTerm(BaseModel):
    """Pydantic model for a single glossary seed file term entry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    surface: str
    definition: str
    confidence: float = 1.0
    status: Literal["active", "draft", "deprecated"] = "draft"

    @field_validator("surface")
    @classmethod
    def surface_must_be_normalized(cls, v: str) -> str:
        if not v:
            raise ValueError("surface must not be empty")
        if v != v.lower().strip():
            raise ValueError(
                f"surface must be normalized (lowercase, trimmed): "
                f"got {v!r}, expected {v.lower().strip()!r}"
            )
        return v

    @field_validator("definition")
    @classmethod
    def definition_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("definition must not be empty")
        return v

    @field_validator("confidence")
    @classmethod
    def confidence_in_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be 0.0..1.0, got {v}")
        return v
```

**Files**: `src/specify_cli/glossary/seed_schema.py`

### T005: Create GlossarySeedFile Pydantic Model

**Purpose**: Aggregate root Pydantic model for the entire seed file.

**Steps**:
1. In `src/specify_cli/glossary/seed_schema.py`, add:

```python
class GlossarySeedFile(BaseModel):
    """Pydantic model for a glossary seed file (aggregate root)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    terms: list[GlossarySeedTerm]
```

2. Add `__all__` export list:
```python
__all__ = ["GlossarySeedFile", "GlossarySeedTerm"]
```

**Files**: `src/specify_cli/glossary/seed_schema.py`

### T006: Write Unit Tests

**Purpose**: Comprehensive test coverage for the Pydantic models and error types.

**Steps**:
1. Create `tests/specify_cli/glossary/test_seed_schema.py`
2. Test cases for `GlossarySeedTerm`:
   - Valid term with all fields
   - Valid term with optional fields omitted (defaults applied)
   - Surface not normalized → `ValidationError` with descriptive message
   - Empty surface → `ValidationError`
   - Empty definition → `ValidationError`
   - Confidence below 0.0 → `ValidationError`
   - Confidence above 1.0 → `ValidationError`
   - Invalid status value → `ValidationError`
   - Unknown field → `ValidationError` (extra="forbid")
3. Test cases for `GlossarySeedFile`:
   - Valid file with terms list
   - Empty terms list (allowed)
   - Missing terms key → `ValidationError`
   - Unknown field at root → `ValidationError`
   - Multiple invalid terms → all errors collected
4. Test cases for `SeedValidationError` and `SeedFileValidationError`:
   - Error formatting with term index, surface, field, message
   - Multi-error formatting
   - `SeedFileValidationError` extends `GlossaryError`

**Files**: `tests/specify_cli/glossary/test_seed_schema.py`

**Validation**:
- [ ] All Pydantic field validators are tested (surface normalization, definition non-empty, confidence range, status enum)
- [ ] `extra="forbid"` is tested at both term and file level
- [ ] Error message formatting is tested
- [ ] mypy --strict passes on both source and test files

## Definition of Done

- [ ] `.kittify/glossaries/spec_kitty_core.yaml` has no non-normalized surface values
- [ ] `SeedValidationError` and `SeedFileValidationError` exist in `exceptions.py`
- [ ] `GlossarySeedTerm` and `GlossarySeedFile` Pydantic models exist in `seed_schema.py`
- [ ] All field validators enforce: surface normalization, non-empty definition, confidence 0.0..1.0, status enum
- [ ] `extra="forbid"` rejects unknown fields
- [ ] Unit tests cover all invariants
- [ ] mypy --strict passes
- [ ] pytest passes

## Risks

- Existing seed files may have fields beyond `surface`, `definition`, `confidence`, `status`. Audit `.kittify/glossaries/` before implementing `extra="forbid"`.

## Reviewer Guidance

- Verify Pydantic models match the doctrine pattern in `src/doctrine/directives/models.py`
- Check error messages are actionable: each should name the field and explain what's wrong
- Confirm `extra="forbid"` is tested
- Verify the bad data fix doesn't introduce other issues

## Activity Log

- 2026-05-27T17:42:27Z – claude:opus:implementer-ivan:implementer – shell_pid=63810 – Assigned agent via action command
- 2026-05-27T17:48:36Z – claude:opus:implementer-ivan:implementer – shell_pid=63810 – Ready for review: foundation Pydantic models, error types, bad data fix, 30 passing tests
- 2026-05-27T17:49:27Z – claude:opus:implementer-ivan:reviewer – shell_pid=66942 – Started review via action command
