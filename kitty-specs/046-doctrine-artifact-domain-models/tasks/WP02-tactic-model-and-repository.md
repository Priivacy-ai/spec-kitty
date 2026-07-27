---
work_package_id: WP02
title: Tactic Model & Repository
lane: "done"
dependencies: []
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
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

# Work Package Prompt: WP02 – Tactic Model & Repository

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`,````bash`

---

## Objectives & Success Criteria

- Create `Tactic`, `TacticStep`, `TacticReference` Pydantic models and `ReferenceType` enum
- Create `TacticRepository` following the `agent_profiles/repository.py` pattern
- Create schema validation utility using `Draft202012Validator`
- Move existing tactic YAML files into `src/doctrine/tactics/shipped/`
- `TacticRepository().get("zombies-tdd")` returns a `Tactic` with 7 steps
- `TacticRepository().list_all()` returns all shipped tactics
- `TacticRepository().save(tactic)` writes a compliant YAML file

## Context & Constraints

- **Pattern to follow**: `src/doctrine/agent_profiles/` — study `profile.py`, `repository.py`, `validation.py`
- **Data model**: See `kitty-specs/046-doctrine-artifact-domain-models/data-model.md` § Tactic, TacticStep, TacticReference
- **Schema**: `src/doctrine/schemas/tactic.schema.yaml` — uses `$defs` for reference objects
- **Design decisions**: DD-001 (files move to `shipped/`), DD-004 (repository base pattern)
- **ATDD/TDD**: Write acceptance tests FIRST, then implement to make them pass

## Subtasks & Detailed Guidance

### Subtask T007 – Create `src/doctrine/tactics/__init__.py`

- **Purpose**: Establish the tactics subpackage with clean public API.
- **Steps**:
  1. Create `src/doctrine/tactics/__init__.py`
  2. Export: `Tactic`, `TacticStep`, `TacticReference`, `TacticRepository`, `ReferenceType`
  3. Use `__all__` to declare public API
- **Files**: `src/doctrine/tactics/__init__.py` (new, ~15 lines)

### Subtask T008 – Create `src/doctrine/tactics/models.py`

- **Purpose**: Define Tactic, TacticStep, TacticReference Pydantic models and ReferenceType enum.
- **Steps**:
  1. Create `ReferenceType` as `StrEnum`: `styleguide`, `tactic`, `directive`, `toolguide`
  2. Create `TacticReference` as frozen `BaseModel`:
     - `name: str` — required
     - `type: ReferenceType` — required
     - `id: str` — required
     - `when: str` — required
  3. Create `TacticStep` as frozen `BaseModel`:
     - `title: str` — required
     - `description: str | None = None`
     - `examples: list[str] = Field(default_factory=list)`
     - `references: list[TacticReference] = Field(default_factory=list)`
  4. Create `Tactic` as frozen `BaseModel` with `ConfigDict(frozen=True, populate_by_name=True)`:
     - `id: str` — pattern `^[a-z][a-z0-9-]*$` (kebab-case)
     - `schema_version: str` — alias `"schema-version"`
     - `name: str`
     - `purpose: str | None = None`
     - `steps: list[TacticStep]` — minItems: 1
     - `references: list[TacticReference] = Field(default_factory=list)`
- **Files**: `src/doctrine/tactics/models.py` (new, ~70 lines)
- **Notes**:
  - Both `Tactic` and `TacticStep` have `references` fields — these are independent lists
  - The schema uses `$defs` for reference objects; model both at tactic and step level

### Subtask T009 – Create `src/doctrine/tactics/repository.py`

- **Purpose**: Implement `TacticRepository` for loading, querying, and saving tactic YAML files.
- **Steps**:
  1. Constructor: `__init__(shipped_dir: Path | None = None, project_dir: Path | None = None)`
     - Default `shipped_dir`: `importlib.resources.files("doctrine.tactics") / "shipped"`
  2. Implement `_load()`: scan for `*.tactic.yaml`, parse, construct `Tactic` objects
  3. Implement `list_all() -> list[Tactic]`
  4. Implement `get(id: str) -> Tactic | None` — simple kebab-case lookup (no normalization needed)
  5. Implement `save(tactic: Tactic) -> Path`: write YAML to `project_dir`
  6. Implement `_merge_tactics()` for project overrides
- **Files**: `src/doctrine/tactics/repository.py` (new, ~120 lines)
- **Notes**: Simpler than DirectiveRepository — no ID normalization needed. Tactic IDs are kebab-case, so direct lookup.

### Subtask T010 – Create `src/doctrine/tactics/validation.py`

- **Purpose**: Schema validation utility for tactic YAML files.
- **Steps**:
  1. Load schema from `src/doctrine/schemas/tactic.schema.yaml`
  2. Use `@lru_cache` for schema loading
  3. Create `validate_tactic(data: dict) -> list[str]`
  4. Use `Draft202012Validator`
- **Files**: `src/doctrine/tactics/validation.py` (new, ~40 lines)

### Subtask T011 – Move tactic YAML files into `shipped/`

- **Purpose**: Relocate existing tactic YAML files to `src/doctrine/tactics/shipped/`.
- **Steps**:
  1. Create `src/doctrine/tactics/shipped/` directory with `__init__.py`
  2. Move all `*.tactic.yaml` files from `src/doctrine/tactics/` to `shipped/`
  3. Update `README.md` in `src/doctrine/tactics/`
- **Files**: All `*.tactic.yaml` files (moved)
- **Notes**: Existing tests referencing old paths will be fixed in WP10

### Subtask T012 – Write ATDD/TDD tests

- **Purpose**: Comprehensive test coverage for Tactic models and repository.
- **Steps**:
  1. Create `tests/doctrine/tactics/` directory with `__init__.py` and `conftest.py`
  2. **Acceptance tests** (`test_acceptance.py`):
     - `TacticRepository().get("zombies-tdd")` returns Tactic with 7 steps
     - `TacticRepository().list_all()` returns non-empty list
     - Saving and reloading a tactic preserves all fields
     - All shipped tactics validate against schema
  3. **Unit tests** (`test_models.py`):
     - `Tactic` construction with required fields
     - `TacticStep` with optional fields
     - `TacticReference` with all required fields
     - `ReferenceType` enum values
     - YAML alias mapping (`schema-version` → `schema_version`)
  4. **Repository tests** (`test_repository.py`):
     - `get()` returns `None` for unknown ID
     - Malformed YAML skipped with warning
     - Field-level merge with project overrides
- **Files**: `tests/doctrine/tactics/` (new directory, ~180 lines total)

## Test Strategy

**Methodology**: ATDD/TDD

```bash
pytest tests/doctrine/tactics/ -v
mypy src/doctrine/tactics/ --strict
```

## Risks & Mitigations

- **Nested model parsing**: `TacticStep` contains `TacticReference` list — ensure Pydantic handles nested model validation correctly with YAML data
- **Schema `$defs`**: The tactic schema uses `$defs` for reference objects — verify `Draft202012Validator` resolves `$ref` correctly

## Review Guidance

- Verify nested models (`TacticStep` → `TacticReference`) parse correctly from YAML
- Verify `steps` field enforces minItems: 1 (at least one step required)
- Verify `ReferenceType` enum matches schema values exactly

## Activity Log

- 2026-02-26T04:36:22Z – system – lane=planned – Prompt created.

---

### Implementation Command

No dependencies — branch from target branch:
```bash
spec-kitty implement WP02
```
- 2026-02-28T04:26:32Z – unknown – lane=in_progress – Starting WP02: Tactic Model & Repository
- 2026-02-28T04:31:28Z – unknown – lane=done – Tactic model, repository, validation implemented. 27 new + 62 existing tests pass. | Done override: DD-010: Branch Simplicity - committed directly to feature branch, no worktree needed.
