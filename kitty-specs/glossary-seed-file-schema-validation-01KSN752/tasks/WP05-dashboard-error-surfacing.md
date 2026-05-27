---
work_package_id: WP05
title: Dashboard Error Surfacing
dependencies:
- WP03
requirement_refs:
- FR-014
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-glossary-seed-file-schema-validation-01KSN752
base_commit: efec054539979268c404cee54726d746657776c4
created_at: '2026-05-27T18:01:44.354666+00:00'
subtasks:
- T020
- T021
- T022
- T023
- T024
agent: "claude:opus:implementer-ivan:implementer"
shell_pid: "72713"
history:
- at: '2026-05-27T17:32:55+00:00'
  event: created
  agent: claude
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/dashboard/
execution_mode: code_change
owned_files:
- src/specify_cli/dashboard/handlers/glossary.py
- src/specify_cli/dashboard/api_types.py
- tests/specify_cli/dashboard/test_glossary_handler.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile:

```
/ad-hoc-profile-load implementer-ivan
```

## Objective

Replace silent empty-data responses in dashboard glossary handlers with structured validation error reporting. When a seed file is invalid, the dashboard should show operators what's wrong instead of misleading zero-terms data.

## Context

In `src/specify_cli/dashboard/handlers/glossary.py`:
- `_collect_all_senses()` iterates all `GlossaryScope` values, calls `load_seed_file()` for each, catches `Exception` broadly, and returns empty list on any error
- `handle_glossary_health()` calls `_collect_all_senses()`, catches `Exception`, returns response with `total_terms: 0`
- `handle_glossary_terms()` calls `_collect_all_senses()`, catches `Exception`, returns empty array `[]`

After WP03, `load_seed_file()` raises `SeedFileValidationError` (subclass of `GlossaryError` → `Exception`). The dashboard needs to catch this specifically and surface the error details.

See `kitty-specs/glossary-seed-file-schema-validation-01KSN752/contracts/validate-command.md` for the dashboard API contract changes.

## Branch Strategy

- **Planning base branch**: `main`
- **Final merge target**: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`.

## Detailed Guidance

### T020: Add validation_errors to GlossaryHealthResponse

**Purpose**: Extend the health response TypedDict with an optional validation errors field.

**Steps**:
1. Open `src/specify_cli/dashboard/api_types.py`
2. Find `GlossaryHealthResponse` TypedDict
3. Add field:

```python
class GlossaryHealthResponse(TypedDict):
    total_terms: int
    active_count: int
    draft_count: int
    deprecated_count: int
    high_severity_drift_count: int
    orphaned_term_count: int
    entity_pages_generated: bool
    entity_pages_path: str | None
    last_conflict_at: str | None  # or datetime | None
    validation_errors: list[dict[str, Any]] | None  # NEW
```

**Files**: `src/specify_cli/dashboard/api_types.py`

**Note**: `validation_errors` is `None` when no errors exist (omitted from JSON for backward compatibility with existing consumers).

### T021: Update handle_glossary_health

**Purpose**: Catch `SeedFileValidationError` specifically and include error details in the response.

**Steps**:
1. In `src/specify_cli/dashboard/handlers/glossary.py`, update `handle_glossary_health`:

```python
def handle_glossary_health(self) -> None:
    # ... existing setup ...
    try:
        # ... existing logic ...
        response: GlossaryHealthResponse = {
            # ... existing fields ...
            "validation_errors": None,  # No errors
        }
    except SeedFileValidationError as exc:
        logger.warning("glossary health: validation error in %s: %s", exc.file_path, exc)
        response = {
            "total_terms": 0,
            "active_count": 0,
            "draft_count": 0,
            "deprecated_count": 0,
            "high_severity_drift_count": 0,
            "orphaned_term_count": 0,
            "entity_pages_generated": False,
            "entity_pages_path": None,
            "last_conflict_at": None,
            "validation_errors": [
                {
                    "file": str(e.file_path),
                    "term_index": e.term_index,
                    "term_surface": e.term_surface,
                    "field": e.field,
                    "message": e.message,
                }
                for e in exc.errors
            ],
        }
    except Exception as exc:
        logger.exception("glossary health error: %s", exc)
        response = {
            # ... existing fallback with all zeros ...
            "validation_errors": None,
        }

    self.wfile.write(json.dumps(response).encode())
```

2. Add import:
```python
from specify_cli.glossary.exceptions import SeedFileValidationError
```

**Files**: `src/specify_cli/dashboard/handlers/glossary.py`

**Key**: `SeedFileValidationError` is caught BEFORE the broad `Exception` catch. This is the priority order: specific validation errors first, then generic fallback.

### T022: Update handle_glossary_terms

**Purpose**: Log validation errors instead of silently returning empty array.

**Steps**:
1. Update the `except` block in `handle_glossary_terms`:

```python
def handle_glossary_terms(self) -> None:
    # ... existing setup ...
    try:
        # ... existing logic to build records ...
    except SeedFileValidationError as exc:
        logger.warning(
            "glossary terms: validation error in %s: %s",
            exc.file_path, exc
        )
        records = []
    except Exception as exc:
        logger.exception("glossary terms error: %s", exc)
        records = []

    self.wfile.write(json.dumps(records).encode())
```

**Files**: `src/specify_cli/dashboard/handlers/glossary.py`

**Note**: The response format for `/api/glossary-terms` stays as a bare array for backward compatibility. The dashboard HTML checks `/api/glossary-health` for `validation_errors` to display error state.

### T023: Update _collect_all_senses

**Purpose**: Let `SeedFileValidationError` propagate instead of being silently caught.

**Steps**:
1. Update `_collect_all_senses()`:

```python
def _collect_all_senses(repo_root: Path) -> list[Any]:
    """Load all TermSense objects from seed files across all scopes."""
    try:
        from specify_cli.glossary.scope import GlossaryScope, load_seed_file
        from specify_cli.glossary.exceptions import SeedFileValidationError

        senses = []
        for scope in GlossaryScope:
            try:
                senses.extend(load_seed_file(scope, repo_root))
            except SeedFileValidationError:
                raise  # Let validation errors propagate to handler
            except Exception as exc:
                logger.debug("Skipping scope %s: %s", scope.value, exc)
        return senses
    except SeedFileValidationError:
        raise  # Re-raise through outer try
    except Exception as exc:
        logger.debug("Could not load glossary senses: %s", exc)
        return []
```

**Files**: `src/specify_cli/dashboard/handlers/glossary.py`

**Key change**: `SeedFileValidationError` is explicitly re-raised instead of being caught by the broad `except Exception`. This lets the handler-level catch produce the structured error response.

### T024: Write Dashboard Handler Tests

**Purpose**: Test that validation errors are surfaced correctly in the dashboard API.

**Steps**:
1. Create or update `tests/specify_cli/dashboard/test_glossary_handler.py`
2. Test cases:
   - **Health endpoint with valid data**: `validation_errors` is `None`
   - **Health endpoint with invalid seed file**: `validation_errors` contains error dicts with file, term_index, term_surface, field, message
   - **Health endpoint with invalid data**: `total_terms` is 0 when validation fails
   - **Terms endpoint with invalid seed file**: Returns empty array `[]` (not crash), logs warning
   - **_collect_all_senses with mixed valid/invalid scopes**: `SeedFileValidationError` propagates for the invalid scope
   - **Backward compatibility**: Response structure still matches existing `GlossaryHealthResponse` for valid data (no `validation_errors` key when null, or null value accepted)

3. Use mock or `tmp_path` to create test scenarios. Mock `load_seed_file` to raise `SeedFileValidationError` for specific scopes.

**Files**: `tests/specify_cli/dashboard/test_glossary_handler.py`

## Definition of Done

- [ ] `GlossaryHealthResponse` includes `validation_errors` field
- [ ] `handle_glossary_health` catches `SeedFileValidationError` and includes error details
- [ ] `handle_glossary_terms` logs validation errors and returns empty array
- [ ] `_collect_all_senses` propagates `SeedFileValidationError` instead of catching it
- [ ] Dashboard no longer silently reports zero terms when seed file is invalid
- [ ] Tests cover valid, invalid, and mixed scenarios
- [ ] mypy --strict passes

## Risks

- Adding `validation_errors` to `GlossaryHealthResponse` may break consumers that strictly validate response shape. Mitigation: field is `None` when no errors (backward-compatible).
- Re-raising from `_collect_all_senses` means the first invalid scope stops all scope loading. This is intentional (aggregate boundary: fail-fast).

## Reviewer Guidance

- Verify `SeedFileValidationError` is caught BEFORE `Exception` in handler methods
- Check that `_collect_all_senses` re-raises `SeedFileValidationError` through both try layers
- Confirm the health endpoint includes error details (file, term, field, message)
- Verify `/api/glossary-terms` still returns bare array (not wrapped object) for backward compatibility

## Activity Log

- 2026-05-27T18:01:44Z – claude:opus:implementer-ivan:implementer – shell_pid=72713 – Assigned agent via action command
