---
work_package_id: WP03
title: Styleguide Model & Repository
lane: "done"
dependencies: []
subtasks:
- T013
- T014
- T015
- T016
- T017
- T018
phase: Phase 1 - Foundation
assignee: ''
agent: ''
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

# Work Package Prompt: WP03 – Styleguide Model & Repository

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Create `Styleguide`, `AntiPattern` Pydantic models and `StyleguideScope` enum
- Create `StyleguideRepository` following the `agent_profiles/repository.py` pattern
- Move existing styleguide YAML files into `src/doctrine/styleguides/shipped/`
- `StyleguideRepository().get("kitty-glossary-writing")` returns a `Styleguide` with `scope == "glossary"`
- `StyleguideRepository().list_all()` returns all shipped styleguides
- Handle the `writing/` subdirectory structure (recursive scan)

## Context & Constraints

- **Data model**: See `kitty-specs/046-doctrine-artifact-domain-models/data-model.md` § Styleguide, AntiPattern
- **Schema**: `src/doctrine/schemas/styleguide.schema.yaml`
- **Important**: The `writing/kitty-glossary-writing.styleguide.yaml` is in a subdirectory — repository must scan recursively
- **ATDD/TDD**: Write acceptance tests FIRST

## Subtasks & Detailed Guidance

### Subtask T013 – Create `src/doctrine/styleguides/__init__.py`

- **Purpose**: Establish the styleguides subpackage.
- **Steps**:
  1. Create `__init__.py` exporting `Styleguide`, `AntiPattern`, `StyleguideScope`, `StyleguideRepository`
  2. Use `__all__`
- **Files**: `src/doctrine/styleguides/__init__.py` (new, ~15 lines)

### Subtask T014 – Create `src/doctrine/styleguides/models.py`

- **Purpose**: Define Styleguide, AntiPattern models and StyleguideScope enum.
- **Steps**:
  1. Create `StyleguideScope` as `StrEnum`: `code`, `docs`, `architecture`, `testing`, `operations`, `glossary`
  2. Create `AntiPattern` as frozen `BaseModel`:
     - `name: str` — required
     - `description: str` — required
     - `bad_example: str` — required
     - `good_example: str` — required
  3. Create `Styleguide` as frozen `BaseModel` with `ConfigDict(frozen=True, populate_by_name=True)`:
     - `id: str` — kebab-case
     - `schema_version: str` — alias `"schema-version"`
     - `title: str`
     - `scope: StyleguideScope`
     - `principles: list[str]` — minItems: 1
     - `anti_patterns: list[AntiPattern] = Field(default_factory=list)`
     - `quality_test: str | None = None` — alias `"quality_test"`
     - `references: list[str] = Field(default_factory=list)`
- **Files**: `src/doctrine/styleguides/models.py` (new, ~55 lines)
- **Notes**: Check the actual YAML key naming convention in the schema — `anti_patterns` may use underscores or hyphens in YAML. Verify against `styleguide.schema.yaml`.

### Subtask T015 – Create `src/doctrine/styleguides/repository.py`

- **Purpose**: Implement `StyleguideRepository`.
- **Steps**:
  1. Constructor with `shipped_dir` and `project_dir`
     - Default: `importlib.resources.files("doctrine.styleguides") / "shipped"`
  2. `_load()`: scan for `**/*.styleguide.yaml` — MUST be recursive to find `writing/` subdirectory files
  3. `list_all()`, `get(id)`, `save(styleguide)`
  4. `_merge_styleguides()` for project overrides
- **Files**: `src/doctrine/styleguides/repository.py` (new, ~120 lines)
- **Notes**: The recursive scan is the key difference from other repositories. Use `Path.rglob("*.styleguide.yaml")` or equivalent.

### Subtask T016 – Create `src/doctrine/styleguides/validation.py`

- **Purpose**: Schema validation for styleguide YAML files.
- **Steps**: Same pattern as T004 but using `styleguide.schema.yaml`
- **Files**: `src/doctrine/styleguides/validation.py` (new, ~40 lines)

### Subtask T017 – Move styleguide YAML files into `shipped/`

- **Purpose**: Relocate styleguide YAML files to `src/doctrine/styleguides/shipped/`.
- **Steps**:
  1. Create `src/doctrine/styleguides/shipped/` with `__init__.py`
  2. Move all `*.styleguide.yaml` from `src/doctrine/styleguides/` to `shipped/`
  3. Move `writing/` subdirectory into `shipped/writing/`
  4. Preserve the `writing/` subdirectory structure inside `shipped/`
  5. Update README.md
- **Files**: All styleguide YAML files + `writing/` directory (moved)
- **Notes**: The `writing/` subdirectory must be preserved inside `shipped/` to maintain the organizational structure

### Subtask T018 – Write ATDD/TDD tests

- **Purpose**: Test coverage for Styleguide models and repository.
- **Steps**:
  1. Create `tests/doctrine/styleguides/` directory
  2. **Acceptance tests**:
     - `StyleguideRepository().get("kitty-glossary-writing")` returns Styleguide with scope `glossary`
     - `list_all()` returns all shipped styleguides (including subdirectory ones)
     - All shipped styleguides validate against schema
  3. **Unit tests**:
     - `StyleguideScope` enum values
     - `AntiPattern` with 4 required fields
     - `Styleguide` construction and alias mapping
  4. **Repository tests**:
     - Recursive scan finds `writing/` subdirectory files
     - `get()` returns `None` for unknown ID
- **Files**: `tests/doctrine/styleguides/` (new, ~150 lines)

## Test Strategy

```bash
pytest tests/doctrine/styleguides/ -v
mypy src/doctrine/styleguides/ --strict
```

## Risks & Mitigations

- **Recursive scan**: Must handle `writing/` subdirectory correctly. Test with nested directory structure.
- **`importlib.resources` with subdirectories**: Verify `importlib.resources.files()` handles nested directories in both dev and installed mode.

## Review Guidance

- Verify recursive scan finds styleguides in `writing/` subdirectory
- Verify `AntiPattern` has all 4 required fields
- Verify `StyleguideScope` enum values match schema exactly

## Activity Log

- 2026-02-26T04:36:22Z – system – lane=planned – Prompt created.

---

### Implementation Command

```bash
spec-kitty implement WP03
```
- 2026-02-28T04:31:40Z – unknown – lane=in_progress – Starting WP03: Styleguide Model & Repository
- 2026-02-28T04:35:02Z – unknown – lane=done – Styleguide model, repository, validation implemented. 25 new + 62 existing tests pass. | Done override: DD-010: Branch Simplicity - committed directly to feature branch.
