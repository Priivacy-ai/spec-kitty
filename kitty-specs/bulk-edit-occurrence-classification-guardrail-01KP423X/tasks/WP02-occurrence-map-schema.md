---
work_package_id: WP02
title: Occurrence Map Schema & Validation
dependencies: []
requirement_refs:
- FR-003
- FR-004
- FR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T003
- T004
- T005
agent: "claude:opus:reviewer:reviewer"
shell_pid: "59383"
history:
- date: '2026-04-13'
  author: claude
  action: created
authoritative_surface: src/specify_cli/bulk_edit/
execution_mode: code_change
owned_files:
- src/specify_cli/bulk_edit/__init__.py
- src/specify_cli/bulk_edit/occurrence_map.py
- tests/specify_cli/bulk_edit/__init__.py
- tests/specify_cli/bulk_edit/test_occurrence_map.py
tags: []
---

# WP02 — Occurrence Map Schema & Validation

## Objective

Create the `bulk_edit` package and implement the occurrence map YAML loading, structural validation, and admissibility checking. This module defines the schema for `occurrence_map.yaml` and provides functions to validate it.

## Context

- **Spec**: FR-003 (machine-readable artifact), FR-004 (occurrence categories), FR-005 (per-category actions)
- **Plan**: Integration Point — Occurrence Map Schema
- **Data model**: See `data-model.md` section 2 for full schema, validation rules, and admissibility criteria
- Follows the `ruamel.yaml` parsing pattern used elsewhere in the codebase
- The validation function will be imported by `gate.py` (WP04) and `guards.py` (WP05)

## Branch Strategy

- Planning base branch: `main`
- Merge target: `main`
- Execution worktrees are allocated per computed lane from `lanes.json`

---

### Subtask T003: Create bulk_edit Package

**Purpose**: Set up the new package directory with `__init__.py`.

**Steps**:

1. Create `src/specify_cli/bulk_edit/__init__.py` with public API exports:
   ```python
   """Bulk edit occurrence classification guardrail.

   Provides workflow gates and validation for missions that perform
   codebase-wide renames, terminology migrations, or other bulk edits.
   """

   from specify_cli.bulk_edit.occurrence_map import (
       load_occurrence_map,
       validate_occurrence_map,
       check_admissibility,
       OccurrenceMap,
       ValidationResult,
       VALID_ACTIONS,
       VALID_OPERATIONS,
   )

   __all__ = [
       "load_occurrence_map",
       "validate_occurrence_map",
       "check_admissibility",
       "OccurrenceMap",
       "ValidationResult",
       "VALID_ACTIONS",
       "VALID_OPERATIONS",
   ]
   ```

2. Create `tests/specify_cli/bulk_edit/__init__.py` (empty, for test discovery)

**Files**: `src/specify_cli/bulk_edit/__init__.py`, `tests/specify_cli/bulk_edit/__init__.py`

---

### Subtask T004: Create occurrence_map.py — Loading, Validation, Admissibility

**Purpose**: Implement the core schema validation for `occurrence_map.yaml`.

**Steps**:

1. Create `src/specify_cli/bulk_edit/occurrence_map.py`

2. Define constants:
   ```python
   VALID_ACTIONS: frozenset[str] = frozenset({
       "rename", "manual_review", "do_not_change", "rename_if_user_visible",
   })
   VALID_OPERATIONS: frozenset[str] = frozenset({
       "rename", "remove", "deprecate",
   })
   PLACEHOLDER_TERMS: frozenset[str] = frozenset({
       "TODO", "TBD", "FIXME", "XXX", "PLACEHOLDER", "",
   })
   REQUIRED_TOP_LEVEL_KEYS: frozenset[str] = frozenset({
       "target", "categories",
   })
   OPTIONAL_TOP_LEVEL_KEYS: frozenset[str] = frozenset({
       "exceptions", "status",
   })
   MIN_ADMISSIBLE_CATEGORIES: int = 3
   ```

3. Define dataclasses:
   ```python
   @dataclass(frozen=True)
   class ValidationResult:
       valid: bool
       errors: list[str]
       warnings: list[str]

   @dataclass(frozen=True)
   class OccurrenceMap:
       target_term: str
       target_replacement: str | None
       target_operation: str
       categories: dict[str, dict[str, str]]  # name -> {action, notes?}
       exceptions: list[dict[str, str]]
       status: dict[str, Any] | None
       raw: dict[str, Any]  # full parsed YAML for forward compatibility
   ```

4. Implement `load_occurrence_map(feature_dir: Path) -> OccurrenceMap | None`:
   - Look for `feature_dir / "occurrence_map.yaml"`
   - If missing: return None
   - Parse with `ruamel.yaml` (YAML round-trip loader for comment preservation)
   - Return `OccurrenceMap` dataclass

5. Implement `validate_occurrence_map(omap: OccurrenceMap) -> ValidationResult`:
   Apply all validation rules from data-model.md:
   - `target` section exists with non-empty `term`
   - `target.operation` is in `VALID_OPERATIONS`
   - `categories` section exists with at least 1 entry
   - Every category entry has `action` key
   - Every action is in `VALID_ACTIONS`
   - Warn on unknown top-level keys (don't error — forward compat)

6. Implement `check_admissibility(omap: OccurrenceMap) -> ValidationResult`:
   Beyond structural validation:
   - `target.term` is not a placeholder (not in `PLACEHOLDER_TERMS`)
   - At least `MIN_ADMISSIBLE_CATEGORIES` categories classified
   - Returns separate admissibility errors

7. Use `from __future__ import annotations` and full type annotations throughout.

**Files**: `src/specify_cli/bulk_edit/occurrence_map.py`

**Validation**:
- [ ] `load_occurrence_map()` returns None for missing file
- [ ] `load_occurrence_map()` parses valid YAML into OccurrenceMap
- [ ] `validate_occurrence_map()` catches all structural errors from data-model.md
- [ ] `check_admissibility()` rejects placeholder terms and insufficient categories
- [ ] Unknown top-level keys produce warnings, not errors
- [ ] mypy --strict passes

---

### Subtask T005: Unit Tests for Occurrence Map Validation

**Purpose**: Comprehensive tests for loading, validation, and admissibility.

**Steps**:

1. Create `tests/specify_cli/bulk_edit/test_occurrence_map.py`

2. Test fixtures — create helper to write YAML files in `tmp_path`:
   ```python
   def write_occurrence_map(feature_dir: Path, content: dict) -> Path:
       """Write occurrence_map.yaml and return its path."""
       ...
   ```

3. Test cases for `load_occurrence_map`:
   - `test_load_missing_file_returns_none`
   - `test_load_valid_yaml_returns_occurrence_map`
   - `test_load_malformed_yaml_raises`

4. Test cases for `validate_occurrence_map`:
   - `test_valid_complete_map_passes`
   - `test_missing_target_section_fails`
   - `test_missing_target_term_fails`
   - `test_empty_target_term_fails`
   - `test_invalid_target_operation_fails`
   - `test_missing_categories_section_fails`
   - `test_empty_categories_fails`
   - `test_category_missing_action_fails`
   - `test_category_invalid_action_fails`
   - `test_unknown_top_level_keys_warn`
   - `test_multiple_errors_reported_together`

5. Test cases for `check_admissibility`:
   - `test_admissible_map_passes`
   - `test_placeholder_term_fails` (for each placeholder: TODO, TBD, etc.)
   - `test_fewer_than_3_categories_fails`
   - `test_exactly_3_categories_passes`

6. Test valid YAML fixture with all 8 standard categories (code_symbols, import_paths, filesystem_paths, serialized_keys, cli_commands, user_facing_strings, tests_fixtures, logs_telemetry).

**Files**: `tests/specify_cli/bulk_edit/test_occurrence_map.py`

**Validation**:
- [ ] All tests pass: `pytest tests/specify_cli/bulk_edit/test_occurrence_map.py -v`
- [ ] Coverage >= 90% on `occurrence_map.py`

## Definition of Done

- [ ] `bulk_edit` package created with `__init__.py` exporting public API
- [ ] `occurrence_map.py` loads, validates, and checks admissibility of YAML
- [ ] All 8 standard categories defined as constants
- [ ] All validation rules from data-model.md implemented
- [ ] Tests pass with 90%+ coverage
- [ ] mypy --strict passes

## Risks

- **Low**: ruamel.yaml API differences between versions. Use round-trip loader (`YAML(typ='safe')` or `YAML()`) consistently with existing codebase patterns.

## Reviewer Guidance

- Verify all validation rules from `data-model.md` are implemented (compare rule table)
- Check that unknown keys produce warnings, not errors (forward compatibility)
- Confirm admissibility criteria match data model (3+ categories, no placeholder terms)
- Verify frozen dataclasses are used (immutable after construction)

## Activity Log

- 2026-04-13T19:01:19Z – claude:opus:implementer:implementer – shell_pid=49899 – Started implementation via action command
- 2026-04-13T19:06:19Z – claude:opus:implementer:implementer – shell_pid=49899 – Ready for review
- 2026-04-13T19:06:41Z – claude:opus:reviewer:reviewer – shell_pid=59383 – Started review via action command
- 2026-04-13T19:07:09Z – claude:opus:reviewer:reviewer – shell_pid=59383 – Review passed: clean schema, validation, admissibility. 17 tests. Frozen dataclasses, ruamel.yaml safe loader, forward-compatible warnings.
- 2026-04-13T19:32:07Z – claude:opus:reviewer:reviewer – shell_pid=59383 – Done override: Feature merged to main
