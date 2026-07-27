---
work_package_id: WP01
title: Directive Model & Repository
lane: "done"
dependencies: []
base_branch: feature/agent-profile-implementation
base_commit: 36e93d77a380d95a374f9a9f32281ebd688886b8
created_at: '2026-02-27T18:47:20.298002+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Foundation
assignee: ''
agent: claude-opus
shell_pid: '121229'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-02-26T04:36:22Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP01 – Directive Model & Repository

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`,````bash`

---

## Objectives & Success Criteria

- Create the `Directive` Pydantic model with all fields from the data model (id, schema_version, title, intent, enforcement, tactic_refs, scope, procedures, integrity_rules, validation_criteria)
- Create `DirectiveRepository` following the `agent_profiles/repository.py` pattern exactly
- Create schema validation utility using `Draft202012Validator`
- Move existing directive YAML files into `src/doctrine/directives/shipped/`
- `DirectiveRepository().list_all()` returns all shipped directives as `Directive` objects
- `DirectiveRepository().get("004")` normalizes to `DIRECTIVE_004` and returns the directive
- `DirectiveRepository().save(directive)` writes a compliant YAML file
- All code passes `mypy --strict` and `ruff check`

## Context & Constraints

- **Pattern to follow**: `src/doctrine/agent_profiles/` — study `profile.py`, `repository.py`, and `validation.py` carefully before implementing
- **Data model**: See `kitty-specs/046-doctrine-artifact-domain-models/data-model.md` § Directive
- **Schema**: `src/doctrine/schemas/directive.schema.yaml` (use `Draft202012Validator`, NOT `Draft7Validator`)
- **Design decisions**: DD-001 (files move to `shipped/`), DD-004 (repository base pattern), DD-006 (ID normalization)
- **ATDD/TDD**: Write acceptance tests FIRST, then implement to make them pass

## Subtasks & Detailed Guidance

### Subtask T001 – Create `src/doctrine/directives/__init__.py`

- **Purpose**: Establish the directives subpackage with clean public API.
- **Steps**:
  1. Create `src/doctrine/directives/__init__.py`
  2. Export: `Directive`, `DirectiveRepository`, `Enforcement`
  3. Use `__all__` to declare public API
- **Files**: `src/doctrine/directives/__init__.py` (new, ~15 lines)
- **Notes**: Follow the same export pattern as `src/doctrine/agent_profiles/__init__.py`

### Subtask T002 – Create `src/doctrine/directives/models.py`

- **Purpose**: Define the `Directive` Pydantic model and `Enforcement` enum.
- **Steps**:
  1. Create `Enforcement` as a `StrEnum` with values `required` and `advisory`
  2. Create `Directive` as a frozen Pydantic `BaseModel` with `ConfigDict(frozen=True, populate_by_name=True)`
  3. Map all fields from the data model:
     - `id: str` — pattern `^[A-Z][A-Z0-9_-]*$` (SCREAMING_SNAKE_CASE)
     - `schema_version: str` — alias `"schema-version"`
     - `title: str`
     - `intent: str`
     - `enforcement: Enforcement`
     - `tactic_refs: list[str] = Field(default_factory=list, alias="tactic-refs")` — kebab-case IDs
     - `scope: str | None = None`
     - `procedures: list[str] = Field(default_factory=list)`
     - `integrity_rules: list[str] = Field(default_factory=list, alias="integrity-rules")`
     - `validation_criteria: list[str] = Field(default_factory=list, alias="validation-criteria")`
  4. Use `BeforeValidator` for `enforcement` to handle case-insensitive parsing (follow `agent_profiles/profile.py` pattern)
- **Files**: `src/doctrine/directives/models.py` (new, ~60 lines)
- **Notes**:
  - Check existing `profile.py` for the exact Pydantic v2 pattern used (ConfigDict, Field aliases, validators)
  - The `scope`, `procedures`, `integrity_rules`, `validation_criteria` fields are optional — they will be populated in WP05-WP09

### Subtask T003 – Create `src/doctrine/directives/repository.py`

- **Purpose**: Implement `DirectiveRepository` for loading, querying, and saving directive YAML files.
- **Steps**:
  1. Study `src/doctrine/agent_profiles/repository.py` thoroughly — replicate its structure
  2. Constructor: `__init__(shipped_dir: Path | None = None, project_dir: Path | None = None)`
     - Default `shipped_dir`: use `importlib.resources.files("doctrine.directives") / "shipped"`
     - `project_dir`: optional, for project-level overrides
  3. Implement `_load()`:
     - Scan `shipped_dir` for `*.directive.yaml` files
     - Parse each with `ruamel.yaml` YAML loader
     - Construct `Directive` objects via Pydantic model validation
     - Log warnings (don't crash) on malformed files
     - If `project_dir` exists, scan it too and merge at field level
  4. Implement `list_all() -> list[Directive]`: return all loaded directives
  5. Implement `get(id: str) -> Directive | None`:
     - Accept both `"004"` and `"DIRECTIVE_004"` forms
     - Normalize: if `id` is all digits or matches `^\d+$`, prepend `"DIRECTIVE_"`
     - If `id` matches `^[A-Z]` but doesn't start with `DIRECTIVE_`, try as-is
     - Return `None` if not found
  6. Implement `save(directive: Directive) -> Path`:
     - Derive filename: extract numeric prefix from id (e.g., `DIRECTIVE_004` → `004`), slugify title → `004-test-driven-implementation-standard.directive.yaml`
     - Write to `project_dir` (or `shipped_dir` if no project_dir)
     - Use `ruamel.yaml` for writing (preserves formatting)
     - Return the written file path
  7. Implement `_merge_directives(shipped: Directive, project: Directive) -> Directive`:
     - Field-level merge: project fields override shipped fields where set
     - Follow `_merge_profiles()` pattern from agent_profiles
- **Files**: `src/doctrine/directives/repository.py` (new, ~150 lines)
- **Notes**:
  - The ID normalization logic is unique to directives (DD-006) — other repositories use simple kebab-case lookup
  - Use `@lru_cache` or lazy loading to avoid re-scanning on every call
  - Handle the `__init__.py` file in shipped/ directory (must not be treated as YAML)

### Subtask T004 – Create `src/doctrine/directives/validation.py`

- **Purpose**: Schema validation utility for directive YAML files.
- **Steps**:
  1. Study `src/doctrine/agent_profiles/validation.py` — replicate its pattern
  2. Load schema from `src/doctrine/schemas/directive.schema.yaml` using `importlib.resources.files`
  3. Use `@lru_cache` for schema loading (avoid re-reading on each validation)
  4. Create `validate_directive(data: dict) -> list[str]`: returns list of validation error messages (empty = valid)
  5. Use `Draft202012Validator` (per research.md R-005, NOT `Draft7Validator`)
- **Files**: `src/doctrine/directives/validation.py` (new, ~40 lines)
- **Notes**: The validator class differs from agent_profiles (which uses `Draft7Validator`). This is intentional per the schema draft version.

### Subtask T005 – Move directive YAML files into `shipped/`

- **Purpose**: Relocate existing directive YAML files from `src/doctrine/directives/` to `src/doctrine/directives/shipped/` (DD-001).
- **Steps**:
  1. Create `src/doctrine/directives/shipped/` directory
  2. Create `src/doctrine/directives/shipped/__init__.py` (empty, for package resource access)
  3. Move all `*.directive.yaml` files from `src/doctrine/directives/` to `src/doctrine/directives/shipped/`
  4. Update `src/doctrine/directives/README.md` to reflect new subpackage structure
  5. Verify no other code references the old paths (search for `doctrine/directives/*.yaml` patterns)
- **Files**:
  - `src/doctrine/directives/shipped/` (new directory)
  - All `*.directive.yaml` files (moved)
- **Parallel?**: Must be done before or alongside T003 (repository needs files in `shipped/`)
- **Notes**:
  - The `test-first.directive.yaml` file also needs to be moved
  - Existing tests that reference these paths will break — they'll be fixed in WP10

### Subtask T006 – Write ATDD/TDD tests

- **Purpose**: Comprehensive test coverage for the Directive model and repository.
- **Steps**:
  1. Create `tests/doctrine/directives/` directory with `__init__.py` and `conftest.py`
  2. **Acceptance tests first** (`tests/doctrine/directives/test_acceptance.py`):
     - Test: `DirectiveRepository().list_all()` returns all shipped directives
     - Test: `DirectiveRepository().get("004")` returns `Directive` with correct `title`, `enforcement`
     - Test: `DirectiveRepository().get("DIRECTIVE_004")` returns same directive as `get("004")`
     - Test: `DirectiveRepository().save(directive)` writes valid YAML, re-loadable
     - Test: Loading shipped directives produces zero validation errors
  3. **Unit tests** (`tests/doctrine/directives/test_models.py`):
     - Test: `Directive` construction with all required fields
     - Test: `Directive` construction with optional fields (scope, procedures, etc.)
     - Test: `Enforcement` enum values (`required`, `advisory`)
     - Test: Invalid `Enforcement` value raises `ValidationError`
     - Test: YAML alias mapping (`schema-version` → `schema_version`, etc.)
     - Test: Model is frozen (immutable)
  4. **Repository tests** (`tests/doctrine/directives/test_repository.py`):
     - Test: ID normalization (`"004"` → `DIRECTIVE_004`)
     - Test: `get()` returns `None` for unknown ID
     - Test: `list_all()` returns non-empty list
     - Test: Field-level merge with project overrides
     - Test: Malformed YAML file is skipped with warning (not crash)
  5. **Validation tests** (`tests/doctrine/directives/test_validation.py`):
     - Test: Valid directive data passes validation
     - Test: Missing required field fails validation
     - Test: Invalid enforcement value fails validation
- **Files**: `tests/doctrine/directives/` (new directory, ~200 lines total)
- **Notes**: Write acceptance tests FIRST, watch them fail, then implement code to make them pass (ATDD flow)

## Test Strategy

**Methodology**: ATDD/TDD — acceptance tests drive the implementation.

**Test execution order**:
1. Write acceptance tests (T006 step 2) → they fail
2. Implement T001-T005 → acceptance tests pass
3. Write unit tests (T006 steps 3-5) → they may fail
4. Refine implementation → all tests pass

**Commands**:
```bash
pytest tests/doctrine/directives/ -v
mypy src/doctrine/directives/ --strict
ruff check src/doctrine/directives/
```

**Fixtures**: Create a `conftest.py` with:
- `tmp_directive_dir` — temp directory with sample directive YAML files
- `sample_directive_data` — dict with valid directive fields

## Risks & Mitigations

- **Moving YAML files breaks existing tests**: Known risk. Existing tests will be updated in WP10. Focus on new tests passing in this WP.
- **ID normalization edge cases**: Test with various formats (`"4"`, `"04"`, `"004"`, `"DIRECTIVE_004"`, `"directive_004"`). Decide on canonical behavior and document.
- **importlib.resources path resolution**: Test that `importlib.resources.files("doctrine.directives")` resolves correctly in both development (editable install) and packaged mode.

## Review Guidance

- Verify the repository follows `agent_profiles/repository.py` structure closely
- Verify ID normalization handles `"004"` and `"DIRECTIVE_004"` correctly
- Verify `Draft202012Validator` is used (not Draft7)
- Verify all acceptance tests exist and pass
- Verify no hardcoded paths — all use `importlib.resources`

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-02-26T04:36:22Z – system – lane=planned – Prompt created.

---

### Updating Lane Status

To change a work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter AND append activity log entry (at the end)
2. **Use CLI**: `spec-kitty agent tasks move-task WP01 --to <lane> --note "message"` (recommended)

**Valid lanes**: `planned`, `doing`, `for_review`, `done`

### Implementation Command

No dependencies — branch from target branch:
```bash
spec-kitty implement WP01
```
- 2026-02-27T18:47:20Z – claude-opus – shell_pid=16652 – lane=doing – Assigned agent via workflow command
- 2026-02-28T04:02:22Z – claude-opus – shell_pid=16652 – lane=for_review – 23 new tests + 62 existing tests pass. Schema extended, files relocated, test paths updated.
- 2026-02-28T04:06:06Z – claude-opus – shell_pid=121229 – lane=doing – Started review via workflow command
- 2026-02-28T04:22:32Z – claude-opus – shell_pid=121229 – lane=done – Review passed: WP01 merged into feature branch. Directive model, repository, validation verified. 85 tests pass.
