---
work_package_id: WP03
title: Runtime Integration — load_seed_file and save_seed_file
dependencies:
- WP02
requirement_refs:
- FR-012
- FR-013
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-glossary-seed-file-schema-validation-01KSN752
base_commit: efec054539979268c404cee54726d746657776c4
created_at: '2026-05-27T17:55:32.261326+00:00'
subtasks:
- T011
- T012
- T013
- T014
- T015
agent: "claude:opus:implementer-ivan:implementer"
shell_pid: "69207"
history:
- at: '2026-05-27T17:32:55+00:00'
  event: created
  agent: claude
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/glossary/
execution_mode: code_change
owned_files:
- src/specify_cli/glossary/scope.py
- tests/specify_cli/glossary/test_scope.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load implementer-ivan
```

## Objective

Wire the Pydantic validation into the existing `load_seed_file()` and `save_seed_file()` functions so all runtime load/save paths enforce the glossary seed file schema. This is the core bug fix — after this WP, the silent zero-terms dashboard failure cannot occur.

## Context

Currently in `src/specify_cli/glossary/scope.py`:
- `validate_seed_file(data)` checks only structure (terms key, surface/definition presence)
- `load_seed_file()` calls `validate_seed_file(data)`, then constructs `TermSurface(term_data["surface"])` which raises `ValueError` on non-normalized surfaces
- `save_seed_file()` writes directly without validation

After this WP:
- `validate_seed_file()` delegates to `validate_seed_file_data()` for full Pydantic validation
- `load_seed_file()` validates first, then constructs domain objects (guaranteed valid)
- `save_seed_file()` validates the serialized form before writing

## Branch Strategy

- **Planning base branch**: `main`
- **Final merge target**: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`.

## Detailed Guidance

### T011: Update validate_seed_file() to Delegate

**Purpose**: Replace minimal structural checks with full Pydantic validation.

**Steps**:
1. In `src/specify_cli/glossary/scope.py`, update `validate_seed_file()`:

```python
def validate_seed_file(data: dict[str, Any], file_path: Path | None = None) -> None:
    """Validate seed file schema using Pydantic models.

    Raises SeedFileValidationError on invalid data.
    For backward compatibility, also catches and re-raises as ValueError
    when file_path is not provided (legacy call sites).
    """
    from .seed_validation import validate_seed_file_data

    effective_path = file_path or Path("<unknown>")
    validate_seed_file_data(data, effective_path)
```

**Important**: The existing function signature takes only `data: dict[str, Any]`. Adding `file_path` as optional preserves backward compatibility while enabling richer error context.

**Files**: `src/specify_cli/glossary/scope.py`

### T012: Update load_seed_file()

**Purpose**: Use Pydantic validation before constructing `TermSurface`/`TermSense` objects.

**Steps**:
1. In `src/specify_cli/glossary/scope.py`, update `load_seed_file()`:
   - Replace `validate_seed_file(data)` with `validate_seed_file_data(data, seed_path)`
   - The validated `GlossarySeedFile` return value confirms all terms are valid
   - `TermSurface(term_data["surface"])` is now guaranteed to succeed (surface already validated as normalized)

```python
def load_seed_file(scope: GlossaryScope, repo_root: Path) -> list[TermSense]:
    seed_path = repo_root / ".kittify" / "glossaries" / f"{scope.value}.yaml"

    if not seed_path.exists():
        return []

    yaml = YAML()
    yaml.preserve_quotes = True
    data = yaml.load(seed_path)

    # Full Pydantic validation — raises SeedFileValidationError on failure
    from .seed_validation import validate_seed_file_data
    validate_seed_file_data(data, seed_path)

    senses = []
    for term_data in data.get("terms") or []:
        sense = TermSense(
            surface=TermSurface(term_data["surface"]),
            scope=scope.value,
            definition=term_data["definition"],
            provenance=Provenance(
                actor_id="system:seed_file",
                timestamp=datetime.now(),
                source="seed_file",
            ),
            confidence=term_data.get("confidence", 1.0),
            status=_parse_sense_status(term_data.get("status")),
        )
        senses.append(sense)

    return senses
```

**Files**: `src/specify_cli/glossary/scope.py`

### T013: Update save_seed_file()

**Purpose**: Validate the serialized term data before writing to disk.

**Steps**:
1. In `src/specify_cli/glossary/scope.py`, at the start of `save_seed_file()`, add validation:

```python
def save_seed_file(
    scope: GlossaryScope,
    repo_root: Path,
    terms: list[TermSense],
) -> None:
    seed_path = repo_root / ".kittify" / "glossaries" / f"{scope.value}.yaml"
    seed_path.parent.mkdir(parents=True, exist_ok=True)

    # Validate the data that will be written
    from .seed_validation import validate_seed_file_data
    validation_data = {
        "terms": [
            {
                "surface": t.surface.surface_text,
                "definition": t.definition,
                "confidence": t.confidence,
                "status": t.status.value,
            }
            for t in terms
        ]
    }
    validate_seed_file_data(validation_data, seed_path)

    # ... rest of existing write logic unchanged ...
```

**Files**: `src/specify_cli/glossary/scope.py`

**Edge case**: `save_seed_file()` receives already-validated `TermSense` objects, so this is defense-in-depth. The validation catches edge cases like rounding in confidence serialization.

### T014: Update Imports

**Purpose**: Add necessary imports for the new modules.

**Steps**:
1. In `src/specify_cli/glossary/scope.py`, the imports from `.seed_validation` are done inline (inside functions) to avoid circular imports. Verify no circular dependency exists.
2. If no circular dependency, move to top-level imports for clarity.
3. Update `src/specify_cli/glossary/__init__.py` to export new public names:
   - `SeedValidationError`, `SeedFileValidationError` from `.exceptions`
   - `GlossarySeedFile`, `GlossarySeedTerm` from `.seed_schema`
   - `validate_seed_file_data`, `validate_scope_filename` from `.seed_validation`

**Files**: `src/specify_cli/glossary/scope.py`, `src/specify_cli/glossary/__init__.py`

### T015: Update test_scope.py

**Purpose**: Update existing scope tests for the new validation behavior.

**Steps**:
1. Find or create `tests/specify_cli/glossary/test_scope.py`
2. Update tests that currently expect `ValueError` from `load_seed_file()` to expect `SeedFileValidationError` instead
3. Add test: `load_seed_file()` with non-normalized surface raises `SeedFileValidationError` (not `ValueError`)
4. Add test: `load_seed_file()` with valid data returns `TermSense` list as before
5. Add test: `save_seed_file()` with invalid term data raises `SeedFileValidationError`
6. Add test: `save_seed_file()` with valid data writes file as before
7. Ensure backward compatibility: code that catches `GlossaryError` still catches validation errors

**Files**: `tests/specify_cli/glossary/test_scope.py`

## Definition of Done

- [ ] `load_seed_file()` raises `SeedFileValidationError` (not `ValueError`) on invalid seed data
- [ ] `load_seed_file()` validates before constructing `TermSurface` objects
- [ ] `save_seed_file()` validates before writing to disk
- [ ] `validate_seed_file()` delegates to Pydantic validation
- [ ] Existing valid seed files continue to load correctly
- [ ] `__init__.py` exports new public names
- [ ] All tests pass, mypy --strict passes

## Risks

- Changing `ValueError` to `SeedFileValidationError` may break callers that catch `ValueError` specifically. Grep for `except ValueError` in glossary-related code. `SeedFileValidationError` extends `GlossaryError` which extends `Exception`, so broad `except Exception` catches still work.
- Circular import risk between `scope.py` → `seed_validation.py` → `seed_schema.py`. Use inline imports if needed.

## Reviewer Guidance

- Verify `load_seed_file()` validates BEFORE constructing `TermSurface` — the Pydantic check must happen first
- Check that `save_seed_file()` validation doesn't break the write path for valid data
- Confirm no callers of `load_seed_file()` catch `ValueError` specifically (should catch `GlossaryError` or `SeedFileValidationError`)
- Verify `__init__.py` exports are complete

## Activity Log

- 2026-05-27T17:55:32Z – claude:opus:implementer-ivan:implementer – shell_pid=69207 – Assigned agent via action command
