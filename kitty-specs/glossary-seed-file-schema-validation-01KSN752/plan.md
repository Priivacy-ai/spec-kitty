# Implementation Plan: Glossary Seed File Schema Validation

**Branch**: `main` | **Date**: 2026-05-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/glossary-seed-file-schema-validation-01KSN752/spec.md`

## Summary

Add Pydantic-based schema validation for glossary seed files at all write/edit/load/CI boundaries. Invalid glossary state — such as a non-normalized `surface` value — is currently caught only at `TermSurface` construction time inside `load_seed_file()`, causing the entire scope to fail with a raw `ValueError`. Dashboard handlers silently catch this and report zero terms.

This plan introduces `GlossarySeedFile` and `GlossarySeedTerm` Pydantic models as the aggregate boundary for seed file validation, following the doctrine artifact pattern (`ConfigDict(frozen=True, extra="forbid")`). Validation runs before domain object construction in `load_seed_file()`, before writes in `save_seed_file()`, and via a new `spec-kitty glossary validate` CLI command for manual and CI use.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pydantic>=2.0 (already in pyproject.toml), typer, rich, ruamel.yaml, pytest, mypy (strict)
**Storage**: Filesystem — `.kittify/glossaries/*.yaml` seed files
**Testing**: pytest with 90%+ coverage for new code, mypy --strict, integration tests for CLI commands
**Target Platform**: CLI (cross-platform)
**Project Type**: Single project — extends existing `src/specify_cli/glossary/` package
**Performance Goals**: Validation of 100-term seed file < 500ms
**Constraints**: Must not break existing valid seed files; Pydantic models are validation layer only — existing dataclass domain objects (`TermSurface`, `TermSense`) remain as runtime model

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **typer**: CLI framework — confirmed, glossary CLI already uses typer
- **rich**: Console output — confirmed, glossary CLI already uses rich
- **ruamel.yaml**: YAML parsing — confirmed, `load_seed_file()` already uses it
- **pydantic>=2.0**: Already a project dependency (pyproject.toml line 63)
- **pytest 90%+ coverage**: Will be met for new validation code
- **mypy --strict**: Will be met for new modules
- **Integration tests for CLI**: Will cover new `validate` command

No charter violations. All technologies are existing project dependencies.

## Project Structure

### Documentation (this feature)

```
kitty-specs/glossary-seed-file-schema-validation-01KSN752/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: codebase analysis and pattern decisions
├── data-model.md        # Phase 1: Pydantic model design
├── quickstart.md        # Phase 1: developer guide
├── contracts/           # Phase 1: CLI and dashboard API contracts
│   └── validate-command.md
└── meta.json            # Mission metadata
```

### Source Code (repository root)

```
src/specify_cli/glossary/
├── seed_schema.py       # NEW: GlossarySeedFile, GlossarySeedTerm Pydantic models
├── seed_validation.py   # NEW: validate_seed_file_data(), structured error collection
├── exceptions.py        # MODIFY: add SeedFileValidationError
├── scope.py             # MODIFY: update validate_seed_file(), load_seed_file(), save_seed_file()
└── ... (existing files unchanged)

src/specify_cli/cli/commands/
└── glossary.py          # MODIFY: add validate subcommand

src/specify_cli/dashboard/handlers/
└── glossary.py          # MODIFY: surface validation errors instead of silent empty

tests/
├── specify_cli/glossary/
│   ├── test_seed_schema.py       # NEW: Pydantic model unit tests
│   ├── test_seed_validation.py   # NEW: validation function tests
│   └── test_scope.py             # MODIFY: update for new validation behavior
├── specify_cli/cli/commands/
│   └── test_glossary_validate.py # NEW: CLI validate command tests
└── specify_cli/dashboard/
    └── test_glossary_handler.py  # MODIFY: validation error surfacing tests
```

**Structure Decision**: Extends existing `src/specify_cli/glossary/` package with two new modules (`seed_schema.py` for Pydantic models, `seed_validation.py` for validation orchestration). Follows the doctrine pattern of separating model definition from validation logic.

## Architecture

### Validation Layer Design

```
YAML on disk
    │
    ▼
ruamel.yaml parse → dict
    │
    ▼
seed_validation.validate_seed_file_data(data, file_path)
    │
    ├─ Pydantic parse: GlossarySeedFile.model_validate(data)
    │      │
    │      ├─ Root: mapping with "terms" key
    │      ├─ Per term: GlossarySeedTerm validates:
    │      │   ├─ surface: str, normalized (== lower().strip())
    │      │   ├─ definition: str, non-empty
    │      │   ├─ confidence: float, 0.0..1.0 (optional, default 1.0)
    │      │   └─ status: Literal["active","draft","deprecated"] (optional, default "draft")
    │      └─ extra="forbid" — unknown fields rejected
    │
    ├─ On success → return validated data
    │
    └─ On failure → raise SeedFileValidationError
           │
           └─ errors: list[SeedValidationError]
                  each has: file_path, term_index, term_surface, field, message
```

### Integration Points

| Boundary | Current Behavior | New Behavior |
|----------|-----------------|--------------|
| `load_seed_file()` | `validate_seed_file()` checks structure, then `TermSurface()` raises `ValueError` on bad surface | `validate_seed_file_data()` runs full Pydantic validation first; raises `SeedFileValidationError` with all errors at once |
| `save_seed_file()` | No validation — writes directly | Validates term data before writing; raises `SeedFileValidationError` if invalid |
| CLI `glossary validate` | Does not exist | New command: validates file or directory, reports all errors, exits non-zero on failure |
| Dashboard handlers | Catches `Exception`, returns empty data | Catches `SeedFileValidationError` specifically, includes error details in response |
| CI | No glossary validation | Runs `spec-kitty glossary validate .kittify/glossaries/` |

### Scope Filename Validation

Seed filenames must map to known `GlossaryScope` values. The `validate` command validates this when given a directory path:

| Filename | Valid Scope |
|----------|-------------|
| `mission_local.yaml` | `GlossaryScope.MISSION_LOCAL` |
| `team_domain.yaml` | `GlossaryScope.TEAM_DOMAIN` |
| `audience_domain.yaml` | `GlossaryScope.AUDIENCE_DOMAIN` |
| `spec_kitty_core.yaml` | `GlossaryScope.SPEC_KITTY_CORE` |
| anything else | **Rejected** with error |

### Error Model

```
SeedFileValidationError(GlossaryError)
├── file_path: Path
├── errors: list[SeedValidationError]
│       each: file_path, term_index (int|None), term_surface (str|None),
│              field (str|None), message (str)
└── __str__() → human-readable multi-line report
```

### Dashboard Error Surfacing

The `handle_glossary_health` and `handle_glossary_terms` handlers currently catch `Exception` broadly and return empty/zero data. After this change:

- `SeedFileValidationError` is caught specifically
- `GlossaryHealthResponse` gains an optional `validation_errors` field (list of error dicts)
- `/api/glossary-terms` returns a JSON object with `terms: []` and `validation_errors: [...]` instead of bare `[]`
- Existing consumers that parse the array response continue to work via a backward-compatible wrapper (the `/api/glossary-terms` endpoint returns `[]` only when there are no errors; when errors exist, it returns the object form)

### Immediate Data Fix

The known bad entry (`surface: Sonar quality gate`) in `.kittify/glossaries/spec_kitty_core.yaml` will be fixed as the first work package — a prerequisite commit that normalizes the surface to `sonar quality gate`.

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Existing seed files have fields not in schema | Audit all seed files in repo before finalizing `extra="forbid"`. If metadata fields exist, add them to the model or use an allowlist. |
| Dashboard API contract change breaks consumers | Add `validation_errors` as optional field; bare-array response remains default for valid data |
| `save_seed_file()` validation rejects data that was previously written | `save_seed_file()` already constructs `TermSense` objects with validated `TermSurface` — the Pydantic layer catches the same invariants earlier |
| Replacing `ValueError` with `SeedFileValidationError` breaks callers | Grep all `except ValueError` and `except Exception` catches in glossary callers; `SeedFileValidationError` extends `GlossaryError` which extends `Exception`, so broad catches still work |

## Charter Re-check (Post-Design)

- All new modules use project dependencies only (pydantic, typer, rich, ruamel.yaml)
- No new external dependencies introduced
- Testing strategy aligned with charter (pytest 90%+, mypy strict, integration tests)
- No charter violations identified post-design
