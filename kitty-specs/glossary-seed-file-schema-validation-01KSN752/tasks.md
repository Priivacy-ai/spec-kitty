# Tasks: Glossary Seed File Schema Validation

**Mission**: glossary-seed-file-schema-validation-01KSN752
**Date**: 2026-05-27
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|----------|
| T001 | Fix bad data: normalize `Sonar quality gate` surface in spec_kitty_core.yaml | WP01 | |
| T002 | Add `SeedValidationError` dataclass to `exceptions.py` | WP01 | |
| T003 | Add `SeedFileValidationError` exception to `exceptions.py` | WP01 | |
| T004 | Create `GlossarySeedTerm` Pydantic model in `seed_schema.py` | WP01 | |
| T005 | Create `GlossarySeedFile` Pydantic model in `seed_schema.py` | WP01 | |
| T006 | Write unit tests for seed_schema.py and exception classes | WP01 | |
| T007 | Create `validate_seed_file_data()` in `seed_validation.py` | WP02 | |
| T008 | Add `validate_scope_filename()` in `seed_validation.py` | WP02 | |
| T009 | Implement Pydantic `ValidationError` → `SeedValidationError` translation | WP02 | |
| T010 | Write unit tests for `seed_validation.py` | WP02 | |
| T011 | Update `validate_seed_file()` in scope.py to delegate to Pydantic | WP03 | |
| T012 | Update `load_seed_file()` to use `validate_seed_file_data()` | WP03 | |
| T013 | Update `save_seed_file()` to validate before writing | WP03 | |
| T014 | Update scope.py imports for new modules | WP03 | |
| T015 | Update `test_scope.py` for new validation behavior | WP03 | |
| T016 | Add `validate` subcommand to glossary CLI typer app | WP04 | [P] |
| T017 | Implement single-file validation mode | WP04 | |
| T018 | Implement directory validation mode with scope filename check | WP04 | |
| T019 | Write CLI validate command integration tests | WP04 | |
| T020 | Add `validation_errors` field to `GlossaryHealthResponse` in `api_types.py` | WP05 | [P] |
| T021 | Update `handle_glossary_health` to catch `SeedFileValidationError` | WP05 | |
| T022 | Update `handle_glossary_terms` error handling | WP05 | |
| T023 | Update `_collect_all_senses` to propagate validation errors | WP05 | |
| T024 | Write dashboard handler validation error tests | WP05 | |

## Work Packages

### WP01: Foundation — Pydantic Models and Error Types

**Priority**: 1 (Critical Path)
**Dependencies**: None
**Prompt**: [tasks/WP01-foundation-models.md](tasks/WP01-foundation-models.md)
**Estimated size**: ~350 lines

**Goal**: Create the Pydantic validation models (`GlossarySeedFile`, `GlossarySeedTerm`) and error types (`SeedValidationError`, `SeedFileValidationError`) that all downstream WPs depend on. Fix the known bad data.

**Subtasks**:
- [ ] T001 Fix bad data: normalize `Sonar quality gate` → `sonar quality gate` in `.kittify/glossaries/spec_kitty_core.yaml` (WP01)
- [ ] T002 Add `SeedValidationError` frozen dataclass to `src/specify_cli/glossary/exceptions.py` (WP01)
- [ ] T003 Add `SeedFileValidationError` exception class to `src/specify_cli/glossary/exceptions.py` (WP01)
- [ ] T004 Create `GlossarySeedTerm` Pydantic model in `src/specify_cli/glossary/seed_schema.py` (WP01)
- [ ] T005 Create `GlossarySeedFile` Pydantic model in `src/specify_cli/glossary/seed_schema.py` (WP01)
- [ ] T006 Write unit tests in `tests/specify_cli/glossary/test_seed_schema.py` (WP01)

**Implementation sketch**: Fix bad YAML data first. Add error dataclass and exception to existing exceptions.py. Create new seed_schema.py with Pydantic models following doctrine pattern (ConfigDict frozen=True, extra="forbid"). Write comprehensive unit tests covering all invariants.

**Risks**: Unknown fields in existing seed files may trigger `extra="forbid"` — audit `.kittify/glossaries/` first.

---

### WP02: Validation Orchestration

**Priority**: 2 (Critical Path)
**Dependencies**: WP01
**Prompt**: [tasks/WP02-validation-orchestration.md](tasks/WP02-validation-orchestration.md)
**Estimated size**: ~350 lines

**Goal**: Build the validation orchestration layer that translates Pydantic errors into structured `SeedValidationError` lists and validates scope filenames.

**Subtasks**:
- [ ] T007 Create `validate_seed_file_data()` in `src/specify_cli/glossary/seed_validation.py` (WP02)
- [ ] T008 Add `validate_scope_filename()` in `src/specify_cli/glossary/seed_validation.py` (WP02)
- [ ] T009 Implement Pydantic `ValidationError` → `SeedValidationError` translation logic (WP02)
- [ ] T010 Write unit tests in `tests/specify_cli/glossary/test_seed_validation.py` (WP02)

**Implementation sketch**: Create seed_validation.py. The main fn parses YAML dict via `GlossarySeedFile.model_validate()`, catches `ValidationError`, translates each error's `loc` tuple into file/term/field context. Scope filename validator maps against `GlossaryScope` enum values.

**Parallel**: WP03 and WP04 can start after WP02 completes (both depend on WP02, not each other).

---

### WP03: Runtime Integration — load_seed_file and save_seed_file

**Priority**: 3
**Dependencies**: WP02
**Prompt**: [tasks/WP03-runtime-integration.md](tasks/WP03-runtime-integration.md)
**Estimated size**: ~350 lines

**Goal**: Wire the Pydantic validation into the existing `load_seed_file()` and `save_seed_file()` functions so all runtime load/save paths enforce the schema.

**Subtasks**:
- [ ] T011 Update `validate_seed_file()` in scope.py to delegate to `validate_seed_file_data()` (WP03)
- [ ] T012 Update `load_seed_file()` to validate via Pydantic before constructing `TermSurface` objects (WP03)
- [ ] T013 Update `save_seed_file()` to validate term data before writing to disk (WP03)
- [ ] T014 Update scope.py imports for new modules (WP03)
- [ ] T015 Update `tests/specify_cli/glossary/test_scope.py` for new validation behavior (WP03)

**Implementation sketch**: Replace the minimal `validate_seed_file(data)` call in `load_seed_file()` with `validate_seed_file_data(data, seed_path)`. The validated `GlossarySeedFile` object's data feeds into `TermSurface`/`TermSense` construction (guaranteed valid). For `save_seed_file()`, construct a validation dict from the `TermSense` list and validate before writing.

**Parallel**: Can run in parallel with WP04 (different files).

---

### WP04: CLI Validate Command

**Priority**: 3
**Dependencies**: WP02
**Prompt**: [tasks/WP04-cli-validate-command.md](tasks/WP04-cli-validate-command.md)
**Estimated size**: ~400 lines

**Goal**: Add `spec-kitty glossary validate <path>` CLI command for manual validation and CI integration.

**Subtasks**:
- [ ] T016 Add `validate` subcommand to glossary CLI typer app in `src/specify_cli/cli/commands/glossary.py` (WP04)
- [ ] T017 Implement single-file validation mode (WP04)
- [ ] T018 Implement directory validation mode with scope filename check (WP04)
- [ ] T019 Write CLI validate command integration tests in `tests/specify_cli/cli/commands/test_glossary_validate.py` (WP04)

**Implementation sketch**: Add `@app.command("validate")` to existing glossary typer app. Accepts `path` argument (file or dir) and `--json` flag. File mode calls `validate_seed_file_data()`. Directory mode iterates `*.yaml`, validates filenames against scopes, validates each file. Rich output for human mode, JSON for `--json`. Exit code 1 on failure.

**Parallel**: Can run in parallel with WP03 (different files).

---

### WP05: Dashboard Error Surfacing

**Priority**: 4
**Dependencies**: WP03
**Prompt**: [tasks/WP05-dashboard-error-surfacing.md](tasks/WP05-dashboard-error-surfacing.md)
**Estimated size**: ~350 lines

**Goal**: Replace silent empty-data responses in dashboard glossary handlers with structured validation error reporting.

**Subtasks**:
- [ ] T020 Add `validation_errors` field to `GlossaryHealthResponse` in `src/specify_cli/dashboard/api_types.py` (WP05)
- [ ] T021 Update `handle_glossary_health` to catch `SeedFileValidationError` and include error details (WP05)
- [ ] T022 Update `handle_glossary_terms` to log validation errors (WP05)
- [ ] T023 Update `_collect_all_senses` to propagate `SeedFileValidationError` instead of silently returning empty list (WP05)
- [ ] T024 Write dashboard handler tests in `tests/specify_cli/dashboard/test_glossary_handler.py` (WP05)

**Implementation sketch**: Add optional `validation_errors` key to `GlossaryHealthResponse` TypedDict. Update `_collect_all_senses` to let `SeedFileValidationError` propagate (catch only other exceptions). In `handle_glossary_health`, catch `SeedFileValidationError`, populate `validation_errors` list with file/term/field/message dicts. `/api/glossary-terms` logs errors and returns `[]` (existing behavior, but with logging).

---

## Dependency Graph

```
WP01 (Foundation)
  │
  ▼
WP02 (Validation Orchestration)
  │
  ├──────────────┐
  ▼              ▼
WP03 (Runtime) WP04 (CLI)  ← parallel
  │
  ▼
WP05 (Dashboard)
```

## Parallelization Opportunities

- **WP03 + WP04**: Independent after WP02 — different file sets, no overlap
- All other WPs are sequential on the critical path

## MVP Scope

**WP01 + WP02 + WP03** is the minimum viable fix — runtime validation prevents the silent zero-terms bug. WP04 and WP05 are high-value polish (CLI for CI, dashboard for operators).
