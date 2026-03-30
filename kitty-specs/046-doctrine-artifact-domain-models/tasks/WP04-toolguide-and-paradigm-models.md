---
work_package_id: WP04
title: Toolguide & Paradigm Models
lane: "done"
dependencies: []
subtasks:
- T019
- T020
- T021
- T022
- T023
- T024
phase: Phase 1 - Foundation
assignee: ''
agent: codex
shell_pid: ''
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-02-26T04:36:22Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 – Toolguide & Paradigm Models

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Create `Toolguide` Pydantic model and `ToolguideRepository`
- Create `Paradigm` Pydantic model and `ParadigmRepository`
- Create `paradigm.schema.yaml` (new schema — DD-003)
- Move YAML (and companion MD) files into `shipped/` subdirectories
- `ToolguideRepository().get("powershell-syntax")` returns a valid `Toolguide`
- `ParadigmRepository().get("test-first")` returns a valid `Paradigm`
- Both `save()` methods write compliant YAML

## Context & Constraints

- **Data model**: See `data-model.md` § Toolguide, Paradigm
- **Toolguide schema**: `src/doctrine/schemas/toolguide.schema.yaml`
- **Paradigm schema**: None exists — create `paradigm.schema.yaml` (DD-003)
- **Important**: Toolguide has companion MD files (`guide-path` field) — these must also move to `shipped/`
- **ATDD/TDD**: Write acceptance tests FIRST

## Subtasks & Detailed Guidance

### Subtask T019 – Create toolguide subpackage files

- **Purpose**: Create `__init__.py`, `models.py`, `repository.py`, `validation.py` for toolguides.
- **Steps**:
  1. Create `src/doctrine/toolguides/__init__.py` exporting `Toolguide`, `ToolguideRepository`
  2. Create `models.py` with `Toolguide` model:
     - `id: str` — kebab-case
     - `schema_version: str` — alias `"schema-version"`
     - `tool: str`
     - `title: str`
     - `guide_path: str` — alias `"guide-path"`, pattern `^src/doctrine/.+\.md$`
     - `summary: str`
     - `commands: list[str] = Field(default_factory=list)`
  3. Create `repository.py` with `ToolguideRepository`:
     - Default shipped dir: `importlib.resources.files("doctrine.toolguides") / "shipped"`
     - Scan for `*.toolguide.yaml`
     - Standard `list_all()`, `get()`, `save()` API
  4. Create `validation.py` with `validate_toolguide()` using `Draft202012Validator`
- **Files**: `src/doctrine/toolguides/` (new subpackage, ~200 lines total)
- **Notes**: The `guide_path` field points to companion markdown files. These paths will need updating after relocation (the paths reference `src/doctrine/...` which remains valid if the MD files are inside the package).

### Subtask T020 – Move toolguide files into `shipped/`

- **Purpose**: Relocate toolguide YAML and companion MD files.
- **Steps**:
  1. Create `src/doctrine/toolguides/shipped/` with `__init__.py`
  2. Move all `*.toolguide.yaml` from `src/doctrine/toolguides/` to `shipped/`
  3. Move companion `.md` files referenced by `guide-path` into `shipped/`
  4. Update `guide-path` values in YAML files if paths change (may need to adjust the path pattern)
  5. Update README.md
- **Files**: All toolguide YAML + companion MD files (moved)
- **Notes**: Carefully check whether `guide-path` values need updating. The schema pattern is `^src/doctrine/.+\.md$` — if the MD files stay within the package, paths remain valid. If paths are relative to the repo root, they may not need updating.

### Subtask T021 – Create paradigm subpackage files

- **Purpose**: Create `__init__.py`, `models.py`, `repository.py`, `validation.py` for paradigms.
- **Steps**:
  1. Create `src/doctrine/paradigms/__init__.py` exporting `Paradigm`, `ParadigmRepository`
  2. Create `models.py` with `Paradigm` model:
     - `id: str` — kebab-case
     - `schema_version: str` — alias `"schema-version"`
     - `name: str`
     - `summary: str` — multiline
  3. Create `repository.py` with `ParadigmRepository`:
     - Default shipped dir: `importlib.resources.files("doctrine.paradigms") / "shipped"`
     - Scan for `*.paradigm.yaml`
     - Standard `list_all()`, `get()`, `save()` API
  4. Create `validation.py` with `validate_paradigm()` using `Draft202012Validator`
- **Files**: `src/doctrine/paradigms/` (new subpackage, ~180 lines total)
- **Notes**: Paradigm is the simplest model — only 4 fields, all required.

### Subtask T022 – Create `paradigm.schema.yaml`

- **Purpose**: Formalize the paradigm structure with a JSON Schema (DD-003).
- **Steps**:
  1. Create `src/doctrine/schemas/paradigm.schema.yaml` following existing schema conventions
  2. Schema structure:
     ```yaml
     $schema: "https://json-schema.org/draft/2020-12/schema"
     title: "Paradigm"
     type: object
     required:
       - schema-version
       - id
       - name
       - summary
     properties:
       schema-version:
         type: string
         pattern: "^1\\.0$"
       id:
         type: string
         pattern: "^[a-z][a-z0-9-]*$"
       name:
         type: string
       summary:
         type: string
     additionalProperties: false
     ```
  3. Validate existing paradigm YAML files against this schema
- **Files**: `src/doctrine/schemas/paradigm.schema.yaml` (new, ~20 lines)
- **Notes**: Follow the same schema structure as `directive.schema.yaml` and `tactic.schema.yaml`

### Subtask T023 – Move paradigm YAML files into `shipped/`

- **Purpose**: Relocate paradigm YAML files.
- **Steps**:
  1. Create `src/doctrine/paradigms/shipped/` with `__init__.py`
  2. Move all `*.paradigm.yaml` from `src/doctrine/paradigms/` to `shipped/`
  3. Update README.md
- **Files**: All paradigm YAML files (moved)

### Subtask T024 – Write ATDD/TDD tests

- **Purpose**: Test coverage for both Toolguide and Paradigm models/repositories.
- **Steps**:
  1. Create `tests/doctrine/toolguides/` and `tests/doctrine/paradigms/`
  2. **Toolguide acceptance tests**:
     - `ToolguideRepository().get("powershell-syntax")` returns valid Toolguide
     - `list_all()` returns all shipped toolguides
     - All shipped toolguides validate against schema
  3. **Paradigm acceptance tests**:
     - `ParadigmRepository().get("test-first")` returns valid Paradigm
     - `list_all()` returns all shipped paradigms
     - All shipped paradigms validate against new schema
  4. **Unit tests for both**: model construction, alias mapping, enum values, frozen models
  5. **Repository tests**: get unknown ID returns None, save and reload, merge
- **Files**: `tests/doctrine/toolguides/` + `tests/doctrine/paradigms/` (new, ~160 lines total)

## Test Strategy

```bash
pytest tests/doctrine/toolguides/ tests/doctrine/paradigms/ -v
mypy src/doctrine/toolguides/ src/doctrine/paradigms/ --strict
```

## Risks & Mitigations

- **Companion MD files**: Toolguide `guide-path` references may need path updates after relocation. Test that paths resolve correctly.
- **New paradigm schema**: No existing schema to validate against — verify existing YAML files conform before deploying schema.

## Review Guidance

- Verify paradigm schema covers all fields in existing YAML files
- Verify toolguide companion MD files are relocated and `guide-path` references work
- Verify both repositories follow the canonical pattern

## Activity Log

- 2026-02-26T04:36:22Z – system – lane=planned – Prompt created.

---

### Implementation Command

```bash
spec-kitty implement WP04
```
- 2026-02-28T04:35:22Z – unknown – lane=in_progress – Starting WP04: Toolguide & Paradigm Models
- 2026-02-28T08:19:19Z – codex – lane=for_review – WP04 implementation complete; doctrine tests passing
- 2026-03-04T04:46:44Z – codex – lane=done – Reviewed and approved: Toolguide and Paradigm models complete, 33 tests passing.
